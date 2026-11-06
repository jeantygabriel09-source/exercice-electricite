from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

DATA_PATH = Path(__file__).resolve().parent / "donnees" / "consommation_propre.csv"
REQUIRED_COLUMNS = {
    "annee",
    "commune",
    "heures_courant",
    "kwh",
    "kwh_par_abonne",
    "mois",
    "quartier",
    "temperature_c",
    "type",
}

st.set_page_config(page_title="Électricité - 12 quartiers", layout="wide")

st.title("Exercice complet : l'électricité dans 12 quartiers")
st.markdown(
    "Tableau de bord analysant la consommation d'électricité par rapport "
    "à la chaleur et aux heures de courant."
)


@st.cache_data
def charger_donnees() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH)


try:
    df = charger_donnees()
except FileNotFoundError:
    st.error(
        "Le fichier `donnees/consommation_propre.csv` est introuvable. "
        "Exécutez d'abord le notebook `exploration.ipynb`."
    )
    st.stop()

colonnes_manquantes = REQUIRED_COLUMNS.difference(df.columns)
if colonnes_manquantes:
    st.error(
        "Le fichier de données ne contient pas les colonnes requises : "
        + ", ".join(sorted(colonnes_manquantes))
    )
    st.stop()

df["annee"] = pd.to_numeric(df["annee"], errors="raise").astype(int)
for colonne in ("heures_courant", "kwh", "kwh_par_abonne", "temperature_c"):
    df[colonne] = pd.to_numeric(df[colonne], errors="raise")

st.sidebar.header("Filtres")

communes_disponibles = sorted(df["commune"].dropna().unique().tolist())
communes_selectionnees = st.sidebar.multiselect(
    "Communes",
    options=communes_disponibles,
    default=communes_disponibles,
)

annees_disponibles = sorted(df["annee"].dropna().unique().tolist())
annee_defaut = 2025 if 2025 in annees_disponibles else annees_disponibles[-1]
annee_selectionnee = st.sidebar.selectbox(
    "Année",
    options=annees_disponibles,
    index=annees_disponibles.index(annee_defaut),
)

df_filtre = df.loc[
    (df["annee"] == annee_selectionnee)
    & df["commune"].isin(communes_selectionnees)
].copy()

if not communes_selectionnees:
    st.warning("Aucune commune n'est choisie.")

st.subheader("Indicateurs clés")
col1, col2, col3 = st.columns(3)

total_kwh = df_filtre["kwh"].sum() / 1e6
moy_abonne = df_filtre["kwh_par_abonne"].mean()
moy_heures = df_filtre["heures_courant"].mean()

col1.metric("Consommation totale", f"{total_kwh:.2f} millions de kWh")
col2.metric(
    "Consommation par abonné",
    "—" if pd.isna(moy_abonne) else f"{moy_abonne:.1f} kWh",
)
col3.metric(
    "Moyenne des heures de courant",
    "—" if pd.isna(moy_heures) else f"{moy_heures:.1f} heures",
)

st.subheader("Analyses et corrélations")
onglet_correlation, onglet_evolution, onglet_quartiers, onglet_details = st.tabs(
    [
        "Chaleur ou courant ?",
        "Évolution temporelle",
        "Répartition par quartier",
        "Détails",
    ]
)

residentiel = df.loc[
    df["type"]
    .astype("string")
    .str.strip()
    .str.casefold()
    .eq("résidentiel")
    .fillna(False)
].copy()
residentiel_filtre = residentiel.loc[
    (residentiel["annee"] == annee_selectionnee)
    & residentiel["commune"].isin(communes_selectionnees)
]

with onglet_correlation:
    st.markdown(
        "### Consommation par abonné : heures de courant et température"
    )
    if len(residentiel) >= 2:
        corr_courant = residentiel["kwh_par_abonne"].corr(
            residentiel["heures_courant"]
        )
        corr_temperature = residentiel["kwh_par_abonne"].corr(
            residentiel["temperature_c"]
        )
        metric1, metric2 = st.columns(2)
        metric1.metric("Corrélation avec les heures de courant", f"{corr_courant:.2f}")
        metric2.metric("Corrélation avec la température", f"{corr_temperature:.2f}")
        st.caption(
            "Corrélations calculées sur tous les relevés résidentiels. "
            "Les graphiques suivent les filtres sélectionnés."
        )

    if residentiel_filtre.empty:
        st.info("Aucune donnée résidentielle pour les filtres sélectionnés.")
    else:
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))
        axes[0].scatter(
            residentiel_filtre["heures_courant"],
            residentiel_filtre["kwh_par_abonne"],
            alpha=0.6,
            color="firebrick",
        )
        axes[0].set_xlabel("Heures de courant par jour")
        axes[0].set_ylabel("Consommation par abonné (kWh)")
        axes[0].set_title("Courant et consommation")

        axes[1].scatter(
            residentiel_filtre["temperature_c"],
            residentiel_filtre["kwh_par_abonne"],
            alpha=0.6,
            color="darkorange",
        )
        axes[1].set_xlabel("Température (°C)")
        axes[1].set_ylabel("Consommation par abonné (kWh)")
        axes[1].set_title("Température et consommation")
        fig.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

with onglet_evolution:
    st.markdown("### Évolution de la consommation")
    if df_filtre.empty:
        st.info("Aucune donnée pour les filtres sélectionnés.")
    else:
        conso_mois = df_filtre.groupby("mois")["kwh"].sum()
        st.line_chart(conso_mois)

with onglet_quartiers:
    st.markdown("### Répartition par quartier")
    if df_filtre.empty:
        st.info("Aucune donnée pour les filtres sélectionnés.")
    else:
        conso_quartier = df_filtre.groupby("quartier")["kwh"].sum().sort_values()
        st.bar_chart(conso_quartier)

with onglet_details:
    st.markdown("### Données filtrées")
    st.dataframe(df_filtre, width="stretch")

st.markdown("---")
with st.expander("Voir la conclusion générale de l'exercice"):
    st.markdown(
        """
        Pour les quartiers résidentiels, la consommation par abonné est fortement
        corrélée aux heures de courant (0,76) et faiblement corrélée, négativement,
        à la température (-0,15). Ces associations ne démontrent pas à elles seules
        un lien de causalité.
        """
    )
