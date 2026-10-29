# Guion de demo en vivo

Guion punto por punto para presentar el proyecto en clase. Todo se controla desde **2 ventanas**: Postman (ejecutás peticiones) y Grafana (ves el efecto). No hace falta abrir Prometheus en ningún momento — su carpeta en Postman existe solo para explicar "por qué hace falta", no porque sea necesaria operar el laboratorio.

Duración total estimada: **20-25 minutos**. De los 7 escenarios disponibles, este guion dispara 5 en vivo (los más representativos); los otros 2 (`AP_OVERLOAD`, `POOR_SIGNAL`) quedan de reserva por si sobra tiempo o alguien pregunta por ellos.

---

## Antes de empezar (fuera de cámara, 2 min)

```bash
cd /Users/equipo/Documents/Udistrital/Inalambricas/grafana-network-stack
docker compose up -d --build
curl -s http://localhost:8000/scenarios   # debe devolver [] -> sin incidentes activos
```

Dejar listo:
- **Postman** abierto, con la colección `grafana-network-stack` importada y expandida (ver sus 4 carpetas).
- **Grafana** (`localhost:3000`, admin/admin) abierto en el dashboard **Network Overview**, variable `site` = "All".
- Si es posible, una segunda ventana/monitor con Grafana, para no estar cambiando de pestaña entre Postman y Grafana todo el tiempo.

---

## Paso a paso

### 1. Introducción oral (30s)

Sin tocar nada todavía. Decir: *"Construí un laboratorio que simula una red WiFi empresarial de 3 sedes y 6 Access Points, 100% local, para poder practicar Grafana y Prometheus disparando incidentes de red a demanda. Todo lo que van a ver sale de un servicio que yo escribí — no hay ningún router real detrás."*

### 2. Grafana en estado normal (30s)

**Mostrar:** dashboard **Network Overview**, ya abierto.
**Decir:** *"Así se ve la red sana: 6 APs arriba, 0 caídos, latencia y clientes estables. Ahora vamos a ir a Postman a romper cosas a propósito."*

### 3. Postman — carpeta "1. Simulador" (1-2 min)

Abrir la colección, mostrar las 4 carpetas de un vistazo: *Simulador*, *Prometheus*, *Incidentes*, *Detener un incidente*.

**Enviar → "Topología (sedes y APs)".**
Decir: *"Esto confirma la topología: 3 sedes, 6 APs. Es el único dato 'fijo' de todo el laboratorio."*

**Enviar → "Catálogo de escenarios".**
Decir: *"Acá están los 7 tipos de incidente que puedo disparar. Hoy vamos a ver 5 de ellos."*

**Enviar → "Métricas crudas (/metrics)".**
Decir: *"Esto es el texto que el simulador expone ahora mismo. Importante: esto SOLO tiene el valor de este instante — no guarda historial. Si lo pido de nuevo en 5 minutos, no sabe qué decía antes. Por eso necesitamos Prometheus en el medio."*

### 4. Postman — carpeta "2. Prometheus" (2-3 min)

**Enviar → "¿Prometheus está sano? (targets)".**
Decir: *"Esto confirma que Prometheus efectivamente está leyendo al simulador cada 15 segundos — los dos targets están en 'up'."*

**Enviar → "Pregunta 1: ¿los APs están prendidos AHORA?".**
Decir: *"Esta pregunta es tan simple que ni siquiera necesita historial — es casi lo mismo que preguntarle al simulador directamente."*

**Enviar → "Pregunta 2: ¿qué tan rápido suben los reintentos?".**
Decir: *"Esta sí es distinta: el número de reintentos solo sube y sube, mirarlo solo no sirve de nada. Acá le estoy preguntando a Prometheus 'qué tan rápido está subiendo ESTE INSTANTE', y esa pregunta es imposible de responder sin que alguien haya guardado el historial. Esa es la única razón por la que existe Prometheus en este proyecto."*

**Enviar → "Pregunta 3: ¿qué % del tráfico son reintentos?".**
Decir: *"Esta es literalmente la fórmula detrás del panel 'Retries ratio' que van a ver en Grafana dentro de un rato."*

**Enviar → "Antes/después: channel utilization de Bogotá".**
Decir: *"Anoten estos 3 números — uno por cada AP de Bogotá. Vamos a romper la sede y volver a hacer esta misma pregunta."* (Guardar mentalmente o anotar los valores.)

### 5. Primer incidente: HIGH_DENSITY (3 min)

**Postman → carpeta "3. Incidentes" → enviar "HIGH_DENSITY — saturación de una sede".**
Decir antes de enviar: *"Vamos a simular que de golpe llega mucha gente a conectarse a TODA la sede de Bogotá — como si hubiera un evento grande. Dura 5 minutos y se revierte sola."*

Esperar ~30 segundos (la rampa de entrada). Mientras tanto:

**Volver a Postman → "2. Prometheus" → reenviar "Antes/después: channel utilization de Bogotá".**
Decir: *"Miren cómo subieron estos mismos 3 números — esto es la prueba de que Postman → simulador → Prometheus → Grafana es una sola cadena real, no magia."*

**Ir a Grafana → Network Overview.**
Señalar: clientes conectados y latencia subieron.

**Ir a Grafana → WiFi RF Health, filtrar `site = bogota`.**
Señalar: channel utilization y retries subieron **en los 3 APs** de la sede (porque el incidente es a nivel sede, no de un AP puntual).

### 6. Segundo incidente: RF_INTERFERENCE (3 min)

**Postman → enviar "RF_INTERFERENCE — interferencia de radio".**
Decir antes de enviar: *"Ahora algo empieza a interferir la señal de radio de un solo punto de acceso en Medellín — como un microondas al lado del router. Esta vez el alcance es un AP puntual, no toda la sede."*

Esperar ~30s.

**Grafana → WiFi RF Health, filtrar `site = medellin`.**
Señalar (el punto más importante de toda la demo): **retries y channel utilization suben solo en `ap-01`; `ap-02` de la misma sede sigue exactamente normal.** Decir: *"Esto prueba que el motor de escenarios respeta el alcance que le pedimos — no es ruido aleatorio por todos lados."*

### 7. Tercer incidente: WAN_DEGRADATION (3 min)

**Postman → enviar "WAN_DEGRADATION — el problema es Internet, no el WiFi".**
Decir antes de enviar: *"Este es mi favorito para explicar: el WiFi de Cali va a seguir funcionando perfecto, pero la conexión a Internet de esa sede se va a poner lenta — como cuando tu router anda bien pero el proveedor de Internet está fallando."*

Esperar ~30s.

**Grafana → Client Experience, filtrar `site = cali`.**
Señalar: "Latencia del uplink WAN" y "Packet loss WAN" se dispararon.

**Grafana → WiFi RF Health, filtrar `site = cali`.**
Señalar: todo normal. Decir: *"Si alguien de soporte viera solo la latencia alta, pensaría 'el WiFi está mal'. Pero mirando esto, queda claro que el WiFi está perfecto — el problema es el proveedor de Internet."*

### 8. Cuarto incidente: AUTHENTICATION_FAILURE (2 min)

**Postman → enviar "AUTHENTICATION_FAILURE — fallos de login".**
Decir antes de enviar: *"Ahora muchos clientes de Bogotá no logran autenticarse a la red — como si el servidor de claves estuviera fallando."*

Esperar ~30s.

**Grafana → Client Experience, filtrar `site = bogota`.**
Señalar: el panel "Fallos de autenticación (%)" sube; el resto de los paneles no se mueve por este incidente.

### 9. Quinto incidente: AP_DOWN (2 min)

**Postman → enviar "AP_DOWN — un AP se apaga".**
Decir antes de enviar: *"Por último, un Access Point en Cali se apaga por completo — como si lo hubieran desenchufado. A diferencia de los anteriores, este no tiene rampa: es instantáneo, porque una falla de hardware real tampoco es gradual."*

**Ir directo a Grafana (no hace falta esperar 30s) → Network Overview.**
Señalar: "APs Down" pasó a 1 al instante, y el panel de disponibilidad pinta a `cali/ap-01` en rojo.

**Grafana → WiFi RF Health, filtrar `site = cali`.**
Señalar: ese AP **desaparece** de los gráficos (no se pone en cero — directamente deja de reportar), a diferencia de cómo se ve un AP con algún otro incidente.

### 10. Composición: todo junto (2-3 min)

En este punto hay 5 incidentes activos a la vez, en 3 sedes distintas.

**Ir a Grafana → Incident Analysis.**
Señalar, en este orden:
1. El número "Incidentes activos" (debería decir 5).
2. El panel **State timeline**: una barra de color por cada incidente, con su nombre y entidad (`site/bogota: high_density`, `ap/medellin/ap-01: rf_interference`, etc.).
3. Las líneas verticales de anotación sobre los gráficos de abajo, marcando el segundo exacto en que empezó cada uno.

Decir: *"Esto demuestra que varios incidentes pueden convivir en paralelo, en entidades distintas, sin pisarse entre sí — y que puedo reconstruir visualmente qué pasó y cuándo."*

### 11. Alertas (2 min)

**Ir a Grafana → Alerting → Alert rules.**
Señalar cuántas de las 7 reglas están en estado **Pending** (debería haber varias, coincidiendo con los incidentes activos: `HighChannelUtilization`, `HighRetriesRatio`, posiblemente `AuthFailureSpike`).

Decir: *"Esto no es un componente aparte tipo Alertmanager — es el motor de alertas nativo de Grafana. Si un incidente dura más de 5 minutos sin resolverse, esa regla pasa de Pending a Firing."*

### 12. Cierre (1 min)

Decir: *"Todo esto —el simulador, los 7 escenarios, los 4 dashboards, las 7 reglas de alerta— está versionado como código en el repo. Se puede levantar de cero con un solo `docker compose up` y queda exactamente así. No usé nada de infraestructura real, cloud, ni APIs externas."*

### 13. Limpieza (fuera de cámara)

Todos los incidentes de este guion tienen `duration_s` configurado, así que se revierten solos. Si desea cortarlos de inmediato:

```bash
curl -s http://localhost:8000/scenarios
# por cada id activo:
curl -X DELETE http://localhost:8000/scenarios/<id>
```

O desde Postman: carpeta "1. Simulador" → "Escenarios activos ahora" para ver los ids, y carpeta "4. Detener un incidente" → "Detener por ID" reemplazando `{{lastScenarioId}}`.

---

## Glosario de una línea (por si preguntan)

- **Prometheus**: le da memoria/historial a datos que de por sí solo existen "en el instante presente".
- **PromQL**: el lenguaje de consultas de Prometheus — como fórmulas de Excel, pero para datos que cambian en el tiempo.
- **Scraping**: Prometheus va y le pregunta al simulador cada 15 segundos "¿cómo estás ahora?", en vez de que el simulador le avise.
- **Rampa**: el incidente no aparece de golpe, sube su severidad durante 30 segundos, como pasaría con una falla real.
- **Scope (alcance)**: si el incidente afecta a toda una sede o a un solo Access Point puntual.
- **Composición**: varios incidentes activos a la vez, en entidades distintas, sin interferirse entre sí.
- **Alerta en Pending vs. Firing**: Pending = "la condición ya se cumple, pero todavía no pasaron los minutos mínimos para confirmarlo"; Firing = "ya se confirmó, dispara de verdad".
