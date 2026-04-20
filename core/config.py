from __future__ import annotations

from pathlib import Path

import yaml


def load_environment_config(environment: str) -> dict:
    base_dir = Path(__file__).resolve().parent.parent / "config" / "environments"
    target = base_dir / f"{environment}.yaml"
    if not target.exists():
        raise FileNotFoundError(f"Configuration not found for environment: {environment}")
    return yaml.safe_load(target.read_text(encoding="utf-8"))
