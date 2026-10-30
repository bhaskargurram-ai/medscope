#!/usr/bin/env bash
# One command to set up a fresh GPU pod (RunPod or any Linux machine with an NVIDIA GPU) and run
# the remaining MedScope steps. Safe to rerun: everything resumes.
#
#   export HF_TOKEN=hf_...                 # Hugging Face token with WRITE access
#   export HF_WORK_REPO=your-name/medscope-work
#   export GITHUB_TOKEN=github_pat_...     # Contents: read and write on the medscope repo
#   bash <(curl -fsSL https://raw.githubusercontent.com/bhaskargurram-ai/medscope/main/scripts/runpod.sh)
#   (private repo: clone it first with the token, then run: bash medscope/scripts/runpod.sh)
set -euo pipefail
cd "${MEDSCOPE_STORE:-/workspace}"

if [ ! -d medscope ]; then
  git clone "https://git:${GITHUB_TOKEN}@github.com/bhaskargurram-ai/medscope" medscope
fi
cd medscope
git fetch --quiet origin main && git reset --quiet --hard origin/main
echo "code version: $(git log --oneline -1)"

if [ ! -f /workspace/.medscope_deps ]; then
  pip install -q -U pip
  pip install -q -U "transformers>=5.20" accelerate peft bitsandbytes huggingface_hub safetensors \
      opencv-python-headless pyyaml pillow numpy
  pip uninstall -q -y torchao || true
  python - <<'PY'
import torch
print("torch", torch.__version__, "GPU:", torch.cuda.get_device_name(0))
PY
  if python -c "import torch,sys; sys.exit(0 if torch.cuda.get_device_capability()[0] >= 8 else 1)"; then
    pip install -q flash-linear-attention || echo "flash-linear-attention unavailable; using the slower reference code"
    python -c "import fla" 2>/dev/null || pip uninstall -q -y flash-linear-attention fla-core || true
  fi
  pip install -q -e . --no-deps
  touch /workspace/.medscope_deps
fi

huggingface-cli login --token "$HF_TOKEN" >/dev/null 2>&1 || python -c "from huggingface_hub import login; import os; login(os.environ['HF_TOKEN'])"
python scripts/pipeline.py "$@" 2>&1 | tee -a /workspace/pipeline.log
