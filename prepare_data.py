"""
Script de préparation des données — À exécuter UNE SEULE FOIS avant de lancer l'app.
Génère des fichiers nettoyés dans data/clean/ utilisés par tous les modules.

Usage :
    python prepare_data.py

Fichiers requis dans data/ :
    - communes_france_2025.csv                      (UTF-8, séparateur ;)
    - DS_RP_EMPLOI_LR_COMP_2022_data.csv
    - DS_RP_EMPLOI_LR_COMP_2022_metadata.csv
"""

import pandas as pd
import os

DATA_RAW   = "data"
DATA_CLEAN = os.path.join("data", "clean")
os.makedirs(DATA_CLEAN, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════
# 1. COMMUNES
#    Fichier : communes_france_2025.csv
#    Format  : UTF-8, séparateur ;, 483 lignes (toutes +20 000 hab)
#    Colonnes utiles :
#      code_insee, nom_standard, population, superficie_km2,
#      densite, latitude_mairie, longitude_mairie,
#      reg_nom, dep_nom, dep_code
# ═══════════════════════════════════════════════════════════════════
print("📍 Traitement communes...")

df_com = pd.read_csv(
    os.path.join(DATA_RAW, "communes_france_2025.csv"),
    sep=";",
    encoding="utf-8",
    low_memory=False,
    index_col=0,        # La première colonne est un index numérique inutile
)

# Renommage vers noms standardisés utilisés dans toute l'app
df_com = df_com.rename(columns={
    "nom_standard":    "nom_commune",
    "latitude_mairie": "latitude",
    "longitude_mairie":"longitude",
    "reg_nom":         "region",
    "dep_nom":         "departement",
})

# Nettoyages
df_com["code_insee"]    = df_com["code_insee"].astype(str).str.strip().str.zfill(5)
df_com["population"]    = pd.to_numeric(df_com["population"],    errors="coerce")
df_com["superficie_km2"]= pd.to_numeric(df_com["superficie_km2"],errors="coerce")
df_com["densite"]       = pd.to_numeric(df_com["densite"],       errors="coerce")
df_com["latitude"]      = pd.to_numeric(df_com["latitude"],      errors="coerce")
df_com["longitude"]     = pd.to_numeric(df_com["longitude"],     errors="coerce")
df_com["nom_commune"]   = df_com["nom_commune"].astype(str).str.strip()

# Tri alphabétique
df_com = df_com.sort_values("nom_commune").reset_index(drop=True)

# Colonnes finales à garder
COLS_COMMUNES = [
    "code_insee", "nom_commune", "population", "superficie_km2",
    "densite", "latitude", "longitude", "region", "departement", "dep_code",
    "altitude_moyenne", "grille_densite_texte",
    "niveau_equipements_services_texte",
]
COLS_COMMUNES = [c for c in COLS_COMMUNES if c in df_com.columns]
df_com = df_com[COLS_COMMUNES]

print(f"  {len(df_com)} communes · colonnes conservées : {list(df_com.columns)}")
print(df_com[["nom_commune", "code_insee", "population", "latitude", "longitude"]].head(5).to_string())

out = os.path.join(DATA_CLEAN, "communes.csv")
df_com.to_csv(out, index=False, encoding="utf-8-sig")
print(f"  ✅ {out}")


# ═══════════════════════════════════════════════════════════════════
# 2. EMPLOI
#    Fichier : DS_RP_EMPLOI_LR_COMP_2022_data.csv
#              DS_RP_EMPLOI_LR_COMP_2022_metadata.csv
#    Colonnes data : GEO, GEO_OBJECT, EMPSTA_ENQ, AGE, PCS,
#                    RP_MEASURE, FREQ, TIME_PERIOD, OBS_VALUE
#    Clé jointure  : GEO (code INSEE commune)
# ═══════════════════════════════════════════════════════════════════
print("\n💼 Traitement données emploi...")

df_emp = pd.read_csv(
    os.path.join(DATA_RAW, "DS_RP_EMPLOI_LR_COMP_2022_data.csv"),
    sep=None, engine="python", encoding="utf-8-sig",
)
df_meta = pd.read_csv(
    os.path.join(DATA_RAW, "DS_RP_EMPLOI_LR_COMP_2022_metadata.csv"),
    sep=None, engine="python", encoding="utf-8-sig",
)

print(f"  Data  : {len(df_emp):,} lignes · colonnes : {list(df_emp.columns)}")
print(f"  Meta  : {len(df_meta)} lignes · colonnes : {list(df_meta.columns)}")

# Nettoyage colonnes
df_emp.columns  = [c.strip() for c in df_emp.columns]
df_meta.columns = [c.strip() for c in df_meta.columns]

# Forcer les noms metadata si encodage cassé
if "COD_VAR" not in df_meta.columns:
    df_meta.columns = ["COD_VAR", "LIB_VAR", "COD_MOD", "LIB_MOD"]
    print("  ⚠️ Noms colonnes metadata forcés.")

for c in df_meta.columns:
    df_meta[c] = df_meta[c].astype(str).str.strip()

# Dictionnaires de décodage depuis metadata
def build_decode(meta, variable):
    sub = meta[meta["COD_VAR"] == variable][["COD_MOD", "LIB_MOD"]].copy()
    sub["COD_MOD"] = sub["COD_MOD"].astype(str).str.strip()
    # Correction encodage latin-1 mal converti
    sub["LIB_MOD"] = (
        sub["LIB_MOD"]
        .str.replace("Ã©", "é", regex=False)
        .str.replace("Ã¨", "è", regex=False)
        .str.replace("Ã ", "à", regex=False)
        .str.replace("Ã‰", "É", regex=False)
        .str.replace("Ã´", "ô", regex=False)
        .str.replace("Ã§", "ç", regex=False)
        .str.replace("Ã¹", "ù", regex=False)
        .str.replace("Ã»", "û", regex=False)
        .str.replace("Ã¢", "â", regex=False)
        .str.replace("Ã®", "î", regex=False)
        .str.replace("â€™", "'", regex=False)
        .str.replace("â€˜", "'", regex=False)
        .str.replace("â\x80\x93", "-", regex=False)
    )
    return dict(zip(sub["COD_MOD"], sub["LIB_MOD"]))

pcs_map    = build_decode(df_meta, "PCS")
empsta_map = build_decode(df_meta, "EMPSTA_ENQ")

# Fallback manuel si metadata vide ou mal encodée
PCS_FALLBACK = {
    "1":   "Agriculteurs exploitants",
    "2":   "Artisans, commerçants et chefs d'entreprise",
    "3":   "Cadres et professions intellectuelles supérieures",
    "4":   "Professions intermédiaires",
    "5":   "Employés",
    "6":   "Ouvriers",
    "_T":  "Total toutes PCS",
}
EMPSTA_FALLBACK = {
    "1":   "Actif occupé",
    "1T2": "Actif (occupé + chômeur)",
    "2":   "Chômeur",
}
for k, v in PCS_FALLBACK.items():
    pcs_map.setdefault(k, v)
for k, v in EMPSTA_FALLBACK.items():
    empsta_map.setdefault(k, v)

print(f"  PCS : {pcs_map}")
print(f"  EMPSTA : {empsta_map}")

# Nettoyage data emploi
df_emp["GEO"]         = df_emp["GEO"].astype(str).str.strip().str.zfill(5)
df_emp["OBS_VALUE"]   = pd.to_numeric(df_emp["OBS_VALUE"],   errors="coerce")
df_emp["TIME_PERIOD"] = pd.to_numeric(df_emp["TIME_PERIOD"], errors="coerce")
df_emp["EMPSTA_ENQ"]  = df_emp["EMPSTA_ENQ"].astype(str).str.strip()
df_emp["PCS"]         = df_emp["PCS"].astype(str).str.strip()
df_emp["AGE"]         = df_emp["AGE"].astype(str).str.strip()

# Garder seulement les communes
df_emp = df_emp[df_emp["GEO_OBJECT"] == "COM"].copy()
print(f"  Après filtre COM     : {len(df_emp):,} lignes")

# Garder années 2011+
df_emp = df_emp[df_emp["TIME_PERIOD"] >= 2011].copy()
print(f"  Après filtre 2011+   : {len(df_emp):,} lignes")

# Garder seulement les communes +20 000 hab
codes_com = set(df_com["code_insee"].tolist())
df_emp = df_emp[df_emp["GEO"].isin(codes_com)].copy()
print(f"  Après filtre +20k hab: {len(df_emp):,} lignes · {df_emp['GEO'].nunique()} communes")

# Ajouter libellés lisibles
df_emp["LIB_EMPSTA"] = df_emp["EMPSTA_ENQ"].map(empsta_map).fillna(df_emp["EMPSTA_ENQ"])
df_emp["LIB_PCS"]    = df_emp["PCS"].map(pcs_map).fillna(df_emp["PCS"])

# Jointure infos commune
df_emp = df_emp.merge(
    df_com[["code_insee", "nom_commune", "latitude", "longitude", "population"]],
    left_on="GEO", right_on="code_insee",
    how="left",
)

df_emp = df_emp.dropna(subset=["OBS_VALUE"]).reset_index(drop=True)
print(f"  Lignes finales       : {len(df_emp):,}")

out = os.path.join(DATA_CLEAN, "emploi.csv")
df_emp.to_csv(out, index=False, encoding="utf-8-sig")
print(f"  ✅ {out}")

print("\n🎉 Préparation terminée. Lance maintenant : streamlit run app.py")


# ═══════════════════════════════════════════════════════════════════
# 3. LOGEMENT
#    pred-app-mef-dhup.csv  → loyers appartements
#    pred-mai-mef-dhup.csv  → loyers maisons
#    Cle jointure : INSEE_C → code_insee communes
# ═══════════════════════════════════════════════════════════════════
print("\n🏠 Traitement données logement...")

def load_loyer(filename, type_bien):
    path = os.path.join(DATA_RAW, filename)
    # Séparateur tabulation, encodage UTF-8
    # Détecter le vrai séparateur
    df = pd.read_csv(path, sep=None, engine="python", encoding="latin-1")
    print(f"  Colonnes détectées ({filename}) : {list(df.columns)}")
    df.columns = [c.strip() for c in df.columns]

    # Code INSEE → string 5 caractères
    df["INSEE_C"] = df["INSEE_C"].astype(str).str.strip().str.zfill(5)

    # Virgule décimale française → point
    for col in ["loypredm2", "lwr.IPm2", "upr.IPm2", "R2_adj"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "."), errors="coerce"
            )
    for col in ["nbobs_com", "nbobs_mail"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["type_bien"] = type_bien
    return df

df_app = load_loyer("pred-app-mef-dhup.csv", "Appartement")
df_mai = load_loyer("pred-mai-mef-dhup.csv", "Maison")

print(f"  Appartements brut : {len(df_app):,} lignes")
print(f"  Maisons brut      : {len(df_mai):,} lignes")

# Concaténer
df_log = pd.concat([df_app, df_mai], ignore_index=True)

# Filtrer sur communes +20 000 hab uniquement
codes_com = set(df_com["code_insee"].tolist())
df_log = df_log[df_log["INSEE_C"].isin(codes_com)].copy()
print(f"  Après filtre +20k hab : {len(df_log):,} lignes · {df_log['INSEE_C'].nunique()} communes")

# Jointure avec infos communes
df_log = df_log.merge(
    df_com[["code_insee", "nom_commune", "latitude", "longitude",
            "population", "region", "departement", "superficie_km2"]],
    left_on="INSEE_C", right_on="code_insee",
    how="left",
)

# Renommage
df_log = df_log.rename(columns={
    "loypredm2": "loyer_m2",
    "lwr.IPm2":  "loyer_m2_min",
    "upr.IPm2":  "loyer_m2_max",
    "R2_adj":    "r2_adj",
    "TYPPRED":   "niveau_prediction",
    "nbobs_com": "nb_obs_commune",
})

COLS_LOG = [
    "nom_commune", "code_insee", "type_bien",
    "loyer_m2", "loyer_m2_min", "loyer_m2_max",
    "niveau_prediction", "nb_obs_commune", "r2_adj",
    "population", "superficie_km2", "region", "departement",
    "latitude", "longitude",
]
COLS_LOG = [c for c in COLS_LOG if c in df_log.columns]
df_log = df_log[COLS_LOG].dropna(subset=["loyer_m2"]).reset_index(drop=True)

print(f"  Lignes finales : {len(df_log):,}")
print(df_log[["nom_commune", "type_bien", "loyer_m2", "loyer_m2_min", "loyer_m2_max"]].head(6).to_string())

out = os.path.join(DATA_CLEAN, "logement.csv")
df_log.to_csv(out, index=False, encoding="utf-8-sig")
print(f"  ✅ {out}")

print("\n🎉 Tout est prêt. Lance : streamlit run app.py")


# ═══════════════════════════════════════════════════════════════════
# 4. CULTURE
#    Fichier : basilic.csv (Ministère de la Culture — BASILIC)
#    Colonnes connues :
#      nom, type_equipement, label_appellation,
#      commune, code_insee, dep, reg,
#      latitude, longitude, adresse
#    Clé jointure : code_insee → communes.csv
# ═══════════════════════════════════════════════════════════════════
print("\n🎭 Traitement données culture...")

df_cult = pd.read_csv(
    os.path.join(DATA_RAW, "basilic.csv"),
    sep=None, engine="python", encoding="utf-8-sig",
)

df_cult.columns = [c.strip().lower() for c in df_cult.columns]
print(f"  Colonnes détectées : {list(df_cult.columns)}")
print(f"  Lignes brutes : {len(df_cult):,}")

# Mapping robuste des colonnes (plusieurs variantes possibles selon export)
ALIAS_CULT = {
    "nom":              ["nom", "name", "denomination", "nom_du_lieu", "appellation"],
    "categorie":        ["type_equipement", "categorie", "type", "domaine", "type_de_lieu",
                         "label_et_appellation", "label_appellation"],
    "code_insee":       ["code_insee", "codeinsee", "insee", "com", "codecommune",
                         "code_commune", "inseecom"],
    "commune":          ["commune", "ville", "nom_commune", "libgeo", "libelle_commune"],
    "latitude":         ["latitude", "lat", "y", "geo_point_2d_lat"],
    "longitude":        ["longitude", "lon", "lng", "x", "long", "geo_point_2d_lon"],
    "adresse":          ["adresse", "adress", "address", "adr"],
    "departement":      ["dep", "departement", "code_dep", "dep_code"],
    "region":           ["reg", "region", "code_reg"],
}

def find_col_cult(df, aliases):
    for a in aliases:
        if a in df.columns:
            return a
    return None

rename_cult = {}
for target, aliases in ALIAS_CULT.items():
    found = find_col_cult(df_cult, aliases)
    if found and found != target:
        rename_cult[found] = target
    elif found is None:
        print(f"  ⚠️ Colonne '{target}' non trouvée (aliases: {aliases})")

df_cult = df_cult.rename(columns=rename_cult)

# Cas spécial : geo_point_2d peut être "lat,lon" dans une seule colonne
if "latitude" not in df_cult.columns:
    for c in df_cult.columns:
        if "geo_point" in c or "geoloc" in c or "coordonnees" in c:
            try:
                coords = df_cult[c].astype(str).str.split(",", expand=True)
                df_cult["latitude"]  = pd.to_numeric(coords[0], errors="coerce")
                df_cult["longitude"] = pd.to_numeric(coords[1], errors="coerce")
                print(f"  ℹ️ Coordonnées extraites depuis '{c}'")
                break
            except Exception:
                pass

# Nettoyage code INSEE
if "code_insee" in df_cult.columns:
    df_cult["code_insee"] = df_cult["code_insee"].astype(str).str.strip().str.zfill(5)

# Nettoyage coordonnées
for col in ["latitude", "longitude"]:
    if col in df_cult.columns:
        df_cult[col] = pd.to_numeric(
            df_cult[col].astype(str).str.replace(",", "."), errors="coerce"
        )

# Nettoyage catégorie
if "categorie" in df_cult.columns:
    df_cult["categorie"] = df_cult["categorie"].astype(str).str.strip()

# Nettoyage nom
if "nom" in df_cult.columns:
    df_cult["nom"] = df_cult["nom"].astype(str).str.strip()

# Filtre : garder seulement les communes +20 000 hab
codes_com = set(df_com["code_insee"].tolist())
if "code_insee" in df_cult.columns:
    df_cult = df_cult[df_cult["code_insee"].isin(codes_com)].copy()
    print(f"  Après filtre +20k hab : {len(df_cult):,} lieux · {df_cult['code_insee'].nunique()} communes")
else:
    print("  ⚠️ Impossible de filtrer sans code_insee — jointure sur nom commune")
    if "commune" in df_cult.columns:
        noms_com = set(df_com["nom_commune"].str.lower().tolist())
        df_cult = df_cult[df_cult["commune"].str.lower().isin(noms_com)].copy()
        print(f"  Après filtre nom commune : {len(df_cult):,} lieux")

# Jointure avec infos communes
join_key = "code_insee" if "code_insee" in df_cult.columns else None
if join_key:
    df_cult = df_cult.merge(
        df_com[["code_insee", "nom_commune", "population", "region",
                "departement", "latitude", "longitude"]].rename(
            columns={"latitude": "lat_commune", "longitude": "lon_commune"}),
        on="code_insee", how="left",
    )
    # Si lat/lon du lieu manquante → utiliser celle de la commune
    if "latitude" in df_cult.columns:
        df_cult["latitude"]  = df_cult["latitude"].fillna(df_cult["lat_commune"])
        df_cult["longitude"] = df_cult["longitude"].fillna(df_cult["lon_commune"])
    else:
        df_cult["latitude"]  = df_cult["lat_commune"]
        df_cult["longitude"] = df_cult["lon_commune"]
    df_cult = df_cult.drop(columns=["lat_commune", "lon_commune"], errors="ignore")

# Colonnes finales
COLS_CULT = [
    "nom", "categorie", "code_insee", "nom_commune",
    "adresse", "latitude", "longitude",
    "population", "region", "departement",
]
COLS_CULT = [c for c in COLS_CULT if c in df_cult.columns]
df_cult = df_cult[COLS_CULT].reset_index(drop=True)

print(f"  Lignes finales : {len(df_cult):,}")
if "categorie" in df_cult.columns:
    print(f"  Catégories : {df_cult['categorie'].value_counts().head(8).to_dict()}")

out = os.path.join(DATA_CLEAN, "culture.csv")
df_cult.to_csv(out, index=False, encoding="utf-8-sig")
print(f"  ✅ {out}")

print("\n🎉 Tout est prêt. Lance : streamlit run app.py")