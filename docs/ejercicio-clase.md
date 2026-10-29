# Ejercicio: tu primer panel en Grafana

Bienvenido/a. Este es un ejercicio corto (15-20 minutos) para que practiques con el mismo stack que viste en la presentación: un simulador de red WiFi + Prometheus + Grafana, todo corriendo local en tu computador.

No hace falta que entiendas todo el proyecto a fondo. Seguí los pasos en orden y listo.

## Objetivo

Vas a agregar **un panel nuevo** al dashboard "Network Overview" que muestre el **throughput total de toda la red** (la suma de los 6 Access Points de las 3 sedes, en un solo número).

Es el mismo ejercicio para todos — misma métrica, mismo tipo de panel — así que no hay vuelta incorrecta: si seguís los pasos, llegás al mismo resultado.

## 1. Requisitos

- **Docker Desktop** instalado y corriendo (Mac/Windows/Linux). Si no lo tenés: https://www.docker.com/products/docker-desktop/
- El archivo `grafana-network-stack.zip` que te compartimos (descomprimilo donde quieras)

> ¿Preferís clonarlo en vez de usar el zip? También está público en GitHub: https://github.com/StevenD15/grafana-network-stack

## 2. Levantar el stack

Abrí una terminal, entrá a la carpeta descomprimida y corré:

```bash
cd grafana-network-stack
docker compose up -d --build
```

Esperá aproximadamente 1 minuto (la primera vez descarga las imágenes de Docker). Verificá que los 3 servicios estén arriba:

```bash
docker compose ps
```

Deberías ver `simulator`, `prometheus` y `grafana`, los tres en estado `Up`.

## 3. Entrar a Grafana

Abrí en el navegador: **http://localhost:3000**

- Usuario: `admin`
- Contraseña: `admin`

Te va a pedir cambiar la contraseña — podés tocar **"Skip"**, no hace falta para este ejercicio.

Andá a **Dashboards → carpeta "Network Stack" → Network Overview**. Deberías ver la red en estado normal: 6 APs arriba, 0 caídos, números moviéndose solos cada 10 segundos.

## 4. Tu tarea: agregar el panel

| | |
|---|---|
| **Dashboard** | Network Overview |
| **Tipo de panel** | Stat (el mismo tipo que ya usan los paneles "APs Up" / "Clientes conectados" arriba del dashboard) |
| **Título del panel** | `Throughput total de la red` |
| **Query (PromQL)** | `sum(network_ap_throughput_mbps{direction="download"})` |
| **Unidad** | Mbits/sec |

### Paso a paso en Grafana

> Ensayado de punta a punta antes de pasarlo — estos son los nombres de botón exactos en esta versión de Grafana.

1. En el dashboard **Network Overview**, hacé clic en **Edit** (arriba a la derecha).
2. Hacé clic en **Add** → **Visualization**. Se abre el editor de panel.
3. Abajo, en la query, el editor arranca en modo **Builder**. Hacé clic en **Code** (al lado de Builder) para pasar a modo texto libre, y pegá exactamente:
   ```
   sum(network_ap_throughput_mbps{direction="download"})
   ```
4. Arriba a la derecha del todo dice **"Time series"** — hacé clic ahí y elegí **Stat** de la lista (es el mismo tipo que ya usan los paneles "APs Up" / "Clientes conectados").
5. En **Panel options → Title** (columna derecha), borrá "Panel Title" y escribí: `Throughput total de la red`
6. Scrolleá hacia abajo en la columna derecha hasta **Standard options → Unit**. Hacé clic en el selector, escribí `Mbits` y elegí la opción **"Data rate / megabits/sec"**.
7. Arriba a la izquierda, hacé clic en **"← Back to dashboard"** (no hay botón "Apply" en esta versión — este es el que agrega el panel al dashboard).
8. Arriba a la derecha, hacé clic en **"Save dashboard"**, y en la ventana que aparece, confirmá con el botón **"Save"**.

## 5. ¿Cómo sé que funcionó?

Tu panel nuevo debería mostrar un número (algo entre 300 y 900) que cambia solo cada 10 segundos. Eso confirma que está leyendo datos en vivo del simulador a través de Prometheus.

## 6. Opcional — si te sobra tiempo

Podés comprobar que tu panel reacciona a un incidente real, disparando uno desde la terminal:

```bash
curl -X POST http://localhost:8000/scenarios \
  -H "Content-Type: application/json" \
  -d '{"scenario":"high_density","scope":"site","target":"bogota","duration_s":120}'
```

Esperá unos 30 segundos y mirá tu panel. El número se va a mover — tratá de explicar con tus palabras por qué sube o baja.

## 7. Entrega

Sacale una captura de pantalla a tu panel ya guardado dentro del dashboard, y compartila en [canal / medio que indique el profesor].

## Si algo no funciona

- `docker compose ps` no muestra los 3 servicios en `Up` → corré `docker compose logs` y fijate qué error aparece.
- Grafana no abre en `localhost:3000` → verificá que Docker Desktop esté corriendo (el ícono de la ballena en la barra de tareas/menú).
- El panel no muestra ningún número → revisá que copiaste la query exactamente como está arriba, sin espacios de más ni comillas distintas.
