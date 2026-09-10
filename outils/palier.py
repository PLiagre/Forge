"""Le palier : ce qu'une couche finie déclenche.

Un lot prouve sa règle. Il ne prouve pas que les lots tiennent
ensemble. Quand toutes les fiches d'une couche sont livrées — le monde
vivant, les villes, les armées — plus aucun lot n'a de raison d'ouvrir
le sujet, et c'est là que les défauts transversaux dorment : une
grandeur que deux lots font bouger sans se connaître, une vue qui
montre autre chose que ce que le moteur joue, un déterminisme perdu à
la jointure. Le palier est ce qui les réveille — un lot de
stabilisation et de QA, qui nomme les lots qu'il couvre.

Il se déclenche sur une mesure, pas sur une intention : une couche est
finie quand aucune de ses fiches n'attend plus rien, et le palier est
dû tant qu'il reste un lot livré que nul palier ne couvre. Les deux se
dérivent du registre ; aucun compteur n'est tenu à la main.

Ce module ne lit pas le registre. Il reçoit des fiches et rend une
décision : le lecteur du registre est celui de l'atelier, et il n'y en
a qu'un (voir `outils/registre.py`).
"""

from __future__ import annotations

from dataclasses import dataclass
import re

# Les couches du produit, dans l'ordre où la vision les nomme. La liste
# est celle des fiches : une couche sans fiche n'existe pas ici.
COUCHES = ("1", "2", "3", "4", "5")

# Une fiche qui n'attend plus rien. `abandonne` en fait partie : un lot
# qu'on ne fera pas ne retient aucune couche.
FINIS = frozenset({"livre", "archive", "abandonne"})

# Une fiche dont le travail est vraiment dans `master`. Elle seule
# s'ajoute à ce qu'un palier a nommément couvert.
LIVRES = frozenset({"livre", "archive"})

# Ce qu'un palier ne couvre pas, même livré : les lots d'avant le
# dégraissage V1. Leurs briefs et leurs preuves vivent au tag, hors de
# l'arbre de travail — un lot de stabilisation ne pourrait ni les citer,
# ni les rejouer. Ils n'attendent donc rien, et n'appellent rien.
HORS_PORTEE = frozenset({"archive"})

# Le nom d'un lot de palier se lit dans le chemin de son brief. Pas de
# champ nouveau dans la fiche : le format du registre appartient à
# l'atelier, et une clé de plus serait une clé qu'il refuserait.
GABARIT_SLUG = "{numero}-stabilisation-couche-{couche}"
_STABILISATION = re.compile(r"\d{3}(?:-(?:bis|ter))?-stabilisation-couche-([1-5])\.md$")

# Le titre ne nomme pas la couche : « le monde vivant », « les villes »
# vivent dans VISION.md, et les recopier ici en ferait une seconde
# source qui vieillirait sans prévenir.
GABARIT_TITRE = "Stabilisation et QA — couche {couche}"

VIDE = "—"


def couche_stabilisee(chemin: str) -> str | None:
    """La couche qu'un brief stabilise, ou None si ce n'est pas un palier."""
    trouve = _STABILISATION.search(chemin)
    return trouve.group(1) if trouve else None


@dataclass(frozen=True)
class Etape:
    """Une couche, vue par le registre."""

    couche: str
    en_cours: tuple[str, ...]
    couverts: tuple[str, ...]
    a_couvrir: tuple[str, ...]

    @property
    def finie(self) -> bool:
        """Plus rien n'avance, et quelque chose a été livré.

        Le second membre n'est pas une précaution : une couche dont
        toutes les fiches sont abandonnées ne serait qu'un échantillon
        vide, et un échantillon vide ne prouve rien.
        """
        return not self.en_cours and bool(self.couverts or self.a_couvrir)

    @property
    def due(self) -> bool:
        return self.finie and bool(self.a_couvrir)


def etapes(fiches) -> tuple[Etape, ...]:
    """Chaque couche présente au registre, et ce qu'elle attend."""
    resultat: list[Etape] = []
    for couche in COUCHES:
        de_la_couche = [f for f in fiches if f.couche == couche]
        if not de_la_couche:
            continue
        deja_couverts = {
            dep
            for f in de_la_couche
            if couche_stabilisee(f.chemin) == couche
            for dep in f.depend_de
        }
        en_cours: list[str] = []
        couverts: list[str] = []
        a_couvrir: list[str] = []
        for fiche in de_la_couche:
            if fiche.etat not in FINIS:
                en_cours.append(fiche.numero)
            elif fiche.etat not in LIVRES:
                continue  # abandonné : rien n'a été livré, rien à couvrir
            elif couche_stabilisee(fiche.chemin) == couche:
                continue  # un palier ne se stabilise pas lui-même
            elif fiche.etat in HORS_PORTEE or fiche.numero in deja_couverts:
                couverts.append(fiche.numero)
            else:
                a_couvrir.append(fiche.numero)
        resultat.append(
            Etape(
                couche=couche,
                en_cours=tuple(en_cours),
                couverts=tuple(couverts),
                a_couvrir=tuple(a_couvrir),
            )
        )
    return tuple(resultat)


def due(fiches) -> Etape | None:
    """La première couche, dans l'ordre, qui appelle son palier."""
    for etape in etapes(fiches):
        if etape.due:
            return etape
    return None


def numero_libre(fiches, reserves=()) -> str:
    """Le premier numéro au-dessus du plus grand recensé.

    La règle vit dans ROADMAP.md § « Ajouter un lot » ; elle est
    appliquée ici, pas réécrite. Un suffixe `-bis` ne compte pas comme
    un numéro de plus.
    """
    numeros = [int(f.numero[:3]) for f in fiches]
    if not numeros:
        raise ValueError("registre sans fiche : aucun numéro à dériver")
    numeros.extend(int(str(n).split("-")[0]) for n in reserves)
    return f"{max(numeros) + 1:03d}"


def slug(etape: Etape, numero: str) -> str:
    return GABARIT_SLUG.format(numero=numero, couche=etape.couche)


def fiche(etape: Etape, numero: str, briefs: str = "briefs") -> str:
    """Les deux lignes de la fiche du palier, sans ligne vide autour.

    Elle entre `a-briefer` : le briefer écrira le brief, et c'est sa PR
    qui la passera à `pret`. Elle dépend nommément des lots qu'elle
    couvre — c'est cette liste, et rien d'autre, qui empêchera le
    palier suivant de les recompter.
    """
    if not etape.a_couvrir:
        raise ValueError(
            f"couche {etape.couche} : aucun lot à couvrir, il n'y a pas de palier à écrire"
        )
    souche = slug(etape, numero)
    titre = GABARIT_TITRE.format(couche=etape.couche)
    depend = ", ".join(sorted(etape.a_couvrir))
    return (
        f"### [{numero} — {titre}]({briefs}/{souche}.md)\n"
        f"état : a-briefer · couche : {etape.couche} · dépend de : {depend} · PR : {VIDE}"
    )


def inserer(texte: str, fiche_texte: str, repere_debut: str) -> str:
    """Poser la fiche en tête du registre — l'ordre est la priorité.

    Un palier passe avant les lots qui attendent : c'est lui qui dit si
    ce qui vient d'être livré tient debout. Le repère est passé par
    l'appelant, qui le tient de l'atelier : le format du registre ne se
    recopie pas ici.
    """
    lignes = texte.splitlines()
    for i, ligne in enumerate(lignes):
        if ligne.strip() == repere_debut:
            avant = lignes[: i + 1]
            apres = lignes[i + 1 :]
            fin = "\n" if texte.endswith("\n") else ""
            return "\n".join(avant + ["", *fiche_texte.splitlines()] + apres) + fin
    raise ValueError(f"repère « {repere_debut} » introuvable : le registre ne commence nulle part")
