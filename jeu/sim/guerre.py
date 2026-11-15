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
}
_CHAMPS_D_UNE_LEVEE = ("cell", "rang", "hommes")


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
    jours = document["siege"]["jours_de_faim_avant_la_chute"]
    if isinstance(jours, bool) or not isinstance(jours, int) or jours < 1:
        raise GuerreInvalide("siege.jours_de_faim_avant_la_chute : entier au moins égal à 1 attendu")
    return Regles(
        _nombre(document["levee"]["part_maximale"], "levee.part_maximale", 0, 1),
        batiment,
        _nombre(document["marche"]["km_par_jour"], "marche.km_par_jour", 0),
        _nombre(document["vivres"]["ration_kg_par_homme_par_jour"], "vivres.ration_kg_par_homme_par_jour", 0),
        _nombre(document["vivres"]["part_prise_par_jour"], "vivres.part_prise_par_jour", 0, 1, strict=False),
        jours)


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
        return f"la levée est fermée : la capitale de {maison} est hors de la carte"
    bourg = _bourg(monde.cells[fiche.cell_id])
    if bourg is None or bourg.maitre != maison:
        return (f"la levée est fermée : le bourg de la capitale (cellule {fiche.cell_id}) "
                f"est à {getattr(bourg, 'maitre', None)!r}")
    if not any(b.cell_id == fiche.cell_id and b.nature == regles.batiment_de_levee and not b.en_chantier
               for b in monde.batiments_de_province):
        return (f"la levée est fermée : aucune {regles.batiment_de_levee} achevée dans la capitale "
                f"(cellule {fiche.cell_id})")
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
        return None, f"armée inconnue : {identifiant}"
    if armee.maison != maison:
        return None, f"cette armée n'est pas à toi : elle est à {armee.maison}"
    return armee, None


# --- Les refus --------------------------------------------------------------------

def verifier_declaration(monde, maison, cible, declarees=()) -> str | None:
    """La raison du refus d'une déclaration, ou None. `declarees` : couples déjà déposés."""
    if _maison(monde, maison) is None:
        return f"maison inconnue ou mal formée : {maison!r}"
    if _maison(monde, cible) is None:
        return f"cible inconnue : {cible!r}"
    if cible == maison:
        return "on ne se déclare pas la guerre à soi-même"
    if en_guerre(monde, maison, cible, declarees):
        return f"déjà en guerre avec {cible}"
    if not any(lieu.maitre == cible for cid in sorted(monde.cells) for lieu in monde.cells[cid].lieux):
        return f"{cible} ne tient aucun lieu : rien à prendre"
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
        return f"grenier insuffisant : {vivres_kg:g} kg de vivres demandés, {grain_libre:g} kg disponibles"
    par_cellule = {}
    for cid, rang, hommes in lieux:
        cellule = monde.cells.get(cid)
        if cellule is None or not 0 <= rang < len(cellule.lieux):
            return f"lieu inconnu : ({cid}, {rang})"
        lieu = cellule.lieux[rang]
        if lieu.maitre != maison:
            return f"ce lieu n'est pas à toi : ({cid}, {rang}) est à {lieu.maitre!r}"
        maximum = levee_maximale(monde, cid, rang, regles, en_attente)
        if hommes > maximum:
            return (f"trop d'hommes : ({cid}, {rang}) peut en donner {maximum}, "
                    f"{hommes} demandés (au plus {regles.part_maximale_levee:g} de ses habitants sous les armes)")
        par_cellule[cid] = par_cellule.get(cid, 0) + hommes
    for cid, hommes in sorted(par_cellule.items()):
        deja = sum(h for c, _r, h in en_attente if c == cid)
        paysans = _paysans(monde.cells[cid]) - deja
        if hommes > paysans:
            return f"pas assez de paysans : {hommes} hommes demandés dans la cellule {cid}, {paysans} paysans"
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
        return f"lieu inconnu : ({cell_id}, {rang})"
    if (armee.cell_id, armee.rang) == (cell_id, rang):
        return f"l'armée est déjà à ({cell_id}, {rang})"
    try:
        route = chemin(monde, armee.cell_id, cell_id)
    except ValueError as exc:
        return f"aucun chemin terrestre : {exc}"
    if route is None:
        return f"aucun chemin terrestre de la cellule {armee.cell_id} à la cellule {cell_id}"
    return None


def verifier_siege(monde, maison, identifiant, declarees=()) -> str | None:
    armee, refus = _armee(monde, maison, identifiant)
    if refus is not None:
        return refus
    if armee.destination is not None:
        return f"l'armée marche encore vers {tuple(armee.destination)}"
    if armee.rang != 0:
        return f"ce lieu n'est pas une place : ({armee.cell_id}, {armee.rang}) n'est pas un bourg"
    if armee.siege == armee.cell_id:
        return f"l'armée assiège déjà la cellule {armee.cell_id}"
    maitre = getattr(_bourg(monde.cells[armee.cell_id]), "maitre", None)
    if maitre == maison:
        return f"cette place est à toi : cellule {armee.cell_id}"
    if not en_guerre(monde, maison, maitre, declarees):
        return f"pas en guerre avec le maître de la place : {maitre!r}"
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
