"""
Module ACP — Analyse en Composantes Principales sur les villes françaises
SAE Outils Décisionnels

Variables utilisées (toutes numériques, issues des fichiers nettoyés) :
  - population, densité, superficie        (communes.csv)
  - taux_chomage, taux_emploi              (emploi.csv)
  - % cadres, % ouvriers, % employes       (emploi.csv)
  - loyer_app_m2, loyer_mai_m2             (logement.csv)

Les deux villes sélectionnées sont surlignées sur tous les graphiques.

Usage : from acp_module import show_acp
        show_acp(ville1, ville2, v1_info, v2_info)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import os

from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

COLOR_V1   = "#1f77b4"
COLOR_V2   = "#d62728"
COLOR_BASE = "rgba(150,150,150,0.4)"

CLEAN_DIR = os.path.join(os.path.dirname(__file__), "data", "clean")


# ─────────────────────────────────────────────
# CONSTRUCTION DU TABLEAU INDIVIDUS × VARIABLES
# ─────────────────────────────────────────────
@st.cache_data
def build_acp_data():
    """
    Construit un DataFrame ville × variables numériques
    en fusionnant communes, emploi et logement.
    Retourne (df_acp, df_scaled, variables, scaler, pca_model)
    """

    # ── 1. Communes ──────────────────────────
    path_com = os.path.join(CLEAN_DIR, "communes.csv")
    if not os.path.exists(path_com):
        return None, None, None, None, None

    df_com = pd.read_csv(path_com, encoding="utf-8-sig")
    df_base = df_com[["nom_commune", "code_insee",
                       "population", "superficie_km2", "densite"]].copy()

    # ── 2. Emploi ────────────────────────────
    path_emp = os.path.join(CLEAN_DIR, "emploi.csv")
    if os.path.exists(path_emp):
        df_emp = pd.read_csv(path_emp, encoding="utf-8-sig")

        # Année la plus récente disponible
        annee_max = int(df_emp["TIME_PERIOD"].max())
        df_emp_y = df_emp[df_emp["TIME_PERIOD"] == annee_max].copy()

        # Taux de chômage par ville
        rows_chom = []
        for insee, grp in df_emp_y.groupby("GEO"):
            actifs = grp[(grp["EMPSTA_ENQ"] == "1T2") & (grp["PCS"] == "_T")]["OBS_VALUE"].sum()
            chomeurs = grp[(grp["EMPSTA_ENQ"] == "2") & (grp["PCS"] == "_T")]["OBS_VALUE"].sum()
            occ = grp[(grp["EMPSTA_ENQ"] == "1") & (grp["PCS"] == "_T")]["OBS_VALUE"].sum()

            # PCS en % des actifs occupés
            pcs_tot = grp[(grp["EMPSTA_ENQ"] == "1") & (grp["PCS"] != "_T")]["OBS_VALUE"].sum()
            def pct_pcs(code):
                v = grp[(grp["EMPSTA_ENQ"] == "1") & (grp["PCS"] == code)]["OBS_VALUE"].sum()
                return (v / pcs_tot * 100) if pcs_tot > 0 else np.nan

            rows_chom.append({
                "code_insee":    str(insee).zfill(5),
                "taux_chomage":  (chomeurs / actifs * 100) if actifs > 0 else np.nan,
                "taux_emploi":   (occ / actifs * 100)     if actifs > 0 else np.nan,
                "pct_cadres":    pct_pcs("3"),
                "pct_ouvriers":  pct_pcs("6"),
                "pct_employes":  pct_pcs("5"),
            })

        df_emp_stats = pd.DataFrame(rows_chom)
        df_base = df_base.merge(df_emp_stats, on="code_insee", how="left")

    # ── 3. Logement ──────────────────────────
    path_log = os.path.join(CLEAN_DIR, "logement.csv")
    if os.path.exists(path_log):
        df_log = pd.read_csv(path_log, encoding="utf-8-sig")

        # Loyer appartement
        df_app = (
            df_log[df_log["type_bien"] == "Appartement"]
            .groupby("code_insee")["loyer_m2"]
            .mean()
            .reset_index()
            .rename(columns={"loyer_m2": "loyer_app_m2"})
        )
        # Loyer maison
        df_mai = (
            df_log[df_log["type_bien"] == "Maison"]
            .groupby("code_insee")["loyer_m2"]
            .mean()
            .reset_index()
            .rename(columns={"loyer_m2": "loyer_mai_m2"})
        )
        df_base = df_base.merge(df_app, on="code_insee", how="left")
        df_base = df_base.merge(df_mai, on="code_insee", how="left")

    # ── 4. Nettoyage ─────────────────────────
    VARIABLES = [
        "population", "densite", "superficie_km2",
        "taux_emploi",
        "pct_cadres", "pct_ouvriers", "pct_employes",
        "loyer_app_m2", "loyer_mai_m2",
    ]
    VARIABLES = [v for v in VARIABLES if v in df_base.columns]

    LABELS = {
        "population":    "Population",
        "densite":       "Densité",
        "superficie_km2":"Superficie",
        "taux_emploi":   "Taux emploi",
        "pct_cadres":    "% Cadres",
        "pct_ouvriers":  "% Ouvriers",
        "pct_employes":  "% Employés",
        "loyer_app_m2":  "Loyer appt/m²",
        "loyer_mai_m2":  "Loyer maison/m²",
    }

    # Garder seulement les villes avec assez de données
    df_acp = df_base[["nom_commune", "code_insee"] + VARIABLES].copy()
    df_acp = df_acp.dropna(thresh=len(VARIABLES) - 2)  # tolérance 2 NA max

    # Imputation par médiane pour les rares NA restants
    for v in VARIABLES:
        if v in df_acp.columns:
            df_acp[v] = df_acp[v].fillna(df_acp[v].median())

    df_acp = df_acp.reset_index(drop=True)

    # ── 5. Standardisation + ACP ─────────────
    X = df_acp[VARIABLES].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    pca = PCA(n_components=min(len(VARIABLES), 5))
    coords = pca.fit_transform(X_scaled)

    df_acp["PC1"] = coords[:, 0]
    df_acp["PC2"] = coords[:, 1]
    if coords.shape[1] > 2:
        df_acp["PC3"] = coords[:, 2]

    labels_list = [LABELS.get(v, v) for v in VARIABLES]

    return df_acp, X_scaled, VARIABLES, labels_list, pca, scaler


# ─────────────────────────────────────────────
# ONGLET 1 — VARIANCE EXPLIQUÉE
# ─────────────────────────────────────────────
def tab_variance(pca, variables):
    st.subheader("Variance expliquée par composante")

    st.markdown("""
**Qu'est-ce que l'ACP ?**

L'Analyse en Composantes Principales (ACP) est une méthode statistique qui permet de simplifier un grand nombre de variables tout en conservant l'essentiel de l'information.

Dans cette application, plusieurs indicateurs décrivent les villes : population, densité, loyers, taux d'emploi, part de cadres, d'ouvriers et d'employés.
L'ACP résume toutes ces informations en quelques axes principaux appelés composantes (PC1, PC2…).

**A quoi servent les composantes ?**

Chaque composante représente une combinaison des variables initiales :
- **PC1** : c'est l'axe qui explique le plus de différences entre les villes. C'est le plus important.
- **PC2** : c'est le deuxième axe le plus important, indépendant du premier.
- Et ainsi de suite…

Plus le pourcentage de variance expliquée est élevé, plus la composante est importante.
Le graphique ci-dessous montre combien d'information chaque axe conserve, et la courbe rouge indique le cumul.
    """)
    st.divider()

    var_exp   = pca.explained_variance_ratio_ * 100
    var_cumul = np.cumsum(var_exp)
    axes      = [f"PC{i+1}" for i in range(len(var_exp))]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=axes, y=var_exp.round(1),
        name="Variance expliquée",
        marker_color=COLOR_V1,
        text=[f"{v:.1f}%" for v in var_exp],
        textposition="outside",
    ))
    fig.add_trace(go.Scatter(
        x=axes, y=var_cumul.round(1),
        name="Cumul",
        mode="lines+markers+text",
        line=dict(color=COLOR_V2, width=2.5),
        marker=dict(size=8),
        text=[f"{v:.0f}%" for v in var_cumul],
        textposition="top center",
        yaxis="y2",
    ))
    fig.update_layout(
        yaxis=dict(title="Variance expliquée (%)", range=[0, max(var_exp) * 1.3]),
        yaxis2=dict(title="Cumul (%)", overlaying="y", side="right",
                    range=[0, 110]),
        height=380, legend_title="", hovermode="x unified",
        margin=dict(t=20),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Tableau
    df_var = pd.DataFrame({
        "Composante":           axes,
        "Variance expliquée (%)": var_exp.round(2),
        "Cumul (%)":            var_cumul.round(2),
    })
    st.dataframe(df_var, use_container_width=True, hide_index=True)

    n_axes_80 = int(np.argmax(var_cumul >= 80)) + 1
    st.markdown(
        f"> 👉 Les **{n_axes_80} premières composantes** expliquent au moins **80%** "
        f"de la variance totale. PC1 et PC2 en capturent "
        f"**{var_cumul[1]:.1f}%** — le plan factoriel est "
        f"{'très représentatif' if var_cumul[1] >= 60 else 'partiellement représentatif'}."
    )


# ─────────────────────────────────────────────
# ONGLET 2 — CERCLE DE CORRÉLATION
# ─────────────────────────────────────────────
def tab_cercle(pca, variables, labels):
    st.subheader("Cercle de corrélation — Variables")
    st.markdown("""
Le cercle de corrélation montre comment chaque variable contribue aux axes de l'ACP.

Chaque flèche représente une variable. Voici comment le lire :
- Une **flèche longue** = la variable est bien représentée sur ces axes, elle contribue fortement.
- Une **flèche courte** = la variable est peu représentée sur ce plan, elle est surtout expliquée par d'autres axes.
- Deux **flèches dans la même direction** = ces deux variables évoluent ensemble (elles sont corrélées). Par exemple, loyer appartement et loyer maison ont tendance à être élevés dans les mêmes villes.
- Deux **flèches opposées** = ces variables évoluent en sens inverse. Par exemple, % cadres et % ouvriers vont généralement dans des directions opposées.

Utilise les menus ci-dessous pour changer les axes affichés.
    """)
    st.divider()

    ax_x = st.selectbox("Axe X :", [f"PC{i+1}" for i in range(pca.n_components_)],
                         index=0, key="cercle_x")
    ax_y = st.selectbox("Axe Y :", [f"PC{i+1}" for i in range(pca.n_components_)],
                         index=1, key="cercle_y")

    ix = int(ax_x[2]) - 1
    iy = int(ax_y[2]) - 1

    # Corrélations variables / composantes
    loadings = pca.components_
    corr_x = loadings[ix]
    corr_y = loadings[iy]

    # Facteur d'échelle pour les flèches
    std_x = np.sqrt(pca.explained_variance_[ix])
    std_y = np.sqrt(pca.explained_variance_[iy])

    fig = go.Figure()

    # Cercle unité
    theta = np.linspace(0, 2 * np.pi, 200)
    fig.add_trace(go.Scatter(
        x=np.cos(theta), y=np.sin(theta),
        mode="lines",
        line=dict(color="lightgrey", dash="dash"),
        showlegend=False,
    ))

    # Flèches et labels
    colors_var = px.colors.qualitative.Set2
    for i, (label, cx, cy) in enumerate(zip(labels, corr_x * std_x, corr_y * std_y)):
        color = colors_var[i % len(colors_var)]
        fig.add_annotation(
            x=cx, y=cy, ax=0, ay=0,
            xref="x", yref="y", axref="x", ayref="y",
            arrowhead=3, arrowsize=1.2,
            arrowwidth=2, arrowcolor=color,
        )
        fig.add_trace(go.Scatter(
            x=[cx * 1.12], y=[cy * 1.12],
            mode="text",
            text=[label],
            textfont=dict(size=11, color=color),
            showlegend=False,
        ))

    var_x = pca.explained_variance_ratio_[ix] * 100
    var_y = pca.explained_variance_ratio_[iy] * 100

    fig.update_layout(
        xaxis=dict(title=f"{ax_x} ({var_x:.1f}%)",
                   range=[-1.5, 1.5], zeroline=True,
                   zerolinecolor="lightgrey"),
        yaxis=dict(title=f"{ax_y} ({var_y:.1f}%)",
                   range=[-1.5, 1.5], zeroline=True,
                   zerolinecolor="lightgrey",
                   scaleanchor="x"),
        height=520,
        margin=dict(t=20),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Tableau des contributions
    st.markdown("#### 📊 Contributions des variables")
    df_contrib = pd.DataFrame({
        "Variable":           labels,
        f"Corrélation {ax_x}": (corr_x * std_x).round(3),
        f"Corrélation {ax_y}": (corr_y * std_y).round(3),
    }).sort_values(f"Corrélation {ax_x}", key=abs, ascending=False)
    st.dataframe(df_contrib, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
# ONGLET 3 — GRAPHE DES INDIVIDUS
# ─────────────────────────────────────────────
def tab_individus(df_acp, pca, ville1, ville2):
    st.subheader("Graphe des individus — Les villes dans le plan factoriel")
    st.markdown("""
Sur ce graphique, **chaque point représente une ville**. Les 483 villes françaises de plus de 20 000 habitants sont placées dans le plan factoriel selon leur profil socio-économique.

Comment le lire :
- **Deux villes proches** sur le graphique ont des profils similaires : elles se ressemblent sur les variables analysées (loyers, emploi, densité…).
- **Deux villes éloignées** sont très différentes l'une de l'autre.
- Les **deux villes que tu compares** sont surlignées en couleur avec un symbole en diamant pour les repérer facilement.
- Les villes situées **à droite** ont tendance à avoir des loyers élevés et beaucoup de cadres (car PC1 capture principalement ces variables).
- Les villes situées **en haut ou en bas** se distinguent principalement sur l'axe PC2 (superficie, taux d'emploi).

Utilise les menus ci-dessous pour changer les axes affichés.
    """)
    st.divider()

    ax_x = st.selectbox("Axe X :", [f"PC{i+1}" for i in range(pca.n_components_)],
                         index=0, key="ind_x")
    ax_y = st.selectbox("Axe Y :", [f"PC{i+1}" for i in range(pca.n_components_)],
                         index=1, key="ind_y")

    col_x = ax_x.replace("PC", "PC")
    col_y = ax_y.replace("PC", "PC")

    if col_x not in df_acp.columns or col_y not in df_acp.columns:
        st.warning("Composante non disponible.")
        return

    # Colorier les catégories
    def cat_ville(nom):
        if nom == ville1:
            return f"🔵 {ville1}"
        elif nom == ville2:
            return f"🔴 {ville2}"
        else:
            return "Autres villes"

    df_plot = df_acp.copy()
    df_plot["Catégorie"] = df_plot["nom_commune"].apply(cat_ville)

    color_map = {
        f"🔵 {ville1}": COLOR_V1,
        f"🔴 {ville2}": COLOR_V2,
        "Autres villes": COLOR_BASE,
    }
    size_map = {
        f"🔵 {ville1}": 18,
        f"🔴 {ville2}": 18,
        "Autres villes": 7,
    }

    fig = go.Figure()

    # Autres villes en arrière-plan
    df_autres = df_plot[df_plot["Catégorie"] == "Autres villes"]
    fig.add_trace(go.Scatter(
        x=df_autres[col_x], y=df_autres[col_y],
        mode="markers",
        marker=dict(color=COLOR_BASE, size=7),
        text=df_autres["nom_commune"],
        hovertemplate="<b>%{text}</b><br>%{x:.2f}, %{y:.2f}<extra></extra>",
        name="Autres villes",
    ))

    # Villes sélectionnées en avant-plan
    for ville, color in [(ville1, COLOR_V1), (ville2, COLOR_V2)]:
        row = df_plot[df_plot["nom_commune"] == ville]
        if not row.empty:
            fig.add_trace(go.Scatter(
                x=row[col_x], y=row[col_y],
                mode="markers+text",
                marker=dict(color=color, size=18,
                            line=dict(width=2, color="white"),
                            symbol="diamond"),
                text=[ville],
                textposition="top center",
                textfont=dict(size=12, color=color),
                hovertemplate=f"<b>{ville}</b><br>{col_x}: %{{x:.2f}}<br>{col_y}: %{{y:.2f}}<extra></extra>",
                name=ville,
            ))

    var_x = pca.explained_variance_ratio_[int(ax_x[2]) - 1] * 100
    var_y = pca.explained_variance_ratio_[int(ax_y[2]) - 1] * 100

    fig.update_layout(
        xaxis=dict(title=f"{ax_x} ({var_x:.1f}%)", zeroline=True,
                   zerolinecolor="lightgrey"),
        yaxis=dict(title=f"{ax_y} ({var_y:.1f}%)", zeroline=True,
                   zerolinecolor="lightgrey"),
        height=560,
        legend_title="",
        hovermode="closest",
        margin=dict(t=20),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Distance entre les deux villes dans le plan
    r1 = df_acp[df_acp["nom_commune"] == ville1]
    r2 = df_acp[df_acp["nom_commune"] == ville2]
    if not r1.empty and not r2.empty:
        d = np.sqrt(
            (r1["PC1"].values[0] - r2["PC1"].values[0])**2 +
            (r1["PC2"].values[0] - r2["PC2"].values[0])**2
        )
        # Distance moyenne entre villes pour comparaison
        all_dists = []
        coords_all = df_acp[["PC1", "PC2"]].values
        for i in range(min(500, len(coords_all))):
            for j in range(i+1, min(501, len(coords_all))):
                all_dists.append(np.sqrt(np.sum((coords_all[i] - coords_all[j])**2)))
        med_dist = np.median(all_dists)

        sim = "proches" if d < med_dist else "éloignées"
        st.markdown(
            f"> 👉 **{ville1}** et **{ville2}** sont **{sim}** dans le plan factoriel "
            f"(distance = {d:.2f} · médiane = {med_dist:.2f}). "
            + ("Leurs profils socio-économiques sont **similaires**."
               if sim == "proches"
               else "Leurs profils socio-économiques sont **distincts**.")
        )


# ─────────────────────────────────────────────
# ONGLET 4 — BIPLOT
# ─────────────────────────────────────────────
def tab_biplot(df_acp, pca, labels, ville1, ville2):
    st.subheader("Biplot — Individus + Variables superposés")
    st.markdown("""
Le biplot combine sur un seul graphique les deux vues précédentes : les villes (points) et les variables (flèches).

Cela permet de voir directement **quelles villes sont associées à quelles caractéristiques** :
- Une ville dans la **même direction qu'une flèche** = cette ville a une valeur élevée pour cette variable.
- Une ville dans la **direction opposée à une flèche** = cette ville a une valeur basse pour cette variable.

Par exemple, si les flèches "Loyer appt/m²" et "% Cadres" pointent vers la droite, et qu'une ville est aussi à droite, alors cette ville a probablement des loyers élevés et beaucoup de cadres.
    """)
    st.divider()

    ix, iy = 0, 1
    loadings = pca.components_
    std_x = np.sqrt(pca.explained_variance_[ix])
    std_y = np.sqrt(pca.explained_variance_[iy])

    scale = max(df_acp["PC1"].abs().max(), df_acp["PC2"].abs().max()) * 0.7

    fig = go.Figure()

    # Individus
    df_autres = df_acp[~df_acp["nom_commune"].isin([ville1, ville2])]
    fig.add_trace(go.Scatter(
        x=df_autres["PC1"], y=df_autres["PC2"],
        mode="markers",
        marker=dict(color=COLOR_BASE, size=6),
        text=df_autres["nom_commune"],
        hovertemplate="<b>%{text}</b><extra></extra>",
        name="Autres villes",
    ))

    for ville, color in [(ville1, COLOR_V1), (ville2, COLOR_V2)]:
        row = df_acp[df_acp["nom_commune"] == ville]
        if not row.empty:
            fig.add_trace(go.Scatter(
                x=row["PC1"], y=row["PC2"],
                mode="markers+text",
                marker=dict(color=color, size=16, symbol="diamond",
                            line=dict(width=2, color="white")),
                text=[ville],
                textposition="top center",
                textfont=dict(size=11, color=color),
                name=ville,
            ))

    # Flèches variables
    colors_var = px.colors.qualitative.Set1
    for i, label in enumerate(labels):
        cx = loadings[ix, i] * std_x / max(std_x, std_y) * scale
        cy = loadings[iy, i] * std_y / max(std_x, std_y) * scale
        color = colors_var[i % len(colors_var)]
        fig.add_annotation(
            x=cx, y=cy, ax=0, ay=0,
            xref="x", yref="y", axref="x", ayref="y",
            arrowhead=3, arrowsize=1.2, arrowwidth=2, arrowcolor=color,
        )
        fig.add_trace(go.Scatter(
            x=[cx * 1.15], y=[cy * 1.15],
            mode="text",
            text=[label],
            textfont=dict(size=10, color=color),
            showlegend=False,
        ))

    var_x = pca.explained_variance_ratio_[ix] * 100
    var_y = pca.explained_variance_ratio_[iy] * 100

    fig.update_layout(
        xaxis=dict(title=f"PC1 ({var_x:.1f}%)", zeroline=True,
                   zerolinecolor="lightgrey"),
        yaxis=dict(title=f"PC2 ({var_y:.1f}%)", zeroline=True,
                   zerolinecolor="lightgrey"),
        height=580, legend_title="", hovermode="closest",
        margin=dict(t=20),
    )
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────
# ONGLET 5 — PROFIL DES VILLES
# ─────────────────────────────────────────────
def tab_profil(df_acp, pca, variables, labels, ville1, ville2, scaler):
    st.subheader("Profil détaillé des deux villes sélectionnées")
    st.markdown("""
Ce graphique compare les deux villes choisies **variable par variable**, par rapport à la moyenne de toutes les villes françaises.

Les valeurs affichées sont des **z-scores** (écarts à la moyenne) :
- Un score **positif** = la ville est **au-dessus** de la moyenne nationale sur cette variable.
- Un score **négatif** = la ville est **en dessous** de la moyenne nationale.
- Un score **supérieur à +2 ou inférieur à -2** = la ville a une valeur exceptionnelle, très différente des autres villes.

Par exemple, un z-score de +2 pour la densité signifie que la ville est beaucoup plus dense que la moyenne des 483 villes analysées.
    """)
    st.divider()

    r1 = df_acp[df_acp["nom_commune"] == ville1]
    r2 = df_acp[df_acp["nom_commune"] == ville2]

    if r1.empty and r2.empty:
        st.info("Données non disponibles pour ces villes.")
        return

    # Valeurs standardisées
    fig = go.Figure()
    for ville, row, color in [(ville1, r1, COLOR_V1), (ville2, r2, COLOR_V2)]:
        if not row.empty:
            vals = [row[v].values[0] if v in row.columns else np.nan
                    for v in variables]
            # Standardiser manuellement pour avoir les z-scores
            vals_std = [(v - scaler.mean_[i]) / scaler.scale_[i]
                        if not np.isnan(v) else 0
                        for i, v in enumerate(vals)]
            fig.add_trace(go.Bar(
                x=labels,
                y=[round(v, 2) for v in vals_std],
                name=ville,
                marker_color=color,
                opacity=0.8,
                text=[f"{v:+.2f}" for v in vals_std],
                textposition="outside",
            ))

    fig.add_hline(y=0, line_dash="dash", line_color="grey", line_width=1)
    fig.update_layout(
        barmode="group",
        yaxis_title="Z-score (écart à la moyenne nationale)",
        height=420, legend_title="",
        xaxis_tickangle=-25,
        margin=dict(t=20),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("""
> 👉 Un z-score **positif** = la ville est **au-dessus de la moyenne** nationale sur cette variable.
> Un z-score **négatif** = elle est **en dessous**.
> Un z-score > 2 ou < -2 indique une valeur exceptionnelle.
    """)

    st.divider()

    # Tableau comparatif valeurs brutes
    st.markdown("#### 📋 Valeurs brutes comparées")
    rows = []
    for label, var in zip(labels, variables):
        v1_raw = r1[var].values[0] if not r1.empty and var in r1.columns else np.nan
        v2_raw = r2[var].values[0] if not r2.empty and var in r2.columns else np.nan
        moy = df_acp[var].mean() if var in df_acp.columns else np.nan
        rows.append({
            "Variable":             label,
            f"🔵 {ville1}":         round(v1_raw, 2) if not np.isnan(v1_raw) else "N/D",
            f"🔴 {ville2}":         round(v2_raw, 2) if not np.isnan(v2_raw) else "N/D",
            "Moyenne nationale":    round(moy, 2)    if not np.isnan(moy)    else "N/D",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
# FONCTION PRINCIPALE
# ─────────────────────────────────────────────
def show_acp(ville1, ville2, v1_info, v2_info):
    st.header("📐 Analyse en Composantes Principales (ACP)")
    st.caption(
        f"Comparaison : **{ville1}** vs **{ville2}** · "
        "Variables : population, densité, loyers, emploi, PCS · "
        f"Toutes les villes +20 000 hab"
    )

    with st.expander("Cest quoi une ACP ? Comprendre en 2 minutes"):
        st.markdown("""
Imagine que tu veux comparer 483 villes à la fois, mais que chaque ville est décrite par 9 chiffres différents : sa population, sa densité, ses loyers, le pourcentage de cadres, etc. C'est beaucoup trop d'informations pour les visualiser directement sur un graphique.

L'ACP (Analyse en Composantes Principales) est une méthode mathématique qui résout ce problème. Elle prend toutes ces informations et les résume en 2 ou 3 grandes dimensions, appelées axes ou composantes, qui capturent le maximum d'information possible. C'est un peu comme si tu prenais une photo d'un objet en 3D : tu perds un peu d'information mais tu gardes l'essentiel.

**Ce que tu peux lire dans les graphiques :**

- **Variance expliquée** : indique combien d'information chaque axe conserve. Si PC1 explique 51%, ça veut dire que cet axe résume à lui seul plus de la moitié de toutes les différences entre les villes.

- **Cercle de corrélation** : montre le rôle de chaque variable. Une flèche longue vers la droite = la variable tire fortement vers cet axe. Deux flèches dans la même direction = ces deux variables évoluent ensemble (elles sont corrélées).

- **Graphe des individus** : chaque point est une ville. Deux villes proches sur le graphique ont des profils similaires. Deux villes éloignées sont très différentes. Les deux villes que tu compares sont surlignées en couleur.

- **Biplot** : combine les deux graphiques précédents pour voir en un coup d'oeil quelles villes ressemblent à quelles caractéristiques.

- **Profil des villes** : compare les deux villes choisies variable par variable, par rapport à la moyenne de toutes les villes françaises. Un score positif veut dire que la ville est au-dessus de la moyenne, un score négatif qu'elle est en dessous.
        """)


    with st.spinner("Calcul de l'ACP en cours..."):
        result = build_acp_data()

    if result[0] is None:
        st.error(
            "❌ Données insuffisantes pour l'ACP.\n\n"
            "Assure-toi d'avoir exécuté `python prepare_data.py` avec au moins "
            "`communes.csv` et `emploi.csv` dans `data/clean/`."
        )
        return

    df_acp, X_scaled, variables, labels, pca, scaler = result

    st.info(
        f"📊 **{len(df_acp)} villes** analysées sur **{len(variables)} variables** : "
        f"{', '.join(labels)}"
    )

    onglet1, onglet2, onglet3, onglet4, onglet5 = st.tabs([
        "📊 Variance expliquée",
        "🔵 Cercle de corrélation",
        "🏙️ Graphe des individus",
        "🔀 Biplot",
        "🔍 Profil des villes",
    ])

    with onglet1:
        tab_variance(pca, variables)
    with onglet2:
        tab_cercle(pca, variables, labels)
    with onglet3:
        tab_individus(df_acp, pca, ville1, ville2)
    with onglet4:
        tab_biplot(df_acp, pca, labels, ville1, ville2)
    with onglet5:
        tab_profil(df_acp, pca, variables, labels, ville1, ville2, scaler)

    with st.expander("📚 Méthode et sources"):
        st.markdown(f"""
**Méthode** : ACP (sklearn.decomposition.PCA) après standardisation (StandardScaler).

**Variables utilisées ({len(variables)})** :

| Variable | Source |
|---|---|
| Population, Densité, Superficie | communes_france_2025.csv (INSEE) |
| Taux de chômage, Taux d'emploi | DS_RP_EMPLOI (INSEE RP {int(df_acp.get('annee', [2022])[0]) if 'annee' in df_acp.columns else 2022}) |
| % Cadres, % Ouvriers, % Employés | DS_RP_EMPLOI (INSEE RP) |
| Loyer appartement/m², Loyer maison/m² | DHUP — pred-app/mai-mef-dhup.csv |

**Villes** : {len(df_acp)} villes de plus de 20 000 habitants ayant des données disponibles.
        """)