"""
Module Logement — Comparaison Paris vs Marseille
SAE Outils Décisionnels

Sources :
- Paris    : Logements_Paris.xlsx    (Open Data / INSEE)
- Marseille: Logements_Marseille.xlsx (Open Data / INSEE)

Colonnes attendues :
  - "Nombre de logements"  : int ou float
  - "Année d'autorisation" : int
  - "GeoPoint"             : "lat,lon"  (optionnel, pour la carte)

Usage : from logement_module import show_logement
        show_logement()

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
BASE_DIR       = os.path.dirname(__file__)
PATH_LOG_PARIS = os.path.join(BASE_DIR, "data", "Logements_Paris.xlsx")
PATH_LOG_MARS  = os.path.join(BASE_DIR, "data", "Logements_Marseille.xlsx")

# ─────────────────────────────────────────────
# COULEURS
# ─────────────────────────────────────────────
COLOR_PARIS     = "#1f77b4"
COLOR_MARSEILLE = "#d62728"


# ─────────────────────────────────────────────
# CHARGEMENT & NETTOYAGE
# ─────────────────────────────────────────────
@st.cache_data
def load_logements():
    df_paris = pd.read_excel(PATH_LOG_PARIS)
    df_mars  = pd.read_excel(PATH_LOG_MARS)

    df_paris["ville"] = "Paris"
    df_mars["ville"]  = "Marseille"
    df = pd.concat([df_paris, df_mars], ignore_index=True)

    df = df.rename(columns={
        "Nombre de logements":  "nb_logements",
        "Annee d autorisation": "annee",
    })
    # Fallback si le nom de colonne est different
    if "annee" not in df.columns:
        for c in df.columns:
            if "ann" in c.lower() and "auto" in c.lower():
                df = df.rename(columns={c: "annee"})
                break

    df["annee"] = pd.to_numeric(df["annee"], errors="coerce")
    df["nb_logements"] = pd.to_numeric(
        df["nb_logements"].astype(str).str.replace(",", "."), errors="coerce"
    )
    df = df.dropna(subset=["annee", "nb_logements"])
    df["annee"] = df["annee"].astype(int)

    return df, df_paris, df_mars


@st.cache_data
def build_grouped(df):
    return df.groupby(["annee", "ville"])["nb_logements"].sum().reset_index()


def fmt(n):
    return f"{int(n):,}".replace(",", "\u202f")


def latest_common_year(df_grouped):
    y_p = set(df_grouped[df_grouped["ville"] == "Paris"]["annee"])
    y_m = set(df_grouped[df_grouped["ville"] == "Marseille"]["annee"])
    common = sorted(y_p & y_m)
    return int(common[-1]) if common else None


def get_val(df_grouped, ville, annee):
    rows = df_grouped[
        (df_grouped["ville"] == ville) & (df_grouped["annee"] == annee)
    ]["nb_logements"]
    return int(rows.values[0]) if len(rows) > 0 else 0


# ─────────────────────────────────────────────
# ONGLET 1 — VUE GLOBALE
# ─────────────────────────────────────────────
def tab_vue_globale(df_grouped, latest_year):
    st.subheader(f"Résumé du parc de logements — {latest_year}")

    paris_val = get_val(df_grouped, "Paris",     latest_year)
    mars_val  = get_val(df_grouped, "Marseille", latest_year)
    ratio     = paris_val / mars_val if mars_val > 0 else 0
    ecart     = paris_val - mars_val

    # ── KPIs ─────────────────────────────────
    col1, col2, col3 = st.columns(3)
    col1.metric("🗼 Logements Paris",     fmt(paris_val))
    col2.metric(
        "⚓ Logements Marseille", fmt(mars_val),
        delta=f"{fmt(mars_val - paris_val)} vs Paris",
    )
    col3.metric("📊 Ratio Paris / Marseille", f"{ratio:.1f}×")

    st.divider()

    # ── Jauges ───────────────────────────────
    st.markdown("#### Visualisation comparative")
    max_val = max(paris_val, mars_val) * 1.25
    fig_gauge = go.Figure()
    for i, (nom, val, color) in enumerate([
        ("Paris",     paris_val, COLOR_PARIS),
        ("Marseille", mars_val,  COLOR_MARSEILLE),
    ]):
        fig_gauge.add_trace(go.Indicator(
            mode="gauge+number",
            value=val,
            title={"text": nom, "font": {"size": 14}},
            number={"valueformat": ",.0f"},
            gauge={
                "axis": {"range": [0, max_val]},
                "bar":  {"color": color},
                "steps": [
                    {"range": [0,               max_val * 0.33], "color": "#d4edda"},
                    {"range": [max_val * 0.33,  max_val * 0.66], "color": "#fff3cd"},
                    {"range": [max_val * 0.66,  max_val],        "color": "#f8d7da"},
                ],
            },
            domain={"column": i, "row": 0},
        ))
    fig_gauge.update_layout(
        grid={"rows": 1, "columns": 2}, height=240, margin=dict(t=30, b=0)
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

    # ── Analyse automatique ───────────────────
    st.divider()
    st.markdown("#### 💡 Lecture des chiffres")
    st.info(
        f"En **{latest_year}**, Paris comptabilise **{fmt(paris_val)} logements autorisés**, "
        f"soit **{ratio:.1f}× plus** que Marseille ({fmt(mars_val)}). "
        f"Cet écart de **{fmt(ecart)}** logements reflète directement la différence de population "
        f"et de densité urbaine entre les deux villes. "
        f"Paris, avec sa forte pression foncière, génère mécaniquement davantage de demandes "
        f"d'autorisation de construction, tandis que Marseille, plus étendue, "
        f"dispose de réserves foncières plus importantes."
    )


# ─────────────────────────────────────────────
# ONGLET 2 — ÉVOLUTION TEMPORELLE
# ─────────────────────────────────────────────
def tab_evolution(df_grouped):
    st.subheader("📈 Évolution du nombre de logements autorisés")
    st.caption("Données annuelles agrégées — source : Logements_Paris.xlsx & Logements_Marseille.xlsx")

    # ── Courbe principale ─────────────────────
    df_plot = df_grouped.copy()
    df_plot["label"] = df_plot.apply(
        lambda r: f"{int(r['nb_logements'] / 1000)}k" if r["annee"] % 2 == 0 else "",
        axis=1,
    )

    fig = px.line(
        df_plot, x="annee", y="nb_logements", color="ville",
        markers=True,
        color_discrete_map={"Paris": COLOR_PARIS, "Marseille": COLOR_MARSEILLE},
        labels={"annee": "Année", "nb_logements": "Nb logements autorisés", "ville": "Ville"},
    )
    fig.update_traces(
        mode="lines+markers+text",
        text=df_plot["label"],
        textposition="top center",
        line=dict(width=2.5),
        marker=dict(size=7),
    )
    fig.update_traces(hovertemplate="<b>%{x}</b><br>%{y:,.0f} logements<extra></extra>")
    fig.update_layout(height=430, hovermode="x unified", margin=dict(t=20))
    st.plotly_chart(fig, use_container_width=True)

    # ── Analyse tendance ─────────────────────
    st.divider()
    st.markdown("#### 📌 Lecture de la tendance")
    col_p, col_m = st.columns(2)
    for col, ville in [(col_p, "Paris"), (col_m, "Marseille")]:
        sub = df_grouped[df_grouped["ville"] == ville].sort_values("annee")
        if len(sub) >= 2:
            debut = sub.iloc[0]
            fin   = sub.iloc[-1]
            delta = fin["nb_logements"] - debut["nb_logements"]
            pic   = sub.loc[sub["nb_logements"].idxmax()]
            creux = sub.loc[sub["nb_logements"].idxmin()]
            signe = "📈" if delta > 0 else "📉"
            with col:
                emoji = "🗼" if ville == "Paris" else "⚓"
                st.markdown(f"**{emoji} {ville}**")
                st.markdown(
                    f"- {signe} Évolution : {fmt(int(debut['nb_logements']))} ({int(debut['annee'])}) "
                    f"→ **{fmt(int(fin['nb_logements']))}** ({int(fin['annee'])})\n"
                    f"- 🔝 Pic : **{fmt(int(pic['nb_logements']))}** en **{int(pic['annee'])}**\n"
                    f"- 🔻 Creux : **{fmt(int(creux['nb_logements']))}** en **{int(creux['annee'])}**"
                )

    st.divider()

    # ── Variation annuelle ────────────────────
    st.markdown("#### 📊 Variation annuelle (% par rapport à l'année précédente)")
    records = []
    for ville in ["Paris", "Marseille"]:
        sub = df_grouped[df_grouped["ville"] == ville].sort_values("annee").copy()
        sub["variation"] = sub["nb_logements"].pct_change() * 100
        sub = sub.dropna(subset=["variation"])
        records.append(sub)
    df_var = pd.concat(records)

    fig_var = px.bar(
        df_var, x="annee", y="variation", color="ville", barmode="group",
        color_discrete_map={"Paris": COLOR_PARIS, "Marseille": COLOR_MARSEILLE},
        labels={"annee": "Année", "variation": "Variation (%)", "ville": "Ville"},
    )
    fig_var.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
    fig_var.update_layout(height=320, margin=dict(t=20))
    st.plotly_chart(fig_var, use_container_width=True)
    st.caption(
        "👉 Les barres positives indiquent une hausse des autorisations par rapport à l'année "
        "précédente. Les fortes variations peuvent refléter des politiques de construction "
        "ou des effets conjoncturels (crise, relance…)."
    )


# ─────────────────────────────────────────────
# ONGLET 3 — COMPARAISON ANNUELLE
# ─────────────────────────────────────────────
def tab_comparaison(df_grouped):
    st.subheader("📊 Comparaison directe sur une année donnée")

    annees_communes = sorted(
        set(df_grouped[df_grouped["ville"] == "Paris"]["annee"]) &
        set(df_grouped[df_grouped["ville"] == "Marseille"]["annee"])
    )
    if not annees_communes:
        st.warning("Aucune année commune disponible.")
        return

    annee_sel = st.select_slider(
        "📅 Choisir une année :", options=annees_communes, value=annees_communes[-1]
    )

    paris_val = get_val(df_grouped, "Paris",     annee_sel)
    mars_val  = get_val(df_grouped, "Marseille", annee_sel)
    ratio     = paris_val / mars_val if mars_val > 0 else 0

    # ── KPIs ─────────────────────────────────
    col1, col2, col3 = st.columns(3)
    col1.metric("🗼 Paris",     fmt(paris_val))
    col2.metric("⚓ Marseille", fmt(mars_val))
    col3.metric("📊 Ratio",     f"{ratio:.1f}×")
    st.divider()

    # ── Graphiques ───────────────────────────
    df_sel = df_grouped[df_grouped["annee"] == annee_sel]
    col_bar, col_pie = st.columns(2)

    with col_bar:
        st.markdown(f"**Logements autorisés en {annee_sel}**")
        fig_bar = px.bar(
            df_sel, x="ville", y="nb_logements", color="ville",
            color_discrete_map={"Paris": COLOR_PARIS, "Marseille": COLOR_MARSEILLE},
            text="nb_logements",
        )
        fig_bar.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
        fig_bar.update_layout(height=360, showlegend=False, yaxis_title="Nb logements")
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_pie:
        st.markdown(f"**Répartition en {annee_sel}**")
        fig_pie = px.pie(
            df_sel, values="nb_logements", names="ville",
            color="ville",
            color_discrete_map={"Paris": COLOR_PARIS, "Marseille": COLOR_MARSEILLE},
            hole=0.4,
        )
        fig_pie.update_traces(textinfo="percent+label")
        fig_pie.update_layout(height=360)
        st.plotly_chart(fig_pie, use_container_width=True)

    # ── Interprétation ────────────────────────
    st.divider()
    st.markdown("#### 💡 Interprétation")
    pct_paris = paris_val / (paris_val + mars_val) * 100 if (paris_val + mars_val) > 0 else 0
    st.info(
        f"En **{annee_sel}**, Paris représente **{pct_paris:.0f}%** du total des logements autorisés "
        f"dans les deux villes ({fmt(paris_val)} contre {fmt(mars_val)} à Marseille). "
        f"Ce ratio de **{ratio:.1f}×** est cohérent avec la différence de population "
        f"(Paris ≈ 2,1 M hab. vs Marseille ≈ 870 000 hab.)."
    )


# ─────────────────────────────────────────────
# ONGLET 4 — CARTE GÉOGRAPHIQUE
# ─────────────────────────────────────────────
def tab_carte(df_raw):
    st.subheader("🗺️ Répartition géographique des logements autorisés")

    if "GeoPoint" not in df_raw.columns:
        st.info("ℹ️ Colonne 'GeoPoint' absente des données — carte non disponible.")
        return

    df_map = df_raw.copy()
    coords = df_map["GeoPoint"].astype(str).str.split(",", expand=True)
    df_map["lat"] = pd.to_numeric(coords[0], errors="coerce")
    df_map["lon"] = pd.to_numeric(coords[1], errors="coerce")
    df_map["nb_logements"] = pd.to_numeric(
        df_map["nb_logements"].astype(str).str.replace(",", "."), errors="coerce"
    )
    df_map["annee"] = pd.to_numeric(df_map["annee"], errors="coerce")
    df_map = df_map.dropna(subset=["lat", "lon", "nb_logements", "annee"])

    if df_map.empty:
        st.warning("⚠️ Aucune coordonnée valide après nettoyage.")
        return

    annee_min = int(df_map["annee"].min())
    annee_max = int(df_map["annee"].max())
    annee_sel = st.slider("📅 Choisir une année :", annee_min, annee_max, annee_max)
    df_filtered = df_map[df_map["annee"] == annee_sel]
    st.caption(f"📍 {len(df_filtered)} points affichés pour {annee_sel}.")

    fig_map = px.scatter_mapbox(
        df_filtered, lat="lat", lon="lon",
        color="ville", size="nb_logements",
        color_discrete_map={"Paris": COLOR_PARIS, "Marseille": COLOR_MARSEILLE},
        hover_name="ville",
        hover_data={"nb_logements": True, "annee": True, "lat": False, "lon": False},
        zoom=4.5,
        center={"lat": 46.6, "lon": 2.5},
        height=550,
    )
    fig_map.update_layout(
        mapbox_style="carto-positron",
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
    )
    st.plotly_chart(fig_map, use_container_width=True)
    st.caption(
        "👉 La taille des bulles est proportionnelle au nombre de logements autorisés. "
        "Paris concentre ses autorisations dans une zone dense, tandis que Marseille "
        "montre une dispersion plus large liée à son territoire étendu (240 km²)."
    )


# ─────────────────────────────────────────────
# ONGLET 5 — ANALYSE APPROFONDIE
# ─────────────────────────────────────────────
def tab_analyse(df_grouped, latest_year):
    st.subheader("🧠 Analyse approfondie du marché du logement")

    paris_val = get_val(df_grouped, "Paris",     latest_year)
    mars_val  = get_val(df_grouped, "Marseille", latest_year)
    ratio     = paris_val / mars_val if mars_val > 0 else 0

    # ── Contexte général ─────────────────────
    st.markdown("#### 🏙️ Contexte et différences structurelles")
    col_p, col_m = st.columns(2)

    with col_p:
        st.markdown(f"""
**🗼 Paris — {fmt(paris_val)} logements en {latest_year}**

Paris est soumise à une **pression foncière extrême** : prix au m² parmi
les plus élevés d'Europe et superficie limitée à **105 km²**.
Les politiques de construction sont contraintes par :
- La densité déjà très élevée (≈ 20 000 hab/km²).
- La préservation du patrimoine architectural.
- Un marché locatif sous tension (~60 % de locataires).
        """)

    with col_m:
        st.markdown(f"""
**⚓ Marseille — {fmt(mars_val)} logements en {latest_year}**

Marseille dispose de **réserves foncières bien plus importantes** sur ses
**240 km²** de territoire. Le marché y est structurellement différent :
- Des prix au m² nettement inférieurs (~2× moins chers qu'à Paris).
- Une part de propriétaires plus élevée.
- Des inégalités marquées entre les arrondissements nord et sud.
        """)

    st.divider()

    # ── Top 3 années ──────────────────────────
    st.markdown("#### 📊 Années clés par ville")
    col_a, col_b = st.columns(2)
    for col, ville in [(col_a, "Paris"), (col_b, "Marseille")]:
        sub = df_grouped[df_grouped["ville"] == ville].sort_values("nb_logements", ascending=False)
        with col:
            emoji = "🗼" if ville == "Paris" else "⚓"
            st.markdown(f"**{emoji} {ville} — Top 3 années**")
            for _, row in sub.head(3).iterrows():
                st.markdown(f"- **{int(row['annee'])}** : {fmt(int(row['nb_logements']))} logements")

    st.divider()

    # ── Évolution relative base 100 ───────────
    st.markdown("#### 📈 Évolution relative (base 100 = première année disponible)")
    st.caption(
        "Permet de comparer les dynamiques de croissance indépendamment des volumes absolus."
    )
    records = []
    for ville in ["Paris", "Marseille"]:
        sub = df_grouped[df_grouped["ville"] == ville].sort_values("annee").copy()
        if len(sub) > 0:
            base = sub.iloc[0]["nb_logements"]
            if base > 0:
                sub["indice"] = sub["nb_logements"] / base * 100
                records.append(sub)

    if records:
        df_idx = pd.concat(records)
        fig_idx = px.line(
            df_idx, x="annee", y="indice", color="ville",
            markers=True,
            color_discrete_map={"Paris": COLOR_PARIS, "Marseille": COLOR_MARSEILLE},
            labels={"annee": "Année", "indice": "Indice (base 100)", "ville": "Ville"},
        )
        fig_idx.add_hline(y=100, line_dash="dash", line_color="gray", line_width=1,
                          annotation_text="base 100")
        fig_idx.update_traces(line_width=2.5, marker_size=6)
        fig_idx.update_layout(height=360, margin=dict(t=20))
        st.plotly_chart(fig_idx, use_container_width=True)
        st.caption(
            "👉 Un indice > 100 signifie que la ville a augmenté ses autorisations par rapport "
            "à sa propre première année de référence — indépendamment des volumes absolus."
        )

    st.divider()

    # ── Synthèse ──────────────────────────────
    st.markdown("#### 📌 Synthèse comparative")
    st.success(
        f"L'écart entre Paris (**{fmt(paris_val)}**) et Marseille (**{fmt(mars_val)}**) "
        f"est un facteur **{ratio:.1f}×**, ce qui reflète fidèlement la différence de population.\n\n"
        "Les deux villes font face à des défis distincts : "
        "Paris doit **densifier encore** un tissu urbain déjà saturé, "
        "tandis que Marseille cherche à **rééquilibrer son territoire** en favorisant "
        "la réhabilitation des quartiers nord et la maîtrise de l'étalement urbain au sud."
    )


# ─────────────────────────────────────────────
# FONCTION PRINCIPALE
# ─────────────────────────────────────────────
def show_logement():
    st.header("🏠 Logement")
    st.caption(
        "Sources : Logements_Paris.xlsx · Logements_Marseille.xlsx (INSEE / Open Data) · "
        "Données : autorisations de construction par année"
    )

    with st.spinner("Chargement des données logement..."):
        df_raw, _, _ = load_logements()
        df_grouped   = build_grouped(df_raw)
        latest_year  = latest_common_year(df_grouped)

    if latest_year is None:
        st.error("❌ Impossible de trouver une année commune entre Paris et Marseille.")
        return

    st.info(f"📅 Année de référence pour la comparaison : **{latest_year}**")

    onglet1, onglet2, onglet3, onglet4, onglet5 = st.tabs([
        "📊 Vue globale",
        "📈 Évolution",
        "📊 Comparaison annuelle",
        "🗺️ Carte",
        "🧠 Analyse approfondie",
    ])

    with onglet1:
        tab_vue_globale(df_grouped, latest_year)

    with onglet2:
        tab_evolution(df_grouped)

    with onglet3:
        tab_comparaison(df_grouped)

    with onglet4:
        tab_carte(df_raw)

    with onglet5:
        tab_analyse(df_grouped, latest_year)

    with st.expander("📚 Sources de données"):
        st.markdown("""
| Dataset | Ville | Source |
|---|---|---|
| Logements autorisés | Paris | [Open Data Paris](https://opendata.paris.fr) / INSEE |
| Logements autorisés | Marseille | [Open Data AMP](https://data.ampmetropole.fr) / INSEE |

> ⚠️ Les données correspondent aux **autorisations de construction** délivrées par année,
> pas au parc total de logements existants.
        """)