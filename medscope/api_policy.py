"""Frontier models behind an API (OpenAI, Anthropic, Google Gemini) as agent policies.

They see exactly the same system prompt, images, tool results and turn structure as the local
models; only the transport differs. Several conversations are sent in parallel. Keys come from
the environment (OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY), never from code.

Every call's token usage is recorded (input, output including reasoning), so a run's real cost is
measured from the provider's own counts, not estimated.
"""

from __future__ import annotations

import base64
import io
import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import numpy as np
from PIL import Image

from .agent.episode import Generation


def png_bytes(img: np.ndarray, max_side: int = 768) -> bytes:
    im = Image.fromarray(img).convert("RGB")
    scale = max_side / max(im.size)
    if scale < 1:
        im = im.resize((round(im.size[0] * scale), round(im.size[1] * scale)), Image.BICUBIC)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def with_retries(fn, tries: int = 6):
    for attempt in range(tries):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 - rate limits, timeouts, transient server errors
            if attempt == tries - 1:
                raise
            wait = min(60, 2 ** attempt + random.random())
            cause = f" <- {type(e.__cause__).__name__}: {str(e.__cause__)[:120]}" if e.__cause__ else ""
            print(f"  API error ({type(e).__name__}: {str(e)[:100]}{cause}); retrying in {wait:.0f}s", flush=True)
            time.sleep(wait)


# A request that hangs is cut off after this many seconds and retried (with_retries), so one stuck
# connection cannot stall a run. Generous: thinking models can take a minute on a hard image.
TIMEOUT_S = 180

# USD per 1M tokens (input, output), standard tier, from the providers' pricing pages on 2026-10-31.
# Output includes reasoning/thinking tokens. Image inputs are billed as input tokens.
PRICES = {
    "gpt-6-astra": (10.00, 50.00), "gpt-6.1-sol": (2.00, 10.00), "gpt-6.1-terra": (1.00, 5.00),
    "gpt-6-luna": (0.10, 0.50),
    "gpt-6-sol": (2.00, 10.00),               # superseded; no longer on OpenAI's page, price from third-party listings
    "claude-fable-5-1": (10.00, 50.00), "claude-opus-5-5": (4.00, 20.00), "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
    "gemini-4-argon": (2.00, 10.00),          # until 2026-11-30, then 4.00 / 20.00
    "gemini-3.1-pro-preview": (2.00, 12.00), "gemini-3.8-flash": (0.75, 3.75),
}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> Optional[float]:
    if model not in PRICES:
        return None
    pin, pout = PRICES[model]
    return input_tokens / 1e6 * pin + output_tokens / 1e6 * pout


def measured_cost_per_view(run_dir) -> Optional[dict]:
    """Average tokens and dollars per view from a run's usage.json (only calls that ran views count)."""
    import json
    from pathlib import Path
    p = Path(run_dir) / "usage.json"
    if not p.exists():
        return None
    u = json.loads(p.read_text())
    calls = [c for c in u.get("calls", []) if c.get("views_run")]
    n = sum(c["views_run"] for c in calls)
    if not n:
        return None
    tin, tout = sum(c["input_tokens"] for c in calls), sum(c["output_tokens"] for c in calls)
    return {"model": u["model"], "views": n, "requests_per_view": sum(c["requests"] for c in calls) / n,
            "input_per_view": tin / n, "output_per_view": tout / n,
            "usd_per_view": None if cost_usd(u["model"], tin, tout) is None else cost_usd(u["model"], tin, tout) / n}


class _ApiPolicy:
    load_in_4bit = False
    dtype = "api"

    def __init__(self, model: str, max_tokens: int = 16000, workers: int = 8, effort: Optional[str] = None,
                 image_detail: Optional[str] = None):
        # effort="high": the provider's highest reasoning setting (OpenAI reasoning_effort="high", Anthropic
        # output_config effort "max" with adaptive thinking, Gemini thinking level "high"); None keeps the provider
        # default used in the main comparison. Thinking counts toward the output limit, so it is raised.
        # image_detail="high": the provider's highest image-processing setting (OpenAI image detail "high", Gemini
        # media resolution "high"); None keeps the provider default. Anthropic has no such setting: images up to
        # 1568 px are always processed at the size sent, so the main runs already use its highest setting.
        self.model, self.max_tokens, self.workers, self.effort = model, max_tokens, workers, effort
        self.image_detail = image_detail
        if image_detail not in (None, "high"):
            raise ValueError(f"image_detail must be None or 'high', not {image_detail!r}")
        if effort == "high":
            self.max_tokens = max(max_tokens, 64000)
        self.usage = {"requests": 0, "input_tokens": 0, "output_tokens": 0, "errors": 0}
        self._lock = threading.Lock()

    def _record(self, input_tokens: int, output_tokens: int) -> None:
        with self._lock:
            self.usage["requests"] += 1
            self.usage["input_tokens"] += int(input_tokens or 0)
            self.usage["output_tokens"] += int(output_tokens or 0)

    def generate(self, messages: list[dict], sample: bool = False) -> Generation:
        try:
            text = with_retries(lambda: self._call(messages))
        except Exception as e:  # noqa: BLE001 - a refused or failed request is scored as malformed
            with self._lock:
                self.usage["errors"] += 1
            text = f"[API error: {type(e).__name__}: {str(e)[:200]}]"
        return Generation(text or "")

    def generate_batch(self, conversations: list[list[dict]], sample: bool = False) -> list[Generation]:
        with ThreadPoolExecutor(self.workers) as pool:
            return list(pool.map(lambda m: self.generate(m, sample), conversations))

    def _call(self, messages: list[dict]) -> str:
        raise NotImplementedError


class OpenAIPolicy(_ApiPolicy):
    def __init__(self, model: str, **kw):
        super().__init__(model, **kw)
        from openai import OpenAI
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=TIMEOUT_S, max_retries=0)

    def to_openai(self, messages: list[dict]) -> list[dict]:
        out = []
        for m in messages:
            if m["role"] == "system":
                out.append({"role": "system", "content": " ".join(c["text"] for c in m["content"])})
                continue
            if m["role"] == "assistant":
                out.append({"role": "assistant", "content": " ".join(c["text"] for c in m["content"])})
                continue
            parts = []
            for c in m["content"]:
                if c["type"] == "image":
                    b64 = base64.b64encode(png_bytes(c["image"])).decode()
                    url = {"url": f"data:image/png;base64,{b64}"}
                    if self.image_detail == "high":
                        url["detail"] = "high"
                    parts.append({"type": "image_url", "image_url": url})
                else:
                    parts.append({"type": "text", "text": c["text"]})
            out.append({"role": "user", "content": parts})
        return out

    def _call(self, messages: list[dict]) -> str:
        extra = {"reasoning_effort": "high"} if self.effort == "high" else {}
        r = self.client.chat.completions.create(model=self.model, messages=self.to_openai(messages),
                                                max_completion_tokens=self.max_tokens, **extra)
        if getattr(r, "usage", None):
            self._record(r.usage.prompt_tokens, r.usage.completion_tokens)
        return r.choices[0].message.content or ""


class AnthropicPolicy(_ApiPolicy):
    def __init__(self, model: str, **kw):
        super().__init__(model, **kw)
        import anthropic
        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], timeout=TIMEOUT_S, max_retries=0)

    @staticmethod
    def to_anthropic(messages: list[dict]) -> tuple[str, list[dict]]:
        system = " ".join(c["text"] for m in messages if m["role"] == "system" for c in m["content"])
        out = []
        for m in messages:
            if m["role"] == "system":
                continue
            parts = []
            for c in m["content"]:
                if c["type"] == "image":
                    parts.append({"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                                              "data": base64.b64encode(png_bytes(c["image"])).decode()}})
                else:
                    parts.append({"type": "text", "text": c["text"]})
            out.append({"role": m["role"], "content": parts})
        return system, out

    def _call(self, messages: list[dict]) -> str:
        if self.image_detail:
            raise ValueError("Anthropic models have no image-detail setting (images up to 1568 px are processed as sent)")
        system, msgs = self.to_anthropic(messages)
        if self.effort == "high":
            # highest effort; a long output limit needs streaming in the SDK
            with self.client.messages.stream(model=self.model, system=system, messages=msgs, max_tokens=self.max_tokens,
                                             thinking={"type": "adaptive"},
                                             extra_body={"output_config": {"effort": "max"}}) as s:
                r = s.get_final_message()
        else:
            r = self.client.messages.create(model=self.model, system=system, messages=msgs, max_tokens=self.max_tokens)
        if getattr(r, "usage", None):
            self._record(r.usage.input_tokens, r.usage.output_tokens)
        return "".join(b.text for b in r.content if getattr(b, "type", "") == "text")


class GeminiPolicy(_ApiPolicy):
    def __init__(self, model: str, **kw):
        super().__init__(model, **kw)
        from google import genai
        from google.genai import types
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"],
                                   http_options=types.HttpOptions(timeout=TIMEOUT_S * 1000))   # milliseconds

    def _call(self, messages: list[dict]) -> str:
        from google.genai import types
        system = " ".join(c["text"] for m in messages if m["role"] == "system" for c in m["content"])
        contents = []
        for m in messages:
            if m["role"] == "system":
                continue
            parts = [types.Part.from_bytes(data=png_bytes(c["image"]), mime_type="image/png") if c["type"] == "image"
                     else types.Part.from_text(text=c["text"]) for c in m["content"]]
            contents.append(types.Content(role="model" if m["role"] == "assistant" else "user", parts=parts))
        extra = {}
        if self.image_detail == "high":
            extra["media_resolution"] = types.MediaResolution.MEDIA_RESOLUTION_HIGH   # raises on an SDK without it
        if self.effort == "high":
            try:
                extra = {**extra, "thinking_config": types.ThinkingConfig(thinking_level="high")}
            except Exception:          # older SDKs: a large thinking budget instead
                extra = {**extra, "thinking_config": types.ThinkingConfig(thinking_budget=32768)}
        r = self.client.models.generate_content(
            model=self.model, contents=contents,
            config=types.GenerateContentConfig(system_instruction=system, max_output_tokens=self.max_tokens, **extra))
        u = getattr(r, "usage_metadata", None)
        if u:
            self._record(u.prompt_token_count or 0, (u.candidates_token_count or 0) + (getattr(u, "thoughts_token_count", 0) or 0))
        return r.text or ""


def api_policy(provider: str, model: str, workers: int = 8, effort: Optional[str] = None,
               image_detail: Optional[str] = None) -> _ApiPolicy:
    return {"openai": OpenAIPolicy, "anthropic": AnthropicPolicy, "gemini": GeminiPolicy}[provider](
        model, workers=workers, effort=effort, image_detail=image_detail)


def available_models(provider: str) -> Optional[list[str]]:
    """Model ids the key can use (to pick the newest flagship)."""
    try:
        if provider == "openai":
            from openai import OpenAI
            return sorted(m.id for m in OpenAI(api_key=os.environ["OPENAI_API_KEY"]).models.list())
        if provider == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
            return sorted(m.id for m in client.models.list())
        from google import genai
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])   # keep a reference: the list is fetched lazily
        return sorted(m.name for m in client.models.list())
    except Exception as e:  # noqa: BLE001
        print(f"could not list {provider} models: {e}")
        return None


def cost_table(rows: list[tuple[str, str, str]], pilot_root, results_root, all_views) -> str:
    """Markdown: per model, measured tokens and $ per view (pilot or full run), the cost so far and
    the projected cost of finishing the full run. rows: (run name, provider, model id)."""
    from pathlib import Path
    from .eval.runner import remaining
    lines = ["| Model | Price in/out per 1M | Measured on (views) | Requests per view | Input tokens per view | "
             "Output tokens per view | $ per view | Spent so far | Views left | Projected to finish | Full run total |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    total_left = total_all = 0.0
    for run, provider, model in rows:
        main, pilot = Path(results_root) / run, Path(pilot_root) / run
        m = measured_cost_per_view(main) or measured_cost_per_view(pilot)
        price = PRICES.get(model)
        price_s = f"${price[0]:g} / ${price[1]:g}" if price else "not listed"
        spent = sum(_spent(d) for d in (main, pilot))
        left = len(remaining(all_views, main, "api"))
        if not m:
            lines.append(f"| {model} | {price_s} | not measured yet | | | | | ${spent:.2f} | {left} | run the pilot | |")
            continue
        upv = m["usd_per_view"]
        fin = None if upv is None else upv * left
        full = None if upv is None else upv * len(all_views)
        if fin is not None:
            total_left += fin
            total_all += full
        money = lambda x: "price not listed" if x is None else f"${x:.2f}"  # noqa: E731
        lines.append(f"| {model} | {price_s} | {m['views']} | {m['requests_per_view']:.2f} | {m['input_per_view']:,.0f} | "
                     f"{m['output_per_view']:,.0f} | {money(upv) if upv is None else f'${upv:.4f}'} | ${spent:.2f} | {left} | "
                     f"{money(fin)} | {money(full)} |")
    lines.append(f"\n**Projected cost to finish all listed models: ${total_left:.2f}** "
                 f"(a full run of every model from scratch: ${total_all:.2f}). Tokens are the providers' own counts; "
                 f"prices are the standard-tier list prices of 2026-10-31 (gemini-4-argon doubles from 2026-12-01).")
    return "\n".join(lines)


def _spent(run_dir) -> float:
    import json
    from pathlib import Path
    p = Path(run_dir) / "usage.json"
    if not p.exists():
        return 0.0
    return json.loads(p.read_text()).get("cost_usd") or 0.0

