"""La guerre : déclarer, lever, marcher, assiéger, renvoyer.

Chaque geste est une intention (`sim/intentions.py`) que le joueur et l'IA
déposent par le même chemin ; ce module dit pourquoi elle se refuse et ce
qu'elle écrit au monde quand elle s'applique. Les chiffres vivent dans
`data/guerre.toml` (niveau 2).

Les soldats sont des habitants : la levée les retire de leurs lieux et des
paysans de leur cellule, le renvoi les rend à leur lieu d'origine, comme
paysans. Les vivres sortent du grenier de la maison et y reviennent au renvoi :
aucun kilo ni aucune personne ne se crée. Une armée garde ses hommes par lieu
d'origine ; `cell_id` reste la seule clé spatiale.
"""
from dataclasses import dataclass, replace
import heapq
import math
from pathlib import Path
import tomllib

import sim.constants as _constantes
from sim import modificateurs as _modificateurs
from sim.model import (_NoBadSpatialField, ecrire_habitants_par_metier, ecrire_maitre, ecrire_stock_marchandise,
                       lire_habitants_par_metier, lire_stock_marchandise)

_CHEMIN = Path(__file__).parents[1] / "data" / "guerre.toml"
GRANDEUR_LEVEE = "levee"
_SECTIONS = {
    "levee": {"part_maximale", "batiment"},
    "marche": {"km_par_jour"},
    "vivres": {"ration_kg_par_homme_par_jour", "part_prise_par_jour"},
    "siege": {"jours_de_faim_avant_la_chute"},
    "ia": {"jours_de_marche_max", "jours_de_siege_voulus", "hommes_minimum"},
}
_CHAMPS_D_UNE_LEVEE = ("cell", "rang", "hommes")
# Le séparateur des milliers des textes du monde, celui de l'écran (`TexteDuMonde` côté Unity).
_ESPACE_DES_MILLIERS = " "
# Les décimales au plus d'un nombre écrit dans un refus, comme les masses de l'écran.
DECIMALES_DES_TEXTES = 2
_POUR_CENT = 100


def ecrire_nombre(valeur, decimales=DECIMALES_DES_TEXTES) -> str:
    """Un nombre comme l'écran l'écrit : milliers séparés, virgule décimale, au plus `decimales` décimales.

    Les refus des gestes de guerre se lisent tels quels par le joueur : aucun identifiant, et chaque
    nombre suivi de son unité.
    """
    texte = f"{round(valeur, decimales):,.{decimales}f}"
    entier, _, fraction = texte.partition(".")
    fraction = fraction.rstrip("0")
    entier = entier.replace(",", _ESPACE_DES_MILLIERS)
    return entier + ("," + fraction if fraction else "")


class GuerreInvalide(ValueError):
    """Une donnée de la guerre que le monde refuse, avec sa raison."""


@dataclass(frozen=True)
class Regles:
    part_maximale_levee: float
    batiment_de_levee: str
    vitesse_marche_km_par_jour: float
    ration_kg_par_homme_par_jour: float
    part_prise_par_jour: float
    jours_de_faim_avant_la_chute: int
    ia_jours_de_marche_max: int
    ia_jours_de_siege_voulus: int
    ia_hommes_minimum: int


@dataclass(frozen=True)
class Guerre(_NoBadSpatialField):
    """Une guerre déclarée : la maison qui l'a déclarée, celle qu'elle vise, son tick."""

    identifiant: int
    agresseur: str
    defenseur: str
    debut: int

    def en_document(self) -> dict:
        return {"identifiant": self.identifiant, "agresseur": self.agresseur,
                "defenseur": self.defenseur, "debut": self.debut}


@dataclass(frozen=True)
class Armee(_NoBadSpatialField):
    """Une armée en campagne.

    `cell_id`, `rang` : le lieu où elle se trouve. `effectifs` : ses hommes par
    lieu d'origine, `((cell_id, rang, hommes), …)` triés, chaque compte positif.
    `destination` : le lieu où elle marche, ou None ; `route` : les cellules qui
    restent à traverser, la dernière étant celle de la destination ;
    `avance_km` : le chemin déjà fait vers la prochaine. `siege` : la cellule
    dont elle assiège le bourg, ou None. `dette_kg` et `reste_mortalite` : sa
    faim, comme celle d'un lieu.
    """

    identifiant: int
    maison: str
    cell_id: int
    rang: int
    effectifs: tuple
    vivres_kg: float
    debut: int
    destination: tuple | None = None
    route: tuple = ()
    avance_km: float = 0.0
    siege: int | None = None
    dette_kg: float = 0.0
    reste_mortalite: float = 0.0

    @property
    def hommes(self) -> int:
        return sum(hommes for _cid, _rang, hommes in self.effectifs)

    def en_document(self) -> dict:
        return {"identifiant": self.identifiant, "maison": self.maison, "cell_id": self.cell_id,
                "rang": self.rang, "effectifs": [list(e) for e in self.effectifs], "hommes": self.hommes,
                "vivres_kg": self.vivres_kg, "debut": self.debut,
                "destination": None if self.destination is None else list(self.destination),
                "route": list(self.route), "avance_km": self.avance_km, "siege": self.siege,
                "dette_kg": self.dette_kg, "reste_mortalite": self.reste_mortalite}


def _nombre(valeur, ou, minimum, maximum=None, strict=True):
    if isinstance(valeur, bool) or not isinstance(valeur, (int, float)) or not math.isfinite(valeur):
        raise GuerreInvalide(f"{ou} : nombre fini attendu")
    if valeur < minimum or (strict and valeur == minimum) or (maximum is not None and valeur > maximum):
        borne = "]" if strict else "["
        raise GuerreInvalide(f"{ou} : nombre dans {borne}{minimum}, {maximum if maximum is not None else '∞'}] attendu")
    return float(valeur)


def lire_regles(document, types=None) -> Regles:
    """Valide un document déjà lu ; le bâtiment de la levée existe dans les bâtiments de province."""
    if not isinstance(document, dict):
        raise GuerreInvalide("document de la guerre : table attendue")
    for section in sorted(set(document) - set(_SECTIONS)):
        raise GuerreInvalide(f"section inconnue : {section}")
    for section, champs in _SECTIONS.items():
        brute = document.get(section)
        if not isinstance(brute, dict):
            raise GuerreInvalide(f"{section} : table attendue")
        if set(brute) != champs:
            raise GuerreInvalide(f"{section} : champs {sorted(champs)} attendus, reçu {sorted(brute)}")
    if types is None:
        from sim.batiments import charger_types
        types = charger_types()
    batiment = document["levee"]["batiment"]
    if batiment not in types:
        raise GuerreInvalide(f"levee.batiment : {batiment!r} absent des bâtiments de province")
    entiers = {}
    for section, champ in (("siege", "jours_de_faim_avant_la_chute"), ("ia", "jours_de_marche_max"),
                           ("ia", "jours_de_siege_voulus"), ("ia", "hommes_minimum")):
        valeur = document[section][champ]
        if isinstance(valeur, bool) or not isinstance(valeur, int) or valeur < 1:
            raise GuerreInvalide(f"{section}.{champ} : entier au moins égal à 1 attendu")
        entiers[section, champ] = valeur
    return Regles(
        _nombre(document["levee"]["part_maximale"], "levee.part_maximale", 0, 1),
        batiment,
        _nombre(document["marche"]["km_par_jour"], "marche.km_par_jour", 0),
        _nombre(document["vivres"]["ration_kg_par_homme_par_jour"], "vivres.ration_kg_par_homme_par_jour", 0),
        _nombre(document["vivres"]["part_prise_par_jour"], "vivres.part_prise_par_jour", 0, 1, strict=False),
        entiers["siege", "jours_de_faim_avant_la_chute"], entiers["ia", "jours_de_marche_max"],
        entiers["ia", "jours_de_siege_voulus"], entiers["ia", "hommes_minimum"])


def charger_regles(chemin=None) -> Regles:
    with open(chemin if chemin is not None else _CHEMIN, "rb") as fichier:
        return lire_regles(tomllib.load(fichier))


# --- Lire le monde --------------------------------------------------------------

def _maison(monde, identifiant):
    if not isinstance(identifiant, str):
        return None
    return next((m for m in monde.maisons if m.id == identifiant), None)


def _bourg(cellule):
    return next((lieu for lieu in cellule.lieux if lieu.rang == 0), None)


def _paysans(cellule) -> int:
    metiers = lire_habitants_par_metier(cellule)
    return cellule.population if metiers == -1 else metiers.get(_constantes.METIER_PAYSANS, 0)


def en_guerre(monde, a, b, declarees=()) -> bool:
    """Vrai si une guerre oppose les deux maisons, déclarée ou déposée (`declarees` : couples en attente)."""
    paires = [(g.agresseur, g.defenseur) for g in monde.guerres] + list(declarees)
    return any({x, y} == {a, b} for x, y in paires)


def hommes_sous_les_armes(monde, cell_id, rang, en_attente=()) -> int:
    """Les hommes de ce lieu dans une armée, de toute maison, plus ceux des levées déposées."""
    total = sum(h for armee in monde.armees for c, r, h in armee.effectifs if (c, r) == (cell_id, rang))
    return total + sum(h for c, r, h in en_attente if (c, r) == (cell_id, rang))


def levee_maximale(monde, cell_id, rang, regles, en_attente=()) -> int:
    """Les hommes que ce lieu peut encore donner : la part de ses habitants, levés compris, moins les levés.

    Les hommes des levées déposées (`en_attente`) sont encore comptés parmi les habitants du lieu.
    """
    lieu = monde.cells[cell_id].lieux[rang]
    leves = hommes_sous_les_armes(monde, cell_id, rang)
    promis = hommes_sous_les_armes(monde, cell_id, rang, en_attente) - leves
    part = regles.part_maximale_levee * _modificateurs.facteur(monde, GRANDEUR_LEVEE, cell_id, rang)
    return max(0, math.floor(part * (lieu.population + leves)) - leves - promis)


def raison_levee_fermee(monde, maison, regles) -> str | None:
    """Pourquoi la levée est fermée à cette maison, ou None : une caserne achevée dans sa capitale tenue."""
    fiche = _maison(monde, maison)
    if fiche is None:
        return f"maison inconnue ou mal formée : {maison!r}"
    if fiche.cell_id is None or fiche.cell_id not in monde.cells:
        return "la levée est fermée : votre capitale est hors de la carte"
    bourg = _bourg(monde.cells[fiche.cell_id])
    if bourg is None or bourg.maitre != maison:
        return "la levée est fermée : le bourg de votre capitale n'est plus à vous"
    if not any(b.cell_id == fiche.cell_id and b.nature == regles.batiment_de_levee and not b.en_chantier
               for b in monde.batiments_de_province):
        return f"la levée est fermée : aucune {regles.batiment_de_levee} achevée dans votre capitale"
    return None


def chemin(monde, depart, arrivee) -> tuple | None:
    """Les cellules à traverser de `depart` à `arrivee`, arrivée comprise, par le plus court chemin terrestre.

    () dans la même cellule, None sans chemin. Les égalités se départagent par cell_id : même monde, même route.
    """
    if depart == arrivee:
        return ()
    from sim.convois import _longueur_arete, _voisins_terrestres
    voisins = _voisins_terrestres(monde)
    dist, precedent = {depart: 0.0}, {}
    file = [(0.0, depart)]
    while file:
        cout, noeud = heapq.heappop(file)
        if noeud == arrivee:
            break
        if cout > dist[noeud]:
            continue
        for voisin in voisins.get(noeud, ()):
            nouveau = cout + _longueur_arete(monde, noeud, voisin)
            if nouveau < dist.get(voisin, math.inf):
                dist[voisin], precedent[voisin] = nouveau, noeud
                heapq.heappush(file, (nouveau, voisin))
    if arrivee not in precedent:
        return None
    etapes, noeud = [], arrivee
    while noeud != depart:
        etapes.append(noeud)
        noeud = precedent[noeud]
    return tuple(reversed(etapes))


def _armee(monde, maison, identifiant):
    """L'armée de cette maison, ou la raison du refus."""
    if isinstance(identifiant, bool) or not isinstance(identifiant, int):
        return None, f"armée invalide : entier attendu, reçu {identifiant!r}"
    armee = next((a for a in monde.armees if a.identifiant == identifiant), None)
    if armee is None:
        return None, "cette armée n'existe plus"
    if armee.maison != maison:
        return None, "cette armée n'est pas à vous"
    return armee, None


# --- Les refus --------------------------------------------------------------------
#
# Un refus d'un geste valide dans sa forme se lit tel quel par le joueur : il ne nomme ni lieu ni
# maison par son identifiant, et chaque nombre porte son unité. Un refus de forme (champ, type)
# garde ce qu'il a reçu : seul un client mal écrit le voit.

def verifier_declaration(monde, maison, cible, declarees=()) -> str | None:
    """La raison du refus d'une déclaration, ou None. `declarees` : couples déjà déposés."""
    if _maison(monde, maison) is None:
        return f"maison inconnue ou mal formée : {maison!r}"
    if _maison(monde, cible) is None:
        return f"cible inconnue : {cible!r}"
    if cible == maison:
        return "on ne se déclare pas la guerre à soi-même"
    if en_guerre(monde, maison, cible, declarees):
        return "vous êtes déjà en guerre avec cette maison"
    if not any(lieu.maitre == cible for cid in sorted(monde.cells) for lieu in monde.cells[cid].lieux):
        return "cette maison ne tient aucun lieu : rien à prendre"
    return None


def lire_lieux_de_levee(brute):
    """`[[cell, rang, hommes], …]` → tuple trié, ou la raison du refus de sa forme."""
    if not isinstance(brute, list) or not brute:
        return None, "lieux : liste non vide de [cell, rang, hommes] attendue"
    lieux = {}
    for entree in brute:
        if (not isinstance(entree, list) or len(entree) != len(_CHAMPS_D_UNE_LEVEE)
                or any(isinstance(v, bool) or not isinstance(v, int) for v in entree)):
            return None, f"lieux : [cell, rang, hommes] entiers attendus, reçu {entree!r}"
        cid, rang, hommes = entree
        if hommes < 1:
            return None, f"lieux : au moins un homme par lieu, reçu {hommes} pour ({cid}, {rang})"
        if (cid, rang) in lieux:
            return None, f"lieux : ({cid}, {rang}) nommé deux fois"
        lieux[cid, rang] = hommes
    return tuple((cid, rang, hommes) for (cid, rang), hommes in sorted(lieux.items())), None


def verifier_levee(monde, maison, lieux, vivres_kg, regles, grain_libre, en_attente=()) -> str | None:
    """La raison du refus d'une levée, ou None.

    `lieux` : la forme lue par `lire_lieux_de_levee`. `grain_libre` : le grain du grenier que les
    intentions déjà déposées n'ont pas engagé. `en_attente` : les `(cell_id, rang, hommes)` des
    levées déjà déposées pour le tick.
    """
    fermee = raison_levee_fermee(monde, maison, regles)
    if fermee is not None:
        return fermee
    if (isinstance(vivres_kg, bool) or not isinstance(vivres_kg, (int, float))
            or not math.isfinite(vivres_kg) or vivres_kg < 0):
        return f"vivres_kg invalide : nombre fini positif ou nul attendu, reçu {vivres_kg!r}"
    if vivres_kg > grain_libre:
        return (f"grenier insuffisant : {ecrire_nombre(vivres_kg)} kg de vivres demandés, "
                f"{ecrire_nombre(grain_libre)} kg disponibles")
    par_cellule = {}
    for cid, rang, hommes in lieux:
        cellule = monde.cells.get(cid)
        if cellule is None or not 0 <= rang < len(cellule.lieux):
            return "ce lieu n'existe pas sur la carte"
        lieu = cellule.lieux[rang]
        if lieu.maitre != maison:
            return "ce lieu n'est pas à vous"
        maximum = levee_maximale(monde, cid, rang, regles, en_attente)
        if hommes > maximum:
            return (f"trop d'hommes : ce lieu peut en donner {ecrire_nombre(maximum)} hommes, "
                    f"{ecrire_nombre(hommes)} hommes demandés (au plus "
                    f"{ecrire_nombre(regles.part_maximale_levee * _POUR_CENT)} % de ses habitants sous les armes)")
        par_cellule[cid] = par_cellule.get(cid, 0) + hommes
    for cid, hommes in sorted(par_cellule.items()):
        deja = sum(h for c, _r, h in en_attente if c == cid)
        paysans = _paysans(monde.cells[cid]) - deja
        if hommes > paysans:
            return (f"pas assez de paysans : {ecrire_nombre(hommes)} hommes demandés sur cette terre, "
                    f"{ecrire_nombre(paysans)} paysans")
    return None


def verifier_marche(monde, maison, identifiant, cell_id, rang) -> str | None:
    armee, refus = _armee(monde, maison, identifiant)
    if refus is not None:
        return refus
    if (isinstance(cell_id, bool) or not isinstance(cell_id, int) or isinstance(rang, bool)
            or not isinstance(rang, int)):
        return f"lieu invalide : entiers attendus, reçu ({cell_id!r}, {rang!r})"
    cellule = monde.cells.get(cell_id)
    if cellule is None or not 0 <= rang < len(cellule.lieux):
        return "ce lieu n'existe pas sur la carte"
    if (armee.cell_id, armee.rang) == (cell_id, rang):
        return "l'armée est déjà à ce lieu"
    try:
        route = chemin(monde, armee.cell_id, cell_id)
    except ValueError as exc:
        return f"aucun chemin terrestre : {exc}"
    if route is None:
        return "aucun chemin terrestre jusqu'à ce lieu"
    return None


def verifier_siege(monde, maison, identifiant, declarees=()) -> str | None:
    armee, refus = _armee(monde, maison, identifiant)
    if refus is not None:
        return refus
    if armee.destination is not None:
        return "l'armée marche encore : elle assiège une fois arrivée"
    if armee.rang != 0:
        return "ce lieu n'est pas une place : l'armée n'est pas dans un bourg"
    if armee.siege == armee.cell_id:
        return "l'armée assiège déjà cette place"
    maitre = getattr(_bourg(monde.cells[armee.cell_id]), "maitre", None)
    if maitre == maison:
        return "cette place est à vous"
    if not en_guerre(monde, maison, maitre, declarees):
        return "vous n'êtes pas en guerre avec le maître de cette place"
    return None


def verifier_renvoi(monde, maison, identifiant) -> str | None:
    return _armee(monde, maison, identifiant)[1]


# --- Les gestes appliqués -----------------------------------------------------------

def declarer(monde, maison, cible) -> Guerre:
    guerre = Guerre(max((g.identifiant for g in monde.guerres), default=-1) + 1, maison, cible,
                    monde.ticks_ecoules)
    monde.guerres = [*monde.guerres, guerre]
    return guerre


def _changer_paysans(cellule, ecart):
    """Ajoute (ou retire) des paysans ; sans métiers calculés, seule la population bouge."""
    metiers = lire_habitants_par_metier(cellule)
    if metiers == -1:
        cellule.population = cellule.population + ecart
        return
    paysans = metiers.get(_constantes.METIER_PAYSANS, 0) + ecart
    if paysans:
        metiers[_constantes.METIER_PAYSANS] = paysans
    else:
        metiers.pop(_constantes.METIER_PAYSANS, None)
    ecrire_habitants_par_metier(cellule, metiers)


def lever(monde, maison, lieux, vivres_kg) -> Armee | None:
    """Retire les hommes de leurs lieux et des paysans, les vivres du grenier ; l'armée naît au bourg de la capitale.

    Le dépôt a vérifié les comptes ; chaque lieu ne donne jamais plus que ses habitants et sa cellule
    que ses paysans, et l'armée ne compte que ce qui a été pris.
    """
    fiche = _maison(monde, maison)
    pris = []
    for cid, rang, hommes in lieux:
        cellule = monde.cells[cid]
        lieu = cellule.lieux[rang]
        n = min(hommes, lieu.population, _paysans(cellule))
        if n <= 0:
            continue
        lieu.population -= n
        _changer_paysans(cellule, -n)
        pris.append((cid, rang, n))
    if not pris:
        return None
    nourriture = _constantes.MARCHANDISE_NOURRITURE
    panier = monde.greniers[maison]
    vivres = min(vivres_kg, max(0.0, panier.get(nourriture, 0.0)))
    if vivres > 0:
        panier[nourriture] = panier.get(nourriture, 0.0) - vivres
    armee = Armee(monde.armees_levees, maison, fiche.cell_id, 0, tuple(pris), float(vivres), monde.ticks_ecoules)
    monde.armees_levees += 1
    monde.armees = [*monde.armees, armee]
    return armee


def _remplacer(monde, armee):
    monde.armees = [armee if a.identifiant == armee.identifiant else a for a in monde.armees]


def marcher(monde, identifiant, cell_id, rang):
    armee = next(a for a in monde.armees if a.identifiant == identifiant)
    _remplacer(monde, replace(armee, destination=(cell_id, rang), route=chemin(monde, armee.cell_id, cell_id),
                              avance_km=0.0, siege=None))


def assieger(monde, identifiant):
    armee = next(a for a in monde.armees if a.identifiant == identifiant)
    _remplacer(monde, replace(armee, siege=armee.cell_id))


def renvoyer(monde, identifiant):
    """Les vivants rentrent dans leurs lieux d'origine, comme paysans ; les vivres restants au grenier."""
    _dissoudre(monde, next(a for a in monde.armees if a.identifiant == identifiant))


def _dissoudre(monde, armee):
    """Rend les hommes de l'armée à leurs lieux et ses vivres au grenier, puis la retire."""
    identifiant = armee.identifiant
    for cid, rang, hommes in armee.effectifs:
        cellule = monde.cells[cid]
        cellule.lieux[rang].population += hommes
        _changer_paysans(cellule, hommes)
    if armee.vivres_kg > 0:
        nourriture = _constantes.MARCHANDISE_NOURRITURE
        panier = monde.greniers[armee.maison]
        panier[nourriture] = panier.get(nourriture, 0.0) + armee.vivres_kg
    monde.armees = [a for a in monde.armees if a.identifiant != identifiant]


# --- Le maillon de la guerre ----------------------------------------------------------

def places_assiegees(monde) -> set:
    """Les cellules dont une armée assiège le bourg : aucun grain n'y entre."""
    return {a.siege for a in getattr(monde, "armees", ()) if a.siege is not None}


def _places_de_la_cellule(monde, cell_id):
    """Les places des lieux, ancrées au chargement : une conquête ne déplace pas un bourg."""
    from sim.routes_interieures import _places_de
    places = _places_de(monde, cell_id)
    if places is None:
        raise GuerreInvalide(f"cellule {cell_id} : ancres des bourgs absentes, aucune distance n'est devinée")
    return places


def _troncon_km(monde, armee):
    """La longueur du prochain tronçon : vers le bourg, la cellule suivante, ou le lieu visé dans la cellule."""
    from sim.convois import _longueur_arete
    from sim.places import distance_km
    if armee.route:
        if armee.rang != 0:
            places = _places_de_la_cellule(monde, armee.cell_id)
            return distance_km(places[armee.rang], places[0]), (armee.cell_id, 0, armee.route)
        suivante = armee.route[0]
        return _longueur_arete(monde, armee.cell_id, suivante), (suivante, 0, armee.route[1:])
    places = _places_de_la_cellule(monde, armee.cell_id)
    rang = armee.destination[1]
    return distance_km(places[armee.rang], places[rang]), (armee.cell_id, rang, ())


def _marcher_un_jour(monde, armee, regles):
    """Avance de `vitesse_marche_km_par_jour`, tronçon par tronçon ; arrivée, la destination s'efface."""
    budget = regles.vitesse_marche_km_par_jour
    while armee.destination is not None and budget > 0:
        if (armee.cell_id, armee.rang) == tuple(armee.destination) and not armee.route:
            break
        longueur, (cid, rang, route) = _troncon_km(monde, armee)
        reste = longueur - armee.avance_km
        if budget < reste:
            armee = replace(armee, avance_km=armee.avance_km + budget)
            budget = 0
        else:
            budget -= reste
            armee = replace(armee, cell_id=cid, rang=rang, route=route, avance_km=0.0)
    if armee.destination is not None and (armee.cell_id, armee.rang) == tuple(armee.destination) and not armee.route:
        armee = replace(armee, destination=None, avance_km=0.0)
    return armee


def _lieu_de_fourrage(monde, armee):
    """Le lieu où l'armée prend ce qui manque : le sien, ou, devant une place, le plus garni des autres lieux."""
    cellule = monde.cells[armee.cell_id]
    if armee.siege != armee.cell_id:
        return cellule.lieux[armee.rang]
    autres = [l for l in cellule.lieux if l.rang != 0]
    if not autres:
        return None
    nourriture = _constantes.MARCHANDISE_NOURRITURE
    return max(autres, key=lambda l: (lire_stock_marchandise(l, nourriture), -l.rang))


def _manger(monde, armee, regles):
    """Ses vivres, puis au plus `part_prise_par_jour` du stock de son lieu ; le reste devient une dette qui tue."""
    from sim.lieux import partager
    nourriture = _constantes.MARCHANDISE_NOURRITURE
    besoin = armee.hommes * regles.ration_kg_par_homme_par_jour * _constantes.TICK_DURATION_DAYS
    mange = min(besoin, armee.vivres_kg)
    vivres, manque = armee.vivres_kg - mange, besoin - mange
    if manque > 0:
        lieu = _lieu_de_fourrage(monde, armee)
        if lieu is not None:
            stock = max(0.0, lire_stock_marchandise(lieu, nourriture))
            pris = min(manque, stock * regles.part_prise_par_jour)
            if pris > 0:
                cellule = monde.cells[armee.cell_id]
                ecrire_stock_marchandise(lieu, nourriture, stock - pris)
                ecrire_stock_marchandise(cellule, nourriture, lire_stock_marchandise(cellule, nourriture) - pris)
                mange += pris
                manque -= pris
    dette = armee.dette_kg + manque
    if manque <= 0 and dette > 0:
        # Rassasiée, l'armée rembourse sa dette sur ses vivres, jamais plus qu'ils ne portent.
        rembourse = min(dette, vivres)
        vivres -= rembourse
        mange += rembourse
        dette -= rembourse
    monde.mange_par_les_armees_kg += mange
    armee = replace(armee, vivres_kg=vivres, dette_kg=dette)
    if dette <= 0 or not armee.hommes:
        return armee
    taux = min(dette / armee.hommes * _constantes.HUNGER_DEATH_SCALE, _constantes.MAX_DEATH_RATE_PER_TICK)
    brut = armee.hommes * taux + armee.reste_mortalite
    morts = min(int(brut), armee.hommes)
    armee = replace(armee, reste_mortalite=brut - int(brut))
    if not morts:
        return armee
    parts = partager(morts, [h for _c, _r, h in armee.effectifs])
    effectifs = tuple((c, r, h - int(p)) for (c, r, h), p in zip(armee.effectifs, parts) if h - int(p) > 0)
    monde.morts_des_armees += morts
    return replace(armee, effectifs=effectifs)


def _siege_tient(monde, armee):
    """Le siège tient tant que l'armée est au bourg assiégé, en guerre avec son maître."""
    if armee.siege is None:
        return False
    maitre = getattr(_bourg(monde.cells[armee.siege]), "maitre", None)
    return ((armee.cell_id, armee.rang) == (armee.siege, 0) and maitre != armee.maison
            and en_guerre(monde, armee.maison, maitre))


def tomber(monde, armee):
    """La place tombe : les lieux de la cellule que tenait le maître du bourg passent à l'assiégeant."""
    from sim.convois import changer_de_maitre
    cid = armee.siege
    cellule = monde.cells[cid]
    defenseur = _bourg(cellule).maitre
    rangs = [lieu.rang for lieu in sorted(cellule.lieux, key=lambda l: l.rang) if lieu.maitre == defenseur]
    for rang in rangs:
        ecrire_maitre(cellule.lieux[rang], armee.maison)
    changer_de_maitre(monde, cid, rangs, armee.maison)
    # Les bâtiments et chantiers de province de l'ancien maître dans la cellule passent au nouveau.
    monde.batiments_de_province = [replace(b, maison=armee.maison) if b.cell_id == cid and b.maison == defenseur
                                   else b for b in monde.batiments_de_province]
    monde.prises = [*monde.prises, {"tick": monde.ticks_ecoules, "cell_id": cid, "de": defenseur,
                                    "a": armee.maison, "armee": armee.identifiant, "rangs": rangs}]
    monde.armees = [replace(a, siege=None) if a.siege == cid else a for a in monde.armees]


def avancer(monde, regles=None) -> None:
    """Un jour de guerre, armée par armée, par identifiant : la chute, la marche, la ration et les morts.

    Une place assiégée qui a faim depuis `jours_de_faim_avant_la_chute` jours, ou dont le bourg
    est vide, tombe. Sans armée, rien n'est lu ni écrit.
    """
    if not getattr(monde, "armees", None):
        return
    regles = charger_regles() if regles is None else regles
    for identifiant in sorted(a.identifiant for a in monde.armees):
        armee = next((a for a in monde.armees if a.identifiant == identifiant), None)
        if armee is None:
            continue
        if armee.siege is not None and not _siege_tient(monde, armee):
            armee = replace(armee, siege=None)
            _remplacer(monde, armee)
        if armee.siege is not None:
            bourg = _bourg(monde.cells[armee.siege])
            if bourg.population == 0 or bourg.duree_faim_ticks >= regles.jours_de_faim_avant_la_chute:
                tomber(monde, armee)
                armee = next(a for a in monde.armees if a.identifiant == identifiant)
        armee = _manger(monde, _marcher_un_jour(monde, armee, regles), regles)
        _remplacer(monde, armee)
        if not armee.hommes:
            _dissoudre(monde, armee)


def prendre_la_recolte(monde, recoltes) -> None:
    """Devant une place, la récolte du jour de son bourg va aux vivres de l'assiégeant, avant le prélèvement."""
    if not getattr(monde, "armees", None):
        return
    nourriture = _constantes.MARCHANDISE_NOURRITURE
    servies = set()
    for armee in sorted(monde.armees, key=lambda a: a.identifiant):
        cid = armee.siege
        if cid is None or cid in servies or not recoltes.get(cid):
            continue
        servies.add(cid)
        kg = recoltes[cid][0]
        if kg <= 0:
            continue
        cellule = monde.cells[cid]
        bourg = _bourg(cellule)
        ecrire_stock_marchandise(bourg, nourriture, lire_stock_marchandise(bourg, nourriture) - kg)
        ecrire_stock_marchandise(cellule, nourriture, lire_stock_marchandise(cellule, nourriture) - kg)
        recoltes[cid] = [0.0, *recoltes[cid][1:]]
        _remplacer(monde, replace(armee, vivres_kg=armee.vivres_kg + kg))


def retenir_les_secours(monde, charges) -> dict:
    """Les secours du jour, moins ceux qui arrivent au bourg d'une place assiégée : ils attendent le lendemain."""
    fermees = places_assiegees(monde)
    if not fermees:
        return charges
    livres = {}
    for (cid, rang), kg in charges.items():
        if rang == 0 and cid in fermees:
            demain = monde.secours.setdefault(monde.ticks_ecoules + 1, {})
            demain[cid, rang] = demain.get((cid, rang), 0.0) + kg
        else:
            livres[cid, rang] = kg
    return livres


def document_de_la_guerre(monde) -> dict:
    """Les guerres, les armées et les prises du monde, pour le service et la photographie, sans arrondi.

    Chaque armée porte son lieu (`cell_id`, `rang`), ses effectifs par lieu d'origine
    `[[cell_id, rang, hommes]]`, son effectif total, ses vivres, sa route en cellules, sa
    destination et la cellule dont elle assiège le bourg, ou None.
    """
    return {
        "tick": monde.ticks_ecoules,
        "date": _constantes.date_de_tick(monde.ticks_ecoules),
        "guerres": [g.en_document() for g in getattr(monde, "guerres", ())],
        "armees": [a.en_document() for a in sorted(getattr(monde, "armees", ()), key=lambda a: a.identifiant)],
        "prises": [dict(p, rangs=list(p["rangs"])) for p in getattr(monde, "prises", ())],
        "morts_des_armees": getattr(monde, "morts_des_armees", 0),
    }


def _etapes(armee, places) -> list:
    """Les places que l'armée doit encore atteindre, dans l'ordre des tronçons de `_troncon_km` : avec une route,
    son bourg si elle part d'un autre lieu, le bourg de chaque cellule de la route, puis le lieu visé s'il n'est pas
    un bourg ; sans route, le lieu visé dans sa cellule. La première est la fin du tronçon en cours."""
    if armee.destination is None:
        return []
    cid, rang = armee.destination
    if not armee.route:
        return [places[cid][rang]] if (armee.cell_id, armee.rang) != (cid, rang) else []
    etapes = [places[armee.cell_id][0]] if armee.rang != 0 else []
    etapes.extend(places[c][0] for c in armee.route)
    if rang != 0:
        etapes.append(places[cid][rang])
    return etapes


def document_servi_de_la_guerre(monde, places) -> dict:
    """`document_de_la_guerre`, où chaque armée porte en plus sa place (`point`) et celles de sa route (`etapes`).

    `point` est la place de son lieu, avancée sur le tronçon en cours de la part qu'elle en a faite
    (`avance_km` sur la longueur de `_troncon_km`) : la carte la dessine où elle marche, sans rien recalculer.
    Le service seul le sert ; `places` vient de `places_du_monde`. La photographie garde `document_de_la_guerre`.
    """
    document = document_de_la_guerre(monde)
    par_id = {a.identifiant: a for a in getattr(monde, "armees", ())}
    for servie in document["armees"]:
        armee = par_id[servie["identifiant"]]
        etapes = _etapes(armee, places)
        point = places[armee.cell_id][armee.rang].en_document()
        if etapes and armee.avance_km > 0:
            longueur = _troncon_km(monde, armee)[0]
            part = min(1.0, armee.avance_km / longueur) if longueur > 0 else 0.0
            vers = etapes[0].en_document()
            point = {cle: point[cle] + (vers[cle] - point[cle]) * part for cle in point}
        servie["point"] = point
        servie["etapes"] = [p.en_document() for p in etapes]
    return document


def km_de_marche(monde, armee, route) -> float:
    """Les kilomètres freinés de la marche par `route` vers un bourg, comme le maillon les fait : de son lieu
    au bourg de sa cellule, puis d'arête en arête (`convois._longueur_arete`)."""
    from sim.convois import _longueur_arete
    from sim.places import distance_km
    km = 0.0
    if armee.rang != 0:
        places = _places_de_la_cellule(monde, armee.cell_id)
        km += distance_km(places[armee.rang], places[0])
    depart = armee.cell_id
    for cid in route:
        km += _longueur_arete(monde, depart, cid)
        depart = cid
    return km


def devis_des_ordres(monde, maison, cell_id=None, regles=None) -> dict:
    """Ce que coûtent les ordres de guerre de `maison` aujourd'hui, et pourquoi chacun serait refusé.

    Chaque refus est celui que le dépôt rendrait au même instant, par les mêmes fonctions et les mêmes
    intentions déjà déposées ; le dépôt garde ses propres vérifications. `cell_id` : la terre visée par la
    déclaration (son bourg) et par la marche de chaque armée, ou None. Rien n'est écrit au monde.
    """
    from sim import intentions as _intentions
    regles = charger_regles() if regles is None else regles
    fiche = _maison(monde, maison)
    if fiche is None:
        raise GuerreInvalide(f"maison inconnue : {maison!r}")
    en_attente = _intentions.levees_en_attente(monde)
    declarees = _intentions.declarations_en_attente(monde)
    lieux, paysans = [], 0
    if fiche.cell_id is not None and fiche.cell_id in monde.cells:
        capitale = monde.cells[fiche.cell_id]
        paysans = max(0, _paysans(capitale) - sum(h for c, _r, h in en_attente if c == fiche.cell_id))
        lieux = [{"cell_id": fiche.cell_id, "rang": lieu.rang,
                  "hommes_max": min(paysans, levee_maximale(monde, fiche.cell_id, lieu.rang, regles, en_attente))}
                 for lieu in sorted(capitale.lieux, key=lambda l: l.rang) if lieu.maitre == maison]
    levee = {"refus": raison_levee_fermee(monde, maison, regles), "lieux": lieux, "paysans": paysans,
             "grain_libre_kg": _intentions.grain_libre_de(monde, maison),
             "ration_kg_par_homme_par_jour": regles.ration_kg_par_homme_par_jour}
    cible = None
    if cell_id is not None:
        maitre = getattr(_bourg(monde.cells[cell_id]), "maitre", None)
        refus = ("personne ne tient le bourg de cette terre" if maitre is None
                 else verifier_declaration(monde, maison, maitre, declarees))
        cible = {"cell_id": cell_id, "maitre": maitre, "declaration": {"refus": refus}}
    armees = []
    for armee in sorted((a for a in monde.armees if a.maison == maison), key=lambda a: a.identifiant):
        deja = _intentions.ordre_deja_donne(monde, armee.identifiant)
        marche = None
        if cell_id is not None:
            refus = deja or verifier_marche(monde, maison, armee.identifiant, cell_id, 0)
            route = [] if refus is not None else list(chemin(monde, armee.cell_id, cell_id))
            km = 0.0 if refus is not None else km_de_marche(monde, armee, route)
            marche = {"refus": refus, "route": route, "km": km,
                      "jours": 0 if refus is not None else max(1, math.ceil(km / regles.vitesse_marche_km_par_jour))}
        armees.append({
            "identifiant": armee.identifiant, "cell_id": armee.cell_id, "rang": armee.rang, "hommes": armee.hommes,
            "vivres_kg": armee.vivres_kg, "siege": armee.siege,
            "destination": None if armee.destination is None else list(armee.destination),
            "marche": marche,
            "assieger": {"refus": deja or verifier_siege(monde, maison, armee.identifiant, declarees)},
            "renvoyer": {"refus": deja or verifier_renvoi(monde, maison, armee.identifiant),
                         "hommes": armee.hommes, "vivres_kg": armee.vivres_kg},
        })
    return {"tick": monde.ticks_ecoules, "date": _constantes.date_de_tick(monde.ticks_ecoules), "maison": maison,
            "levee": levee, "cible": cible, "armees": armees}


# --- Ce que l'IA lit pour faire la guerre ---------------------------------------------

def racine(par_id, maison) -> str | None:
    """La maison au sommet de la suzeraineté de `maison` (elle-même sans suzerain) ; `par_id` : id → fiche."""
    vus = set()
    while maison in par_id and par_id[maison].suzerain is not None and maison not in vus:
        vus.add(maison)
        maison = par_id[maison].suzerain
    return maison


def jours_de_marche(monde, depart, regles) -> dict:
    """cell_id → jours de marche depuis la cellule `depart`, par le plus court chemin terrestre freiné par le relief.

    Au moins un jour hors de sa cellule ; seules les cellules à au plus `ia_jours_de_marche_max` jours.
    """
    from sim.convois import _plus_court
    jours = {}
    for cid, km in _plus_court(monde, depart).items():
        n = 0 if cid == depart else max(1, math.ceil(km / regles.vitesse_marche_km_par_jour))
        if n <= regles.ia_jours_de_marche_max:
            jours[cid] = n
    return jours


def place_a_prendre(monde, maison, depart, regles, vise) -> tuple | None:
    """`(cell_id, jours, maître)` du bourg le plus proche en jours de marche dont le maître est visé.

    `vise(maître)` dit si ce maître se prend. À égalité de jours, le bourg le moins peuplé, puis la
    plus petite cellule. Les bourgs de la maison et ceux sans maître ne se prennent pas.
    """
    retenue = None
    for cid, jours in jours_de_marche(monde, depart, regles).items():
        bourg = _bourg(monde.cells[cid])
        if bourg is None or bourg.maitre is None or bourg.maitre == maison or not vise(bourg.maitre):
            continue
        cle = (jours, bourg.population, cid)
        if retenue is None or cle < retenue[0]:
            retenue = (cle, bourg.maitre)
    if retenue is None:
        return None
    (jours, _population, cid), maitre = retenue
    return cid, jours, maitre
