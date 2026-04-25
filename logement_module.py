"""
Module Logement — Comparateur de villes françaises
SAE Outils Décisionnels

Sources :
- pred-app-mef-dhup.csv  : Loyers de référence appartements (DHUP/Ministère du Logement)
- pred-mai-mef-dhup.csv  : Loyers de référence maisons (DHUP/Ministère du Logement)

Variables clés :
- loyer_m2      : loyer prédit au m²
- loyer_m2_min  : borne basse de l'intervalle de confiance
- loyer_m2_max  : borne haute de l'intervalle de confiance
- type_bien     : Appartement ou Maison

Usage : from logement_module import show_logement
        show_logement(ville1, ville2, v1_info, v2_info)
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
        return f"{float(n):,.2f}".replace(",", " ").replace(".", ",")
    except Exception:
        return str(n)


# ─────────────────────────────────────────────
# CHARGEMENT
# ─────────────────────────────────────────────
@st.cache_data
def load_logement():
    path = os.path.join(CLEAN_DIR, "logement.csv")
    if not os.path.exists(path):
        return None
    return pd.read_csv(path, encoding="utf-8-sig")


def get_ville_logement(df, nom_ville):
    return df[df["nom_commune"].str.lower() == nom_ville.lower()].copy()


def get_stats(df_ville):
    """Retourne les stats loyers pour une ville (app + maison)."""
    stats = {}
    for typ in ["Appartement", "Maison"]:
        sub = df_ville[df_ville["type_bien"] == typ]
        if not sub.empty:
            # Prendre la ligne avec le plus d'observations (plus fiable)
            row = sub.sort_values("nb_obs_commune", ascending=False).iloc[0]
            stats[typ] = {
                "loyer_m2":     row["loyer_m2"],
                "loyer_m2_min": row["loyer_m2_min"],
                "loyer_m2_max": row["loyer_m2_max"],
                "niveau":       row.get("niveau_prediction", "N/D"),
                "nb_obs":       row.get("nb_obs_commune", 0),
                "r2":           row.get("r2_adj", None),
            }
    return stats


# ─────────────────────────────────────────────
# ONGLET 1 — CHIFFRES CLÉS
# ─────────────────────────────────────────────
def tab_kpis(ville1, ville2, s1, s2):
    st.subheader("Loyers de référence au m²")
    st.caption(
        "Source : DHUP — Ministère du Logement · "
        "Loyer prédit au m² avec intervalle de confiance à 95%"
    )

    for typ in ["Appartement", "Maison"]:
        emoji = "🏢" if typ == "Appartement" else "🏠"
        st.markdown(f"#### {emoji} {typ}")

        d1 = s1.get(typ)
        d2 = s2.get(typ)

        col_lbl, col_v1, col_v2 = st.columns([1.5, 2, 2])
        col_lbl.markdown("**Indicateur**")
        col_v1.markdown(f"**🔵 {ville1}**")
        col_v2.markdown(f"**🔴 {ville2}**")

        # Loyer m²
        c1, c2, c3 = st.columns([1.5, 2, 2])
        c1.markdown("**💶 Loyer moyen/m²**")
        if d1:
            c2.metric("", f"{d1['loyer_m2']:.2f} €/m²")
        else:
            c2.info("N/D")
        if d2:
            delta = None
            if d1:
                diff = d2["loyer_m2"] - d1["loyer_m2"]
                delta = f"{diff:+.2f} €/m²"
            c3.metric("", f"{d2['loyer_m2']:.2f} €/m²", delta=delta,
                      delta_color="inverse")
        else:
            c3.info("N/D")

        # Intervalle de confiance
        c1, c2, c3 = st.columns([1.5, 2, 2])
        c1.markdown("**📊 Intervalle (95%)**")
        if d1:
            c2.metric("", f"{d1['loyer_m2_min']:.2f} – {d1['loyer_m2_max']:.2f} €/m²")
        else:
            c2.info("N/D")
        if d2:
            c3.metric("", f"{d2['loyer_m2_min']:.2f} – {d2['loyer_m2_max']:.2f} €/m²")
        else:
            c3.info("N/D")

        # Fiabilité
        c1, c2, c3 = st.columns([1.5, 2, 2])
        c1.markdown("**🎯 Nb observations**")
        if d1:
            c2.metric("", f"{int(d1['nb_obs'])} obs.")
        else:
            c2.info("N/D")
        if d2:
            c3.metric("", f"{int(d2['nb_obs'])} obs.")
        else:
            c3.info("N/D")

        if d1 and d2:
            diff = d2["loyer_m2"] - d1["loyer_m2"]
            plus_cher = ville2 if diff > 0 else ville1
            st.markdown(
                f"> 👉 Pour les **{typ.lower()}s**, **{plus_cher}** est plus chère "
                f"de **{abs(diff):.2f} €/m²** "
                f"({max(d1['loyer_m2'], d2['loyer_m2']):.2f} €/m² vs "
                f"{min(d1['loyer_m2'], d2['loyer_m2']):.2f} €/m²)."
            )
        st.divider()

    # Jauges loyers appartements
    a1 = s1.get("Appartement")
    a2 = s2.get("Appartement")
    if a1 and a2:
        st.markdown("#### 📊 Loyer appartement — vue comparative")
        max_val = max(a1["loyer_m2_max"], a2["loyer_m2_max"]) * 1.1
        fig_g = go.Figure()
        for i, (nom, d, color) in enumerate([
            (ville1, a1, COLOR_V1),
            (ville2, a2, COLOR_V2),
        ]):
            fig_g.add_trace(go.Indicator(
                mode="gauge+number",
                value=round(d["loyer_m2"], 2),
                title={"text": f"{nom}<br>Appartement", "font": {"size": 12}},
                number={"suffix": " €/m²", "valueformat": ".2f"},
                gauge={
                    "axis": {"range": [0, max_val]},
                    "bar":  {"color": color},
                    "steps": [
                        {"range": [0,            max_val * 0.33], "color": "#d4edda"},
                        {"range": [max_val * 0.33, max_val * 0.66], "color": "#fff3cd"},
                        {"range": [max_val * 0.66, max_val],        "color": "#f8d7da"},
                    ],
                },
                domain={"column": i, "row": 0},
            ))
        fig_g.update_layout(
            grid={"rows": 1, "columns": 2}, height=240, margin=dict(t=40, b=0)
        )
        st.plotly_chart(fig_g, use_container_width=True)


# ─────────────────────────────────────────────
# ONGLET 2 — COMPARAISON VISUELLE
# ─────────────────────────────────────────────
def tab_comparaison(ville1, ville2, s1, s2):
    st.subheader("Comparaison visuelle des loyers")

    rows = []
    for typ in ["Appartement", "Maison"]:
        d1 = s1.get(typ)
        d2 = s2.get(typ)
        if d1:
            rows.append({"Ville": ville1, "Type": typ,
                         "Loyer (€/m²)": d1["loyer_m2"],
                         "Min": d1["loyer_m2_min"], "Max": d1["loyer_m2_max"]})
        if d2:
            rows.append({"Ville": ville2, "Type": typ,
                         "Loyer (€/m²)": d2["loyer_m2"],
                         "Min": d2["loyer_m2_min"], "Max": d2["loyer_m2_max"]})

    if not rows:
        st.info("Données insuffisantes pour la comparaison.")
        return

    df_plot = pd.DataFrame(rows)

    # Bar chart groupé
    st.markdown("#### 📊 Loyer au m² — Appartement vs Maison")
    fig_bar = px.bar(
        df_plot, x="Type", y="Loyer (€/m²)", color="Ville",
        barmode="group",
        color_discrete_map={ville1: COLOR_V1, ville2: COLOR_V2},
        text="Loyer (€/m²)",
        error_y=df_plot["Max"] - df_plot["Loyer (€/m²)"],
        error_y_minus=df_plot["Loyer (€/m²)"] - df_plot["Min"],
        title="Loyers de référence au m² avec intervalle de confiance",
    )
    fig_bar.update_traces(texttemplate="%{text:.2f} €", textposition="outside")
    fig_bar.update_layout(
        height=420, yaxis_title="€/m²",
        legend_title="", margin=dict(t=40),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("""
> 👉 Les **barres d'erreur** représentent l'intervalle de confiance à 95% du modèle de prédiction.
> Un intervalle étroit = estimation fiable. Un intervalle large = peu d'observations dans cette commune.
    """)

    st.divider()

    # Graphique en points avec intervalles
    st.markdown("#### 🎯 Intervalles de confiance détaillés")
    fig_dot = go.Figure()
    colors = {ville1: COLOR_V1, ville2: COLOR_V2}

    for _, row in df_plot.iterrows():
        color = colors[row["Ville"]]
        label = f"{row['Ville']} — {row['Type']}"
        fig_dot.add_trace(go.Scatter(
            x=[row["Loyer (€/m²)"]],
            y=[label],
            mode="markers",
            marker=dict(color=color, size=14, symbol="diamond"),
            error_x=dict(
                type="data",
                symmetric=False,
                array=[row["Max"] - row["Loyer (€/m²)"]],
                arrayminus=[row["Loyer (€/m²)"] - row["Min"]],
                color=color,
            ),
            name=row["Ville"],
            showlegend=False,
        ))
    fig_dot.update_layout(
        xaxis_title="Loyer au m² (€)",
        height=280, margin=dict(t=10),
    )
    st.plotly_chart(fig_dot, use_container_width=True)


# ─────────────────────────────────────────────
# ONGLET 3 — CLASSEMENT RÉGIONAL
# ─────────────────────────────────────────────
def tab_classement(df, ville1, ville2):
    st.subheader("Classement des villes par loyer au m²")
    st.caption("Toutes les villes +20 000 hab disponibles dans les données")

    type_bien = st.radio(
        "Type de bien :", ["Appartement", "Maison"],
        horizontal=True, key="radio_classement"
    )

    df_type = df[df["type_bien"] == type_bien].copy()

    if df_type.empty:
        st.info("Données non disponibles.")
        return

    # Garder la meilleure observation par commune
    df_best = (
        df_type.sort_values("nb_obs_commune", ascending=False)
        .drop_duplicates("nom_commune")
        .sort_values("loyer_m2", ascending=False)
        .reset_index(drop=True)
    )
    df_best["rang"] = df_best.index + 1

    # Trouver le rang des villes sélectionnées
    rang1 = df_best[df_best["nom_commune"] == ville1]["rang"].values
    rang2 = df_best[df_best["nom_commune"] == ville2]["rang"].values

    col1, col2, col3 = st.columns(3)
    col1.metric(f"🔵 Rang {ville1}", f"#{rang1[0]}" if len(rang1) else "N/D",
                f"sur {len(df_best)} villes")
    col2.metric(f"🔴 Rang {ville2}", f"#{rang2[0]}" if len(rang2) else "N/D",
                f"sur {len(df_best)} villes")
    col3.metric("🏆 Ville la + chère", df_best.iloc[0]["nom_commune"],
                f"{df_best.iloc[0]['loyer_m2']:.2f} €/m²")

    st.divider()

    # Top 20
    st.markdown(f"#### 🏆 Top 20 villes les plus chères — {type_bien}s")
    df_top20 = df_best.head(20).copy()

    # Coloriser les villes sélectionnées
    df_top20["couleur"] = df_top20["nom_commune"].apply(
        lambda x: COLOR_V1 if x == ville1 else (COLOR_V2 if x == ville2 else "#95a5a6")
    )

    fig_top = px.bar(
        df_top20.sort_values("loyer_m2"),
        x="loyer_m2", y="nom_commune",
        orientation="h",
        text="loyer_m2",
        color="nom_commune",
        color_discrete_map={
            v: (COLOR_V1 if v == ville1 else COLOR_V2 if v == ville2 else "#95a5a6")
            for v in df_top20["nom_commune"]
        },
        title=f"Top 20 loyers {type_bien}s (€/m²)",
    )
    fig_top.update_traces(texttemplate="%{text:.2f} €", textposition="outside")
    fig_top.update_layout(
        height=560, showlegend=False,
        xaxis_title="Loyer au m² (€)", yaxis_title="",
        margin=dict(t=40),
    )
    st.plotly_chart(fig_top, use_container_width=True)

    st.divider()

    # Tableau complet avec filtre
    st.markdown("#### 📋 Tableau complet")
    search = st.text_input("🔍 Rechercher une ville :", "")
    df_show = df_best.copy()
    if search:
        df_show = df_show[df_show["nom_commune"].str.lower().str.contains(search.lower())]

    df_show = df_show[["rang", "nom_commune", "loyer_m2", "loyer_m2_min",
                        "loyer_m2_max", "departement", "region"]].copy()
    df_show.columns = ["Rang", "Ville", "Loyer (€/m²)", "Min (€/m²)",
                       "Max (€/m²)", "Département", "Région"]
    df_show["Loyer (€/m²)"] = df_show["Loyer (€/m²)"].round(2)
    df_show["Min (€/m²)"]   = df_show["Min (€/m²)"].round(2)
    df_show["Max (€/m²)"]   = df_show["Max (€/m²)"].round(2)

    st.dataframe(df_show, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
# ONGLET 4 — ANALYSE
# ─────────────────────────────────────────────
def tab_analyse(ville1, ville2, s1, s2):
    st.subheader("🧠 Analyse du marché locatif")

    a1 = s1.get("Appartement")
    a2 = s2.get("Appartement")
    m1 = s1.get("Maison")
    m2 = s2.get("Maison")

    lignes = []

    if a1 and a2:
        diff_a = a2["loyer_m2"] - a1["loyer_m2"]
        plus_a = ville2 if diff_a > 0 else ville1
        lignes.append(
            f"**🏢 Appartements** : {plus_a} est plus chère de **{abs(diff_a):.2f} €/m²** "
            f"({max(a1['loyer_m2'], a2['loyer_m2']):.2f} €/m² vs "
            f"{min(a1['loyer_m2'], a2['loyer_m2']):.2f} €/m²)."
        )

    if m1 and m2:
        diff_m = m2["loyer_m2"] - m1["loyer_m2"]
        plus_m = ville2 if diff_m > 0 else ville1
        lignes.append(
            f"**🏠 Maisons** : {plus_m} est plus chère de **{abs(diff_m):.2f} €/m²** "
            f"({max(m1['loyer_m2'], m2['loyer_m2']):.2f} €/m² vs "
            f"{min(m1['loyer_m2'], m2['loyer_m2']):.2f} €/m²)."
        )

    if a1 and m1:
        diff_v1 = a1["loyer_m2"] - m1["loyer_m2"]
        lignes.append(
            f"**📊 À {ville1}** : les appartements coûtent "
            f"{'plus' if diff_v1 > 0 else 'moins'} cher que les maisons "
            f"({abs(diff_v1):.2f} €/m² d'écart)."
        )

    if a2 and m2:
        diff_v2 = a2["loyer_m2"] - m2["loyer_m2"]
        lignes.append(
            f"**📊 À {ville2}** : les appartements coûtent "
            f"{'plus' if diff_v2 > 0 else 'moins'} cher que les maisons "
            f"({abs(diff_v2):.2f} €/m² d'écart)."
        )

    if lignes:
        for l in lignes:
            st.markdown(f"- {l}")
    else:
        st.info("Données insuffisantes pour l'analyse.")

    st.markdown("""
---
**ℹ️ À propos des données**

Les loyers sont issus du **modèle de prédiction DHUP** (Direction de l'Habitat, de l'Urbanisme et des Paysages).
Il s'agit de **loyers de référence estimés** — non des loyers réels observés — basés sur les déclarations fiscales.

- `niveau_prediction = "commune"` : l'estimation est fiable au niveau de la commune.
- `niveau_prediction = "maille"` : l'estimation est mutualisée avec les communes voisines (moins précise).
- Le **R² ajusté** mesure la qualité du modèle (proche de 1 = très bon).
    """)


# ─────────────────────────────────────────────
# FONCTION PRINCIPALE
# ─────────────────────────────────────────────
def show_logement(ville1, ville2, v1_info, v2_info):
    st.header("🏠 Logement")
    st.caption(
        f"Comparaison : **{ville1}** vs **{ville2}** · "
        "Source : DHUP — pred-app-mef-dhup.csv & pred-mai-mef-dhup.csv"
    )

    df = load_logement()
    if df is None:
        st.error(
            "❌ Fichier `data/clean/logement.csv` introuvable.\n\n"
            "Exécute : `python prepare_data.py`"
        )
        return

    df1 = get_ville_logement(df, ville1)
    df2 = get_ville_logement(df, ville2)

    if df1.empty:
        st.warning(f"⚠️ Aucune donnée logement pour **{ville1}**.")
    if df2.empty:
        st.warning(f"⚠️ Aucune donnée logement pour **{ville2}**.")

    s1 = get_stats(df1) if not df1.empty else {}
    s2 = get_stats(df2) if not df2.empty else {}

    onglet1, onglet2, onglet3, onglet4 = st.tabs([
        "💶 Chiffres clés",
        "📊 Comparaison",
        "🏆 Classement national",
        "🧠 Analyse",
    ])

    with onglet1:
        tab_kpis(ville1, ville2, s1, s2)
    with onglet2:
        tab_comparaison(ville1, ville2, s1, s2)
    with onglet3:
        tab_classement(df, ville1, ville2)
    with onglet4:
        tab_analyse(ville1, ville2, s1, s2)

    with st.expander("📚 Sources de données"):
        st.markdown("""
| Dataset | Description | Source |
|---|---|---|
| pred-app-mef-dhup.csv | Loyers de référence appartements au m² | [DHUP / data.gouv.fr](https://www.data.gouv.fr) |
| pred-mai-mef-dhup.csv | Loyers de référence maisons au m² | [DHUP / data.gouv.fr](https://www.data.gouv.fr) |
        """)