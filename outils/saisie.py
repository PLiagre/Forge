"""Une demande de lot devient une fiche.

C'est le maillon qui manquait pour que le propriétaire n'ait plus qu'à
donner des directions : il remplit un formulaire, et la fiche entre au
registre par une PR relue comme les autres. Il n'édite plus le cahier à
la main, donc il ne peut plus s'y tromper.

Le formulaire est un formulaire GitHub : sa réponse arrive sous forme de
texte, `### Intitulé` puis la valeur. Ce module le lit et refuse ce qu'il
ne comprend pas — un champ manquant n'est pas un champ vide, et un lot
sans titre n'est pas un lot.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

# Les intitulés du formulaire, tels qu'ils s'affichent. Les changer ici
# sans les changer dans `.github/ISSUE_TEMPLATE/nouveau-lot.yml` casse la
# lecture — et le contrôle `test_saisie` le dit.
TITRE = "Titre du lot"
COUCHE = "Couche"
DEPEND = "Dépend de"

AUCUNE = "aucune"
VIDE = "—"
COUCHES = ("1", "2", "3", "4", "5")

_SECTION = re.compile(r"^###\s+(?P<cle>.+?)\s*$", re.MULTILINE)
_NUMERO = re.compile(r"\d{3}(?:-(?:bis|ter))?")


class DemandeIllisible(ValueError):
    """Le formulaire ne dit pas ce qu'il faut. On refuse, on ne devine pas."""


@dataclass(frozen=True)
class Demande:
    titre: str
    couche: str | None
    depend_de: tuple[str, ...]


def _sections(corps: str) -> dict[str, str]:
    """Chaque `### Intitulé` et le texte qui le suit."""
    trouves = list(_SECTION.finditer(corps or ""))
    sections: dict[str, str] = {}
    for rang, debut in enumerate(trouves):
        fin = trouves[rang + 1].start() if rang + 1 < len(trouves) else len(corps)
        sections[debut.group("cle").strip()] = corps[debut.end():fin].strip()
    return sections


def slug(titre: str) -> str:
    """Le nom de fichier du brief, dérivé du titre. Sans accent, sans surprise."""
    plat = unicodedata.normalize("NFKD", titre)
    plat = "".join(c for c in plat if not unicodedata.combining(c))
    plat = re.sub(r"[^a-zA-Z0-9]+", "-", plat).strip("-").lower()
    plat = re.sub(r"-{2,}", "-", plat)
    if not plat:
        raise DemandeIllisible(f"le titre « {titre} » ne donne aucun nom de fichier lisible")
    # Un nom trop long finit tronqué par un outil ou un autre, et le jour
    # où il l'est, la fiche et le brief ne se ressemblent plus.
    morceaux = plat.split("-")
    court = morceaux[0]
    for morceau in morceaux[1:]:
        if len(court) + 1 + len(morceau) > 48:
            break
        court += "-" + morceau
    return court


def lire(corps: str) -> Demande:
    """La demande, lue dans la réponse au formulaire."""
    sections = _sections(corps)
    manquantes = [c for c in (TITRE, COUCHE, DEPEND) if c not in sections]
    if manquantes:
        raise DemandeIllisible(
            f"le formulaire ne porte pas : {', '.join(manquantes)} "
            "(a-t-il été rempli avec le bon gabarit ?)"
        )

    titre = " ".join(sections[TITRE].split())
    if not titre or titre == "_No response_":
        raise DemandeIllisible("un lot sans titre n'est pas un lot")

    brut = sections[COUCHE].strip()
    couche = None
    if brut and brut != AUCUNE and brut != "_No response_":
        premier = brut.split()[0].rstrip("—-–.").strip()
        if premier not in COUCHES:
            raise DemandeIllisible(
                f"couche « {brut} » inconnue (attendu : {', '.join(COUCHES)}, ou « {AUCUNE} »)"
            )
        couche = premier

    depend: list[str] = []
    texte = sections[DEPEND].strip()
    if texte and texte not in ("_No response_", VIDE, AUCUNE):
        for morceau in re.split(r"[,\s]+", texte):
            if not morceau:
                continue
            if not _NUMERO.fullmatch(morceau):
                raise DemandeIllisible(
                    f"dépendance « {morceau} » illisible : un numéro de lot s'écrit 046"
                )
            if morceau not in depend:
                depend.append(morceau)
    return Demande(titre=titre, couche=couche, depend_de=tuple(depend))


def fiche(demande: Demande, numero: str, briefs: str = "briefs") -> str:
    """Les deux lignes de la fiche. Elle entre `a-briefer`, jamais plus loin.

    C'est le seul état d'entrée qui a du sens ici : le brief n'existe pas
    encore, et c'est justement ce qu'on demande.
    """
    souche = f"{numero}-{slug(demande.titre)}"
    couche = demande.couche or VIDE
    depend = ", ".join(demande.depend_de) or VIDE
    return (
        f"### [{numero} — {demande.titre}]({briefs}/{souche}.md)\n"
        f"état : a-briefer · couche : {couche} · dépend de : {depend} · PR : {VIDE}"
    )


def souche(demande: Demande, numero: str) -> str:
    return f"{numero}-{slug(demande.titre)}"
