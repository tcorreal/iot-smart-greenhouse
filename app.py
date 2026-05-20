import streamlit as st
import pandas as pd
from influxdb_client import InfluxDBClient
import plotly.express as px
import plotly.graph_objects as go

# --------------------------------------------------
# CONFIGURACION GENERAL
# --------------------------------------------------

st.set_page_config(
    page_title="Smart Greenhouse Lab",
    page_icon="🌿",
    layout="wide"
)

st.title("🌿 Smart Greenhouse Lab")
st.markdown(
    """
    Sistema IoT para monitoreo ambiental y de movimiento
    utilizando InfluxDB y Streamlit.
    """
)

# --------------------------------------------------
# CONEXION INFLUXDB
# --------------------------------------------------

url = st.secrets["INFLUX_URL"]
token = st.secrets["INFLUX_TOKEN"]
org = st.secrets["INFLUX_ORG"]
bucket = st.secrets["INFLUX_BUCKET"]

client = InfluxDBClient(
    url=url,
    token=token,
    org=org
)

query_api = client.query_api()

# --------------------------------------------------
# CONSULTA FLUX
# --------------------------------------------------

query = f'''
from(bucket: "{bucket}")
  |> range(start: -1h)
'''

try:

    df = query_api.query_data_frame(query)

    # ----------------------------------------------
    # LIMPIEZA
    # ----------------------------------------------

    if isinstance(df, list):
        df = pd.concat(df)

    df = df[["_time", "_measurement", "_field", "_value"]]

    df["_time"] = pd.to_datetime(df["_time"])

    # ----------------------------------------------
    # KPIs
    # ----------------------------------------------

    temp_df = df[df["_field"] == "temperature"]
    hum_df = df[df["_field"] == "humidity"]

    accel_df = df[
        (df["_field"] == "accel_x") |
        (df["_field"] == "accel_y") |
        (df["_field"] == "accel_z")
    ]

    temperatura_actual = (
        temp_df["_value"].iloc[-1]
        if not temp_df.empty else 0
    )

    humedad_actual = (
        hum_df["_value"].iloc[-1]
        if not hum_df.empty else 0
    )

    movimiento_actual = (
        accel_df["_value"].abs().max()
        if not accel_df.empty else 0
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "🌡️ Temperatura Actual",
        f"{temperatura_actual:.2f} °C"
    )

    col2.metric(
        "💧 Humedad Actual",
        f"{humedad_actual:.2f} %"
    )

    col3.metric(
        "📈 Movimiento Detectado",
        f"{movimiento_actual:.2f}"
    )

    st.divider()

    # --------------------------------------------------
    # ALERTAS
    # --------------------------------------------------

    if temperatura_actual > 30:
        st.error("⚠️ Alerta: temperatura alta detectada")

    elif temperatura_actual < 18:
        st.warning("⚠️ Temperatura baja detectada")

    else:
        st.success("✅ Temperatura en rango normal")

    # --------------------------------------------------
    # GRAFICA TEMPERATURA
    # --------------------------------------------------

    st.subheader("🌡️ Temperatura")

    fig_temp = px.line(
        temp_df,
        x="_time",
        y="_value",
        title="Comportamiento de la temperatura",
        labels={
            "_time": "Tiempo",
            "_value": "Temperatura °C"
        }
    )

    st.plotly_chart(fig_temp, use_container_width=True)

    # --------------------------------------------------
    # GRAFICA HUMEDAD
    # --------------------------------------------------

    st.subheader("💧 Humedad")

    fig_hum = px.line(
        hum_df,
        x="_time",
        y="_value",
        title="Comportamiento de la humedad",
        labels={
            "_time": "Tiempo",
            "_value": "Humedad %"
        }
    )

    st.plotly_chart(fig_hum, use_container_width=True)

    # --------------------------------------------------
    # GRAFICA MOVIMIENTO
    # --------------------------------------------------

    st.subheader("📈 Movimiento / Aceleracion")

    fig_accel = px.line(
        accel_df,
        x="_time",
        y="_value",
        color="_field",
        title="Movimiento detectado por MPU6050",
        labels={
            "_time": "Tiempo",
            "_value": "Aceleracion"
        }
    )

    st.plotly_chart(fig_accel, use_container_width=True)

    # --------------------------------------------------
    # TABLA
    # --------------------------------------------------

    st.subheader("📋 Datos recientes")

    st.dataframe(
        df.tail(20),
        use_container_width=True
    )

except Exception as e:

    st.error(
        f"No fue posible consultar InfluxDB.\n\nDetalle técnico: {e}"
    )
