"""L'histoire de la chaîne : ce qui est entré, quand, et combien de temps ça a mis.

Le registre dit *où en est* chaque lot. Il ne dit pas *depuis combien de
temps*, ni *à quelle allure* la chaîne avance, ni *où* elle est lente.
Ces trois-là ne s'écrivent nulle part : ils se dérivent des propositions
fermées — leur branche, leur date d'ouverture, leur date de fusion — et
d'aucun compteur tenu à la main (règle 3, mode de défaillance n°5).

La branche est la couture. Un lot traverse la chaîne sous trois noms
successifs, et chacun date une étape :

    feuille/NNN-…   fusionnée : la fiche est entrée au registre
    brief/NNN-…     fusionnée : le bon de travail est sur la base
    agent/NNN-…     ouverte    : le code est écrit
                    approuvée  : un tiers l'a relu
                    fusionnée  : le lot est livré

D'où le temps de traversée et sa décomposition. Un lot dont une étape
n'a pas de date — le registre était encore édité à la main — sort de
l'échantillon de cette étape-là, et la taille de l'échantillon accompagne
chaque médiane : c'est ce qui empêche de lire « deux jours » sans voir
que c'est deux jours sur un seul lot.

Ce module ne parle pas à GitHub et ne lit pas le registre. Il reçoit des
propositions déjà lues et rend des nombres.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import re

from .mesure import NON_CALCULE, Mesure, PAS_ENCORE, mediane

# Les trois postes, tels que les préfixes de branche les nomment. La
# liste des préfixes intégrés vit dans `atelier.toml` ; ceux-ci sont les
# seuls qui **datent une étape**, et ce n'est pas la même chose : une
# branche d'expérience entre parfois dans la base sans être un lot.
FEUILLE = "feuille/"
BRIEF = "brief/"
CODE = "agent/"

_LOT = re.compile(r"^(?:agent|brief|feuille)/(?P<lot>\d{3}(?:-(?:bis|ter))?)(?:-|$)")

SEMAINE = timedelta(days=7)

# Ce que GitHub appelle un contrôle qui est passé. Le mot vient de lui :
# le journal **rapporte** ce que GitHub a dit d'un contrôle, il ne le
# retraduit pas. La lecture qui gouverne une fusion vit ailleurs
# (`integration.etat_du_controle`) et elle est plus sévère — pour elle un
# `neutral` n'est pas un vert, parce qu'un contrôle requis qui ne s'est
# pas joué n'a rien prouvé. Les deux lectures sont justes, chacune à sa
# place ; les confondre ferait dire au journal qu'un robot d'analyse a
# mis une PR en échec.
PASSE = "success"
# Un contrôle qui tourne encore, et un contrôle terminé dont GitHub ne
# nomme pas la conclusion. Ni l'un ni l'autre n'est un vert, et aucun des
# deux ne se déguise en échec.
EN_COURS = "en cours"
SANS_MOT = "sans conclusion"


def conclusion(statut: str, mot: str | None) -> str:
    """Le mot de GitHub pour un contrôle, tel qu'il sera rapporté."""
    if statut != "completed":
        return EN_COURS
    return mot or SANS_MOT

# Les quatre attentes que la traversée décompose, dans l'ordre où un lot
# les subit. Le libellé vit ici : la page le reprend, elle ne le réécrit
# pas.
ETAPES = (
    ("attente_du_bon", "attente du bon de travail"),
    ("ecriture", "écriture du code"),
    ("attente_relecture", "attente de relecture"),
    ("attente_integration", "attente d'intégration"),
)


def lot_de_la_branche(branche: str) -> str | None:
    """Le numéro de lot que porte une branche, ou rien.

    Rien, et non une chaîne vide : une branche d'expérience ne porte
    aucun lot, et lui en inventer un ferait entrer du bruit dans toutes
    les mesures qui suivent.
    """
    trouve = _LOT.match(branche or "")
    return trouve.group("lot") if trouve else None


@dataclass(frozen=True)
class Proposition:
    """Une proposition fermée, telle que le journal la montre.

    `relecteurs` sont les connexions qui ont approuvé ; `auteurs` celles
    qui ont écrit les commits. Deux ensembles disjoints, c'est la règle
    de rôle tenue ; un recouvrement, c'est ce que la page doit dire.
    """

    numero: int
    titre: str
    branche: str
    auteurs: tuple[str, ...] = ()
    relecteurs: tuple[str, ...] = ()
    ouverte: datetime | None = None
    fermee: datetime | None = None
    fusionnee: datetime | None = None
    approuvee: datetime | None = None
    # (nom, conclusion) telle que GitHub la rend : `success`,
    # `neutral`, `failure`, `en cours`… Le mot est le sien.
    controles: tuple[tuple[str, str], ...] = ()
    mot_de_la_fin: str = ""
    lien: str = ""

    @property
    def lot(self) -> str | None:
        return lot_de_la_branche(self.branche)

    @property
    def poste(self) -> str | None:
        for prefixe in (FEUILLE, BRIEF, CODE):
            if self.branche.startswith(prefixe):
                return prefixe
        return None

    @property
    def duree(self) -> float:
        """Secondes entre l'ouverture et la fusion. `NON_CALCULE` sinon."""
        if self.ouverte is None or self.fusionnee is None:
            return NON_CALCULE
        return max(0.0, (self.fusionnee - self.ouverte).total_seconds())

    @property
    def verts(self) -> tuple[str, ...]:
        """Les contrôles que GitHub a conclus « passés »."""
        return tuple(nom for nom, conclusion in self.controles if conclusion == PASSE)

    @property
    def non_verts(self) -> tuple[tuple[str, str], ...]:
        """Les autres, avec le mot que GitHub emploie pour chacun."""
        return tuple((nom, c) for nom, c in self.controles if c != PASSE)

    @property
    def relue_par_un_tiers(self) -> bool:
        """Deux connexions différentes, celle qui écrit et celle qui juge."""
        auteurs = {a.lower() for a in self.auteurs if a}
        return any(r and r.lower() not in auteurs for r in self.relecteurs)


# ------------------------------------------------------------- vélocité


@dataclass(frozen=True)
class Semaine:
    """Une semaine du calendrier de la chaîne, et ce qu'elle a livré."""

    debut: datetime
    fin: datetime
    lots: tuple[str, ...]

    @property
    def compte(self) -> int:
        return len(self.lots)


def livraisons(propositions) -> tuple[Proposition, ...]:
    """Les propositions qui ont livré un lot : `agent/NNN-…` fusionnée."""
    return tuple(
        p for p in propositions
        if p.branche.startswith(CODE) and p.fusionnee is not None and p.lot
    )


def velocite(propositions, fin: datetime, semaines: int) -> tuple[Semaine, ...]:
    """Les lots livrés par semaine, de la plus ancienne à la plus récente.

    Un échantillon sans aucune livraison **échoue** : zéro lot par
    semaine serait un chiffre, et ce chiffre dirait « la chaîne n'a rien
    livré » là où la vérité est « on n'a rien lu qui permette de le dire »
    (mode de défaillance n°6). Une semaine vide **dans** un échantillon
    qui porte des livraisons, elle, est une vraie mesure : c'est une
    semaine où rien n'est entré.
    """
    if semaines <= 0:
        raise ValueError("une vélocité se mesure sur au moins une semaine")
    livrees = livraisons(propositions)
    if not livrees:
        raise ValueError(
            "aucun lot livré dans l'échantillon : la vélocité n'est pas mesurable, "
            "et zéro par semaine serait une mesure inventée"
        )
    tranches: list[Semaine] = []
    for rang in range(semaines - 1, -1, -1):
        borne_fin = fin - rang * SEMAINE
        borne_debut = borne_fin - SEMAINE
        dedans = sorted(
            p.lot for p in livrees if borne_debut < p.fusionnee <= borne_fin
        )
        tranches.append(Semaine(borne_debut, borne_fin, tuple(dedans)))
    return tuple(tranches)


# --------------------------------------------------------- la traversée


@dataclass(frozen=True)
class Parcours:
    """Les cinq dates d'un lot livré. Chacune peut manquer, aucune ne s'invente."""

    lot: str
    entree: datetime | None
    brief_livre: datetime | None
    code_ouvert: datetime | None
    approuve: datetime | None
    livre: datetime | None

    def _ecart(self, debut: datetime | None, fin: datetime | None) -> float | None:
        if debut is None or fin is None or fin < debut:
            return None
        return (fin - debut).total_seconds()

    @property
    def total(self) -> float | None:
        return self._ecart(self.entree, self.livre)

    @property
    def attente_du_bon(self) -> float | None:
        return self._ecart(self.entree, self.brief_livre)

    @property
    def ecriture(self) -> float | None:
        return self._ecart(self.brief_livre, self.code_ouvert)

    @property
    def attente_relecture(self) -> float | None:
        return self._ecart(self.code_ouvert, self.approuve)

    @property
    def attente_integration(self) -> float | None:
        return self._ecart(self.approuve, self.livre)


def _premiere(propositions, prefixe: str, lot: str, champ: str) -> datetime | None:
    """La date la plus ancienne de ce champ, parmi les branches de ce poste.

    La plus ancienne : un lot repassé deux fois par le même poste — un
    brief réécrit — a commencé la première fois.
    """
    dates = [
        getattr(p, champ)
        for p in propositions
        if p.branche.startswith(prefixe) and p.lot == lot and getattr(p, champ) is not None
    ]
    return min(dates) if dates else None


def parcours(propositions) -> tuple[Parcours, ...]:
    """Le chemin de chaque lot livré, daté étape par étape."""
    resultat: list[Parcours] = []
    for livraison in sorted(livraisons(propositions), key=lambda p: p.lot):
        lot = livraison.lot
        resultat.append(
            Parcours(
                lot=lot,
                entree=_premiere(propositions, FEUILLE, lot, "fusionnee"),
                brief_livre=_premiere(propositions, BRIEF, lot, "fusionnee"),
                code_ouvert=livraison.ouverte,
                approuve=livraison.approuvee,
                livre=livraison.fusionnee,
            )
        )
    return tuple(resultat)


@dataclass(frozen=True)
class Traversee:
    """Le temps qu'un lot met à traverser la chaîne, et où il l'a passé."""

    total: Mesure
    attente_du_bon: Mesure
    ecriture: Mesure
    attente_relecture: Mesure
    attente_integration: Mesure

    @property
    def mesurable(self) -> bool:
        return any(
            getattr(self, nom).connue for nom, _ in ETAPES
        ) or self.total.connue

    @property
    def plus_lente(self) -> tuple[str, Mesure] | None:
        """L'étape qui coûte le plus de temps — celle qu'il faut regarder."""
        connues = [(libelle, getattr(self, nom)) for nom, libelle in ETAPES
                   if getattr(self, nom).connue]
        return max(connues, key=lambda paire: paire[1].valeur) if connues else None


def traversee(chemins) -> Traversee:
    """Les médianes de chaque étape. Une étape sans échantillon reste inconnue."""
    chemins = tuple(chemins)

    def _mediane(champ: str) -> Mesure:
        valeurs = [getattr(c, champ) for c in chemins]
        return mediane([v for v in valeurs if v is not None])

    return Traversee(
        total=_mediane("total"),
        attente_du_bon=_mediane("attente_du_bon"),
        ecriture=_mediane("ecriture"),
        attente_relecture=_mediane("attente_relecture"),
        attente_integration=_mediane("attente_integration"),
    )


# ------------------------------------------------------------- les âges


def entree_dans_l_etat(propositions, fiche) -> datetime | None:
    """Quand la fiche a pris son état courant, si une fusion peut le dater.

    Ce n'est pas une déduction : chaque état d'une fiche est écrit par la
    fusion d'une proposition nommée, et c'est cette fusion-là qu'on date.
    `a-briefer` vient de la proposition de feuille, `pret` de celle du
    brief, `livre` de celle du lot. Les autres états n'ont pas de
    proposition qui les porte : ils restent sans date, et la page le dit.
    """
    prefixe = {"a-briefer": FEUILLE, "pret": BRIEF, "livre": CODE}.get(fiche.etat)
    if prefixe is None:
        return None
    return _premiere(propositions, prefixe, fiche.numero, "fusionnee")


def age(propositions, fiche, maintenant: datetime) -> float:
    """Depuis combien de secondes la fiche porte son état. `NON_CALCULE` sinon."""
    debut = entree_dans_l_etat(propositions, fiche)
    if debut is None:
        return NON_CALCULE
    return max(0.0, (maintenant - debut).total_seconds())


# ---------------------------------------------- ce qu'on déduit, et le dire


@dataclass(frozen=True)
class Deduction:
    """Un fait qu'on n'a pas mesuré, mais qu'on infère — et qui se nomme.

    Les cartes de l'atelier vivent sur le serveur du propriétaire ; la
    page ne les voit pas. Elle peut inférer qu'un codeur a commencé —
    une branche `agent/NNN-…` poussée sans proposition ouverte — mais
    une inférence n'est pas une mesure, et la confondre avec une mesure
    est exactement la règle 10 prise à l'envers.
    """

    texte: str
    sur_quoi: str


def travaux_commences(branches, branches_ouvertes) -> tuple[Deduction, ...]:
    """Les branches de code poussées sans proposition ouverte sur elles.

    `branches` : les noms des branches distantes. `branches_ouvertes` :
    celles qui portent déjà une proposition ouverte — celles-là sont
    visibles dans le registre, et les compter ici donnerait deux agents
    là où il n'y en a qu'un.

    La comparaison porte sur la **branche**, pas sur le lot : un lot dont
    le brief est en proposition et dont la branche de code existe déjà,
    c'est justement le cas qu'on cherche à voir — quelqu'un a commencé à
    coder pendant que le brief attendait.
    """
    ouvertes = set(branches_ouvertes)
    vus: list[Deduction] = []
    for branche in sorted(set(branches)):
        if not branche.startswith(CODE) or branche in ouvertes:
            continue
        lot = lot_de_la_branche(branche)
        if lot is None:
            continue
        vus.append(
            Deduction(
                f"un codeur a commencé le lot {lot} : la branche « {branche} » existe, "
                "sans proposition ouverte",
                branche,
            )
        )
    return tuple(vus)
