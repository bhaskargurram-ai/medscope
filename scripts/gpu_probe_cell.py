# ===== GPU use probe: how much of the GPU does one MedScope training job use? (~5 min) =====
import threading, subprocess, time, random, statistics
import numpy as np, torch
from medscope.train.hf_policy import HFPolicy
from medscope.train.sft import samples_for
from medscope.eval.runner import load_views

N_SAMPLES, GRAD_ACCUM = 48, 8                      # same micro-batch (1) and accumulation (8) as the real training
p = torch.cuda.get_device_properties(0)
name, total_gb = p.name, p.total_memory / 2**30
PEAK = next((v for k, v in {'A100': 312, 'H100': 989, 'L4': 121, 'RTX PRO 6000': 500}.items() if k in name), None)
print(f'GPU: {name} | {p.multi_processor_count} SMs | {total_gb:.0f} GB | BF16 peak ~{PEAK} TFLOPS')

# the same model, LoRA and gradient checkpointing as scripts/train_sft.py
policy = HFPolicy('Qwen/Qwen3.5-4B', trainable=True, new_lora=True)
model = policy.model
model.train()                                       # as in train_sft (gradient checkpointing is active in train mode)
n_params = sum(q.numel() for q in model.parameters())
opt = torch.optim.AdamW([q for q in model.parameters() if q.requires_grad], lr=1e-4)

# real v4 training samples (same trajectory builder and options as stage 1)
views = [v for f in TRAIN_V4.split() for v in load_views(f)]
random.seed(0)
samples = []
for i, v in enumerate(random.sample(views, 200)):
    samples += samples_for(v, 'agentic', 0, i, window_prob=0.3, small_zoom=True)
    if len(samples) >= N_SAMPLES + 4:
        break

util = []
def watch(stop):                                    # GPU busy % every 0.2 s while the probe runs
    while not stop.is_set():
        out = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
                             capture_output=True, text=True).stdout.strip()
        if out.isdigit():
            util.append(int(out))
        time.sleep(0.2)

# token count of each sample (prompt incl. image tokens + answer), measured outside the timed loop
lengths = [policy.encode(s.messages)['input_ids'].shape[1] + policy.target_ids(s.target).shape[0] for s in samples]

def step(s):                                        # exactly what train_sft does for one sample
    target = policy.target_ids(s.target)
    lp = policy.token_logprobs(s.messages, target)
    (-lp.mean() / GRAD_ACCUM).backward()

for s in samples[:4]:                               # warm-up (kernel compilation), not timed
    step(s)
opt.zero_grad(set_to_none=True)
torch.cuda.synchronize(); torch.cuda.reset_peak_memory_stats()
stop = threading.Event(); threading.Thread(target=watch, args=(stop,), daemon=True).start()
t0, per = time.time(), []
tokens = lengths[4:4 + N_SAMPLES]
for k, s in enumerate(samples[4:4 + N_SAMPLES]):
    ts = time.time()
    step(s)
    if (k + 1) % GRAD_ACCUM == 0:
        opt.step(); opt.zero_grad(set_to_none=True)
    torch.cuda.synchronize(); per.append(time.time() - ts)
secs = time.time() - t0
stop.set()

tok = sum(tokens)
tflops = 6 * n_params * tok / secs / 1e12          # forward 2N + backward 2N + checkpoint recompute 2N per token
peak_gb = torch.cuda.max_memory_reserved() / 2**30
print(f'\n--- one training job, {N_SAMPLES} samples ---')
print(f'model parameters: {n_params / 1e9:.2f} B | tokens per sample: mean {np.mean(tokens):.0f}, max {max(tokens)}')
print(f'time per sample: {np.mean(per):.2f} s  ->  {60 / np.mean(per) / GRAD_ACCUM:.1f} optimiser steps per minute')
print(f'compute used: ~{tflops:.0f} TFLOPS' + (f' = ~{100 * tflops / PEAK:.0f}% of the GPU peak' if PEAK else ''))
print(f'GPU busy (nvidia-smi): mean {statistics.mean(util):.0f}%, median {statistics.median(util):.0f}%  '
      '(this only says a kernel was running, not how many cores were used)')
print(f'peak GPU memory: {peak_gb:.1f} of {total_gb:.0f} GB')
fit = int(total_gb * 0.92 // (peak_gb + 1.5))
print(f'\n=> about {fit} training job(s) of this size fit in this GPU at the same time'
      + (' -> try two parts in one tab, e.g. PART = "3+4"' if fit >= 2 else ' -> one part per tab'))
del policy, model, opt; torch.cuda.empty_cache()
