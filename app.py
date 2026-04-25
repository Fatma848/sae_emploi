"""
Application principale — Comparateur de villes françaises
SAE Outils Décisionnels

Lancement :
    streamlit run app.py

Prérequis :
    1. Placer les fichiers source dans data/
    2. Exécuter : python prepare_data.py
    3. Lancer l'app
"""

import streamlit as st
import pandas as pd
import os

# ─────────────────────────────────────────────
# CONFIG PAGE (doit être en premier)
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Comparateur de villes françaises",
    layout="wide",
    page_icon="🏙️",
)

# ─────────────────────────────────────────────
# CHARGEMENT COMMUNES
# ─────────────────────────────────────────────
CLEAN_DIR = os.path.join(os.path.dirname(__file__), "data", "clean")

@st.cache_data
def load_communes():
    path = os.path.join(CLEAN_DIR, "communes.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path, encoding="utf-8-sig")
    return df

df_communes = load_communes()

# ─────────────────────────────────────────────
# VÉRIFICATION DONNÉES
# ─────────────────────────────────────────────
if df_communes is None:
    st.error(
        "❌ Fichier `data/clean/communes.csv` introuvable.\n\n"
        "Exécute d'abord le script de préparation :\n```\npython prepare_data.py\n```"
    )
    st.stop()

villes_dispo = sorted(df_communes["nom_commune"].dropna().unique().tolist())

# ─────────────────────────────────────────────
# SESSION STATE — Villes sélectionnées
# ─────────────────────────────────────────────
if "ville1" not in st.session_state:
    st.session_state.ville1 = "Paris" if "Paris" in villes_dispo else villes_dispo[0]
if "ville2" not in st.session_state:
    st.session_state.ville2 = "Marseille" if "Marseille" in villes_dispo else villes_dispo[1]

# ─────────────────────────────────────────────
# SIDEBAR — Navigation + Sélecteur de villes
# ─────────────────────────────────────────────
with st.sidebar:
    st.title("🏙️ Comparateur")
    st.markdown("---")

    st.markdown("### 🔍 Choisir les villes")

    idx1 = villes_dispo.index(st.session_state.ville1) if st.session_state.ville1 in villes_dispo else 0
    idx2 = villes_dispo.index(st.session_state.ville2) if st.session_state.ville2 in villes_dispo else 1

    ville1 = st.selectbox(
        "🏙️ Ville 1",
        options=villes_dispo,
        index=idx1,
        key="select_v1",
    )
    ville2 = st.selectbox(
        "🏙️ Ville 2",
        options=villes_dispo,
        index=idx2,
        key="select_v2",
    )

    # Validation
    if ville1 == ville2:
        st.warning("⚠️ Choisissez deux villes différentes.")

    # Sauvegarder dans session_state
    st.session_state.ville1 = ville1
    st.session_state.ville2 = ville2

    st.markdown("---")
    st.markdown("### 📌 Navigation")

    page = st.radio("", [
        "🏠 Accueil",
        "📊 Données générales",
        "💼 Emploi",
        "🏠 Logement",
        "🌤️ Météo",
        "🎭 Culture",
        "📐 ACP",
    ])

    st.markdown("---")
    st.caption("SAE Outils Décisionnels · 2024-2025")

# ─────────────────────────────────────────────
# HELPER — Infos d'une ville
# ─────────────────────────────────────────────
def get_ville_info(nom):
    row = df_communes[df_communes["nom_commune"] == nom]
    if row.empty:
        return {}
    return row.iloc[0].to_dict()

v1_info = get_ville_info(ville1)
v2_info = get_ville_info(ville2)

# ─────────────────────────────────────────────
# PAGES
# ─────────────────────────────────────────────

# ── ACCUEIL ──────────────────────────────────
if page == "🏠 Accueil":
    st.title("🏙️ Comparateur de villes françaises")
    st.markdown(
        "Bienvenue ! Sélectionne **deux villes** dans le menu à gauche "
        "pour comparer leurs données sur plusieurs thématiques."
    )

    if ville1 != ville2:
        st.markdown(f"### Comparaison en cours : **{ville1}** vs **{ville2}**")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"#### 🔵 {ville1}")
            if v1_info:
                if "population"   in v1_info: st.metric("👥 Population",      f"{int(v1_info['population']):,}".replace(",", " "))
                if "departement"  in v1_info: st.metric("📍 Département",      str(v1_info["departement"]))
                if "latitude"     in v1_info: st.metric("🌐 Coordonnées",      f"{v1_info['latitude']:.4f}, {v1_info['longitude']:.4f}")

        with col2:
            st.markdown(f"#### 🔴 {ville2}")
            if v2_info:
                if "population"   in v2_info: st.metric("👥 Population",      f"{int(v2_info['population']):,}".replace(",", " "))
                if "departement"  in v2_info: st.metric("📍 Département",      str(v2_info["departement"]))
                if "latitude"     in v2_info: st.metric("🌐 Coordonnées",      f"{v2_info['latitude']:.4f}, {v2_info['longitude']:.4f}")

        st.divider()

    st.markdown("### 📂 Thématiques disponibles")
    cols = st.columns(3)
    thematiques = [
        ("📊", "Données générales", "Population, densité, superficie"),
        ("💼", "Emploi",           "Chômage, actifs, PCS"),
        ("🏠", "Logement",         "Parc immobilier, prix, évolution"),
        ("🌤️", "Météo",           "Climat annuel + prévisions 7j"),
        ("🎭", "Culture",          "Lieux culturels, catégories"),
        ("🗺️", "Carte",           "Localisation des deux villes"),
    ]
    for i, (emoji, titre, desc) in enumerate(thematiques):
        with cols[i % 3]:
            st.info(f"{emoji} **{titre}**\n\n{desc}")

    st.divider()
    st.markdown("### 🗺️ Localisation des deux villes")

    if v1_info.get("latitude") and v2_info.get("latitude"):
        import plotly.express as px

        map_df = pd.DataFrame([
            {
                "Ville": ville1,
                "lat": v1_info["latitude"],
                "lon": v1_info["longitude"],
                "population": int(v1_info.get("population", 0)),
            },
            {
                "Ville": ville2,
                "lat": v2_info["latitude"],
                "lon": v2_info["longitude"],
                "population": int(v2_info.get("population", 0)),
            },
        ])
        fig = px.scatter_mapbox(
            map_df,
            lat="lat", lon="lon",
            color="Ville",
            size="population",
            hover_name="Ville",
            hover_data={"population": True, "lat": False, "lon": False},
            color_discrete_sequence=["#1f77b4", "#d62728"],
            zoom=4.5,
            center={"lat": 46.6, "lon": 2.5},
            height=450,
        )
        fig.update_layout(mapbox_style="carto-positron", margin={"r":0,"t":0,"l":0,"b":0})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ℹ️ Coordonnées GPS non disponibles pour afficher la carte.")

# ── DONNÉES GÉNÉRALES ────────────────────────
elif page == "📊 Données générales":
    from donnees_generales_module import show_donnees_generales
    show_donnees_generales(ville1, ville2, v1_info, v2_info)

# ── EMPLOI ───────────────────────────────────
elif page == "💼 Emploi":
    from emploi_module import show_emploi
    show_emploi(ville1, ville2, v1_info, v2_info)

# ── LOGEMENT ─────────────────────────────────
elif page == "🏠 Logement":
    from logement_module import show_logement
    show_logement(ville1, ville2, v1_info, v2_info)

# ── MÉTÉO ─────────────────────────────────────
elif page == "🌤️ Météo":
    from meteo_module import show_meteo
    show_meteo(ville1, ville2, v1_info, v2_info)

# ── CULTURE ──────────────────────────────────
elif page == "🎭 Culture":
    from culture_module import show_culture
    show_culture(ville1, ville2, v1_info, v2_info)

# ── ACP ───────────────────────────────────────
elif page == "📐 ACP":
    from acp_module import show_acp
    show_acp(ville1, ville2, v1_info, v2_info)