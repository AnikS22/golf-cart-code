#!/usr/bin/env python3
"""
Smoke test: does Comma's supercombo model actually RUN on this Mac?
Executes driving_supercombo.onnx with correctly-shaped inputs via onnxruntime and
reports the output. Proves the model half of the loop works locally (no NVIDIA).
"""
import numpy as np
import onnxruntime as ort
from pathlib import Path

MODEL = Path(__file__).resolve().parent.parent / "models" / "driving_supercombo.onnx"

sess = ort.InferenceSession(str(MODEL), providers=["CPUExecutionProvider"])
print("providers:", sess.get_providers())

# Build zero inputs matching the model's declared shapes/dtypes.
feeds = {}
for i in sess.get_inputs():
    shape = [d if isinstance(d, int) and d > 0 else 1 for d in i.shape]
    if "uint8" in i.type:
        dtype = np.uint8
    elif "float16" in i.type:
        dtype = np.float16
    else:
        dtype = np.float32
    feeds[i.name] = np.zeros(shape, dtype=dtype)
    print(f"  input {i.name:18s} {shape} {dtype.__name__}")

out = sess.run(None, feeds)
o = out[0]
print(f"\nOUTPUT shape={o.shape} dtype={o.dtype}  finite={np.isfinite(o).all()}")
print(f"first 8 values: {np.asarray(o).ravel()[:8]}")
print("MODEL_RUNS_ON_MAC=SUCCESS")
