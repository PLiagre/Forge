"""Les frontières de 1400 : le pays de chaque cellule déclarée, et des lieux d'une cellule partagée.

Une vue pure, recalculée : la table `data/frontieres-1400.json` déclare le pays de chaque cellule
tenue d'une région, d'après une source par pays. Pour ces cellules, l'ancre la plus proche
(`sim/puissances.py`) ne décide plus rien. Une cellule que deux pays se partageaient nomme une
ville par pays ; chaque lieu de la cellule va au pays de la ville la plus proche de sa place
(`sim/places.py`), et la puissance de la cellule est celle de son bourg. Une ville de partage sans
pays (`pays: null`, avec sa raison) laisse ses lieux sans pays. Une cellule en lacune n'a pas de
pays. Rien ne se pose sur le monde, et le tick ne lit pas cette vue.
"""
import dataclasses
import json
import pathlib

from sim.lieux import lieux_de_cellule
from sim.model import _NoBadSpatialField
from sim.places import _villes_placees, places_de_cellule, sieges_des_maisons
from sim.projection import projeter_epsg3035
from sim.puissances import PuissanceInvalide, _nombre, _refuser_id, _texte, charger_table
from sim.villes import point_dans_geometrie

_CHEMIN = pathlib.Path(__file__).resolve().parents[1] / "data" / "frontieres-1400.json"
_DATE = "1400-01-01"
_CLES = frozenset({"date", "fidelite", "regions", "pays", "partages", "lacunes", "petits_pays", "temoins"})
# Un partage met au moins deux pays dans la cellule, la ville sans pays comptant pour un.
PAYS_MIN_D_UN_PARTAGE = 2


@dataclasses.dataclass(frozen=True)
class VilleDePartage(_NoBadSpatialField):
    nom: str
    lat: float
    lon: float
    pays: int | None
    source: str
    raison: str | None


@dataclasses.dataclass(frozen=True)
class Temoin(_NoBadSpatialField):
    nom: str
    lat: float
    lon: float
    pays: int
    source: str
    hors_carte: str | None


@dataclasses.dataclass(frozen=True)
class TableDesFrontieres(_NoBadSpatialField):
    date: str
    regions: dict     # nom de région → puissances de la région, triées
    cellules: dict    # cell_id → puissance déclarée
    sources: dict     # puissance → source publique de ses cellules
    partages: dict    # cell_id → villes du partage, dans l'ordre déclaré
    lacunes: dict     # cell_id → raison
    petits_pays: tuple  # (nom, raison) des pays plus petits que deux lieux
    temoins: tuple

    def declarees(self) -> frozenset:
        """Les cellules que la table décide : un pays, un partage ou une lacune."""
        return frozenset(self.cellules) | frozenset(self.partages) | frozenset(self.lacunes)


def _liste(document, cle):
    valeur = document.get(cle)
    if not isinstance(valeur, list):
        raise PuissanceInvalide(f"frontières, champ {cle} : liste attendue")
    return valeur


def _ligne(brute, sorte, identifiant):
    if not isinstance(brute, dict):
        raise PuissanceInvalide(f"{sorte} {identifiant!r} : ligne attendue")
    return brute


def _pays_connu(valeur, sorte, identifiant, connus):
    if isinstance(valeur, bool) or not isinstance(valeur, int) or valeur not in connus:
        raise PuissanceInvalide(f"{sorte} {identifiant!r}, champ pays : pays inconnu {valeur!r}")
    return valeur


def _cellule(valeur, sorte, vues):
    if isinstance(valeur, bool) or not isinstance(valeur, int):
        raise PuissanceInvalide(f"{sorte} {valeur!r}, champ cell_id : entier attendu")
    if valeur in vues:
        raise PuissanceInvalide(f"{sorte} {valeur}, champ cell_id : cellule déclarée deux fois")
    vues.add(valeur)
    return valeur


def charger_frontieres(path=None, table=None, carte=None, partielle=False) -> TableDesFrontieres:
    """Lit la table, la valide entièrement et rend ses lignes triées.

    `carte` (cell_id → enregistrement de la carte figée), quand elle est donnée, fait refuser une
    cellule inconnue et une ville de partage hors de sa cellule. `partielle` dit que la carte n'est
    qu'une part de la carte figée, celle d'un monde d'épreuve : une cellule déclarée qui n'y est pas
    est laissée de côté au lieu d'être refusée."""
    chemin = pathlib.Path(path) if path is not None else _CHEMIN
    document = json.loads(chemin.read_text(encoding="utf-8"))
    table = charger_table() if table is None else table
    connus = {p.id for p in table.puissances}
    if not isinstance(document, dict) or set(document) != _CLES:
        raise PuissanceInvalide(f"frontières : clés {sorted(_CLES)} attendues")
    if document["date"] != _DATE:
        raise PuissanceInvalide(f"frontières, champ date : {_DATE!r} attendu")
    _texte(document["fidelite"], "frontières", "table", "fidelite")

    regions = document["regions"]
    if not isinstance(regions, dict) or not regions:
        raise PuissanceInvalide("frontières, champ regions : régions absentes")
    lues = {}
    for nom, pays in sorted(regions.items()):
        _texte(nom, "région", nom, "nom")
        if not isinstance(pays, list) or not pays:
            raise PuissanceInvalide(f"région {nom!r}, champ pays : liste absente ou vide")
        lues[nom] = tuple(sorted({_pays_connu(p, "région", nom, connus) for p in pays}))

    vues, cellules, sources, pays_vus = set(), {}, {}, set()
    for brute in _liste(document, "pays"):
        brute = _ligne(brute, "pays", None)
        pays = _pays_connu(brute.get("pays"), "pays", brute.get("pays"), connus)
        if pays in pays_vus:
            raise PuissanceInvalide(f"pays {pays}, champ pays : pays déclaré deux fois")
        pays_vus.add(pays)
        sources[pays] = _texte(brute.get("source"), "pays", pays, "source")
        liste = brute.get("cellules")
        if not isinstance(liste, list) or not liste:
            raise PuissanceInvalide(f"pays {pays}, champ cellules : liste absente ou vide")
        for cid in liste:
            cellules[_cellule(cid, "cellule", vues)] = pays

    partages = {}
    for brute in _liste(document, "partages"):
        brute = _ligne(brute, "partage", None)
        cid = _cellule(brute.get("cell_id"), "partage", vues)
        villes = []
        for ville in brute.get("villes") or ():
            ville = _ligne(ville, "partage", cid)
            nom = _texte(ville.get("nom"), "partage", cid, "villes.nom")
            pays = ville.get("pays")
            if pays is not None:
                pays = _pays_connu(pays, "partage", cid, connus)
            raison = (_texte(ville.get("raison"), "partage", cid, f"villes.{nom}.raison")
                      if pays is None else None)
            lieu = VilleDePartage(nom, _nombre(ville.get("lat"), cid, "lat", "partage"),
                                  _nombre(ville.get("lon"), cid, "lon", "partage"), pays,
                                  _texte(ville.get("source"), "partage", cid, f"villes.{nom}.source"), raison)
            villes.append(lieu)
        if len({v.pays for v in villes}) < PAYS_MIN_D_UN_PARTAGE:
            raise PuissanceInvalide(f"partage {cid}, champ villes : au moins deux pays attendus")
        partages[cid] = tuple(villes)

    lacunes = {}
    for brute in _liste(document, "lacunes"):
        brute = _ligne(brute, "lacune", None)
        cid = _cellule(brute.get("cell_id"), "lacune", vues)
        lacunes[cid] = _texte(brute.get("raison"), "lacune", cid, "raison")

    petits, noms_vus = [], set()
    for brute in _liste(document, "petits_pays"):
        brute = _ligne(brute, "petit pays", None)
        nom = _texte(brute.get("nom"), "petit pays", brute.get("nom"), "nom")
        if nom in noms_vus:
            raise PuissanceInvalide(f"petit pays {nom!r}, champ nom : déclaré deux fois")
        noms_vus.add(nom)
        petits.append((nom, _texte(brute.get("raison"), "petit pays", nom, "raison")))

    temoins, noms_vus = [], set()
    for brute in _liste(document, "temoins"):
        brute = _ligne(brute, "témoin", None)
        nom = _texte(brute.get("nom"), "témoin", brute.get("nom"), "nom")
        if nom in noms_vus:
            raise PuissanceInvalide(f"témoin {nom!r}, champ nom : déclaré deux fois")
        noms_vus.add(nom)
        hors = (_texte(brute["hors_carte"], "témoin", nom, "hors_carte")
                if "hors_carte" in brute else None)
        temoins.append(Temoin(nom, _nombre(brute.get("lat"), nom, "lat", "témoin"),
                              _nombre(brute.get("lon"), nom, "lon", "témoin"),
                              _pays_connu(brute.get("pays"), "témoin", nom, connus),
                              _texte(brute.get("source"), "témoin", nom, "source"), hors))
    if not temoins:
        raise PuissanceInvalide("frontières, champ temoins : liste vide")
    if carte is not None:
        cellules, partages, lacunes = _juger_contre_la_carte(cellules, partages, lacunes, carte, partielle)
    return TableDesFrontieres(_DATE, lues, dict(sorted(cellules.items())), dict(sorted(sources.items())),
                              dict(sorted(partages.items())), dict(sorted(lacunes.items())),
                              tuple(sorted(petits)), tuple(sorted(temoins, key=lambda t: t.nom)))


def _juger_contre_la_carte(cellules, partages, lacunes, carte, partielle):
    """Refuse une cellule absente de la carte (ou l'écarte si la carte n'est qu'une part de la carte
    figée) et une ville de partage hors de sa cellule."""
    gardees = []
    for sorte, lignes in (("cellule", cellules), ("partage", partages), ("lacune", lacunes)):
        for cid in sorted(lignes):
            if cid not in carte and not partielle:
                raise PuissanceInvalide(f"{sorte} {cid}, champ cell_id : cellule inconnue")
        gardees.append({cid: ligne for cid, ligne in lignes.items() if cid in carte})
    for cid, villes in sorted(gardees[1].items()):
        for ville in villes:
            if not point_dans_geometrie(*projeter_epsg3035(ville.lat, ville.lon), carte[cid]["geometry"]):
                raise PuissanceInvalide(f"partage {cid}, champ villes : {ville.nom} hors de sa cellule")
    return tuple(gardees)


def frontieres_du_monde(monde, table=None) -> TableDesFrontieres:
    """La table lue pour un monde : jugée contre sa carte, qui peut n'être qu'une part de la carte figée."""
    return charger_frontieres(table=table, carte=monde.carte, partielle=True)


def maison_du_bourg(monde, cell_id):
    """La maison du registre qui prend le bourg de la cellule : la première seigneurie qui y siège,
    sinon la première grande maison ou institution, par identifiant ; sinon aucune.

    C'est l'ordre de `maitres.attribuer_maitres`, et le siège de cette maison place le bourg
    (`places.ancres_des_bourgs`) : la place du bourg se connaît avant ses maîtres."""
    registre = sorted(monde.maisons, key=lambda m: m.id)
    for sortes in (("seigneurie",), ("grande maison", "institution")):
        for maison in registre:
            if maison.sorte in sortes and maison.cell_id == cell_id:
                return maison.id
    return None


def pays_de_la_place(place, villes):
    """Le pays de la ville de partage la plus proche de la place, dans le plan EPSG:3035 ;
    à égalité exacte, la première déclarée. Une ville sans pays rend `None`."""
    meilleure = None
    for indice, ville in enumerate(villes):
        x, y = projeter_epsg3035(ville.lat, ville.lon)
        ecart_x, ecart_y = place.x_m - x, place.y_m - y
        cle = (ecart_x * ecart_x + ecart_y * ecart_y, indice)
        if meilleure is None or cle < meilleure[0]:
            meilleure = (cle, ville.pays)
    return meilleure[1]


def puissances_des_lieux(monde, table=None, frontieres=None) -> dict:
    """(cell_id, rang) → pays de chaque lieu d'une cellule partagée, ou `None` sans pays.

    Les places sont celles du chargement : le bourg au siège de `maison_du_bourg`, sinon à la plus
    grande ville placée, et les autres rangs par le tirage de `places_de_cellule`. Hors des cellules
    partagées, un lieu a le pays de sa cellule : il n'est pas dans ce dictionnaire."""
    table = charger_table() if table is None else table
    frontieres = frontieres_du_monde(monde, table) if frontieres is None else frontieres
    partagees = [cid for cid in frontieres.partages if cid in monde.cells]
    if not partagees:
        return {}
    sieges, villes = sieges_des_maisons(table), _villes_placees(monde)
    resultat = {}
    for cid in partagees:
        surfaces = [lieu.surface_km2 for lieu in lieux_de_cellule(cid, monde.cells[cid].area_km2)]
        places = places_de_cellule(cid, monde.carte.get(cid), surfaces,
                                   sieges.get(maison_du_bourg(monde, cid)), villes.get(cid))
        for rang, place in enumerate(places):
            resultat[cid, rang] = pays_de_la_place(place, frontieres.partages[cid])
    return resultat


def decisions_des_frontieres(monde, table=None, frontieres=None, lieux=None) -> dict:
    """cell_id → puissance (ou `None`) de chaque cellule du monde que la table décide : son pays
    déclaré, le pays de son bourg si elle est partagée, `None` si elle est en lacune."""
    table = charger_table() if table is None else table
    frontieres = frontieres_du_monde(monde, table) if frontieres is None else frontieres
    lieux = puissances_des_lieux(monde, table, frontieres) if lieux is None else lieux
    decisions = {cid: pays for cid, pays in frontieres.cellules.items() if cid in monde.cells}
    decisions.update({cid: None for cid in frontieres.lacunes if cid in monde.cells})
    decisions.update({cid: lieux.get((cid, 0)) for cid in frontieres.partages if cid in monde.cells})
    return dict(sorted(decisions.items()))
