"""Les événements du monde : la famine qui pose un modificateur, et les événements à choix qu'elle ouvre.

Un événement ne décide ni un kilo ni une mort : il lit un état que le tick a
déjà calculé (ici, la faim d'un lieu) et pose, dans le registre des
modificateurs (`sim/modificateurs.py`), une pose datée que `expirer` ôtera
seule. La faim, elle, tue toujours par la dette (`engine._apply_mortality`).

Un événement à choix (`data/evenements.toml`, décision 41) naît d'une cause du
monde, lue au mois sur le registre des modificateurs, et attend la réponse de sa
maison : une intention, du joueur ou de l'IA, par le même chemin
(`intentions.RepondreEvenement`). Sans réponse au bout de son délai, le choix
par défaut s'applique. Aucun choix n'écrit un stock, ne tue ni ne finit la
famine : il pose des modificateurs, déplace une jauge ou verse une part du
grenier aux lieux de la maison.
"""
import dataclasses
import math
from pathlib import Path
import tomllib

import sim.constants as _constantes
import sim.modificateurs as _modificateurs

IDENTIFIANT_FAMINE = "famine"
SOURCE_FAMINE = "evenement:famine"
SOURCE_DES_CHOIX = "evenement"  # « evenement:<modificateur>:<maison> » : la pose d'un choix, qu'une seconde réponse renouvelle

_CHEMIN = Path(__file__).parents[1] / "data" / "evenements.toml"
CAUSE_FAMINE = "famine"
CAUSES = (CAUSE_FAMINE,)  # les seules que le code sait lire ; la révolte et la succession viendront avec leurs lots
CHOIX_MIN, CHOIX_MAX = 2, 3
_CHAMPS_EVENEMENT = frozenset({"nom", "dit", "cause", "delai_jours", "par_defaut", "choix"})
_CHAMPS_CHOIX = frozenset({"id", "nom", "dit", "grenier", "modificateurs", "jauges"})


class EvenementInvalide(ValueError):
    """Une donnée des événements que le monde refuse, avec le champ qu'elle nomme."""


@dataclasses.dataclass(frozen=True)
class Choix:
    identifiant: str
    nom: str
    dit: str
    grenier: float | None
    jauges: dict
    modificateurs: tuple


@dataclasses.dataclass(frozen=True)
class Evenement:
    identifiant: str
    nom: str
    dit: str
    cause: str
    delai_jours: int
    par_defaut: str
    choix: tuple

    def choix_de(self, identifiant) -> Choix | None:
        return next((c for c in self.choix if c.identifiant == identifiant), None)


def _lieu(monde, cid, rang):
    return next(lieu for lieu in monde.cells[cid].lieux if lieu.rang == rang)


def _famine_du_lieu(monde, cible):
    """L'indice de la pose `famine` d'un lieu dans `monde.modificateurs`, ou None."""
    return next((i for i, pose in enumerate(getattr(monde, "modificateurs", ()))
                 if pose.identifiant == IDENTIFIANT_FAMINE and pose.cible == cible), None)


def _fin(definition, tick):
    """La fin d'une pose, comme `modificateurs.poser` la compte ; aucune sans durée."""
    if not definition.duree_jours:
        return None
    return tick + definition.duree_jours // _constantes.TICK_DURATION_DAYS


def poser_les_famines(monde, affames, donnees=None) -> list:
    """Au tick courant : pose la famine au lieu dont la faim dépasse le seuil du secours, la prolonge sinon.

    `affames` : les lieux `(cell_id, rang)` dont la population est positive, la
    pénurie aussi et la faim déjà comptée. Un lieu qui porte la famine voit sa
    fin repoussée de sa durée entière, son début restant celui du premier jour ;
    un lieu qui n'en porte pas la reçoit quand sa faim dépasse
    `FAIM_AVANT_SECOURS_JOURS` ; un lieu qui a faim depuis moins longtemps n'a
    rien. Rend les lieux où une famine commence. Les données ne se lisent que
    si une pose se fait ou se prolonge.
    """
    if not affames:
        return []
    t = monde.ticks_ecoules
    seuil = _constantes.FAIM_AVANT_SECOURS_JOURS
    jour = _constantes.TICK_DURATION_DAYS
    commencent = []
    for cid, rang in sorted(affames):
        i = _famine_du_lieu(monde, ("lieu", cid, rang))
        if i is None and _lieu(monde, cid, rang).duree_faim_ticks * jour <= seuil:
            continue
        donnees = _modificateurs.charger_donnees() if donnees is None else donnees
        if i is not None:
            poses = list(monde.modificateurs)
            poses[i] = dataclasses.replace(poses[i], fin=_fin(donnees.definitions[IDENTIFIANT_FAMINE], t))
            monde.modificateurs = poses
        else:
            _modificateurs.poser(monde, IDENTIFIANT_FAMINE, SOURCE_FAMINE, {"lieu": [cid, rang]}, donnees)
            commencent.append((cid, rang))
    return commencent


def _texte(valeur, ou):
    if not isinstance(valeur, str) or not valeur.strip():
        raise EvenementInvalide(f"{ou} : texte non vide attendu")
    return valeur


def _nombre(valeur, ou):
    if isinstance(valeur, bool) or not isinstance(valeur, (int, float)) or not math.isfinite(valeur):
        raise EvenementInvalide(f"{ou} : nombre fini attendu")
    return valeur


def _lire_choix(ou, brute, donnees, regles) -> Choix:
    if not isinstance(brute, dict):
        raise EvenementInvalide(f"{ou} : table attendue")
    for champ in sorted(set(brute) - _CHAMPS_CHOIX):
        raise EvenementInvalide(
            f"{ou} : champ inconnu {champ!r} ; un choix ne peut ni écrire un stock, ni tuer, ni finir une famine")
    identifiant = _texte(brute.get("id"), f"{ou}.id")
    nom, dit = _texte(brute.get("nom"), f"{ou}.nom"), _texte(brute.get("dit"), f"{ou}.dit")
    modificateurs = brute.get("modificateurs", [])
    if not isinstance(modificateurs, list):
        raise EvenementInvalide(f"{ou}.modificateurs : liste attendue")
    for numero, cle in enumerate(modificateurs):
        place = f"{ou}.modificateurs[{numero}]"
        definition = donnees.definitions.get(cle) if isinstance(cle, str) else None
        if definition is None:
            raise EvenementInvalide(f"{place} : {cle!r} absent des données des modificateurs")
        if not donnees.grandeurs[definition.grandeur].lue:
            raise EvenementInvalide(f"{place} : grandeur {definition.grandeur!r} que le moteur ne lit pas")
        if definition.portee != "pays":
            raise EvenementInvalide(f"{place} : {cle} se pose sur un {definition.portee}, un pays attendu")
        if modificateurs.count(cle) > 1:
            raise EvenementInvalide(f"{place} : {cle} deux fois")
    ecarts = brute.get("jauges", {})
    if not isinstance(ecarts, dict):
        raise EvenementInvalide(f"{ou}.jauges : table attendue")
    for jauge, ecart in sorted(ecarts.items()):
        if jauge not in regles.jauges:
            raise EvenementInvalide(f"{ou}.jauges : {jauge!r} absente des jauges ({', '.join(sorted(regles.jauges))})")
        if _nombre(ecart, f"{ou}.jauges.{jauge}") == 0:
            raise EvenementInvalide(f"{ou}.jauges.{jauge} : écart non nul attendu")
    grenier = brute.get("grenier")
    if grenier is not None and not 0 < _nombre(grenier, f"{ou}.grenier") <= 1:
        raise EvenementInvalide(f"{ou}.grenier : part du grenier dans ]0, 1] attendue, reçu {grenier!r}")
    if not modificateurs and not ecarts:
        raise EvenementInvalide(f"{ou} : ni modificateur ni jauge ; un choix pose des modificateurs ou dépense une jauge")
    return Choix(identifiant, nom, dit, None if grenier is None else float(grenier), dict(ecarts), tuple(modificateurs))


def lire_evenements(document, modificateurs=None, regles=None) -> dict:
    """Valide un document déjà lu : identifiant → `Evenement`. Chaque refus nomme son champ."""
    from sim import jauges
    if not isinstance(document, dict) or not isinstance(document.get("evenements"), dict) or not document["evenements"]:
        raise EvenementInvalide("evenements : table d'événements attendue")
    donnees = modificateurs or _modificateurs.charger_donnees()
    regles = jauges.charger_regles() if regles is None else regles
    lus, causes = {}, {}
    for identifiant, brute in sorted(document["evenements"].items()):
        ou = f"evenements.{identifiant}"
        if not isinstance(brute, dict):
            raise EvenementInvalide(f"{ou} : table attendue")
        for champ in sorted(set(brute) - _CHAMPS_EVENEMENT):
            raise EvenementInvalide(f"{ou} : champ inconnu {champ!r}")
        nom, dit = _texte(brute.get("nom"), f"{ou}.nom"), _texte(brute.get("dit"), f"{ou}.dit")
        cause = brute.get("cause")
        if cause not in CAUSES:
            raise EvenementInvalide(f"{ou}.cause : {cause!r} inconnue ({', '.join(CAUSES)})")
        if cause in causes:
            raise EvenementInvalide(f"{ou}.cause : {cause!r} est déjà celle de {causes[cause]}")
        causes[cause] = identifiant
        delai = brute.get("delai_jours")
        if isinstance(delai, bool) or not isinstance(delai, int) or delai < 1:
            raise EvenementInvalide(f"{ou}.delai_jours : entier ≥ 1 attendu, reçu {delai!r}")
        liste = brute.get("choix")
        if not isinstance(liste, list) or not CHOIX_MIN <= len(liste) <= CHOIX_MAX:
            raise EvenementInvalide(
                f"{ou}.choix : de {CHOIX_MIN} à {CHOIX_MAX} choix attendus, reçu "
                f"{len(liste) if isinstance(liste, list) else repr(liste)}")
        choix = []
        for numero, brut in enumerate(liste):
            lu = _lire_choix(f"{ou}.choix[{numero}]", brut, donnees, regles)
            if any(lu.identifiant == autre.identifiant for autre in choix):
                raise EvenementInvalide(f"{ou}.choix[{numero}].id : {lu.identifiant!r} déjà pris par un autre choix")
            choix.append(lu)
        par_defaut = brute.get("par_defaut")
        if par_defaut not in [c.identifiant for c in choix]:
            raise EvenementInvalide(
                f"{ou}.par_defaut : un des choix attendu ({', '.join(c.identifiant for c in choix)}), reçu {par_defaut!r}")
        lus[identifiant] = Evenement(identifiant, nom, dit, cause, delai, par_defaut, tuple(choix))
    return lus


def charger_evenements(chemin=None, modificateurs=None, regles=None) -> dict:
    """Lit `data/evenements.toml` (ou le fichier donné), à chaque appel."""
    with open(chemin if chemin is not None else _CHEMIN, "rb") as fichier:
        return lire_evenements(tomllib.load(fichier), modificateurs, regles)


def _jours_en_ticks(jours) -> int:
    return jours // _constantes.TICK_DURATION_DAYS


def lieux_en_cause(monde, donnees=None) -> dict:
    """maison → ses lieux `[cell_id, rang]`, triés, dont la famine a eu son dernier jour de faim dans le mois écoulé.

    Lit le registre des modificateurs, jamais la faim brute : un lieu affamé depuis sept
    jours ou moins n'a pas de pose et ne fait pas la cause. La pose finit 365 jours après
    le dernier jour de faim : `fin − durée ≥ t − FENETRE_FLUX_TICKS`.
    """
    donnees = _modificateurs.charger_donnees() if donnees is None else donnees
    duree = _jours_en_ticks(donnees.definitions[IDENTIFIANT_FAMINE].duree_jours)
    debut = monde.ticks_ecoules - _constantes.FENETRE_FLUX_TICKS
    par_maison = {}
    for pose in monde.modificateurs:
        if (pose.identifiant != IDENTIFIANT_FAMINE or pose.cible[0] != "lieu"
                or pose.fin is None or pose.fin - duree < debut):
            continue
        _, cid, rang = pose.cible
        maitre = _lieu(monde, cid, rang).maitre
        if maitre is not None:
            par_maison.setdefault(maitre, []).append([cid, rang])
    return {maison: sorted(lieux) for maison, lieux in par_maison.items()}


_LECTEURS_DE_CAUSE = {CAUSE_FAMINE: lieux_en_cause}  # une clé par cause de `CAUSES`


def choix_attendu(monde, maison, choix, definitions=None) -> Choix | None:
    """Le choix `choix` de l'événement en attente de la maison, ou None."""
    attente = monde.evenements.get(maison)
    if attente is None:
        return None
    definitions = charger_evenements() if definitions is None else definitions
    return definitions[attente["identifiant"]].choix_de(choix)


def appliquer_choix(monde, maison, choix, kg, regles=None, donnees=None, definitions=None):
    """Joue le choix d'une maison : ôte l'événement, déplace les jauges, pose les modificateurs, ouvre le grenier.

    Dans cet ordre (MODELE.md, « Les événements à choix ») ; `kg` est la part du grenier
    déjà comptée au dépôt, et n'ouvre rien s'il n'est pas positif. Une seconde pose du
    même modificateur renouvelle la première au lieu de s'y ajouter.
    """
    from sim import jauges
    from sim.intentions import OuvrirGrenier
    regles = jauges.charger_regles() if regles is None else regles
    donnees = _modificateurs.charger_donnees() if donnees is None else donnees
    definitions = charger_evenements(modificateurs=donnees, regles=regles) if definitions is None else definitions
    attente = monde.evenements.pop(maison, None)
    if attente is None:
        raise EvenementInvalide(f"aucun événement en attente : {maison}")
    retenu = definitions[attente["identifiant"]].choix_de(choix)
    if retenu is None:
        raise EvenementInvalide(f"choix inconnu : {choix!r}")
    if retenu.jauges:
        jauges.deplacer_les_jauges(monde, maison, retenu.jauges, regles)
    for identifiant in retenu.modificateurs:
        source = f"{SOURCE_DES_CHOIX}:{identifiant}:{maison}"
        _modificateurs.retirer(monde, source)
        _modificateurs.poser(monde, identifiant, source, {"pays": maison}, donnees)
    if kg > 0:
        OuvrirGrenier(maison, kg).appliquer(monde)


def au_mois(monde, regles=None):
    """Aux bornes de mois (`jauges.avant_le_tick`) : ferme par défaut, puis ouvre, maison par maison triée.

    1. **Fermer** : un événement ouvert depuis son délai, dont aucune réponse n'attend, se ferme
       par son choix par défaut, par la même fonction que la réponse déposée.
    2. **Ouvrir** : une maison sans événement en attente, qui a la cause, en reçoit un.
    Toutes les maisons du registre, celles que personne ne joue comprises. Un monde sans
    événement et sans famine ne lit aucun fichier.
    """
    table = getattr(monde, "evenements", None)
    if table is None or not (table or any(p.identifiant == IDENTIFIANT_FAMINE for p in monde.modificateurs)):
        return
    from sim import jauges
    from sim.intentions import RepondreEvenement, IntentionRefusee, kilos_du_grenier
    regles = jauges.charger_regles() if regles is None else regles
    donnees = _modificateurs.charger_donnees()
    definitions = charger_evenements(modificateurs=donnees, regles=regles)
    causes = {e.identifiant: _LECTEURS_DE_CAUSE[e.cause](monde, donnees) for e in definitions.values()}
    attendent = {i.maison for i in monde.intentions_en_attente if isinstance(i, RepondreEvenement)}
    t = monde.ticks_ecoules
    for maison in sorted(m.id for m in monde.maisons):
        courant = table.get(maison)
        if courant is not None:
            definition = definitions[courant["identifiant"]]
            if t - courant["ouvert"] >= _jours_en_ticks(definition.delai_jours) and maison not in attendent:
                part = definition.choix_de(definition.par_defaut).grenier
                try:
                    kg = 0 if part is None else kilos_du_grenier(monde, maison, part)
                except IntentionRefusee:
                    kg = 0  # le choix par défaut n'est jamais refusé : sans grain à verser, il ne verse rien
                appliquer_choix(monde, maison, definition.par_defaut, kg, regles, donnees, definitions)
        if maison in table:
            continue
        for evenement in definitions.values():
            lieux = causes[evenement.identifiant].get(maison)
            if lieux:
                table[maison] = {"identifiant": evenement.identifiant, "ouvert": t, "lieux": lieux}
                break


def _prix_du_choix(choix, refus, kg, donnees) -> dict:
    return {
        "id": choix.identifiant, "nom": choix.nom, "dit": choix.dit,
        "grenier_kg": None if choix.grenier is None else max(kg, 0.0),
        "jauges": dict(choix.jauges),
        "modificateurs": [
            {"nom": d.nom, "grandeur": d.grandeur, "grandeur_nom": donnees.grandeurs[d.grandeur].nom,
             "valeur": d.valeur, "portee": d.portee, "duree_jours": d.duree_jours}
            for d in (donnees.definitions[cle] for cle in choix.modificateurs)],
        "refus": refus,
    }


def document_de_l_evenement(monde, maison_id) -> dict:
    """Pour `GET /evenement` : l'événement en attente de la maison, ses choix, leurs prix, leurs effets et leurs refus."""
    from sim.intentions import verifier_reponse
    document = {"maison": maison_id, "tick": monde.ticks_ecoules, "date": monde.date_simulation, "evenement": None}
    attente = monde.evenements.get(maison_id)
    if attente is None:
        return document
    donnees = _modificateurs.charger_donnees()
    definition = charger_evenements(modificateurs=donnees)[attente["identifiant"]]
    fenetre = _constantes.FENETRE_FLUX_TICKS
    echeance = attente["ouvert"] + _jours_en_ticks(definition.delai_jours)
    document["evenement"] = {
        "identifiant": definition.identifiant, "nom": definition.nom, "dit": definition.dit,
        "ouvert": attente["ouvert"], "ouvert_date": _constantes.date_de_tick(attente["ouvert"]),
        "ferme_au_tick": -(-echeance // fenetre) * fenetre,  # le premier mois qui suit le délai
        "par_defaut": definition.par_defaut, "lieux": [list(lieu) for lieu in attente["lieux"]],
        "choix": [_prix_du_choix(c, *verifier_reponse(monde, maison_id, c.identifiant), donnees)
                  for c in definition.choix],
    }
    return document
