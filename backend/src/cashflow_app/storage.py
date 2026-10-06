"""Scenario persistence.

Saved scenarios bind to a dataset version and a business. Two adapters exist:
in-memory (tests) and a local JSON file written atomically (demo). A DynamoDB
adapter is a later milestone and is not implemented here.
"""

import json
import os
import secrets
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .config import STORAGE_LOCAL, STORAGE_MEMORY, AppConfig


@dataclass(frozen=True)
class SavedScenario:
    scenario_id: str
    business_id: str
    dataset_version: str
    invoice_id: str
    delay_days: int
    name: str
    created_at: str

    def as_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "business_id": self.business_id,
            "dataset_version": self.dataset_version,
            "invoice_id": self.invoice_id,
            "delay_days": self.delay_days,
            "name": self.name,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SavedScenario":
        return cls(
            scenario_id=str(data["scenario_id"]),
            business_id=str(data["business_id"]),
            dataset_version=str(data["dataset_version"]),
            invoice_id=str(data["invoice_id"]),
            delay_days=int(data["delay_days"]),
            name=str(data.get("name") or ""),
            created_at=str(data["created_at"]),
        )


def new_scenario_id() -> str:
    """Opaque generated identifier (docs/DATA_MODEL.md)."""
    return "scn_" + secrets.token_urlsafe(9)


class ScenarioStore(Protocol):
    backend: str

    def save(self, scenario: SavedScenario) -> None: ...
    def get(self, business_id: str, scenario_id: str) -> SavedScenario | None: ...
    def list(self, business_id: str) -> list[SavedScenario]: ...
    def delete(self, business_id: str, scenario_id: str) -> bool: ...
    def clear(self, business_id: str) -> int: ...


class InMemoryScenarioStore:
    backend = STORAGE_MEMORY

    def __init__(self) -> None:
        self._items: dict[tuple[str, str], SavedScenario] = {}

    def save(self, scenario: SavedScenario) -> None:
        self._items[(scenario.business_id, scenario.scenario_id)] = scenario

    def get(self, business_id: str, scenario_id: str) -> SavedScenario | None:
        return self._items.get((business_id, scenario_id))

    def list(self, business_id: str) -> list[SavedScenario]:
        return sorted(
            (s for (b, _), s in self._items.items() if b == business_id),
            key=lambda s: (s.created_at, s.scenario_id),
        )

    def delete(self, business_id: str, scenario_id: str) -> bool:
        return self._items.pop((business_id, scenario_id), None) is not None

    def clear(self, business_id: str) -> int:
        keys = [k for k in self._items if k[0] == business_id]
        for k in keys:
            del self._items[k]
        return len(keys)


class LocalJsonScenarioStore:
    """One JSON file; every write replaces the file atomically."""

    backend = STORAGE_LOCAL

    def __init__(self, path: Path) -> None:
        self.path = path
        self._memory = InMemoryScenarioStore()
        self._load()

    def _load(self) -> None:
        if not self.path.is_file():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise RuntimeError(f"scenario store {self.path} is not valid JSON") from None
        for item in data.get("scenarios", []):
            self._memory.save(SavedScenario.from_dict(item))

    def _flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "format": "cashflow-scenarios/1",
            "scenarios": [s.as_dict() for s in self._memory._items.values()],
        }
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".scenarios-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
            os.replace(tmp, self.path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    def save(self, scenario: SavedScenario) -> None:
        self._memory.save(scenario)
        self._flush()

    def get(self, business_id: str, scenario_id: str) -> SavedScenario | None:
        return self._memory.get(business_id, scenario_id)

    def list(self, business_id: str) -> list[SavedScenario]:
        return self._memory.list(business_id)

    def delete(self, business_id: str, scenario_id: str) -> bool:
        removed = self._memory.delete(business_id, scenario_id)
        if removed:
            self._flush()
        return removed

    def clear(self, business_id: str) -> int:
        count = self._memory.clear(business_id)
        self._flush()
        return count


def build_scenario_store(config: AppConfig) -> ScenarioStore:
    if config.storage_backend == STORAGE_MEMORY:
        return InMemoryScenarioStore()
    return LocalJsonScenarioStore(config.data_dir / "scenarios.json")
