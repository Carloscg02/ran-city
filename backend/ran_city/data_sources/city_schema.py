"""Declarative city configuration schema and YAML loader/serializer for RAN-city."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from ran_city.domain.grid import EnvironmentType
from ran_city.domain.models import Site


class CityZoneSpec(BaseModel):
    """Specification of a planning environment zone in the city."""

    model_config = ConfigDict(frozen=True)

    zone_id: str
    name: str
    environment: EnvironmentType
    description: str = ""


class OperatorSpectrumSpec(BaseModel):
    """CNAF spectrum allocation assigned to an active network operator alias."""

    model_config = ConfigDict(frozen=True)

    network_alias: str
    mcc: int = 214
    mnc: int
    cnaf_blocks: list[str] = Field(default_factory=lambda: ["n28", "n78"])


class CityConfig(BaseModel):
    """City geographic metadata, bounding boxes, zones, and operator configurations."""

    model_config = ConfigDict(frozen=True)

    city_id: str
    city_name: str
    bbox_wgs84: tuple[float, float, float, float]  # min_lon, min_lat, max_lon, max_lat
    bbox_utm30: tuple[float, float, float, float]  # min_x, min_y, max_x, max_y
    zones: list[CityZoneSpec]
    operators: list[OperatorSpectrumSpec]


class CityScenario(BaseModel):
    """Complete, self-contained multi-operator city scenario for simulation."""

    model_config = ConfigDict(frozen=True)

    config: CityConfig
    sites: list[Site]


def load_city_scenario(yaml_path: str | Path) -> CityScenario:
    """Load a CityScenario from a declarative YAML file.

    Args:
        yaml_path: Path to the .yaml scenario file.

    Returns:
        Instantiated and validated CityScenario.
    """
    path = Path(yaml_path)
    if not path.is_file():
        raise FileNotFoundError(f"Scenario YAML file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise TypeError(f"Invalid YAML content in {path}: expected dict mapping")

    config = CityConfig.model_validate(data["config"])
    sites = [Site.model_validate(site_data) for site_data in data.get("sites", [])]

    return CityScenario(config=config, sites=sites)


def save_city_scenario(scenario: CityScenario, yaml_path: str | Path) -> None:
    """Save a CityScenario to a YAML file.

    Args:
        scenario: CityScenario instance to persist.
        yaml_path: Target path for the YAML file.
    """
    path = Path(yaml_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    raw_data = scenario.model_dump(mode="json")
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(raw_data, f, sort_keys=False, allow_unicode=True)
