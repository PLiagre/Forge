"""Ce qui demande une décision maintenant.

Le bloc de tête de la page, et le seul qui ait le droit d'être vide. Tout
ce qui est ici attend quelqu'un : personne d'autre ne le débloquera, et
tant que ça attend, la chaîne n'avance pas.

Deux règles gouvernent ce module, et elles sont la même vue de deux côtés :

- **il ne décide rien.** La cause qui retient une proposition est celle
  que `integration.examiner` rend, mot pour mot. La page ne la reformule
  pas, ne la résume pas, ne la traduit pas. Une présentation qui
  reformule finit par dire autre chose que ce que la machine fait, et
  c'est le mode de défaillance n°4 du dépôt ;
- **il porte une durée sur chaque ligne.** « Une proposition attend » ne
  dit rien ; « une proposition attend depuis six jours » dit tout. C'est
  la seule information que le registre ne porte pas et que le
  propriétaire ne peut obtenir qu'en ouvrant GitHub.

Ce module ne parle ni à GitHub ni au registre : il reçoit des décisions
déjà prises et des fiches déjà lues.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from . import integration, palier
from .mesure import instant, jours

# Les catégories, dans l'ordre où elles passent. L'ordre est
# l'information : ce qui bloque une fusion précède ce qui bloque un
# départ, qui précède ce qui vieillit tout seul.
CONFLIT = "conflit avec la base"
RETENUE = "proposition retenue"
BASE_ROUGE = "contrôle rouge sur la base"
LOT_BLOQUE = "lot prêt, dépendance non livrée"
PALIER_DU = "palier dû"
BROUILLON = "brouillon oublié"

RANGS = (CONFLIT, BASE_ROUGE, RETENUE, LOT_BLOQUE, PALIER_DU, BROUILLON)


@dataclass(frozen=True)
class Alerte:
    """Une chose qui attend, sa cause exacte, et depuis quand."""

    quoi: str
    texte: str
    depuis: datetime | None
    lien: str = ""

    @property
    def rang(self) -> int:
        return RANGS.index(self.quoi) if self.quoi in RANGS else len(RANGS)


# Une date qui n'existe pas ne se compare pas : les lignes sans durée
# passent après les autres, et se départagent sur leur texte. Ce repère
# n'est jamais affiché, il ne sert qu'à ranger.
_JAMAIS = datetime.min.replace(tzinfo=timezone.utc)


def _tri(alerte: Alerte) -> tuple:
    """Par catégorie, puis la plus vieille d'abord ; sans date, à la fin."""
    return (alerte.rang, alerte.depuis is None, alerte.depuis or _JAMAIS, alerte.texte)


def _propositions(examens, prefixes, brouillon_jours, maintenant, depot) -> list[Alerte]:
    alertes: list[Alerte] = []
    for pr, decision in examens:
        ouverte = instant(pr.ouverte)
        lien = f"https://github.com/{depot}/pull/{pr.numero}" if depot else ""
        if pr.brouillon:
            if ouverte is not None and maintenant - ouverte > jours(brouillon_jours):
                alertes.append(Alerte(
                    BROUILLON,
                    f"#{pr.numero} « {pr.titre or pr.branche} » est en brouillon : "
                    "la chaîne ne regarde pas les brouillons",
                    ouverte, lien,
                ))
            continue
        if not integration.integree(pr.branche, prefixes):
            continue  # une expérience attend le propriétaire, pas la chaîne
        if pr.fusionnable is False:
            alertes.append(Alerte(
                CONFLIT,
                f"#{pr.numero} ({pr.branche}) : {decision.raison}",
                ouverte, lien,
            ))
            continue
        if decision.action == integration.RIEN:
            alertes.append(Alerte(
                RETENUE,
                f"#{pr.numero} ({pr.branche}) : {decision.raison}",
                ouverte, lien,
            ))
    return alertes


def _lots_bloques(fiches, depot) -> list[Alerte]:
    par_numero = {f.numero: f for f in fiches}
    alertes: list[Alerte] = []
    for fiche in fiches:
        if fiche.etat != "pret":
            continue
        for dep in fiche.depend_de:
            attendue = par_numero.get(dep)
            if attendue is None:
                alertes.append(Alerte(
                    LOT_BLOQUE,
                    f"le lot {fiche.numero} dépend du lot {dep}, qui n'a aucune fiche",
                    None, "",
                ))
            elif attendue.etat not in palier.LIVRES:
                alertes.append(Alerte(
                    LOT_BLOQUE,
                    f"le lot {fiche.numero} est prêt mais dépend du lot {dep}, "
                    f"qui est « {attendue.etat} »",
                    None, "",
                ))
    return alertes


def _paliers(etapes, depot) -> list[Alerte]:
    alertes: list[Alerte] = []
    for etape in etapes:
        if not etape.due:
            continue
        alertes.append(Alerte(
            PALIER_DU,
            f"la couche {etape.couche} est finie et son palier n'est pas au registre ; "
            f"lots à couvrir : {', '.join(etape.a_couvrir)}",
            None,
            f"https://github.com/{depot}/actions/workflows/integration.yml" if depot else "",
        ))
    return alertes


def _base(controles_base, requis, base, depot) -> list[Alerte]:
    """Les contrôles rouges de la branche de base — ceux qui gouvernent.

    Seulement les contrôles **requis**. La base porte aussi des contrôles
    de tiers, dont beaucoup se concluent `neutral` : la règle du dépôt
    les compte rouges, et c'est juste pour un contrôle requis — un
    contrôle qui ne s'est pas joué n'a rien prouvé. Mais une ligne rouge
    permanente sur un robot qui ne gouverne rien noierait les vraies, et
    un bloc de tête qu'on n'ouvre plus ne sert plus à rien. La liste des
    requis vient du branchement, pas d'une liste d'exclusions écrite ici.
    """
    gouvernants = set(requis)
    rouges = [
        nom for nom, statut, conclusion in controles_base
        if nom in gouvernants
        and integration.etat_du_controle(statut, conclusion) == integration.ROUGE
    ]
    if not rouges:
        return []
    return [Alerte(
        BASE_ROUGE,
        f"la branche {base} porte {len(rouges)} contrôle(s) requis rouge(s) : "
        f"{', '.join(sorted(set(rouges)))}",
        None,
        f"https://github.com/{depot}/commits/{base}" if depot else "",
    )]


def alertes(
    *,
    examens=(),
    fiches=(),
    controles_base=(),
    requis=(),
    prefixes=(),
    base: str = "master",
    brouillon_jours: float,
    maintenant: datetime,
    depot: str = "",
) -> tuple[Alerte, ...]:
    """Tout ce qui attend une décision, du plus bloquant au plus dormant.

    `brouillon_jours` n'a pas de valeur par défaut : le seuil vit dans
    `atelier.toml`, et un défaut écrit ici serait un réglage que
    personne ne relit.
    """
    trouvees = (
        _propositions(examens, prefixes, brouillon_jours, maintenant, depot)
        + _base(controles_base, requis, base, depot)
        + _lots_bloques(fiches, depot)
        + _paliers(palier.etapes(fiches), depot)
    )
    return tuple(sorted(trouvees, key=_tri))
