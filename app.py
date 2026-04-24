import streamlit as st
from donnees_generales_module import show_donnees_generales
from logement_module import show_logement
from culture_module import show_culture
from emploi_module import show_emploi
from meteo_module import show_meteo
from transport_module import show_transport


st.set_page_config(page_title="Paris vs Marseille", layout="wide", page_icon="🏙️")

st.sidebar.title("🏙️ Navigation")
page = st.sidebar.radio("Choisir une page :", [
    "🏠 Accueil",
    "📊 Données générales",
    "💼 Emploi",
    "🏠 Logement",
    "🌤️ Météo",
    "🚇 Transport",
    "🎭 Culture",
])

if page == "🏠 Accueil":
    st.title("🏙️ Comparaison Paris vs Marseille")
    st.markdown("""
    Bienvenue sur notre application de comparaison entre **Paris** et **Marseille** !

    Navigue dans le menu à gauche pour explorer :
    - 📊 **Données générales** — population, densité, superficie
    - 💼 **Emploi** — chômage, actifs, évolution
    - 🏠 **Logement** — parc immobilier, évolution, carte
    - 🌤️ **Météo** — climat annuel et prévisions 7 jours
    - 🚇 **Transport** — réseau, lignes, perturbations
    - 🎭 **Culture** — lieux culturels, catégories, carte
    """)

elif page == "📊 Données générales":
    show_donnees_generales()

elif page == "💼 Emploi":
    show_emploi()

elif page == "🏠 Logement":
    show_logement()

elif page == "🌤️ Météo":
    show_meteo()

elif page == "🚇 Transport":
    show_transport()

elif page == "🎭 Culture":
    show_culture()