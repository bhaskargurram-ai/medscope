"""Hugging Face backend for the agent: generation, token log-probs and LoRA.

Works for Qwen3.5-4B and MedGemma 1.5 4B through the shared AutoProcessor +
image-text-to-text interface. Heavy imports happen inside the class so the rest
of the package stays importable without torch.
"""

from __future__ import annotations

import os
from typing import Any, Optional

# fewer out-of-memory errors from fragmentation; must be set before CUDA starts
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import numpy as np
from PIL import Image

from ..agent.episode import Generation

STOP_STRINGS = ["</tool>", "</final>"]
# Vision encoder and projector stay in 16-bit and outside LoRA: only the language model is adapted.
VISION_MODULES = ["visual", "vision_tower", "vision_model", "multi_modal_projector"]
VISION_REGEX = r".*(" + "|".join(VISION_MODULES) + r").*"
LORA_DEFAULTS = dict(r=16, lora_alpha=32, lora_dropout=0.05, target_modules="all-linear",
                     exclude_modules=VISION_REGEX, task_type="CAUSAL_LM")


BIG_GPU_GB = 20  # with at least this much GPU memory, a 4B model runs in 16-bit: faster than 4-bit


def pick_quantization(torch) -> bool:
    """True = load in 4-bit. Only on small GPUs (T4, 15 GB); L4 and A100 run in bf16."""
    if not torch.cuda.is_available():
        return True
    return torch.cuda.get_device_properties(0).total_memory / 2**30 < BIG_GPU_GB


def pick_dtype(torch, model_id: str):
    """bf16 only on GPUs that support it natively (compute capability 8+: L4, A100).

    On older GPUs (T4) use fp16, except Gemma-family models whose activations overflow
    fp16, which get fp32.
    """
    if torch.cuda.is_available() and torch.cuda.get_device_capability()[0] >= 8:
        return torch.bfloat16
    if "gemma" in model_id.lower():
        return torch.float32
    return torch.float16


def _to_pil(img: np.ndarray, max_side: int) -> Image.Image:
    pil = Image.fromarray(img)
    if max(pil.size) > max_side:
        scale = max_side / max(pil.size)
        pil = pil.resize((max(1, round(pil.width * scale)), max(1, round(pil.height * scale))), Image.BICUBIC)
    return pil


class HFPolicy:
    def __init__(
        self,
        model_id: str,
        adapter: Optional[str] = None,
        trainable: bool = False,
        new_lora: bool = False,
        load_in_4bit: Optional[bool] = None,  # None: 4-bit only on GPUs under 20 GB
        max_new_tokens: int = 384,
        temperature: float = 1.0,
        top_p: float = 1.0,
        max_image_side: int = 768,
        gradient_checkpointing: bool = True,
        lora_r: int = 16,                     # new adapters only; the recipe uses 16
        lora_vision: bool = False,            # new adapters only: also adapt the vision encoder and projector
    ):
        import torch
        import transformers
        from transformers import AutoProcessor, BitsAndBytesConfig

        self.torch = torch
        self.model_id = model_id
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.max_image_side = max_image_side
        self.dtype = pick_dtype(torch, model_id)
        if load_in_4bit is None:
            load_in_4bit = pick_quantization(torch)
        self.load_in_4bit = load_in_4bit
        print(f"loading {model_id} in {'4-bit' if load_in_4bit else str(self.dtype).replace('torch.', '')}")

        self.processor = AutoProcessor.from_pretrained(model_id)
        self.tokenizer = getattr(self.processor, "tokenizer", self.processor)
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        template = getattr(self.processor, "chat_template", None) or getattr(self.tokenizer, "chat_template", None) or ""
        self.template_kwargs = {"enable_thinking": False} if "enable_thinking" in str(template) else {}

        model_cls = getattr(transformers, "AutoModelForImageTextToText", None) or transformers.AutoModelForMultimodalLM
        kwargs: dict[str, Any] = dict(dtype=self.dtype, device_map="auto")
        if load_in_4bit:
            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=self.dtype, bnb_4bit_use_double_quant=True,
                llm_int8_skip_modules=VISION_MODULES + ["lm_head"])
        model = model_cls.from_pretrained(model_id, **kwargs)

        if trainable or adapter or new_lora:
            from peft import LoraConfig, PeftModel, get_peft_model, prepare_model_for_kbit_training
            if trainable and load_in_4bit:
                model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=gradient_checkpointing,
                                                        gradient_checkpointing_kwargs={"use_reentrant": False})
            elif trainable and gradient_checkpointing:
                model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
                model.enable_input_require_grads()
            if adapter:
                model = PeftModel.from_pretrained(model, adapter, is_trainable=trainable)
            elif new_lora:
                lora = dict(LORA_DEFAULTS, r=lora_r, lora_alpha=2 * lora_r)
                if lora_vision:
                    lora.pop("exclude_modules")      # LoRA on the vision tower and projector as well
                model = get_peft_model(model, LoraConfig(**lora))
                n_train = sum(p.numel() for p in model.parameters() if p.requires_grad)
                n_vis = sum(p.numel() for n, p in model.named_parameters()
                            if p.requires_grad and any(v in n for v in VISION_MODULES))
                print(f"LoRA rank {lora_r}, vision adapted: {lora_vision}; trainable {n_train / 1e6:.1f}M "
                      f"({n_vis / 1e6:.1f}M in the vision encoder and projector)")
        self.model = model
        if not trainable:
            self.model.eval()
        self.end_of_turn_id = self._find_end_of_turn_id()

    # ---- message encoding ---------------------------------------------------

    def to_hf(self, messages: list[dict]) -> list[dict]:
        out = []
        for m in messages:
            content = []
            for c in m["content"]:
                if c["type"] == "image":
                    content.append({"type": "image", "image": _to_pil(c["image"], self.max_image_side)})
                else:
                    content.append({"type": "text", "text": c["text"]})
            out.append({"role": m["role"], "content": content})
        return out

    def encode(self, messages: list[dict]):
        """Tokenise a conversation ending where the assistant should start writing."""
        return self.encode_cpu(messages).to(self.model.device)

    def encode_cpu(self, messages: list[dict]):
        """Same as encode, left on the CPU: training prepares the next samples this way while the GPU works."""
        hf = self.to_hf(messages)
        return self.processor.apply_chat_template(
            hf, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt",
            **self.template_kwargs)

    def _find_end_of_turn_id(self) -> int:
        """Token that closes an assistant turn (<|im_end|>, <end_of_turn>, ...)."""
        marker = "XQZMARKERXQZ"
        convo = [{"role": "user", "content": [{"type": "text", "text": "hi"}]},
                 {"role": "assistant", "content": [{"type": "text", "text": marker}]}]
        try:
            rendered = self.processor.apply_chat_template(convo, tokenize=False)
            after = rendered.split(marker, 1)[1]
            ids = self.tokenizer(after, add_special_tokens=False)["input_ids"]
            if ids:
                return int(ids[0])
        except Exception:  # noqa: BLE001 - fall back to the tokenizer's eos
            pass
        return int(self.tokenizer.eos_token_id)

    # ---- generation -----------------------------------------------------------

    def _gen_kwargs(self, sample: bool) -> dict:
        # every model decodes the same way: no repetition penalty or n-gram blocking from its own
        # generation_config (some ship one), plain greedy for evaluation, plain sampling for training
        kw = dict(max_new_tokens=self.max_new_tokens, do_sample=sample, stop_strings=STOP_STRINGS,
                  tokenizer=self.tokenizer, pad_token_id=self.tokenizer.pad_token_id,
                  repetition_penalty=1.0, no_repeat_ngram_size=0)
        if sample:
            kw.update(temperature=self.temperature, top_p=self.top_p, top_k=0)
        else:
            kw.update(temperature=None, top_p=None, top_k=None)
        return kw

    def _trim(self, ids):
        """Drop padding and anything after the first end-of-turn token."""
        ids = ids.tolist()
        pad = self.tokenizer.pad_token_id
        out = []
        for t in ids:
            if t == pad and pad != self.end_of_turn_id:
                break
            out.append(t)
            if t == self.end_of_turn_id:
                break
        return self.torch.tensor(out, dtype=self.torch.long)

    def _finish(self, out, prompt_len: int, recorder) -> list[Generation]:
        """Generations from generate() output; with a recorder (greedy), also the answer's probability."""
        from ..confidence import answer_prob
        gens = []
        for i, row in enumerate(out[:, prompt_len:]):
            ids = self._trim(row.cpu())
            extra = {"gen_ids": ids}
            if recorder is not None:
                pieces = [self.tokenizer.decode([int(t)], skip_special_tokens=False) for t in ids]
                extra["answer_prob"] = answer_prob(pieces, recorder.row(i, len(ids)))
            gens.append(Generation(self.decode(ids), extra))
        return gens

    def _generate(self, inputs, sample: bool, n: int = 1):
        from transformers import LogitsProcessorList

        from ..confidence import GreedyProbRecorder
        recorder = None if sample else GreedyProbRecorder()
        kw = self._gen_kwargs(sample)
        if recorder is not None:
            kw["logits_processor"] = LogitsProcessorList([recorder])
        if n > 1:
            kw["num_return_sequences"] = n
        out = self.model.generate(**inputs, **kw)
        return out, recorder

    def generate_n(self, messages: list[dict], n: int, sample: bool = True) -> list[Generation]:
        torch = self.torch
        inputs = self.encode(messages)
        prompt_len = inputs["input_ids"].shape[1]
        was_training = self.model.training
        self.model.eval()
        with torch.no_grad():
            out, recorder = self._generate(inputs, sample, n)
        if was_training:
            self.model.train()
        return self._finish(out, prompt_len, recorder)

    def generate_batch(self, conversations: list[list[dict]], sample: bool = False) -> list[Generation]:
        """One turn for several different conversations in a single left-padded batch.
        Falls back to one at a time if this model's processor cannot batch."""
        torch = self.torch
        if len(conversations) == 1 or getattr(self, "_no_batch", False):
            return [self.generate(m, sample) for m in conversations]
        tok = self.tokenizer
        side = tok.padding_side
        try:
            tok.padding_side = "left"
            inputs = self.processor.apply_chat_template(
                [self.to_hf(m) for m in conversations], add_generation_prompt=True, tokenize=True,
                return_dict=True, return_tensors="pt", padding=True, **self.template_kwargs).to(self.model.device)
        except Exception as e:  # noqa: BLE001
            print(f"batched generation unavailable for this model ({type(e).__name__}); running one at a time")
            self._no_batch = True
            return [self.generate(m, sample) for m in conversations]
        finally:
            tok.padding_side = side
        prompt_len = inputs["input_ids"].shape[1]
        was_training = self.model.training
        self.model.eval()
        try:
            with torch.no_grad():
                out, recorder = self._generate(inputs, sample)
        except torch.cuda.OutOfMemoryError:
            # too large a batch for this GPU: split it in two (same replies, only slower) instead of giving up
            del inputs
            torch.cuda.empty_cache()
            half = len(conversations) // 2
            if not getattr(self, "_oom_noted", False):
                print(f"batch of {len(conversations)} does not fit in GPU memory: running it in halves")
                self._oom_noted = True
            return self.generate_batch(conversations[:half], sample) + self.generate_batch(conversations[half:], sample)
        except Exception as e:  # noqa: BLE001 - e.g. a model whose vision tower can't batch mixed sizes
            print(f"batched generation failed for this model ({type(e).__name__}: {str(e)[:120]}); "
                  "running one at a time")
            self._no_batch = True
            torch.cuda.empty_cache()
            return [self.generate(m, sample) for m in conversations]
        finally:
            if was_training:
                self.model.train()
        return self._finish(out, prompt_len, recorder)

    KEEP_TOKENS = ("<think>", "</think>", "<unused94>", "<unused95>")  # thinking markers the parser needs

    def decode(self, ids) -> str:
        """Decode, dropping special tokens except the ones that mark thinking blocks."""
        text = self.tokenizer.decode(ids, skip_special_tokens=False)
        for tok in self.tokenizer.all_special_tokens:
            if tok and tok not in self.KEEP_TOKENS:
                text = text.replace(tok, "")
        return text

    def generate(self, messages: list[dict], sample: bool = False) -> Generation:
        return self.generate_n(messages, 1, sample)[0]

    # ---- training signals ------------------------------------------------------

    def token_logprobs(self, messages: list[dict], target_ids, inputs=None):
        """Log-prob of each target token given the conversation (with gradients).
        `inputs`: the conversation already tokenised by encode_cpu (identical result, prepared ahead)."""
        torch = self.torch
        inputs = self.encode(messages) if inputs is None else inputs.to(self.model.device)
        prompt = inputs["input_ids"]
        target = target_ids.to(prompt.device).unsqueeze(0)
        n_prompt, n_target = prompt.shape[1], target.shape[1]
        batch = {}
        for k, v in inputs.items():
            if torch.is_tensor(v) and v.dim() >= 2 and v.shape[:2] == prompt.shape:
                pad_val = 1 if k == "attention_mask" else 0
                extra = torch.full((v.shape[0], n_target, *v.shape[2:]), pad_val, dtype=v.dtype, device=v.device)
                batch[k] = torch.cat([v, extra], dim=1)
            else:
                batch[k] = v
        batch["input_ids"] = torch.cat([prompt, target], dim=1)
        try:
            logits = self.model(**batch, use_cache=False, logits_to_keep=n_target + 1).logits[:, :n_target]
        except TypeError:
            logits = self.model(**batch, use_cache=False).logits[:, n_prompt - 1:n_prompt - 1 + n_target]
        logp = torch.log_softmax(logits.float(), dim=-1)
        return logp.gather(-1, target.unsqueeze(-1)).squeeze(-1).squeeze(0)

    def token_logprobs_pair(self, messages: list[dict], target_a, target_b, inputs=None):
        """Per-token log-probs of two candidate replies to the same conversation, in one forward pass of batch 2
        (the prompt, image included, is encoded once and repeated). Returns (logp_a, logp_b), each 1-D."""
        torch = self.torch
        inputs = self.encode(messages) if inputs is None else inputs.to(self.model.device)
        prompt = inputs["input_ids"]
        n_prompt = prompt.shape[1]
        n = max(target_a.shape[0], target_b.shape[0])
        pad = self.tokenizer.pad_token_id or 0
        tgt = torch.full((2, n), pad, dtype=torch.long, device=prompt.device)
        mask = torch.zeros((2, n), dtype=torch.long, device=prompt.device)
        for r, t in enumerate((target_a, target_b)):
            tgt[r, :t.shape[0]] = t.to(prompt.device)
            mask[r, :t.shape[0]] = 1
        batch = {}
        for k, v in inputs.items():
            if torch.is_tensor(v) and v.dim() >= 2 and v.shape[:2] == prompt.shape:      # per-token tensors
                extra = torch.full((1, n, *v.shape[2:]), 0, dtype=v.dtype, device=v.device)
                row = torch.cat([v, extra], dim=1)
                if k == "attention_mask":
                    row = torch.cat([v, mask[:1]], dim=1)
                    batch[k] = torch.cat([row, torch.cat([v, mask[1:]], dim=1)], dim=0)
                else:
                    batch[k] = row.repeat(2, *([1] * (row.dim() - 1)))
            elif torch.is_tensor(v) and v.dim() >= 1 and v.shape[0] != prompt.shape[0]:   # image patches, grids
                batch[k] = torch.cat([v, v], dim=0)
            elif torch.is_tensor(v):
                batch[k] = v.repeat(2, *([1] * (v.dim() - 1)))
            else:
                batch[k] = v
        batch["input_ids"] = torch.cat([prompt.repeat(2, 1), tgt], dim=1)
        try:
            logits = self.model(**batch, use_cache=False, logits_to_keep=n + 1).logits[:, :n]
        except TypeError:
            logits = self.model(**batch, use_cache=False).logits[:, n_prompt - 1:n_prompt - 1 + n]
        logp = torch.log_softmax(logits.float(), dim=-1).gather(-1, tgt.unsqueeze(-1)).squeeze(-1)
        return logp[0, :target_a.shape[0]], logp[1, :target_b.shape[0]]

    def target_ids(self, text: str):
        ids = self.tokenizer(text, add_special_tokens=False)["input_ids"] + [self.end_of_turn_id]
        return self.torch.tensor(ids, dtype=self.torch.long)

    def save_adapter(self, path: str, adapter_name: str = "default") -> None:
        """Save one LoRA adapter's files directly into `path`."""
        cfg = getattr(self.model, "peft_config", {})
        if adapter_name in cfg and len(cfg) > 1:
            # PEFT writes non-default adapters into a subfolder; save just this one at the root
            active = self.model.active_adapter
            self.model.save_pretrained(path, selected_adapters=[adapter_name])
            if adapter_name != "default":
                import shutil
                sub = f"{path}/{adapter_name}"
                for name in ("adapter_config.json", "adapter_model.safetensors", "adapter_model.bin"):
                    src = f"{sub}/{name}"
                    import os
                    if os.path.exists(src):
                        shutil.move(src, f"{path}/{name}")
                shutil.rmtree(sub, ignore_errors=True)
            self.model.set_adapter(active)
        else:
            self.model.save_pretrained(path)
