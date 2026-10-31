"""Frontier models behind an API (OpenAI, Google Gemini) as agent policies.

They see exactly the same system prompt, images, tool results and turn structure as the local
models; only the transport differs. Several conversations are sent in parallel. Keys come from
the environment (OPENAI_API_KEY, GEMINI_API_KEY), never from code.
"""

from __future__ import annotations

import base64
import io
import os
import random
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
            print(f"  API error ({type(e).__name__}: {str(e)[:100]}); retrying in {wait:.0f}s", flush=True)
            time.sleep(wait)


class _ApiPolicy:
    load_in_4bit = False
    dtype = "api"

    def __init__(self, model: str, max_tokens: int = 16000, workers: int = 8):
        self.model, self.max_tokens, self.workers = model, max_tokens, workers

    def generate(self, messages: list[dict], sample: bool = False) -> Generation:
        try:
            text = with_retries(lambda: self._call(messages))
        except Exception as e:  # noqa: BLE001 - a refused or failed request is scored as malformed
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
        self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    @staticmethod
    def to_openai(messages: list[dict]) -> list[dict]:
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
                    parts.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})
                else:
                    parts.append({"type": "text", "text": c["text"]})
            out.append({"role": "user", "content": parts})
        return out

    def _call(self, messages: list[dict]) -> str:
        r = self.client.chat.completions.create(model=self.model, messages=self.to_openai(messages),
                                                max_completion_tokens=self.max_tokens)
        return r.choices[0].message.content or ""


class GeminiPolicy(_ApiPolicy):
    def __init__(self, model: str, **kw):
        super().__init__(model, **kw)
        from google import genai
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

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
        r = self.client.models.generate_content(
            model=self.model, contents=contents,
            config=types.GenerateContentConfig(system_instruction=system, max_output_tokens=self.max_tokens))
        return r.text or ""


def api_policy(provider: str, model: str, workers: int = 8) -> _ApiPolicy:
    return {"openai": OpenAIPolicy, "gemini": GeminiPolicy}[provider](model, workers=workers)


def available_models(provider: str) -> Optional[list[str]]:
    """Model ids the key can use (to pick the newest flagship)."""
    try:
        if provider == "openai":
            from openai import OpenAI
            return sorted(m.id for m in OpenAI(api_key=os.environ["OPENAI_API_KEY"]).models.list())
        from google import genai
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])   # keep a reference: the list is fetched lazily
        return sorted(m.name for m in client.models.list())
    except Exception as e:  # noqa: BLE001
        print(f"could not list {provider} models: {e}")
        return None
