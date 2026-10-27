"""depth: Depth Anything V2 Small (ONNX) gives a grayscale depth map per frame."""

from __future__ import annotations

import numpy as np
from PIL import Image

from factory.core import Episode, digest, fresh, mark

PROVIDERS = {
    "onnx-coreml": ["CoreMLExecutionProvider", "CPUExecutionProvider"],
    "onnx-cuda": ["CUDAExecutionProvider", "DmlExecutionProvider", "CPUExecutionProvider"],
    "onnx-cpu": ["CPUExecutionProvider"],
}
MEAN, STD = np.array([0.485, 0.456, 0.406]), np.array([0.229, 0.224, 0.225])


def run(ep: Episode, profile: dict) -> None:
    import onnxruntime as ort

    d = ep.work("frames")
    frames = sorted(d.glob("[0-9][0-9]-916.png"))
    todo = [(f, f.with_name(f.stem + "-depth.png"), digest(f)) for f in frames]
    todo = [t for t in todo if not fresh(t[1], t[2])]
    if todo:
        wanted = PROVIDERS[profile["providers"]["depth"]]
        sess = ort.InferenceSession(
            profile["depth_model"], providers=[p for p in wanted if p in ort.get_available_providers()]
        )
        name = sess.get_inputs()[0].name
        for src, out, key in todo:
            im = Image.open(src).convert("RGB")
            x = (np.asarray(im.resize((518, 518), Image.Resampling.BICUBIC)) / 255.0 - MEAN) / STD
            depth = np.asarray(sess.run(None, {name: x.transpose(2, 0, 1)[None].astype(np.float32)})[0]).squeeze()
            depth = (depth - depth.min()) / (depth.max() - depth.min())
            Image.fromarray((depth * 255).astype(np.uint8)).resize(im.size, Image.Resampling.BICUBIC).save(out)
            mark(out, key)
    print(f"depth: {len(frames) - len(todo)} cached, {len(todo)} made")
