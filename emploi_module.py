"""
Module Emploi — Comparateur de villes françaises
SAE Outils Décisionnels

Source : DS_RP_EMPLOI_LR_COMP_2022_data.csv (INSEE Recensement de la Population)

Usage : from modules.emploi_module import show_emploi
        show_emploi(ville1, ville2, v1_info, v2_info)
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
        return f"{int(float(n)):,}".replace(",", "\u202f")
    except Exception:
        return str(n)


# ─────────────────────────────────────────────
# CHARGEMENT
# ─────────────────────────────────────────────
@st.cache_data
def load_emploi():
    path = os.path.join(CLEAN_DIR, "emploi.csv")
    if not os.path.exists(path):
        return None
    return pd.read_csv(path, encoding="utf-8-sig")


def get_ville_emploi(df, nom_ville):
    """Retourne le sous-dataframe pour une ville donnée."""
    return df[df["nom_commune"].str.lower() == nom_ville.lower()].copy()


# ─────────────────────────────────────────────
# CALCULS
# ─────────────────────────────────────────────
def calc_stats(df_ville, annee=None):
    """Calcule les stats emploi clés pour une ville."""
    if df_ville.empty:
        return {}

    # Prendre l'année la plus récente si non spécifiée
    if annee is None:
        annee = int(df_ville["TIME_PERIOD"].max())

    df_y = df_ville[df_ville["TIME_PERIOD"] == annee].copy()

    stats = {"annee": annee}

    # Actifs (EMPSTA_ENQ = "1T2") toutes PCS (_T)
    actifs = df_y[
        (df_y["EMPSTA_ENQ"] == "1T2") &
        (df_y["PCS"] == "_T")
    ]["OBS_VALUE"].sum()

    # Actifs occupés (EMPSTA_ENQ = "1") toutes PCS
    occ = df_y[
        (df_y["EMPSTA_ENQ"] == "1") &
        (df_y["PCS"] == "_T")
    ]["OBS_VALUE"].sum()

    # Chômeurs (EMPSTA_ENQ = "2") toutes PCS
    chom = df_y[
        (df_y["EMPSTA_ENQ"] == "2") &
        (df_y["PCS"] == "_T")
    ]["OBS_VALUE"].sum()

    stats["actifs"]       = actifs if actifs > 0 else None
    stats["occ"]          = occ    if occ > 0 else None
    stats["chom"]         = chom   if chom > 0 else None
    stats["taux_chom"]    = (chom / actifs * 100) if actifs > 0 and chom > 0 else None
    stats["taux_emploi"]  = (occ  / actifs * 100) if actifs > 0 and occ  > 0 else None

    # Répartition par PCS (actifs occupés)
    pcs_df = df_y[
        (df_y["EMPSTA_ENQ"] == "1") &
        (df_y["PCS"] != "_T")
    ][["PCS", "LIB_PCS", "OBS_VALUE"]].copy()

    pcs_df = (
        pcs_df.groupby(["PCS", "LIB_PCS"])["OBS_VALUE"]
        .sum()
        .reset_index()
        .sort_values("OBS_VALUE", ascending=False)
    )
    stats["pcs_df"] = pcs_df

    return stats


def get_evol(df_ville):
    """Retourne l'évolution des actifs par année."""
    evol = (
        df_ville[
            (df_ville["EMPSTA_ENQ"] == "1T2") &
            (df_ville["PCS"] == "_T")
        ]
        .groupby("TIME_PERIOD")["OBS_VALUE"]
        .sum()
        .reset_index()
        .sort_values("TIME_PERIOD")
    )
    evol.columns = ["Année", "Actifs"]
    return evol


def get_chom_par_annee(df_ville):
    """Retourne l'évolution du taux de chômage par année."""
    rows = []
    for annee in sorted(df_ville["TIME_PERIOD"].dropna().unique()):
        s = calc_stats(df_ville, int(annee))
        if s.get("taux_chom") is not None:
            rows.append({"Année": int(annee), "Taux chômage (%)": round(s["taux_chom"], 2)})
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────
# ONGLET 1 — CHIFFRES CLÉS
# ─────────────────────────────────────────────
def tab_kpis(ville1, ville2, s1, s2):
    annee = s1.get("annee", s2.get("annee", "N/D"))
    st.subheader(f"Indicateurs clés — {annee}")
    st.caption("Source : INSEE Recensement de la Population · Tranche d'âge 15-64 ans")

    # ── KPIs côte à côte ──
    col_lbl, col_v1, col_v2 = st.columns([1.5, 2, 2])
    col_lbl.markdown("**Indicateur**")
    col_v1.markdown(f"**🔵 {ville1}**")
    col_v2.markdown(f"**🔴 {ville2}**")

    kpis = [
        ("💼 Actifs totaux",      "actifs"),
        ("✅ Actifs occupés",     "occ"),
        ("📈 Taux d'emploi",     "taux_emploi"),
    ]

    for label, key in kpis:
        val1 = s1.get(key)
        val2 = s2.get(key)
        c1, c2, c3 = st.columns([1.5, 2, 2])
        c1.markdown(f"**{label}**")

        def render_val(v, key):
            if v is None:
                return "N/D"
            if "taux" in key:
                return f"{v:.1f} %"
            return fmt(v)

        def render_delta(v1, v2, key):
            if v1 is None or v2 is None:
                return None
            try:
                d = v2 - v1
                if "taux" in key:
                    return f"{d:+.1f} pts"
                return f"{d:+,.0f}".replace(",", "\u202f")
            except Exception:
                return None

        c2.metric("", render_val(val1, key))
        c3.metric("", render_val(val2, key), delta=render_delta(val1, val2, key),
                  delta_color="inverse" if "chom" in key else "normal")




# ─────────────────────────────────────────────
# ONGLET 2 — RÉPARTITION PCS
# ─────────────────────────────────────────────
def tab_pcs(ville1, ville2, s1, s2):
    st.subheader("Répartition par catégorie socioprofessionnelle (PCS)")
    st.caption("Actifs occupés de 15-64 ans · Source : INSEE RP")

    st.markdown("""
La **catégorie socioprofessionnelle (PCS)** classe les personnes en emploi selon leur métier et leur statut.
L'INSEE distingue 6 grandes catégories :

| Catégorie | Qui sont-ils ? | Exemple |
|---|---|---|
| **Agriculteurs exploitants** | Personnes qui exploitent une ferme | Agriculteur, éleveur |
| **Artisans, commerçants, chefs d'entreprise** | Indépendants qui dirigent une petite structure | Boulanger, plombier, gérant de PME |
| **Cadres et professions intellectuelles supérieures** | Métiers très qualifiés, souvent bac+5 | Ingénieur, médecin, avocat, chercheur |
| **Professions intermédiaires** | Entre cadres et employés, niveau bac+2/3 | Infirmier, technicien, comptable |
| **Employés** | Postes d'exécution dans les services | Vendeur, secrétaire, agent administratif |
| **Ouvriers** | Travail manuel dans l'industrie ou le bâtiment | Maçon, opérateur en usine, chauffeur |

La répartition des PCS reflète la **structure économique** d'une ville :
une ville avec beaucoup de cadres est souvent une ville tertiaire dynamique (sièges sociaux, universités),
tandis qu'une forte proportion d'ouvriers traduit un tissu industriel marqué.
    """)
    st.divider()

    col_v1, col_v2 = st.columns(2)

    for col, ville, stats, color in [
        (col_v1, ville1, s1, COLOR_V1),
        (col_v2, ville2, s2, COLOR_V2),
    ]:
        with col:
            st.markdown(f"**{'🔵' if color == COLOR_V1 else '🔴'} {ville}**")
            pcs_df = stats.get("pcs_df")
            if pcs_df is None or pcs_df.empty:
                st.info("Données PCS non disponibles.")
                continue

            # Nettoyer les libellés trop longs
            pcs_df = pcs_df.copy()
            pcs_df["LIB_PCS"] = pcs_df["LIB_PCS"].str.slice(0, 45)

            fig = px.bar(
                pcs_df.sort_values("OBS_VALUE"),
                x="OBS_VALUE", y="LIB_PCS",
                orientation="h",
                color_discrete_sequence=[color],
                text="OBS_VALUE",
                title=f"PCS — {ville}",
            )
            fig.update_traces(
                texttemplate="%{text:,.0f}", textposition="outside"
            )
            fig.update_layout(
                height=360, showlegend=False,
                xaxis_title="Nb actifs occupés", yaxis_title="",
                margin=dict(t=30, l=0),
            )
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Comparaison directe PCS
    st.markdown("#### 🔁 Comparaison PCS directe")
    pcs1 = s1.get("pcs_df")
    pcs2 = s2.get("pcs_df")

    if pcs1 is not None and pcs2 is not None and not pcs1.empty and not pcs2.empty:
        pcs_comp = pd.merge(
            pcs1[["LIB_PCS", "OBS_VALUE"]].rename(columns={"OBS_VALUE": ville1}),
            pcs2[["LIB_PCS", "OBS_VALUE"]].rename(columns={"OBS_VALUE": ville2}),
            on="LIB_PCS", how="outer",
        ).fillna(0)

        pcs_melt = pcs_comp.melt(id_vars="LIB_PCS", var_name="Ville", value_name="Nb actifs")
        pcs_melt["LIB_PCS"] = pcs_melt["LIB_PCS"].str.slice(0, 45)

        fig_comp = px.bar(
            pcs_melt, x="LIB_PCS", y="Nb actifs", color="Ville",
            barmode="group",
            color_discrete_map={ville1: COLOR_V1, ville2: COLOR_V2},
            text="Nb actifs",
        )
        fig_comp.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
        fig_comp.update_layout(
            height=400, xaxis_tickangle=-30,
            legend_title="", margin=dict(t=20),
        )
        st.plotly_chart(fig_comp, use_container_width=True)

        st.markdown("""
> 👉 La répartition par PCS reflète la **structure économique** de chaque ville :
> une part élevée de cadres indique une économie tertiaire avancée,
> tandis qu'une forte proportion d'ouvriers traduit un tissu industriel plus marqué.
        """)


# ─────────────────────────────────────────────
# ONGLET 3 — ÉVOLUTION
# ─────────────────────────────────────────────
def tab_evolution(ville1, ville2, df1, df2):
    st.subheader("Évolution de l'emploi dans le temps")
    st.caption("Actifs de 15-64 ans · Source : INSEE RP (toutes les années disponibles)")

    evol1 = get_evol(df1)
    evol2 = get_evol(df2)

    if evol1.empty and evol2.empty:
        st.info("ℹ️ Données d'évolution non disponibles.")
        return

    fig = go.Figure()
    for nom, evol, color in [(ville1, evol1, COLOR_V1), (ville2, evol2, COLOR_V2)]:
        if not evol.empty:
            fig.add_trace(go.Scatter(
                x=evol["Année"], y=evol["Actifs"],
                name=nom, mode="lines+markers",
                line=dict(color=color, width=2.5),
                marker=dict(size=8),
                hovertemplate=f"<b>{nom}</b><br>Année : %{{x}}<br>Actifs : %{{y:,.0f}}<extra></extra>",
            ))
    fig.update_layout(
        yaxis_title="Nombre d'actifs (15-64 ans)",
        height=420, legend_title="",
        hovermode="x unified", margin=dict(t=20),
    )
    st.plotly_chart(fig, use_container_width=True)



    st.markdown("""
> 👉 L'évolution temporelle permet de distinguer les **tendances structurelles** 
> (baisse ou hausse durable) des **variations conjoncturelles** liées à la conjoncture économique nationale.
    """)


# ─────────────────────────────────────────────
# ONGLET 4 — ANALYSE
# ─────────────────────────────────────────────
def tab_analyse(ville1, ville2, s1, s2):
    st.subheader("🧠 Analyse du marché du travail")

    lignes = []

    te1 = s1.get("taux_emploi")
    te2 = s2.get("taux_emploi")
    a1  = s1.get("annee", "N/D")

    if te1 is not None and te2 is not None:
        plus_emp = ville1 if te1 > te2 else ville2
        lignes.append(
            f"**📈 Taux d'emploi** : {plus_emp} présente le taux d'emploi le plus élevé "
            f"({max(te1,te2):.1f}%)."
        )

    pcs1 = s1.get("pcs_df")
    pcs2 = s2.get("pcs_df")
    if pcs1 is not None and not pcs1.empty:
        top1 = pcs1.iloc[0]["LIB_PCS"]
        lignes.append(f"**👔 PCS dominante à {ville1}** : {top1}")
    if pcs2 is not None and not pcs2.empty:
        top2 = pcs2.iloc[0]["LIB_PCS"]
        lignes.append(f"**👔 PCS dominante à {ville2}** : {top2}")

    if lignes:
        for l in lignes:
            st.markdown(f"- {l}")
    else:
        st.info("ℹ️ Données insuffisantes pour l'analyse.")

    st.markdown(f"\n> Données issues du Recensement de la Population INSEE ({a1}), tranche 15-64 ans.")


# ─────────────────────────────────────────────
# FONCTION PRINCIPALE
# ─────────────────────────────────────────────
def show_emploi(ville1, ville2, v1_info, v2_info):
    st.header("💼 Emploi")
    st.caption(
        f"Comparaison : **{ville1}** vs **{ville2}** · "
        "Source : INSEE Recensement de la Population 2022 · 15-64 ans"
    )

    df = load_emploi()
    if df is None:
        st.error(
            "❌ Fichier `data/clean/emploi.csv` introuvable.\n\n"
            "Exécute : `python prepare_data.py`"
        )
        return

    df1 = get_ville_emploi(df, ville1)
    df2 = get_ville_emploi(df, ville2)

    if df1.empty:
        st.warning(f"⚠️ Aucune donnée emploi pour **{ville1}**. Vérifie que son code INSEE est dans le fichier.")
    if df2.empty:
        st.warning(f"⚠️ Aucune donnée emploi pour **{ville2}**. Vérifie que son code INSEE est dans le fichier.")

    if df1.empty and df2.empty:
        return

    # Année commune la plus récente
    annees1 = set(df1["TIME_PERIOD"].dropna().unique()) if not df1.empty else set()
    annees2 = set(df2["TIME_PERIOD"].dropna().unique()) if not df2.empty else set()
    annees_communes = sorted(annees1 & annees2, reverse=True)
    annee_ref = int(annees_communes[0]) if annees_communes else None

    if annee_ref:
        st.info(f"📅 Année de référence : **{annee_ref}** (dernière année commune aux deux villes)")

    s1 = calc_stats(df1, annee_ref) if not df1.empty else {}
    s2 = calc_stats(df2, annee_ref) if not df2.empty else {}

    onglet1, onglet2, onglet3, onglet4 = st.tabs([
        "📊 Chiffres clés",
        "👔 Répartition PCS",
        "📈 Évolution",
        "🧠 Analyse",
    ])

    with onglet1:
        tab_kpis(ville1, ville2, s1, s2)
    with onglet2:
        tab_pcs(ville1, ville2, s1, s2)
    with onglet3:
        tab_evolution(ville1, ville2, df1, df2)
    with onglet4:
        tab_analyse(ville1, ville2, s1, s2)

    with st.expander("📚 Sources de données"):
        st.markdown("""
| Dataset | Description | Source |
|---|---|---|
| DS_RP_EMPLOI_LR_COMP_2022_data.csv | Emploi, chômage, PCS par commune | [INSEE RP 2022](https://www.insee.fr) |
| DS_RP_EMPLOI_LR_COMP_2022_metadata.csv | Dictionnaire des codes | [INSEE](https://www.insee.fr) |
        """)