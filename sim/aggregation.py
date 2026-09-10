"""
Agrégation dérivée : la Province se recalcule, elle ne s'estampille pas.

`cell_id` est la seule clé spatiale. La Province n'est donc pas un
champ posé sur une entité, mais le regroupement des cellules qui relèvent
aujourd'hui d'un centre administratif plutôt que d'un autre.

Chaîne causale : un centre administratif exerce son autorité sur les terres qui
lui sont les plus proches. Une cellule relève donc du centre le plus proche
d'elle, et de personne d'autre. Quand un centre se déplace, aucune cellule
n'est réécrite : la réponse à « de qui cette terre relève-t-elle ? » est
simplement recalculée.

Entrées lues, jamais écrites — elles vivent toutes dans `data/` :
- `data/world-1400.json` — position géographique de chaque cellule
  (`centroid.lat`, `centroid.lon`, repère WGS84) ;
- `data/province-centres-1400.json` — les centres administratifs
  (`coordinates`) et le paramètre de projection (`projection.mid_latitude`).

Voir `sim/MODELE.md` pour la provenance des données,
la projection employée, la règle de départage des égalités et la politique de
refus de deviner.
"""

import dataclasses
import json
import math
import pathlib

from sim import constants as _constantes
from sim.model import _NoBadSpatialField

# Racine du dépôt : un niveau au-dessus du paquet sim/
_RACINE_DEPOT = pathlib.Path(__file__).parent.parent

_CHEMIN_CELLULES = _RACINE_DEPOT / "data" / "world-1400.json"
_CHEMIN_CENTRES = _RACINE_DEPOT / "data" / "province-centres-1400.json"

# Clés des documents lus. Nommées ici, jamais recopiées dans les corps de
# fonctions : un chemin de lecture dérive, il ne se répète pas.
_CLE_CELLULES = "cellules"
_CLE_CENTROIDE = "centroid"
_CLE_IDENTIFIANT_CELLULE = "cell_id"
_CLE_LATITUDE = "lat"
_CLE_LONGITUDE = "lon"
_CLE_CENTRES = "coordinates"
_CLE_PROJECTION = "projection"
_CLE_LATITUDE_MOYENNE = "mid_latitude"
_CLE_IDENTIFIANT_CENTRE = "id"
_CLE_NOM_CENTRE = "name"


class PositionCelluleInconnue(LookupError):
    """
    Levée quand une cellule chargée n'a aucune position connue.

    Le code refuse d'attribuer une province par défaut et refuse d'écarter la
    cellule en silence : l'absence de donnée se déclare, elle ne s'invente pas.
    """


@dataclasses.dataclass(frozen=True)
class CentreAdministratif(_NoBadSpatialField):
    """
    Un centre administratif hérité du jeu, tel que lu dans le fichier.

    Champs :
        id   : identifiant du centre, lu du fichier.
        name : nom d'usage du centre, lu du fichier.
        lon  : longitude géographique du centre (degrés).
        lat  : latitude géographique du centre (degrés).

    Enregistrement immuable : le redessin d'un centre produit un nouvel
    enregistrement, il ne réécrit pas l'ancien.
    """

    id: int
    name: str
    lon: float
    lat: float


@dataclasses.dataclass(frozen=True)
class Regroupement(_NoBadSpatialField):
    """
    Vue dérivée : l'ensemble des cellules qui relèvent d'un centre donné.

    Cette vue vit hors de `sim.model` à dessein. `sim.model` contient les
    entités persistées que le moteur fait évoluer ; y déclarer ce type
    inviterait à traiter l'appartenance comme un état stockable, ce que
    la clé spatiale unique interdit. Un regroupement se recalcule, il ne se
    conserve pas.

    Champs :
        id       : identifiant du centre dont relèvent ces cellules.
        name     : nom du centre.
        cell_ids : identifiants des cellules qui en relèvent, triés.
                   Un tuple vide est un fait mesuré — un centre peut
                   n'attirer aucune cellule.
    """

    id: int
    name: str
    cell_ids: tuple


def charger_positions(path=None) -> dict:
    """
    Lit la position géographique de chaque cellule dans les artefacts G3.

    Rend un dictionnaire `cell_id → (latitude, longitude)` en degrés. Le
    nombre de cellules est celui du fichier ; il n'est écrit nulle part.
    """
    chemin = pathlib.Path(path) if path is not None else _CHEMIN_CELLULES
    document = json.loads(chemin.read_text(encoding="utf-8"))

    positions: dict = {}
    for brute in document[_CLE_CELLULES]:
        centroide = brute[_CLE_CENTROIDE]
        positions[brute[_CLE_IDENTIFIANT_CELLULE]] = (
            centroide[_CLE_LATITUDE],
            centroide[_CLE_LONGITUDE],
        )
    return positions


def charger_centres(path=None) -> list:
    """
    Lit les centres administratifs hérités du jeu.

    Rend la liste des enregistrements du tableau `coordinates`, dans l'ordre
    du fichier. Leur nombre est celui du fichier.
    """
    chemin = pathlib.Path(path) if path is not None else _CHEMIN_CENTRES
    document = json.loads(chemin.read_text(encoding="utf-8"))

    return [
        CentreAdministratif(
            id=brut[_CLE_IDENTIFIANT_CENTRE],
            name=brut[_CLE_NOM_CENTRE],
            lon=brut[_CLE_LONGITUDE],
            lat=brut[_CLE_LATITUDE],
        )
        for brut in document[_CLE_CENTRES]
    ]


def charger_latitude_moyenne(path=None) -> float:
    """
    Lit le paramètre de projection `projection.mid_latitude` du fichier de
    centres. Ce paramètre n'est jamais recopié dans un corps de fonction :
    la projection est celle que le fichier documente lui-même.
    """
    chemin = pathlib.Path(path) if path is not None else _CHEMIN_CENTRES
    document = json.loads(chemin.read_text(encoding="utf-8"))
    return document[_CLE_PROJECTION][_CLE_LATITUDE_MOYENNE]


def facteur_de_projection(latitude_moyenne: float) -> float:
    """
    Facteur d'écrasement des longitudes de la projection équirectangulaire
    documentée par le fichier de centres : `x = lon × cos(mid_latitude)`.
    """
    return math.cos(math.radians(latitude_moyenne))


def projeter(latitude: float, longitude: float, facteur: float) -> tuple:
    """
    Projette une position géographique dans le plan du fichier de centres :
    `x = lon × facteur`, `y = −lat`.
    """
    return (longitude * facteur, -latitude)


def derive_appartenance(positions: dict, centres, latitude_moyenne: float) -> dict:
    """
    Fonction pure : rend `cell_id → id du centre dont la cellule relève`.

    Ne modifie aucun objet reçu, n'écrit aucun fichier, et deux appels sur les
    mêmes entrées rendent le même résultat — y compris si la liste des centres
    est passée dans un ordre différent.

    Départage des égalités (D4) : à distance exactement égale, la cellule
    relève du centre dont l'`id` est le plus petit. La comparaison porte sur
    les carrés des distances (même ordre, pas de racine carrée).
    """
    if not centres:
        raise ValueError(
            "Aucun centre administratif fourni : l'appartenance n'est pas "
            "dérivable. Le code refuse de deviner une province."
        )

    facteur = facteur_de_projection(latitude_moyenne)
    centres_projetes = []
    for centre in centres:
        abscisse, ordonnee = projeter(centre.lat, centre.lon, facteur)
        centres_projetes.append((centre.id, abscisse, ordonnee))

    appartenance: dict = {}
    for cell_id in sorted(positions):
        latitude, longitude = positions[cell_id]
        abscisse_cellule, ordonnee_cellule = projeter(latitude, longitude, facteur)

        meilleur_id = None
        meilleur_carre = None
        for centre_id, abscisse, ordonnee in centres_projetes:
            ecart_x = abscisse_cellule - abscisse
            ecart_y = ordonnee_cellule - ordonnee
            carre = ecart_x * ecart_x + ecart_y * ecart_y
            if (
                meilleur_carre is None
                or carre < meilleur_carre
                or (carre == meilleur_carre and centre_id < meilleur_id)
            ):
                meilleur_carre = carre
                meilleur_id = centre_id

        appartenance[cell_id] = meilleur_id

    return appartenance


def positions_du_monde(world, positions: dict) -> dict:
    """
    Restreint les positions aux cellules réellement chargées par le monde.

    Refuse de deviner (D5) : si une cellule chargée n'a pas de position
    connue, lève `PositionCelluleInconnue` en nommant la cellule. Aucune
    province par défaut, aucun écart silencieux.
    """
    retenues: dict = {}
    for cell_id in sorted(world.cells):
        if cell_id not in positions:
            raise PositionCelluleInconnue(
                f"cellule {cell_id} : aucune position connue dans les artefacts "
                "géographiques. Le code refuse d'attribuer une province par "
                "défaut et refuse d'écarter la cellule en silence."
            )
        retenues[cell_id] = positions[cell_id]
    return retenues


def regroupements_depuis_appartenance(appartenance: dict, centres) -> tuple:
    """
    Construit la vue dérivée à partir de l'appartenance.

    Tous les centres lus figurent dans la vue, y compris ceux qui n'attirent
    aucune cellule : le nombre de provinces peuplées est un fait mesuré, pas
    un plancher imposé (D6).
    """
    cellules_par_centre: dict = {centre.id: [] for centre in centres}
    for cell_id in sorted(appartenance):
        cellules_par_centre[appartenance[cell_id]].append(cell_id)

    return tuple(
        Regroupement(
            id=centre.id,
            name=centre.name,
            cell_ids=tuple(cellules_par_centre[centre.id]),
        )
        for centre in sorted(centres, key=lambda centre: centre.id)
    )


def agregat_depuis_monde(world, positions=None, centres=None, latitude_moyenne=None) -> tuple:
    """
    Adaptateur en lecture seule : lit `World.cells` et rend la vue dérivée.

    N'écrit rien, ni sur les cellules, ni sur disque. Les entrées non
    fournies sont lues des fichiers.
    """
    if positions is None:
        positions = charger_positions()
    if centres is None:
        centres = charger_centres()
    if latitude_moyenne is None:
        latitude_moyenne = charger_latitude_moyenne()

    retenues = positions_du_monde(world, positions)
    appartenance = derive_appartenance(retenues, centres, latitude_moyenne)
    return regroupements_depuis_appartenance(appartenance, centres)


def appartenance_depuis_regroupements(regroupements) -> dict:
    """Relit la vue dérivée et rend `cell_id → id du centre`."""
    appartenance: dict = {}
    for regroupement in regroupements:
        for cell_id in regroupement.cell_ids:
            appartenance[cell_id] = regroupement.id
    return appartenance


def province_de_cellule(cell_id: int, regroupements):
    """
    Consultation : de quel regroupement cette cellule relève-t-elle ?

    Rend le regroupement, ou `None` si la cellule n'apparaît dans aucun. Ce
    `None` est un fait consultable, pas une province par défaut.
    """
    for regroupement in regroupements:
        if cell_id in regroupement.cell_ids:
            return regroupement
    return None


def nom_de_province_de_cellule(cell_id: int, regroupements):
    """Rend le nom du centre dont relève la cellule, ou `None`."""
    regroupement = province_de_cellule(cell_id, regroupements)
    if regroupement is None:
        return None
    return regroupement.name


def identifiant_de_province_de_cellule(cell_id: int, regroupements):
    """Rend l'identifiant du centre dont relève la cellule, ou `None`."""
    regroupement = province_de_cellule(cell_id, regroupements)
    if regroupement is None:
        return None
    return regroupement.id


def regroupements_non_vides(regroupements) -> tuple:
    """Rend les regroupements comptant au moins une cellule (fait mesuré)."""
    return tuple(
        regroupement for regroupement in regroupements if regroupement.cell_ids
    )


# --- Bourg : vue dérivée de la part non agricole ---


@dataclasses.dataclass(frozen=True)
class RepartitionBourg(_NoBadSpatialField):
    """
    Vue dérivée : répartition bourg / campagne dans une cellule.

    Le bourg regroupe les habitants qui ne tirent pas leur nourriture des
    champs de la cellule ; la campagne est définie comme le reste, donc la
    somme des deux vaut exactement la population.

    Champs :
        cell_id               : identifiant de la cellule.
        habitants_du_bourg    : population non agricole (troncature entière).
        habitants_des_champs  : population agricole, dérivée comme le reste.
    """

    cell_id: int
    habitants_du_bourg: int
    habitants_des_champs: int


def _gisements_de_cellule(world, cell_id: int) -> list:
    """Gisements lus dans la carte figée, jamais recopiés ailleurs."""
    entree = world.carte.get(cell_id) or {}
    return entree.get("gisements") or []


def _part_non_agricole(gisements) -> float:
    """Relit la fonction unique du lot 044 ; aucune seconde version ici."""
    return _constantes.part_miniere_de(
        gisements, _constantes.facteurs_richesse_extraction()
    )


def repartition_bourg_de_cellule(cellule, gisements) -> RepartitionBourg:
    """
    Fonction pure : rend la répartition bourg / campagne d'une cellule.

    Ne modifie aucun objet reçu. La troncature est délibérée ; la campagne
    est le reste, donc personne ne se perd.
    """
    habitants_du_bourg = int(cellule.population * _part_non_agricole(gisements))
    habitants_des_champs = cellule.population - habitants_du_bourg
    return RepartitionBourg(
        cell_id=cellule.cell_id,
        habitants_du_bourg=habitants_du_bourg,
        habitants_des_champs=habitants_des_champs,
    )


def bourg_depuis_monde(world) -> tuple:
    """
    Adaptateur en lecture seule : lit `World.cells` et la carte, rend la vue.

    N'écrit rien, ni sur les cellules, ni sur disque. L'ordre de sortie suit
    `cell_id` croissant.
    """
    return tuple(
        repartition_bourg_de_cellule(
            world.cells[cell_id], _gisements_de_cellule(world, cell_id)
        )
        for cell_id in sorted(world.cells)
    )


def repartition_bourg_de_cellule_consultation(cell_id: int, repartitions):
    """
    Consultation : quelle répartition pour cette cellule ?

    Rend l'enregistrement, ou `None` si la cellule n'apparaît dans aucun.
    """
    for repartition in repartitions:
        if repartition.cell_id == cell_id:
            return repartition
    return None


def habitants_du_bourg_de_cellule(cell_id: int, repartitions) -> int | None:
    """Rend le nombre d'habitants du bourg, ou `None` si la cellule est absente."""
    repartition = repartition_bourg_de_cellule_consultation(cell_id, repartitions)
    if repartition is None:
        return None
    return repartition.habitants_du_bourg


def habitants_des_champs_de_cellule(cell_id: int, repartitions) -> int | None:
    """Rend le nombre d'habitants des champs, ou `None` si la cellule est absente."""
    repartition = repartition_bourg_de_cellule_consultation(cell_id, repartitions)
    if repartition is None:
        return None
    return repartition.habitants_des_champs


def repartitions_avec_bourg(repartitions) -> tuple:
    """Rend les répartitions dont le bourg compte au moins un habitant."""
    return tuple(
        repartition
        for repartition in repartitions
        if repartition.habitants_du_bourg > 0
    )
