# Arquitectura

## Objetivo funcional

Laboratorio local de observabilidad que simula una red WiFi empresarial multi-sede
(Access Points, clientes, uplink WAN por sede) con inyección controlada de incidentes,
para practicar y demostrar el uso de Grafana/Prometheus sobre un caso de networking
sin depender de infraestructura real, dispositivos físicos ni servicios cloud.

## Componentes

| Componente | Responsabilidad | Implementación |
|---|---|---|
| Simulador (`simulator/`) | Genera métricas correlacionadas, expone `/metrics`, expone la API de control de escenarios | FastAPI + `prometheus_client`, un solo proceso, sin base de datos externa |
| Prometheus | Scrape del simulador, recording implícito vía PromQL en dashboards/alertas, evaluación de alertas | Imagen oficial `prom/prometheus`, un solo target |
| Grafana | Dashboards, variables, alerting nativo, anotaciones | Imagen oficial `grafana/grafana`, todo provisionado como código |
| Docker Compose | Orquestación de los tres servicios en un solo host | `docker-compose.yml` |

## Flujo de datos

```
                 ┌─────────────────────┐
                 │   Simulador Python   │
                 │  (FastAPI)           │
                 │  - /metrics          │
                 │  - /scenarios (API)  │
                 │  - motor de estados  │
                 └──────────┬───────────┘
                             │ scrape (pull, /metrics, cada 15s)
                             v
                 ┌─────────────────────┐
                 │     Prometheus       │
                 │  - scrape config     │
                 │  - alert rules       │
                 └──────────┬───────────┘
                             │ PromQL
                             v
                 ┌─────────────────────┐
                 │       Grafana        │
                 │  - datasource prov.  │
                 │  - dashboards prov.  │
                 │  - unified alerting  │
                 │  - annotations query │
                 └─────────────────────┘
```

1. El simulador mantiene en memoria la topología (`topology.py`, cargada desde
   `simulator/config/topology.yaml`) y el registro de escenarios activos
   (`scenario_engine.py`).
2. Cada 5s (`UPDATE_INTERVAL_SECONDS` en `app.py`) recalcula todas las métricas:
   para cada AP resuelve los rangos vigentes (NORMAL + modificadores de escenarios
   activos) y llama a `metrics.apply_tick(...)`.
3. Prometheus hace scrape de `/metrics` cada 15s.
4. Grafana consulta Prometheus vía PromQL para poblar dashboards y evaluar alertas,
   y consulta `network_scenario_active_info` para pintar anotaciones de inicio/fin
   de incidente.
5. El usuario dispara incidentes con `POST /scenarios` y los ve propagarse por todo
   el pipeline en segundos, sin reiniciar nada.

## Decisiones de diseño (y por qué)

**Un solo Prometheus, un solo target.** El simulador es quien conoce toda la
topología y expone todas las métricas de todos los APs/sedes en un único
`/metrics`. No hay un exporter por AP ni Prometheus federado: agregaría
complejidad operativa sin ningún valor pedagógico adicional, dado que todo es
simulado por el mismo proceso.

**Grafana Unified Alerting en vez de Alertmanager separado.** El objetivo
explícito del proyecto es aprender Grafana; delegar a un Alertmanager aparte
suma un contenedor y una capa de configuración sin aportar a ese objetivo. Las
reglas viven en `grafana/provisioning/alerting/rules.yaml` y usan la política de
notificación por defecto de Grafana.

**Sin Kafka, sin Kubernetes, sin bases de datos externas.** Nada de esto aporta
valor a un laboratorio que corre en un solo host para fines de aprendizaje y
portafolio; se descartaron explícitamente para no sobredimensionar la
arquitectura.

**Topología declarativa en YAML, no en una base de datos.** `simulator/config/topology.yaml`
es toda la fuente de verdad de sedes y APs. Agregar/quitar entidades es editar
un archivo y reconstruir el contenedor — no se necesita un CMDB para 3 sedes y
6 APs.

**`network_ap_up` se mantiene incluso cuando el AP está "caído".** Ver
`docs/scenarios.md` para el detalle de `ap_down`: la intención es distinguir
"el dispositivo dejó de enviar telemetría" (staleness del resto de sus métricas)
de "el sistema de monitoreo ya no sabe si existe" (lo cual rompería el propio
dashboard de disponibilidad). Un heartbeat externo que sigue viendo al AP pero
lo marca caído es un patrón real de NOC.

**`uid: prometheus` fijo en el datasource.** Permite que los JSON de los
dashboards y de las anotaciones referencien el datasource de forma
determinística, sin depender de un uid autogenerado que cambiaría en cada
instalación limpia.

## Convenciones de métricas

- **Namespace**: todas las métricas usan el prefijo `network_`.
- **Labels acotados**: `site` (3 valores), `ap_id` (1-3 por sede), `band`/`direction`/`result`
  donde aplica. **Nunca** se etiqueta por cliente individual — con hasta 100
  clientes por AP eso dispararía la cardinalidad sin necesidad; los datos de
  cliente se agregan a nivel de AP (promedios, o el histograma de latencia).
- **Gauges** para estado instantáneo: `network_ap_up`, `network_ap_clients_connected`,
  `network_ap_channel_utilization_ratio`, `network_ap_rssi_dbm_avg`, `network_ap_snr_db_avg`,
  `network_ap_throughput_mbps`, `network_wan_latency_ms`, `network_wan_packet_loss_ratio`.
- **Counters** (siempre con sufijo `_total`, pensados para usar con `rate()`):
  `network_ap_frames_total`, `network_ap_retries_total`, `network_ap_packets_total`,
  `network_ap_packets_lost_total`, `network_auth_attempts_total{result}`.
- **Histogram**: `network_client_latency_seconds`, con buckets pensados para cubrir
  desde el rango NORMAL (~10-30ms) hasta `wan_degradation` a magnitud plena (~150-300ms).
- **Métrica de anotación**: `network_scenario_active_info{scope,target,scenario}`,
  presente (valor 1) solo mientras un escenario tiene efecto visible sobre esa
  entidad; se usa como fuente de las anotaciones de Grafana y del panel
  State timeline de "Incident Analysis".

## Motor de escenarios

Ver `docs/scenarios.md` para el catálogo completo. En términos de arquitectura,
lo relevante es:

- **Composición**: varias instancias de escenario pueden estar activas a la vez
  sobre distintas entidades (`scenario_engine.ScenarioRegistry`). Cuando dos
  escenarios activos tocan la misma métrica de la misma entidad, se combinan
  tomando el valor más severo por métrica (`METRIC_SEVERITY` en `scenario_defs.py`),
  nunca sumando sin límite.
- **Rampas**: 30s de entrada y 30s de salida (`RAMP_SECONDS`), salvo `ap_down`,
  que es binario (una falla de hardware no es gradual).
- **Auto-expiración** opcional por `duration_s`, o cierre manual con `DELETE /scenarios/{id}`.
- **Alcance**: cada escenario declara si puede invocarse por `site`, por `ap`, o
  ambos (`authentication_failure`).

## Extensiones futuras (fuera de alcance de este proyecto)

No implementadas a propósito, para no sobredimensionar el laboratorio:

- Capa WAN/LAN más rica (switches, enlaces primario/backup) — llevaría el
  proyecto hacia un NOC multi-sede más amplio.
- SLA por cliente/suscriptor (modelo tipo WISP).
- Un servicio de detección de anomalías (z-score/EWMA) sobre las mismas series.
- Un contenedor Mailhog para ver notificaciones de alerta reales sin depender
  de SMTP externo.
