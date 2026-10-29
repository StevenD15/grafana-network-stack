"""Catálogo de escenarios de incidente.

Cada escenario declara: en qué alcances (`scopes`) se puede invocar
(`site` o `ap`), y una función `ranges(m)` que devuelve, para magnitud
`m` en [0, 1], los rangos de valores hacia los que se desplazan las
métricas que afecta -- partiendo siempre del rango NORMAL definido en
`metrics.py`.

`AP_DOWN` es un caso aparte: no participa del sistema de rangos (no
tiene sentido "interpolar" un AP hacia estar caído), lo maneja
directamente `scenario_engine.py`.

`METRIC_SEVERITY` indica, por métrica, si "peor" es un valor más alto
o más bajo. Se usa para combinar varios escenarios activos sobre la
misma entidad sin que sus efectos se sumen sin límite: en vez de sumar,
nos quedamos con el rango más severo por métrica.
"""

from dataclasses import dataclass
from typing import Callable

import metrics

Range = tuple[float, float]

AP_DOWN = "ap_down"

METRIC_SEVERITY: dict[str, str] = {
    "clients": "high",
    "channel_utilization": "high",
    "retries_ratio": "high",
    "packet_loss_ratio": "high",
    "latency_ms": "high",
    "throughput_multiplier": "low",
    "rssi_dbm": "low",
    "snr_db": "low",
    "wan_latency_ms": "high",
    "wan_loss_ratio": "high",
    "auth_failure_rate": "high",
}


def lerp_range(base: Range, target: Range, m: float) -> Range:
    m = max(0.0, min(1.0, m))
    return (
        base[0] + (target[0] - base[0]) * m,
        base[1] + (target[1] - base[1]) * m,
    )


@dataclass(frozen=True)
class ScenarioDef:
    name: str
    scopes: frozenset[str]
    ranges: Callable[[float], dict[str, Range]]
    description: str


def _high_density_ranges(m: float) -> dict[str, Range]:
    return {
        "clients": lerp_range(metrics.NORMAL_CLIENTS, (70, 100), m),
        "channel_utilization": lerp_range(metrics.NORMAL_CHANNEL_UTILIZATION, (0.75, 0.95), m),
        "retries_ratio": lerp_range(metrics.NORMAL_RETRIES_RATIO, (0.15, 0.30), m),
        "packet_loss_ratio": lerp_range(metrics.NORMAL_PACKET_LOSS_RATIO, (0.02, 0.05), m),
        "latency_ms": lerp_range(metrics.NORMAL_LATENCY_MS, (40, 100), m),
        "throughput_multiplier": lerp_range((1.0, 1.0), (0.3, 0.5), m),
    }


def _rf_interference_ranges(m: float) -> dict[str, Range]:
    return {
        "channel_utilization": lerp_range(metrics.NORMAL_CHANNEL_UTILIZATION, (0.75, 0.95), m),
        "retries_ratio": lerp_range(metrics.NORMAL_RETRIES_RATIO, (0.20, 0.40), m),
    }


def _poor_signal_ranges(m: float) -> dict[str, Range]:
    return {
        "rssi_dbm": lerp_range(metrics.NORMAL_RSSI_DBM, (-90, -75), m),
        "snr_db": lerp_range(metrics.NORMAL_SNR_DB, (5, 15), m),
        "packet_loss_ratio": lerp_range(metrics.NORMAL_PACKET_LOSS_RATIO, (0.03, 0.07), m),
        "latency_ms": lerp_range(metrics.NORMAL_LATENCY_MS, (50, 120), m),
        "throughput_multiplier": lerp_range((1.0, 1.0), (0.4, 0.6), m),
    }


def _wan_degradation_ranges(m: float) -> dict[str, Range]:
    return {
        "wan_latency_ms": lerp_range(metrics.NORMAL_WAN_LATENCY_MS, (150, 300), m),
        "wan_loss_ratio": lerp_range(metrics.NORMAL_WAN_LOSS_RATIO, (0.05, 0.15), m),
    }


def _authentication_failure_ranges(m: float) -> dict[str, Range]:
    return {
        "auth_failure_rate": lerp_range(metrics.NORMAL_AUTH_FAILURE_RATE, (0.3, 0.6), m),
    }


SCENARIOS: dict[str, ScenarioDef] = {
    "high_density": ScenarioDef(
        name="high_density",
        scopes=frozenset({"site"}),
        ranges=_high_density_ranges,
        description="Crecimiento orgánico de clientes en toda una sede: satura canal, "
        "sube retries/latencia, baja throughput.",
    ),
    "ap_overload": ScenarioDef(
        name="ap_overload",
        scopes=frozenset({"ap"}),
        ranges=_high_density_ranges,
        description="Carga desbalanceada en un AP puntual (mismos síntomas que "
        "high_density, acotados a un solo AP).",
    ),
    "rf_interference": ScenarioDef(
        name="rf_interference",
        scopes=frozenset({"ap"}),
        ranges=_rf_interference_ranges,
        description="Interferencia RF en un AP: sube retries y channel utilization; "
        "RSSI/SNR no cambian.",
    ),
    "poor_signal": ScenarioDef(
        name="poor_signal",
        scopes=frozenset({"ap"}),
        ranges=_poor_signal_ranges,
        description="Degradación del RSSI/SNR promedio del AP (aproxima un subconjunto "
        "de clientes con mala señal, ya que las métricas se agregan por AP).",
    ),
    "wan_degradation": ScenarioDef(
        name="wan_degradation",
        scopes=frozenset({"site"}),
        ranges=_wan_degradation_ranges,
        description="El uplink a Internet de la sede se degrada; el WiFi en sí "
        "funciona normal (RF y capacidad no cambian).",
    ),
    "authentication_failure": ScenarioDef(
        name="authentication_failure",
        scopes=frozenset({"site", "ap"}),
        ranges=_authentication_failure_ranges,
        description="Aumentan los fallos de autenticación de clientes.",
    ),
}
