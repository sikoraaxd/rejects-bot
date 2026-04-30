import json
from pathlib import Path
from typing import Any

from app.core.config import settings


class JsonCache:
    def __init__(self, root: Path = settings.cache_path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def get(self, key: str) -> dict[str, Any] | None:
        path = self._path(key)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def set(self, key: str, payload: dict[str, Any]) -> None:
        self._path(key).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def list_items(self) -> list[dict[str, Any]]:
        return [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(self.root.glob("*.json"), reverse=True)
        ]

    def _path(self, key: str) -> Path:
        safe_key = "".join(char if char.isalnum() or char in "-_" else "_" for char in key)
        return self.root / f"{safe_key}.json"
