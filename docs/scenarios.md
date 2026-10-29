# Escenarios de incidente

## Taxonomía: alcance × dominio de falla

En vez de un único "modo global" de red, cada escenario se inyecta sobre una
entidad puntual (una sede, o un AP dentro de una sede), y varios pueden estar
activos a la vez sobre entidades distintas — o incluso sobre la misma, en cuyo
caso sus efectos se combinan (ver `docs/architecture.md`).

| Escenario | Alcance | Dominio | Métricas que toca |
|---|---|---|---|
| `high_density` | sede | Capacidad | clientes, channel utilization, retries, packet loss, latencia, throughput |
| `ap_overload` | AP puntual | Capacidad | igual que `high_density`, acotado a un AP |
| `rf_interference` | AP puntual | RF | channel utilization, retries |
| `poor_signal` | AP puntual | RF | RSSI, SNR, packet loss, latencia, throughput |
| `wan_degradation` | sede | Backhaul | latencia y packet loss del uplink WAN (nada de RF/capacidad) |
| `authentication_failure` | sede o AP | AuthN | ratio de fallos de autenticación |
| `ap_down` | AP puntual | Disponibilidad | `up=0`; el resto de sus métricas desaparece (staleness) |

`high_density` y `ap_overload` comparten la misma función de rangos
(`scenario_defs._high_density_ranges`) porque son el mismo fenómeno de
saturación a distinta escala: uno afecta a todos los APs de una sede
(crecimiento orgánico de clientes), el otro a un AP puntual (carga
desbalanceada, p. ej. por un algoritmo de roaming que no distribuye bien).

`poor_signal` es una aproximación: el modelo de métricas agrega por AP (RSSI/SNR
promedio) para no explotar la cardinalidad etiquetando por cliente individual,
así que "un subconjunto de clientes con mala señal" se representa como un
desplazamiento del promedio del AP hacia abajo, no como una serie separada por
cliente.

## Rangos por escenario (a magnitud plena, `magnitude=1.0`)

| Métrica | NORMAL | high_density / ap_overload | rf_interference | poor_signal | wan_degradation | authentication_failure |
|---|---|---|---|---|---|---|
| clientes conectados | 20-40 | 70-100 | — | — | — | — |
| channel utilization | 20-50% | 75-95% | 75-95% | — | — | — |
| retries ratio | 1-5% | 15-30% | 20-40% | — | — | — |
| packet loss WiFi | 0.1-1% | 2-5% | — | 3-7% | — | — |
| latencia (cliente) | 10-30ms | 40-100ms | — | 50-120ms | — | — |
| throughput (multiplicador) | 100% | 30-50% | — | 40-60% | — | — |
| RSSI | -60 a -45 dBm | — | — | -90 a -75 dBm | — | — |
| SNR | 25-40 dB | — | — | 5-15 dB | — | — |
| latencia WAN | 10-30ms | — | — | — | 150-300ms | — |
| packet loss WAN | 0-1% | — | — | — | 5-15% | — |
| fallos de autenticación | 0-2% | — | — | — | — | 30-60% |

Los guiones indican que ese escenario no desplaza esa métrica: cae al rango
NORMAL. Para `magnitude` entre 0 y 1 (parámetro opcional de la API), el rango
objetivo se interpola linealmente entre NORMAL y el valor de esta tabla.

## Rampas

Al activarse, cada escenario (salvo `ap_down`) hace una rampa de entrada de 30s
antes de alcanzar su magnitud objetivo — no hay saltos instantáneos. Al
detenerse (por `DELETE` o por vencimiento de `duration_s`), hace una rampa de
salida de otros 30s antes de desaparecer del todo. `ap_down` es binario: una
falla de hardware no es gradual.

## API de control

```bash
# Catálogo de escenarios disponibles, con su(s) alcance(s) válido(s)
curl http://localhost:8000/scenarios/catalog

# Disparar un escenario
curl -X POST http://localhost:8000/scenarios \
  -H "Content-Type: application/json" \
  -d '{
        "scenario": "<nombre>",
        "scope": "site" | "ap",
        "target": "<sede>" | "<sede>/<ap_id>",
        "duration_s": <segundos, opcional>,
        "magnitude": <0.0-1.0, opcional, default 1.0>
      }'

# Ver escenarios activos y su progreso de rampa (0.0-1.0)
curl http://localhost:8000/scenarios

# Detener manualmente (inicia la rampa de salida)
curl -X DELETE http://localhost:8000/scenarios/<id>
```

### Ejemplos

```bash
# Saturación en toda la sede de Bogotá, permanente hasta que se detenga a mano
curl -X POST http://localhost:8000/scenarios -H "Content-Type: application/json" \
  -d '{"scenario":"high_density","scope":"site","target":"bogota"}'

# Interferencia RF en un solo AP de Medellín, durante 10 minutos, y que se revierta sola
curl -X POST http://localhost:8000/scenarios -H "Content-Type: application/json" \
  -d '{"scenario":"rf_interference","scope":"ap","target":"medellin/ap-01","duration_s":600}'

# Degradación de WAN en Cali al 50% de magnitud (para ver un incidente "leve")
curl -X POST http://localhost:8000/scenarios -H "Content-Type: application/json" \
  -d '{"scenario":"wan_degradation","scope":"site","target":"cali","magnitude":0.5}'

# Un AP se cae por completo
curl -X POST http://localhost:8000/scenarios -H "Content-Type: application/json" \
  -d '{"scenario":"ap_down","scope":"ap","target":"cali/ap-01"}'
```

## Qué observar en los dashboards durante cada escenario

- **`high_density` / `ap_overload`**: en *WiFi RF Health* sube channel utilization
  y retries; en *Client Experience* sube la latencia y baja el throughput; RSSI/SNR
  no se mueven — si alguien reporta "el WiFi está lento" y ve esto, la causa es
  saturación, no señal.
- **`rf_interference`**: solo sube channel utilization y retries en el AP puntual;
  el resto de APs de la misma sede no se ven afectados (scoping).
- **`poor_signal`**: baja RSSI/SNR del AP y sube su latencia/packet loss; los
  demás APs de la sede quedan normales.
- **`wan_degradation`**: sube la latencia/packet loss del uplink WAN en
  *Client Experience*, pero *WiFi RF Health* del mismo sitio se ve completamente
  normal — el caso de uso central para demostrar que no todo problema percibido
  por el usuario es culpa del WiFi.
- **`authentication_failure`**: solo sube el panel de fallos de autenticación;
  nada de RF ni de capacidad cambia.
- **`ap_down`**: el AP desaparece del panel *RSSI/SNR/channel utilization* (sin
  quedar en cero, sencillamente sin datos) y el *State timeline* de
  *Incident Analysis* junto con el panel *Disponibilidad de APs* de
  *Network Overview* lo muestran en rojo.

En todos los casos, el dashboard **Incident Analysis** superpone anotaciones
verticales (inicio/fin) y un panel State timeline con el escenario activo por
entidad, para poder correlacionar visualmente "qué cambió durante el incidente".
