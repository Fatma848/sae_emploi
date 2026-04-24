"""
Module Emploi — Comparaison Paris vs Marseille
SAE Outils Décisionnels

Sources :
- Paris : emploi-au-quart-de-1968-a-2016-dile-de-france.csv (INSEE / Open Data IDF)
           chomage-structure-par-age-exhaustif-des-communes-dile-de-france-donnee-insee0.csv
- Marseille : ls-caracteristiques-de-l-emploi-en-2018.csv (INSEE)
              emploi-population-active-en-2020.csv (INSEE)

Usage : from emploi_module import show_emploi / show_emploi()
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os

# ─────────────────────────────────────────────
# CHEMINS
# ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(__file__)

PATH_EMP_IDF  = os.path.join(BASE_DIR, "data", "emploi-au-quart-de-1968-a-2016-dile-de-france.csv")
PATH_CHOM_IDF = os.path.join(BASE_DIR, "data", "chomage-structure-par-age-exhaustif-des-communes-dile-de-france-donnee-insee0.csv")
PATH_CAR_2018 = os.path.join(BASE_DIR, "data", "ls-caracteristiques-de-l-emploi-en-2018.csv")
PATH_POP_2020 = os.path.join(BASE_DIR, "data", "emploi-population-active-en-2020.csv")

# ─────────────────────────────────────────────
# COULEURS
# ─────────────────────────────────────────────
COLOR_PARIS     = "#1f77b4"
COLOR_MARSEILLE = "#d62728"

# ─────────────────────────────────────────────
# CHARGEMENT DES DONNÉES
# ─────────────────────────────────────────────
@st.cache_data
def load_paris():
    df_emp  = pd.read_csv(PATH_EMP_IDF,  sep=";", encoding="utf-8-sig")
    df_chom = pd.read_csv(PATH_CHOM_IDF, sep=";", encoding="utf-8-sig")

    paris_emp  = df_emp[df_emp["insee"].astype(str).str.startswith("75")]
    paris_chom = df_chom[df_chom["insee"].astype(str).str.startswith("75")]

    emp_total = paris_emp["emp2020"].sum()
    emp_h     = paris_emp["emp_h2020"].sum()
    emp_f     = paris_emp["emp_f2020"].sum()
    chom      = paris_chom["chom2020"].sum()
    popact    = paris_chom["popact"].sum()

    taux_chom   = chom / popact * 100
    taux_emploi = emp_total / popact * 100

    # Regroupement tranches d'âge → 3 classes comparables à Marseille
    c1519 = paris_chom["chom15_19"].sum()
    c2024 = paris_chom["chom20_24"].sum()
    c2529 = paris_chom["chom25_29"].sum()
    c3049 = paris_chom["chom30_49"].sum()
    c5054 = paris_chom["chom50_54"].sum()
    c5559 = paris_chom["chom55_59"].sum()
    c6064 = paris_chom["chom60_64"].sum()

    p1519 = paris_chom["popact1519"].sum()
    p2024 = paris_chom["popact2024"].sum()
    p2529 = paris_chom["popact2529"].sum()
    p3049 = paris_chom["popact3049"].sum()
    p5054 = paris_chom["popact5054"].sum()
    p5559 = paris_chom["popact5559"].sum()
    p6064 = paris_chom["popact6064"].sum()

    chom_age_comp = {
        "15-24": c1519 + c2024,
        "25-54": c2529 + c3049 + c5054,
        "55-64": c5559 + c6064,
    }
    pop_age_comp = {
        "15-24": p1519 + p2024,
        "25-54": p2529 + p3049 + p5054,
        "55-64": p5559 + p6064,
    }
    taux_chom_age = {k: chom_age_comp[k] / pop_age_comp[k] * 100 for k in chom_age_comp}

    annees = [1968, 1975, 1982, 1990, 1999, 2006, 2007, 2008, 2009,
              2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020]
    cols   = ["emp1968","emp1975","emp1982","emp1990","emp1999",
              "emp2006","emp2007","emp2008","emp2009","emp2010",
              "emp2011","emp2012","emp2013","emp2014","emp2015",
              "emp2016","emp2017","emp2018","emp2019","emp2020"]
    evol = {a: paris_emp[c].sum() for a, c in zip(annees, cols) if c in paris_emp.columns}

    return {
        "emp_total": emp_total, "emp_h": emp_h, "emp_f": emp_f,
        "chom": chom, "popact": popact,
        "taux_chom": taux_chom, "taux_emploi": taux_emploi,
        "chom_age_comp": chom_age_comp, "taux_chom_age": taux_chom_age,
        "evol": evol, "salaries": None, "non_salaries": None,
    }


@st.cache_data
def load_marseille():
    df_car = pd.read_csv(PATH_CAR_2018, sep=";", encoding="utf-8-sig")
    df_pop = pd.read_csv(PATH_POP_2020, sep=";", encoding="utf-8-sig")

    mars_car = df_car[df_car["libelle_geographique"].str.lower().str.contains("marseille")].iloc[0]
    mars_pop = df_pop[df_pop["libelle_geographique"].str.lower().str.contains("marseille")].iloc[0]

    emp_total = mars_pop["actifs_occupes_en_2020_princ"]
    emp_h     = mars_pop["actifs_occupes_15_64_ans_hommes_en_2020_princ"]
    emp_f     = mars_pop["actifs_occupes_15_64_ans_femmes_en_2020_princ"]
    chom      = mars_pop["chomeurs_15_64_ans_en_2020_princ"]
    popact    = mars_pop["actifs_15_64_ans_en_2020_princ"]

    taux_chom   = chom / popact * 100
    taux_emploi = emp_total / popact * 100

    c1524 = mars_pop["chomeurs_de_15_24_ans_en_2020_princ"]
    c2554 = mars_pop["chomeurs_de_25_54_ans_en_2020_princ"]
    c5564 = mars_pop["chomeurs_de_55_64_ans_en_2020_princ"]
    p1524 = mars_pop["actifs_15_24_ans_en_2020_princ"]
    p2554 = mars_pop["actifs_25_54_ans_en_2020_princ"]
    p5564 = mars_pop["actifs_55_64_ans_en_2020_princ"]

    chom_age_comp = {"15-24": c1524, "25-54": c2554, "55-64": c5564}
    taux_chom_age = {
        "15-24": c1524 / p1524 * 100,
        "25-54": c2554 / p2554 * 100,
        "55-64": c5564 / p5564 * 100,
    }

    salaries     = mars_car["salaries_15_ans_ou_plus_en_2018_princ"]
    non_salaries = mars_car["non_salaries_15_ans_ou_plus_en_2018_princ"]

    return {
        "emp_total": emp_total, "emp_h": emp_h, "emp_f": emp_f,
        "chom": chom, "popact": popact,
        "taux_chom": taux_chom, "taux_emploi": taux_emploi,
        "chom_age_comp": chom_age_comp, "taux_chom_age": taux_chom_age,
        "evol": None, "salaries": salaries, "non_salaries": non_salaries,
    }


def fmt(n):
    return f"{int(n):,}".replace(",", "\u202f")


# ─────────────────────────────────────────────
# ONGLET 1 — CHIFFRES CLÉS
# ─────────────────────────────────────────────
def tab_chiffres_cles(paris, mars):
    st.subheader("Indicateurs clés du marché du travail — 2020")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🗼 Taux de chômage Paris",    f"{paris['taux_chom']:.1f} %")
        st.metric("⚓ Taux de chômage Marseille", f"{mars['taux_chom']:.1f} %",
                  delta=f"{mars['taux_chom'] - paris['taux_chom']:+.1f} pts",
                  delta_color="inverse")
    with col2:
        st.metric("🗼 Taux d'emploi Paris",    f"{paris['taux_emploi']:.1f} %")
        st.metric("⚓ Taux d'emploi Marseille", f"{mars['taux_emploi']:.1f} %",
                  delta=f"{mars['taux_emploi'] - paris['taux_emploi']:+.1f} pts",
                  delta_color="normal")
    with col3:
        st.metric("🗼 Actifs occupés Paris",     fmt(paris["emp_total"]))
        st.metric("⚓ Actifs occupés Marseille", fmt(mars["emp_total"]))

    st.divider()

    # Jauges taux de chômage
    fig_gauge = go.Figure()
    for i, (nom, data, color) in enumerate([("Paris", paris, COLOR_PARIS), ("Marseille", mars, COLOR_MARSEILLE)]):
        fig_gauge.add_trace(go.Indicator(
            mode="gauge+number",
            value=round(data["taux_chom"], 1),
            title={"text": nom, "font": {"size": 16}},
            number={"suffix": " %"},
            gauge={
                "axis": {"range": [0, 25]},
                "bar": {"color": color},
                "steps": [
                    {"range": [0, 8],   "color": "#d4edda"},
                    {"range": [8, 15],  "color": "#fff3cd"},
                    {"range": [15, 25], "color": "#f8d7da"},
                ],
            },
            domain={"column": i, "row": 0},
        ))
    fig_gauge.update_layout(grid={"rows": 1, "columns": 2}, height=240, margin=dict(t=30, b=0))
    st.plotly_chart(fig_gauge, use_container_width=True)

    st.markdown(
        f"👉 **Marseille présente un taux de chômage nettement plus élevé que Paris** "
        f"({mars['taux_chom']:.1f}% contre {paris['taux_chom']:.1f}%), soit un écart de "
        f"**+{mars['taux_chom'] - paris['taux_chom']:.1f} points**. "
        "Cela reflète des dynamiques économiques très différentes : Paris concentre l'essentiel "
        "des emplois qualifiés et des sièges sociaux, tandis que Marseille fait face à "
        "des difficultés structurelles d'insertion professionnelle."
    )


# ─────────────────────────────────────────────
# ONGLET 2 — COMPARAISON GLOBALE
# ─────────────────────────────────────────────
def tab_comparaison_globale(paris, mars):
    st.subheader("Vue d'ensemble — Volumes et taux comparés")

    # Bar chart volumes
    st.markdown("#### Actifs, actifs occupés et chômeurs")
    indicateurs = ["Population active", "Actifs occupés", "Chômeurs"]
    vals_paris  = [paris["popact"], paris["emp_total"], paris["chom"]]
    vals_mars   = [mars["popact"],  mars["emp_total"],  mars["chom"]]

    fig_vol = go.Figure()
    fig_vol.add_trace(go.Bar(
        name="🗼 Paris", x=indicateurs, y=vals_paris,
        marker_color=COLOR_PARIS,
        text=[fmt(v) for v in vals_paris], textposition="outside",
    ))
    fig_vol.add_trace(go.Bar(
        name="⚓ Marseille", x=indicateurs, y=vals_mars,
        marker_color=COLOR_MARSEILLE,
        text=[fmt(v) for v in vals_mars], textposition="outside",
    ))
    fig_vol.update_layout(barmode="group", yaxis_title="Nombre de personnes",
                          height=400, legend_title="", margin=dict(t=20))
    st.plotly_chart(fig_vol, use_container_width=True)

    st.markdown(
        f"👉 **Les volumes sont très différents** : Paris compte "
        f"**{fmt(paris['emp_total'])} actifs occupés** contre "
        f"**{fmt(mars['emp_total'])} pour Marseille** (~6 fois plus). "
        "La comparaison en taux reste donc plus pertinente."
    )

    st.divider()

    # Bar chart taux
    st.markdown("#### Comparaison des taux (%)")
    taux_labels = ["Taux de chômage", "Taux d'emploi"]
    taux_paris  = [paris["taux_chom"], paris["taux_emploi"]]
    taux_mars   = [mars["taux_chom"],  mars["taux_emploi"]]

    fig_taux = go.Figure()
    fig_taux.add_trace(go.Bar(
        name="🗼 Paris", x=taux_labels, y=taux_paris,
        marker_color=COLOR_PARIS,
        text=[f"{v:.1f}%" for v in taux_paris], textposition="outside",
    ))
    fig_taux.add_trace(go.Bar(
        name="⚓ Marseille", x=taux_labels, y=taux_mars,
        marker_color=COLOR_MARSEILLE,
        text=[f"{v:.1f}%" for v in taux_mars], textposition="outside",
    ))
    fig_taux.update_layout(barmode="group", yaxis_title="(%)",
                           height=350, legend_title="", margin=dict(t=20))
    st.plotly_chart(fig_taux, use_container_width=True)

    st.markdown(
        f"👉 Paris affiche un **taux d'emploi de {paris['taux_emploi']:.1f}%** "
        f"contre **{mars['taux_emploi']:.1f}% pour Marseille**, confirmant "
        "une meilleure intégration des actifs dans le marché du travail parisien."
    )


# ─────────────────────────────────────────────
# ONGLET 3 — STRUCTURE EMPLOI
# ─────────────────────────────────────────────
def tab_structure_emploi(paris, mars):
    st.subheader("Structure de l'emploi")

    # H/F
    st.markdown("#### Répartition Hommes / Femmes parmi les actifs occupés")
    fig_hf = go.Figure()
    for ville, data, color in [("Paris", paris, COLOR_PARIS), ("Marseille", mars, COLOR_MARSEILLE)]:
        total = data["emp_h"] + data["emp_f"]
        pct_h = data["emp_h"] / total * 100
        pct_f = data["emp_f"] / total * 100
        fig_hf.add_trace(go.Bar(
            name=f"{ville} — Hommes", x=[ville], y=[pct_h],
            marker_color=color, opacity=0.9,
            text=f"{pct_h:.1f}%", textposition="inside",
        ))
        fig_hf.add_trace(go.Bar(
            name=f"{ville} — Femmes", x=[ville], y=[pct_f],
            marker_color=color, opacity=0.45,
            text=f"{pct_f:.1f}%", textposition="inside",
        ))
    fig_hf.update_layout(barmode="stack", yaxis_title="% des actifs occupés",
                         height=320, legend_title="", margin=dict(t=10))
    st.plotly_chart(fig_hf, use_container_width=True)

    tot_p = paris["emp_h"] + paris["emp_f"]
    tot_m = mars["emp_h"] + mars["emp_f"]
    st.markdown(
        f"👉 La répartition H/F est quasi similaire dans les deux villes : "
        f"Paris ({paris['emp_h']/tot_p*100:.0f}% H / {paris['emp_f']/tot_p*100:.0f}% F) "
        f"et Marseille ({mars['emp_h']/tot_m*100:.0f}% H / {mars['emp_f']/tot_m*100:.0f}% F)."
    )

    st.divider()

    # Salariés / Non-salariés
    st.markdown("#### Statut des actifs — Marseille 2018")
    st.caption("⚠️ Donnée disponible uniquement pour Marseille (INSEE 2018).")

    total_s = mars["salaries"] + mars["non_salaries"]
    pct_ns  = mars["non_salaries"] / total_s * 100
    col_d, col_txt = st.columns([1, 1])

    with col_d:
        fig_donut = go.Figure(go.Pie(
            labels=["Salariés", "Non-salariés"],
            values=[mars["salaries"], mars["non_salaries"]],
            hole=0.5,
            marker_colors=[COLOR_MARSEILLE, "#ff7f0e"],
            textinfo="label+percent",
        ))
        fig_donut.update_layout(height=280, margin=dict(t=10))
        st.plotly_chart(fig_donut, use_container_width=True)

    with col_txt:
        st.markdown(f"""
**Marseille — Répartition du statut :**
- 👔 Salariés : **{fmt(mars['salaries'])}** ({100-pct_ns:.1f}%)
- 🏪 Non-salariés : **{fmt(mars['non_salaries'])}** ({pct_ns:.1f}%)

👉 Avec **{pct_ns:.1f}% de non-salariés**, Marseille présente
une part significative d'indépendants et d'auto-entrepreneurs,
témoignant d'un tissu économique local dynamique
mais parfois plus précaire que le salariat classique.
        """)


# ─────────────────────────────────────────────
# ONGLET 4 — ANALYSE PAR ÂGE
# ─────────────────────────────────────────────
def tab_analyse_age(paris, mars):
    st.subheader("Chômage par tranche d'âge")
    st.caption(
        "Tranches harmonisées (15-24 / 25-54 / 55-64) pour une comparaison directe."
    )

    tranches = list(paris["taux_chom_age"].keys())

    # Taux comparés
    st.markdown("#### Taux de chômage par tranche d'âge (%)")
    fig_age = go.Figure()
    fig_age.add_trace(go.Bar(
        name="🗼 Paris", x=tranches,
        y=[round(v, 1) for v in paris["taux_chom_age"].values()],
        marker_color=COLOR_PARIS,
        text=[f"{v:.1f}%" for v in paris["taux_chom_age"].values()],
        textposition="outside",
    ))
    fig_age.add_trace(go.Bar(
        name="⚓ Marseille", x=tranches,
        y=[round(v, 1) for v in mars["taux_chom_age"].values()],
        marker_color=COLOR_MARSEILLE,
        text=[f"{v:.1f}%" for v in mars["taux_chom_age"].values()],
        textposition="outside",
    ))
    fig_age.update_layout(barmode="group", yaxis_title="Taux de chômage (%)",
                          height=380, legend_title="", margin=dict(t=20))
    st.plotly_chart(fig_age, use_container_width=True)

    t_j_p = paris["taux_chom_age"]["15-24"]
    t_j_m = mars["taux_chom_age"]["15-24"]
    st.markdown(
        f"👉 **Le chômage des jeunes (15-24 ans) est particulièrement marqué à Marseille** "
        f"({t_j_m:.1f}% vs {t_j_p:.1f}% à Paris), soit un écart de "
        f"**+{t_j_m - t_j_p:.1f} points**. Cet écart révèle des difficultés d'insertion "
        "professionnelle plus importantes chez les jeunes marseillais."
    )

    st.divider()

    # Volumes
    st.markdown("#### Nombre de chômeurs par tranche d'âge")
    col_p, col_m = st.columns(2)

    with col_p:
        st.markdown("**🗼 Paris**")
        df_p = pd.DataFrame({
            "Tranche": tranches,
            "Chômeurs": [round(v) for v in paris["chom_age_comp"].values()],
        })
        fig_p = px.bar(df_p, x="Tranche", y="Chômeurs",
                       color_discrete_sequence=[COLOR_PARIS], text="Chômeurs")
        fig_p.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
        fig_p.update_layout(height=280, showlegend=False)
        st.plotly_chart(fig_p, use_container_width=True)

    with col_m:
        st.markdown("**⚓ Marseille**")
        df_m = pd.DataFrame({
            "Tranche": tranches,
            "Chômeurs": [round(v) for v in mars["chom_age_comp"].values()],
        })
        fig_m = px.bar(df_m, x="Tranche", y="Chômeurs",
                       color_discrete_sequence=[COLOR_MARSEILLE], text="Chômeurs")
        fig_m.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
        fig_m.update_layout(height=280, showlegend=False)
        st.plotly_chart(fig_m, use_container_width=True)


# ─────────────────────────────────────────────
# ONGLET 5 — ÉVOLUTION
# ─────────────────────────────────────────────
def tab_evolution(paris):
    st.subheader("Évolution de l'emploi à Paris (1968–2020)")
    st.caption("Données uniquement disponibles pour Paris (source Open Data IDF).")

    df_evol = pd.DataFrame(
        [(a, v) for a, v in paris["evol"].items()],
        columns=["Année", "Emplois"]
    )

    fig_evol = px.line(
        df_evol, x="Année", y="Emplois",
        markers=True,
        color_discrete_sequence=[COLOR_PARIS],
        labels={"Emplois": "Nombre d'emplois"},
    )
    fig_evol.update_traces(line_width=2.5, marker_size=7)
    fig_evol.update_layout(height=420, margin=dict(t=20))
    st.plotly_chart(fig_evol, use_container_width=True)

    max_ann = max(paris["evol"], key=paris["evol"].get)
    min_ann = min(paris["evol"], key=paris["evol"].get)
    st.markdown(
        f"👉 **L'emploi à Paris a connu une longue période de déclin** entre 1968 et 1999 "
        f"(de {fmt(paris['evol'][1968])} à {fmt(paris['evol'][1999])} emplois), "
        f"avant de **se redresser progressivement** jusqu'en 2020 "
        f"({fmt(paris['evol'][2020])} emplois). "
        f"Le pic historique est en **{max_ann}** avec {fmt(paris['evol'][max_ann])} emplois, "
        f"et le creux en **{min_ann}** avec {fmt(paris['evol'][min_ann])} emplois."
    )


# ─────────────────────────────────────────────
# FONCTION PRINCIPALE
# ─────────────────────────────────────────────
def show_emploi():
    st.header("💼 Emploi")
    st.caption(
        "Sources : INSEE / Open Data Île-de-France (Paris) · INSEE fichiers détail (Marseille) · Données 2020"
    )

    paris = load_paris()
    mars  = load_marseille()

    # Navigation par onglets — "Chiffres clés" affiché par défaut
    onglet1, onglet2, onglet3, onglet4, onglet5 = st.tabs([
        "📊 Chiffres clés",
        "🔍 Comparaison globale",
        "🏗️ Structure emploi",
        "📉 Analyse par âge",
        "📈 Évolution",
    ])

    with onglet1:
        tab_chiffres_cles(paris, mars)

    with onglet2:
        tab_comparaison_globale(paris, mars)

    with onglet3:
        tab_structure_emploi(paris, mars)

    with onglet4:
        tab_analyse_age(paris, mars)

    with onglet5:
        tab_evolution(paris)

    with st.expander("📚 Sources de données"):
        st.markdown("""
| Dataset | Ville | Année | Source |
|---|---|---|---|
| Emploi au quart IDF | Paris | 1968–2020 | [Open Data IDF](https://data.iledefrance.fr) |
| Chômage par âge IDF | Paris | 2020 | [Open Data IDF](https://data.iledefrance.fr) |
| Caractéristiques emploi | Marseille | 2018 | [INSEE](https://www.insee.fr) |
| Emploi & population active | Marseille | 2020 | [INSEE](https://www.insee.fr) |
        """)