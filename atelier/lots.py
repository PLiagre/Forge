"""L'état d'un lot, dérivé de GitHub, et l'action qui vient ensuite.

Un lot est une issue : l'étiquette `lot`, un état (`pret`, `en-cours`,
`bloque`, `livre`), une piste (`monde`, `ville`, `interface`), `pc` s'il
demande Unity ou Blender, `simple` si le développeur le mène seul, et le
jalon GitHub de son palier (« Palier 1 — La première guerre »). Son travail
est une branche et une PR. Ce que la chaîne y a fait est écrit par le pilote,
dans les commentaires, sous une marque invisible :

    <!-- atelier {"role": "relecteur", "sha": "…", "verdict": "ACCEPTE"} -->

Rien n'est gardé ailleurs. Le pilote peut s'arrêter au milieu d'un tour : le
tour suivant relit GitHub et reprend où les faits disent qu'on en est. Tout
ce module est fait de fonctions pures : il décide, le pilote fait les gestes.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
import json
import re
import unicodedata
import uuid

from .projet import CHEF, CTO, DEVELOPPEUR, RELECTEUR, ROLES_MENEURS

ETATS = ("pret", "en-cours", "bloque", "livre")
ETIQUETTE_LOT = "lot"
ETIQUETTE_PC = "pc"
# Le développeur mène seul ce lot (données, écran courant).
ETIQUETTE_SIMPLE = "simple"
# Une réparation de master : elle passe avant tout autre lot.
ETIQUETTE_URGENT = "urgent"
# L'issue d'un palier : le propriétaire y écrit le samedi, le CTO y répond.
ETIQUETTE_PALIER = "palier"
_MARQUE = re.compile(r"<!-- atelier (\{.*?\}) -->", re.S)
_DEPEND = re.compile(r"^[ \t]*(?:#+[ \t]*)?D[ée]pend de[ \t]*:?[ \t]*(.*)$", re.I | re.M)
_DECOUPE = re.compile(r"D[ée]coup[ée] du lot #(\d+)", re.I)
_PALIER = re.compile(r"^Palier (\d+)\b")


def slug(titre: str, longueur: int = 48) -> str:
    plat = unicodedata.normalize("NFKD", titre).encode("ascii", "ignore").decode()
    mots = re.sub(r"[^a-z0-9]+", "-", plat.lower()).strip("-")
    return mots[:longueur].rstrip("-") or "lot"


def numero_de_palier(titre: str | None) -> int | None:
    m = _PALIER.match(titre or "")
    return int(m.group(1)) if m else None


def marque(**champs) -> str:
    """La marque du pilote. « --> » fermerait le commentaire qui la porte."""
    return "<!-- atelier " + json.dumps(champs, ensure_ascii=False, sort_keys=True).replace("-->", "→") + " -->"


def marques(commentaires: list[dict]) -> list[dict]:
    """Les marques du pilote, dans l'ordre des commentaires."""
    trouvees = []
    for c in commentaires or []:
        for brut in _MARQUE.findall(c.get("body") or ""):
            try:
                trouvees.append(json.loads(brut))
            except json.JSONDecodeError:
                continue
    return trouvees


def sans_marque(texte: str) -> str:
    return _MARQUE.sub("", texte or "").strip()


def session_du_lot(depot: str, numero: int, generation: int = 0) -> str:
    """L'identifiant de la session du lot : le même à chaque tour, pour que le
    chef reprenne sa session. `generation` en ouvre une autre."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"https://github.com/{depot}/issues/{numero}#{generation}"))


@dataclass(frozen=True)
class Palier:
    numero: int
    titre: str
    id: int
    ouvert: bool


def paliers(jalons: list[dict]) -> list[Palier]:
    """Les jalons GitHub qui sont des paliers, dans l'ordre."""
    trouves = [Palier(numero=n, titre=m["title"], id=m["number"], ouvert=m.get("state") == "open")
               for m in jalons if (n := numero_de_palier(m.get("title"))) is not None]
    return sorted(trouves, key=lambda p: p.numero)


def palier_courant(liste: list[Palier]) -> Palier | None:
    """Le premier palier ouvert : c'est dans lui que le pilote prend."""
    return next((p for p in liste if p.ouvert), None)


@dataclass(frozen=True)
class Lot:
    numero: int
    titre: str
    corps: str
    etiquettes: tuple[str, ...]
    palier: int | None
    palier_titre: str | None

    @classmethod
    def de(cls, issue: dict) -> "Lot":
        etiquettes = tuple(e["name"] for e in issue.get("labels") or [])
        titre = (issue.get("milestone") or {}).get("title")
        return cls(numero=issue["number"], titre=issue["title"], corps=issue.get("body") or "",
                   etiquettes=etiquettes, palier=numero_de_palier(titre), palier_titre=titre)

    @property
    def est_un_lot(self) -> bool:
        return ETIQUETTE_LOT in self.etiquettes

    @property
    def etat(self) -> str:
        return next((e for e in ETATS if e in self.etiquettes), "pret")

    @property
    def machine(self) -> str:
        return "pc" if ETIQUETTE_PC in self.etiquettes else "vps"

    @property
    def meneur(self) -> str:
        """Le rôle qui mène le lot : le chef, ou le développeur seul pour un lot simple."""
        return DEVELOPPEUR if ETIQUETTE_SIMPLE in self.etiquettes else CHEF

    @property
    def urgent(self) -> bool:
        return ETIQUETTE_URGENT in self.etiquettes

    def piste(self, pistes: Iterable[str]) -> str:
        return next((p for p in pistes if p in self.etiquettes), "")

    def branche(self, prefixe: str) -> str:
        return f"{prefixe}{self.numero}-{slug(self.titre)}"

    @property
    def dependances(self) -> frozenset[int]:
        """Les issues que ce lot attend : « Dépend de : #12, #13 » dans son
        texte, ou le champ « Dépend de » du formulaire, dont la valeur est au
        paragraphe suivant."""
        trouvees: set[int] = set()
        for m in _DEPEND.finditer(self.corps):
            lignes = self.corps[m.start():].splitlines()
            bloc = [lignes[0]]
            # Seul le titre nu du formulaire porte sa valeur plus bas : une
            # ligne qui dit autre chose (« aucune ») a déjà tout dit.
            if not m.group(1).strip():
                for ligne in lignes[1:]:
                    if ligne.startswith("#") and not re.match(r"#\d", ligne) or (not ligne.strip() and any(b.strip() for b in bloc[1:])):
                        break
                    bloc.append(ligne)
            trouvees |= {int(n) for n in re.findall(r"#(\d+)", " ".join(bloc))}
        return frozenset(trouvees)

    @property
    def decoupe_de(self) -> int | None:
        """Le lot dont celui-ci est un morceau, quand le CTO l'a redécoupé."""
        m = _DECOUPE.search(self.corps)
        return int(m.group(1)) if m else None


def bloquantes(ouvertes: list[Lot], fermees: list[Lot] = ()) -> frozenset[int]:
    """Les issues qu'un lot qui en dépend attend encore : chaque issue
    ouverte, et un lot redécoupé tant qu'un de ses morceaux est ouvert. Les
    découpes s'emboîtent : les lots fermés disent de qui ils descendent."""
    parents = {l.numero: l.decoupe_de for l in (*ouvertes, *fermees) if l.decoupe_de is not None}
    resultat = {l.numero for l in ouvertes}
    for lot in ouvertes:
        n, vus = lot.decoupe_de, set()
        while n is not None and n not in vus:
            vus.add(n)
            resultat.add(n)
            n = parents.get(n)
    return frozenset(resultat)


def boucles(ouvertes: list[Lot]) -> list[tuple[int, ...]]:
    """Les lots ouverts qui s'attendent en rond : chaque boucle est rendue une
    fois, du plus petit numéro au suivant (« 12 attend 15, qui attend 12 »).
    Des lots pris dans une boucle n'avanceraient jamais, sans que rien ne le
    dise."""
    attend = {l.numero: sorted(l.dependances) for l in ouvertes}
    trouvees: set[tuple[int, ...]] = set()

    def suivre(depart: int, courant: int, chemin: list[int]) -> None:
        for suivant in attend.get(courant, ()):
            if suivant == depart:
                trouvees.add(tuple(chemin))
            elif suivant > depart and suivant not in chemin and suivant in attend:
                suivre(depart, suivant, chemin + [suivant])

    for numero in sorted(attend):
        suivre(numero, numero, [numero])
    return sorted(trouvees)


def ferme_une_boucle(lot: Lot, nouvelles: Iterable[int], ouvertes: list[Lot]) -> tuple[int, ...] | None:
    """La boucle que créerait l'ajout de ces dépendances à ce lot, ou None."""
    essai = Lot(numero=lot.numero, titre=lot.titre, etiquettes=lot.etiquettes, palier=lot.palier,
                palier_titre=lot.palier_titre, corps=avec_dependances(lot.corps, nouvelles))
    autres = [l for l in ouvertes if l.numero != lot.numero]
    return next((b for b in boucles([*autres, essai]) if lot.numero in b), None)


def avec_dependances(corps: str, numeros: Iterable[int]) -> str:
    """Le texte d'une issue avec ces issues de plus dans son « Dépend de »."""
    ajout = ", ".join(f"#{n}" for n in numeros)
    if not ajout:
        return corps
    lignes = corps.split("\n")
    for i in range(len(lignes) - 1, -1, -1):
        m = _DEPEND.match(lignes[i])
        if m and re.search(r"#\d+", m.group(1)):
            nu = lignes[i].rstrip()
            lignes[i] = f"{nu}, {ajout}{lignes[i][len(nu):]}"
            return "\n".join(lignes)
    return corps.rstrip("\r\n") + f"\n\nDépend de : {ajout}\n"


def sans_dependances(corps: str, numeros: Iterable[int]) -> str:
    """Le texte d'une issue sans ces issues dans son « Dépend de »."""
    retirer = {int(n) for n in numeros}

    def garder(ligne: str) -> str:
        return ", ".join(f"#{n}" for n in re.findall(r"#(\d+)", ligne) if int(n) not in retirer)

    lignes, dans_le_champ = [], False
    for ligne in corps.split("\n"):
        m = _DEPEND.match(ligne)
        if m and m.group(1).strip():
            # « Dépend de : #12, #13 » : la ligne garde ce qui reste, ou disparaît.
            reste = garder(ligne)
            if reste:
                lignes.append(f"Dépend de : {reste}")
            dans_le_champ = False
        elif m:
            # Le titre du formulaire : sa valeur est au paragraphe suivant.
            lignes.append(ligne)
            dans_le_champ = True
        elif dans_le_champ and re.search(r"#\d+", ligne):
            lignes.append(garder(ligne))
            dans_le_champ = False
        else:
            if dans_le_champ and ligne.startswith("#"):
                dans_le_champ = False
            lignes.append(ligne)
    return "\n".join(lignes)


def a_prendre(lots: list[Lot], palier: int | None, machine_libre: dict[str, bool],
              ouvertes: frozenset[int] = frozenset()) -> Lot | None:
    """Le lot suivant : une réparation urgente d'abord, quel que soit son
    palier ; puis le lot prêt du palier courant au plus petit numéro. Une
    machine occupée ne prend rien ; un lot dont une dépendance est encore
    ouverte attend."""
    prets = [l for l in sorted(lots, key=lambda l: l.numero)
             if l.est_un_lot and l.etat == "pret" and machine_libre.get(l.machine, False)
             and not (l.dependances & ouvertes)]
    return next((l for l in prets if l.urgent), None) or next((l for l in prets if l.palier == palier
                                                               and palier is not None), None)


@dataclass(frozen=True)
class Action:
    nom: str
    raison: str = ""
    essai: int = 0


# Ce que le PC répond à un envoi : une étape faite, un échec, une coupure, ou
# une attente (aucun de ses agents n'a pu répondre : ce n'est pas un passage).
HEURES_ATTENTE_PC = 1
HEURES_SILENCE_PC = 24
# Les marques d'un passage du meneur.
PLAN, ETAPE, CORRECTION, REPONSE, COUPE, ECHEC, ENVOYE, ATTENTE = (
    "plan", "etape", "correction", "reponse", "coupe", "echec", "envoye", "attente")
# Les marques du pilote.
REPRISE, BLOQUE, DECISION, BOUCLE = "reprise", "bloque", "decision", "boucle"
# Un passage qui a compté : il a rendu quelque chose, bon ou non.
_PASSAGES = (PLAN, ETAPE, CORRECTION, REPONSE, ECHEC, COUPE)
# Deux échecs de suite du meneur, et le lot est bloqué : le CTO regarde.
ECHECS_MAX = 2
# Une étape rendue inachevée se poursuit ; trois fois de suite, elle est trop grosse.
POURSUITES_MAX = 3


def depuis_reprise(liste: list[dict]) -> list[dict]:
    """Les marques depuis la dernière reprise : un lot bloqué qui repart
    recompte ses essais de zéro."""
    for i in range(len(liste) - 1, -1, -1):
        if liste[i].get("etat") == REPRISE:
            return liste[i + 1:]
    return list(liste)


def du_meneur(liste: list[dict]) -> list[dict]:
    return [m for m in liste if m.get("role") in ROLES_MENEURS]


def plan_du_lot(liste: list[dict]) -> dict | None:
    """La marque du dernier plan : ses étapes, et la session qui l'a écrit."""
    return next((m for m in reversed(liste) if m.get("role") in ROLES_MENEURS and m.get("etat") == PLAN), None)


def etapes_faites(liste: list[dict]) -> set[int]:
    """Les étapes du dernier plan que le meneur a finies."""
    plan = plan_du_lot(liste)
    if plan is None:
        return set()
    apres = liste[max(i for i, m in enumerate(liste) if m is plan):]
    return {int(m["etape"]) for m in apres if m.get("role") in ROLES_MENEURS and m.get("etat") == ETAPE
            and m.get("fini") and m.get("etape")}


def _de_suite(passages: list[dict], etat: str) -> int:
    """Combien de passages de cet état se suivent, à la fin."""
    n = 0
    for m in reversed(passages):
        if m.get("etat") != etat:
            break
        n += 1
    return n


def action_suivante(pr: dict | None, etat_ci: str, liste: list[dict], *, corrections_max: int,
                    coupures_max: int, heures_depuis_envoi_pc: float | None = None,
                    heures_depuis_attente_pc: float | None = None) -> Action:
    """Ce que le pilote fait ensuite pour un lot en cours. Fonction pure.

    Le chemin : le plan, puis ses étapes une à une, puis la CI, puis la
    relecture, puis la fusion. Une CI rouge ou une relecture « CORRIGER »
    renvoie au meneur, `corrections_max` fois au plus ; au-delà, le lot est
    bloqué et le CTO le regarde. Les compteurs partent de la dernière
    reprise ; l'état du travail (plan, étapes, verdicts), de tout
    l'historique."""
    if pr is None:
        return Action("planifier")
    if pr.get("state") == "MERGED" or pr.get("mergedAt"):
        return Action("livrer")
    if pr.get("state") == "CLOSED":
        return Action("bloquer", "la PR a été fermée sans fusion")
    tete = pr.get("headRefOid") or ""
    siens = du_meneur(depuis_reprise(liste))

    # Un envoi au PC attend sa réponse ; sans réponse en un jour, on renvoie.
    if siens and siens[-1].get("etat") == ENVOYE:
        if heures_depuis_envoi_pc is not None and heures_depuis_envoi_pc > HEURES_SILENCE_PC:
            return Action("relancer_pc", "le PC n'a pas répondu en 24 h")
        return Action("attendre_pc", "le travail est parti sur le PC")
    if (siens and siens[-1].get("etat") == ATTENTE and heures_depuis_attente_pc is not None
            and heures_depuis_attente_pc < HEURES_ATTENTE_PC):
        return Action("attendre_pc", "aucun agent du PC n'a pu répondre : renvoi au bout d'une heure")

    passages = [m for m in siens if m.get("etat") in _PASSAGES]
    if _de_suite(passages, COUPE) >= coupures_max:
        return Action("bloquer", f"le {passages[-1].get('role')} a été coupé par son délai {coupures_max} fois de suite")
    if _de_suite(passages, ECHEC) >= ECHECS_MAX:
        return Action("bloquer", f"le {passages[-1].get('role')} a échoué {ECHECS_MAX} fois de suite")

    if pr.get("mergeable") == "CONFLICTING":
        return Action("conflit", "la branche est en conflit avec la base")

    plan = plan_du_lot(liste)
    if plan is None:
        return Action("planifier")
    faites = etapes_faites(liste)
    suivante = next((k for k in range(1, int(plan.get("etapes") or 0) + 1) if k not in faites), None)
    if suivante is not None:
        poursuites = 0
        for m in reversed(passages):
            if not (m.get("etat") == ETAPE and m.get("etape") == suivante and not m.get("fini")):
                break
            poursuites += 1
        if poursuites >= POURSUITES_MAX:
            return Action("bloquer", f"l'étape {suivante} a été rendue inachevée {POURSUITES_MAX} fois : "
                                     "elle est trop grosse pour un passage")
        return Action("etape", essai=suivante)

    corrections = sum(1 for m in siens if m.get("etat") == CORRECTION)
    if etat_ci == "attente":
        return Action("attendre_ci")
    if etat_ci == "rouge":
        if corrections >= corrections_max:
            return Action("bloquer", f"CI rouge après {corrections} correction(s)")
        resume = any(m.get("role") == "lecteur" and m.get("sha") == tete for m in liste)
        return Action("corriger_ci" if resume else "resumer_ci", "CI rouge", essai=corrections + 1)

    verdicts = [(i, m) for i, m in enumerate(liste) if m.get("role") in (RELECTEUR, CTO) and m.get("verdict")
                and m.get("sha") == tete]
    if not verdicts:
        return Action("relire")
    rang, dernier = verdicts[-1]
    if dernier["verdict"] == "ACCEPTE":
        return Action("attendre_fusion" if pr.get("autoMergeRequest") else "fusionner")
    # Le meneur a contesté ce verdict sans changer de fichier : le CTO tranche.
    suite = liste[rang + 1:]
    conteste = any(m.get("role") in ROLES_MENEURS and m.get("etat") == REPONSE for m in suite)
    arbitre = any(m.get("role") == CTO and m.get("etat") == "arbitrage" for m in suite)
    if conteste and not arbitre:
        return Action("arbitrer", "le meneur conteste la relecture")
    if corrections >= corrections_max:
        return Action("bloquer", f"relecture « CORRIGER » après {corrections} correction(s)")
    return Action("corriger_relecture", "relecture « CORRIGER »", essai=corrections + 1)


# Le travail de la CI qui chronomètre le moteur. Au bord de son budget sur
# les runners partagés, il rougit sans que le lot y soit pour rien : le pilote
# le rejoue une fois avant d'appeler le meneur, sans compter d'essai.
TRAVAIL_CHRONOMETRE = "chronometre"
ETAT_REJEU = "rejeu"
# Un rejeu qui n'a rien rendu au bout de ce temps rend la main au meneur.
HEURES_REJEU = 2


def _instant(texte: str) -> datetime | None:
    try:
        return datetime.fromisoformat(texte.replace("Z", "+00:00"))
    except ValueError:
        return None


def _depuis_le_dernier_passage(liste: list[dict]) -> list[dict]:
    """Les marques depuis le dernier passage du meneur (et la dernière reprise)."""
    passages = [i for i, m in enumerate(liste) if m.get("role") in ROLES_MENEURS and m.get("etat") in _PASSAGES]
    return depuis_reprise(liste[passages[-1] + 1:] if passages else liste)


def rejeu_du_chronometre(travaux: dict[str, dict[str, str]], agregat: str, liste: list[dict], *,
                         heures_depuis_rejeu: float | None = None) -> str:
    """Ce que fait le pilote d'une CI rouge avant d'appeler le meneur.

    `travaux` : ceux du workflow de `chronometre`, dont `agregat`, le travail
    qui les attend tous. « rejouer » : seul `chronometre` est rouge, le run
    est fini, et rien n'a été rejoué depuis le dernier passage du meneur.
    « attendre » : ce run, ou le rejeu, tourne encore ; un rouge d'avant le
    rejeu est périmé. « » : le meneur corrige."""
    depuis = _depuis_le_dernier_passage(liste)
    rejeu = next((m for m in reversed(depuis) if m.get("role") == "pilote" and m.get("etat") == ETAT_REJEU), None)
    if rejeu is not None:
        if heures_depuis_rejeu is not None and heures_depuis_rejeu > HEURES_REJEU:
            return ""
        quand = _instant(rejeu.get("quand") or "")

        def perime(t: dict[str, str]) -> bool:
            parti = _instant(t["date"])
            return quand is not None and (parti is None or parti < quand)

        en_cours = any(t["etat"] == "attente" or (t["etat"] == "rouge" and perime(t)) for t in travaux.values())
        return "attendre" if en_cours else ""
    rouges = {n for n, t in travaux.items() if t["etat"] == "rouge" and n != agregat}
    if rouges != {TRAVAIL_CHRONOMETRE}:
        return ""
    if agregat not in travaux or any(t["etat"] == "attente" for t in travaux.values()):
        return "attendre"
    return "rejouer"


# Un travail de CI tombé avant d'avoir rien contrôlé (un téléchargement, une
# installation, le checkout) n'a rien dit du lot. Le pilote le rejoue
# lui-même, sans compter d'essai, `PANNES_MAX` fois au plus depuis le dernier
# passage du meneur ; au-delà, le lot se bloque en nommant l'étape.
ETAT_REJEU_PANNE = "rejeu_panne"
PANNES_MAX = 3
# Le nom que GitHub donne aux étapes qui préparent un travail : celles d'une
# action (`uses:`), les siennes (« Set up job »…), et nos installations.
_ETAPE_D_INFRASTRUCTURE = re.compile(
    r"^(Set up job|Complete job|Post |Run actions/|Install |Run (python3?|py) -m pip install)", re.IGNORECASE)


def panne_d_infrastructure(etapes: list[dict]) -> str:
    """Le nom de l'étape en panne quand un travail rouge est tombé en se
    préparant, « » quand c'est un contrôle qui a échoué ou qu'on ne sait pas.
    Seule la première étape en échec compte : les suivantes sont sautées."""
    rouge = next((e for e in etapes if e.get("conclusion") == "failure"), None)
    nom = (rouge or {}).get("name") or ""
    return nom if _ETAPE_D_INFRASTRUCTURE.match(nom) else ""


def rejeux_de_panne(liste: list[dict]) -> list[dict]:
    """Les marques « rejeu_panne » du pilote depuis le dernier passage du meneur."""
    return [m for m in _depuis_le_dernier_passage(liste)
            if m.get("role") == "pilote" and m.get("etat") == ETAT_REJEU_PANNE]


def rejeu_de_panne_en_vol(dates_des_rouges: Iterable[str], en_cours: bool, rejeux: list[dict],
                          heures_depuis_rejeu: float | None = None) -> str:
    """Ce que le pilote fait d'une CI rouge après avoir rejoué une panne.

    « attendre » : le rejeu tourne, ou n'est pas encore parti (un rouge
    d'avant lui est périmé). « abandonner » : il n'a rien rendu en
    `HEURES_REJEU` heures, le lot reprend son chemin ordinaire. « » : pas de
    rejeu en vol ; les rouges sont ceux d'aujourd'hui, à regarder."""
    if not rejeux:
        return ""
    quand = _instant(rejeux[-1].get("quand") or "")

    def perime(date: str) -> bool:
        parti = _instant(date)
        return quand is not None and (parti is None or parti < quand)

    if not (en_cours or any(perime(d) for d in dates_des_rouges)):
        return ""
    if heures_depuis_rejeu is not None and heures_depuis_rejeu > HEURES_REJEU:
        return "abandonner"
    return "attendre"


# Un rouge que la base de la PR portait déjà n'est pas au lot.
ETAT_BASE_ROUGE = "base_rouge"


def rouge_de_la_base(rouges: set[str], base: dict[str, str], master: dict[str, str]) -> str:
    """Ce que fait le pilote d'une CI rouge dont la base est peut-être en cause.

    `rouges` : les travaux rouges de la PR, sans l'agrégat ; `base` et
    `master` : l'état des travaux du commit d'où part la PR et de la tête de
    master. « » : un des rouges est au lot, le meneur corrige. « attendre » :
    master porte encore ce rouge, ou n'a pas fini de le jouer ; le lot ne
    compte pas d'essai. « fusionner » : master l'a guéri depuis, la branche le
    reçoit."""
    if not rouges or not rouges <= {n for n, e in base.items() if e == "rouge"}:
        return ""
    if any(master.get(n) != "vert" for n in rouges):
        return "attendre"
    return "fusionner"


@dataclass(frozen=True)
class Question:
    """Ce que le meneur demande quand le lot exige une décision qu'il n'a pas
    le droit de prendre : la question, deux à quatre réponses avec ce
    qu'elles coûtent, et sa recommandation."""

    texte: str
    options: tuple[tuple[str, str, str], ...] = ()  # (lettre, réponse, ce qu'elle coûte)
    recommandation: tuple[str, str] | None = None    # (lettre, pourquoi)

    @classmethod
    def de(cls, lu: dict | None) -> "Question | None":
        """La question, lue dans la sortie d'un agent ou dans une marque."""
        if not isinstance(lu, dict) or not (lu.get("texte") or lu.get("question")):
            return None
        options = tuple((str(o.get("lettre", "")).strip().upper(), str(o.get("reponse", "")).strip(),
                         str(o.get("cout", "")).strip())
                        for o in lu.get("options") or [] if isinstance(o, dict) and o.get("lettre"))
        reco = lu.get("recommandation") if isinstance(lu.get("recommandation"), dict) else None
        lettre = str((reco or {}).get("lettre", "")).strip().upper()
        return cls(texte=str(lu.get("texte") or lu.get("question")).strip(), options=options,
                   recommandation=(lettre, str(reco.get("pourquoi", "")).strip())
                   if lettre and lettre in {o[0] for o in options} else None)

    def marque(self) -> dict:
        return {"question": self.texte,
                "options": [{"lettre": l, "reponse": r, "cout": c} for l, r, c in self.options],
                "recommandation": ({"lettre": self.recommandation[0], "pourquoi": self.recommandation[1]}
                                   if self.recommandation else None)}

    def reponse(self, lettre: str) -> str:
        return next((r for l, r, _ in self.options if l == lettre.strip().upper()), "")

    def en_clair(self) -> str:
        lignes = [f"**{self.texte}**"] + [f"- **{l}** — {r}" + (f" ({c})" if c else "") for l, r, c in self.options]
        if self.recommandation:
            lignes.append(f"Recommandation : **{self.recommandation[0]}**"
                          + (f" — {self.recommandation[1]}" if self.recommandation[1] else ""))
        return "\n".join(lignes)


def dernier_blocage(commentaires: list[dict]) -> tuple[int, dict] | None:
    """Le rang et la marque du dernier blocage du lot."""
    liste = marques(commentaires)
    rang = max((i for i, m in enumerate(liste) if m.get("etat") == BLOQUE), default=None)
    return None if rang is None else (rang, liste[rang])


def deblocage_a_faire(commentaires: list[dict]) -> bool:
    """Le CTO doit-il regarder ce lot bloqué ? Oui si son dernier blocage
    n'est pas le sien (il ne se relit pas), et qu'il n'a rien dit depuis."""
    trouve = dernier_blocage(commentaires)
    if trouve is None:
        return False
    rang, blocage = trouve
    if blocage.get("par") == CTO:
        return False
    return not any(m.get("role") == CTO for m in marques(commentaires)[rang + 1:])


def relances_du_cto(commentaires: list[dict]) -> int:
    """Combien de fois le CTO a déjà relancé ce lot."""
    return sum(1 for m in marques(commentaires) if m.get("role") == CTO and m.get("etat") == DECISION
               and m.get("decision") == "relancer")


def reponse_apres_blocage(commentaires: list[dict], proprietaire: str) -> bool:
    """Le propriétaire a-t-il écrit sur l'issue depuis son dernier blocage ?
    Ce commentaire vaut réponse : le pilote remet le lot en route. Les
    commentaires du pilote (marqués) et ceux d'un autre compte ne comptent pas."""
    dernier = None
    for i, c in enumerate(commentaires or []):
        if any(m.get("etat") == BLOQUE for m in marques([c])):
            dernier = i
    if dernier is None:
        return False
    return any(ecrit_par_le_proprietaire(c, proprietaire) for c in commentaires[dernier + 1:])


def ecrit_par_le_proprietaire(c: dict, proprietaire: str) -> bool:
    """Ce commentaire est-il la parole du propriétaire ? Il porte son compte,
    et pas de marque (le pilote écrit sous le même compte, mais il marque ce
    qu'il écrit). Le dépôt est public : ce qu'un autre compte écrit sur une
    issue n'est ni une réponse, ni une consigne, ni un accord, et n'arrive
    jamais à un agent."""
    corps = (c.get("body") or "").strip()
    auteur = ((c.get("author") or {}).get("login") or "").lower()
    return bool(corps) and "<!-- atelier" not in corps and bool(proprietaire) and auteur == proprietaire.lower()


def decisions_du_lot(commentaires: list[dict], proprietaire: str) -> list[str]:
    """Ce qui a été décidé sur ce lot, en entier : chaque décision du CTO
    avec ses raisons et ses bornes, et tout ce que le propriétaire a écrit sur
    l'issue. Rien ne les efface, ni un blocage ni une reprise : le meneur et
    le relecteur les reçoivent à chaque passage, comme une consigne qui prime
    sur la fiche là où elle la contredit."""
    decisions: list[str] = []
    for c in commentaires or []:
        faites = marques([c])
        for m in faites:
            if m.get("role") != CTO or m.get("etat") != DECISION:
                continue
            quoi = {"relancer": "Le CTO a relancé le lot", "trancher": "Le CTO a tranché",
                    "reporter": "Le CTO a reporté le lot"}.get(m.get("decision"), "")
            if not quoi:
                continue
            morceaux = [quoi]
            if m.get("question"):
                morceaux.append(f"Question : {m['question']}")
            if m.get("reponse"):
                morceaux.append(f"Réponse : {m['reponse']}")
            if m.get("consigne"):
                morceaux.append(f"Consigne : {m['consigne']}")
            if m.get("pourquoi"):
                morceaux.append(f"Pourquoi : {m['pourquoi']}")
            if m.get("bornes"):
                morceaux.append(f"Bornes : {m['bornes']}")
            decisions.append(". ".join(x.rstrip(". ") for x in morceaux) + ".")
        if not faites and ecrit_par_le_proprietaire(c, proprietaire):
            decisions.append(f"Le propriétaire a écrit sur l'issue : {(c.get('body') or '').strip()[:3000]}")
    return decisions


def tests_changes(noms_et_etats: Iterable[tuple[str, str]]) -> list[str]:
    """Les fichiers de test qu'un lot modifie ou retire, d'après `git diff
    --name-status` : ceux-là doivent figurer, avec leur raison, dans la section
    « Tests changés » de la PR. Un fichier de test ajouté n'y figure pas."""
    return sorted(nom for etat, nom in noms_et_etats
                  if etat[:1] in "MDR" and re.search(r"(^|/)tests?/|(^|/)test_[^/]+\.py$|Tests?\.cs$", nom, re.I))
