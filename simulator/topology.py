from dataclasses import dataclass
from pathlib import Path

import yaml

TOPOLOGY_PATH = Path(__file__).parent / "config" / "topology.yaml"


@dataclass(frozen=True)
class AccessPoint:
    site: str
    ap_id: str


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def load_access_points(path: Path = TOPOLOGY_PATH) -> list[AccessPoint]:
    data = _load(path)
    return [
        AccessPoint(site=site["name"], ap_id=ap["id"])
        for site in data["sites"]
        for ap in site["aps"]
    ]


def load_site_names(path: Path = TOPOLOGY_PATH) -> list[str]:
    data = _load(path)
    return [site["name"] for site in data["sites"]]
