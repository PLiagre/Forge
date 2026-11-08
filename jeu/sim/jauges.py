"""Les quatre jauges du pays : la Concorde, le Renom, le Droit, et la Plume, le Sceau, l'Épée.

VISION.md, décisions 36, 38 et 39 ; les règles et les chiffres vivent dans
`data/jauges.toml`. L'état de chaque maison vit dans `World.jauges` (sa
valeur de départ n'y est pas écrite) ; il change une fois par mois, au début
du tick, par :

- les **points** : chaque réserve reçoit la compétence du souverain dans son
  domaine, fois son taux, jusqu'à son plafond ; un pays sans chef connu n'en
  reçoit pas, et le dit ;
- les **causes du monde**, lues sur les lieux que le pays tient : un mois de
  famine (plus d'une part de ses lieux affamés) ôte un point de Concorde ;
  chaque ouvrage achevé dans ses bourgs ajoute du Renom, qui s'efface peu à
  peu ;
- les **gestes** qui les dépensent (`depenser_jauge`), du joueur ou de l'IA,
  par le même chemin.

Chaque jauge pose ensuite ses modificateurs au pays, dans le même registre
que les bâtiments (`sim.modificateurs`), sous la source « jauge:<nom>:<maison> » :
la valeur, par point d'écart à son neutre ; à son neutre, elle ne pose rien.
"""
from dataclasses import dataclass
import math
from pathlib import Path
import tomllib
import zlib

import sim.constants as _constantes
from sim import modificateurs as _modificateurs
from sim.flux import _jours_de_fenetre

_CHEMIN = Path(__file__).parents[1] / "data" / "jauges.toml"
SOURCE = "jauge"


class JaugeInvalide(ValueError):
    """Une règle des jauges, ou un geste, que le monde refuse, avec sa raison."""


@dataclass(frozen=True)
class Regles:
    domaines: tuple
    competence_min: int
    competence_max: int
    jauges: dict
    points: dict
    causes: dict
    gestes: dict


def _nombre(valeur, ou):
    if isinstance(valeur, bool) or not isinstance(valeur, (int, float)) or not math.isfinite(valeur):
        raise JaugeInvalide(f"{ou} : nombre fini attendu")
    return valeur


def lire_regles(document, modificateurs=None) -> Regles:
    """Valide un document déjà lu ; chaque modificateur d'une jauge vise une grandeur lue du moteur."""
    grandeurs = (modificateurs or _modificateurs.charger_donnees()).grandeurs
    competences = document.get("competences") or {}
    domaines = tuple(competences.get("domaines") or ())
    if not domaines or not all(isinstance(d, str) and d for d in domaines):
        raise JaugeInvalide("competences.domaines : liste de noms attendue")
    cmin, cmax = (_nombre(competences.get(k), f"competences.{k}") for k in ("minimum", "maximum"))
    if not cmin < cmax:
        raise JaugeInvalide("competences : minimum < maximum attendu")
    jauges = {}
    for nom, brute in sorted((document.get("jauges") or {}).items()):
        minimum, maximum, depart, neutre = (_nombre(brute.get(k), f"jauges.{nom}.{k}")
                                            for k in ("minimum", "maximum", "depart", "neutre"))
        if not minimum <= depart <= maximum or not minimum <= neutre <= maximum:
            raise JaugeInvalide(f"jauges.{nom} : départ et neutre entre minimum et maximum attendus")
        for grandeur, par_point in sorted((brute.get("modificateurs") or {}).items()):
            _nombre(par_point, f"jauges.{nom}.modificateurs.{grandeur}")
            if grandeur not in grandeurs or not grandeurs[grandeur].lue:
                raise JaugeInvalide(f"jauges.{nom}.modificateurs : grandeur {grandeur!r} que le moteur ne lit pas")
        jauges[nom] = dict(brute)
    points = {}
    for nom, brute in sorted((document.get("points") or {}).items()):
        if brute.get("domaine") not in domaines:
            raise JaugeInvalide(f"points.{nom}.domaine : un des domaines des compétences attendu")
        for k in ("par_point_de_competence_par_mois", "plafond"):
            if _nombre(brute.get(k), f"points.{nom}.{k}") < 0:
                raise JaugeInvalide(f"points.{nom}.{k} : positif attendu")
        points[nom] = dict(brute)
    if set(jauges) & set(points) or len(jauges) + len(points) != len(set(jauges) | set(points)):
        raise JaugeInvalide("une jauge et une réserve de points portent le même nom")
    causes = dict(document.get("causes") or {})
    for k in ("famine_part_des_lieux", "famine_concorde", "renom_par_ouvrage", "renom_effacement_par_mois"):
        _nombre(causes.get(k), f"causes.{k}")
    for jauge in ("concorde", "renom"):
        if jauge not in jauges:
            raise JaugeInvalide(f"jauges.{jauge} : jauge que les causes du monde font bouger, absente")
    gestes = {}
    for nom, brute in sorted((document.get("gestes") or {}).items()):
        cout, effet = brute.get("cout") or {}, brute.get("effet") or {}
        if not cout or any(k not in points or _nombre(v, f"gestes.{nom}.cout.{k}") <= 0 for k, v in cout.items()):
            raise JaugeInvalide(f"gestes.{nom}.cout : des points de Plume, de Sceau ou d'Épée attendus")
        if not effet or any(k not in jauges or _nombre(v, f"gestes.{nom}.effet.{k}") == 0 for k, v in effet.items()):
            raise JaugeInvalide(f"gestes.{nom}.effet : une jauge et un écart non nul attendus")
        gestes[nom] = {"nom": brute.get("nom", nom), "cout": dict(cout), "effet": dict(effet)}
    return Regles(domaines, cmin, cmax, jauges, points, causes, gestes)


def charger_regles(chemin=None) -> Regles:
    with open(chemin if chemin is not None else _CHEMIN, "rb") as fichier:
        return lire_regles(tomllib.load(fichier))


def competences(monde, maison_id, regles) -> dict | None:
    """Les compétences du chef de la maison (niveau 2, décision 39), ou None s'il n'est pas connu.

    Dérivées de l'identifiant de la personne, sans aléa du monde : stables d'une
    partie à l'autre, rien de stocké. #434 les remplacera par l'hérédité,
    l'âge et l'éducation, et par une valeur sourcée quand on la sait.
    """
    lien = (getattr(monde, "chefs", None) or {}).get(maison_id)
    personne = lien.get("personnage") if isinstance(lien, dict) else None
    if not personne:
        return None
    etendue = int(regles.competence_max - regles.competence_min) + 1
    return {domaine: int(regles.competence_min) + zlib.crc32(f"{personne}:{domaine}".encode("utf-8")) % etendue
            for domaine in regles.domaines}


def etat_initial(regles) -> dict:
    return {**{nom: j["depart"] for nom, j in regles.jauges.items()},
            **{nom: 0.0 for nom in regles.points}, "ouvrages": 0}


def etat(monde, maison_id, regles) -> dict:
    """L'état courant d'une maison (une copie) : ce qu'en garde le monde, ou le départ."""
    garde = (getattr(monde, "jauges", None) or {}).get(maison_id)
    return dict(garde) if garde is not None else etat_initial(regles)


def _borner(regles, nom, valeur):
    jauge = regles.jauges[nom]
    return min(jauge["maximum"], max(jauge["minimum"], valeur))


def _ecrire(monde, maison_id, valeurs, regles):
    if valeurs == etat_initial(regles):
        monde.jauges.pop(maison_id, None)
    else:
        monde.jauges[maison_id] = valeurs


def _ouvrages_acheves(monde, bourgs):
    compte = 0
    for cid in bourgs:
        plan = monde.plans.get(cid)
        if plan is None:
            continue
        compte += sum(not o.en_chantier for o in (*plan.rues, *plan.parcelles, *plan.batiments))
        compte += int(plan.enceinte is not None and not plan.enceinte.en_chantier)
    return compte


def mois_ecoule(monde) -> bool:
    """Vrai avant le premier tick de chaque mois de jeu, le tout premier excepté.

    Ne lit que le compteur : un monde d'épreuve sans état des jauges n'a pas de mois.
    """
    if not hasattr(monde, "jauges"):
        return False
    t = monde.ticks_ecoules
    return t > 0 and t % _constantes.FENETRE_FLUX_TICKS == 0


def avant_le_tick(monde, regles=None):
    """Ce que la boucle de jeu joue avant chaque tick, comme l'IA : le mois écoulé des jauges.

    Hors du tick : la mise à jour lit le registre des maisons, leurs chefs et les
    maîtres des lieux, que le tick ne lit jamais (MODELE.md, « Les maisons du
    monde », « Les personnes »). Les trois boucles — le service, `python -m sim`
    et `python -m forge` — l'appellent avant `jouer_ia`, IA ou non, rejeu compris.
    """
    if mois_ecoule(monde):
        mettre_a_jour(monde, regles)


def mettre_a_jour(monde, regles=None, raisons=None):
    """Le mois écoulé : points, causes du monde, puis les modificateurs de chaque pays."""
    regles = charger_regles() if regles is None else regles
    tenus = {}
    for cid in sorted(monde.cells):
        for lieu in monde.cells[cid].lieux:
            if lieu.maitre is not None:
                tenus.setdefault(lieu.maitre, []).append((cid, lieu.rang))
    affames = set()
    for jour in _jours_de_fenetre(monde):
        affames |= jour.affames
    causes = regles.causes
    for maison in sorted(monde.maisons, key=lambda m: m.id):
        valeurs = etat(monde, maison.id, regles)
        avant = dict(valeurs)
        comp = competences(monde, maison.id, regles)
        if comp is not None:
            for nom, reserve in regles.points.items():
                gain = comp[reserve["domaine"]] * reserve["par_point_de_competence_par_mois"]
                valeurs[nom] = min(reserve["plafond"], valeurs[nom] + gain)
        lieux = tenus.get(maison.id, ())
        if lieux:
            part_affamee = sum(cle in affames for cle in lieux) / len(lieux)
            if part_affamee > causes["famine_part_des_lieux"]:
                valeurs["concorde"] = _borner(regles, "concorde", valeurs["concorde"] + causes["famine_concorde"])
        acheves = _ouvrages_acheves(monde, sorted({cid for cid, rang in lieux if rang == 0}))
        nouveaux = max(0, acheves - valeurs["ouvrages"])
        valeurs["ouvrages"] = acheves
        renom = valeurs["renom"] * (1 - causes["renom_effacement_par_mois"]) + nouveaux * causes["renom_par_ouvrage"]
        valeurs["renom"] = _borner(regles, "renom", renom)
        _ecrire(monde, maison.id, valeurs, regles)
        if raisons is not None and valeurs != avant:
            raisons[maison.id] = {"avant": avant, "apres": valeurs, "competences": comp,
                                  "lieux": len(lieux), "affames": sum(cle in affames for cle in lieux)}
    poser_les_modificateurs(monde, regles)


def modificateurs_de(maison_id, valeurs, regles, tick) -> list:
    """Les poses qu'un état de jauges donne à son pays : une par jauge et par grandeur, hors du neutre."""
    poses = []
    for nom, jauge in sorted(regles.jauges.items()):
        ecart = valeurs[nom] - jauge["neutre"]
        for grandeur, par_point in sorted((jauge.get("modificateurs") or {}).items()):
            valeur = ecart * par_point
            if valeur:
                poses.append(_modificateurs.Pose(
                    f"jauge-{nom}", f"{jauge['nom']} ({valeurs[nom]:+g})", grandeur, valeur,
                    f"{SOURCE}:{nom}:{maison_id}", ("pays", maison_id), tick, None))
    return poses


def poser_les_modificateurs(monde, regles):
    """Remplace en une fois toutes les poses des jauges par celles de l'état courant."""
    autres = [p for p in monde.modificateurs if not p.source.startswith(f"{SOURCE}:")]
    neuves = [pose for maison_id in sorted(monde.jauges)
              for pose in modificateurs_de(maison_id, monde.jauges[maison_id], regles, monde.ticks_ecoules)]
    if neuves or len(autres) != len(monde.modificateurs):
        monde.modificateurs = sorted(autres + neuves, key=_modificateurs._ordre)


def verifier_geste(monde, maison_id, geste, regles, engages=None, registre=True):
    """La raison du refus d'un geste, ou None : maison connue, points suffisants, jauge pas à sa borne.

    `registre=False` : la maison a été vérifiée au dépôt ; au tick, le registre ne se lit pas.
    """
    if not isinstance(maison_id, str) or (registre and not any(m.id == maison_id for m in monde.maisons)):
        return f"maison inconnue ou mal formée : {maison_id!r}"
    if geste not in regles.gestes:
        return f"geste inconnu : {geste!r} ({', '.join(sorted(regles.gestes))})"
    valeurs = etat(monde, maison_id, regles)
    for precedent in engages or ():
        for nom, cout in regles.gestes[precedent]["cout"].items():
            valeurs[nom] -= cout
        for nom, ecart in regles.gestes[precedent]["effet"].items():
            valeurs[nom] = _borner(regles, nom, valeurs[nom] + ecart)
    for nom, cout in regles.gestes[geste]["cout"].items():
        if valeurs[nom] < cout:
            return (f"pas assez de points de {regles.points[nom]['nom']} : {cout} demandés, "
                    f"{valeurs[nom]:g} disponibles")
    for nom, ecart in regles.gestes[geste]["effet"].items():
        if _borner(regles, nom, valeurs[nom] + ecart) == valeurs[nom]:
            return f"{regles.jauges[nom]['nom']} déjà à sa borne : {valeurs[nom]:g}"
    return None


def appliquer_geste(monde, maison_id, geste, regles=None):
    """Dépense les points du geste et déplace sa jauge ; ses modificateurs suivent au même tick."""
    regles = charger_regles() if regles is None else regles
    raison = verifier_geste(monde, maison_id, geste, regles, registre=False)
    if raison is not None:
        raise JaugeInvalide(raison)
    valeurs = etat(monde, maison_id, regles)
    for nom, cout in regles.gestes[geste]["cout"].items():
        valeurs[nom] -= cout
    for nom, ecart in regles.gestes[geste]["effet"].items():
        valeurs[nom] = _borner(regles, nom, valeurs[nom] + ecart)
    _ecrire(monde, maison_id, valeurs, regles)
    poser_les_modificateurs(monde, regles)


def document_des_jauges(monde, maison_id, regles=None) -> dict:
    """Pour le service et le panneau du pays : les valeurs, leurs bornes, les compétences, les poses."""
    regles = charger_regles() if regles is None else regles
    valeurs = etat(monde, maison_id, regles)
    comp = competences(monde, maison_id, regles)
    return {
        "jauges": {nom: {"nom": j["nom"], "valeur": valeurs[nom], "minimum": j["minimum"],
                         "maximum": j["maximum"], "neutre": j["neutre"]} for nom, j in sorted(regles.jauges.items())},
        "points": {nom: {"nom": p["nom"], "valeur": valeurs[nom], "plafond": p["plafond"], "domaine": p["domaine"],
                         "par_mois": None if comp is None else comp[p["domaine"]] * p["par_point_de_competence_par_mois"]}
                   for nom, p in sorted(regles.points.items())},
        "competences": comp,
        "absents": {} if comp is not None else {"competences": f"chef de la maison {maison_id} non connu : aucun point"},
        "gestes": {nom: {"nom": g["nom"], "cout": g["cout"], "effet": g["effet"],
                         "refus": verifier_geste(monde, maison_id, nom, regles)} for nom, g in sorted(regles.gestes.items())},
        "modificateurs": [p.en_document() for p in modificateurs_de(maison_id, valeurs, regles, monde.ticks_ecoules)],
    }
