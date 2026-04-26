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
    st.session_state.ville1 = None
if "ville2" not in st.session_state:
    st.session_state.ville2 = None

# ─────────────────────────────────────────────
# SIDEBAR — Navigation + Sélecteur de villes
# ─────────────────────────────────────────────
with st.sidebar:
    st.title("🏙️ Comparateur")
    st.markdown("---")

    st.markdown("### 🔍 Choisir les villes")

    options_avec_vide = ["— Choisir une ville —"] + villes_dispo

    idx1 = (villes_dispo.index(st.session_state.ville1) + 1
            if st.session_state.ville1 in villes_dispo else 0)
    idx2 = (villes_dispo.index(st.session_state.ville2) + 1
            if st.session_state.ville2 in villes_dispo else 0)

    sel1 = st.selectbox("🏙️ Ville 1", options=options_avec_vide, index=idx1, key="select_v1")
    sel2 = st.selectbox("🏙️ Ville 2", options=options_avec_vide, index=idx2, key="select_v2")

    ville1 = sel1 if sel1 != "— Choisir une ville —" else None
    ville2 = sel2 if sel2 != "— Choisir une ville —" else None

    # Validation
    if ville1 and ville2 and ville1 == ville2:
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
    if not nom:
        return {}
    row = df_communes[df_communes["nom_commune"] == nom]
    if row.empty:
        return {}
    return row.iloc[0].to_dict()

v1_info = get_ville_info(ville1)
v2_info = get_ville_info(ville2)

# ─────────────────────────────────────────────
# PAGES
# ─────────────────────────────────────────────

# ── GARDE FOU — villes non choisies ─────────
def check_villes():
    if not ville1 or not ville2:
        st.warning("👈 Sélectionne deux villes dans le menu à gauche pour afficher cette page.")
        return False
    if ville1 == ville2:
        st.warning("⚠️ Choisis deux villes différentes.")
        return False
    return True

# ── ACCUEIL ──────────────────────────────────
if page == "🏠 Accueil":
        # Message de bienvenue
    st.markdown("""
<div style="background: linear-gradient(135deg, #1f77b4, #2ca02c); padding: 2rem 2.5rem; border-radius: 12px; color: white; margin-bottom: 1.5rem;">
    <h2 style="color: white; margin: 0 0 0.5rem 0;">Bienvenue sur notre comparateur de villes françaises</h2>
    <p style="margin: 0 0 1rem 0; font-size: 1.05rem; opacity: 0.95;">
        Cette application vous permet de comparer deux villes françaises de plus de 20 000 habitants
        sur plusieurs thématiques : données générales, emploi, logement, météo, culture et analyse statistique.
        Sélectionnez vos deux villes dans le menu à gauche et explorez les différences !
    </p>
    <hr style="border-color: rgba(255,255,255,0.3); margin: 1rem 0;">
    <p style="margin: 0; font-size: 0.9rem; opacity: 0.85;">
        Application réalisée par <strong>Jana Laouchir</strong> et <strong>Fatma Ben Ltaief</strong> — SAE Outils Décisionnels
    </p>
</div>
    """, unsafe_allow_html=True)

    if not ville1 or not ville2:
        st.info("👈 Sélectionne deux villes dans le menu à gauche pour commencer la comparaison.")
    elif ville1 == ville2:
        st.warning("⚠️ Choisis deux villes différentes.")
    else:
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
    if check_villes():
        from donnees_generales_module import show_donnees_generales
        show_donnees_generales(ville1, ville2, v1_info, v2_info)

# ── EMPLOI ───────────────────────────────────
elif page == "💼 Emploi":
    if check_villes():
        from emploi_module import show_emploi
        show_emploi(ville1, ville2, v1_info, v2_info)

# ── LOGEMENT ─────────────────────────────────
elif page == "🏠 Logement":
    if check_villes():
        from logement_module import show_logement
        show_logement(ville1, ville2, v1_info, v2_info)

# ── MÉTÉO ─────────────────────────────────────
elif page == "🌤️ Météo":
    if check_villes():
        from meteo_module import show_meteo
        show_meteo(ville1, ville2, v1_info, v2_info)

# ── CULTURE ──────────────────────────────────
elif page == "🎭 Culture":
    if check_villes():
        from culture_module import show_culture
        show_culture(ville1, ville2, v1_info, v2_info)

# ── ACP ───────────────────────────────────────
elif page == "📐 ACP":
    if check_villes():
        from acp_module import show_acp
        show_acp(ville1, ville2, v1_info, v2_info)