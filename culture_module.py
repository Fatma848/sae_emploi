"""
Module Culture — Comparateur de villes françaises
SAE Outils Décisionnels

Source : BASILIC — Base des lieux et équipements culturels
         Ministère de la Culture / data.culture.gouv.fr

Usage : from culture_module import show_culture
        show_culture(ville1, ville2, v1_info, v2_info)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os

COLOR_V1 = "#1f77b4"
COLOR_V2 = "#d62728"

CLEAN_DIR = os.path.join(os.path.dirname(__file__), "data", "clean")


def fmt(n):
    try:
        return f"{int(n):,}".replace(",", "\u202f")
    except Exception:
        return str(n)


# ─────────────────────────────────────────────
# CHARGEMENT
# ─────────────────────────────────────────────
@st.cache_data
def load_culture():
    path = os.path.join(CLEAN_DIR, "culture.csv")
    if not os.path.exists(path):
        return None
    return pd.read_csv(path, encoding="utf-8-sig")


def get_ville_culture(df, nom_ville):
    return df[df["nom_commune"].str.lower() == nom_ville.lower()].copy()


# ─────────────────────────────────────────────
# ONGLET 1 — CHIFFRES CLÉS
# ─────────────────────────────────────────────
def tab_kpis(ville1, ville2, df1, df2):
    st.subheader("Indicateurs clés — Offre culturelle")
    st.caption("Source : BASILIC — Ministère de la Culture · France entière")

    n1 = len(df1)
    n2 = len(df2)
    ratio = n1 / n2 if n2 > 0 else 0

    # KPIs côte à côte
    col_lbl, col_v1, col_v2 = st.columns([1.5, 2, 2])
    col_lbl.markdown("**Indicateur**")
    col_v1.markdown(f"**🔵 {ville1}**")
    col_v2.markdown(f"**🔴 {ville2}**")

    kpis_data = [("🏛️ Lieux culturels", n1, n2)]

    if "categorie" in df1.columns and "categorie" in df2.columns:
        kpis_data.append(("🎨 Catégories distinctes",
                          df1["categorie"].nunique(),
                          df2["categorie"].nunique()))

    for label, v1, v2 in kpis_data:
        c1, c2, c3 = st.columns([1.5, 2, 2])
        c1.markdown(f"**{label}**")
        c2.metric("", fmt(v1))
        diff = v2 - v1
        c3.metric("", fmt(v2), delta=f"{diff:+,}".replace(",", "\u202f"))

    st.divider()

    # Jauges
    st.markdown("#### 📊 Nombre de lieux culturels")
    max_val = max(n1, n2) * 1.2
    fig_g = go.Figure()
    for i, (nom, val, color) in enumerate([
        (ville1, n1, COLOR_V1),
        (ville2, n2, COLOR_V2),
    ]):
        fig_g.add_trace(go.Indicator(
            mode="gauge+number",
            value=val,
            title={"text": nom, "font": {"size": 13}},
            gauge={
                "axis": {"range": [0, max_val]},
                "bar":  {"color": color},
                "steps": [
                    {"range": [0,           max_val * 0.33], "color": "#d4edda"},
                    {"range": [max_val * 0.33, max_val * 0.66], "color": "#fff3cd"},
                    {"range": [max_val * 0.66, max_val],        "color": "#f8d7da"},
                ],
            },
            domain={"column": i, "row": 0},
        ))
    fig_g.update_layout(
        grid={"rows": 1, "columns": 2}, height=240, margin=dict(t=30, b=0)
    )
    st.plotly_chart(fig_g, use_container_width=True)

    plus_riche = ville1 if n1 > n2 else ville2
    st.markdown(
        f"> 👉 **{plus_riche}** dispose d'une offre culturelle plus importante "
        f"avec **{fmt(max(n1, n2))} lieux** contre **{fmt(min(n1, n2))}** "
        f"({'×'.join([str(round(max(n1,n2)/min(n1,n2),1))])} fois plus)."
        if min(n1, n2) > 0 else
        f"> 👉 **{ville1}** : {fmt(n1)} lieux · **{ville2}** : {fmt(n2)} lieux."
    )


# ─────────────────────────────────────────────
# ONGLET 2 — RÉPARTITION PAR CATÉGORIE
# ─────────────────────────────────────────────
def tab_categories(ville1, ville2, df1, df2):
    st.subheader("Répartition par type d'équipement culturel")

    if "categorie" not in df1.columns or "categorie" not in df2.columns:
        st.info("ℹ️ Colonne 'categorie' absente des données.")
        return

    col_v1, col_v2 = st.columns(2)

    for col, ville, df, color in [
        (col_v1, ville1, df1, COLOR_V1),
        (col_v2, ville2, df2, COLOR_V2),
    ]:
        with col:
            emoji = "🔵" if color == COLOR_V1 else "🔴"
            st.markdown(f"**{emoji} {ville}**")
            df_cat = (
                df.groupby("categorie")
                .size()
                .reset_index(name="nb")
                .sort_values("nb", ascending=True)
            )
            df_cat["categorie"] = df_cat["categorie"].str.slice(0, 50)
            fig = px.bar(
                df_cat, x="nb", y="categorie",
                orientation="h",
                color_discrete_sequence=[color],
                text="nb",
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(
                height=max(320, len(df_cat) * 28 + 60),
                showlegend=False,
                xaxis_title="Nb lieux", yaxis_title="",
                margin=dict(t=10, l=0),
            )
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Comparaison directe catégories communes
    st.markdown("#### 🔁 Catégories présentes dans les deux villes")
    cats1 = set(df1["categorie"].dropna().unique())
    cats2 = set(df2["categorie"].dropna().unique())
    communes = sorted(cats1 & cats2)

    if communes:
        g1 = df1[df1["categorie"].isin(communes)].groupby("categorie").size().reset_index(name=ville1)
        g2 = df2[df2["categorie"].isin(communes)].groupby("categorie").size().reset_index(name=ville2)
        df_comp = g1.merge(g2, on="categorie")
        df_melt = df_comp.melt(id_vars="categorie", var_name="Ville", value_name="Nb")
        df_melt["categorie"] = df_melt["categorie"].str.slice(0, 50)

        fig_comp = px.bar(
            df_melt, x="categorie", y="Nb", color="Ville",
            barmode="group",
            color_discrete_map={ville1: COLOR_V1, ville2: COLOR_V2},
            text="Nb",
            title="Comparaison directe des catégories communes",
        )
        fig_comp.update_traces(textposition="outside")
        fig_comp.update_layout(
            height=420, xaxis_tickangle=-35,
            legend_title="", margin=dict(t=40),
        )
        st.plotly_chart(fig_comp, use_container_width=True)

        st.markdown(f"""
> 👉 Les deux villes partagent **{len(communes)} catégories** communes.
> La comparaison directe permet d'identifier les secteurs culturels où
> l'une des villes est structurellement mieux dotée.
        """)
    else:
        st.info("ℹ️ Aucune catégorie commune entre les deux villes.")

    st.divider()

    # Sunburst global
    st.markdown("#### 🌐 Vue globale — Ville → Catégorie")
    df_both = pd.concat([
        df1.assign(Ville=ville1),
        df2.assign(Ville=ville2),
    ])
    if "categorie" in df_both.columns:
        df_sun = df_both.groupby(["Ville", "categorie"]).size().reset_index(name="nb")
        df_sun["categorie"] = df_sun["categorie"].str.slice(0, 45)
        fig_sun = px.sunburst(
            df_sun, path=["Ville", "categorie"], values="nb",
            color="Ville",
            color_discrete_map={ville1: COLOR_V1, ville2: COLOR_V2},
        )
        fig_sun.update_layout(height=480)
        st.plotly_chart(fig_sun, use_container_width=True)


# ─────────────────────────────────────────────
# ONGLET 3 — CARTE
# ─────────────────────────────────────────────
def tab_carte(ville1, ville2, df1, df2):
    st.subheader("🗺️ Carte des lieux culturels")

    df_both = pd.concat([
        df1.assign(Ville=ville1),
        df2.assign(Ville=ville2),
    ])

    if "latitude" not in df_both.columns or "longitude" not in df_both.columns:
        st.info("ℹ️ Coordonnées GPS non disponibles.")
        return

    df_map = df_both.dropna(subset=["latitude", "longitude"]).copy()

    if df_map.empty:
        st.warning("⚠️ Aucune coordonnée valide après nettoyage.")
        return

    # Filtre par catégorie
    if "categorie" in df_map.columns:
        cats = ["Toutes"] + sorted(df_map["categorie"].dropna().unique().tolist())
        cat_sel = st.selectbox("🎭 Filtrer par catégorie :", cats, key="carte_cat")
        if cat_sel != "Toutes":
            df_map = df_map[df_map["categorie"] == cat_sel]

    hover_data = {
        "latitude": False, "longitude": False, "Ville": True,
    }
    if "categorie" in df_map.columns:
        hover_data["categorie"] = True

    hover_name = "nom" if "nom" in df_map.columns else "Ville"

    fig_map = px.scatter_mapbox(
        df_map,
        lat="latitude", lon="longitude",
        color="Ville",
        color_discrete_map={ville1: COLOR_V1, ville2: COLOR_V2},
        hover_name=hover_name,
        hover_data=hover_data,
        zoom=10 if len(df_map["Ville"].unique()) == 1 else 5,
        height=580,
    )
    fig_map.update_layout(
        mapbox_style="carto-positron",
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
    )
    st.plotly_chart(fig_map, use_container_width=True)
    st.caption(f"📍 {len(df_map)} lieux affichés.")


# ─────────────────────────────────────────────
# ONGLET 4 — CLASSEMENT
# ─────────────────────────────────────────────
def tab_classement(df, ville1, ville2):
    st.subheader("🏆 Classement des villes par richesse culturelle")
    st.caption("Toutes les villes +20 000 hab présentes dans BASILIC")

    df_rank = (
        df.groupby("nom_commune")
        .size()
        .reset_index(name="nb_lieux")
        .sort_values("nb_lieux", ascending=False)
        .reset_index(drop=True)
    )
    df_rank["rang"] = df_rank.index + 1

    rang1 = df_rank[df_rank["nom_commune"] == ville1]["rang"].values
    rang2 = df_rank[df_rank["nom_commune"] == ville2]["rang"].values

    col1, col2, col3 = st.columns(3)
    col1.metric(f"🔵 Rang {ville1}",
                f"#{rang1[0]}" if len(rang1) else "N/D",
                f"sur {len(df_rank)} villes")
    col2.metric(f"🔴 Rang {ville2}",
                f"#{rang2[0]}" if len(rang2) else "N/D",
                f"sur {len(df_rank)} villes")
    col3.metric("🏆 Ville la + dotée",
                df_rank.iloc[0]["nom_commune"],
                f"{df_rank.iloc[0]['nb_lieux']} lieux")

    st.divider()

    # Top 20
    st.markdown("#### 🏆 Top 20 villes les mieux dotées culturellement")
    df_top = df_rank.head(20).copy()
    df_top["couleur"] = df_top["nom_commune"].apply(
        lambda x: COLOR_V1 if x == ville1 else (COLOR_V2 if x == ville2 else "#95a5a6")
    )

    fig_top = px.bar(
        df_top.sort_values("nb_lieux"),
        x="nb_lieux", y="nom_commune",
        orientation="h",
        text="nb_lieux",
        color="nom_commune",
        color_discrete_map={
            v: (COLOR_V1 if v == ville1 else COLOR_V2 if v == ville2 else "#95a5a6")
            for v in df_top["nom_commune"]
        },
    )
    fig_top.update_traces(textposition="outside")
    fig_top.update_layout(
        height=560, showlegend=False,
        xaxis_title="Nb lieux culturels", yaxis_title="",
        margin=dict(t=10),
    )
    st.plotly_chart(fig_top, use_container_width=True)

    st.divider()

    # Tableau avec recherche
    st.markdown("#### 📋 Tableau complet")
    search = st.text_input("🔍 Rechercher une ville :", "", key="search_cult")
    df_show = df_rank.copy()
    if search:
        df_show = df_show[df_show["nom_commune"].str.lower().str.contains(search.lower())]
    df_show.columns = ["Ville", "Nb lieux culturels", "Rang"]
    st.dataframe(df_show[["Rang", "Ville", "Nb lieux culturels"]],
                 use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
# ONGLET 5 — ANALYSE
# ─────────────────────────────────────────────
def tab_analyse(ville1, ville2, df1, df2):
    st.subheader("🧠 Analyse de l'offre culturelle")

    n1, n2 = len(df1), len(df2)
    plus_riche = ville1 if n1 > n2 else ville2
    moins_riche = ville2 if n1 > n2 else ville1

    lignes = [
        f"**🏛️ Richesse globale** : {plus_riche} ({fmt(max(n1,n2))} lieux) est "
        f"**{max(n1,n2)/min(n1,n2):.1f}× mieux dotée** que {moins_riche} ({fmt(min(n1,n2))} lieux)."
        if min(n1, n2) > 0 else
        f"**🏛️ Richesse globale** : {ville1} = {fmt(n1)} lieux · {ville2} = {fmt(n2)} lieux."
    ]

    if "categorie" in df1.columns and not df1.empty:
        top1 = df1["categorie"].value_counts().idxmax()
        lignes.append(f"**🎨 Catégorie dominante à {ville1}** : {top1}")

    if "categorie" in df2.columns and not df2.empty:
        top2 = df2["categorie"].value_counts().idxmax()
        lignes.append(f"**🎨 Catégorie dominante à {ville2}** : {top2}")

    if "categorie" in df1.columns and "categorie" in df2.columns:
        cats1 = set(df1["categorie"].dropna().unique())
        cats2 = set(df2["categorie"].dropna().unique())
        only1 = cats1 - cats2
        only2 = cats2 - cats1
        if only1:
            lignes.append(
                f"**🔵 Exclusif à {ville1}** : {', '.join(sorted(only1)[:5])}"
                + ("…" if len(only1) > 5 else "")
            )
        if only2:
            lignes.append(
                f"**🔴 Exclusif à {ville2}** : {', '.join(sorted(only2)[:5])}"
                + ("…" if len(only2) > 5 else "")
            )

    for l in lignes:
        st.markdown(f"- {l}")

    st.markdown("""
---
**ℹ️ À propos des données BASILIC**

La base BASILIC est administrée par le **Ministère de la Culture** et agrège plusieurs sources :
musées, théâtres, cinémas, bibliothèques, conservatoires, monuments historiques, galeries,
centres culturels, écoles d'art, salles de spectacle…

Elle alimente l'**Atlas Culture des territoires** et la base permanente des équipements INSEE.
Les données couvrent l'ensemble du territoire français.
    """)


# ─────────────────────────────────────────────
# FONCTION PRINCIPALE
# ─────────────────────────────────────────────
def show_culture(ville1, ville2, v1_info, v2_info):
    st.header("🎭 Culture")
    st.caption(
        f"Comparaison : **{ville1}** vs **{ville2}** · "
        "Source : BASILIC — Ministère de la Culture"
    )

    df = load_culture()
    if df is None:
        st.error(
            "❌ Fichier `data/clean/culture.csv` introuvable.\n\n"
            "Exécute : `python prepare_data.py`"
        )
        return

    df1 = get_ville_culture(df, ville1)
    df2 = get_ville_culture(df, ville2)

    if df1.empty:
        st.warning(f"⚠️ Aucune donnée culture pour **{ville1}**.")
    if df2.empty:
        st.warning(f"⚠️ Aucune donnée culture pour **{ville2}**.")
    if df1.empty and df2.empty:
        return

    onglet1, onglet2, onglet3, onglet4, onglet5 = st.tabs([
        "🔑 Chiffres clés",
        "🎨 Par catégorie",
        "🗺️ Carte",
        "🏆 Classement",
        "🧠 Analyse",
    ])

    with onglet1:
        tab_kpis(ville1, ville2, df1, df2)
    with onglet2:
        tab_categories(ville1, ville2, df1, df2)
    with onglet3:
        tab_carte(ville1, ville2, df1, df2)
    with onglet4:
        tab_classement(df, ville1, ville2)
    with onglet5:
        tab_analyse(ville1, ville2, df1, df2)

    with st.expander("📚 Sources de données"):
        st.markdown("""
| Dataset | Description | Source |
|---|---|---|
| basilic.csv | Lieux et équipements culturels — France entière | [data.culture.gouv.fr](https://data.culture.gouv.fr/explore/dataset/base-des-lieux-et-des-equipements-culturels/export/) |
        """)