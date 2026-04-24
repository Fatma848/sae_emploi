"""
Module Culture — Comparaison Paris vs Marseille
SAE Outils Décisionnels

Sources :
- Paris    : Culture_Paris.xlsx    (Open Data Paris)
- Marseille: Culture_Marseille.xlsx (Open Data Marseille / AMP)

Colonnes attendues :
  - "Categorie"   : type de lieu culturel
  - "Nom du site" : nom du lieu
  - "Latitude"    : coordonnée (float ou str avec virgule décimale)
  - "Longitude"   : coordonnée

Usage : from culture_module import show_culture
        show_culture()

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
BASE_DIR         = os.path.dirname(__file__)
PATH_CULT_PARIS  = os.path.join(BASE_DIR, "data", "Culture_Paris.xlsx")
PATH_CULT_MARS   = os.path.join(BASE_DIR, "data", "Culture_Marseille.xlsx")

# ─────────────────────────────────────────────
# COULEURS
# ─────────────────────────────────────────────
COLOR_PARIS     = "#1f77b4"
COLOR_MARSEILLE = "#d62728"


# ─────────────────────────────────────────────
# CHARGEMENT & NETTOYAGE
# ─────────────────────────────────────────────
@st.cache_data
def load_culture():
    df_paris = pd.read_excel(PATH_CULT_PARIS)
    df_mars  = pd.read_excel(PATH_CULT_MARS)

    df_paris["Ville"] = "Paris"
    df_mars["Ville"]  = "Marseille"

    df = pd.concat([df_paris, df_mars], ignore_index=True)

    # Nettoyage colonne Categorie
    if "Categorie" in df.columns:
        df["Categorie"] = df["Categorie"].astype(str).str.strip()

    # Nettoyage coordonnées
    for col in ["Latitude", "Longitude"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "."), errors="coerce"
            )

    return df, df_paris, df_mars


def fmt(n):
    return f"{int(n):,}".replace(",", "\u202f")


# ─────────────────────────────────────────────
# ONGLET 1 — CHIFFRES CLÉS
# ─────────────────────────────────────────────
def tab_kpis(df):
    st.subheader("Indicateurs clés — Offre culturelle")

    n_paris = len(df[df["Ville"] == "Paris"])
    n_mars  = len(df[df["Ville"] == "Marseille"])
    ratio   = n_paris / n_mars if n_mars > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("🗼 Lieux culturels Paris",     fmt(n_paris))
    col2.metric("⚓ Lieux culturels Marseille", fmt(n_mars))
    col3.metric("📊 Ratio Paris / Marseille",   f"{ratio:.1f}×")

    st.divider()

    # Jauges
    fig_gauge = go.Figure()
    max_val = max(n_paris, n_mars) * 1.25
    for i, (nom, val, color) in enumerate([
        ("Paris",     n_paris, COLOR_PARIS),
        ("Marseille", n_mars,  COLOR_MARSEILLE),
    ]):
        fig_gauge.add_trace(go.Indicator(
            mode="gauge+number",
            value=val,
            title={"text": nom, "font": {"size": 14}},
            gauge={
                "axis": {"range": [0, max_val]},
                "bar":  {"color": color},
                "steps": [
                    {"range": [0,           max_val * 0.33], "color": "#d4edda"},
                    {"range": [max_val * 0.33, max_val * 0.66], "color": "#fff3cd"},
                    {"range": [max_val * 0.66, max_val],     "color": "#f8d7da"},
                ],
            },
            domain={"column": i, "row": 0},
        ))
    fig_gauge.update_layout(grid={"rows": 1, "columns": 2}, height=240, margin=dict(t=30, b=0))
    st.plotly_chart(fig_gauge, use_container_width=True)

    st.markdown(
        f"👉 Paris recense **{fmt(n_paris)} lieux culturels** contre "
        f"**{fmt(n_mars)} à Marseille**, soit un ratio de **{ratio:.1f}×**. "
        "Cette différence reflète la taille et le rayonnement international de Paris, "
        "capitale culturelle de rang mondial."
    )


# ─────────────────────────────────────────────
# ONGLET 2 — RÉPARTITION PAR CATÉGORIE
# ─────────────────────────────────────────────
def tab_categories(df):
    st.subheader("Répartition des lieux culturels par catégorie")

    if "Categorie" not in df.columns:
        st.info("ℹ️ Colonne 'Categorie' absente des données.")
        return

    col_p, col_m = st.columns(2)

    for col, ville, color in [
        (col_p, "Paris",     COLOR_PARIS),
        (col_m, "Marseille", COLOR_MARSEILLE),
    ]:
        with col:
            emoji = "🗼" if ville == "Paris" else "⚓"
            st.markdown(f"**{emoji} {ville}**")
            df_v = (
                df[df["Ville"] == ville]
                .groupby("Categorie")
                .size()
                .reset_index(name="count")
                .sort_values("count", ascending=True)
            )
            fig = px.bar(
                df_v, x="count", y="Categorie", orientation="h",
                color_discrete_sequence=[color],
                text="count",
                title=f"Catégories — {ville}",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(height=max(300, len(df_v) * 30 + 80),
                              showlegend=False, xaxis_title="Nb lieux")
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Top catégories communes
    st.markdown("#### 🔁 Catégories présentes dans les deux villes")
    cats_p = set(df[df["Ville"] == "Paris"]["Categorie"].unique())
    cats_m = set(df[df["Ville"] == "Marseille"]["Categorie"].unique())
    communes = sorted(cats_p & cats_m)

    if communes:
        df_comm = df[df["Categorie"].isin(communes)].groupby(["Categorie", "Ville"]).size().reset_index(name="count")
        fig_comm = px.bar(
            df_comm, x="Categorie", y="count", color="Ville", barmode="group",
            color_discrete_map={"Paris": COLOR_PARIS, "Marseille": COLOR_MARSEILLE},
            text="count",
            title="Catégories communes — comparaison directe",
        )
        fig_comm.update_traces(textposition="outside")
        fig_comm.update_layout(height=400, xaxis_tickangle=-30)
        st.plotly_chart(fig_comm, use_container_width=True)
    else:
        st.info("ℹ️ Aucune catégorie commune trouvée entre les deux villes.")


# ─────────────────────────────────────────────
# ONGLET 3 — PART GLOBALE (CAMEMBERT)
# ─────────────────────────────────────────────
def tab_global(df):
    st.subheader("🥧 Part des lieux culturels entre les deux villes")

    col_pie, col_bar = st.columns(2)

    n_paris = len(df[df["Ville"] == "Paris"])
    n_mars  = len(df[df["Ville"] == "Marseille"])
    df_pie = pd.DataFrame({
        "Ville":  ["Paris", "Marseille"],
        "Nombre": [n_paris, n_mars],
    })

    with col_pie:
        fig_pie = px.pie(
            df_pie, values="Nombre", names="Ville",
            color="Ville",
            color_discrete_map={"Paris": COLOR_PARIS, "Marseille": COLOR_MARSEILLE},
            hole=0.4,
        )
        fig_pie.update_traces(textinfo="percent+label")
        fig_pie.update_layout(height=340)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_bar:
        fig_bar = px.bar(
            df_pie, x="Ville", y="Nombre", color="Ville",
            color_discrete_map={"Paris": COLOR_PARIS, "Marseille": COLOR_MARSEILLE},
            text="Nombre",
            title="Total des lieux culturels",
        )
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(height=340, showlegend=False, yaxis_title="Nb lieux")
        st.plotly_chart(fig_bar, use_container_width=True)

    # Répartition interne par catégorie (sunburst)
    if "Categorie" in df.columns:
        st.divider()
        st.markdown("#### 🌐 Vue globale — Sunburst (Ville → Catégorie)")
        df_sun = df.groupby(["Ville", "Categorie"]).size().reset_index(name="count")
        fig_sun = px.sunburst(
            df_sun, path=["Ville", "Categorie"], values="count",
            color="Ville",
            color_discrete_map={"Paris": COLOR_PARIS, "Marseille": COLOR_MARSEILLE},
        )
        fig_sun.update_layout(height=480)
        st.plotly_chart(fig_sun, use_container_width=True)


# ─────────────────────────────────────────────
# ONGLET 4 — CARTE DES LIEUX CULTURELS
# ─────────────────────────────────────────────
def tab_carte(df):
    st.subheader("🗺️ Carte des lieux culturels")

    if "Latitude" not in df.columns or "Longitude" not in df.columns:
        st.info("ℹ️ Colonnes 'Latitude'/'Longitude' absentes — carte non disponible.")
        return

    df_map = df.dropna(subset=["Latitude", "Longitude"]).copy()

    if df_map.empty:
        st.warning("⚠️ Aucune coordonnée valide après nettoyage.")
        return

    # Filtre catégorie
    if "Categorie" in df_map.columns:
        toutes = ["Toutes"] + sorted(df_map["Categorie"].dropna().unique().tolist())
        cat_sel = st.selectbox("🎭 Filtrer par catégorie :", toutes)
        if cat_sel != "Toutes":
            df_map = df_map[df_map["Categorie"] == cat_sel]

    hover_cols = {}
    if "Categorie"   in df_map.columns: hover_cols["Categorie"]   = True
    if "Nom du site" in df_map.columns: hover_cols["Nom du site"] = True
    hover_cols["Latitude"]  = False
    hover_cols["Longitude"] = False

    fig_map = px.scatter_mapbox(
        df_map,
        lat="Latitude", lon="Longitude",
        color="Ville",
        color_discrete_map={"Paris": COLOR_PARIS, "Marseille": COLOR_MARSEILLE},
        hover_name="Nom du site" if "Nom du site" in df_map.columns else "Ville",
        hover_data=hover_cols,
        zoom=4.5,
        center={"lat": 46.6, "lon": 2.5},
        height=580,
    )
    fig_map.update_layout(
        mapbox_style="carto-positron",
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
    )
    st.plotly_chart(fig_map, use_container_width=True)
    st.caption(f"📍 {len(df_map)} lieux affichés sur la carte.")


# ─────────────────────────────────────────────
# ONGLET 5 — ANALYSE
# ─────────────────────────────────────────────
def tab_analyse(df):
    st.subheader("🧠 Analyse de l'offre culturelle")

    n_paris = len(df[df["Ville"] == "Paris"])
    n_mars  = len(df[df["Ville"] == "Marseille"])

    top_cat_paris = "N/D"
    top_cat_mars  = "N/D"

    if "Categorie" in df.columns:
        top_cat_paris = df[df["Ville"] == "Paris"]["Categorie"].value_counts().idxmax()
        top_cat_mars  = df[df["Ville"] == "Marseille"]["Categorie"].value_counts().idxmax()

    st.markdown(f"""
#### 🗼 Paris
Paris recense **{fmt(n_paris)} lieux culturels** répartis sur l'ensemble de ses arrondissements.
La catégorie la plus représentée est **{top_cat_paris}**. Cette richesse culturelle
s'explique par :
- Son statut de capitale et son rayonnement international.
- L'accumulation historique de musées, théâtres et institutions culturelles.
- Les importantes subventions publiques (État, Ville de Paris).

#### ⚓ Marseille
Marseille compte **{fmt(n_mars)} lieux culturels**, avec une prédominance de **{top_cat_mars}**.
La ville a fortement développé son offre culturelle depuis **Marseille-Provence 2013
(Capitale Européenne de la Culture)**, notamment via :
- Le MuCEM (Musée des Civilisations de l'Europe et de la Méditerranée).
- La Friche la Belle de Mai, pôle culturel majeur.
- Un réseau de théâtres et de galeries en expansion.

#### 📊 Synthèse
L'écart entre les deux villes (**{n_paris / n_mars:.1f}×** plus de lieux à Paris)
est cohérent avec la différence de population et de budget municipal.
Marseille présente néanmoins une dynamique culturelle en forte progression depuis 2013.
    """)


# ─────────────────────────────────────────────
# FONCTION PRINCIPALE
# ─────────────────────────────────────────────
def show_culture():
    st.header("🎭 Culture")
    st.caption("Sources : Culture_Paris.xlsx · Culture_Marseille.xlsx (Open Data Paris / Open Data Marseille)")

    with st.spinner("Chargement des données culturelles..."):
        df, df_paris_raw, df_mars_raw = load_culture()

    onglet1, onglet2, onglet3, onglet4, onglet5 = st.tabs([
        "🔑 Chiffres clés",
        "🎨 Par catégorie",
        "🥧 Vue globale",
        "🗺️ Carte",
        "🧠 Analyse",
    ])

    with onglet1:
        tab_kpis(df)

    with onglet2:
        tab_categories(df)

    with onglet3:
        tab_global(df)

    with onglet4:
        tab_carte(df)

    with onglet5:
        tab_analyse(df)

    with st.expander("📚 Sources de données"):
        st.markdown("""
| Dataset | Ville | Source |
|---|---|---|
| Équipements culturels | Paris | [Open Data Paris](https://opendata.paris.fr) |
| Équipements culturels | Marseille | [Open Data Métropole AMP](https://data.ampmetropole.fr) |
        """)