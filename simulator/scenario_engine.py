"""Registro en memoria de los escenarios de incidente activos.

Soporta composición (varias instancias activas a la vez, en distintos
alcances y sobre distintas entidades), rampas suaves de entrada/salida
(en vez de saltos instantáneos) y auto-expiración por duración.

`AP_DOWN` es la excepción: es binario (el AP está caído o no lo está),
sin rampa -- así se comporta una falla de hardware real.
"""

import time
import uuid
from dataclasses import dataclass

from scenario_defs import AP_DOWN, METRIC_SEVERITY, SCENARIOS, Range

RAMP_SECONDS = 30.0


@dataclass
class ScenarioInstance:
    id: str
    scenario: str
    scope: str  # "site" | "ap"
    target: str  # nombre de sede, o "sede/ap_id" para scope="ap"
    started_at: float
    duration_s: float | None
    magnitude: float
    ending_at: float | None = None

    def progress(self, now: float) -> float:
        """Severidad efectiva en [0, magnitude], aplicando rampa de entrada y salida."""
        ramp_in = min(1.0, (now - self.started_at) / RAMP_SECONDS)
        if self.ending_at is not None:
            ramp_out = min(1.0, (now - self.ending_at) / RAMP_SECONDS)
            return max(0.0, ramp_in * (1.0 - ramp_out) * self.magnitude)
        return ramp_in * self.magnitude

    def is_finished(self, now: float) -> bool:
        return self.ending_at is not None and (now - self.ending_at) >= RAMP_SECONDS


def _combine(current: Range | None, candidate: Range, severity: str) -> Range:
    if current is None:
        return candidate
    pick = max if severity == "high" else min
    return (pick(current[0], candidate[0]), pick(current[1], candidate[1]))


class ScenarioRegistry:
    def __init__(self) -> None:
        self._instances: dict[str, ScenarioInstance] = {}

    def create(
        self, scenario: str, scope: str, target: str, duration_s: float | None, magnitude: float
    ) -> ScenarioInstance:
        instance = ScenarioInstance(
            id=uuid.uuid4().hex[:12],
            scenario=scenario,
            scope=scope,
            target=target,
            started_at=time.monotonic(),
            duration_s=duration_s,
            magnitude=magnitude,
        )
        self._instances[instance.id] = instance
        return instance

    def stop(self, instance_id: str) -> bool:
        instance = self._instances.get(instance_id)
        if instance is None or instance.ending_at is not None:
            return False
        instance.ending_at = time.monotonic()
        return True

    def list_active(self) -> list[ScenarioInstance]:
        return list(self._instances.values())

    def sweep(self) -> None:
        """Expira instancias vencidas por duración y purga las que ya terminaron su rampa de salida."""
        now = time.monotonic()
        for instance in list(self._instances.values()):
            if instance.ending_at is None and instance.duration_s is not None:
                if (now - instance.started_at) >= instance.duration_s:
                    instance.ending_at = now
            if instance.is_finished(now):
                del self._instances[instance.id]

    def _matching(self, scope: str, target: str) -> list[ScenarioInstance]:
        return [i for i in self._instances.values() if i.scope == scope and i.target == target]

    def ap_is_down(self, site: str, ap_id: str) -> bool:
        return any(
            i.scenario == AP_DOWN and i.ending_at is None
            for i in self._matching("ap", f"{site}/{ap_id}")
        )

    def resolve_ap_ranges(self, site: str, ap_id: str) -> dict[str, Range]:
        now = time.monotonic()
        candidates = self._matching("site", site) + self._matching("ap", f"{site}/{ap_id}")
        ranges: dict[str, Range] = {}
        for instance in candidates:
            if instance.scenario == AP_DOWN:
                continue
            m = instance.progress(now)
            if m <= 0:
                continue
            for key, candidate_range in SCENARIOS[instance.scenario].ranges(m).items():
                ranges[key] = _combine(ranges.get(key), candidate_range, METRIC_SEVERITY[key])
        return ranges

    def resolve_site_wan_ranges(self, site: str) -> dict[str, Range]:
        now = time.monotonic()
        ranges: dict[str, Range] = {}
        for instance in self._matching("site", site):
            m = instance.progress(now)
            if m <= 0:
                continue
            for key, candidate_range in SCENARIOS[instance.scenario].ranges(m).items():
                if key not in ("wan_latency_ms", "wan_loss_ratio"):
                    continue
                ranges[key] = _combine(ranges.get(key), candidate_range, METRIC_SEVERITY[key])
        return ranges

    def active_scenario_labels(self) -> set[tuple[str, str, str]]:
        """(scope, target, scenario) de instancias con efecto visible, para anotaciones en Grafana."""
        now = time.monotonic()
        return {
            (i.scope, i.target, i.scenario)
            for i in self._instances.values()
            if i.scenario == AP_DOWN or i.progress(now) > 0
        }


registry = ScenarioRegistry()
