# Ejercicio: su primer panel en Grafana

Bienvenido/a. Este es un ejercicio corto (15-20 minutos) para practicar con el mismo stack presentado en clase: un simulador de red WiFi + Prometheus + Grafana, ejecutándose de forma local en su computador.

No es necesario comprender el proyecto en profundidad. Basta con seguir los pasos en orden.

## Objetivo

Deberá agregar **un panel nuevo** al dashboard "Network Overview" que muestre el **throughput total de toda la red** (la suma de los 6 Access Points de las 3 sedes, en un solo número).

Es el mismo ejercicio para todos — misma métrica, mismo tipo de panel — por lo que no hay margen de error: siguiendo los pasos, se llega al mismo resultado.

## 1. Requisitos

- **Docker Desktop** instalado y en ejecución (Mac/Windows/Linux). Si no lo tiene instalado: https://www.docker.com/products/docker-desktop/
- El archivo `grafana-network-stack.zip` compartido (descomprímalo en la ubicación de su preferencia)

> ¿Prefiere clonar el repositorio en lugar de usar el zip? También está disponible públicamente en GitHub: https://github.com/StevenD15/grafana-network-stack

## 2. Levantar el stack

Abra una terminal, ingrese a la carpeta descomprimida y ejecute:

```bash
cd grafana-network-stack
docker compose up -d --build
```

Espere aproximadamente 1 minuto (la primera vez se descargan las imágenes de Docker). Verifique que los 3 servicios estén activos:

```bash
docker compose ps
```

Debería ver `simulator`, `prometheus` y `grafana`, los tres en estado `Up`.

## 3. Ingresar a Grafana

Abra en el navegador: **http://localhost:3000**

- Usuario: `admin`
- Contraseña: `admin`

Va a solicitar el cambio de contraseña — puede seleccionar **"Skip"**, no es necesario para este ejercicio.

Diríjase a **Dashboards → carpeta "Network Stack" → Network Overview**. Debería ver la red en estado normal: 6 APs activos, 0 caídos, números actualizándose cada 10 segundos.

## 4. Tarea: agregar el panel

| | |
|---|---|
| **Dashboard** | Network Overview |
| **Tipo de panel** | Stat (el mismo tipo que ya utilizan los paneles "APs Up" / "Clientes conectados") |
| **Título del panel** | `Throughput total de la red` |
| **Query (PromQL)** | `sum(network_ap_throughput_mbps{direction="download"})` |
| **Unidad** | Mbits/sec |

### Procedimiento en Grafana

> Verificado paso a paso antes de compartirlo — estos son los nombres de botón exactos en esta versión de Grafana.

1. En el dashboard **Network Overview**, haga clic en **Edit** (arriba a la derecha).
2. Haga clic en **Add** → **Visualization**. Se abre el editor de panel.
3. En la parte inferior, el editor de consultas inicia en modo **Builder**. Haga clic en **Code** (junto a Builder) para pasar a modo texto libre, y pegue exactamente:
   ```
   sum(network_ap_throughput_mbps{direction="download"})
   ```
4. Arriba a la derecha aparece **"Time series"** — haga clic ahí y seleccione **Stat** de la lista.
5. En **Panel options → Title** (columna derecha), elimine "Panel Title" y escriba: `Throughput total de la red`
6. Desplácese hacia abajo en la columna derecha hasta **Standard options → Unit**. Haga clic en el selector, escriba `Mbits` y elija la opción **"Data rate / megabits/sec"**.
7. Arriba a la izquierda, haga clic en **"← Back to dashboard"** (en esta versión no existe el botón "Apply" — esta es la opción equivalente para incorporar el panel al dashboard).
8. Arriba a la derecha, haga clic en **"Save dashboard"**, y en la ventana que aparece, confirme con el botón **"Save"**.

## 5. Verificación de resultado

El panel nuevo debería mostrar un número (aproximadamente entre 300 y 900) que se actualiza automáticamente cada 10 segundos. Esto confirma que está leyendo datos en vivo del simulador a través de Prometheus.

## 6. Opcional — si dispone de tiempo adicional

Puede comprobar que el panel reacciona ante un incidente real, generando uno desde la terminal:

```bash
curl -X POST http://localhost:8000/scenarios \
  -H "Content-Type: application/json" \
  -d '{"scenario":"high_density","scope":"site","target":"bogota","duration_s":120}'
```

Espere unos 30 segundos y observe el panel. El número va a variar — intente explicar con sus propias palabras por qué sube o baja.

## 7. Entrega

Tome una captura de pantalla del panel ya guardado dentro del dashboard, y compártala en [canal / medio indicado por el profesor].

## Resolución de problemas

- `docker compose ps` no muestra los 3 servicios en `Up` → ejecute `docker compose logs` y revise el error que aparece.
- Grafana no abre en `localhost:3000` → verifique que Docker Desktop esté en ejecución (el ícono de la ballena en la barra de tareas/menú).
- El panel no muestra ningún número → verifique que la query se haya copiado exactamente como se indica arriba, sin espacios adicionales ni comillas distintas.
