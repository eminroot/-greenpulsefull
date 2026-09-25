"""
Layer 7: Streamlit Demo Dashboard
----------------------------------------------------------------
Münsiflərlə üz-üzə olan interfeys. Hesabatın semifinal üçün tələb etdiyi
hər bir elementi tətbiq edir:
    - Edge AI resurs/gecikmə monitoru (Inference Time, CPU, RAM)
    - Manual sensor sliderlər (münsif istənilən ssenarini canlı simulyasiya edə bilər)
    - GPSS risk göstəricisi + aktuator ON/OFF status kartları
    - Risk-tarixçəsi qrafiki, st.session_state-də saxlanılır (SQLite YOXDUR —
      bu, hesabatdakı "Layer 9 (SQLite) Lazımsızlığı" tapıntısına birbaşa cavabdır).

İşə salmaq üçün:
    streamlit run app.py
"""

import time
import cv2
import numpy as np
import pandas as pd
import streamlit as st

from pipeline import GreenPulsePipeline
from hal import SensorReading

st.set_page_config(page_title="GreenPulse — Proactive Greenhouse AI", layout="wide")


@st.cache_resource
def load_pipeline(weights_path: str, device: str):
    return GreenPulsePipeline(weights_path=weights_path, device=device)


# ---------- session state ----------
if "history" not in st.session_state:
    st.session_state.history = []  # əvvəlki nəticələrin siyahısı (dict + timestamp)


# ---------- sidebar: konfiqurasiya ----------
st.sidebar.title("⚙️ GreenPulse Config")
weights_path = st.sidebar.text_input("YOLOv11n-Seg çəki faylı yolu", value="models/yolo11n-seg.pt")
device = st.sidebar.selectbox("Inference cihazı", ["cpu", "cuda:0"], index=0)

st.sidebar.markdown("---")
st.sidebar.subheader("🌱 Sensor Girişi")
sensor_mode = st.sidebar.radio("Sensor mənbəyi", ["Manual (münsif sliderləri)", "Simulyasiya ssenarisi"])

if sensor_mode == "Manual (münsif sliderləri)":
    soil_moisture = st.sidebar.slider("Torpaq nəmliyi (%)", 0, 100, 50)
    temperature = st.sidebar.slider("Temperatur (°C)", -5, 45, 24)
    humidity = st.sidebar.slider("Rütubət (%)", 0, 100, 60)
    light = st.sidebar.slider("İşıq (lux)", 0, 1500, 500)
    manual_reading = SensorReading(soil_moisture, temperature, humidity, light)
    scenario = None
else:
    scenario = st.sidebar.selectbox("Ssenari", ["normal", "drought", "heat", "low_light"])
    manual_reading = None

st.sidebar.markdown("---")
st.sidebar.caption("Edge cihaz hədəfi: Raspberry Pi 4 / NVIDIA Jetson Nano")


# ---------- əsas görünüş ----------
st.title("🌿 GreenPulse — Proaktif Otonom Sera Sistemi")
st.caption("Biyo-Sinyal Analizli Stress Detection · YOLOv11n-Seg · GPSS Engine · Edge AI")

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("📷 Yarpaq Şəkli")
    img_source = st.radio("Şəkil mənbəyi", ["Yüklə", "Kamera"], horizontal=True)
    uploaded_image = None
    if img_source == "Yüklə":
        uploaded_file = st.file_uploader("Yarpaq şəklini yükləyin", type=["jpg", "jpeg", "png"])
        if uploaded_file is not None:
            file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
            uploaded_image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    else:
        camera_file = st.camera_input("Yarpaq şəklini çəkin")
        if camera_file is not None:
            file_bytes = np.asarray(bytearray(camera_file.read()), dtype=np.uint8)
            uploaded_image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    if uploaded_image is not None:
        st.image(cv2.cvtColor(uploaded_image, cv2.COLOR_BGR2RGB), caption="Giriş şəkli", use_container_width=True)

    run_clicked = st.button("▶ GreenPulse Pipeline-ı İşə Sal", type="primary", disabled=uploaded_image is None)

with col_right:
    st.subheader("📊 Nəticə")
    st.empty()

if run_clicked and uploaded_image is not None:
    try:
        pipeline = load_pipeline(weights_path, device)
    except Exception as e:
        st.error(f"YOLOv11n-Seg çəkiləri yüklənmədi ('{weights_path}'): {e}")
        st.stop()

    with st.spinner("Layer 1→6 pipeline işə salınır..."):
        kwargs = {}
        if manual_reading is not None:
            kwargs["sensor_reading"] = manual_reading
        else:
            kwargs["sensor_mode"] = "simulated"
            kwargs["scenario"] = scenario
        result = pipeline.run(uploaded_image, **kwargs)

    result["_ts"] = time.strftime("%H:%M:%S")
    st.session_state.history.append(result)

    with col_right:
        risk_color = {"Low": "🟢", "Medium": "🟡", "High": "🟠", "Critical": "🔴"}[result["risk_level"]]

        m1, m2, m3 = st.columns(3)
        m1.metric("GPSS Score", f"{result['gpss_score']} / 100")
        m2.metric("Risk Səviyyəsi", f"{risk_color} {result['risk_level']}")
        m3.metric("Stress Tipi", result["stress_type"])

        m4, m5, m6 = st.columns(3)
        m4.metric("Qərar", result["decision"])
        m5.metric("Inference Vaxtı", f"{result['inference_latency_ms']} ms")
        m6.metric("Edge CPU İstifadəsi", f"{result['edge_cpu_usage_pct']} %")

        actuator = result["_meta"]["actuator"]
        if actuator != "NONE":
            st.success(f"🔧 Aktuator **{actuator}** → **ON**")
        else:
            st.info("🔧 Aktuator hərəkəti tələb olunmur")

        if result["_meta"]["notify_farmer"]:
            st.warning("📲 Fermerə bildiriş göndərildi (kritik risk səviyyəsi).")

        with st.expander("🔍 Tam pipeline JSON çıxışı"):
            st.json({k: v for k, v in result.items() if k != "_ts"})

        with st.expander("📡 Edge AI resurs & LoRaWAN diaqnostikası"):
            d1, d2 = st.columns(2)
            with d1:
                st.write("**Edge resursları**")
                st.write(f"- Inference gecikməsi: {result['inference_latency_ms']} ms")
                st.write(f"- Ümumi pipeline gecikməsi: {result['_meta']['total_pipeline_latency_ms']} ms")
                st.write(f"- CPU istifadəsi: {result['edge_cpu_usage_pct']} %")
                st.write(f"- RAM istifadəsi: {result['_meta']['edge_ram_usage_mb']} MB "
                         f"({result['_meta']['edge_ram_usage_pct']} %)")
            with d2:
                st.write("**LoRaWAN uplink (simulyasiya)**")
                lw = result["_meta"]["lorawan"]
                st.write(f"- Payload: `{lw['payload_hex']}` ({lw['payload_bytes']} bayt)")
                st.write(f"- Airtime: {lw['airtime_ms']} ms")
                st.write(f"- Şəbəkə gecikməsi: {lw['network_latency_ms']} ms")
                st.write(f"- Ümumi uplink gecikməsi: {lw['total_latency_ms']} ms")
                st.write(f"- RSSI / SNR: {lw['rssi_dbm']} dBm / {lw['snr_db']} dB")

# ---------- risk tarixçəsi (st.session_state — SQLite yoxdur) ----------
st.markdown("---")
st.subheader("📈 Risk Tarixçəsi (bu sessiya)")

if st.session_state.history:
    df = pd.DataFrame([{
        "vaxt": r["_ts"],
        "gpss_score": r["gpss_score"],
        "risk_level": r["risk_level"],
        "stress_type": r["stress_type"],
        "decision": r["decision"],
    } for r in st.session_state.history])

    chart_col, table_col = st.columns([2, 1])
    with chart_col:
        st.line_chart(df.set_index("vaxt")["gpss_score"])
    with table_col:
        st.dataframe(df[::-1], use_container_width=True, hide_index=True)

    if st.button("🗑 Tarixçəni Təmizlə"):
        st.session_state.history = []
        st.rerun()
else:
    st.caption("Hələ heç bir run yoxdur — şəkil yükləyin/çəkin və **GreenPulse Pipeline-ı İşə Sal** düyməsini basın.")
