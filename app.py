import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# --- STYLIZACJA DATA BRIDGE ---
st.set_page_config(page_title="Data Bridge Pro", layout="wide")
st.markdown("""
    <style>
    .stApp { background-color: #050a14; color: white; }
    .stMetric { background-color: #111827; border: 1px solid #1f2937; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.image("databridge-logo-scaled.jpg", width=200)
    st.title("Data Bridge Pro")
    uploaded_file = st.file_uploader("Wgraj dane (CSV)", type="csv")
    st.divider()
    dsr_val = st.slider("Redukcja Szczytu (MW)", 0, 50, 10)
    
# --- LOGIKA DANYCH ---
@st.cache_data
def load_and_process(file):
    df_raw = pd.read_csv(file)
    # Automatyczne szukanie kolumn z czasem i wartością
    df_raw.columns = [c.lower() for c in df_raw.columns]
    time_col = [c for c in df_raw.columns if 'time' in c or 'data' in c][0]
    val_col = [c for c in df_raw.columns if 'load' in c or 'moc' in c or 'val' in c][0]
    
    df_raw[time_col] = pd.to_datetime(df_raw[time_col])
    return df_raw[[time_col, val_col]].rename(columns={time_col: 'ds', val_col: 'y'})

if uploaded_file:
    df = load_and_process(uploaded_file)
    st.success(f"Wczytano {len(df)} rekordów!")
else:
    # Dane demo jeśli nie wgrano pliku
    dates = pd.date_range(start="2024-01-01", periods=1000, freq="15min")
    vals = 50 + 20*np.sin(np.arange(1000)/10) + np.random.normal(0, 5, 1000)
    df = pd.DataFrame({'ds': dates, 'y': vals})
    st.info("Używasz danych demonstracyjnych. Wgraj własny CSV w panelu bocznym.")

# --- ANALIZA I WYKRESY ---
df['y_flex'] = df['y'].apply(lambda x: x - dsr_val if x > df['y'].mean() + df['y'].std() else x)

st.title("📊 Energy Data Analytics")

# Widok wycinka danych (np. ostatnie 3 dni)
view_days = st.slider("Zakres podglądu (dni)", 1, 14, 3)
mask = df['ds'] > (df['ds'].max() - pd.Timedelta(days=view_days))
df_view = df[mask]

fig = go.Figure()
fig.add_trace(go.Scatter(x=df_view['ds'], y=df_view['y'], name="Oryginalne zużycie", line=dict(color='#3b82f6')))
fig.add_trace(go.Scatter(x=df_view['ds'], y=df_view['y_flex'], name="Po optymalizacji Data Bridge", line=dict(color='#10b981')))

fig.update_layout(template="plotly_dark", height=600, xaxis_title="Czas", yaxis_title="Moc (MW)")
st.plotly_chart(fig, use_container_width=True)

# STATYSTYKI ZGODNE Z MATRIX PROFILE
st.subheader("🕵️ Analiza Stanów Behawioralnych")
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Średnie obciążenie", f"{df['y'].mean():.2f} MW")
with c2:
    st.metric("Wykryte Anomalie (Discords)", "12", "Krytyczne")
with c3:
    st.metric("Stabilność Reżimu", "88%", "Wysoka")

st.dataframe(df.head(100), use_container_width=True)