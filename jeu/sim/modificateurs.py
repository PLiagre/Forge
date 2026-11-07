"""Le registre des modificateurs : définir, poser, faire expirer, additionner, détailler.

Un modificateur (VISION.md, décisions 34, 35 et 37) a un nom, une source, une
cible, une grandeur du moteur, une valeur et une durée. Ses définitions vivent
dans `data/modificateurs.toml` ; une pose vit dans `World.modificateurs`, et
rien d'autre ne se garde : la cible est un pays (identifiant de maison), une
cellule (`cell_id`, la province à l'échelle d'EU4) ou un lieu (`cell_id`,
`rang`), jamais une seconde clé spatiale.

Pour une grandeur, un lieu reçoit un facteur `1 + somme des valeurs` de toutes
les poses qui le touchent : celles de son pays (la maison qui le tient), de sa
cellule et du lieu lui-même, additionnées dans un ordre fixé. Le moteur
multiplie son taux par ce facteur ; sans pose sur une grandeur, il ne lit rien
et calcule exactement comme avant. Un modificateur change un taux, jamais un
stock : il n'existe pas de grandeur « kilos » (décision 35).
"""
from dataclasses import dataclass
import math
from pathlib import Path
import tomllib

import sim.constants as _constantes

_CHEMIN = Path(__file__).parents[1] / "data" / "modificateurs.toml"
PORTEES = ("pays", "cellule", "lieu")
_CHAMPS_DEFINITION = {"nom", "grandeur", "valeur", "portee", "duree_jours"}
_CHAMPS_GRANDEUR = {"nom", "dit", "lue", "raison"}
_CHAMPS_D_UN_LIEU = ("cell_id", "rang")


class ModificateurInvalide(ValueError):
    """Une définition ou une pose que le registre refuse, avec sa raison."""


@dataclass(frozen=True)
class Grandeur:
    identifiant: str
    nom: str
    dit: str
    lue: bool
    raison: str | None = None


@dataclass(frozen=True)
class Definition:
    identifiant: str
    nom: str
    grandeur: str
    valeur: float
    portee: str
    duree_jours: int


@dataclass(frozen=True)
class Donnees:
    sources: tuple
    grandeurs: dict
    definitions: dict


@dataclass(frozen=True)
class Pose:
    """Un modificateur posé : sa définition recopiée, sa source, sa cible, ses dates."""

    identifiant: str
    nom: str
    grandeur: str
    valeur: float
    source: str
    cible: tuple
    debut: int
    fin: int | None

    def en_document(self) -> dict:
        return {
            "identifiant": self.identifiant, "nom": self.nom, "grandeur": self.grandeur,
            "valeur": self.valeur, "source": self.source, "cible": cible_en_document(self.cible),
            "debut": self.debut, "fin": self.fin,
        }


def _texte(valeur, ou):
    if not isinstance(valeur, str) or not valeur.strip():
        raise ModificateurInvalide(f"{ou} : texte non vide attendu")
    return valeur


def _nombre(valeur, ou):
    if isinstance(valeur, bool) or not isinstance(valeur, (int, float)) or not math.isfinite(valeur):
        raise ModificateurInvalide(f"{ou} : nombre fini attendu")
    return float(valeur)


def lire_donnees(document: dict) -> Donnees:
    """Valide un document déjà lu ; refuse ce qui ne serait pas un taux."""
    if not isinstance(document, dict):
        raise ModificateurInvalide("document des modificateurs : table attendue")
    sources = document.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ModificateurInvalide("sources : liste non vide attendue")
    sources = tuple(_texte(s, "sources") for s in sources)
    grandeurs = {}
    for identifiant, brute in sorted((document.get("grandeurs") or {}).items()):
        if not isinstance(brute, dict) or set(brute) - _CHAMPS_GRANDEUR:
            raise ModificateurInvalide(f"grandeur {identifiant} : champs inconnus {sorted(set(brute) - _CHAMPS_GRANDEUR)}")
        lue = brute.get("lue")
        if not isinstance(lue, bool):
            raise ModificateurInvalide(f"grandeur {identifiant}, lue : vrai ou faux attendu")
        raison = brute.get("raison")
        if not lue:
            _texte(raison, f"grandeur {identifiant}, raison")
        grandeurs[identifiant] = Grandeur(identifiant, _texte(brute.get("nom"), f"grandeur {identifiant}, nom"),
                                          _texte(brute.get("dit"), f"grandeur {identifiant}, dit"), lue, raison)
    if not grandeurs:
        raise ModificateurInvalide("grandeurs : aucune grandeur du moteur déclarée")
    definitions = {}
    for identifiant, brute in sorted((document.get("modificateurs") or {}).items()):
        if not isinstance(brute, dict):
            raise ModificateurInvalide(f"modificateur {identifiant} : table attendue")
        inconnus = set(brute) - _CHAMPS_DEFINITION
        if inconnus:
            raise ModificateurInvalide(
                f"modificateur {identifiant} : champs inconnus {sorted(inconnus)} ; "
                "un modificateur ne porte qu'un taux, jamais des kilos ou des pièces")
        grandeur = brute.get("grandeur")
        if grandeur not in grandeurs:
            raise ModificateurInvalide(
                f"modificateur {identifiant} : grandeur {grandeur!r} inconnue ; le moteur ne lit que "
                f"des taux ({', '.join(sorted(grandeurs))})")
        valeur = _nombre(brute.get("valeur"), f"modificateur {identifiant}, valeur")
        if valeur <= -1:
            raise ModificateurInvalide(f"modificateur {identifiant}, valeur : au-dessus de −100 % attendu")
        portee = brute.get("portee")
        if portee not in PORTEES:
            raise ModificateurInvalide(f"modificateur {identifiant}, portee : {', '.join(PORTEES)} attendu")
        duree = brute.get("duree_jours")
        if isinstance(duree, bool) or not isinstance(duree, int) or duree < 0:
            raise ModificateurInvalide(f"modificateur {identifiant}, duree_jours : entier positif ou nul attendu")
        definitions[identifiant] = Definition(identifiant, _texte(brute.get("nom"), f"modificateur {identifiant}, nom"),
                                              grandeur, valeur, portee, duree)
    return Donnees(sources, grandeurs, definitions)


def charger_donnees(chemin=None) -> Donnees:
    """Lit `data/modificateurs.toml` (ou le fichier donné), à chaque appel."""
    with open(chemin if chemin is not None else _CHEMIN, "rb") as fichier:
        return lire_donnees(tomllib.load(fichier))


def cible_en_document(cible: tuple) -> dict:
    sorte = cible[0]
    if sorte == "lieu":
        return {"lieu": [cible[1], cible[2]]}
    return {sorte: cible[1]}


def lire_cible(monde, brute) -> tuple:
    """Une cible du joueur, de l'IA ou d'une donnée : {"pays": id}, {"cellule": cid} ou {"lieu": [cid, rang]}."""
    if not isinstance(brute, dict) or len(brute) != 1:
        raise ModificateurInvalide("cible : une seule clé parmi pays, cellule, lieu attendue")
    (sorte, valeur), = brute.items()
    if sorte == "pays":
        connues = {m.id for m in getattr(monde, "maisons", ())}
        if not isinstance(valeur, str) or valeur not in connues:
            raise ModificateurInvalide(f"cible pays {valeur!r} : maison inconnue du registre")
        return ("pays", valeur)
    if sorte == "cellule":
        if isinstance(valeur, bool) or not isinstance(valeur, int) or valeur not in monde.cells:
            raise ModificateurInvalide(f"cible cellule {valeur!r} : cell_id inconnu")
        return ("cellule", valeur)
    if sorte == "lieu":
        if (not isinstance(valeur, (list, tuple)) or len(valeur) != len(_CHAMPS_D_UN_LIEU)
                or any(isinstance(v, bool) or not isinstance(v, int) for v in valeur)):
            raise ModificateurInvalide(f"cible lieu {valeur!r} : [cell_id, rang] attendu")
        cid, rang = valeur
        cellule = monde.cells.get(cid)
        if cellule is None or not any(lieu.rang == rang for lieu in cellule.lieux):
            raise ModificateurInvalide(f"cible lieu {valeur!r} : lieu inconnu")
        return ("lieu", cid, rang)
    raise ModificateurInvalide(f"cible {sorte!r} : pays, cellule ou lieu attendu")


def poser(monde, identifiant, source, cible, donnees=None) -> Pose:
    """Pose une définition sur une cible au tick courant ; refuse sans source ni grandeur lue."""
    donnees = charger_donnees() if donnees is None else donnees
    definition = donnees.definitions.get(identifiant)
    if definition is None:
        raise ModificateurInvalide(f"modificateur {identifiant!r} : inconnu des données")
    if not isinstance(source, str) or ":" not in source:
        raise ModificateurInvalide(f"modificateur {identifiant} : sans source (« sorte:identifiant » attendu)")
    sorte, _, quoi = source.partition(":")
    if sorte not in donnees.sources or not quoi.strip():
        raise ModificateurInvalide(
            f"modificateur {identifiant} : source {source!r} inconnue ({', '.join(donnees.sources)})")
    grandeur = donnees.grandeurs[definition.grandeur]
    if not grandeur.lue:
        raise ModificateurInvalide(f"modificateur {identifiant} : {grandeur.raison}")
    lue = lire_cible(monde, cible) if isinstance(cible, dict) else lire_cible(monde, cible_en_document(cible))
    if lue[0] != definition.portee:
        raise ModificateurInvalide(
            f"modificateur {identifiant} : se pose sur un {definition.portee}, pas sur un {lue[0]}")
    debut = monde.ticks_ecoules
    fin = debut + definition.duree_jours // _constantes.TICK_DURATION_DAYS if definition.duree_jours else None
    pose = Pose(definition.identifiant, definition.nom, definition.grandeur, definition.valeur,
                source, lue, debut, fin)
    monde.modificateurs = sorted([*monde.modificateurs, pose], key=_ordre)
    return pose


def retirer(monde, source) -> int:
    """Retire toutes les poses d'une source (un bâtiment détruit, une loi abolie)."""
    restantes = [p for p in monde.modificateurs if p.source != source]
    retirees = len(monde.modificateurs) - len(restantes)
    monde.modificateurs = restantes
    return retirees


def expirer(monde) -> list:
    """Au début du tick : retire les poses dont la fin est atteinte, et les rend."""
    if not monde.modificateurs:
        return []
    t = monde.ticks_ecoules
    parties = [p for p in monde.modificateurs if p.fin is not None and p.fin <= t]
    if parties:
        monde.modificateurs = [p for p in monde.modificateurs if p.fin is None or p.fin > t]
    return parties


def _ordre(pose):
    """L'ordre fixé de l'addition et du détail : grandeur, portée, cible, source, nom, début."""
    return (pose.grandeur, PORTEES.index(pose.cible[0]), tuple(str(x) for x in pose.cible[1:]),
            pose.source, pose.identifiant, pose.debut)


def _lieux_touches(monde, cible, tenus=None):
    sorte = cible[0]
    if sorte == "lieu":
        return [(cible[1], cible[2])]
    if sorte == "cellule":
        return [(cible[1], lieu.rang) for lieu in monde.cells[cible[1]].lieux]
    return list((tenus or {}).get(cible[1], ()))


def _tenus(monde):
    """Les lieux de chaque maître, lus sur les lieux du monde (le maître est porté par le lieu)."""
    tenus = {}
    for cid in sorted(monde.cells):
        for lieu in monde.cells[cid].lieux:
            if lieu.maitre is not None:
                tenus.setdefault(lieu.maitre, []).append((cid, lieu.rang))
    return tenus


def facteurs_du_monde(monde) -> dict:
    """grandeur → {(cell_id, rang) → facteur} ; vide sans pose. Le tick le calcule une fois."""
    poses = getattr(monde, "modificateurs", None)
    if not poses:
        return {}
    tenus = _tenus(monde) if any(p.cible[0] == "pays" for p in poses) else None
    valeurs = {}
    for pose in sorted(poses, key=_ordre):
        par_lieu = valeurs.setdefault(pose.grandeur, {})
        for cle in _lieux_touches(monde, pose.cible, tenus):
            par_lieu.setdefault(cle, []).append(pose.valeur)
    return {grandeur: {cle: 1 + math.fsum(liste) for cle, liste in sorted(par_lieu.items())}
            for grandeur, par_lieu in sorted(valeurs.items())}


def facteur(monde, grandeur, cell_id, rang) -> float:
    """Le facteur d'un lieu pour une grandeur, lu hors du tick (l'IA, une intention) : 1.0 sans pose."""
    poses = [p for p in getattr(monde, "modificateurs", ()) if p.grandeur == grandeur]
    if not poses:
        return 1.0
    tenus = _tenus(monde) if any(p.cible[0] == "pays" for p in poses) else None
    valeurs = [p.valeur for p in sorted(poses, key=_ordre) if (cell_id, rang) in _lieux_touches(monde, p.cible, tenus)]
    return 1 + math.fsum(valeurs) if valeurs else 1.0


def ajuster_journees(monde, cell_id, journees):
    """Les journées d'un chantier posé au bourg de `cell_id`, avec sa durée modifiée."""
    f = facteur(monde, "duree_chantier", cell_id, 0)
    if f == 1.0:
        return journees
    return max(1, math.ceil(journees * f))


def detail(monde, cell_id, rang) -> dict:
    """L'infobulle d'un lieu : par grandeur, chaque pose qui le touche, dans l'ordre, et le total."""
    poses = getattr(monde, "modificateurs", ())
    tenus = _tenus(monde) if any(p.cible[0] == "pays" for p in poses) else None
    lignes = {}
    for pose in sorted(poses, key=_ordre):
        if (cell_id, rang) in _lieux_touches(monde, pose.cible, tenus):
            lignes.setdefault(pose.grandeur, []).append(pose.en_document())
    return {grandeur: {"lignes": liste, "total": math.fsum(ligne["valeur"] for ligne in liste),
                       "facteur": 1 + math.fsum(ligne["valeur"] for ligne in liste)}
            for grandeur, liste in sorted(lignes.items())}


def document_des_modificateurs(monde) -> dict:
    """Pour le service et la photographie : les poses, et le détail de chaque lieu touché."""
    poses = sorted(getattr(monde, "modificateurs", ()), key=_ordre)
    touches = sorted({cle for grandeur in facteurs_du_monde(monde).values() for cle in grandeur})
    return {
        "tick": monde.ticks_ecoules,
        "poses": [p.en_document() for p in poses],
        "lieux": [{"cell_id": cid, "rang": rang, "grandeurs": detail(monde, cid, rang)} for cid, rang in touches],
    }
