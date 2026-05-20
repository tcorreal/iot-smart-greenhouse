import streamlit as st
import pandas as pd
import plotly.express as px
from influxdb_client import InfluxDBClient

st.set_page_config(
    page_title="Smart Greenhouse Lab",
    page_icon="🌿",
    layout="wide"
)

# =========================
# ESTILOS
# =========================

st.markdown("""
<style>
.main {
    background-color: #f6faf7;
}
.block-container {
    padding-top: 2rem;
}
.hero {
    background: linear-gradient(135deg, #0f5132, #198754);
    padding: 28px;
    border-radius: 22px;
    color: white;
    margin-bottom: 25px;
}
.hero h1 {
    font-size: 42px;
    margin-bottom: 5px;
}
.hero p {
    font-size: 18px;
    opacity: 0.95;
}
.card {
    background-color: white;
    padding: 22px;
    border-radius: 18px;
    box-shadow: 0 4px 18px rgba(0,0,0,0.07);
    border: 1px solid #e6efe8;
}
.section-title {
    font-size: 24px;
    font-weight: 700;
    color: #164b35;
    margin-top: 20px;
    margin-bottom: 10px;
}
.alert-ok {
    background-color: #e7f6ec;
    color: #146c43;
    padding: 15px;
    border-radius: 14px;
    border-left: 6px solid #198754;
}
.alert-warning {
    background-color: #fff3cd;
    color: #664d03;
    padding: 15px;
    border-radius: 14px;
    border-left: 6px solid #ffc107;
}
.alert-danger {
    background-color: #f8d7da;
    color: #842029;
    padding: 15px;
    border-radius: 14px;
    border-left: 6px solid #dc3545;
}
</style>
""", unsafe_allow_html=True)

# =========================
# ENCABEZADO
# =========================

st.markdown("""
<div class="hero">
    <h1>🌿 Smart Greenhouse Lab</h1>
    <p>
    Dashboard IoT para monitoreo ambiental y estabilidad física de un invernadero experimental.
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
Este sistema consulta datos desde **InfluxDB** y permite visualizar en tiempo real variables ambientales
como **temperatura** y **humedad**, además de señales de **movimiento o vibración** asociadas a la estabilidad física del módulo.
""")

# =========================
# SIDEBAR
# =========================

st.sidebar.title("⚙️ Configuración")

range_option = st.sidebar.selectbox(
    "Rango de consulta",
    ["Última hora", "Últimas 6 horas", "Últimas 24 horas", "Últimos 7 días"]
)

range_map = {
    "Última hora": "-1h",
    "Últimas 6 horas": "-6h",
    "Últimas 24 horas": "-24h",
    "Últimos 7 días": "-7d"
}

time_range = range_map[range_option]

temp_high_limit = st.sidebar.slider("Límite temperatura alta °C", 25, 45, 30)
temp_low_limit = st.sidebar.slider("Límite temperatura baja °C", 5, 25, 18)
humidity_low_limit = st.sidebar.slider("Límite humedad baja %", 10, 80, 40)
motion_limit = st.sidebar.slider("Límite movimiento/vibración", 5, 30, 15)

st.sidebar.markdown("---")
st.sidebar.info(
    "La aceleración se usa para detectar vibraciones, golpes, inclinaciones o manipulación física del invernadero."
)

# =========================
# CONEXIÓN INFLUXDB
# =========================

url = st.secrets["INFLUX_URL"]
token = st.secrets["INFLUX_TOKEN"]
org = st.secrets["INFLUX_ORG"]
bucket = st.secrets["INFLUX_BUCKET"]

client = InfluxDBClient(url=url, token=token, org=org)
query_api = client.query_api()

query = f'''
from(bucket: "{bucket}")
  |> range(start: {time_range})
  |> filter(fn: (r) => r._measurement == "environment" or r._measurement == "mpu6050")
  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
'''

# =========================
# FUNCIONES
# =========================

def get_last_value(dataframe, column):
    if column in dataframe.columns and not dataframe[column].dropna().empty:
        return dataframe[column].dropna().iloc[-1]
    return None

def make_line_chart(dataframe, y_column, title, y_label):
    fig = px.line(
        dataframe,
        x="_time",
        y=y_column,
        title=title,
        labels={"_time": "Tiempo", y_column: y_label},
        markers=True
    )
    fig.update_layout(
        height=360,
        margin=dict(l=20, r=20, t=60, b=20),
        plot_bgcolor="white",
        paper_bgcolor="white",
        title_font=dict(size=20),
        xaxis=dict(showgrid=True),
        yaxis=dict(showgrid=True)
    )
    return fig

# =========================
# CONSULTA Y DASHBOARD
# =========================

try:
    df = query_api.query_data_frame(query)

    if isinstance(df, list):
        df = pd.concat(df, ignore_index=True)

    if df.empty:
        st.warning("No se encontraron datos para el rango seleccionado.")
        st.stop()

    df["_time"] = pd.to_datetime(df["_time"])

    keep_cols = [
        "_time",
        "temperature",
        "humidity",
        "accel_x",
        "accel_y",
        "accel_z",
        "gyro_x",
        "gyro_y",
        "gyro_z"
    ]

    existing_cols = [col for col in keep_cols if col in df.columns]
    df = df[existing_cols].sort_values("_time")

    # Magnitud de movimiento
    accel_cols = [c for c in ["accel_x", "accel_y", "accel_z"] if c in df.columns]

    if accel_cols:
        df["movement_intensity"] = (
            df[accel_cols]
            .fillna(0)
            .pow(2)
            .sum(axis=1)
            .pow(0.5)
        )
    else:
        df["movement_intensity"] = 0

    temperatura_actual = get_last_value(df, "temperature")
    humedad_actual = get_last_value(df, "humidity")
    movimiento_actual = get_last_value(df, "movement_intensity")

    # =========================
    # KPIs
    # =========================

    st.markdown('<div class="section-title">Indicadores principales</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Temperatura actual",
        f"{temperatura_actual:.2f} °C" if temperatura_actual is not None else "Sin dato"
    )

    col2.metric(
        "Humedad actual",
        f"{humedad_actual:.2f} %" if humedad_actual is not None else "Sin dato"
    )

    col3.metric(
        "Movimiento/vibración",
        f"{movimiento_actual:.2f}" if movimiento_actual is not None else "Sin dato"
    )

    col4.metric(
        "Registros consultados",
        len(df)
    )

    # =========================
    # ESTADO GENERAL
    # =========================

    st.markdown('<div class="section-title">Estado del invernadero</div>', unsafe_allow_html=True)

    alertas = []

    if temperatura_actual is not None:
        if temperatura_actual > temp_high_limit:
            alertas.append("Temperatura alta: revisar ventilación o exposición solar.")
        elif temperatura_actual < temp_low_limit:
            alertas.append("Temperatura baja: revisar aislamiento térmico.")

    if humedad_actual is not None:
        if humedad_actual < humidity_low_limit:
            alertas.append("Humedad baja: revisar riego o nebulización.")

    if movimiento_actual is not None:
        if movimiento_actual > motion_limit:
            alertas.append("Movimiento anormal: posible vibración, golpe o manipulación del módulo.")

    if not alertas:
        st.markdown(
            '<div class="alert-ok">Estado normal: las variables se encuentran dentro de los rangos esperados.</div>',
            unsafe_allow_html=True
        )
    else:
        for alerta in alertas:
            st.markdown(
                f'<div class="alert-warning">⚠️ {alerta}</div>',
                unsafe_allow_html=True
            )

    # =========================
    # GRÁFICOS
    # =========================

    st.markdown('<div class="section-title">Visualización de datos</div>', unsafe_allow_html=True)

    left, right = st.columns(2)

    with left:
        if "temperature" in df.columns:
            st.plotly_chart(
                make_line_chart(
                    df,
                    "temperature",
                    "Temperatura del ambiente",
                    "Temperatura °C"
                ),
                use_container_width=True
            )

    with right:
        if "humidity" in df.columns:
            st.plotly_chart(
                make_line_chart(
                    df,
                    "humidity",
                    "Humedad relativa",
                    "Humedad %"
                ),
                use_container_width=True
            )

    left2, right2 = st.columns(2)

    with left2:
        fig_motion = px.line(
            df,
            x="_time",
            y="movement_intensity",
            title="Intensidad de movimiento del módulo",
            labels={
                "_time": "Tiempo",
                "movement_intensity": "Intensidad de movimiento"
            },
            markers=True
        )
        fig_motion.update_layout(
            height=360,
            margin=dict(l=20, r=20, t=60, b=20),
            plot_bgcolor="white",
            paper_bgcolor="white",
            title_font=dict(size=20)
        )
        st.plotly_chart(fig_motion, use_container_width=True)

    with right2:
        if accel_cols:
            fig_accel = px.line(
                df,
                x="_time",
                y=accel_cols,
                title="Aceleración por eje",
                labels={
                    "_time": "Tiempo",
                    "value": "Aceleración",
                    "variable": "Eje"
                },
                markers=True
            )
            fig_accel.update_layout(
                height=360,
                margin=dict(l=20, r=20, t=60, b=20),
                plot_bgcolor="white",
                paper_bgcolor="white",
                title_font=dict(size=20)
            )
            st.plotly_chart(fig_accel, use_container_width=True)

    # =========================
    # INTERPRETACIÓN
    # =========================

    st.markdown('<div class="section-title">Interpretación del sistema</div>', unsafe_allow_html=True)

    st.markdown("""
    El tablero permite identificar si el invernadero mantiene condiciones ambientales adecuadas
    y si el módulo presenta movimientos anormales. La variable de movimiento no mide el crecimiento
    de las plantas, sino la estabilidad física del sistema: vibraciones, golpes, inclinaciones o manipulación.
    """)

    # =========================
    # TABLA
    # =========================

    with st.expander("Ver datos recientes"):
        st.dataframe(df.tail(50), use_container_width=True)

except Exception as e:
    st.error("No fue posible consultar InfluxDB.")
    st.code(str(e))
