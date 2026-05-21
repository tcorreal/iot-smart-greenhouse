import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from influxdb_client import InfluxDBClient

st.set_page_config(
    page_title="Smart Greenhouse Lab",
    page_icon="🌿",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #07111f, #0b1728, #102235);
    color: white;
}
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 1500px;
}
.hero {
    background: linear-gradient(135deg, rgba(24,119,78,0.95), rgba(14,83,57,0.95));
    padding: 40px;
    border-radius: 28px;
    margin-bottom: 25px;
    border: 1px solid rgba(255,255,255,0.12);
    box-shadow: 0 8px 32px rgba(0,0,0,0.35);
}
.hero-title {
    font-size: 48px;
    font-weight: 800;
    color: white;
}
.hero-subtitle {
    font-size: 18px;
    color: rgba(255,255,255,0.88);
    line-height: 1.6;
}
.metric-card {
    background: rgba(255,255,255,0.06);
    border-radius: 22px;
    padding: 24px;
    border: 1px solid rgba(255,255,255,0.08);
    box-shadow: 0 8px 20px rgba(0,0,0,0.25);
}
.metric-title {
    color: rgba(255,255,255,0.72);
    font-size: 15px;
    margin-bottom: 10px;
}
.metric-value {
    font-size: 36px;
    font-weight: 800;
    color: white;
}
.section-title {
    font-size: 28px;
    font-weight: 750;
    color: white;
    margin-top: 32px;
    margin-bottom: 15px;
}
.info-card {
    background: rgba(255,255,255,0.055);
    padding: 22px;
    border-radius: 20px;
    border: 1px solid rgba(255,255,255,0.08);
    color: rgba(255,255,255,0.88);
    line-height: 1.6;
}
.alert-ok {
    background: rgba(25,135,84,0.18);
    border-left: 5px solid #22c55e;
    padding: 18px;
    border-radius: 16px;
    color: white;
    margin-bottom: 10px;
}
.alert-warning {
    background: rgba(255,193,7,0.16);
    border-left: 5px solid #ffc107;
    padding: 18px;
    border-radius: 16px;
    color: white;
    margin-bottom: 10px;
}
.alert-danger {
    background: rgba(220,53,69,0.18);
    border-left: 5px solid #dc3545;
    padding: 18px;
    border-radius: 16px;
    color: white;
    margin-bottom: 10px;
}
section[data-testid="stSidebar"] {
    background: #08131f;
}
section[data-testid="stSidebar"] * {
    color: white;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <div class="hero-title">🌿 Smart Greenhouse Lab</div>
    <div class="hero-subtitle">
        Sistema inteligente de monitoreo ambiental y estabilidad física para un invernadero experimental.
        Consulta datos desde InfluxDB y visualiza temperatura, humedad y vibraciones estructurales
        mediante una interfaz IoT clara, moderna y orientada a la toma de decisiones.
    </div>
</div>
""", unsafe_allow_html=True)

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

temp_high_limit = st.sidebar.slider("Temperatura alta °C", 25, 45, 30)
temp_low_limit = st.sidebar.slider("Temperatura baja °C", 5, 25, 18)
humidity_low_limit = st.sidebar.slider("Humedad baja %", 10, 80, 40)
humidity_high_limit = st.sidebar.slider("Humedad alta %", 50, 100, 80)
motion_limit = st.sidebar.slider("Movimiento/vibración", 5, 30, 15)

st.sidebar.markdown("---")
st.sidebar.markdown("""
**Lectura del sistema**

- Temperatura: condición térmica del cultivo.
- Humedad: estado ambiental del invernadero.
- Movimiento: vibraciones, golpes o manipulación física.
""")

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

def get_last_value(dataframe, column):
    if column in dataframe.columns and not dataframe[column].dropna().empty:
        return dataframe[column].dropna().iloc[-1]
    return None

def format_value(value, suffix="", decimals=1):
    if value is None:
        return "Sin dato"
    return f"{value:.{decimals}f}{suffix}"

def update_chart_layout(fig):
    fig.update_layout(
        height=360,
        margin=dict(l=20, r=20, t=60, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.03)",
        font=dict(color="white"),
        title_font=dict(size=20, color="white"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="white")),
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)", zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.08)", zeroline=False)
    )
    return fig

def make_line_chart(dataframe, y_column, title, y_label):
    fig = px.line(
        dataframe,
        x="_time",
        y=y_column,
        title=title,
        labels={"_time": "Tiempo", y_column: y_label},
        markers=True
    )
    return update_chart_layout(fig)

def make_gauge(value, title, max_value):
    if value is None:
        value = 0

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": title, "font": {"color": "white", "size": 18}},
        number={"font": {"color": "white", "size": 34}},
        gauge={
            "axis": {
                "range": [0, max_value],
                "tickcolor": "white",
                "tickfont": {"color": "white"}
            },
            "bar": {"color": "#22c55e"},
            "bgcolor": "rgba(255,255,255,0.04)",
            "borderwidth": 1,
            "bordercolor": "rgba(255,255,255,0.12)",
            "steps": [
                {"range": [0, max_value * 0.35], "color": "rgba(59,130,246,0.30)"},
                {"range": [max_value * 0.35, max_value * 0.70], "color": "rgba(34,197,94,0.28)"},
                {"range": [max_value * 0.70, max_value], "color": "rgba(239,68,68,0.30)"}
            ]
        }
    ))

    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "white"}
    )

    return fig

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

    st.markdown('<div class="section-title">Indicadores principales</div>', unsafe_allow_html=True)

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    with kpi1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🌡️ Temperatura actual</div>
            <div class="metric-value">{format_value(temperatura_actual, "°C", 1)}</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">💧 Humedad relativa</div>
            <div class="metric-value">{format_value(humedad_actual, "%", 1)}</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">📈 Movimiento/vibración</div>
            <div class="metric-value">{format_value(movimiento_actual, "", 2)}</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">📦 Registros consultados</div>
            <div class="metric-value">{len(df)}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="section-title">Estado operativo del invernadero</div>', unsafe_allow_html=True)

    alertas = []

    if temperatura_actual is not None:
        if temperatura_actual > temp_high_limit:
            alertas.append(("danger", "Temperatura alta: revisar ventilación, exposición solar o sistema de enfriamiento."))
        elif temperatura_actual < temp_low_limit:
            alertas.append(("warning", "Temperatura baja: revisar aislamiento térmico o condiciones externas."))

    if humedad_actual is not None:
        if humedad_actual < humidity_low_limit:
            alertas.append(("warning", "Humedad baja: revisar riego, nebulización o ventilación excesiva."))
        elif humedad_actual > humidity_high_limit:
            alertas.append(("warning", "Humedad alta: revisar ventilación, condensación o exceso de riego."))

    if movimiento_actual is not None and movimiento_actual > motion_limit:
        alertas.append(("danger", "Movimiento anormal: posible vibración, golpe, inclinación o manipulación física del módulo."))

    if not alertas:
        st.markdown(
            '<div class="alert-ok">✅ Estado normal: las variables se encuentran dentro de los rangos definidos para el monitoreo.</div>',
            unsafe_allow_html=True
        )
    else:
        for tipo, mensaje in alertas:
            css_class = "alert-danger" if tipo == "danger" else "alert-warning"
            st.markdown(f'<div class="{css_class}">⚠️ {mensaje}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">Lectura rápida del sistema</div>', unsafe_allow_html=True)

    g1, g2, g3 = st.columns(3)

    with g1:
        st.plotly_chart(make_gauge(temperatura_actual, "Temperatura °C", 50), use_container_width=True)

    with g2:
        st.plotly_chart(make_gauge(humedad_actual, "Humedad %", 100), use_container_width=True)

    with g3:
        st.plotly_chart(make_gauge(movimiento_actual, "Movimiento", 30), use_container_width=True)

    st.markdown('<div class="section-title">Tendencias temporales</div>', unsafe_allow_html=True)

    left, right = st.columns(2)

    with left:
        if "temperature" in df.columns:
            st.plotly_chart(
                make_line_chart(df, "temperature", "Temperatura del ambiente", "Temperatura °C"),
                use_container_width=True
            )

    with right:
        if "humidity" in df.columns:
            st.plotly_chart(
                make_line_chart(df, "humidity", "Humedad relativa", "Humedad %"),
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
        st.plotly_chart(update_chart_layout(fig_motion), use_container_width=True)

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
            st.plotly_chart(update_chart_layout(fig_accel), use_container_width=True)

    st.markdown('<div class="section-title">Interpretación del caso de uso</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="info-card">
    <b>Smart Greenhouse Lab</b> permite monitorear las condiciones ambientales y la estabilidad física
    de un invernadero experimental. La temperatura y la humedad permiten evaluar el confort ambiental
    del cultivo, mientras que la aceleración permite identificar vibraciones, golpes, inclinaciones o
    manipulación física del módulo. Esta lectura integrada facilita la supervisión temprana de eventos
    que podrían afectar el entorno de cultivo o la confiabilidad del experimento.
    </div>
    """, unsafe_allow_html=True)

    with st.expander("📋 Ver datos recientes desde InfluxDB"):
        st.dataframe(df.tail(50), use_container_width=True)

except Exception as e:
    st.error("No fue posible consultar InfluxDB.")
    st.code(str(e))
