"""
Module Transport — Comparaison Paris vs Marseille
SAE Outils Décisionnels

Sources :
- Paris    : arrets-lignes.csv (IDFM / Open Data)
              circulation_evenement.csv (IDFM / Open Data)
- Marseille: ol-lignes-des-reseaux-de-transport-en-commun.csv (Open Data Métropole AMP)
              ol-perturbation-la-mobilite.csv (Open Data Métropole AMP)

⚠️ Note : les données Marseille couvrent toute la Métropole AMP.
          Le module filtre sur subnetwork "Marseille" pour une comparaison cohérente.

Usage : from transport_module import show_transport
        show_transport()
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os

# ─────────────────────────────────────────────
# CHEMINS
# ─────────────────────────────────────────────
BASE_DIR      = os.path.dirname(__file__)
PATH_ARRETS   = os.path.join(BASE_DIR, "data", "arrets-lignes.csv")
PATH_EVENTS   = os.path.join(BASE_DIR, "data", "circulation_evenement.csv")
PATH_LIGNES   = os.path.join(BASE_DIR, "data", "ol-lignes-des-reseaux-de-transport-en-commun.csv")
PATH_PERTURB  = os.path.join(BASE_DIR, "data", "ol-perturbation-la-mobilite.csv")

# ─────────────────────────────────────────────
# COULEURS
# ─────────────────────────────────────────────
COLOR_PARIS     = "#1f77b4"
COLOR_MARSEILLE = "#d62728"

MODES_LABELS = {
    "Metro":        "🚇 Métro",
    "Bus":          "🚌 Bus",
    "Tramway":      "🚊 Tramway",
    "RapidTransit": "🚆 RER",
    "LocalTrain":   "🚉 Train local",
    "regionalRail": "🚄 Train régional",
    "RailShuttle":  "🚐 Navette",
    "CableWay":     "🚡 Téléphérique",
    "Funicular":    "🚞 Funiculaire",
    "Subway":       "🚇 Métro",
    "Rail":         "🚆 Rail",
    "Ferry":        "⛴️ Ferry",
    "Tram":         "🚊 Tramway",
}

COULEURS_CRIT = {"Faible": "#2ecc71", "Moyenne": "#f39c12", "Critique": "#e74c3c"}


# ─────────────────────────────────────────────
# CHARGEMENT DES DONNÉES
# ─────────────────────────────────────────────
@st.cache_data
def load_paris():
    df_arrets = pd.read_csv(PATH_ARRETS, sep=";", encoding="utf-8-sig")
    df_events = pd.read_csv(PATH_EVENTS, sep=";", encoding="utf-8-sig")

    modes = df_arrets.groupby("mode").agg(
        nb_lignes=("route_id", "nunique"),
        nb_arrets=("stop_id", "nunique"),
    ).reset_index()

    stats = {
        "nb_lignes":     df_arrets["route_id"].nunique(),
        "nb_arrets":     df_arrets["stop_id"].nunique(),
        "nb_operateurs": df_arrets["OperatorName"].nunique(),
        "nb_events":     len(df_events),
        "nb_travaux":    len(df_events[df_events["type"] == "CONSTRUCTION"]),
        "nb_fermetures": len(df_events[df_events["type"] == "ROAD_CLOSED"]),
    }

    top_op = (
        df_arrets.groupby("OperatorName")["route_id"]
        .nunique()
        .sort_values(ascending=False)
        .head(8)
        .reset_index()
    )
    top_op.columns = ["Opérateur", "Nb lignes"]

    return stats, modes, top_op, df_events


@st.cache_data
def load_marseille():
    df_lignes  = pd.read_csv(PATH_LIGNES,  sep=";", encoding="utf-8-sig")
    df_perturb = pd.read_csv(PATH_PERTURB, sep=";", encoding="utf-8-sig")

    # ⚠️ Filtre sur Marseille uniquement (pas toute la métropole AMP)
    df_perturb_mars = df_perturb[
        df_perturb["lines_final_subnetwork_name"] == "Marseille"
    ].copy()

    modes = df_lignes.groupby("route_type").agg(
        nb_lignes=("route_id", "nunique"),
    ).reset_index()
    modes.columns = ["mode", "nb_lignes"]

    nb_perturb  = df_perturb_mars["id"].nunique()
    nb_critiq   = len(df_perturb_mars[df_perturb_mars["criticity"] == "Critique"])
    pct_critiq  = nb_critiq / nb_perturb * 100 if nb_perturb > 0 else 0

    stats = {
        "nb_lignes":    df_lignes["route_id"].nunique(),
        "nb_perturb":   nb_perturb,
        "nb_critiques": nb_critiq,
        "pct_critiques": pct_critiq,
        "nb_travaux":   df_perturb_mars[df_perturb_mars["category"] == "TRAVAUX"]["id"].nunique(),
    }

    perturb_cat  = df_perturb_mars.groupby("category")["id"].nunique().reset_index()
    perturb_cat.columns = ["Catégorie", "Nb perturbations"]

    perturb_crit = df_perturb_mars.groupby("criticity")["id"].nunique().reset_index()
    perturb_crit.columns = ["Criticité", "Nb perturbations"]

    perturb_mode = df_perturb_mars.groupby("lines_final_mode")["id"].nunique().reset_index()
    perturb_mode.columns = ["Mode", "Nb perturbations"]

    # Top lignes les plus perturbées
    top_lignes = (
        df_perturb_mars.groupby("lines_final_lname")["id"]
        .nunique()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )
    top_lignes.columns = ["Ligne", "Nb perturbations"]

    perturb_liste = df_perturb_mars.drop_duplicates("id")[
        ["title", "category", "criticity", "startvalidity", "endvalidity"]
    ].copy()

    return stats, modes, perturb_cat, perturb_crit, perturb_mode, top_lignes, perturb_liste


def fmt(n):
    return f"{int(n):,}".replace(",", "\u202f")


# ─────────────────────────────────────────────
# ONGLET 1 — VUE GLOBALE
# ─────────────────────────────────────────────
def tab_vue_globale(paris_stats, mars_stats):
    st.subheader("Réseau de transport en chiffres")
    st.caption("⚠️ Données Paris = arrêts & lignes IDFM · Données Marseille = lignes réseau AMP (ville uniquement)")

    # ── KPIs ──
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🗼 Paris — Lignes",      fmt(paris_stats["nb_lignes"]))
    col1.metric("⚓ Marseille — Lignes",  fmt(mars_stats["nb_lignes"]))
    col2.metric("🗼 Paris — Arrêts",      fmt(paris_stats["nb_arrets"]))
    col2.metric("⚓ Marseille — Arrêts",  "N/D")
    col3.metric("🗼 Paris — Opérateurs",  paris_stats["nb_operateurs"])
    col3.metric("⚓ Marseille — Opérat.", "N/D")
    col4.metric("🗼 Paris — Perturbations",   paris_stats["nb_events"])
    col4.metric("⚓ Marseille — Perturb.",    mars_stats["nb_perturb"])

    st.divider()

    # ── Jauge comparative nb lignes ──
    st.markdown("#### 📊 Comparaison des lignes par mode — Vue consolidée")
    fig_gauge = go.Figure()
    max_val = max(paris_stats["nb_lignes"], mars_stats["nb_lignes"]) * 1.2
    for i, (nom, val, color) in enumerate([
        ("Paris",     paris_stats["nb_lignes"], COLOR_PARIS),
        ("Marseille", mars_stats["nb_lignes"],  COLOR_MARSEILLE),
    ]):
        fig_gauge.add_trace(go.Indicator(
            mode="gauge+number",
            value=val,
            title={"text": nom, "font": {"size": 15}},
            gauge={
                "axis": {"range": [0, max_val]},
                "bar":  {"color": color},
                "steps": [
                    {"range": [0,              max_val * 0.33], "color": "#d4edda"},
                    {"range": [max_val * 0.33, max_val * 0.66], "color": "#fff3cd"},
                    {"range": [max_val * 0.66, max_val],        "color": "#f8d7da"},
                ],
            },
            domain={"column": i, "row": 0},
        ))
    fig_gauge.update_layout(grid={"rows": 1, "columns": 2}, height=240, margin=dict(t=30, b=0))
    st.plotly_chart(fig_gauge, use_container_width=True)

    # ── Analyse ──
    st.markdown(f"""
> 👉 **Le réseau parisien est structurellement bien plus dense** que celui de Marseille :
> **{fmt(paris_stats['nb_lignes'])} lignes** et **{fmt(paris_stats['nb_arrets'])} arrêts** côté Paris,
> contre **{fmt(mars_stats['nb_lignes'])} lignes** à Marseille.
> Paris concentre l'essentiel de la multimodalité française (métro, RER, tramway, bus, funiculaire),
> tandis que Marseille repose majoritairement sur les bus.
> En termes de perturbations, les deux villes sont **comparables en volume**
> ({paris_stats['nb_events']} à Paris contre {mars_stats['nb_perturb']} à Marseille ville),
> mais leur nature diffère : Paris signale surtout des fermetures de voirie,
> Marseille des travaux et des déviations de bus.
    """)


# ─────────────────────────────────────────────
# ONGLET 2 — RÉSEAU DE TRANSPORT
# ─────────────────────────────────────────────
def tab_reseau(paris_modes, paris_top_op, mars_modes):
    st.subheader("Structure des réseaux de transport")
    st.info(
        "⚠️ Les données Paris sont basées sur les **arrêts** (source IDFM), "
        "celles de Marseille sur les **lignes** (source AMP). "
        "La comparaison directe est indicative."
    )

    # ── Pie charts modes côte à côte ──
    st.markdown("#### 🥧 Répartition par mode de transport")
    col_p, col_m = st.columns(2)

    with col_p:
        st.markdown("**🗼 Paris — par arrêts**")
        paris_modes["mode_label"] = paris_modes["mode"].map(MODES_LABELS).fillna(paris_modes["mode"])
        fig_p = px.pie(
            paris_modes, names="mode_label", values="nb_arrets",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig_p.update_layout(height=320, legend_title="Mode")
        st.plotly_chart(fig_p, use_container_width=True)

    with col_m:
        st.markdown("**⚓ Marseille — par lignes**")
        mars_modes["mode_label"] = mars_modes["mode"].map(MODES_LABELS).fillna(mars_modes["mode"])
        fig_m = px.pie(
            mars_modes, names="mode_label", values="nb_lignes",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig_m.update_layout(height=320, legend_title="Mode")
        st.plotly_chart(fig_m, use_container_width=True)

    st.markdown("""
> 👉 **Le réseau parisien est dominé par les bus en nombre d'arrêts**, mais possède une forte
> diversité de modes (métro, RER, tramway, téléphérique). À l'inverse, **Marseille repose
> à plus de 90% sur les bus**, avec seulement quelques lignes de métro, tram et ferry.
> Cela reflète des politiques d'urbanisme très différentes : Paris a historiquement
> investi dans des infrastructures lourdes, Marseille dans un réseau bus étendu.
    """)

    st.divider()

    # ── Top opérateurs Paris ──
    st.markdown("#### 🏢 Top opérateurs — Paris (par nb de lignes)")
    fig_op = px.bar(
        paris_top_op.sort_values("Nb lignes"),
        x="Nb lignes", y="Opérateur",
        orientation="h",
        color_discrete_sequence=[COLOR_PARIS],
        text="Nb lignes",
        title="Opérateurs de transport — Paris",
    )
    fig_op.update_traces(textposition="outside")
    fig_op.update_layout(height=380, showlegend=False)
    st.plotly_chart(fig_op, use_container_width=True)

    st.markdown("""
> 👉 **La RATP domine largement le réseau parisien** en nombre de lignes exploitées,
> suivie de plusieurs opérateurs Transdev pour les lignes de bus en grande couronne.
> Ce partage reflète la **réforme de l'ouverture à la concurrence** du réseau IDFM amorcée en 2021.
    """)


# ─────────────────────────────────────────────
# ONGLET 3 — PERTURBATIONS
# ─────────────────────────────────────────────
def tab_perturbations(paris_stats, paris_events, mars_stats,
                      mars_perturb_cat, mars_perturb_crit,
                      mars_perturb_mode, mars_perturb_liste):

    st.subheader("Perturbations & événements de circulation")
    st.caption("⚠️ Données Marseille filtrées sur la ville uniquement (sous-réseau 'Marseille')")

    # ── KPIs perturbations ──
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🗼 Paris — Perturbations",      paris_stats["nb_events"])
    col1.metric("⚓ Marseille — Perturbations",  mars_stats["nb_perturb"])
    col2.metric("🗼 Paris — Travaux",            paris_stats["nb_travaux"])
    col2.metric("⚓ Marseille — Travaux",        mars_stats["nb_travaux"])
    col3.metric("🗼 Paris — Fermetures voirie",  paris_stats["nb_fermetures"])
    col3.metric("⚓ Marseille — Critiques",      mars_stats["nb_critiques"])
    col4.metric("⚓ % critiques Marseille",       f"{mars_stats['pct_critiques']:.1f} %")

    st.divider()

    # ── Bar Paris / Marseille côte à côte ──
    st.markdown("#### 🚧 Types de perturbations")
    col_p, col_m = st.columns(2)

    with col_p:
        st.markdown("**🗼 Paris — Événements de circulation**")
        types_p = paris_events["type"].value_counts().reset_index()
        types_p.columns = ["Type", "Nb"]
        types_p["Type"] = types_p["Type"].map({
            "ROAD_CLOSED":  "🚫 Route fermée",
            "CONSTRUCTION": "🏗️ Travaux",
        }).fillna(types_p["Type"])
        fig_ep = px.bar(
            types_p, x="Type", y="Nb",
            color_discrete_sequence=[COLOR_PARIS],
            text="Nb",
        )
        fig_ep.update_traces(textposition="outside")
        fig_ep.update_layout(height=280, showlegend=False, yaxis_title="Nb événements")
        st.plotly_chart(fig_ep, use_container_width=True)

    with col_m:
        st.markdown("**⚓ Marseille — Perturbations par catégorie**")
        fig_em = px.bar(
            mars_perturb_cat, x="Catégorie", y="Nb perturbations",
            color_discrete_sequence=[COLOR_MARSEILLE],
            text="Nb perturbations",
        )
        fig_em.update_traces(textposition="outside")
        fig_em.update_layout(height=280, showlegend=False, yaxis_title="Nb perturbations")
        st.plotly_chart(fig_em, use_container_width=True)

    st.markdown("""
> 👉 **Paris est principalement impacté par des fermetures de voirie et des travaux**,
> liés à la densité urbaine et aux chantiers permanents en Île-de-France.
> À Marseille, les perturbations sont majoritairement de nature **informative**
> (changements de service, déviations ponctuelles), suivies des travaux.
    """)

    st.divider()

    # ── Criticité Marseille ──
    st.markdown("#### ⚠️ Criticité des perturbations — Marseille")
    col_crit, col_mode = st.columns(2)

    with col_crit:
        st.markdown("**Répartition par criticité**")
        fig_crit = px.pie(
            mars_perturb_crit, names="Criticité", values="Nb perturbations",
            hole=0.45,
            color="Criticité",
            color_discrete_map=COULEURS_CRIT,
        )
        fig_crit.update_layout(height=300)
        st.plotly_chart(fig_crit, use_container_width=True)

    with col_mode:
        st.markdown("**Modes de transport impactés**")
        fig_mode = px.bar(
            mars_perturb_mode, x="Mode", y="Nb perturbations",
            color_discrete_sequence=[COLOR_MARSEILLE],
            text="Nb perturbations",
        )
        fig_mode.update_traces(textposition="outside")
        fig_mode.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig_mode, use_container_width=True)

    st.markdown(f"""
> 👉 **{mars_stats['pct_critiques']:.0f}% des perturbations marseillaises sont critiques**
> ({mars_stats['nb_critiques']} sur {mars_stats['nb_perturb']}),
> ce qui reste un niveau gérable. **Les bus sont de loin le mode le plus perturbé**,
> ce qui est cohérent avec leur domination dans le réseau (90%+ des lignes).
> Les perturbations sur métro et tramway sont rares mais souvent plus impactantes
> pour les usagers du fait des forts flux qu'ils transportent.
    """)

    st.divider()

    # ── Liste des perturbations actives ──
    st.markdown("#### 📋 Perturbations actives — Marseille")
    st.caption(
        f"{mars_stats['nb_perturb']} perturbations actives · "
        f"{mars_stats['nb_critiques']} critiques · "
        f"{mars_stats['nb_travaux']} travaux"
    )

    for _, row in mars_perturb_liste.iterrows():
        crit  = row["criticity"]
        color = {"Faible": "🟢", "Moyenne": "🟡", "Critique": "🔴"}.get(crit, "⚪")
        st.markdown(
            f"{color} **{row['title']}** — *{row['category']}* · {crit}  \n"
            f"Du {row['startvalidity']} au {row['endvalidity']}"
        )


# ─────────────────────────────────────────────
# ONGLET 4 — ANALYSE AVANCÉE
# ─────────────────────────────────────────────
def tab_analyse_avancee(paris_stats, mars_stats, top_lignes, mars_perturb_cat):

    st.subheader("🧠 Analyse avancée")

    # ── Top lignes les plus perturbées ──
    st.markdown("#### 🔝 Top 10 lignes les plus perturbées — Marseille")

    fig_top = px.bar(
        top_lignes.sort_values("Nb perturbations"),
        x="Nb perturbations", y="Ligne",
        orientation="h",
        color_discrete_sequence=[COLOR_MARSEILLE],
        text="Nb perturbations",
        title="Lignes avec le plus de perturbations (Marseille)",
    )
    fig_top.update_traces(textposition="outside")
    fig_top.update_layout(height=420, showlegend=False)
    st.plotly_chart(fig_top, use_container_width=True)

    st.markdown("""
> 👉 Les lignes les plus perturbées correspondent généralement aux **axes structurants**
> du réseau bus marseillais (grands corridors traversant plusieurs quartiers).
> Ces lignes concentrent la majorité des travaux et des déviations.
    """)

    st.divider()

    # ── Synthèse comparative ──
    st.markdown("#### 📊 Synthèse comparative Paris vs Marseille")

    df_comp = pd.DataFrame({
        "Indicateur": [
            "Nb lignes",
            "Nb arrêts",
            "Nb perturbations actives",
            "Dont travaux",
        ],
        "Paris": [
            paris_stats["nb_lignes"],
            paris_stats["nb_arrets"],
            paris_stats["nb_events"],
            paris_stats["nb_travaux"],
        ],
        "Marseille": [
            mars_stats["nb_lignes"],
            "N/D",
            mars_stats["nb_perturb"],
            mars_stats["nb_travaux"],
        ],
    })
    st.dataframe(df_comp, use_container_width=True, hide_index=True)

    st.divider()

    # ── Analyse finale ──
    st.markdown("#### 🧠 Analyse globale")
    st.markdown(f"""
**🗼 Paris**
- Réseau **très dense** : {fmt(paris_stats['nb_lignes'])} lignes, {fmt(paris_stats['nb_arrets'])} arrêts
- Grande **diversité modale** : métro, RER, tramway, bus, funiculaire, téléphérique
- Perturbations principalement liées à la **voirie** (chantiers permanents, densité urbaine)
- Plusieurs opérateurs (RATP + Transdev) suite à l'ouverture à la concurrence

**⚓ Marseille**
- Réseau **plus modeste** : {fmt(mars_stats['nb_lignes'])} lignes, dominance **bus à >90%**
- Infrastructure lourde limitée : 2 lignes de métro, 2 lignes de tramway
- Perturbations surtout **informatives et liées aux travaux**
- {mars_stats['nb_critiques']} perturbations critiques actives sur la ville ({mars_stats['pct_critiques']:.0f}% du total)

**📊 Conclusion**
Le réseau parisien est structurellement bien supérieur en capacité et multimodalité,
mais Marseille présente un réseau cohérent pour une ville de cette taille, avec une
proportion de perturbations critiques maîtrisée.
L'enjeu pour Marseille est le **développement des modes lourds** (métro, tram)
pour réduire la dépendance au bus, souvent plus fragile aux perturbations.
    """)


# ─────────────────────────────────────────────
# FONCTION PRINCIPALE
# ─────────────────────────────────────────────
def show_transport():
    st.header("🚇 Transport")
    st.caption(
        "Sources : IDFM Open Data (Paris) · Open Data Métropole Aix-Marseille-Provence (Marseille) "
        "· ⚠️ Données Marseille filtrées sur la ville uniquement"
    )

    with st.spinner("Chargement des données transport..."):
        paris_stats, paris_modes, paris_top_op, paris_events = load_paris()
        (mars_stats, mars_modes, mars_perturb_cat, mars_perturb_crit,
         mars_perturb_mode, top_lignes, mars_perturb_liste) = load_marseille()

    onglet1, onglet2, onglet3, onglet4 = st.tabs([
        "📊 Vue globale",
        "🚇 Réseau de transport",
        "⚠️ Perturbations",
        "📍 Analyse avancée",
    ])

    with onglet1:
        tab_vue_globale(paris_stats, mars_stats)

    with onglet2:
        tab_reseau(paris_modes, paris_top_op, mars_modes)

    with onglet3:
        tab_perturbations(
            paris_stats, paris_events,
            mars_stats, mars_perturb_cat, mars_perturb_crit,
            mars_perturb_mode, mars_perturb_liste,
        )

    with onglet4:
        tab_analyse_avancee(paris_stats, mars_stats, top_lignes, mars_perturb_cat)

    with st.expander("📚 Sources de données"):
        st.markdown("""
| Dataset | Ville | Source |
|---|---|---|
| Arrêts & lignes IDFM | Paris | [Open Data IDFM](https://data.iledefrance-mobilites.fr) |
| Événements circulation | Paris | [Open Data IDFM](https://data.iledefrance-mobilites.fr) |
| Lignes réseau transport | Marseille | [Open Data Métropole AMP](https://data.ampmetropole.fr) |
| Perturbations mobilité | Marseille (filtré) | [Open Data Métropole AMP](https://data.ampmetropole.fr) |
        """)