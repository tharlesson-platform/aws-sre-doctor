from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DiagnosisContext:
    environment: str
    workload_name: str
    workload_type: str
    metadata: dict[str, Any] = field(default_factory=dict)
