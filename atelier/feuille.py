"""La feuille de route : le registre des lots, lu par une machine.

Une seule représentation fait autorité pour l'état d'un lot : la fiche
de ce lot dans la feuille de route du produit (chez ForgeHistory,
`ROADMAP.md`), entre deux repères `<!-- lots:debut -->` et
`<!-- lots:fin -->`. Le reste du fichier est de la prose : la machine
ne le lit pas, et la prose ne dit jamais l'état d'un lot.

Une fiche tient sur deux lignes, séparées de la suivante par une ligne
vide — c'est cette ligne vide qui permet à deux PR de lots voisins de
fusionner sans conflit :

    ### [046 — La mer est un port commun](briefs/046-la-mer-est-un-port-commun.md)
    état : pret · couche : 1 · dépend de : — · PR : —

Rien ici n'invoque personne. La feuille dit ce qui est ; `decider` dit
ce qu'un cron devrait déposer ; `marquer` réécrit une fiche. Le
propriétaire fusionne, toujours.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

from . import boite, porte, verrou
from .cycle import _fichiers_du_perimetre


REPERE_DEBUT = "<!-- lots:debut -->"
REPERE_FIN = "<!-- lots:fin -->"

# Les états qu'une fiche peut porter. « en cours », « en relecture »,
# « bloqué » ne s'écrivent pas : ils se dérivent des briefs, des cartes
# et des verrous — voir `etat_effectif`.
ETATS = ("idee", "a-briefer", "pret", "livre", "abandonne", "archive")

# Un lot livré n'a plus rien à attendre ; un lot archivé vient d'avant
# le dégraissage, son brief vit dans l'historique git.
ETATS_LIVRES = frozenset({"livre", "archive"})

# D'où vers où une fiche a le droit d'aller, et qui tient le geste.
TRANSITIONS: dict[str, dict[str, str]] = {
    "idee": {
        "a-briefer": "le propriétaire, dans une PR de feuille",
        "pret": "le propriétaire, dans la PR qui apporte le brief",
        "abandonne": "le propriétaire",
    },
    "a-briefer": {
        "pret": "la PR du brief, fusionnée par le propriétaire",
        "idee": "le propriétaire",
        "abandonne": "le propriétaire",
    },
    "pret": {
        "livre": "la PR du lot, fusionnée par le propriétaire",
        "a-briefer": "le propriétaire, quand le brief est à réécrire",
        "abandonne": "le propriétaire",
    },
    "livre": {},
    "archive": {},
    "abandonne": {"idee": "le propriétaire"},
}

# Ce qu'une fiche neuve a le droit d'être : on n'entre jamais livré.
ETATS_D_ENTREE = frozenset({"idee", "a-briefer", "pret"})

COUCHES = ("1", "2", "3", "4", "5")

# Là où le pilote range une carte dont la PR a été fusionnée.
BOITE_FUSIONNEE = "fusionnee"
# Là où le briefer laisse sa carte : le brief est en PR, le propriétaire
# fusionne, et le pilote déposera ensuite la carte du coder. Le nom vient
# de la boîte, il n'est pas recopié ici.
BOITE_BRIEF_A_FUSIONNER = boite.SUIVANT["briefer"]

_NUMERO = r"\d{3}(?:-(?:bis|ter))?"
_TITRE = re.compile(
    rf"^### \[(?P<numero>{_NUMERO}) — (?P<titre>[^\]]+)\]\((?P<chemin>[^)\s]+)\)\s*$"
)
_CHAMP = re.compile(r"^(?P<cle>[^:]+?) : (?P<valeur>.*)$")
_NOTE = re.compile(r"^note : (?P<note>.+)$")
_GROUPE = re.compile(r"^##(?!#)")
_BRIEF_TITRE = re.compile(rf"^#\s+Brief\s+(?P<numero>{_NUMERO})\b", re.MULTILINE)
_FICHIER_BRIEF = re.compile(rf"^(?P<numero>{_NUMERO})-[a-z0-9-]+\.md$")

CLES = ("état", "couche", "dépend de", "PR")
VIDE = "—"


class FeuilleErreur(ValueError):
    pass


@dataclass(frozen=True)
class Fiche:
    numero: str
    titre: str
    chemin: str
    etat: str
    couche: str | None
    depend_de: tuple[str, ...]
    prs: tuple[int, ...]
    note: str
    ligne: int
    ligne_champs: int

    @property
    def lot(self) -> str:
        """L'identifiant du lot : le dernier segment du chemin, sans `.md`.

        Pour un lot vivant c'est la souche du brief (`046-la-mer-…`) ;
        pour un lot archivé, le dossier du brief dans l'historique.
        """
        segment = self.chemin.rstrip("/").rsplit("/", 1)[-1]
        return segment[:-3] if segment.endswith(".md") else segment


@dataclass
class Feuille:
    chemin: Path
    lignes: list[str]
    debut: int
    fin: int
    fiches: list[Fiche] = field(default_factory=list)

    def fiche(self, cle: str) -> Fiche | None:
        for fiche in self.fiches:
            if cle in (fiche.numero, fiche.lot):
                return fiche
        return None

    @property
    def par_numero(self) -> dict[str, Fiche]:
        return {f.numero: f for f in self.fiches}


@dataclass(frozen=True)
class Decision:
    role: str
    boite: str
    lot: str
    brief: str
    fichiers: tuple[str, ...]


@dataclass(frozen=True)
class Rapprochement:
    lot: str
    source: str
    destination: str
    lever_verrou: bool
    raison: str


# ------------------------------------------------------------- lecture


def _erreur(chemin: Path, ligne: int, message: str) -> FeuilleErreur:
    return FeuilleErreur(f"{chemin}:{ligne} — {message}")


def _lire_champs(chemin: Path, ligne: int, texte: str) -> dict[str, str]:
    champs: dict[str, str] = {}
    for morceau in texte.split(" · "):
        match = _CHAMP.match(morceau.strip())
        if not match:
            raise _erreur(chemin, ligne, f"champ illisible : « {morceau.strip()} » (attendu « clé : valeur »)")
        cle = match.group("cle").strip()
        if cle not in CLES:
            raise _erreur(chemin, ligne, f"clé inconnue : « {cle} » (connues : {', '.join(CLES)})")
        if cle in champs:
            raise _erreur(chemin, ligne, f"clé répétée : « {cle} »")
        champs[cle] = match.group("valeur").strip()
    manquantes = [c for c in CLES if c not in champs]
    if manquantes:
        raise _erreur(chemin, ligne, f"champs manquants : {', '.join(manquantes)}")
    return champs


def _liste(valeur: str) -> list[str]:
    if valeur == VIDE:
        return []
    return [v.strip() for v in valeur.split(",") if v.strip()]


def _construire(chemin: Path, ligne_titre: int, titre: re.Match[str], ligne_champs: int,
                champs: dict[str, str], note: str) -> Fiche:
    etat = champs["état"]
    if etat not in ETATS:
        raise _erreur(chemin, ligne_champs, f"état inconnu : « {etat} » (connus : {', '.join(ETATS)})")
    couche = champs["couche"]
    if couche != VIDE and couche not in COUCHES:
        raise _erreur(chemin, ligne_champs, f"couche inconnue : « {couche} » (connues : {', '.join(COUCHES)}, ou {VIDE})")
    depend_de = _liste(champs["dépend de"])
    for dep in depend_de:
        if not re.fullmatch(_NUMERO, dep):
            raise _erreur(chemin, ligne_champs, f"dépendance illisible : « {dep} » (attendu un numéro de lot, ex. 044)")
    prs: list[int] = []
    for brut in _liste(champs["PR"]):
        if not brut.isdigit():
            raise _erreur(chemin, ligne_champs, f"PR illisible : « {brut} » (attendu un numéro entier, sans #)")
        prs.append(int(brut))
    return Fiche(
        numero=titre.group("numero"),
        titre=titre.group("titre").strip(),
        chemin=titre.group("chemin"),
        etat=etat,
        couche=None if couche == VIDE else couche,
        depend_de=tuple(depend_de),
        prs=tuple(prs),
        note=note,
        ligne=ligne_titre,
        ligne_champs=ligne_champs,
    )


def lire_texte(texte: str, chemin: Path = Path("feuille")) -> Feuille:
    lignes = texte.splitlines()
    debuts = [i for i, l in enumerate(lignes) if l.strip() == REPERE_DEBUT]
    fins = [i for i, l in enumerate(lignes) if l.strip() == REPERE_FIN]
    if len(debuts) != 1 or len(fins) != 1:
        raise FeuilleErreur(
            f"{chemin} — le registre des lots doit être délimité par exactement un "
            f"« {REPERE_DEBUT} » et un « {REPERE_FIN} » "
            f"({len(debuts)} début(s), {len(fins)} fin(s) trouvés)"
        )
    debut, fin = debuts[0], fins[0]
    if fin < debut:
        raise FeuilleErreur(f"{chemin} — « {REPERE_FIN} » précède « {REPERE_DEBUT} »")

    feuille = Feuille(chemin=chemin, lignes=lignes, debut=debut, fin=fin)
    i = debut + 1
    while i < fin:
        ligne = lignes[i]
        if not ligne.strip() or _GROUPE.match(ligne):
            i += 1
            continue
        titre = _TITRE.match(ligne)
        if not titre:
            raise _erreur(
                chemin, i + 1,
                "ligne inattendue dans le registre : une fiche commence par "
                "« ### [NNN — Titre](briefs/NNN-slug.md) »",
            )
        if i + 1 >= fin or not lignes[i + 1].strip():
            raise _erreur(chemin, i + 1, f"fiche {titre.group('numero')} sans ligne de champs")
        champs = _lire_champs(chemin, i + 2, lignes[i + 1])
        note = ""
        suivant = i + 2
        if suivant < fin:
            match_note = _NOTE.match(lignes[suivant])
            if match_note:
                note = match_note.group("note").strip()
                suivant += 1
        if suivant < fin and lignes[suivant].strip():
            raise _erreur(
                chemin, suivant + 1,
                f"la fiche {titre.group('numero')} doit être suivie d'une ligne vide "
                "(deux PR de lots voisins fusionnent sans conflit grâce à elle)",
            )
        feuille.fiches.append(_construire(chemin, i + 1, titre, i + 2, champs, note))
        i = suivant
    return feuille


def lire(chemin: Path) -> Feuille:
    chemin = Path(chemin)
    if not chemin.is_file():
        raise FeuilleErreur(f"feuille de route introuvable : {chemin}")
    return lire_texte(chemin.read_text(encoding="utf-8"), chemin)


# ---------------------------------------------------------- les cartes


def cartes_par_lot(racine: Path) -> dict[str, list[tuple[str, boite.Carte]]]:
    """Toutes les cartes de toutes les boîtes, rangées par lot."""
    racine_boite = boite.racine_boite(racine)
    resultat: dict[str, list[tuple[str, boite.Carte]]] = {}
    if not racine_boite.is_dir():
        return resultat
    for dossier in sorted(p for p in racine_boite.iterdir() if p.is_dir()):
        try:
            cartes = boite.lister(racine, dossier.name)
        except boite.BoiteErreur as exc:
            raise FeuilleErreur(f"boîte {dossier.name} illisible : {exc}") from exc
        for carte in cartes:
            resultat.setdefault(carte.lot, []).append((dossier.name, carte))
    return resultat


# ---------------------------------------------------------- les contrôles


def _cycles(feuille: Feuille) -> list[str]:
    par_numero = feuille.par_numero
    erreurs: list[str] = []
    vus: set[str] = set()

    def visiter(numero: str, pile: list[str]) -> None:
        if numero in pile:
            boucle = pile[pile.index(numero):] + [numero]
            erreurs.append("dépendances circulaires : " + " → ".join(boucle))
            return
        if numero in vus or numero not in par_numero:
            return
        pile.append(numero)
        for dep in par_numero[numero].depend_de:
            visiter(dep, pile)
        pile.pop()
        vus.add(numero)

    for fiche in feuille.fiches:
        visiter(fiche.numero, [])
    return erreurs


def verifier(feuille: Feuille, racine: Path, briefs: Path) -> list[str]:
    """Les incohérences entre la feuille et les briefs. Vide = cohérent."""
    racine = Path(racine)
    briefs = Path(briefs)
    erreurs: list[str] = []
    par_numero: dict[str, Fiche] = {}
    briefs_rel = briefs.relative_to(racine).as_posix() if briefs.is_relative_to(racine) else briefs.as_posix()

    for fiche in feuille.fiches:
        ou = f"{feuille.chemin}:{fiche.ligne}"
        if fiche.numero in par_numero:
            erreurs.append(
                f"{ou} — numéro dupliqué : {fiche.numero} apparaît déjà "
                f"ligne {par_numero[fiche.numero].ligne}"
            )
            continue
        par_numero[fiche.numero] = fiche

        if not fiche.lot.startswith(f"{fiche.numero}-"):
            erreurs.append(
                f"{ou} — le chemin « {fiche.chemin} » ne porte pas le numéro {fiche.numero} "
                "en tête de son dernier segment : c'est lui qui identifie le lot"
            )
        if fiche.etat != "archive":
            attendu_prefixe = f"{briefs_rel}/{fiche.numero}-"
            if not fiche.chemin.startswith(attendu_prefixe) or not fiche.chemin.endswith(".md"):
                erreurs.append(
                    f"{ou} — le brief du lot {fiche.numero} doit s'appeler "
                    f"« {attendu_prefixe}<slug>.md », pas « {fiche.chemin} »"
                )

        chemin_brief = racine / fiche.chemin
        existe = chemin_brief.is_file() if not fiche.chemin.startswith(("http://", "https://")) else False
        if fiche.etat in ("pret", "livre") and not existe:
            erreurs.append(
                f"{ou} — le lot {fiche.numero} est « {fiche.etat} » mais son brief "
                f"{fiche.chemin} n'existe pas"
            )
        if fiche.etat in ("idee", "a-briefer") and existe:
            erreurs.append(
                f"{ou} — le lot {fiche.numero} est « {fiche.etat} » mais son brief "
                f"{fiche.chemin} existe déjà : le passer à « pret », ou retirer le fichier"
            )
        if existe:
            texte = chemin_brief.read_text(encoding="utf-8")
            match = _BRIEF_TITRE.search(texte)
            if not match:
                erreurs.append(f"{fiche.chemin} — le brief ne commence pas par « # Brief {fiche.numero} »")
            elif match.group("numero") != fiche.numero:
                erreurs.append(
                    f"{fiche.chemin} — le brief se dit « Brief {match.group('numero')} », "
                    f"la fiche dit {fiche.numero}"
                )
        if fiche.etat == "pret" and existe and not porte.passer(chemin_brief):
            refus = [c for c in porte.inspecter(chemin_brief) if not c.ok]
            erreurs.append(
                f"{ou} — le lot {fiche.numero} est « pret » mais son brief ne passe pas la porte : "
                + " ; ".join(f"{c.nom} ({c.preuve})" for c in refus)
            )

        if fiche.etat == "livre" and not fiche.prs:
            erreurs.append(f"{ou} — le lot {fiche.numero} est « livre » sans numéro de PR")
        if fiche.etat in ("idee", "a-briefer", "pret") and fiche.prs:
            erreurs.append(
                f"{ou} — le lot {fiche.numero} est « {fiche.etat} » mais porte déjà une PR "
                f"({', '.join(map(str, fiche.prs))}) : une PR fusionnée se marque « livre »"
            )

    for fiche in feuille.fiches:
        ou = f"{feuille.chemin}:{fiche.ligne}"
        for dep in fiche.depend_de:
            if dep == fiche.numero:
                erreurs.append(f"{ou} — le lot {fiche.numero} dépend de lui-même")
            elif dep not in par_numero:
                erreurs.append(f"{ou} — le lot {fiche.numero} dépend de {dep}, qui n'a pas de fiche")
            elif fiche.etat in ETATS_LIVRES and par_numero[dep].etat not in ETATS_LIVRES:
                erreurs.append(
                    f"{ou} — le lot {fiche.numero} est « {fiche.etat} » mais dépend de {dep}, "
                    f"qui est « {par_numero[dep].etat} »"
                )
    erreurs.extend(_cycles(feuille))

    if briefs.is_dir():
        connus = {f.chemin for f in feuille.fiches}
        for fichier in sorted(briefs.glob("*.md")):
            match = _FICHIER_BRIEF.match(fichier.name)
            if not match:
                continue
            rel = f"{briefs_rel}/{fichier.name}"
            if rel not in connus:
                erreurs.append(
                    f"{rel} — brief orphelin : aucune fiche ne le nomme "
                    f"(ajouter une fiche {match.group('numero')} au registre)"
                )
    return erreurs


def verifier_cartes(feuille: Feuille, racine: Path) -> list[str]:
    """Les incohérences entre la feuille et les boîtes. Vide = cohérent."""
    erreurs: list[str] = []
    for lot, cartes in sorted(cartes_par_lot(racine).items()):
        fiche = feuille.fiche(lot)
        for nom_boite, carte in cartes:
            ou = f"carte {lot} dans {nom_boite}"
            if fiche is None:
                erreurs.append(f"{ou} — aucune fiche ne porte ce lot")
                continue
            if carte.brief != fiche.chemin:
                erreurs.append(f"{ou} — nomme le brief {carte.brief}, la fiche dit {fiche.chemin}")
            if nom_boite in (BOITE_FUSIONNEE, "echec"):
                continue
            if fiche.etat in ("abandonne", "archive"):
                erreurs.append(f"{ou} — le lot est « {fiche.etat} », la carte n'a rien à y faire")
            elif fiche.etat == "livre":
                # Le pilote la rapproche : ce n'est pas une erreur, c'est une fusion.
                continue
            elif nom_boite == "a-briefer" and fiche.etat != "a-briefer":
                erreurs.append(f"{ou} — le lot est « {fiche.etat} », pas « a-briefer »")
            elif nom_boite in ("a-planifier", "a-coder", "a-relire", "faite") and fiche.etat != "pret":
                erreurs.append(
                    f"{ou} — le lot est « {fiche.etat} » : on ne code pas un lot dont le brief "
                    "n'est pas fusionné"
                )
            elif nom_boite == BOITE_BRIEF_A_FUSIONNER and fiche.etat not in ("a-briefer", "pret"):
                erreurs.append(f"{ou} — le lot est « {fiche.etat} », son brief n'est pas en PR")
    return erreurs


def rapprochements(feuille: Feuille, racine: Path) -> list[Rapprochement]:
    """Les cartes que la feuille déclare dépassées : la PR a été fusionnée."""
    resultat: list[Rapprochement] = []
    for lot, cartes in sorted(cartes_par_lot(racine).items()):
        fiche = feuille.fiche(lot)
        if fiche is None:
            continue
        for nom_boite, _carte in cartes:
            if nom_boite == BOITE_FUSIONNEE:
                continue
            if fiche.etat == "livre":
                resultat.append(Rapprochement(
                    lot, nom_boite, BOITE_FUSIONNEE, lever_verrou=True,
                    raison=f"la fiche dit « livre », PR {', '.join(map(str, fiche.prs))}",
                ))
            elif nom_boite == BOITE_BRIEF_A_FUSIONNER and fiche.etat == "pret":
                resultat.append(Rapprochement(
                    lot, nom_boite, BOITE_FUSIONNEE, lever_verrou=False,
                    raison="la fiche dit « pret » : le brief est fusionné",
                ))
    return resultat


def appliquer(racine: Path, rapprochement: Rapprochement) -> Path:
    carte = boite.lire(racine, rapprochement.source, rapprochement.lot)
    destination = boite.deposer(racine, rapprochement.destination, carte)
    (boite.racine_boite(racine) / rapprochement.source / f"{rapprochement.lot}.json").unlink()
    if rapprochement.lever_verrou:
        verrou.lever(racine, rapprochement.lot)
    return destination


# ---------------------------------------------------------- la décision


def _fichiers_tenus(racine: Path) -> dict[str, str]:
    tenus: dict[str, str] = {}
    for pose in verrou.charger(Path(racine)).poses:
        for fichier in pose.fichiers:
            tenus[fichier] = pose.lot
    return tenus


def _empechement(fiche: Fiche, feuille: Feuille, racine: Path) -> str | None:
    """Pourquoi un lot « pret » n'est pas déposable aujourd'hui. None = il l'est."""
    par_numero = feuille.par_numero
    attend = [d for d in fiche.depend_de if par_numero.get(d) and par_numero[d].etat not in ETATS_LIVRES]
    if attend:
        return "bloqué par " + ", ".join(f"{d} ({par_numero[d].etat})" for d in attend)
    chemin = Path(racine) / fiche.chemin
    if not chemin.is_file():
        return f"brief absent : {fiche.chemin}"
    if not porte.passer(chemin):
        return "le brief ne passe pas la porte"
    fichiers = _fichiers_du_perimetre(chemin)
    if not fichiers:
        return "périmètre sans fichier nommé"
    tenus = _fichiers_tenus(racine)
    pris = sorted(f"{f} tenu par {tenus[f]}" for f in fichiers if tenus.get(f, fiche.lot) != fiche.lot)
    if pris:
        return "attend : " + ", ".join(pris)
    return None


def decider(feuille: Feuille, racine: Path) -> list[Decision]:
    """Ce que le pilote dépose : au plus une carte par rôle, la première admissible."""
    racine = Path(racine)
    cartes = cartes_par_lot(racine)
    decisions: list[Decision] = []
    briefer_pris = coder_pris = False
    for fiche in feuille.fiches:
        if fiche.lot in cartes:
            continue
        if fiche.etat == "a-briefer" and not briefer_pris:
            decisions.append(Decision("briefer", "a-briefer", fiche.lot, fiche.chemin, ()))
            briefer_pris = True
        elif fiche.etat == "pret" and not coder_pris:
            if _empechement(fiche, feuille, racine) is None:
                fichiers = tuple(_fichiers_du_perimetre(racine / fiche.chemin))
                decisions.append(Decision("coder", "a-coder", fiche.lot, fiche.chemin, fichiers))
                coder_pris = True
    return decisions


def deposer(racine: Path, decision: Decision) -> Path:
    carte = boite.Carte(lot=decision.lot, brief=decision.brief, fichiers=list(decision.fichiers))
    return boite.deposer(racine, decision.boite, carte)


# ---------------------------------------------------- l'état, pour l'œil


def etat_effectif(fiche: Fiche, feuille: Feuille, racine: Path) -> str:
    """Ce qu'un humain veut lire : l'état écrit, complété par ce qui se dérive."""
    cartes = cartes_par_lot(racine).get(fiche.lot, [])
    prs = ", ".join(map(str, fiche.prs))
    if fiche.etat == "livre":
        return f"livré (PR {prs})"
    if fiche.etat == "archive":
        return f"archivé (PR {prs})" if prs else "archivé"
    if fiche.etat == "abandonne":
        return "abandonné" + (f" — {fiche.note}" if fiche.note else "")
    if fiche.etat == "idee":
        return "idée — pas de brief demandé"
    for nom_boite, carte in cartes:
        numero_pr = f" (PR {carte.pr})" if carte.pr else ""
        if nom_boite == "echec":
            return f"en échec : {carte.note} — `atelier reprendre --lot {fiche.lot}`"
        if nom_boite == "a-briefer":
            return "brief en file (a-briefer)"
        if nom_boite == BOITE_BRIEF_A_FUSIONNER:
            return f"brief écrit{numero_pr} — à fusionner par le propriétaire"
        if nom_boite == "a-planifier":
            return "en planification (a-planifier)"
        if nom_boite == "a-coder":
            return "en file (a-coder)"
        if nom_boite == "a-relire":
            return f"en relecture{numero_pr}"
        if nom_boite == "faite":
            return f"relu{numero_pr} — à fusionner par le propriétaire"
    if fiche.etat == "a-briefer":
        return "à briefer — le pilote déposera la carte"
    empechement = _empechement(fiche, feuille, racine)
    return "prêt — le pilote déposera la carte" if empechement is None else f"prêt, {empechement}"


# --------------------------------------------------------- les transitions


def transitions(
    avant: Feuille,
    apres: Feuille,
    *,
    prefixe_branche: str | None = None,
    branche: str | None = None,
    pr: int | None = None,
) -> list[str]:
    """Ce qui a le droit de changer entre deux versions de la feuille."""
    erreurs: list[str] = []
    av, ap = avant.par_numero, apres.par_numero
    for numero in av:
        if numero not in ap:
            erreurs.append(
                f"le lot {numero} a disparu de la feuille : un lot ne s'efface pas, "
                "il passe à « abandonne »"
            )
    changes: dict[str, tuple[str, str]] = {}
    for numero, fiche in ap.items():
        if numero not in av:
            if fiche.etat not in ETATS_D_ENTREE:
                erreurs.append(
                    f"le lot {numero} entre dans la feuille « {fiche.etat} » : un lot neuf est "
                    f"« {' », « '.join(sorted(ETATS_D_ENTREE))} », jamais livré d'emblée"
                )
            continue
        ancien = av[numero]
        if ancien.etat != fiche.etat:
            changes[numero] = (ancien.etat, fiche.etat)
            if fiche.etat not in TRANSITIONS[ancien.etat]:
                permises = ", ".join(sorted(TRANSITIONS[ancien.etat])) or "aucune"
                erreurs.append(
                    f"transition interdite pour le lot {numero} : {ancien.etat} → {fiche.etat} "
                    f"(permises depuis {ancien.etat} : {permises})"
                )
        if ancien.etat in ETATS_LIVRES and set(ancien.prs) - set(fiche.prs):
            erreurs.append(f"le lot {numero} perd un numéro de PR : {ancien.prs} → {fiche.prs}")

    if branche and prefixe_branche and branche.startswith(prefixe_branche):
        lot = branche[len(prefixe_branche):]
        fiche = apres.fiche(lot)
        if fiche is None:
            erreurs.append(
                f"la branche {branche} porte le lot {lot}, qui n'a aucune fiche dans la feuille"
            )
        else:
            if fiche.etat != "livre":
                erreurs.append(
                    f"la PR du lot {fiche.numero} ({branche}) ne marque pas le lot « livre » : "
                    f"sa fiche dit « {fiche.etat} »"
                )
            if pr is not None and pr not in fiche.prs:
                erreurs.append(
                    f"la PR {pr} du lot {fiche.numero} n'est pas dans la colonne PR de sa fiche "
                    f"({', '.join(map(str, fiche.prs)) or VIDE})"
                )
            autres = sorted(n for n in changes if n != fiche.numero)
            if autres:
                erreurs.append(
                    f"la PR du lot {fiche.numero} change aussi l'état de : {', '.join(autres)} — "
                    "une PR de lot ne touche que sa propre fiche"
                )
    return erreurs


# -------------------------------------------------------------- marquer


def marquer(texte: str, cle: str, etat: str, prs: tuple[int, ...] = (), chemin: Path = Path("feuille")) -> str:
    """Le texte de la feuille avec la fiche `cle` passée à `etat`."""
    feuille = lire_texte(texte, chemin)
    fiche = feuille.fiche(cle)
    if fiche is None:
        raise FeuilleErreur(f"aucune fiche pour le lot {cle} dans {chemin}")
    if etat not in ETATS:
        raise FeuilleErreur(f"état inconnu : « {etat} » (connus : {', '.join(ETATS)})")
    if etat != fiche.etat and etat not in TRANSITIONS[fiche.etat]:
        permises = ", ".join(sorted(TRANSITIONS[fiche.etat])) or "aucune"
        raise FeuilleErreur(
            f"transition interdite pour le lot {fiche.numero} : {fiche.etat} → {etat} "
            f"(permises : {permises})"
        )
    nouvelles_prs = tuple(sorted(set(fiche.prs) | set(prs)))
    if etat == "livre" and not nouvelles_prs:
        raise FeuilleErreur(f"le lot {fiche.numero} ne se marque pas « livre » sans numéro de PR (--pr)")
    valeurs = {
        "état": etat,
        "couche": fiche.couche or VIDE,
        "dépend de": ", ".join(fiche.depend_de) or VIDE,
        "PR": ", ".join(map(str, nouvelles_prs)) or VIDE,
    }
    lignes = list(feuille.lignes)
    lignes[fiche.ligne_champs - 1] = " · ".join(f"{cle_} : {valeurs[cle_]}" for cle_ in CLES)
    fin = "\n" if texte.endswith("\n") else ""
    return "\n".join(lignes) + fin
