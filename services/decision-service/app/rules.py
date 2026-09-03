"""Standalone decision-service rules shared by the realtime demo."""
from collections.abc import Iterable
from dataclasses import dataclass

RULES = {
    ("scratch", "severe"): 1,
    ("scratch", "minor"): 5,
    ("pitted_surface", "severe"): 4,
    ("pitted_surface", "minor"): 9,
}


@dataclass(frozen=True)
class Defect:
    type: str
    level: str


def decide(defects: Iterable[Defect]) -> str:
    items = list(defects)
    counts = {(kind, level): sum(d.type == kind and d.level == level for d in items) for kind, level in RULES}
    return "NG" if any(counts[key] >= limit for key, limit in RULES.items()) or any(d.level == "severe" for d in items) else "PASS"
