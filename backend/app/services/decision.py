from collections.abc import Iterable
from dataclasses import dataclass

ALLOWED_TYPES = frozenset({"scratch", "pitted_surface"})
ALLOWED_LEVELS = frozenset({"minor", "severe"})
DEFAULT_RULES: dict[tuple[str, str], int] = {
    ("scratch", "severe"): 1,
    ("scratch", "minor"): 5,
    ("pitted_surface", "severe"): 4,
    ("pitted_surface", "minor"): 9,
}


@dataclass(frozen=True)
class DefectResult:
    type: str
    level: str
    confidence: float
    bbox: list[float]
    width_mm: float | None = None
    height_mm: float | None = None


def decide(defects: Iterable[DefectResult], rules: dict[tuple[str, str], int] | None = None) -> str:
    defects = list(defects)
    for defect in defects:
        if defect.type not in ALLOWED_TYPES or defect.level not in ALLOWED_LEVELS:
            raise ValueError("unsupported defect type or level")
    active_rules = rules or DEFAULT_RULES
    counts: dict[tuple[str, str], int] = {}
    for defect in defects:
        key = (defect.type, defect.level)
        counts[key] = counts.get(key, 0) + 1
    if any(counts.get(key, 0) >= limit for key, limit in active_rules.items()):
        return "NG"
    if any(defect.level == "severe" for defect in defects):
        return "NG"
    return "PASS"
