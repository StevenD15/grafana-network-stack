import random

from prometheus_client import Counter, Gauge, Histogram

from topology import AccessPoint

Range = tuple[float, float]

# Rangos del perfil NORMAL. El motor de escenarios (scenario_engine.py)
# parte de estos mismos rangos y los desplaza hacia el objetivo de cada
# escenario activo; por eso viven acá como constantes nombradas y no
# como números mágicos dentro de la función de tick.
NORMAL_CLIENTS: Range = (20, 40)
NORMAL_CHANNEL_UTILIZATION: Range = (0.20, 0.50)
NORMAL_RSSI_DBM: Range = (-60, -45)
NORMAL_SNR_DB: Range = (25, 40)
NORMAL_RETRIES_RATIO: Range = (0.01, 0.05)
NORMAL_PACKET_LOSS_RATIO: Range = (0.001, 0.01)
NORMAL_LATENCY_MS: Range = (10, 30)
NORMAL_THROUGHPUT_DOWN_MBPS: Range = (50, 150)
NORMAL_THROUGHPUT_UP_MBPS: Range = (10, 40)
NORMAL_AUTH_FAILURE_RATE: Range = (0.0, 0.02)
NORMAL_WAN_LATENCY_MS: Range = (10, 30)
NORMAL_WAN_LOSS_RATIO: Range = (0.0, 0.01)
NORMAL_THROUGHPUT_MULTIPLIER: Range = (1.0, 1.0)

# Volumen de tráfico "de fondo" generado por tick, independiente del escenario.
FRAMES_PER_TICK = (500, 2000)
PACKETS_PER_TICK = (2000, 8000)
AUTH_ATTEMPTS_PER_TICK = (1, 5)
LATENCY_SAMPLES_PER_TICK = (3, 8)

# Buckets pensados para cubrir desde NORMAL (~10-30ms) hasta escenarios
# de degradación de WAN (~150-300ms) sin sobredimensionar la cardinalidad.
LATENCY_BUCKETS = (0.005, 0.01, 0.015, 0.02, 0.03, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0)

ap_up = Gauge("network_ap_up", "1 si el AP está reportando, 0 si está caído", ["site", "ap_id"])
ap_clients_connected = Gauge(
    "network_ap_clients_connected", "Clientes WiFi conectados al AP", ["site", "ap_id"]
)
ap_channel_utilization_ratio = Gauge(
    "network_ap_channel_utilization_ratio", "Utilización del canal RF (0-1)", ["site", "ap_id"]
)
ap_rssi_dbm_avg = Gauge(
    "network_ap_rssi_dbm_avg", "RSSI promedio de los clientes del AP (dBm)", ["site", "ap_id"]
)
ap_snr_db_avg = Gauge(
    "network_ap_snr_db_avg", "SNR promedio de los clientes del AP (dB)", ["site", "ap_id"]
)
ap_frames_total = Counter(
    "network_ap_frames_total", "Frames 802.11 transmitidos por el AP", ["site", "ap_id"]
)
ap_retries_total = Counter(
    "network_ap_retries_total", "Frames retransmitidos por el AP", ["site", "ap_id"]
)
ap_packets_total = Counter(
    "network_ap_packets_total", "Paquetes de cliente cursados por el AP", ["site", "ap_id"]
)
ap_packets_lost_total = Counter(
    "network_ap_packets_lost_total", "Paquetes de cliente perdidos", ["site", "ap_id"]
)
ap_throughput_mbps = Gauge(
    "network_ap_throughput_mbps", "Throughput agregado del AP (Mbps)", ["site", "ap_id", "direction"]
)
client_latency_seconds = Histogram(
    "network_client_latency_seconds",
    "Latencia extremo a extremo percibida por los clientes",
    ["site", "ap_id"],
    buckets=LATENCY_BUCKETS,
)
auth_attempts_total = Counter(
    "network_auth_attempts_total", "Intentos de autenticación de clientes", ["site", "ap_id", "result"]
)
wan_latency_ms = Gauge("network_wan_latency_ms", "Latencia del uplink WAN de la sede (ms)", ["site"])
wan_packet_loss_ratio = Gauge(
    "network_wan_packet_loss_ratio", "Pérdida de paquetes del uplink WAN de la sede (0-1)", ["site"]
)
scenario_active_info = Gauge(
    "network_scenario_active_info",
    "1 mientras un escenario de incidente tiene efecto visible sobre la entidad",
    ["scope", "target", "scenario"],
)

_AP_SIMPLE_METRICS = (
    ap_clients_connected,
    ap_channel_utilization_ratio,
    ap_rssi_dbm_avg,
    ap_snr_db_avg,
    ap_frames_total,
    ap_retries_total,
    ap_packets_total,
    ap_packets_lost_total,
    client_latency_seconds,
)


def _safe_remove(metric, label_values: tuple[str, ...]) -> None:
    try:
        metric.remove(*label_values)
    except KeyError:
        pass


def apply_tick(ap: AccessPoint, ranges: dict[str, Range]) -> None:
    """Genera un tick de métricas para un AP a partir de rangos ya resueltos.

    `ranges` trae únicamente las claves que algún escenario activo está
    desplazando; lo que falte cae al rango NORMAL correspondiente. Con
    `ranges={}` el resultado es exactamente el perfil NORMAL.
    """
    labels = (ap.site, ap.ap_id)

    clients_range = ranges.get("clients", NORMAL_CLIENTS)
    channel_range = ranges.get("channel_utilization", NORMAL_CHANNEL_UTILIZATION)
    rssi_range = ranges.get("rssi_dbm", NORMAL_RSSI_DBM)
    snr_range = ranges.get("snr_db", NORMAL_SNR_DB)
    retries_ratio_range = ranges.get("retries_ratio", NORMAL_RETRIES_RATIO)
    packet_loss_range = ranges.get("packet_loss_ratio", NORMAL_PACKET_LOSS_RATIO)
    latency_range_ms = ranges.get("latency_ms", NORMAL_LATENCY_MS)
    throughput_mult_range = ranges.get("throughput_multiplier", NORMAL_THROUGHPUT_MULTIPLIER)
    auth_failure_range = ranges.get("auth_failure_rate", NORMAL_AUTH_FAILURE_RATE)

    ap_up.labels(*labels).set(1)
    ap_clients_connected.labels(*labels).set(round(random.uniform(*clients_range)))
    ap_channel_utilization_ratio.labels(*labels).set(round(random.uniform(*channel_range), 3))
    ap_rssi_dbm_avg.labels(*labels).set(round(random.uniform(*rssi_range), 1))
    ap_snr_db_avg.labels(*labels).set(round(random.uniform(*snr_range), 1))

    frames = random.randint(*FRAMES_PER_TICK)
    retries = int(frames * random.uniform(*retries_ratio_range))
    ap_frames_total.labels(*labels).inc(frames)
    ap_retries_total.labels(*labels).inc(retries)

    packets = random.randint(*PACKETS_PER_TICK)
    lost = int(packets * random.uniform(*packet_loss_range))
    ap_packets_total.labels(*labels).inc(packets)
    ap_packets_lost_total.labels(*labels).inc(lost)

    throughput_mult = random.uniform(*throughput_mult_range)
    ap_throughput_mbps.labels(ap.site, ap.ap_id, "download").set(
        round(random.uniform(*NORMAL_THROUGHPUT_DOWN_MBPS) * throughput_mult, 1)
    )
    ap_throughput_mbps.labels(ap.site, ap.ap_id, "upload").set(
        round(random.uniform(*NORMAL_THROUGHPUT_UP_MBPS) * throughput_mult, 1)
    )

    for _ in range(random.randint(*LATENCY_SAMPLES_PER_TICK)):
        latency_ms = random.uniform(*latency_range_ms)
        client_latency_seconds.labels(*labels).observe(latency_ms / 1000)

    attempts = random.randint(*AUTH_ATTEMPTS_PER_TICK)
    failures = int(attempts * random.uniform(*auth_failure_range))
    successes = attempts - failures
    if successes:
        auth_attempts_total.labels(ap.site, ap.ap_id, "success").inc(successes)
    if failures:
        auth_attempts_total.labels(ap.site, ap.ap_id, "failure").inc(failures)


def apply_wan_tick(site: str, ranges: dict[str, Range]) -> None:
    latency_range = ranges.get("wan_latency_ms", NORMAL_WAN_LATENCY_MS)
    loss_range = ranges.get("wan_loss_ratio", NORMAL_WAN_LOSS_RATIO)
    wan_latency_ms.labels(site).set(round(random.uniform(*latency_range), 1))
    wan_packet_loss_ratio.labels(site).set(round(random.uniform(*loss_range), 4))


def mark_ap_down(ap: AccessPoint) -> None:
    """Simula que el AP dejó de reportar telemetría.

    `network_ap_up` se mantiene en 0 (como lo haría un heartbeat externo
    que sigue viendo al dispositivo, solo que caído), pero el resto de
    métricas del AP se retira del /metrics: al dejar de scrapearse, se
    vuelven "stale" para Prometheus en vez de congelarse en su último
    valor o caer a cero, que es como se comporta un AP real que perdió
    conectividad de gestión.
    """
    labels = (ap.site, ap.ap_id)
    ap_up.labels(*labels).set(0)
    for metric in _AP_SIMPLE_METRICS:
        _safe_remove(metric, labels)
    for direction in ("download", "upload"):
        _safe_remove(ap_throughput_mbps, (*labels, direction))
    for result in ("success", "failure"):
        _safe_remove(auth_attempts_total, (*labels, result))
