# Smart Greenhouse Lab - Proyecto Integrador IoT

Dashboard en Streamlit para monitorear datos ambientales y de movimiento desde InfluxDB.

## Caso de uso

Una estación experimental de cultivo requiere monitorear temperatura, humedad y movimiento del módulo. El DHT22 reporta variables ambientales y el MPU6050 permite detectar vibraciones, golpes o manipulación física.

## Instalación

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Configuración de credenciales

Crear el archivo `.streamlit/secrets.toml` con esta estructura:

```toml
influx_url = "https://us-east-1-1.aws.cloud2.influxdata.com"
influx_org = "miguelcmo"
influx_bucket = "iot_telemetry_data"
influx_token = "PEGAR_AQUI_EL_TOKEN_DE_INFLUXDB"
```

## Ejecución

```bash
streamlit run app.py
```

## Visualizaciones incluidas

1. Temperatura en tiempo real.
2. Humedad relativa en tiempo real.
3. Aceleración por ejes y magnitud.
4. Giroscopio por ejes y magnitud.
5. Indicadores clave y alertas básicas.
6. Tabla de lecturas recientes.

## Nota de seguridad

No subir el archivo `secrets.toml` a repositorios públicos. Si el token fue compartido en un entorno público, debe regenerarse en InfluxDB.
