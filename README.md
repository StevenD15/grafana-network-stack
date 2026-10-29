# grafana-network-stack

Laboratorio local de observabilidad de una red WiFi empresarial simulada (multi-sede, Access Points y clientes), con inyección controlada de incidentes (interferencia RF, saturación, degradación de WAN, fallos de autenticación, caída de APs, etc.).

Backend simulador de red WiFi + stack de observabilidad (Prometheus + Grafana), 100% local vía Docker Compose. Sin infraestructura real, sin servicios cloud, sin APIs externas.

## Estado actual: Fase 8 — Documentación

La topología (sedes y APs) se declara en `simulator/config/topology.yaml` y se carga en `topology.py`. `metrics.py` define el set completo de métricas y el perfil **NORMAL** (rangos base sin incidentes). `scenario_defs.py` cataloga los escenarios de incidente y `scenario_engine.py` es el registro que los activa/expira con rampas y composición — ver más abajo.

Topología por defecto: 3 sedes (`bogota`, `medellin`, `cali`), 6 APs en total. Editable sin tocar código.

Métricas expuestas:

- `network_ap_up`, `network_ap_clients_connected`
- `network_ap_channel_utilization_ratio`, `network_ap_rssi_dbm_avg`, `network_ap_snr_db_avg`
- `network_ap_frames_total`, `network_ap_retries_total`
- `network_ap_packets_total`, `network_ap_packets_lost_total`
- `network_ap_throughput_mbps{direction}`
- `network_client_latency_seconds` (histogram)
- `network_auth_attempts_total{result}`
- `network_wan_latency_ms`, `network_wan_packet_loss_ratio` (por sede)

## Dashboards

Provisionados automáticamente en la carpeta "Network Stack" de Grafana:

- **Network Overview** — estado global: APs up/down, clientes conectados, latencia/packet loss/throughput agregados, disponibilidad de APs en el tiempo. Variable `$site`.
- **WiFi RF Health** — detalle por AP: RSSI, SNR, channel utilization, retries, clientes por AP, ranking de peor channel utilization. Variables `$site` → `$ap` (encadenadas).
- **Client Experience** — latencia (p50/p90/p99), packet loss WiFi, throughput, fallos de autenticación, y **latencia/packet loss del uplink WAN por sede** (para poder distinguir si un problema percibido por el usuario es del WiFi o de Internet). Variables `$site` → `$ap`.
- **Incident Analysis** — dashboard de "war room": cuenta de incidentes activos, un panel **State timeline** que muestra qué escenario estuvo activo por entidad a lo largo del tiempo, y todas las métricas clave con anotaciones automáticas (líneas verticales) marcando cuándo empezó/terminó cada incidente, tomadas de `network_scenario_active_info`. Variables `$site` → `$ap`.

## Motor de escenarios (control de incidentes)

Cada escenario se puede disparar sobre una sede (`scope=site`) o un AP puntual (`scope=ap`, `target="sede/ap_id"`), y varios pueden estar activos a la vez sobre distintas entidades (composición). Al activarse, hace una rampa de entrada de 30s (menos `ap_down`, que es binario); al detenerse, rampa de salida de otros 30s antes de desaparecer del todo.

```bash
# Catálogo de escenarios disponibles
curl http://localhost:8000/scenarios/catalog

# Disparar high_density en toda la sede bogota
curl -X POST http://localhost:8000/scenarios \
  -H "Content-Type: application/json" \
  -d '{"scenario":"high_density","scope":"site","target":"bogota"}'

# Disparar rf_interference solo en un AP, por 10 minutos, y que se revierta solo
curl -X POST http://localhost:8000/scenarios \
  -H "Content-Type: application/json" \
  -d '{"scenario":"rf_interference","scope":"ap","target":"medellin/ap-01","duration_s":600}'

# Ver escenarios activos y su progreso de rampa
curl http://localhost:8000/scenarios

# Detener un escenario manualmente (inicia su rampa de salida)
curl -X DELETE http://localhost:8000/scenarios/<id>
```

Escenarios disponibles: `high_density` (sede), `ap_overload` (AP), `rf_interference` (AP), `poor_signal` (AP), `wan_degradation` (sede), `authentication_failure` (sede o AP), `ap_down` (AP, sin rampa).

## Alertas

Provisionadas como código en `grafana/provisioning/alerting/rules.yaml`, usando el motor de alerting nativo de Grafana (no se usa Alertmanager como contenedor aparte). Cada regla es multi-dimensional: una sola definición evalúa todas las combinaciones `site`/`ap_id` que devuelva la query, sin duplicar reglas por entidad.

| Regla | Condición | `for` | Severidad |
|---|---|---|---|
| `APDown` | `network_ap_up < 1` | 2m | critical |
| `HighChannelUtilization` | `channel_utilization_ratio > 0.85` | 5m | warning |
| `HighRetriesRatio` | `retries/frames > 0.20` (rate 5m) | 5m | warning |
| `HighLatencyP90Warning` | p90 latencia > 100ms | 5m | warning |
| `HighLatencyP90Critical` | p90 latencia > 300ms | 5m | critical |
| `HighPacketLoss` | packet loss WiFi > 5% | 5m | warning |
| `AuthFailureSpike` | fallos de auth > 30% | 5m | warning |

No se configuró ningún contact point propio: las reglas usan la política de notificación por defecto de Grafana (contact point `grafana-default-email`), que sin SMTP configurado no llega a enviar el correo pero sí deja ver el ciclo de vida completo de la alerta (Pending → Firing → Resolved) en la UI de Alerting — que es el objetivo de este laboratorio. Si más adelante se quiere ver una notificación real sin depender de infraestructura externa, un contenedor local de Mailhog sería la forma más simple de agregarlo.

## Requisitos

- Docker y Docker Compose

## Uso

```bash
docker compose up -d --build
```

- Simulador: http://localhost:8000/metrics
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (usuario `admin`, contraseña `admin`)

Para detener:

```bash
docker compose down
```

## Estructura del repositorio

```
grafana-network-stack/
├── docker-compose.yml
├── simulator/
│   ├── app.py              # FastAPI: /metrics, API de control de escenarios, tick loop
│   ├── topology.py         # carga sedes/APs desde config/topology.yaml
│   ├── metrics.py           # métricas Prometheus + perfil NORMAL + AP_DOWN (staleness)
│   ├── scenario_defs.py     # catálogo de escenarios (rangos objetivo por magnitud)
│   ├── scenario_engine.py   # registro de escenarios activos: rampas, composición, expiración
│   ├── config/topology.yaml # sedes y APs, editable sin tocar código
│   ├── requirements.txt
│   └── Dockerfile
├── prometheus/
│   └── prometheus.yml
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/prometheus.yaml
│   │   ├── dashboards/dashboards.yaml
│   │   └── alerting/rules.yaml
│   └── dashboards/           # los 4 dashboards, como JSON versionado
│       ├── network-overview.json
│       ├── wifi-rf-health.json
│       ├── client-experience.json
│       └── incident-analysis.json
├── docs/
│   ├── architecture.md      # decisiones de arquitectura y por qué
│   └── scenarios.md         # catálogo de escenarios, rangos, ejemplos de la API
└── README.md
```

## Documentación

- **[`docs/architecture.md`](docs/architecture.md)** — objetivo funcional, componentes, flujo de datos, decisiones de diseño (por qué esta arquitectura y no otra) y convenciones de métricas.
- **[`docs/scenarios.md`](docs/scenarios.md)** — catálogo completo de escenarios con sus rangos objetivo, ejemplos de la API de control, y qué esperar ver en cada dashboard durante cada incidente.
- **[`postman/grafana-network-stack.postman_collection.json`](postman/grafana-network-stack.postman_collection.json)** — colección de Postman lista para importar, con 4 carpetas: simulador, Prometheus (para entender por qué hace falta), incidentes (uno por escenario, cada uno con su explicación en el campo "description"), y cómo detenerlos.
- **[`docs/ejercicio-clase.md`](docs/ejercicio-clase.md)** — instructivo para compañeros de curso: levantar el stack y agregar un panel nuevo en Grafana (métrica y pasos ya definidos, igual para todos).

## Roadmap

1. ✅ Infraestructura local (Docker Compose, Prometheus, Grafana)
2. ✅ Simulador mínimo (FastAPI + `/metrics`)
3. ✅ Modelo de red (sedes, APs, clientes)
4. ✅ Dashboards base
5. ✅ Motor de escenarios de incidentes
6. ✅ Dashboards de incidentes
7. ✅ Alertas
8. ✅ Documentación

Pendiente (fuera del alcance de este repo por ahora): publicación en GitHub.
