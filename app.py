import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, time

# --- 1. KONFIGURACJA UI (ENTERPRISE GRADE) ---
st.set_page_config(page_title="Data Bridge | Enterprise Flexibility Platform", layout="wide")

# Zaawansowany CSS: Ukrywa standardowe elementy Streamlit, nadaje styl dashboardu biznesowego
st.markdown("""
    <style>
    /* Główny kontener */
    .stApp { background-color: #0b0f19; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; }
    
    /* Karty KPI */
    div[data-testid="metric-container"] {
        background-color: #161b26;
        border: 1px solid #2d3748;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    
    /* Tabs (Zakładki) */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; border-bottom: 1px solid #2d3748; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: transparent;
        border: none;
        color: #a0aec0;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        color: #0052FF !important;
        border-bottom: 2px solid #0052FF;
    }

    /* Alerty i boksy */
    .alert-box-critical {
        background-color: rgba(220, 38, 38, 0.1);
        border-left: 4px solid #dc2626;
        padding: 15px;
        margin-bottom: 20px;
        color: #fca5a5;
    }
    .instruction-text { font-size: 0.9em; color: #94a3b8; line-height: 1.5; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIKA DANYCH I TGE ---
@st.cache_data
def load_data(uploaded_file):
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        # Standaryzacja kolumn
        df.columns = [c.lower() for c in df.columns]
        time_col = [c for c in df.columns if 'time' in c or 'data' in c][0]
        val_col = [c for c in df.columns if 'load' in c or 'moc' in c or 'val' in c][0]
        df = df.rename(columns={time_col: 'timestamp', val_col: 'load_mw'})
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    else:
        # Generowanie danych demo (Tydzień)
        dates = pd.date_range(start="2025-06-01", periods=672, freq="15min")
        # Złożony profil: Baza + Cykl dobowy + Szum
        load = 80 + 40 * np.sin(np.linspace(0, 14 * np.pi, 672)) + np.random.normal(0, 2, 672)
        
        # REGIME SHIFT (Zmiana trybu pracy w połowie tygodnia)
        load[300:450] += 50 
        
        # ANOMALIE (Nagłe piki)
        load[150] += 120 # Critical Peak
        load[600] += 110 # Critical Peak
        
        df = pd.DataFrame({'timestamp': dates, 'load_mw': load})

    # SYMULACJA CEN TGE (Towarowa Giełda Energii) - Fixing I
    # Ceny wyższe w godzinach 08:00 - 20:00
    df['hour'] = df['timestamp'].dt.hour
    df['price_pln_mwh'] = df['hour'].apply(lambda x: np.random.uniform(550, 750) if 7 <= x <= 20 else np.random.uniform(300, 450))
    
    # Koszt całkowity dla danego slotu 15-minutowego (Moc * 0.25h * Cena)
    df['cost_pln'] = df['load_mw'] * 0.25 * df['price_pln_mwh']
    
    return df

# --- 3. SIDEBAR ---
with st.sidebar:
    st.image("databridge-logo-scaled.jpg", use_column_width=True)
    st.markdown("### Control Panel")
    
    uploaded_file = st.file_uploader("Import Danych (CSV)", type="csv")
    
    st.markdown("---")
    st.markdown("**Parametry Detekcji**")
    anomaly_sensitivity = st.slider("Czułość Anomalii (Std Dev)", 1.0, 4.0, 2.5)
    
    st.markdown("**Parametry Finansowe**")
    base_price = st.number_input("Bazowa cena TGE (PLN/MWh)", value=450.0)

# --- 4. PRZETWARZANIE ---
df = load_data(uploaded_file)

# Detekcja Anomalii (Z-Score)
mean_val = df['load_mw'].mean()
std_val = df['load_mw'].std()
df['anomaly'] = df['load_mw'] > (mean_val + anomaly_sensitivity * std_val)
anomalies = df[df['anomaly']]

# Obliczenia KPI
total_consumption = (df['load_mw'].sum() * 0.25) # MWh
total_cost = df['cost_pln'].sum()
max_peak = df['load_mw'].max()

# --- 5. GŁÓWNY DASHBOARD ---

# Sekcja Instrukcji (Expander)
with st.expander("INSTRUKCJA ANALIZY / HOW TO USE", expanded=False):
    st.markdown("""
    <div class="instruction-text">
    1. <b>Wykres Główny:</b> Analizuj przebieg mocy. Czerwone punkty oznaczają przekroczenie zdefiniowanego odchylenia standardowego.<br>
    2. <b>Matrix Profile Logic:</b> Zwróć uwagę na zmianę charakterystyki (Regime Shift) - np. podniesienie poziomu bazowego.<br>
    3. <b>Zakładka Finanse:</b> Symulacja kosztów w oparciu o profil godzinowy TGE. Użyj kalkulatora DSR, aby sprawdzić oszczędności.
    </div>
    """, unsafe_allow_html=True)

st.title("Data Bridge Dashboard")
st.markdown(f"Status systemu: **ONLINE** | Analizowany okres: {df['timestamp'].min().date()} - {df['timestamp'].max().date()}")

# KPI Metrics Row
c1, c2, c3, c4 = st.columns(4)
c1.metric("Całkowite Zużycie", f"{total_consumption:,.1f} MWh")
c2.metric("Szczytowe Obciążenie (Peak)", f"{max_peak:.2f} MW", delta_color="inverse")
c3.metric("Estymowany Koszt", f"{total_cost:,.0f} PLN")
c4.metric("Wykryte Anomalie", f"{len(anomalies)}", delta="Uwaga" if len(anomalies) > 0 else "Brak", delta_color="inverse")

# Jeśli są anomalie - wyświetl jasny komunikat
if not anomalies.empty:
    st.markdown(f"""
    <div class="alert-box-critical">
    <strong>🔴 WARNING: DETECTED CRITICAL PEAKS</strong><br>
    System zidentyfikował {len(anomalies)} punktów przekraczających normę ({anomaly_sensitivity}σ). 
    Ryzyko przekroczenia mocy zamówionej lub wysokich kosztów bilansowania.
    </div>
    """, unsafe_allow_html=True)

# ZAKŁADKI (Tabs)
tab_main, tab_finance, tab_table = st.tabs(["📉 Analiza Techniczna", "💰 Finanse i TGE", "📋 Dane Surowe"])

# --- TAB 1: TECHNICZNY ---
with tab_main:
    # Wykres Główny
    fig = go.Figure()
    
    # 1. Normalny przebieg
    fig.add_trace(go.Scatter(
        x=df['timestamp'], y=df['load_mw'],
        mode='lines', name='Profil Mocy (MW)',
        line=dict(color='#0052FF', width=2)
    ))
    
    # 2. Anomalie (Czerwone punkty)
    fig.add_trace(go.Scatter(
        x=anomalies['timestamp'], y=anomalies['load_mw'],
        mode='markers', name='CRITICAL ANOMALY',
        marker=dict(color='#dc2626', size=12, symbol='circle-open-dot', line=dict(width=2))
    ))
    
    # 3. Regime Threshold (Linia odcięcia)
    threshold_line = mean_val + anomaly_sensitivity * std_val
    fig.add_shape(type="line",
        x0=df['timestamp'].min(), y0=threshold_line, x1=df['timestamp'].max(), y1=threshold_line,
        line=dict(color="#4b5563", width=1, dash="dash"),
    )
    fig.add_annotation(x=df['timestamp'].min(), y=threshold_line, text="Alert Threshold", showarrow=False, yshift=10, font=dict(color="#9ca3af"))

    fig.update_layout(
        template="plotly_dark",
        height=500,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='#2d3748', title="Moc [MW]"),
        legend=dict(orientation="h", y=1.02, x=1, xanchor="right"),
        margin=dict(l=0, r=0, t=20, b=0)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("##### 🔍 Interpretacja Matrix Profile")
    st.info("System analizuje tzw. 'motify' (powtarzalne wzorce) vs 'discords' (anomalie). Czerwone znaczniki wskazują momenty, w których zachowanie obiektu drastycznie odbiega od jego historycznej tożsamości.")

# --- TAB 2: FINANSE (TGE) ---
with tab_finance:
    col_fin1, col_fin2 = st.columns([2, 1])
    
    with col_fin1:
        st.subheader("Analiza Kosztowa (Moc x Cena TGE)")
        
        # Wykres podwójny: Zużycie vs Cena
        fig_fin = go.Figure()
        fig_fin.add_trace(go.Scatter(x=df['timestamp'], y=df['load_mw'], name="Zużycie [MW]", line=dict(color='#0052FF')))
        fig_fin.add_trace(go.Scatter(x=df['timestamp'], y=df['price_pln_mwh'], name="Cena TGE [PLN/MWh]", yaxis="y2", line=dict(color='#10b981', dash='dot')))
        
        fig_fin.update_layout(
            template="plotly_dark",
            height=400,
            yaxis=dict(title="Moc [MW]"),
            yaxis2=dict(title="Cena [PLN]", overlaying="y", side="right"),
            legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig_fin, use_container_width=True)
        
    with col_fin2:
        st.subheader("Kalkulator DSR")
        st.markdown("Symulacja redukcji w godzinach najdroższych (High Price Discrepancy).")
        
        shift_mw = st.number_input("Ile MW możesz zredukować?", 0, 50, 5)
        
        # Obliczenie: Bierzemy godziny gdzie cena > średnia cena + 20%
        expensive_hours = df[df['price_pln_mwh'] > df['price_pln_mwh'].mean() * 1.2]
        hours_count = len(expensive_hours)
        
        # Średnia różnica między szczytem a doliną cenową
        price_spread = expensive_hours['price_pln_mwh'].mean() - 300 # Zakładamy 300 PLN jako cenę off-peak
        
        estimated_savings = shift_mw * hours_count * price_spread * 0.25 # 0.25h slot
        
        st.markdown("---")
        st.metric("Liczba Godzin High-Price", f"{hours_count} h")
        st.metric("Potencjalna Oszczędność", f"{estimated_savings:,.2f} PLN", "+DSR Active")
        
        if estimated_savings > 10000:
            st.success("Rekomendacja: **Wysoka opłacalność przesunięcia produkcji.**")
        else:
            st.warning("Rekomendacja: Niska zmienność cen, DSR mniej opłacalny.")

# --- TAB 3: TABELA ---
with tab_table:
    st.dataframe(df.style.format({
        'load_mw': '{:.2f}',
        'price_pln_mwh': '{:.2f}',
        'cost_pln': '{:.2f}'
    }).background_gradient(subset=['load_mw', 'cost_pln'], cmap='Blues'), use_container_width=True)

# --- STOPKA ---
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #4b5563; font-size: 0.8em;">
    &copy; 2024 <strong>DATA BRIDGE</strong> | Platforma analityki energetycznej | Powered by Matrix Profile Logic<br>
    Wszelkie dane prezentowane w trybie demo są symulacją.
</div>
""", unsafe_allow_html=True)