"""Le catalogue des procédés de l'usine d'assets visuels.

Chaque type d'asset a son procédé optimal, sans clé d'API payante : génération
d'image par Antigravity CLI (`agy`, abonnement Google), post-traitement local
déterministe (Python/Pillow/NumPy, ou Blender sur le PC pour la 3D), et preuve
automatique avant fusion.
"""

from __future__ import annotations

from dataclasses import dataclass

TYPES_ASSETS = ("icone", "planche_icones", "illustration", "blason", "texture_pbr", "prop_3d")


@dataclass(frozen=True)
class Procede:
    """Ce que l'usine applique à un type d'asset."""

    type_asset: str
    titre: str
    machine: str
    transparent: bool
    raccordable: bool
    dimensions_defaut: str
    references_da: tuple[str, ...]
    generation: str
    post_traitement: str
    controles: tuple[str, ...]

    def consigne(self) -> str:
        refs = ", ".join(f"`{r}`" for r in self.references_da)
        controles = "; ".join(self.controles)
        return (
            f"Procédé retenu (`{self.type_asset}` — {self.titre}) :\n"
            f"- Références de DA à lire et passer à `generate_image` : {refs}.\n"
            f"- Génération (`generate_image` via l'abonnement Google) : {self.generation}\n"
            f"- Post-traitement local obligatoire : {self.post_traitement}\n"
            f"- Preuves avant de rendre la main : {controles}."
        )


PROCEDES: dict[str, Procede] = {
    "planche_icones": Procede(
        type_asset="planche_icones",
        titre="Planche d'icônes d'interface (économie de quota AI Pro)",
        machine="asset",
        transparent=True,
        raccordable=False,
        dimensions_defaut="128x128",
        references_da=("docs/interface/DA.md", "docs/interface/MATIERES.md"),
        generation=(
            "Produis UNE seule image carrée en grille uniforme 3x3 (ou 4x4) contenant toutes les icônes "
            "demandées dans l'ordre ligne par ligne, sur un fond uni neutre très contrasté (par exemple noir mat "
            "#000000 ou magenta #ff00ff), sans bordure ni texte ni numéro, style gravure/métal patiné/pigments "
            "mats de `docs/interface/DA.md`."
        ),
        post_traitement=(
            "Découpe et détoure la planche par `python3 -m atelier.fabrique decouper-planche <planche> "
            "--grille <RxC> --noms <n1,n2,...> --sortie <dossier> --taille 128`, puis supprime la planche brute."
        ),
        controles=(
            "chaque PNG existe et ouvre sans erreur",
            "dimensions carrées exactes",
            "fond transparent (alpha 0) et cœur strictement opaque (alpha max 255)",
            "couverture du sujet entre 5 % et 95 %",
        ),
    ),
    "icone": Procede(
        type_asset="icone",
        titre="Icône unitaire d'interface ou de sceau",
        machine="asset",
        transparent=True,
        raccordable=False,
        dimensions_defaut="128x128",
        references_da=("docs/interface/DA.md", "docs/interface/MATIERES.md"),
        generation=(
            "Produis une image carrée centrée d'un seul symbole lisible en petit format, sur fond uni "
            "contrasté sans ombre portée au bord ni texte, dans la palette sombre/gothique/médiévale de "
            "`docs/interface/DA.md` (pierre, bois brûlé, cuivre patiné, rouge garance, or vieilli)."
        ),
        post_traitement=(
            "Détoure et normalise par `python3 -m atelier.fabrique detourer <brut> <cible> --taille 128`, "
            "puis supprime le fichier brut."
        ),
        controles=(
            "PNG carré à la dimension demandée",
            "alpha strict (fond 0, cœur 255)",
            "sujet centré et lisible",
        ),
    ),
    "blason": Procede(
        type_asset="blason",
        titre="Blason, sceau ou drapeau détouré",
        machine="asset",
        transparent=True,
        raccordable=False,
        dimensions_defaut="512x512",
        references_da=("docs/direction-artistique/README.md", "docs/interface/DA.md"),
        generation=(
            "Produis un emblème héraldique ou un sceau de cire centré sur fond uni contrasté, matières mates "
            "perceptibles, aucun texte parasite, en prenant en référence les planches de "
            "`docs/direction-artistique/11_blasons/` ou `12_drapeaux/`."
        ),
        post_traitement=(
            "Détoure proprement par `python3 -m atelier.fabrique detourer <brut> <cible> --taille 512` "
            "pour garantir un alpha plein (255) sur le motif."
        ),
        controles=(
            "PNG détouré sans translucidité résiduelle (alpha max 255)",
            "dimensions exactes",
        ),
    ),
    "illustration": Procede(
        type_asset="illustration",
        titre="Illustration de direction artistique, portrait ou fond d'écran",
        machine="asset",
        transparent=False,
        raccordable=False,
        dimensions_defaut="1536x1024",
        references_da=("docs/direction-artistique/README.md", "docs/interface/DA.md"),
        generation=(
            "Produis une illustration dans la grammaire visuelle de `docs/direction-artistique/README.md` "
            "(réalisme historique illustré, lumière naturelle, matières perceptibles, palette terre d'ombre / "
            "calcaire crème / bleu ardoise / rouge garance / cuivre patiné), sans texte ni cadre."
        ),
        post_traitement=(
            "Vérifie le ratio et les dimensions cibles ; redimensionne proprement si besoin et enregistre "
            "dans `assets/manifeste.json`."
        ),
        controles=(
            "PNG intègre aux dimensions demandées",
            "aucun bord vide ni corruption",
        ),
    ),
    "texture_pbr": Procede(
        type_asset="texture_pbr",
        titre="Matériau PBR raccordable (albedo + normal + roughness + ao)",
        machine="asset",
        transparent=False,
        raccordable=True,
        dimensions_defaut="1024x1024",
        references_da=("docs/interface/MATIERES.md", "docs/direction-artistique/README.md"),
        generation=(
            "Produis une texture orthographique vue strictement de face (aucune perspective, aucune ombre "
            "directionnelle, éclairage parfaitement diffus, matière uniforme jusqu'aux bords)."
        ),
        post_traitement=(
            "Rends raccordable et synthétise le quatuor PBR localement par "
            "`python3 -m atelier.fabrique pbr <albedo_brut> <dossier_cible> --nom <id> --taille 1024 --raccorder`."
        ),
        controles=(
            "jeu PBR complet (albedo, normal, roughness, ao, height)",
            "dimensions identiques sur toutes les cartes",
            "erreur de couture aux bords sous le seuil",
        ),
    ),
    "prop_3d": Procede(
        type_asset="prop_3d",
        titre="Prop ou bâtiment 3D (vue de référence DA → maillage Blender/PC)",
        machine="pc",
        transparent=False,
        raccordable=False,
        dimensions_defaut="1024x1024",
        references_da=("docs/direction-artistique/README.md", "3d/local3d/README.md"),
        generation=(
            "Produis une vue 3/4 propre sur fond gris neutre uni, éclairage diffus sans ombre au sol, "
            "montrant l'objet entier à l'échelle métrique plausible."
        ),
        post_traitement=(
            "Range la vue de référence dans le dossier cible et prépare/normalise le maillage dans "
            "`3d/local3d/` (Blender 5.2 : échelle métrique, pivot au sol, 3 LOD, textures PBR, export FBX)."
        ),
        controles=(
            "vue de référence présente et conforme à la DA",
            "contrôle du manifeste vert",
        ),
    ),
}


def procede_pour(type_asset: str) -> Procede:
    """Le procédé canonique pour ce type d'asset ; refuse un type inconnu."""
    if type_asset not in PROCEDES:
        connus = ", ".join(TYPES_ASSETS)
        raise ValueError(f"type d'asset inconnu {type_asset!r} (connus : {connus})")
    return PROCEDES[type_asset]


def machine_pour(type_asset: str) -> str:
    """La file qui mène ce type d'asset : `pc` pour la 3D, `asset` pour le reste."""
    return procede_pour(type_asset).machine
