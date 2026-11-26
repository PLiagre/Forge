"""Les grandes régions de population de 1400 : leurs pays, leur cible d'habitants et leur part cultivée.

La table `data/population-1400.json` réunit les pays de 1400 (puissances et terres sans État de la
table des frontières) en grandes régions. Chaque région porte sa cible d'habitants vers 1400,
dérivée de sa composition en pays d'aujourd'hui sourcés, et la part de sa terre mise en culture.
Une cellule nommée par une région lui revient quel que soit son pays : c'est ainsi qu'un pays tenu
à cheval sur deux régions se partage. Rien ne se pose sur le monde : la table règle une part de
terre, jamais un habitant, et le tick ne la lit pas. La population reste dérivée de la production.
"""
import dataclasses
import json
import math
import pathlib
from fractions import Fraction

from sim.frontieres import (
    charger_frontieres, frontieres_du_monde, puissances_des_lieux, terres_des_lieux, villes_des_lieux,
)
from sim.model import _NoBadSpatialField
from sim.puissances import charger_table, puissances_depuis_monde

_CHEMIN = pathlib.Path(__file__).resolve().parents[1] / "data" / "population-1400.json"
_DATE = "1400-01-01"
_CLES = frozenset({"date", "fidelite", "tolerance", "sources", "regions"})
_CLES_REGION = frozenset({"id", "nom", "puissances", "terres", "cellules", "raison_cellules",
                          "part_cultivee", "habitants_1400", "cible"})
_CLES_PART = frozenset({"pays_actuel", "habitants", "source"})
_CLES_PART_PARTIELLE = _CLES_PART | {"part", "raison"}


class RegionInvalide(ValueError):
    """Une ligne de la table des régions est absente, mal formée ou contredit la carte."""


@dataclasses.dataclass(frozen=True)
class PaysActuel(_NoBadSpatialField):
    """Un pays d'aujourd'hui dans la composition d'une région : ses habitants en 1400 et la part
    qui en revient à la région (1 quand la carte le couvre en entier)."""
    pays_actuel: str
    habitants: int
    part: Fraction
    source: str
    raison: str | None


@dataclasses.dataclass(frozen=True)
class Region(_NoBadSpatialField):
    id: str
    nom: str
    puissances: tuple
    terres: tuple
    cellules: tuple
    part_cultivee: float
    habitants_1400: tuple
    cible: int


@dataclasses.dataclass(frozen=True)
class TableDesRegions(_NoBadSpatialField):
    date: str
    tolerance: Fraction
    sources: dict
    regions: tuple                  # triées par identifiant
    region_de_puissance: dict       # puissance → identifiant de sa région
    region_de_terre: dict           # terre sans État → identifiant de sa région
    region_de_cellule: dict         # cell_id nommée par une région → identifiant de cette région

    def par_id(self) -> dict:
        return {region.id: region for region in self.regions}

    def fourchette(self, region) -> tuple:
        """Les bornes d'habitants de la région, la cible à la tolérance près, en fractions exactes."""
        return region.cible * (1 - self.tolerance), region.cible * (1 + self.tolerance)


def _refus(identifiant, champ, motif):
    return RegionInvalide(f"région {identifiant!r}, champ {champ} : {motif}")


def _texte(valeur, identifiant, champ):
    if not isinstance(valeur, str) or not valeur.strip():
        raise _refus(identifiant, champ, "texte absent ou vide")
    return valeur


def _entier(valeur, identifiant, champ):
    if isinstance(valeur, bool) or not isinstance(valeur, int):
        raise _refus(identifiant, champ, f"entier attendu, pas {valeur!r}")
    return valeur


def _liste(valeur, identifiant, champ):
    if not isinstance(valeur, list):
        raise _refus(identifiant, champ, "liste attendue")
    return valeur


def _fraction(valeur, identifiant, champ):
    """Une fraction écrite « a/b » ; refuse un nombre, un texte illisible et un dénominateur nul."""
    if not isinstance(valeur, str):
        raise _refus(identifiant, champ, f"fraction « a/b » attendue, pas {valeur!r}")
    try:
        return Fraction(valeur)
    except (ValueError, ZeroDivisionError) as erreur:
        raise _refus(identifiant, champ, f"fraction illisible {valeur!r}") from erreur


def _composition(brutes, identifiant, sources):
    """Les pays d'aujourd'hui d'une région ; une part partielle dit sa raison."""
    if not isinstance(brutes, list) or not brutes:
        raise _refus(identifiant, "habitants_1400", "liste vide : la cible n'a pas de source")
    lus = []
    for brute in brutes:
        if not isinstance(brute, dict) or not _CLES_PART <= set(brute) <= _CLES_PART_PARTIELLE:
            raise _refus(identifiant, "habitants_1400", f"ligne {brute!r} : clés {sorted(_CLES_PART)} attendues")
        nom = _texte(brute["pays_actuel"], identifiant, "habitants_1400.pays_actuel")
        champ = f"habitants_1400.{nom}"
        habitants = _entier(brute["habitants"], identifiant, f"{champ}.habitants")
        if habitants <= 0:
            raise _refus(identifiant, f"{champ}.habitants", f"nombre positif attendu, pas {habitants}")
        if brute["source"] not in sources:
            raise _refus(identifiant, f"{champ}.source", f"source inconnue {brute['source']!r}")
        part, raison = Fraction(1), None
        if "part" in brute or "raison" in brute:
            if "part" not in brute or "raison" not in brute:
                raise _refus(identifiant, champ, "une part partielle porte sa part et sa raison")
            part = _fraction(brute["part"], identifiant, f"{champ}.part")
            if not 0 < part <= 1:
                raise _refus(identifiant, f"{champ}.part", f"part hors de ]0, 1] : {brute['part']}")
            raison = _texte(brute["raison"], identifiant, f"{champ}.raison")
        lus.append(PaysActuel(nom, habitants, part, brute["source"], raison))
    return tuple(lus)


def _region(brute, sources, puissances_connues, terres_connues):
    if not isinstance(brute, dict):
        raise RegionInvalide(f"région {brute!r} : ligne attendue")
    identifiant = brute.get("id")
    if set(brute) != _CLES_REGION:
        raise _refus(identifiant, "clés", f"clés {sorted(_CLES_REGION)} attendues")
    _texte(identifiant, identifiant, "id")
    nom = _texte(brute["nom"], identifiant, "nom")
    puissances = []
    for valeur in _liste(brute["puissances"], identifiant, "puissances"):
        if _entier(valeur, identifiant, "puissances") not in puissances_connues:
            raise _refus(identifiant, "puissances", f"puissance inconnue {valeur}")
        puissances.append(valeur)
    terres = []
    for valeur in _liste(brute["terres"], identifiant, "terres"):
        if valeur not in terres_connues:
            raise _refus(identifiant, "terres", f"terre sans État inconnue {valeur!r}")
        terres.append(valeur)
    cellules = [_entier(valeur, identifiant, "cellules")
                for valeur in _liste(brute["cellules"], identifiant, "cellules")]
    if cellules:
        _texte(brute["raison_cellules"], identifiant, "raison_cellules")
    elif brute["raison_cellules"] is not None:
        raise _refus(identifiant, "raison_cellules", "une raison sans cellule nommée")
    part = brute["part_cultivee"]
    if (isinstance(part, bool) or not isinstance(part, (int, float)) or not math.isfinite(part)
            or not 0 < part <= 1):
        raise _refus(identifiant, "part_cultivee", f"part hors de ]0, 1] : {part!r}")
    composition = _composition(brute["habitants_1400"], identifiant, sources)
    cible = _entier(brute["cible"], identifiant, "cible")
    derivee = round(sum(pays.habitants * pays.part for pays in composition))
    if cible != derivee:
        raise _refus(identifiant, "cible", f"{cible} déclarés, {derivee} d'après habitants_1400")
    return Region(identifiant, nom, tuple(sorted(puissances)), tuple(sorted(terres)), tuple(sorted(cellules)),
                  float(part), composition, cible)


def _une_fois(regions, champ, connus):
    """Chaque élément connu dans une région et une seule ; rend élément → région."""
    vus = {}
    for region in regions:
        for element in getattr(region, champ):
            if element in vus:
                raise _refus(region.id, champ, f"{element!r} déjà dans la région {vus[element]!r}")
            vus[element] = region.id
    for element in sorted(connus, key=str):
        if element not in vus:
            raise RegionInvalide(f"{champ} {element!r} : dans aucune région de la table")
    return dict(sorted(vus.items(), key=lambda paire: str(paire[0])))


def charger_regions(path=None, table=None, frontieres=None, carte=None, partielle=False) -> TableDesRegions:
    """Lit la table, la valide entièrement et rend ses régions triées.

    Chaque puissance de la table des puissances et chaque terre sans État de la table des
    frontières sont dans une région et une seule ; une cellule n'est nommée que par une région.
    `carte` (cell_id → enregistrement de la carte figée), quand elle est donnée, fait refuser une
    cellule nommée hors de la carte et une région qui n'y tient aucune cellule. `partielle` dit que la
    carte n'est qu'une part de la carte figée (un monde d'épreuve) : ces deux refus s'y lèvent."""
    chemin = pathlib.Path(path) if path is not None else _CHEMIN
    document = json.loads(chemin.read_text(encoding="utf-8"))
    table = charger_table() if table is None else table
    if frontieres is None:
        frontieres = charger_frontieres(table=table, carte=carte, partielle=True) if carte is not None \
            else charger_frontieres(table=table)
    if not isinstance(document, dict) or set(document) != _CLES:
        raise RegionInvalide(f"régions : clés {sorted(_CLES)} attendues")
    if document["date"] != _DATE:
        raise RegionInvalide(f"régions, champ date : {_DATE!r} attendu")
    _texte(document["fidelite"], "table", "fidelite")
    tolerance = _fraction(document["tolerance"], "table", "tolerance")
    if not 0 < tolerance < 1:
        raise _refus("table", "tolerance", f"tolérance hors de ]0, 1[ : {document['tolerance']}")
    sources = document["sources"]
    if not isinstance(sources, dict) or not sources:
        raise _refus("table", "sources", "sources absentes")
    for cle, texte in sources.items():
        _texte(texte, "table", f"sources.{cle}")
    brutes = document["regions"]
    if not isinstance(brutes, list) or not brutes:
        raise _refus("table", "regions", "régions absentes")
    puissances_connues = {p.id for p in table.puissances}
    terres_connues = set(frontieres.terres_sans_etat)
    regions, ids = [], set()
    for brute in brutes:
        region = _region(brute, sources, puissances_connues, terres_connues)
        if region.id in ids:
            raise _refus(region.id, "id", "région déclarée deux fois")
        ids.add(region.id)
        regions.append(region)
    regions.sort(key=lambda r: r.id)
    lue = TableDesRegions(_DATE, tolerance, dict(sources), tuple(regions),
                          _une_fois(regions, "puissances", puissances_connues),
                          _une_fois(regions, "terres", terres_connues),
                          _une_fois(regions, "cellules", ()))
    if carte is not None and not partielle:
        _juger_contre_la_carte(lue, frontieres, carte)
    return lue


def _regions_de_la_cellule(cell_id, table_regions, frontieres) -> list:
    """Les régions que touche une cellule, dans l'ordre déclaré : la région qui la nomme ; sinon
    celle de son pays, ou de la terre sans État de sa lacune ; sinon, pour une cellule partagée,
    celle de chacune de ses villes de partage. Vide pour une cellule que rien ne décide."""
    nommee = table_regions.region_de_cellule.get(cell_id)
    if nommee is not None:
        return [nommee]
    if cell_id in frontieres.cellules:
        return [table_regions.region_de_puissance[frontieres.cellules[cell_id]]]
    if cell_id in frontieres.terres_des_lacunes:
        return [table_regions.region_de_terre[frontieres.terres_des_lacunes[cell_id]]]
    return [table_regions.region_de_puissance[ville.pays] if ville.pays is not None
            else table_regions.region_de_terre[ville.terre]
            for ville in frontieres.partages.get(cell_id, ())]


def _juger_contre_la_carte(table_regions, frontieres, carte):
    """Refuse une cellule nommée hors de la carte et une région qui n'y tient aucune cellule."""
    for cell_id, region in table_regions.region_de_cellule.items():
        if cell_id not in carte:
            raise _refus(region, "cellules", f"cellule {cell_id} absente de la carte")
    tenues = set()
    for cell_id in sorted(carte):
        tenues.update(_regions_de_la_cellule(cell_id, table_regions, frontieres))
    for region in table_regions.regions:
        if region.id not in tenues:
            raise _refus(region.id, "puissances", "aucune cellule de la carte : la région n'a pas de pays sur la carte")


def parts_cultivees(carte, table_regions=None, frontieres=None, table=None) -> dict:
    """cell_id → part de terre mise en culture de chaque cellule de la carte.

    Une cellule prend la part de sa région (`_regions_de_la_cellule`) ; une cellule partagée, la
    moyenne des parts des régions de ses villes de partage, une par ville, dans l'ordre déclaré
    (niveau 2). Une cellule sans région est refusée : sa part ne se devine pas."""
    table = charger_table() if table is None else table
    frontieres = charger_frontieres(table=table, carte=carte, partielle=True) if frontieres is None else frontieres
    table_regions = (charger_regions(table=table, frontieres=frontieres, carte=carte, partielle=True)
                     if table_regions is None else table_regions)
    parts = table_regions.par_id()
    resultat = {}
    for cell_id in sorted(carte):
        regions = _regions_de_la_cellule(cell_id, table_regions, frontieres)
        if not regions:
            raise RegionInvalide(f"cellule {cell_id}, champ cell_id : cellule de la carte sans région")
        resultat[cell_id] = sum(parts[region].part_cultivee for region in regions) / len(regions)
    return resultat


def regions_des_lieux(monde, table_regions=None, table=None, frontieres=None) -> dict:
    """(cell_id, rang) → région de chaque lieu du monde : celle qui nomme sa cellule ; sinon celle
    de sa terre sans État ; sinon celle de son pays de 1400 (celui de sa ville de partage la plus
    proche dans une cellule partagée, celui de sa cellule ailleurs). Un lieu sans région est refusé."""
    table = charger_table() if table is None else table
    frontieres = frontieres_du_monde(monde, table) if frontieres is None else frontieres
    table_regions = (charger_regions(table=table, frontieres=frontieres, carte=monde.carte, partielle=True)
                     if table_regions is None else table_regions)
    vue = puissances_depuis_monde(monde, table=table, frontieres=frontieres)
    villes = villes_des_lieux(monde, table, frontieres)
    puissances = puissances_des_lieux(monde, table, frontieres, villes)
    terres = terres_des_lieux(monde, table, frontieres, villes)
    resultat = {}
    for cell_id in sorted(monde.cells):
        nommee = table_regions.region_de_cellule.get(cell_id)
        for lieu in monde.cells[cell_id].lieux:
            cle = (cell_id, lieu.rang)
            if nommee is not None:
                resultat[cle] = nommee
            elif cle in terres:
                resultat[cle] = table_regions.region_de_terre[terres[cle]]
            else:
                puissance = puissances.get(cle, vue.get(cell_id))
                if puissance is None:
                    raise RegionInvalide(f"lieu {cle}, champ pays : lieu sans pays ni terre sans État")
                resultat[cle] = table_regions.region_de_puissance[puissance]
    return resultat


def habitants_des_regions(monde, table_regions=None, table=None, frontieres=None) -> dict:
    """identifiant de région → la somme des habitants de ses lieux, pour chaque région de la table
    (0 pour une région dont le monde ne porte aucun lieu : une mesure)."""
    table = charger_table() if table is None else table
    frontieres = frontieres_du_monde(monde, table) if frontieres is None else frontieres
    table_regions = (charger_regions(table=table, frontieres=frontieres, carte=monde.carte, partielle=True)
                     if table_regions is None else table_regions)
    habitants = {region.id: 0 for region in table_regions.regions}
    des_lieux = regions_des_lieux(monde, table_regions, table, frontieres)
    for cell_id, cellule in sorted(monde.cells.items()):
        for lieu in cellule.lieux:
            habitants[des_lieux[cell_id, lieu.rang]] += lieu.population
    return habitants
