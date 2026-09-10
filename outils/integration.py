"""L'intégration : qui entre dans `master`, et à quelle condition.

Elle ne lit ni le brief, ni le diff, ni un avis. Elle lit **la liste des
contrôles requis**, déclarée dans `atelier.toml`, et les vérifie sur la
révision courante de la PR — plus une chose qu'elle vérifie elle-même :
qu'un tiers a approuvé cette révision.

Ce dernier point n'est pas une exception à la règle « elle ne juge pas ».
C'est le contraire : le contrôle `relecture` est posé par un travail qui
tourne **sur le code de la PR**, et une PR peut donc changer le code qui
la juge. Le verdict qui gouverne la fusion se calcule ici, dans le code de
`master`, avec le même module que ce travail-là. Une seule règle, deux
appelants ; l'état posé sur la PR reste ce qui la rend lisible, il n'est
plus ce qui l'ouvre.

Trois refus qui ne sont pas des échecs, seulement des attentes :

- un contrôle **absent** n'est pas un contrôle vert ; un contrôle **en
  cours** non plus ;
- un état de fusion **inconnu** retient : GitHub calcule la
  fusionnabilité en différé, et lire un blanc comme un feu vert serait
  céder exactement quand la sonde ne répond plus ;
- une PR **en retard** sur `master` ne rentre pas telle quelle : elle
  est rejouée sur le dernier `master` d'abord. Les contrôles de la
  révision d'avant n'ont pas vu ce qui a été fusionné depuis.

Le rejeu change la révision, donc périme tout ce qui était posé sur
l'ancienne. C'est pourquoi la relecture se demande **après** : les
contrôles qu'une machine repose toute seule décident du rejeu, et la
relecture — qui coûte un tour d'agent — ne se demande que sur la révision
finale. L'exiger avant, ce serait la payer deux fois, et la deuxième pour
rien.

Et une seule PR avance par tour : l'intégration est séquentielle. Deux
PR vertes séparément ne sont pas une PR verte ensemble.

Ce module ne parle pas à GitHub : il reçoit l'état déjà lu et rend une
décision. C'est ce qui permet de l'éprouver sans compte.
"""

from __future__ import annotations

from dataclasses import dataclass, field

VERT = "vert"
ROUGE = "rouge"
EN_COURS = "en-cours"

FUSIONNER = "fusionner"
REBASER = "rebaser"
RIEN = "rien"


def etat_du_controle(statut: str, conclusion: str | None) -> str:
    """L'état d'un contrôle GitHub, ramené aux trois seuls qui décident.

    Tout ce qui n'est pas `success` et qui est terminé est rouge —
    `skipped` compris. Un contrôle requis qui ne s'est pas joué n'a rien
    prouvé, et le nommer rouge le rend visible ; le compter vert le rend
    inutile.
    """
    if statut != "completed":
        return EN_COURS
    return VERT if conclusion == "success" else ROUGE


@dataclass(frozen=True)
class Controle:
    nom: str
    etat: str


@dataclass(frozen=True)
class PR:
    numero: int
    branche: str
    brouillon: bool
    # `None` quand GitHub n'a pas fini de calculer la fusionnabilité.
    fusionnable: bool | None
    # Le nombre de commits de `master` que cette PR n'a pas encore.
    retard: int
    controles: tuple[Controle, ...] = ()
    # Un tiers a-t-il approuvé la révision courante ? `None` tant qu'on ne
    # l'a pas demandé — et un inconnu retient, comme partout ailleurs.
    relue: bool | None = None
    motif_relecture: str = ""
    revision: str = ""
    # Ce que la décision ne regarde pas, et que la page montre : depuis
    # quand cette proposition attend, et sous quel titre. Les porter ici
    # évite une seconde lecture de la même réponse d'API — et une seconde
    # lecture est une seconde occasion de ne pas lire la même chose.
    ouverte: str = ""
    titre: str = ""


def depuis_github(brut: dict, detail: dict | None = None, controles_bruts=(),
                  retard: int = 0, verdict=None) -> PR:
    """Une PR, telle que l'API la rend. Les noms de champs vivent ici.

    C'est la couture où les défauts se logent — une clé mal orthographiée
    rend un brouillon éveillé ou une PR fusionnable inconnue — et c'est
    pour ça qu'elle est une fonction pure plutôt qu'une suite d'accès
    éparpillés dans la ligne de commande.
    """
    if detail is None:
        return PR(
            numero=brut["number"],
            branche=brut["head"]["ref"],
            brouillon=bool(brut.get("draft")),
            fusionnable=None,
            retard=0,
            ouverte=brut.get("created_at", ""),
            titre=brut.get("title", ""),
        )
    return PR(
        numero=brut["number"],
        branche=brut["head"]["ref"],
        brouillon=bool(brut.get("draft")),
        fusionnable=detail.get("mergeable"),
        retard=retard,
        ouverte=brut.get("created_at", ""),
        titre=brut.get("title", ""),
        revision=detail["head"]["sha"],
        controles=tuple(
            Controle(nom, etat_du_controle(statut, conclusion))
            for nom, statut, conclusion in controles_bruts
        ),
        relue=None if verdict is None else verdict.passe,
        motif_relecture="" if verdict is None else verdict.raison,
    )


@dataclass(frozen=True)
class Decision:
    action: str
    pr: int | None
    raison: str


@dataclass
class Rapport:
    decision: Decision
    lignes: list[str] = field(default_factory=list)


def integree(branche: str, prefixes) -> bool:
    """Cette branche est-elle de celles que l'intégration fusionne ?

    Publique, et appelée partout où la question se pose — la décision,
    la page, la ligne de commande. Le jour où le test change, il change
    une fois : deux copies d'un même prédicat finissent par ne plus
    répondre la même chose, et celle qui se trompe est toujours celle
    qu'on n'a pas relue.
    """
    return any(branche.startswith(p) for p in prefixes)


def manque(pr: PR, noms) -> str:
    """Ce qui empêche ces contrôles-là d'être verts, ou une chaîne vide."""
    par_nom = {c.nom: c for c in pr.controles}
    absents = [nom for nom in noms if nom not in par_nom]
    if absents:
        return f"contrôle absent : {', '.join(absents)}"
    rouges = [nom for nom in noms if par_nom[nom].etat == ROUGE]
    if rouges:
        return f"contrôle rouge : {', '.join(rouges)}"
    en_cours = [nom for nom in noms if par_nom[nom].etat == EN_COURS]
    if en_cours:
        return f"contrôle en cours : {', '.join(en_cours)}"
    return ""


def examiner(pr: PR, requis, prefixes) -> Decision:
    """Ce que cette PR appelle, et pourquoi. Jamais deux choses à la fois."""
    if pr.brouillon:
        return Decision(RIEN, pr.numero, "brouillon")
    if not integree(pr.branche, prefixes):
        return Decision(
            RIEN, pr.numero,
            f"branche « {pr.branche} » hors des préfixes intégrés "
            f"({', '.join(prefixes)}) : c'est le propriétaire qui fusionne celle-là",
        )
    if pr.fusionnable is None:
        return Decision(RIEN, pr.numero, "fusionnabilité inconnue : on retient")
    if not pr.fusionnable:
        return Decision(RIEN, pr.numero, "en conflit avec master")

    # Le rejeu peut acquérir un contrôle qui n'existait pas à la création
    # de la PR. Les contrôles déjà présents doivent toutefois être verts.
    # La fusion, elle, exige toujours la liste entière sur la nouvelle tête.
    presents = {c.nom for c in pr.controles}
    a_verifier = [nom for nom in requis if nom in presents] if pr.retard > 0 else requis
    defaut = manque(pr, a_verifier)
    if defaut:
        return Decision(RIEN, pr.numero, defaut)

    if pr.retard > 0:
        return Decision(
            REBASER, pr.numero,
            f"{pr.retard} commit(s) de master en retard : rejouer dessus avant "
            "de demander la relecture",
        )
    if pr.relue is None:
        return Decision(RIEN, pr.numero, "relecture inconnue : on retient")
    if not pr.relue:
        return Decision(RIEN, pr.numero, pr.motif_relecture or "pas de relecture d'un tiers")
    return Decision(
        FUSIONNER, pr.numero,
        f"contrôles requis verts sur sa révision, et {pr.motif_relecture}",
    )


def decider(prs, requis, prefixes) -> Rapport:
    """La PR qui avance ce tour-ci, et le compte rendu de toutes les autres.

    L'ordre est celui des numéros : la plus ancienne d'abord. Une PR qui
    attend ne bloque pas les suivantes — seule la PR qui avance est
    unique.
    """
    if not requis:
        # Une liste vide ferait entrer n'importe quoi : c'est le seul
        # cas où l'intégration refuse de fonctionner plutôt que de
        # fonctionner à vide.
        return Rapport(Decision(RIEN, None, "aucun contrôle requis déclaré : rien n'entre"))
    rapport = Rapport(Decision(RIEN, None, "aucune PR à intégrer"))
    retenue: Decision | None = None
    for pr in sorted(prs, key=lambda p: p.numero):
        decision = examiner(pr, requis, prefixes)
        rapport.lignes.append(f"PR {pr.numero} ({pr.branche}) : {decision.action} — {decision.raison}")
        if decision.action != RIEN and retenue is None:
            retenue = decision
    if retenue is not None:
        rapport.decision = retenue
    return rapport
