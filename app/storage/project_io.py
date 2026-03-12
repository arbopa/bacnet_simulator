from __future__ import annotations

import json
from pathlib import Path

from app.models.project_model import ProjectModel

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


def load_project(path: str | Path) -> ProjectModel:
    project_path = Path(path)
    text = project_path.read_text(encoding="utf-8")
    if yaml is not None:
        raw = yaml.safe_load(text) or {}
    else:
        raw = json.loads(text)
    return ProjectModel.from_dict(raw)


def save_project(project: ProjectModel, path: str | Path) -> None:
    project_path = Path(path)
    project_path.parent.mkdir(parents=True, exist_ok=True)
    data = project.to_dict()
    if yaml is not None:
        payload = yaml.safe_dump(data, sort_keys=False, allow_unicode=False)
    else:
        payload = json.dumps(data, indent=2)
    project_path.write_text(payload, encoding="utf-8")
