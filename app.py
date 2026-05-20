"""
Proyecto Integrador - IoT Dashboard para Monitoreo Ambiental y de Movimiento
Caso de uso: Smart Greenhouse Lab
Autor: ajustar nombre del grupo

Ejecucion:
1) pip install -r requirements.txt
2) Crear .streamlit/secrets.toml con las credenciales de InfluxDB
3) streamlit run app.py
"""

from __future__ import annotations

import math
import os
from datetime import datetime, timezone
from typing import Iterable

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from influxdb_client import InfluxDBClient
from influxdb_client.client.exceptions import InfluxDBError

st.set_page_config(
    page_title="Smart Greenhouse Lab",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# CONFIGURACION
# -----------------------------
DEFAULT_URL = "https://us-east-1-1.aws.cloud2.influxdata.com"
DEFAULT_ORG = "miguelcmo"
DEFAULT_BUCKET = "iot_telemetry_data"


def get_secret(name: str, default: str = "") -> str:
    """Lee credenciales desde Streamlit secrets o variables de entorno."""
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return os.getenv(name.upper(), default)


INFLUX_URL = get_secret("influx_url", DEFAULT_URL)
INFLUX_ORG = get_secret("influx_org", DEFAULT_ORG)
INFLUX_BUCKET = get_secret("influx_bucket", DEFAULT_BUCKET)
INFLUX_TOKEN = get_secret("influx_token", "")

# -----------------------------
# ESTILOS
# -----------------------------
st.markdown(
    """
    <style>
    .main {background-color: #f7faf7;}
    .block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
    .hero-card {
        padding: 1.1rem 1.3rem;
        border-radius: 18px;
        background: linear-gradient(135deg, #e8f5e9 0%, #f4fbf5 100%);
        border: 1px solid #d3ead6;
        margin-bottom: 1rem;
    }
    .status-ok {
        padding: .75rem 1rem; border-radius: 14px; background-color: #e8f5e9;
        border-left: 6px solid #2e7d32; font-weight: 600;
    }
    .status-warn {
        padding: .75rem 1rem; border-radius: 14px; background-color: #fff8e1;
        border-left: 6px solid #f9a825; font-weight: 600;
    }
    .status-danger {
        padding: .75rem 1rem; border-radius: 14px; background-color: #ffebee;
        border-left: 6px solid #c62828; font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# CONSULTAS INFLUXDB
# -----------------------------
@st.cache_data(ttl=15, show_spinner=False)
def query_measurement(measurement: str, fields: tuple[str, ...], minutes: int) -> pd.DataFrame:
    """Consulta una medicion en InfluxDB y retorna datos pivoteados por tiempo."""
    if not INFLUX_TOKEN:
        raise ValueError("No se encontro INFLUX_TOKEN. Configura .streamlit/secrets.toml o variable de entorno.")

    field_filter = " or ".join([f'r._field == "{field}"' for field in fields])
    flux = f'''
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -{minutes}m)
      |> filter(fn: (r) => r._measurement == "{measurement}")
      |> filter(fn: (r) => {field_filter})
      |> aggregateWindow(every: 10s, fn: mean, createEmpty: false)
      |> pivot(rowKey:["_time"], columnKey:["_field"], valueColumn:"_value")
      |> keep(columns: ["_time", {", ".join([f'"{field}"' for field in fields])}])
      |> sort(columns: ["_time"])
    '''
    with InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG, timeout=20_000) as client:
        df = client.query_api().query_data_frame(org=INFLUX_ORG, query=flux)

    if isinstance(df, list):
        df = pd.concat(df, ignore_index=True) if df else pd.DataFrame()
    if df.empty:
        return pd.DataFrame(columns=["time", *fields])

    df = df.rename(columns={"_time": "time"})
    df["time"] = pd.to_datetime(df["time"])
    for field in fields:
        if field not in df.columns:
            df[field] = np.nan
    return df[["time", *fields]].dropna(how="all", subset=list(fields))


def demo_data(minutes: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Genera datos simulados para probar el dashboard sin conexion."""
    periods = max(40, int(minutes * 3))
    times = pd.date_range(end=datetime.now(timezone.utc), periods=periods, freq="20s")
    x = np.linspace(0, 3 * math.pi, periods)
    env = pd.DataFrame(
        {
            "time": times,
            "temperature": 24 + 2.5 * np.sin(x) + np.random.normal(0, 0.35, periods),
            "humidity": 62 + 8 * np.cos(x / 1.3) + np.random.normal(0, 1.2, periods),
        }
    )
    motion = pd.DataFrame(
        {
            "time": times,
            "accel_x": 0.02 * np.random.normal(size=periods),
            "accel_y": 0.02 * np.random.normal(size=periods),
            "accel_z": 1 + 0.03 * np.random.normal(size=periods),
            "gyro_x": 0.5 * np.random.normal(size=periods),
            "gyro_y": 0.5 * np.random.normal(size=periods),
            "gyro_z": 0.5 * np.random.normal(size=periods),
        }
    )
    # Simula un evento de movimiento brusco
    if periods > 15:
        motion.loc[motion.index[-12:-8], ["accel_x", "accel_y"]] += [0.4, -0.3]
        motion.loc[motion.index[-12:-8], ["gyro_x", "gyro_z"]] += [7, -5]
    return env, motion


def latest_value(df: pd.DataFrame, col: str) -> float | None:
    if df.empty or col not in df.columns:
        return None
    values = df[col].dropna()
    return None if values.empty else float(values.iloc[-1])


def metric_delta(df: pd.DataFrame, col: str) -> float | None:
    if df.empty or col not in df.columns:
        return None
    values = df[col].dropna()
    if len(values) < 2:
        return None
    return float(values.iloc[-1] - values.iloc[-2])


def add_motion_features(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    accel_cols = ["accel_x", "accel_y", "accel_z"]
    gyro_cols = ["gyro_x", "gyro_y", "gyro_z"]
    for col in accel_cols + gyro_cols:
        if col not in df.columns:
            df[col] = 0.0
    df["accel_magnitude"] = np.sqrt(df["accel_x"] ** 2 + df["accel_y"] ** 2 + df["accel_z"] ** 2)
    df["gyro_magnitude"] = np.sqrt(df["gyro_x"] ** 2 + df["gyro_y"] ** 2 + df["gyro_z"] ** 2)
    return df


def status_box(label: str, severity: str = "ok") -> None:
    css = {"ok": "status-ok", "warn": "status-warn", "danger": "status-danger"}.get(severity, "status-ok")
    st.markdown(f'<div class="{css}">{label}</div>', unsafe_allow_html=True)


# -----------------------------
# SIDEBAR
# -----------------------------
st.sidebar.title("Configuración")
minutes = st.sidebar.slider("Ventana de análisis", min_value=5, max_value=180, value=60, step=5)
use_demo = st.sidebar.toggle("Usar datos simulados", value=False)
refresh = st.sidebar.selectbox("Actualización visual", ["Manual", "Cada 15 segundos", "Cada 30 segundos", "Cada 60 segundos"], index=1)

try:
    interval = {"Cada 15 segundos": 15, "Cada 30 segundos": 30, "Cada 60 segundos": 60}.get(refresh)
    if interval:
        st.query_params["refresh"] = str(interval)
        # st.rerun no se programa solo; el usuario puede activar Auto rerun o refrescar. Se conserva cache ttl=15.
except Exception:
    pass

st.sidebar.markdown("---")
st.sidebar.caption("Variables: DHT22: temperatura/humedad. MPU6050: acelerómetro y giroscopio.")

# -----------------------------
# CARGA DE DATOS
# -----------------------------
load_error = None
try:
    if use_demo:
        env_df, motion_df = demo_data(minutes)
    else:
        env_df = query_measurement("environment", ("temperature", "humidity"), minutes)
        motion_df = query_measurement(
            "mpu6050",
            ("accel_x", "accel_y", "accel_z", "gyro_x", "gyro_y", "gyro_z"),
            minutes,
        )
except (InfluxDBError, ValueError, Exception) as exc:
    load_error = str(exc)
    env_df, motion_df = demo_data(minutes)
    use_demo = True

motion_df = add_motion_features(motion_df)

# -----------------------------
# HEADER
# -----------------------------
st.markdown(
    """
    <div class="hero-card">
        <h1 style="margin:0; color:#1b5e20;">Smart Greenhouse Lab</h1>
        <p style="margin:.35rem 0 0 0; font-size:1.05rem;">
        Dashboard IoT para monitoreo ambiental y de movimiento en una estación experimental de cultivo.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

if load_error:
    st.warning("No fue posible consultar InfluxDB. El tablero está mostrando datos simulados para pruebas. Detalle técnico: " + load_error)

# -----------------------------
# INDICADORES
# -----------------------------
temp = latest_value(env_df, "temperature")
hum = latest_value(env_df, "humidity")
accel_mag = latest_value(motion_df, "accel_magnitude")
gyro_mag = latest_value(motion_df, "gyro_magnitude")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Temperatura", f"{temp:.1f} °C" if temp is not None else "Sin datos", delta=f"{metric_delta(env_df, 'temperature'):.2f}" if metric_delta(env_df, 'temperature') is not None else None)
c2.metric("Humedad", f"{hum:.1f} %" if hum is not None else "Sin datos", delta=f"{metric_delta(env_df, 'humidity'):.2f}" if metric_delta(env_df, 'humidity') is not None else None)
c3.metric("Magnitud aceleración", f"{accel_mag:.2f} g" if accel_mag is not None else "Sin datos")
c4.metric("Magnitud giroscopio", f"{gyro_mag:.2f} °/s" if gyro_mag is not None else "Sin datos")

# -----------------------------
# ALERTAS
# -----------------------------
st.subheader("Estado operativo")
a1, a2, a3 = st.columns(3)
with a1:
    if temp is None:
        status_box("Temperatura: sin lectura", "warn")
    elif temp >= 30:
        status_box("Alerta: temperatura alta para el cultivo", "danger")
    elif temp <= 16:
        status_box("Alerta: temperatura baja", "warn")
    else:
        status_box("Temperatura en rango operativo", "ok")
with a2:
    if hum is None:
        status_box("Humedad: sin lectura", "warn")
    elif hum < 45:
        status_box("Alerta: humedad baja", "warn")
    elif hum > 80:
        status_box("Alerta: humedad elevada", "warn")
    else:
        status_box("Humedad estable", "ok")
with a3:
    if accel_mag is None or gyro_mag is None:
        status_box("Movimiento: sin lectura", "warn")
    elif accel_mag > 1.25 or gyro_mag > 6:
        status_box("Movimiento detectado: posible golpe o manipulación", "danger")
    else:
        status_box("Sin movimiento anómalo", "ok")

# -----------------------------
# GRAFICAS
# -----------------------------
st.subheader("Visualizaciones en tiempo real")

g1, g2 = st.columns(2)
with g1:
    if not env_df.empty:
        fig = px.line(env_df, x="time", y="temperature", markers=False, title="Temperatura - DHT22")
        fig.update_layout(yaxis_title="°C", xaxis_title="Tiempo", height=360)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos de temperatura.")
with g2:
    if not env_df.empty:
        fig = px.line(env_df, x="time", y="humidity", markers=False, title="Humedad relativa - DHT22")
        fig.update_layout(yaxis_title="%", xaxis_title="Tiempo", height=360)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos de humedad.")

g3, g4 = st.columns(2)
with g3:
    if not motion_df.empty:
        accel_long = motion_df.melt(id_vars="time", value_vars=["accel_x", "accel_y", "accel_z", "accel_magnitude"], var_name="variable", value_name="valor")
        fig = px.line(accel_long, x="time", y="valor", color="variable", title="Aceleración y magnitud - MPU6050")
        fig.update_layout(yaxis_title="g", xaxis_title="Tiempo", height=360)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos de acelerómetro.")
with g4:
    if not motion_df.empty:
        gyro_long = motion_df.melt(id_vars="time", value_vars=["gyro_x", "gyro_y", "gyro_z", "gyro_magnitude"], var_name="variable", value_name="valor")
        fig = px.line(gyro_long, x="time", y="valor", color="variable", title="Giroscopio y magnitud - MPU6050")
        fig.update_layout(yaxis_title="°/s", xaxis_title="Tiempo", height=360)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos de giroscopio.")

st.subheader("Tabla de lecturas recientes")
combined = pd.merge_asof(
    env_df.sort_values("time"),
    motion_df.sort_values("time"),
    on="time",
    direction="nearest",
    tolerance=pd.Timedelta("15s"),
) if not env_df.empty and not motion_df.empty else pd.DataFrame()

if not combined.empty:
    st.dataframe(combined.tail(25).sort_values("time", ascending=False), use_container_width=True)
else:
    st.info("No hay suficientes datos sincronizados para construir la tabla combinada.")

st.caption("Diseñado para proyecto integrador de Computación Física e IoT. Fuente de datos: InfluxDB Cloud / sensores DHT22 y MPU6050.")
