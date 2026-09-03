"""Inference provider contracts for replacing the mock with ONNX/PyTorch later."""
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Defect:
    type: str
    level: str
    confidence: float
    bbox: list[float]


class InferenceProvider:
    model_version = "base"

    def infer(self, image_path: Path) -> list[Defect]:
        raise NotImplementedError


class MockInferenceProvider(InferenceProvider):
    model_version = "mock-v1"

    def infer(self, image_path: Path) -> list[Defect]:
        return [Defect("scratch", "severe", 0.98, [0.2, 0.2, 0.4, 0.35])] if "ng" in image_path.stem.lower() else []
