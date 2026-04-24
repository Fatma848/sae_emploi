"""
Module Données Générales — Comparaison Paris vs Marseille
SAE Outils Décisionnels

Sources :
- Données générales : Donnees_Generales.xlsx (INSEE / Open Data)

Usage : from donnees_generales_module import show_donnees_generales
        show_donnees_generales()

Dépendances :
    pip install streamlit pandas plotly openpyxl
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os

# ─────────────────────────────────────────────
# CHEMINS
# ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(__file__)
PATH_GENERAL = os.path.join(BASE_DIR, "data", "Donnees_Generales.xlsx")

# ─────────────────────────────────────────────
# COULEURS
# ─────────────────────────────────────────────
COLOR_PARIS     = "#1f77b4"
COLOR_MARSEILLE = "#d62728"


# ─────────────────────────────────────────────
# CHARGEMENT DES DONNÉES
# ─────────────────────────────────────────────
@st.cache_data
def load_donnees_generales():
    df = pd.read_excel(PATH_GENERAL)
    paris     = df[df["nom_standard"] == "Paris"].iloc[0]
    marseille = df[df["nom_standard"] == "Marseille"].iloc[0]
    return paris, marseille, df


def fmt(n):
    return f"{int(n):,}".replace(",", "\u202f")


# ─────────────────────────────────────────────
# ONGLET 1 — CHIFFRES CLÉS
# ─────────────────────────────────────────────
def tab_kpis(paris, marseille):
    st.subheader("Indicateurs clés")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🗼 Population Paris",     fmt(paris["population"]))
        st.metric("⚓ Population Marseille", fmt(marseille["population"]),
                  delta=fmt(marseille["population"] - paris["population"]))

    with col2:
        st.metric("🗼 Densité Paris (hab/km²)",     fmt(paris["densite"]))
        st.metric("⚓ Densité Marseille (hab/km²)", fmt(marseille["densite"]),
                  delta=fmt(marseille["densite"] - paris["densite"]))

    with col3:
        st.metric("🗼 Superficie Paris (km²)",     f"{paris['superficie_km2']} km²")
        st.metric("⚓ Superficie Marseille (km²)", f"{marseille['superficie_km2']} km²",
                  delta=f"{marseille['superficie_km2'] - paris['superficie_km2']:.0f} km²")

    st.caption("➡️ Les deltas comparent Marseille à Paris.")
    st.divider()

    # Jauges densité
    fig_gauge = go.Figure()
    for i, (nom, val, color) in enumerate([
        ("Paris",     float(paris["densite"]),     COLOR_PARIS),
        ("Marseille", float(marseille["densite"]), COLOR_MARSEILLE),
    ]):
        fig_gauge.add_trace(go.Indicator(
            mode="gauge+number",
            value=val,
            title={"text": f"Densité — {nom}", "font": {"size": 14}},
            number={"suffix": " hab/km²"},
            gauge={
                "axis": {"range": [0, 25000]},
                "bar":  {"color": color},
                "steps": [
                    {"range": [0,     5000],  "color": "#d4edda"},
                    {"range": [5000,  15000], "color": "#fff3cd"},
                    {"range": [15000, 25000], "color": "#f8d7da"},
                ],
            },
            domain={"column": i, "row": 0},
        ))
    fig_gauge.update_layout(grid={"rows": 1, "columns": 2}, height=240, margin=dict(t=30, b=0))
    st.plotly_chart(fig_gauge, use_container_width=True)

    st.markdown(
        f"👉 **Paris est l'une des villes les plus denses d'Europe** avec "
        f"**{fmt(paris['densite'])} hab/km²**, soit **"
        f"{paris['densite'] / marseille['densite']:.1f}× plus dense que Marseille** "
        f"({fmt(marseille['densite'])} hab/km²). "
        f"Marseille, avec ses **{marseille['superficie_km2']} km²**, est en revanche "
        f"**{marseille['superficie_km2'] / paris['superficie_km2']:.1f}× plus étendue** "
        f"que Paris ({paris['superficie_km2']} km²)."
    )


# ─────────────────────────────────────────────
# ONGLET 2 — COMPARAISON VISUELLE
# ─────────────────────────────────────────────
def tab_comparaison(paris, marseille):
    st.subheader("Comparaison visuelle des indicateurs")

    df_plot = pd.DataFrame([
        {"Ville": "Paris",     "population": paris["population"],
         "densite": paris["densite"], "superficie_km2": paris["superficie_km2"]},
        {"Ville": "Marseille", "population": marseille["population"],
         "densite": marseille["densite"], "superficie_km2": marseille["superficie_km2"]},
    ])

    indicateur = st.selectbox(
        "Choisir un indicateur :",
        ["population", "densite", "superficie_km2"],
        format_func=lambda x: {
            "population":    "👥 Population",
            "densite":       "🏙️ Densité (hab/km²)",
            "superficie_km2": "📏 Superficie (km²)",
        }[x],
    )

    fig_bar = px.bar(
        df_plot, x="Ville", y=indicateur, color="Ville",
        color_discrete_map={"Paris": COLOR_PARIS, "Marseille": COLOR_MARSEILLE},
        text=indicateur,
        title=f"Comparaison — {indicateur}",
    )
    fig_bar.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig_bar.update_layout(height=400, showlegend=False, yaxis_title=indicateur)
    st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    # Camembert population
    st.markdown("#### 🥧 Répartition de la population")
    fig_pie = px.pie(
        df_plot, values="population", names="Ville",
        color="Ville",
        color_discrete_map={"Paris": COLOR_PARIS, "Marseille": COLOR_MARSEILLE},
    )
    fig_pie.update_traces(textinfo="percent+label")
    fig_pie.update_layout(height=350)
    st.plotly_chart(fig_pie, use_container_width=True)


# ─────────────────────────────────────────────
# ONGLET 3 — CARTE
# ─────────────────────────────────────────────
def tab_carte(paris, marseille):
    st.subheader("🗺️ Localisation des deux villes")

    map_data = pd.DataFrame({
        "Ville":      ["Paris",                  "Marseille"],
        "lat":        [48.8566,                  43.2965],
        "lon":        [2.3522,                   5.3698],
        "population": [int(paris["population"]), int(marseille["population"])],
        "densite":    [int(paris["densite"]),    int(marseille["densite"])],
        "superficie": [paris["superficie_km2"],  marseille["superficie_km2"]],
    })

    fig_map = px.scatter_mapbox(
        map_data,
        lat="lat", lon="lon",
        size="population",
        color="Ville",
        color_discrete_map={"Paris": COLOR_PARIS, "Marseille": COLOR_MARSEILLE},
        hover_name="Ville",
        hover_data={"population": True, "densite": True, "superficie": True,
                    "lat": False, "lon": False},
        zoom=4.5,
        center={"lat": 46.6, "lon": 2.5},
        height=500,
    )
    fig_map.update_layout(
        mapbox_style="carto-positron",
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
    )
    st.plotly_chart(fig_map, use_container_width=True)

    st.markdown(
        "👉 Paris est située au nord-centre de la France, Marseille au sud-est sur la Méditerranée. "
        "La taille des bulles est proportionnelle à la population."
    )


# ─────────────────────────────────────────────
# ONGLET 4 — ANALYSE
# ─────────────────────────────────────────────
def tab_analyse(paris, marseille):
    st.subheader("🧠 Analyse comparative")

    ratio_densite  = paris["densite"]     / marseille["densite"]
    ratio_superf   = marseille["superficie_km2"] / paris["superficie_km2"]
    ratio_pop      = paris["population"]  / marseille["population"]

    st.markdown(f"""
#### 👥 Population
Paris est **{ratio_pop:.1f}× plus peuplée** que Marseille
({fmt(paris['population'])} hab. contre {fmt(marseille['population'])} hab.).

#### 🏙️ Densité
Paris est **{ratio_densite:.1f}× plus dense** ({fmt(paris['densite'])} hab/km²
contre {fmt(marseille['densite'])} hab/km²). C'est l'une des densités urbaines
les plus élevées d'Europe, avec une forte pression sur le logement et les transports.

#### 📏 Superficie
Malgré sa population bien moindre, Marseille s'étend sur
**{marseille['superficie_km2']} km²**, soit **{ratio_superf:.1f}× plus grand** que Paris
({paris['superficie_km2']} km²). Cela s'explique par ses nombreux espaces naturels
(massif des Calanques, collines).

#### 📊 Conséquences
- Le logement est structurellement plus tendu à Paris (prix, surface, disponibilité).
- Les transports en commun sont essentiels à Paris du fait de la densité.
- Marseille dispose de plus d'espace par habitant mais présente des inégalités territoriales marquées.
    """)


# ─────────────────────────────────────────────
# FONCTION PRINCIPALE
# ─────────────────────────────────────────────
def show_donnees_generales():
    st.header("📊 Données générales")
    st.caption("Source : INSEE / Open Data · Fichier Donnees_Generales.xlsx")

    paris, marseille, _ = load_donnees_generales()

    onglet1, onglet2, onglet3, onglet4 = st.tabs([
        "🔑 Chiffres clés",
        "📊 Comparaison",
        "🗺️ Carte",
        "🧠 Analyse",
    ])

    with onglet1:
        tab_kpis(paris, marseille)

    with onglet2:
        tab_comparaison(paris, marseille)

    with onglet3:
        tab_carte(paris, marseille)

    with onglet4:
        tab_analyse(paris, marseille)

    with st.expander("📚 Sources de données"):
        st.markdown("""
| Dataset | Description | Source |
|---|---|---|
| Données générales | Population, densité, superficie | [INSEE](https://www.insee.fr) / Open Data |
        """)