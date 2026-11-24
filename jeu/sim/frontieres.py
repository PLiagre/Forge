"""Les frontières de 1400 : le pays de chaque cellule de la carte, et des lieux d'une cellule partagée.

Une vue pure, recalculée : la table `data/frontieres-1400.json` déclare, région par région, le pays
de chaque cellule de la carte, d'après une source par pays, son partage ou sa lacune ; une cellule
de la carte qu'elle ne décide pas est refusée. Une cellule que deux pays se partageaient nomme une
ville par pays ; chaque lieu de la cellule va au pays de la ville la plus proche de sa place
(`sim/places.py`), et la puissance de la cellule est celle de son bourg. Une ville de partage sans
pays (`pays: null`, avec sa raison) laisse ses lieux sans pays. Une cellule en lacune n'a pas de
pays. Chaque lacune et chaque ville sans pays nomment leur terre sans État, une région que la table
déclare avec son nom et sa raison : un lieu sans pays est un lieu de sa terre sans État. Rien ne se
pose sur le monde, et le tick ne lit pas cette vue.
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
_CLES = frozenset({"date", "fidelite", "regions", "pays", "partages", "lacunes", "terres_sans_etat",
                   "petits_pays", "temoins"})
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
    # La terre sans État d'une ville sans pays ; `None` pour une ville qui a son pays.
    terre: str | None = None


@dataclasses.dataclass(frozen=True)
class TerreSansEtat(_NoBadSpatialField):
    """Une région sans pays de la table, sous un seul nom : ses seigneurs restent maîtres de leurs lieux."""
    id: str
    nom: str
    raison: str


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
    terres_sans_etat: dict = dataclasses.field(default_factory=dict)  # id → TerreSansEtat, triées
    terres_des_lacunes: dict = dataclasses.field(default_factory=dict)  # cell_id → id de sa terre

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
    cellule inconnue, une ville de partage hors de sa cellule et une cellule de la carte que la table
    ne décide pas. `partielle` dit que la carte n'est qu'une part de la carte figée, celle d'un monde
    d'épreuve : une cellule déclarée qui n'y est pas est laissée de côté au lieu d'être refusée, et
    chaque cellule de cette part doit être décidée."""
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
            if pays is not None and "terre" in ville:
                raise PuissanceInvalide(f"partage {cid}, champ villes.{nom}.terre : terre sur une ville qui a son pays")
            terre = (_texte(ville.get("terre"), "partage", cid, f"villes.{nom}.terre")
                     if pays is None else None)
            lieu = VilleDePartage(nom, _nombre(ville.get("lat"), cid, "lat", "partage"),
                                  _nombre(ville.get("lon"), cid, "lon", "partage"), pays,
                                  _texte(ville.get("source"), "partage", cid, f"villes.{nom}.source"), raison, terre)
            villes.append(lieu)
        if len({v.pays for v in villes}) < PAYS_MIN_D_UN_PARTAGE:
            raise PuissanceInvalide(f"partage {cid}, champ villes : au moins deux pays attendus")
        partages[cid] = tuple(villes)

    lacunes, terres_des_lacunes = {}, {}
    for brute in _liste(document, "lacunes"):
        brute = _ligne(brute, "lacune", None)
        cid = _cellule(brute.get("cell_id"), "lacune", vues)
        lacunes[cid] = _texte(brute.get("raison"), "lacune", cid, "raison")
        terres_des_lacunes[cid] = _texte(brute.get("terre"), "lacune", cid, "terre")
    terres = _terres_sans_etat(document, terres_des_lacunes, partages)

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
    terres_des_lacunes = {cid: terre for cid, terre in terres_des_lacunes.items() if cid in lacunes}
    return TableDesFrontieres(_DATE, lues, dict(sorted(cellules.items())), dict(sorted(sources.items())),
                              dict(sorted(partages.items())), dict(sorted(lacunes.items())),
                              tuple(sorted(petits)), tuple(sorted(temoins, key=lambda t: t.nom)),
                              terres, dict(sorted(terres_des_lacunes.items())))


def _terres_sans_etat(document, terres_des_lacunes, partages) -> dict:
    """Lit les terres sans État ; refuse une terre en double, sans nom ni raison, une terre citée par
    une lacune ou une ville mais non déclarée, et une terre déclarée que rien ne cite."""
    terres = {}
    for brute in _liste(document, "terres_sans_etat"):
        brute = _ligne(brute, "terre sans État", None)
        identifiant = _texte(brute.get("id"), "terre sans État", brute.get("id"), "id")
        if identifiant in terres:
            raise PuissanceInvalide(f"terre sans État {identifiant!r}, champ id : déclarée deux fois")
        terres[identifiant] = TerreSansEtat(
            identifiant, _texte(brute.get("nom"), "terre sans État", identifiant, "nom"),
            _texte(brute.get("raison"), "terre sans État", identifiant, "raison"))
    citees = set()
    for cid, terre in sorted(terres_des_lacunes.items()):
        if terre not in terres:
            raise PuissanceInvalide(f"lacune {cid}, champ terre : terre sans État inconnue {terre!r}")
        citees.add(terre)
    for cid, villes in sorted(partages.items()):
        for ville in villes:
            if ville.terre is not None and ville.terre not in terres:
                raise PuissanceInvalide(f"partage {cid}, champ villes.{ville.nom}.terre : "
                                        f"terre sans État inconnue {ville.terre!r}")
            citees.add(ville.terre)
    for identifiant in sorted(terres):
        if identifiant not in citees:
            raise PuissanceInvalide(f"terre sans État {identifiant!r}, champ id : citée par aucune lacune ni ville")
    return dict(sorted(terres.items()))


def _juger_contre_la_carte(cellules, partages, lacunes, carte, partielle):
    """Refuse une cellule absente de la carte (ou l'écarte si la carte n'est qu'une part de la carte
    figée), une ville de partage hors de sa cellule et une cellule de la carte que la table ne décide pas."""
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
    decidees = set(cellules) | set(partages) | set(lacunes)
    for cid in sorted(carte):
        if cid not in decidees:
            raise PuissanceInvalide(f"cellule {cid}, champ cell_id : cellule de la carte sans pays, partage ni lacune")
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
    """Le pays de la ville de partage la plus proche de la place (`ville_de_la_place`). Une ville
    sans pays rend `None`."""
    return ville_de_la_place(place, villes).pays


def ville_de_la_place(place, villes):
    """La ville de partage la plus proche de la place, dans le plan EPSG:3035 ; à égalité exacte,
    la première déclarée."""
    meilleure = None
    for indice, ville in enumerate(villes):
        x, y = projeter_epsg3035(ville.lat, ville.lon)
        ecart_x, ecart_y = place.x_m - x, place.y_m - y
        cle = (ecart_x * ecart_x + ecart_y * ecart_y, indice)
        if meilleure is None or cle < meilleure[0]:
            meilleure = (cle, ville)
    return meilleure[1]


def villes_des_lieux(monde, table=None, frontieres=None) -> dict:
    """(cell_id, rang) → ville de partage la plus proche de chaque lieu d'une cellule partagée.

    Les places sont celles du chargement : le bourg au siège de `maison_du_bourg`, sinon à la plus
    grande ville placée, et les autres rangs par le tirage de `places_de_cellule`. Le pays et la terre
    sans État des lieux partagés se lisent sur ce seul passage."""
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
            resultat[cid, rang] = ville_de_la_place(place, frontieres.partages[cid])
    return resultat


def puissances_des_lieux(monde, table=None, frontieres=None, villes=None) -> dict:
    """(cell_id, rang) → pays de chaque lieu d'une cellule partagée, ou `None` sans pays : celui de sa
    ville de partage la plus proche (`villes_des_lieux`, qui se repasse quand elle est déjà lue).
    Hors des cellules partagées, un lieu a le pays de sa cellule : il n'est pas dans ce dictionnaire."""
    villes = villes_des_lieux(monde, table, frontieres) if villes is None else villes
    return {couple: ville.pays for couple, ville in villes.items()}


def terres_des_lieux(monde, table=None, frontieres=None, villes=None) -> dict:
    """(cell_id, rang) → terre sans État de chaque lieu du monde sans pays : tous les lieux d'une
    lacune vont à sa terre, ceux d'une cellule partagée à la terre de leur ville sans pays. Un lieu
    qui a un pays n'est pas dans ce dictionnaire."""
    table = charger_table() if table is None else table
    frontieres = frontieres_du_monde(monde, table) if frontieres is None else frontieres
    villes = villes_des_lieux(monde, table, frontieres) if villes is None else villes
    resultat = {}
    for cid, terre in frontieres.terres_des_lacunes.items():
        if cid in monde.cells:
            for lieu in lieux_de_cellule(cid, monde.cells[cid].area_km2):
                resultat[cid, lieu.rang] = terre
    resultat.update({couple: ville.terre for couple, ville in villes.items() if ville.pays is None})
    return dict(sorted(resultat.items()))


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
