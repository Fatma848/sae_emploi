"""
Module Données Générales — Comparateur de villes françaises
SAE Outils Décisionnels

Usage : from modules.donnees_generales_module import show_donnees_generales
        show_donnees_generales(ville1, ville2, v1_info, v2_info)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

COLOR_V1 = "#1f77b4"
COLOR_V2 = "#d62728"


def fmt(n):
    try:
        return f"{int(float(n)):,}".replace(",", "\u202f")
    except Exception:
        return str(n)


# ─────────────────────────────────────────────
# ONGLET 1 — CHIFFRES CLÉS
# ─────────────────────────────────────────────
def tab_kpis(ville1, ville2, v1, v2):
    st.subheader("Indicateurs clés")
    st.caption("Source : INSEE / communes_france_2025.csv")

    champs = [
        ("👥 Population",         "population"),
        ("🏙️ Densité (hab/km²)",  "densite"),
        ("📏 Superficie (km²)",   "superficie_km2"),
        ("📍 Département",        "departement"),
        ("🌐 Région",             "region"),
    ]

    col_label, col_v1, col_v2 = st.columns([1.5, 2, 2])
    col_label.markdown(f"**Indicateur**")
    col_v1.markdown(f"**🔵 {ville1}**")
    col_v2.markdown(f"**🔴 {ville2}**")

    for label, key in champs:
        val1 = v1.get(key)
        val2 = v2.get(key)
        if val1 is None and val2 is None:
            continue
        c1, c2, c3 = st.columns([1.5, 2, 2])
        c1.markdown(f"**{label}**")

        # Delta numérique si possible
        try:
            n1, n2 = float(val1), float(val2)
            delta = f"{n2 - n1:+,.0f}".replace(",", "\u202f")
            c2.metric("", fmt(n1))
            c3.metric("", fmt(n2), delta=delta)
        except Exception:
            c2.metric("", str(val1) if val1 else "N/D")
            c3.metric("", str(val2) if val2 else "N/D")

    st.divider()

    # Jauges population
    pop1 = v1.get("population")
    pop2 = v2.get("population")
    if pop1 and pop2:
        st.markdown("#### 📊 Population comparée")
        max_pop = max(float(pop1), float(pop2)) * 1.2
        fig = go.Figure()
        for i, (nom, val, color) in enumerate([
            (ville1, float(pop1), COLOR_V1),
            (ville2, float(pop2), COLOR_V2),
        ]):
            fig.add_trace(go.Indicator(
                mode="gauge+number",
                value=val,
                title={"text": nom, "font": {"size": 13}},
                number={"valueformat": ",.0f"},
                gauge={
                    "axis": {"range": [0, max_pop]},
                    "bar": {"color": color},
                    "steps": [
                        {"range": [0,             max_pop * 0.33], "color": "#d4edda"},
                        {"range": [max_pop * 0.33, max_pop * 0.66], "color": "#fff3cd"},
                        {"range": [max_pop * 0.66, max_pop],        "color": "#f8d7da"},
                    ],
                },
                domain={"column": i, "row": 0},
            ))
        fig.update_layout(grid={"rows": 1, "columns": 2}, height=240, margin=dict(t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)

        ratio = float(pop1) / float(pop2) if float(pop2) > 0 else 1
        plus_grande = ville1 if ratio > 1 else ville2
        st.markdown(
            f"> 👉 **{plus_grande}** est la ville la plus peuplée des deux, "
            f"avec un ratio de population de **{max(ratio, 1/ratio):.1f}×**."
        )


# ─────────────────────────────────────────────
# ONGLET 2 — COMPARAISON VISUELLE
# ─────────────────────────────────────────────
def tab_comparaison(ville1, ville2, v1, v2):
    st.subheader("Comparaison visuelle")

    indicateurs_num = {}
    for key, label in [
        ("population",     "👥 Population"),
        ("densite",        "🏙️ Densité (hab/km²)"),
        ("superficie_km2", "📏 Superficie (km²)"),
    ]:
        val1 = v1.get(key)
        val2 = v2.get(key)
        if val1 is not None and val2 is not None:
            try:
                indicateurs_num[label] = {"ville1": float(val1), "ville2": float(val2)}
            except Exception:
                pass

    if not indicateurs_num:
        st.info("ℹ️ Données numériques insuffisantes pour la comparaison visuelle.")
        return

    choix = st.selectbox("Choisir un indicateur :", list(indicateurs_num.keys()))
    vals = indicateurs_num[choix]

    df_bar = pd.DataFrame({
        "Ville": [ville1, ville2],
        "Valeur": [vals["ville1"], vals["ville2"]],
    })

    fig_bar = px.bar(
        df_bar, x="Ville", y="Valeur", color="Ville",
        color_discrete_map={ville1: COLOR_V1, ville2: COLOR_V2},
        text="Valeur",
        title=f"Comparaison — {choix}",
    )
    fig_bar.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig_bar.update_layout(height=380, showlegend=False)
    st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    # Camembert population
    if "👥 Population" in indicateurs_num:
        st.markdown("#### 🥧 Répartition de la population")
        vals_pop = indicateurs_num["👥 Population"]
        df_pie = pd.DataFrame({
            "Ville":  [ville1, ville2],
            "Population": [vals_pop["ville1"], vals_pop["ville2"]],
        })
        fig_pie = px.pie(
            df_pie, values="Population", names="Ville",
            color="Ville",
            color_discrete_map={ville1: COLOR_V1, ville2: COLOR_V2},
            hole=0.4,
        )
        fig_pie.update_traces(textinfo="percent+label")
        fig_pie.update_layout(height=350)
        st.plotly_chart(fig_pie, use_container_width=True)


# ─────────────────────────────────────────────
# ONGLET 3 — CARTE
# ─────────────────────────────────────────────
def tab_carte(ville1, ville2, v1, v2):
    st.subheader("🗺️ Localisation des deux villes")

    lat1 = v1.get("latitude")
    lon1 = v1.get("longitude")
    lat2 = v2.get("latitude")
    lon2 = v2.get("longitude")

    if not (lat1 and lon1 and lat2 and lon2):
        st.info("ℹ️ Coordonnées GPS non disponibles pour l'une des villes.")
        return

    map_df = pd.DataFrame({
        "Ville":      [ville1, ville2],
        "lat":        [float(lat1), float(lat2)],
        "lon":        [float(lon1), float(lon2)],
        "population": [
            int(float(v1.get("population", 100000))),
            int(float(v2.get("population", 100000))),
        ],
    })

    lat_center = (float(lat1) + float(lat2)) / 2
    lon_center = (float(lon1) + float(lon2)) / 2

    fig = px.scatter_mapbox(
        map_df, lat="lat", lon="lon",
        color="Ville", size="population",
        color_discrete_map={ville1: COLOR_V1, ville2: COLOR_V2},
        hover_name="Ville",
        hover_data={"population": True, "lat": False, "lon": False},
        zoom=4.5,
        center={"lat": lat_center, "lon": lon_center},
        height=500,
    )
    fig.update_layout(
        mapbox_style="carto-positron",
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("La taille des bulles est proportionnelle à la population.")


# ─────────────────────────────────────────────
# ONGLET 4 — ANALYSE
# ─────────────────────────────────────────────
def tab_analyse(ville1, ville2, v1, v2):
    st.subheader("🧠 Analyse comparative")

    pop1  = v1.get("population")
    pop2  = v2.get("population")
    den1  = v1.get("densite")
    den2  = v2.get("densite")
    sup1  = v1.get("superficie_km2")
    sup2  = v2.get("superficie_km2")
    dep1  = v1.get("departement", "N/D")
    dep2  = v2.get("departement", "N/D")
    reg1  = v1.get("region", "N/D")
    reg2  = v2.get("region", "N/D")

    lignes = []

    if pop1 and pop2:
        try:
            p1, p2 = float(pop1), float(pop2)
            plus_pop = ville1 if p1 > p2 else ville2
            ratio_pop = max(p1, p2) / min(p1, p2)
            lignes.append(
                f"**👥 Population** : {ville1} ({fmt(p1)} hab.) vs {ville2} ({fmt(p2)} hab.). "
                f"**{plus_pop}** est **{ratio_pop:.1f}× plus peuplée**."
            )
        except Exception:
            pass

    if den1 and den2:
        try:
            d1, d2 = float(den1), float(den2)
            plus_dense = ville1 if d1 > d2 else ville2
            ratio_den = max(d1, d2) / min(d1, d2)
            lignes.append(
                f"**🏙️ Densité** : {plus_dense} est **{ratio_den:.1f}× plus dense** "
                f"({fmt(max(d1,d2))} hab/km² contre {fmt(min(d1,d2))} hab/km²)."
            )
        except Exception:
            pass

    if sup1 and sup2:
        try:
            s1, s2 = float(sup1), float(sup2)
            plus_grande = ville1 if s1 > s2 else ville2
            ratio_sup = max(s1, s2) / min(s1, s2)
            lignes.append(
                f"**📏 Superficie** : {plus_grande} est **{ratio_sup:.1f}× plus étendue** "
                f"({max(s1,s2):.0f} km² contre {min(s1,s2):.0f} km²)."
            )
        except Exception:
            pass

    lignes.append(f"**📍 Département** : {ville1} → {dep1} | {ville2} → {dep2}")
    lignes.append(f"**🌐 Région** : {ville1} → {reg1} | {ville2} → {reg2}")

    for ligne in lignes:
        st.markdown(f"- {ligne}")


# ─────────────────────────────────────────────
# FONCTION PRINCIPALE
# ─────────────────────────────────────────────
def show_donnees_generales(ville1, ville2, v1_info, v2_info):
    st.header("📊 Données générales")
    st.caption(f"Comparaison : **{ville1}** vs **{ville2}** · Source : INSEE / communes_france_2025.csv")

    if not v1_info or not v2_info:
        st.warning("⚠️ Données introuvables pour l'une des villes sélectionnées.")
        return

    onglet1, onglet2, onglet3, onglet4 = st.tabs([
        "🔑 Chiffres clés",
        "📊 Comparaison",
        "🗺️ Carte",
        "🧠 Analyse",
    ])

    with onglet1:
        tab_kpis(ville1, ville2, v1_info, v2_info)
    with onglet2:
        tab_comparaison(ville1, ville2, v1_info, v2_info)
    with onglet3:
        tab_carte(ville1, ville2, v1_info, v2_info)
    with onglet4:
        tab_analyse(ville1, ville2, v1_info, v2_info)

    with st.expander("📚 Source de données"):
        st.markdown("""
| Dataset | Description | Source |
|---|---|---|
| communes_france_2025.csv | Population, densité, superficie, coordonnées GPS | INSEE / Open Data |
        """)