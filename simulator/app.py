import asyncio
import time
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel, Field

import metrics
from scenario_defs import AP_DOWN, SCENARIOS
from scenario_engine import registry
from topology import load_access_points, load_site_names

UPDATE_INTERVAL_SECONDS = 5

ACCESS_POINTS = load_access_points()
SITES = load_site_names()

_previous_scenario_labels: set[tuple[str, str, str]] = set()


def _sync_scenario_info_metric() -> None:
    global _previous_scenario_labels
    current = registry.active_scenario_labels()
    for labels in current - _previous_scenario_labels:
        metrics.scenario_active_info.labels(*labels).set(1)
    for labels in _previous_scenario_labels - current:
        try:
            metrics.scenario_active_info.remove(*labels)
        except KeyError:
            pass
    _previous_scenario_labels = current


def tick() -> None:
    registry.sweep()

    for ap in ACCESS_POINTS:
        if registry.ap_is_down(ap.site, ap.ap_id):
            metrics.mark_ap_down(ap)
        else:
            ranges = registry.resolve_ap_ranges(ap.site, ap.ap_id)
            metrics.apply_tick(ap, ranges)

    for site in SITES:
        wan_ranges = registry.resolve_site_wan_ranges(site)
        metrics.apply_wan_tick(site, wan_ranges)

    _sync_scenario_info_metric()


async def update_loop() -> None:
    while True:
        tick()
        await asyncio.sleep(UPDATE_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    tick()  # valores disponibles desde el primer scrape, sin esperar el primer tick
    task = asyncio.create_task(update_loop())
    yield
    task.cancel()


app = FastAPI(title="grafana-network-stack simulator", lifespan=lifespan)


def _validate_target(scope: str, target: str) -> None:
    if scope == "site":
        if target not in SITES:
            raise HTTPException(status_code=400, detail=f"sede desconocida: {target!r}")
    elif scope == "ap":
        if "/" not in target:
            raise HTTPException(
                status_code=400, detail="target de scope='ap' debe tener forma 'sede/ap_id'"
            )
        site, ap_id = target.split("/", 1)
        if not any(ap.site == site and ap.ap_id == ap_id for ap in ACCESS_POINTS):
            raise HTTPException(status_code=400, detail=f"AP desconocido: {target!r}")
    else:
        raise HTTPException(status_code=400, detail="scope debe ser 'site' o 'ap'")


class ScenarioRequest(BaseModel):
    scenario: str
    scope: str
    target: str
    duration_s: float | None = Field(default=None, gt=0)
    magnitude: float = Field(default=1.0, ge=0.0, le=1.0)


@app.get("/")
def root():
    return {
        "status": "ok",
        "sites": SITES,
        "access_points": [asdict(ap) for ap in ACCESS_POINTS],
    }


@app.get("/metrics")
def metrics_endpoint():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/scenarios/catalog")
def scenario_catalog():
    catalog = {
        name: {"scopes": sorted(defn.scopes), "description": defn.description}
        for name, defn in SCENARIOS.items()
    }
    catalog[AP_DOWN] = {
        "scopes": ["ap"],
        "description": "El AP deja de reportar telemetría (up=0; el resto de sus "
        "métricas desaparece del scrape, sin rampa: es binario).",
    }
    return catalog


@app.post("/scenarios")
def create_scenario(req: ScenarioRequest):
    scenario_name = req.scenario.lower()
    if scenario_name == AP_DOWN:
        allowed_scopes = {"ap"}
    elif scenario_name in SCENARIOS:
        allowed_scopes = SCENARIOS[scenario_name].scopes
    else:
        raise HTTPException(status_code=400, detail=f"escenario desconocido: {req.scenario!r}")

    if req.scope not in allowed_scopes:
        raise HTTPException(
            status_code=400,
            detail=f"scope inválido para {scenario_name!r}: admite {sorted(allowed_scopes)}",
        )

    _validate_target(req.scope, req.target)

    instance = registry.create(scenario_name, req.scope, req.target, req.duration_s, req.magnitude)
    return {
        "id": instance.id,
        "scenario": instance.scenario,
        "scope": instance.scope,
        "target": instance.target,
        "duration_s": instance.duration_s,
        "magnitude": instance.magnitude,
    }


@app.get("/scenarios")
def list_scenarios():
    now = time.monotonic()
    return [
        {
            "id": i.id,
            "scenario": i.scenario,
            "scope": i.scope,
            "target": i.target,
            "magnitude": i.magnitude,
            "progress": round(i.progress(now), 3),
            "ending": i.ending_at is not None,
            "duration_s": i.duration_s,
        }
        for i in registry.list_active()
    ]


@app.delete("/scenarios/{scenario_id}")
def stop_scenario(scenario_id: str):
    if not registry.stop(scenario_id):
        raise HTTPException(status_code=404, detail="id no encontrado o ya en rampa de apagado")
    return {"status": "ending"}
