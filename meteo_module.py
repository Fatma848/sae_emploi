"""
Module Météo — Comparateur de villes françaises
SAE Outils Décisionnels

Source : API Open-Meteo (gratuit, sans clé API)
         Fonctionne pour N'IMPORTE QUELLE ville avec coordonnées GPS.

Usage : from modules.meteo_module import show_meteo
        show_meteo(ville1, ville2, v1_info, v2_info)
"""

import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

COLOR_V1 = "#1f77b4"
COLOR_V2 = "#d62728"

WMO_CODES = {
    0:  "☀️ Ciel dégagé",        1: "🌤️ Principalement dégagé",
    2:  "⛅ Partiellement nuageux", 3: "☁️ Couvert",
    45: "🌫️ Brouillard",          48: "🌫️ Brouillard givrant",
    51: "🌦️ Bruine légère",       53: "🌦️ Bruine modérée",
    55: "🌦️ Bruine dense",        61: "🌧️ Pluie légère",
    63: "🌧️ Pluie modérée",       65: "🌧️ Pluie forte",
    71: "🌨️ Neige légère",        73: "🌨️ Neige modérée",
    75: "🌨️ Neige forte",         80: "🌦️ Averses légères",
    81: "🌦️ Averses modérées",    82: "⛈️ Averses violentes",
    95: "⛈️ Orage",               96: "⛈️ Orage avec grêle",
    99: "⛈️ Orage avec grêle forte",
}

MOIS_FR = ["Jan", "Fév", "Mar", "Avr", "Mai", "Jun",
           "Jul", "Aoû", "Sep", "Oct", "Nov", "Déc"]


# ─────────────────────────────────────────────
# RÉCUPÉRATION API
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_climat(lat, lon, nom_ville):
    end_date   = datetime.today().strftime("%Y-%m-%d")
    start_date = (datetime.today() - timedelta(days=365)).strftime("%Y-%m-%d")
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": start_date, "end_date": end_date,
        "daily": [
            "temperature_2m_mean", "temperature_2m_max", "temperature_2m_min",
            "precipitation_sum", "precipitation_hours",
            "wind_speed_10m_max", "sunshine_duration", "weather_code",
        ],
        "timezone": "auto",
    }
    try:
        resp = requests.get("https://archive-api.open-meteo.com/v1/archive",
                            params=params, timeout=10)
        data = resp.json()["daily"]
    except Exception as e:
        return None

    df = pd.DataFrame({
        "date":           pd.to_datetime(data["time"]),
        "temp_moy":       data["temperature_2m_mean"],
        "temp_max":       data["temperature_2m_max"],
        "temp_min":       data["temperature_2m_min"],
        "pluie":          data["precipitation_sum"],
        "heures_pluie":   data["precipitation_hours"],
        "vent_max":       data["wind_speed_10m_max"],
        "ensoleillement": [s / 3600 if s else 0 for s in data["sunshine_duration"]],
        "weather_code":   data["weather_code"],
    })
    return df


@st.cache_data(ttl=1800)
def get_previsions(lat, lon, nom_ville):
    params = {
        "latitude": lat, "longitude": lon,
        "daily": [
            "temperature_2m_max", "temperature_2m_min",
            "precipitation_sum", "precipitation_probability_max",
            "weather_code", "wind_speed_10m_max",
        ],
        "timezone": "auto",
        "forecast_days": 7,
    }
    try:
        resp = requests.get("https://api.open-meteo.com/v1/forecast",
                            params=params, timeout=10)
        data = resp.json()["daily"]
    except Exception:
        return None

    return pd.DataFrame({
        "date":       pd.to_datetime(data["time"]),
        "temp_max":   data["temperature_2m_max"],
        "temp_min":   data["temperature_2m_min"],
        "pluie":      data["precipitation_sum"],
        "prob_pluie": data["precipitation_probability_max"],
        "vent_max":   data["wind_speed_10m_max"],
        "weather_code": data["weather_code"],
    })


def agr_mensuel(df):
    df = df.copy()
    df["mois"] = df["date"].dt.month
    return df.groupby("mois").agg(
        temp_moy       =("temp_moy",       "mean"),
        temp_max       =("temp_max",       "mean"),
        temp_min       =("temp_min",       "mean"),
        pluie          =("pluie",          "sum"),
        heures_pluie   =("heures_pluie",   "sum"),
        vent_max       =("vent_max",       "mean"),
        ensoleillement =("ensoleillement", "mean"),
    ).reset_index()


def ml(men):
    return [MOIS_FR[m - 1] for m in men["mois"]]


# ─────────────────────────────────────────────
# ONGLET 1 — VUE GLOBALE
# ─────────────────────────────────────────────
def tab_vue_globale(ville1, ville2, df1, df2):
    st.subheader("Résumé climatique — 12 derniers mois")
    st.caption("⚠️ Données sur 365 jours glissants · Certains mois peuvent être partiels")

    delta_temp   = df2["temp_moy"].mean()       - df1["temp_moy"].mean()
    delta_pluie  = df1["pluie"].sum()           - df2["pluie"].sum()
    delta_soleil = df2["ensoleillement"].mean() - df1["ensoleillement"].mean()

    col_lbl, col_v1, col_v2 = st.columns([1.5, 2, 2])
    col_lbl.markdown("**Indicateur**")
    col_v1.markdown(f"**🔵 {ville1}**")
    col_v2.markdown(f"**🔴 {ville2}**")

    kpis = [
        ("🌡️ Temp. moyenne",
         f'{df1["temp_moy"].mean():.1f} °C',
         f'{df2["temp_moy"].mean():.1f} °C',
         f"{ville2} {delta_temp:+.1f}°C"),
        ("🔥 Temp. max moy.",
         f'{df1["temp_max"].mean():.1f} °C',
         f'{df2["temp_max"].mean():.1f} °C', None),
        ("❄️ Temp. min moy.",
         f'{df1["temp_min"].mean():.1f} °C',
         f'{df2["temp_min"].mean():.1f} °C', None),
        ("🌧️ Pluie totale",
         f'{df1["pluie"].sum():.0f} mm',
         f'{df2["pluie"].sum():.0f} mm',
         f"{ville1} +{delta_pluie:.0f} mm" if delta_pluie > 0 else f"{ville2} +{-delta_pluie:.0f} mm"),
        ("☀️ Ensoleillement moy.",
         f'{df1["ensoleillement"].mean():.1f} h/j',
         f'{df2["ensoleillement"].mean():.1f} h/j',
         f"{ville2} +{delta_soleil:.1f} h/j" if delta_soleil > 0 else f"{ville1} +{-delta_soleil:.1f} h/j"),
        ("💨 Vent max moy.",
         f'{df1["vent_max"].mean():.1f} km/h',
         f'{df2["vent_max"].mean():.1f} km/h', None),
    ]

    for label, v1, v2, delta in kpis:
        c1, c2, c3 = st.columns([1.5, 2, 2])
        c1.markdown(f"**{label}**")
        c2.metric("", v1)
        c3.metric("", v2, delta=delta)

    st.divider()

    # Radar climatique
    st.markdown("#### 🕸️ Profil climatique comparé")
    cats = ["Temp. moy (°C)", "Pluie/mois (mm/10)", "Soleil (h/j)", "Vent max (km/h/10)"]
    for nom, df, color in [(ville1, df1, COLOR_V1), (ville2, df2, COLOR_V2)]:
        vals = [
            df["temp_moy"].mean(),
            df["pluie"].sum() / 12 / 10,
            df["ensoleillement"].mean(),
            df["vent_max"].mean() / 10,
        ]

    fig_r = go.Figure()
    for nom, df, color in [(ville1, df1, COLOR_V1), (ville2, df2, COLOR_V2)]:
        vals = [
            df["temp_moy"].mean(),
            df["pluie"].sum() / 12 / 10,
            df["ensoleillement"].mean(),
            df["vent_max"].mean() / 10,
        ]
        fig_r.add_trace(go.Scatterpolar(
            r=vals + [vals[0]], theta=cats + [cats[0]],
            fill="toself", name=nom,
            line_color=color, opacity=0.7,
        ))
    fig_r.update_layout(
        polar=dict(radialaxis=dict(visible=True)),
        height=380, legend_title="",
    )
    st.plotly_chart(fig_r, use_container_width=True)

    plus_chaud = ville2 if delta_temp > 0 else ville1
    plus_pluie = ville1 if delta_pluie > 0 else ville2
    st.markdown(
        f"> 👉 **{plus_chaud}** est en moyenne **{abs(delta_temp):.1f}°C plus chaude** que {ville2 if plus_chaud == ville1 else ville1}. "
        f"**{plus_pluie}** reçoit davantage de précipitations sur l'année."
    )


# ─────────────────────────────────────────────
# ONGLET 2 — TEMPÉRATURES
# ─────────────────────────────────────────────
def tab_temperatures(ville1, ville2, df1, df2, men1, men2):
    st.subheader("Températures mensuelles")

    # Courbe moyenne simplifiée
    st.markdown("#### 🌡️ Température moyenne mensuelle")
    fig = go.Figure()
    for nom, men, color in [(ville1, men1, COLOR_V1), (ville2, men2, COLOR_V2)]:
        fig.add_trace(go.Scatter(
            x=ml(men), y=men["temp_moy"].round(1),
            name=nom, mode="lines+markers",
            line=dict(color=color, width=3), marker=dict(size=8),
        ))
    fig.update_layout(yaxis_title="Température (°C)", height=380,
                      legend_title="", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Max/Min séparés
    st.markdown("#### 🔥❄️ Max et Min mensuels")
    col_v1, col_v2 = st.columns(2)
    for col, nom, men, color in [
        (col_v1, ville1, men1, COLOR_V1),
        (col_v2, ville2, men2, COLOR_V2),
    ]:
        with col:
            st.markdown(f"**{'🔵' if color == COLOR_V1 else '🔴'} {nom}**")
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=ml(men), y=men["temp_max"].round(1),
                                      name="Max", mode="lines+markers",
                                      line=dict(color="#e74c3c", width=2)))
            fig2.add_trace(go.Scatter(x=ml(men), y=men["temp_min"].round(1),
                                      name="Min", mode="lines+markers",
                                      fill="tonexty", fillcolor="rgba(200,200,200,0.2)",
                                      line=dict(color="#3498db", width=2)))
            fig2.update_layout(yaxis_title="°C", height=300,
                               legend_title="", hovermode="x unified", margin=dict(t=10))
            st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # KPIs records
    st.markdown("#### 📊 Records annuels")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(f"🔵 Max absolu {ville1}", f"{df1['temp_max'].max():.1f} °C")
    col1.metric(f"🔴 Max absolu {ville2}", f"{df2['temp_max'].max():.1f} °C")
    col2.metric(f"🔵 Min absolu {ville1}", f"{df1['temp_min'].min():.1f} °C")
    col2.metric(f"🔴 Min absolu {ville2}", f"{df2['temp_min'].min():.1f} °C")
    col3.metric(f"🔵 Jours > 25°C {ville1}", int((df1["temp_max"] > 25).sum()))
    col3.metric(f"🔴 Jours > 25°C {ville2}", int((df2["temp_max"] > 25).sum()))
    col4.metric(f"🔵 Jours < 5°C {ville1}", int((df1["temp_min"] < 5).sum()))
    col4.metric(f"🔴 Jours < 5°C {ville2}", int((df2["temp_min"] < 5).sum()))


# ─────────────────────────────────────────────
# ONGLET 3 — PRÉCIPITATIONS & SOLEIL
# ─────────────────────────────────────────────
def tab_pluie_soleil(ville1, ville2, df1, df2, men1, men2):
    st.subheader("Précipitations & Ensoleillement")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(f"🔵 Pluie {ville1}", f"{df1['pluie'].sum():.0f} mm")
    col1.metric(f"🔴 Pluie {ville2}", f"{df2['pluie'].sum():.0f} mm")
    col2.metric(f"🔵 Pluie/j {ville1}", f"{df1['pluie'].mean():.1f} mm")
    col2.metric(f"🔴 Pluie/j {ville2}", f"{df2['pluie'].mean():.1f} mm")
    col3.metric(f"🔵 Soleil {ville1}", f"{df1['ensoleillement'].mean():.1f} h/j")
    col3.metric(f"🔴 Soleil {ville2}", f"{df2['ensoleillement'].mean():.1f} h/j")
    col4.metric(f"🔵 Jours pluie {ville1}", int((df1["pluie"] > 0).sum()))
    col4.metric(f"🔴 Jours pluie {ville2}", int((df2["pluie"] > 0).sum()))

    st.divider()

    # Bar pluie
    st.markdown("#### 🌧️ Précipitations mensuelles (cumul)")
    fig_p = go.Figure()
    fig_p.add_trace(go.Bar(x=ml(men1), y=men1["pluie"].round(1),
                            name=f"🔵 {ville1}", marker_color=COLOR_V1, opacity=0.85))
    fig_p.add_trace(go.Bar(x=ml(men2), y=men2["pluie"].round(1),
                            name=f"🔴 {ville2}", marker_color=COLOR_V2, opacity=0.85))
    fig_p.update_layout(barmode="group", yaxis_title="mm", height=350,
                        legend_title="", hovermode="x unified")
    st.plotly_chart(fig_p, use_container_width=True)

    st.divider()

    # Bar soleil
    st.markdown("#### ☀️ Ensoleillement mensuel moyen (h/j)")
    fig_s = go.Figure()
    fig_s.add_trace(go.Bar(x=ml(men1), y=men1["ensoleillement"].round(1),
                            name=f"🔵 {ville1}", marker_color=COLOR_V1, opacity=0.85))
    fig_s.add_trace(go.Bar(x=ml(men2), y=men2["ensoleillement"].round(1),
                            name=f"🔴 {ville2}", marker_color=COLOR_V2, opacity=0.85))
    fig_s.update_layout(barmode="group", yaxis_title="h/j", height=350,
                        legend_title="", hovermode="x unified")
    st.plotly_chart(fig_s, use_container_width=True)

    delta_s = df2["ensoleillement"].mean() - df1["ensoleillement"].mean()
    plus_sol = ville2 if delta_s > 0 else ville1
    st.markdown(
        f"> 👉 **{plus_sol}** bénéficie d'un ensoleillement plus important "
        f"(+{abs(delta_s):.1f} h/j en moyenne)."
    )


# ─────────────────────────────────────────────
# ONGLET 4 — PRÉVISIONS
# ─────────────────────────────────────────────
def tab_previsions(ville1, ville2, prev1, prev2):
    st.subheader("📅 Prévisions — 7 prochains jours")
    st.caption("Source : API Open-Meteo Forecast · Mise à jour toutes les 30 min")

    # Tableau comparatif
    rows = []
    for r1, r2 in zip(prev1.itertuples(), prev2.itertuples()):
        jour = r1.date.strftime("%a %d %b")
        c1 = int(r1.weather_code) if not pd.isna(r1.weather_code) else 0
        c2 = int(r2.weather_code) if not pd.isna(r2.weather_code) else 0
        rows.append({
            "📅 Jour":                 jour,
            f"🔵 Météo {ville1}":      WMO_CODES.get(c1, "—"),
            f"🔵 T° {ville1}":         f"{r1.temp_min:.0f}°→{r1.temp_max:.0f}°C",
            f"🔵 Pluie {ville1}":      f"{r1.pluie:.1f} mm ({r1.prob_pluie:.0f}%)",
            f"🔴 Météo {ville2}":      WMO_CODES.get(c2, "—"),
            f"🔴 T° {ville2}":         f"{r2.temp_min:.0f}°→{r2.temp_max:.0f}°C",
            f"🔴 Pluie {ville2}":      f"{r2.pluie:.1f} mm ({r2.prob_pluie:.0f}%)",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.divider()

    # Graphique températures prévues
    st.markdown("#### 🌡️ Températures prévues")
    jours = [r.date.strftime("%a %d") for r in prev1.itertuples()]
    fig = go.Figure()
    for nom, prev, color in [(ville1, prev1, COLOR_V1), (ville2, prev2, COLOR_V2)]:
        fig.add_trace(go.Scatter(x=jours, y=prev["temp_max"],
                                  name=f"{nom} — Max", mode="lines+markers",
                                  line=dict(color=color, dash="dash")))
        fig.add_trace(go.Scatter(x=jours, y=prev["temp_min"],
                                  name=f"{nom} — Min", mode="lines+markers",
                                  line=dict(color=color, dash="dot")))
    fig.update_layout(yaxis_title="°C", height=380, legend_title="", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────
# FONCTION PRINCIPALE
# ─────────────────────────────────────────────
def show_meteo(ville1, ville2, v1_info, v2_info):
    st.header("🌤️ Météo & Climat")
    st.caption(
        f"Comparaison : **{ville1}** vs **{ville2}** · "
        "Source : API Open-Meteo · Gratuit, sans clé API"
    )

    lat1 = v1_info.get("latitude")
    lon1 = v1_info.get("longitude")
    lat2 = v2_info.get("latitude")
    lon2 = v2_info.get("longitude")

    if not lat1 or not lon1:
        st.error(f"❌ Coordonnées GPS manquantes pour **{ville1}**.")
        return
    if not lat2 or not lon2:
        st.error(f"❌ Coordonnées GPS manquantes pour **{ville2}**.")
        return

    with st.spinner("Chargement des données météo..."):
        df1 = get_climat(float(lat1), float(lon1), ville1)
        df2 = get_climat(float(lat2), float(lon2), ville2)
        pr1 = get_previsions(float(lat1), float(lon1), ville1)
        pr2 = get_previsions(float(lat2), float(lon2), ville2)

    if df1 is None or df2 is None:
        st.error("❌ Erreur lors du chargement des données météo. Vérifiez votre connexion internet.")
        return

    men1 = agr_mensuel(df1)
    men2 = agr_mensuel(df2)

    onglet1, onglet2, onglet3, onglet4 = st.tabs([
        "📊 Vue globale",
        "🌡️ Températures",
        "🌧️ Précipitations & Soleil",
        "📅 Prévisions 7 jours",
    ])

    with onglet1:
        tab_vue_globale(ville1, ville2, df1, df2)
    with onglet2:
        tab_temperatures(ville1, ville2, df1, df2, men1, men2)
    with onglet3:
        tab_pluie_soleil(ville1, ville2, df1, df2, men1, men2)
    with onglet4:
        if pr1 is not None and pr2 is not None:
            tab_previsions(ville1, ville2, pr1, pr2)
        else:
            st.info("ℹ️ Prévisions non disponibles.")

    with st.expander("📚 Sources de données"):
        st.markdown("""
| Dataset | Description | Source |
|---|---|---|
| Archive météo (1 an) | Températures, précipitations, ensoleillement, vent | [Open-Meteo Archive API](https://open-meteo.com) |
| Prévisions (7 jours) | Températures, précipitations, probabilité pluie, vent | [Open-Meteo Forecast API](https://open-meteo.com) |
        """)