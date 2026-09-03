from pathlib import Path
from time import perf_counter

from app.services.decision import DefectResult


class InferenceProvider:
    model_version = "base"

    def infer(self, image_path: Path) -> list[DefectResult]:
        raise NotImplementedError


class MockInferenceProvider(InferenceProvider):
    model_version = "mock-v1"

    def __init__(self, model_version: str = "mock-v1") -> None:
        self.model_version = model_version

    def infer(self, image_path: Path) -> list[DefectResult]:
        # Deterministic demo behavior: filenames containing "ng" produce one severe scratch.
        if "ng" in image_path.stem.lower() or sum(image_path.stat().st_size.to_bytes(8, "little")) % 5 == 0:
            return [DefectResult("scratch", "severe", 0.98, [0.2, 0.2, 0.4, 0.35], 2.0, 1.0)]
        return []


def run_inference(provider: InferenceProvider, image_path: Path) -> tuple[list[DefectResult], float]:
    started = perf_counter()
    defects = provider.infer(image_path)
    return defects, round((perf_counter() - started) * 1000, 3)


class ModelRuntimeAdapter:
    """Hot-switch seam for the future ONNX/PyTorch runtime; mock is intentionally in-process."""

    def __init__(self) -> None:
        self.active_model_version = "mock-v1"
        self.active_config_version: str | None = None

    async def hot_switch(self, model_config: dict, config_version: str) -> None:
        self.active_model_version = str(model_config["model_version"])
        self.active_config_version = config_version

    def provider(self) -> InferenceProvider:
        return MockInferenceProvider(self.active_model_version)


model_runtime = ModelRuntimeAdapter()
