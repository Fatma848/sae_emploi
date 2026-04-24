"""
Module Météo — Comparaison Paris vs Marseille
SAE Outils Décisionnels

Sources :
- API Open-Meteo Archive  : https://archive-api.open-meteo.com  (climat 1 an glissant)
- API Open-Meteo Forecast : https://api.open-meteo.com           (prévisions 7 jours)

⚠️ Données basées sur les 12 derniers mois glissants.
   Certains mois peuvent être partiels selon la date d'exécution.

Usage : from meteo_module import show_meteo
        show_meteo()

Dépendances :
    pip install requests pandas plotly streamlit
"""

import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# CONFIGURATION DES VILLES
# ─────────────────────────────────────────────
VILLES = {
    "Paris":     {"lat": 48.8566, "lon": 2.3522,  "color": "#1f77b4", "emoji": "🗼"},
    "Marseille": {"lat": 43.2965, "lon": 5.3698,  "color": "#d62728", "emoji": "⚓"},
}

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
# RÉCUPÉRATION DES DONNÉES
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_climat(lat, lon):
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
    resp = requests.get("https://archive-api.open-meteo.com/v1/archive", params=params)
    data = resp.json()["daily"]
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
def get_previsions(lat, lon):
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
    resp = requests.get("https://api.open-meteo.com/v1/forecast", params=params)
    data = resp.json()["daily"]
    df = pd.DataFrame({
        "date":       pd.to_datetime(data["time"]),
        "temp_max":   data["temperature_2m_max"],
        "temp_min":   data["temperature_2m_min"],
        "pluie":      data["precipitation_sum"],
        "prob_pluie": data["precipitation_probability_max"],
        "vent_max":   data["wind_speed_10m_max"],
        "weather_code": data["weather_code"],
    })
    return df


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


def mois_labels(men):
    return [MOIS_FR[m - 1] for m in men["mois"]]


# ─────────────────────────────────────────────
# ONGLET 1 — VUE GLOBALE
# ─────────────────────────────────────────────
def tab_vue_globale(df_paris, df_mars):
    st.subheader("Résumé climatique — 12 derniers mois")
    st.caption("⚠️ Données basées sur 365 jours glissants · Certains mois peuvent être partiels")

    # Calcul des deltas
    delta_temp   = df_mars["temp_moy"].mean()  - df_paris["temp_moy"].mean()
    delta_pluie  = df_paris["pluie"].sum()     - df_mars["pluie"].sum()
    delta_soleil = df_mars["ensoleillement"].mean() - df_paris["ensoleillement"].mean()
    delta_vent   = df_mars["vent_max"].mean()  - df_paris["vent_max"].mean()

    # ── KPIs en 2 colonnes Paris / Marseille ──
    col_titre, col_paris, col_mars = st.columns([1.2, 2, 2])
    col_titre.markdown("##### Indicateur")
    col_paris.markdown("##### 🗼 Paris")
    col_mars.markdown("##### ⚓ Marseille")

    kpis = [
        ("🌡️ Temp. moyenne",
         f'{df_paris["temp_moy"].mean():.1f} °C',
         f'{df_mars["temp_moy"].mean():.1f} °C',
         f"Marseille +{delta_temp:.1f}°C"),
        ("🔥 Temp. max moy.",
         f'{df_paris["temp_max"].mean():.1f} °C',
         f'{df_mars["temp_max"].mean():.1f} °C', None),
        ("❄️ Temp. min moy.",
         f'{df_paris["temp_min"].mean():.1f} °C',
         f'{df_mars["temp_min"].mean():.1f} °C', None),
        ("🌧️ Pluie totale",
         f'{df_paris["pluie"].sum():.0f} mm',
         f'{df_mars["pluie"].sum():.0f} mm',
         f"Paris +{delta_pluie:.0f} mm"),
        ("☀️ Ensoleillement moy.",
         f'{df_paris["ensoleillement"].mean():.1f} h/j',
         f'{df_mars["ensoleillement"].mean():.1f} h/j',
         f"Marseille +{delta_soleil:.1f} h/j"),
        ("💨 Vent max moy.",
         f'{df_paris["vent_max"].mean():.1f} km/h',
         f'{df_mars["vent_max"].mean():.1f} km/h',
         f"{'Marseille' if delta_vent > 0 else 'Paris'} +{abs(delta_vent):.1f} km/h"),
    ]

    for label, val_p, val_m, delta in kpis:
        c1, c2, c3 = st.columns([1.2, 2, 2])
        c1.markdown(f"**{label}**")
        c2.metric("", val_p)
        c3.metric("", val_m, delta=delta if delta else None)

    st.divider()

    # ── Graphique radar climatique ──
    st.markdown("#### 🕸️ Profil climatique comparé")

    categories = ["Temp. moy (°C)", "Pluie/mois (mm/10)", "Soleil (h/j)", "Vent max (km/h/10)"]
    vals_paris = [
        df_paris["temp_moy"].mean(),
        df_paris["pluie"].sum() / 12 / 10,
        df_paris["ensoleillement"].mean(),
        df_paris["vent_max"].mean() / 10,
    ]
    vals_mars = [
        df_mars["temp_moy"].mean(),
        df_mars["pluie"].sum() / 12 / 10,
        df_mars["ensoleillement"].mean(),
        df_mars["vent_max"].mean() / 10,
    ]

    fig_radar = go.Figure()
    for nom, vals, color in [("Paris", vals_paris, VILLES["Paris"]["color"]),
                              ("Marseille", vals_mars, VILLES["Marseille"]["color"])]:
        fig_radar.add_trace(go.Scatterpolar(
            r=vals + [vals[0]],
            theta=categories + [categories[0]],
            fill="toself", name=nom,
            line_color=color, opacity=0.7,
        ))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True)),
        height=380, legend_title="Ville",
    )
    st.plotly_chart(fig_radar, use_container_width=True)

    # ── Analyse ──
    st.markdown(f"""
> 👉 **Marseille est en moyenne {delta_temp:.1f}°C plus chaude** que Paris sur l'année,
> avec un ensoleillement **{delta_soleil:.1f} h/j supérieur**.
> Paris reçoit en revanche **{delta_pluie:.0f} mm de pluie supplémentaires** sur l'année.
> Ces différences s'expliquent par deux types de climat bien distincts :
> **climat océanique tempéré et humide à Paris** vs **climat méditerranéen chaud et sec à Marseille**.
    """)


# ─────────────────────────────────────────────
# ONGLET 2 — TEMPÉRATURES
# ─────────────────────────────────────────────
def tab_temperatures(df_paris, df_mars, men_paris, men_mars):
    st.subheader("Températures mensuelles")
    st.caption("⚠️ Moyennes calculées sur 365 jours glissants · Certains mois peuvent être partiels")

    # ── Courbe température moyenne (simplifié : 1 courbe / ville) ──
    st.markdown("#### 🌡️ Température moyenne mensuelle — Paris vs Marseille")

    fig_moy = go.Figure()
    for nom, men, cfg in [("Paris", men_paris, VILLES["Paris"]),
                           ("Marseille", men_mars, VILLES["Marseille"])]:
        fig_moy.add_trace(go.Scatter(
            x=mois_labels(men), y=men["temp_moy"].round(1),
            name=f"{cfg['emoji']} {nom}",
            mode="lines+markers",
            line=dict(color=cfg["color"], width=3),
            marker=dict(size=8),
        ))
    fig_moy.update_layout(
        yaxis_title="Température (°C)", height=380,
        legend_title="", hovermode="x unified",
    )
    st.plotly_chart(fig_moy, use_container_width=True)

    st.markdown("""
> 👉 **Marseille est plus chaude toute l'année**, avec un écart particulièrement marqué
> en été (jusqu'à +4°C en juillet-août). En hiver, l'écart se resserre mais reste
> favorable à Marseille. Paris présente des températures plus douces et homogènes
> tout au long de l'année, caractéristique du **climat océanique**.
    """)

    st.divider()

    # ── Courbe max / min séparée ──
    st.markdown("#### 🔥❄️ Températures max et min mensuelles")

    col_p, col_m = st.columns(2)

    for col, nom, men, cfg in [
        (col_p, "Paris",     men_paris, VILLES["Paris"]),
        (col_m, "Marseille", men_mars,  VILLES["Marseille"]),
    ]:
        with col:
            st.markdown(f"**{cfg['emoji']} {nom}**")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=mois_labels(men), y=men["temp_max"].round(1),
                name="Max", mode="lines+markers",
                line=dict(color="#e74c3c", width=2),
            ))
            fig.add_trace(go.Scatter(
                x=mois_labels(men), y=men["temp_min"].round(1),
                name="Min", mode="lines+markers",
                fill="tonexty", fillcolor="rgba(200,200,200,0.2)",
                line=dict(color="#3498db", width=2),
            ))
            fig.update_layout(
                yaxis_title="°C", height=300,
                legend_title="", hovermode="x unified",
                margin=dict(t=10),
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown(f"""
> 👉 **L'amplitude thermique** (écart max/min) est légèrement plus importante à Marseille,
> surtout en été, avec des nuits qui restent fraîches malgré des journées très chaudes.
> À Paris, les températures sont plus homogènes entre le jour et la nuit,
> reflétant l'influence maritime du **climat océanique**.
    """)

    st.divider()

    # ── KPIs températures ──
    st.markdown("#### 📊 Records et moyennes annuelles")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🗼 Temp. max absolue Paris",
                f"{df_paris['temp_max'].max():.1f} °C")
    col1.metric("⚓ Temp. max absolue Marseille",
                f"{df_mars['temp_max'].max():.1f} °C")
    col2.metric("🗼 Temp. min absolue Paris",
                f"{df_paris['temp_min'].min():.1f} °C")
    col2.metric("⚓ Temp. min absolue Marseille",
                f"{df_mars['temp_min'].min():.1f} °C")
    col3.metric("🗼 Jours > 25°C Paris",
                int((df_paris["temp_max"] > 25).sum()))
    col3.metric("⚓ Jours > 25°C Marseille",
                int((df_mars["temp_max"] > 25).sum()))
    col4.metric("🗼 Jours < 5°C Paris",
                int((df_paris["temp_min"] < 5).sum()))
    col4.metric("⚓ Jours < 5°C Marseille",
                int((df_mars["temp_min"] < 5).sum()))


# ─────────────────────────────────────────────
# ONGLET 3 — PRÉCIPITATIONS & SOLEIL
# ─────────────────────────────────────────────
def tab_pluie_soleil(df_paris, df_mars, men_paris, men_mars):
    st.subheader("Précipitations & Ensoleillement")
    st.caption("⚠️ Données sur 365 jours glissants · Certains mois peuvent être partiels")

    # ── KPIs pluie & soleil ──
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🗼 Pluie totale Paris",
                f"{df_paris['pluie'].sum():.0f} mm")
    col1.metric("⚓ Pluie totale Marseille",
                f"{df_mars['pluie'].sum():.0f} mm")
    col2.metric("🗼 Pluie / jour Paris",
                f"{df_paris['pluie'].mean():.1f} mm/j")
    col2.metric("⚓ Pluie / jour Marseille",
                f"{df_mars['pluie'].mean():.1f} mm/j")
    col3.metric("🗼 Soleil moy. Paris",
                f"{df_paris['ensoleillement'].mean():.1f} h/j")
    col3.metric("⚓ Soleil moy. Marseille",
                f"{df_mars['ensoleillement'].mean():.1f} h/j")
    col4.metric("🗼 Jours de pluie Paris",
                int((df_paris["pluie"] > 0).sum()))
    col4.metric("⚓ Jours de pluie Marseille",
                int((df_mars["pluie"] > 0).sum()))

    st.divider()

    # ── Bar chart précipitations ──
    st.markdown("#### 🌧️ Précipitations mensuelles (cumul)")
    fig_pluie = go.Figure()
    fig_pluie.add_trace(go.Bar(
        x=mois_labels(men_paris), y=men_paris["pluie"].round(1),
        name="🗼 Paris", marker_color=VILLES["Paris"]["color"], opacity=0.85,
    ))
    fig_pluie.add_trace(go.Bar(
        x=mois_labels(men_mars), y=men_mars["pluie"].round(1),
        name="⚓ Marseille", marker_color=VILLES["Marseille"]["color"], opacity=0.85,
    ))
    fig_pluie.update_layout(
        barmode="group", yaxis_title="Précipitations (mm)",
        height=360, legend_title="", hovermode="x unified",
    )
    st.plotly_chart(fig_pluie, use_container_width=True)

    st.markdown(f"""
> 👉 **Paris a des précipitations plus régulières** tout au long de l'année
> ({df_paris['pluie'].sum():.0f} mm/an), typiques du climat océanique.
> À Marseille ({df_mars['pluie'].sum():.0f} mm/an), les pluies sont **plus rares mais
> souvent plus intenses**, concentrées à l'automne (épisodes cévenols).
> L'été marseillais est **quasi sans pluie**, contrairement à Paris qui reçoit
> des précipitations modérées toute l'année.
    """)

    st.divider()

    # ── Bar chart ensoleillement ──
    st.markdown("#### ☀️ Ensoleillement moyen mensuel (heures/jour)")
    fig_sun = go.Figure()
    fig_sun.add_trace(go.Bar(
        x=mois_labels(men_paris), y=men_paris["ensoleillement"].round(1),
        name="🗼 Paris", marker_color=VILLES["Paris"]["color"], opacity=0.85,
    ))
    fig_sun.add_trace(go.Bar(
        x=mois_labels(men_mars), y=men_mars["ensoleillement"].round(1),
        name="⚓ Marseille", marker_color=VILLES["Marseille"]["color"], opacity=0.85,
    ))
    fig_sun.update_layout(
        barmode="group", yaxis_title="Heures de soleil / jour",
        height=360, legend_title="", hovermode="x unified",
    )
    st.plotly_chart(fig_sun, use_container_width=True)

    delta_soleil = df_mars["ensoleillement"].mean() - df_paris["ensoleillement"].mean()
    st.markdown(f"""
> 👉 **Marseille bénéficie d'un ensoleillement nettement supérieur** à Paris,
> avec en moyenne **+{delta_soleil:.1f} h/j** de soleil sur l'année.
> L'écart est maximal en été, où Marseille profite de **8 à 10 h/j** contre
> 6 à 7 h/j à Paris. En hiver, les deux villes se rapprochent mais
> Marseille reste avantagée. Cela fait de Marseille l'une des villes
> les plus ensoleillées de France métropolitaine.
    """)

    st.divider()

    # ── Vent ──
    st.markdown("#### 💨 Vent maximum mensuel moyen (km/h)")
    fig_vent = go.Figure()
    fig_vent.add_trace(go.Scatter(
        x=mois_labels(men_paris), y=men_paris["vent_max"].round(1),
        name="🗼 Paris", mode="lines+markers",
        line=dict(color=VILLES["Paris"]["color"], width=2),
    ))
    fig_vent.add_trace(go.Scatter(
        x=mois_labels(men_mars), y=men_mars["vent_max"].round(1),
        name="⚓ Marseille", mode="lines+markers",
        line=dict(color=VILLES["Marseille"]["color"], width=2),
    ))
    fig_vent.update_layout(
        yaxis_title="Vent max (km/h)", height=320,
        legend_title="", hovermode="x unified",
    )
    st.plotly_chart(fig_vent, use_container_width=True)

    st.markdown("""
> 👉 **Marseille est exposée au Mistral**, un vent froid et violent venant du nord-ouest,
> qui peut souffler à plus de 100 km/h en rafales. Il est particulièrement présent
> en hiver et au printemps. À Paris, les vents sont plus modérés et moins saisonniers.
    """)


# ─────────────────────────────────────────────
# ONGLET 4 — PRÉVISIONS 7 JOURS
# ─────────────────────────────────────────────
def tab_previsions(prev_paris, prev_mars):
    st.subheader("📅 Prévisions météo — 7 prochains jours")
    st.caption("Source : API Open-Meteo Forecast · Mise à jour toutes les 30 minutes")

    # ── Tableau comparatif ──
    st.markdown("#### 📋 Tableau des prévisions comparées")

    rows = []
    for _, r_p, r_m in zip(range(7), prev_paris.itertuples(), prev_mars.itertuples()):
        jour = r_p.date.strftime("%a %d %b")
        code_p = int(r_p.weather_code) if not pd.isna(r_p.weather_code) else 0
        code_m = int(r_m.weather_code) if not pd.isna(r_m.weather_code) else 0
        rows.append({
            "📅 Jour":              jour,
            "🗼 Météo Paris":       WMO_CODES.get(code_p, "—"),
            "🗼 T° Paris":          f"{r_p.temp_min:.0f}° → {r_p.temp_max:.0f}°C",
            "🗼 Pluie Paris":       f"{r_p.pluie:.1f} mm ({r_p.prob_pluie:.0f}%)",
            "⚓ Météo Marseille":   WMO_CODES.get(code_m, "—"),
            "⚓ T° Marseille":      f"{r_m.temp_min:.0f}° → {r_m.temp_max:.0f}°C",
            "⚓ Pluie Marseille":   f"{r_m.pluie:.1f} mm ({r_m.prob_pluie:.0f}%)",
        })

    df_prev = pd.DataFrame(rows)
    st.dataframe(df_prev, use_container_width=True, hide_index=True)

    st.divider()

    # ── Graphique températures prévues ──
    st.markdown("#### 🌡️ Températures prévues — Paris vs Marseille")
    fig_prev = go.Figure()
    jours = [r.date.strftime("%a %d") for r in prev_paris.itertuples()]

    for nom, prev, cfg in [("Paris", prev_paris, VILLES["Paris"]),
                            ("Marseille", prev_mars, VILLES["Marseille"])]:
        fig_prev.add_trace(go.Scatter(
            x=jours, y=prev["temp_max"],
            name=f"{cfg['emoji']} {nom} — Max",
            mode="lines+markers",
            line=dict(color=cfg["color"], dash="dash"),
        ))
        fig_prev.add_trace(go.Scatter(
            x=jours, y=prev["temp_min"],
            name=f"{cfg['emoji']} {nom} — Min",
            mode="lines+markers",
            fill="tonexty" if nom == "Marseille" else None,
            fillcolor="rgba(214,39,40,0.08)",
            line=dict(color=cfg["color"], dash="dot"),
        ))
    fig_prev.update_layout(
        yaxis_title="Température (°C)", height=380,
        legend_title="", hovermode="x unified",
    )
    st.plotly_chart(fig_prev, use_container_width=True)

    # ── Graphique pluie prévue ──
    st.markdown("#### 🌧️ Précipitations prévues + probabilité")
    fig_rain = go.Figure()
    for nom, prev, cfg in [("Paris", prev_paris, VILLES["Paris"]),
                            ("Marseille", prev_mars, VILLES["Marseille"])]:
        fig_rain.add_trace(go.Bar(
            x=jours, y=prev["pluie"],
            name=f"{cfg['emoji']} {nom} — Pluie (mm)",
            marker_color=cfg["color"], opacity=0.8,
        ))
        fig_rain.add_trace(go.Scatter(
            x=jours, y=prev["prob_pluie"],
            name=f"{cfg['emoji']} {nom} — Proba (%)",
            mode="lines+markers",
            line=dict(color=cfg["color"], dash="dot"),
            yaxis="y2",
        ))
    fig_rain.update_layout(
        barmode="group",
        yaxis=dict(title="Précipitations (mm)"),
        yaxis2=dict(title="Probabilité (%)", overlaying="y", side="right", range=[0, 100]),
        height=360, legend_title="", hovermode="x unified",
    )
    st.plotly_chart(fig_rain, use_container_width=True)


# ─────────────────────────────────────────────
# FONCTION PRINCIPALE
# ─────────────────────────────────────────────
def show_meteo():
    st.header("🌤️ Météo & Climat")
    st.caption("Source : API Open-Meteo (archive 1 an glissant + prévisions 7 jours) · Mise à jour automatique")

    with st.spinner("Chargement des données météo..."):
        df_paris = get_climat(VILLES["Paris"]["lat"],     VILLES["Paris"]["lon"])
        df_mars  = get_climat(VILLES["Marseille"]["lat"], VILLES["Marseille"]["lon"])
        prev_paris = get_previsions(VILLES["Paris"]["lat"],     VILLES["Paris"]["lon"])
        prev_mars  = get_previsions(VILLES["Marseille"]["lat"], VILLES["Marseille"]["lon"])

    men_paris = agr_mensuel(df_paris)
    men_mars  = agr_mensuel(df_mars)

    onglet1, onglet2, onglet3, onglet4 = st.tabs([
        "📊 Vue globale",
        "🌡️ Températures",
        "🌧️ Précipitations & Soleil",
        "📅 Prévisions 7 jours",
    ])

    with onglet1:
        tab_vue_globale(df_paris, df_mars)

    with onglet2:
        tab_temperatures(df_paris, df_mars, men_paris, men_mars)

    with onglet3:
        tab_pluie_soleil(df_paris, df_mars, men_paris, men_mars)

    with onglet4:
        tab_previsions(prev_paris, prev_mars)

    with st.expander("📚 Sources de données"):
        st.markdown("""
| Dataset | Description | Source |
|---|---|---|
| Archive météo (1 an) | Températures, précipitations, ensoleillement, vent | [Open-Meteo Archive API](https://open-meteo.com/en/docs/historical-weather-api) |
| Prévisions (7 jours) | Températures, précipitations, probabilité pluie, vent | [Open-Meteo Forecast API](https://open-meteo.com/en/docs) |

> Open-Meteo est gratuit pour usage non-commercial et ne nécessite pas de clé API.
        """)