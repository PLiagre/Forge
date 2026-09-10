"""Les actions : ce vers quoi la page emmène, et ce que le geste vérifie avant d'agir.

La page est publiée sur GitHub Pages. Elle est statique : elle ne peut ni
appeler l'API, ni porter un jeton, ni écrire quoi que ce soit. Un jeton
publié est un jeton perdu, et un dépôt public n'a pas de dos. Donc une
action n'est jamais un bouton qui fait : c'est **un lien qui emmène**
vers la page GitHub du geste, et **un travail `workflow_dispatch`** qui
le fait côté serveur, avec le jeton d'Actions.

Ce module porte les deux moitiés :

- les **liens**, construits une seule fois ici pour que la page, la
  documentation et les travaux nomment le même endroit ;
- ce que chaque geste **décide avant d'agir**. Une action déclenchée deux
  fois ne fait pas deux fois le geste : le travail relit l'état, et sort
  en disant « déjà fait ». Cette décision-là est du Python, pas du shell,
  pour la même raison que le reste — elle se joue hors ligne.

Aucune de ces décisions ne recalcule ce que l'intégration sait déjà : la
liste des contrôles qui manquent vient de `integration.manque`, la même
fonction que celle qui retient une fusion.
"""

from __future__ import annotations

from dataclasses import dataclass
import urllib.parse

from . import integration

FAIRE = "faire"
RIEN = "RIEN"

GABARIT_DEMANDE = "nouveau-lot.yml"

# Les travaux que la page sait déclencher, et le fichier de chacun. Un
# nom qui changerait d'un côté seulement ferait un lien mort — et un lien
# mort sur un tableau de bord est pire qu'un lien absent : il se clique.
TRAVAIL_INTEGRATION = "integration.yml"
TRAVAIL_CONTROLES = "controles.yml"
TRAVAIL_BROUILLON = "brouillon.yml"
TRAVAIL_ETAT = "etat-lot.yml"

# Reprendre une carte tombée se fait sur le serveur du propriétaire, où
# vivent les cartes. La page ne peut pas le faire ; elle peut dire quoi
# taper, et c'est tout ce qu'elle prétend faire.
REPRISE = "py -m atelier feuille etat --projet ."


@dataclass(frozen=True)
class Action:
    """Ce que le propriétaire peut déclencher, et où ça se déclenche."""

    titre: str
    quoi: str
    lien: str
    entree: str = ""


@dataclass(frozen=True)
class Geste:
    """Ce qu'un travail fait de son réveil : agir, ou constater que c'est déjà fait."""

    action: str
    raison: str

    @property
    def a_faire(self) -> bool:
        return self.action == FAIRE


# ------------------------------------------------------------- les liens


def _base(depot: str) -> str:
    if not depot or "/" not in depot:
        raise ValueError(f"dépôt attendu sous la forme « proprietaire/nom », reçu « {depot} »")
    return f"https://github.com/{depot}"


def lien_demande(depot: str, couche: str = "") -> str:
    """Le formulaire « Demander un lot », sa couche déjà choisie s'il y en a une.

    `couche` est l'intitulé de l'option, pas le numéro : GitHub remplit
    une liste déroulante par ce qui s'y affiche.
    """
    parametres = {"template": GABARIT_DEMANDE}
    if couche:
        parametres["couche"] = couche
    return f"{_base(depot)}/issues/new?" + urllib.parse.urlencode(parametres)


def lien_travail(depot: str, fichier: str) -> str:
    """La page « Run workflow » d'un travail."""
    return f"{_base(depot)}/actions/workflows/{fichier}"


def lien_proposition(depot: str, numero: int) -> str:
    return f"{_base(depot)}/pull/{numero}"


def lien_branche(depot: str, branche: str) -> str:
    return f"{_base(depot)}/tree/{urllib.parse.quote(branche)}"


def actions(depot: str) -> tuple[Action, ...]:
    """Tout ce que la page sait déclencher, dans l'ordre de sa fréquence."""
    return (
        Action(
            "Demander un lot",
            "Le formulaire écrit la fiche au registre et ouvre sa proposition.",
            lien_demande(depot),
        ),
        Action(
            "Relancer l'intégration",
            "Un tour tout de suite, sans attendre le réveil de l'heure.",
            lien_travail(depot, TRAVAIL_INTEGRATION),
        ),
        Action(
            "Redemander les contrôles d'une proposition",
            "Rejoue tests, security et relecture — le cas d'une proposition "
            "ouverte par la machine, que GitHub refuse de déclencher.",
            lien_travail(depot, TRAVAIL_CONTROLES),
            "le numéro de la proposition",
        ),
        Action(
            "Sortir une proposition du brouillon",
            "Un brouillon n'est pas regardé par la chaîne.",
            lien_travail(depot, TRAVAIL_BROUILLON),
            "le numéro de la proposition",
        ),
        Action(
            "Forcer le dépôt d'un palier",
            "Quand la couche est finie et que le dépôt n'a pas eu lieu.",
            lien_travail(depot, TRAVAIL_INTEGRATION),
            "palier : oui",
        ),
        Action(
            "Changer l'état d'un lot",
            "« abandonne », ou retour à « idee ». Passe par une proposition de "
            "feuille : rien n'est écrit dans la base directement.",
            lien_travail(depot, TRAVAIL_ETAT),
            "le lot, et l'état visé",
        ),
        Action(
            "Reprendre une carte tombée",
            "Se fait sur le serveur du propriétaire, où vivent les cartes. "
            "Cette page ne peut que dire quoi taper : la commande ci-contre dit "
            "par quoi chaque lot est retenu, et « atelier prise » reprend la carte.",
            "",
            REPRISE,
        ),
    )


# ------------------------------------------- ce que chaque geste décide


def redemander_controles(ouverte: bool, brouillon: bool, pr: integration.PR, requis) -> Geste:
    """Faut-il rejouer les contrôles de cette proposition, ou sont-ils là ?

    « Déjà fait » se mesure sur la révision courante : les contrôles
    requis y sont tous présents et aucun n'est rouge. Un contrôle *en
    cours* compte comme présent — le redemander en lancerait un second
    sur la même révision, et deux exécutions concurrentes du même travail
    ne prouvent pas deux fois plus.
    """
    if not ouverte:
        return Geste(RIEN, "la proposition est fermée : il n'y a plus de contrôle à redemander")
    if brouillon:
        return Geste(
            RIEN,
            "la proposition est en brouillon : la sortir du brouillon d'abord, "
            "sinon les contrôles se joueraient pour rien",
        )
    presents = {c.nom for c in pr.controles}
    absents = [nom for nom in requis if nom not in presents]
    rouges = [c.nom for c in pr.controles if c.nom in set(requis) and c.etat == integration.ROUGE]
    if not absents and not rouges:
        return Geste(RIEN, "les contrôles requis sont déjà posés sur cette révision : déjà fait")
    defaut = integration.manque(pr, requis)
    return Geste(FAIRE, defaut or "contrôles à rejouer")


def sortir_du_brouillon(ouverte: bool, brouillon: bool) -> Geste:
    """Faut-il sortir cette proposition du brouillon, ou en est-elle déjà sortie ?"""
    if not ouverte:
        return Geste(RIEN, "la proposition est fermée : un brouillon fermé ne se rouvre pas ici")
    if not brouillon:
        return Geste(RIEN, "la proposition n'est pas en brouillon : déjà fait")
    return Geste(FAIRE, "brouillon : la chaîne ne la regarde pas tant qu'elle en est un")
