"""La santé de la chaîne : est-ce qu'elle tourne, ou est-ce qu'elle tourne à vide ?

Ce module existe à cause d'une panne datée. Entre le 5 et le 7 septembre
2026, l'intégration s'est réveillée quarante fois et a répondu `RIEN`
quarante fois : trois bons de travail attendaient un contrôle `relecture`
qui ne pouvait pas exister, parce que le travail qui le pose mourait
avant. Rien n'était rouge. Le journal de chaque tour le disait, et
personne ne lit quarante journaux. La chaîne était arrêtée depuis sa mise
en place et elle avait l'air de tourner.

Un tour à vide est normal. Quarante à la suite ne le sont pas, et c'est
la seule différence qu'il fallait rendre visible. D'où la mesure de ce
module : **combien de tours d'intégration se sont réveillés depuis la
dernière fusion**. Elle se dérive de deux dates — le démarrage de chaque
exécution, et la fusion la plus récente — et d'aucun compteur tenu à la
main (règle 3).

Le seuil au-delà duquel ce nombre devient une alerte ne vit pas ici : il
est déclaré dans `atelier.toml` § `[tableau]`. Un seuil écrit dans le
code est un réglage qu'on ne relit jamais, et celui-ci décide de ce que
le propriétaire voit en premier.

Ce module ne parle pas à GitHub : il reçoit des dates et des lectures
déjà faites, et rend un état. C'est ce qui permet de l'éprouver hors
ligne — un contrôle qu'on ne peut pas jouer hors ligne est un contrôle
qu'on ne joue pas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .mesure import INCONNU, Lecture

# Ce que GitHub appelle une protection qui exige des contrôles. Le nom du
# champ vit ici, une fois : c'est la couture où une clé mal orthographiée
# ferait passer une protection présente pour une protection absente.
CHAMP_CONTROLES = "required_status_checks"
CHAMP_CONTEXTES = "contexts"
CHAMP_ADMINS = "enforce_admins"
CHAMP_CONSTRUCTION = "build_type"
CONSTRUCTION_ACTIONS = "workflow"


@dataclass(frozen=True)
class Reveil:
    """Une exécution de l'intégration, telle que son historique la rend."""

    moment: datetime
    conclusion: str
    lien: str


@dataclass(frozen=True)
class Rouge:
    """La dernière exécution rouge d'un travail, et où la regarder."""

    travail: str
    moment: datetime
    lien: str


@dataclass(frozen=True)
class Sante:
    """L'état de la chaîne à un instant, tel que la page le montre.

    `seuil` voyage avec la mesure plutôt que d'être relu au moment de
    l'affichage : c'est ce qui garantit que l'alerte affichée et le
    nombre affiché parlent du même réglage.
    """

    tours_sans_fusion: int
    seuil: int
    derniere_fusion: datetime | None
    dernier_reveil: Reveil | None
    requis: tuple[str, ...]
    obligatoires: Lecture
    admins_soumis: Lecture
    pages: Lecture
    rouges: tuple[Rouge, ...]

    @property
    def alerte(self) -> bool:
        """La chaîne tourne-t-elle à vide depuis trop longtemps ?

        Le seuil vient du branchement. S'il était écrit ici, changer le
        réglage demanderait un commit dans `outils/` — et personne ne
        change un réglage qui demande un commit.
        """
        return self.tours_sans_fusion >= self.seuil

    @property
    def jamais_fusionne(self) -> bool:
        return self.derniere_fusion is None


def tours_sans_fusion(demarrages, derniere_fusion: datetime | None) -> int:
    """Combien de tours d'intégration se sont réveillés depuis la dernière fusion.

    `demarrages` : la date de démarrage de chaque exécution du travail
    `integration`, dans n'importe quel ordre. Un échantillon vide
    **échoue** : une chaîne dont on n'a lu aucune exécution n'est pas une
    chaîne dont zéro tour a tourné à vide (règle 9, mode de défaillance
    n°6).
    """
    dates = [d for d in demarrages if d is not None]
    if not dates:
        raise ValueError(
            "aucune exécution de l'intégration n'a été lue : le nombre de tours "
            "à vide n'est pas mesurable, et zéro serait un mensonge"
        )
    if derniere_fusion is None:
        # Rien n'a jamais été fusionné : tous les tours lus ont tourné à
        # vide, et c'est la mesure la plus franche qu'on puisse rendre.
        return len(dates)
    return sum(1 for d in dates if d > derniere_fusion)


def dernier_reveil(reveils) -> Reveil | None:
    """Le réveil le plus récent, ou rien si l'historique est vide."""
    connus = [r for r in reveils if r is not None]
    return max(connus, key=lambda r: r.moment) if connus else None


def controles_obligatoires(protection: Lecture) -> Lecture:
    """Ce que GitHub exige réellement sur la branche de base.

    Une lecture refusée reste refusée : le jeton d'Actions n'est pas
    administrateur, et l'API répond alors 403 sur la protection. Traduire
    ce refus en « aucun contrôle obligatoire » afficherait une porte
    grande ouverte là où elle est peut-être fermée à clé.
    """
    if not protection.connue:
        return protection
    brut = protection.valeur or {}
    bloc = brut.get(CHAMP_CONTROLES) or {}
    contextes = bloc.get(CHAMP_CONTEXTES)
    if contextes is None:
        # La protection existe mais n'exige aucun contrôle : c'est un
        # « non » mesuré, pas un inconnu.
        return Lecture.sue(())
    return Lecture.sue(tuple(str(c) for c in contextes))


def admins_soumis(protection: Lecture) -> Lecture:
    """La protection s'applique-t-elle aussi au propriétaire ?"""
    if not protection.connue:
        return protection
    brut = protection.valeur or {}
    bloc = brut.get(CHAMP_ADMINS)
    if bloc is None:
        return Lecture.sue(False)
    if isinstance(bloc, dict):
        return Lecture.sue(bool(bloc.get("enabled")))
    return Lecture.sue(bool(bloc))


def manquants(requis, obligatoires: Lecture) -> Lecture:
    """Les contrôles déclarés que GitHub n'exige pas — ou l'aveu qu'on ne sait pas."""
    if not obligatoires.connue:
        return obligatoires
    poses = set(obligatoires.valeur or ())
    return Lecture.sue(tuple(nom for nom in requis if nom not in poses))


def publication(pages: Lecture) -> Lecture:
    """La page est-elle publiée par Actions, ou seulement écrite ?

    Un 404 est un « non » mesuré : GitHub dit que Pages n'existe pas sur
    ce dépôt. Toute autre erreur est un inconnu — c'est la distinction
    que `pages.sh` fait déjà côté geste, et les deux la font pareil.
    """
    if not pages.connue:
        return pages
    brut = pages.valeur
    if brut is None:
        return Lecture.sue(False)
    return Lecture.sue((brut or {}).get(CHAMP_CONSTRUCTION) == CONSTRUCTION_ACTIONS)


def mot(lecture: Lecture, oui: str, non: str) -> str:
    """Trois mots possibles, jamais deux : oui, non, ou `inconnu`."""
    if not lecture.connue:
        return INCONNU
    return oui if lecture.valeur else non
