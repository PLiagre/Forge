"""Le cycle d'un lot. Orchestre, ne fusionne pas, n'invoque pas."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from . import echange, etat, porte, projet, verrou, worktree
from .backends import invocation, pour
from .etat import FusionInterdite, Run


_SLUG = re.compile(r"briefs/(\d{3}-[a-z0-9-]+)")
_FICHIER = re.compile(r"`([^`\n]+\.[A-Za-z0-9]+)`")


class CycleErreur(ValueError):
    pass


@dataclass(frozen=True)
class Apercu:
    lot: str
    branche: str
    worktree: str
    fichiers: list[str]
    portes: str
    ecrivain: str
    executant: str
    relecteur: str
    commande_worktree: str
    commande_executant: str
    commande_relecteur: str
    note: str


def _lot_depuis(brief: Path) -> str:
    texte = brief.as_posix()
    match = _SLUG.search(texte) or re.search(r"(\d{3}-[a-z0-9-]+)", brief.stem)
    if not match:
        raise CycleErreur(f"impossible de dériver le slug du brief : {brief}")
    return match.group(1)


# Une phrase du périmètre qui contient l'un de ces mots nomme ce que le
# lot n'a PAS le droit de toucher (règle 6 du produit : « tout autre chemin
# est interdit, nommément »). Ses fichiers ne sont pas des fichiers du lot.
# La convention côté brief : les fichiers autorisés dans leur phrase, les
# interdits dans la leur — jamais les deux dans la même.
_MOTS_D_EXCLUSION = re.compile(
    r"interdit|pas modifiable|ne sont pas touchés|n'est pas touché",
    re.IGNORECASE,
)
# Une phrase finit par un point suivi d'un blanc : le point d'un nom de
# fichier (`sim/engine.py`) est suivi d'une lettre, il ne coupe pas.
_PHRASE = re.compile(r"(?<=[.!?])\s+")


def _fichiers_du_perimetre(brief: Path) -> list[str]:
    texte = brief.read_text(encoding="utf-8")
    match = re.search(
        r"^##\s+Périmètre\b(.*?)(?=^##\s+|\Z)",
        texte,
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    if not match:
        return []
    autorises: list[str] = []
    exclus: set[str] = set()
    for phrase in _PHRASE.split(match.group(1)):
        noms = _FICHIER.findall(phrase)
        if _MOTS_D_EXCLUSION.search(phrase):
            exclus.update(noms)
            continue
        for nom in noms:
            if nom not in autorises:
                autorises.append(nom)
    return [nom for nom in autorises if nom not in exclus]


def _prompts(brief: Path, lot: str) -> tuple[str, str]:
    rel = brief.as_posix()
    executant = (
        f"Exécute {rel} sur une branche agent/{lot}.\n"
        "Ce brief est ta SEULE source d'instruction.\n"
        "N'écris que dans les fichiers que sa section Périmètre autorise."
    )
    relecteur = (
        f"Relis le diff du lot {lot}. Tu n'as pas écrit ce code "
        "et tu ne le corriges pas.\n"
        "Vérifie le périmètre, les conditions de succès, "
        "et qu'aucun test existant n'a été relâché."
    )
    return executant, relecteur


def preparer(brief: Path, racine_projet: Path) -> Apercu:
    brief = Path(brief).resolve()
    produit = projet.charger(racine_projet)
    if not porte.passer(brief):
        raise CycleErreur("le brief ne passe pas la porte :\n" + porte.rendre(brief))

    lot = _lot_depuis(brief)
    fichiers = _fichiers_du_perimetre(brief)
    if not fichiers:
        raise CycleErreur("périmètre sans fichier nommé")

    branche = f"{produit.prefixe_branche}{lot}"
    destination = produit.racine.parent / f"{produit.racine.name}-{lot}"
    exec_prompt, rev_prompt = _prompts(brief, lot)
    executant = pour(produit.roles.execution)
    relecteur = pour(produit.roles.controle)

    return Apercu(
        lot=lot,
        branche=branche,
        worktree=destination.as_posix(),
        fichiers=fichiers,
        portes=porte.rendre(brief),
        ecrivain=produit.roles.ecriture,
        executant=executant.nom,
        relecteur=relecteur.nom,
        commande_worktree=worktree.apercu(produit.racine, branche, destination),
        commande_executant=invocation(executant, exec_prompt),
        commande_relecteur=invocation(relecteur, rev_prompt),
        note="sans --run : rien n'est écrit. l'atelier n'invoque personne.",
    )


def lancer(brief: Path, racine_projet: Path) -> Run:
    apercu = preparer(brief, racine_projet)
    produit = projet.charger(racine_projet)
    brief = Path(brief).resolve()

    verrou.poser(produit.racine, apercu.lot, apercu.fichiers)

    destination = Path(apercu.worktree)
    try:
        worktree.creer(produit.racine, apercu.branche, destination)
    except worktree.WorktreeErreur:
        # Un worktree déjà créé pour ce lot se récupère, il ne se recréé pas.
        if not destination.exists():
            verrou.lever(produit.racine, apercu.lot)
            raise

    echange.ouvrir(destination)
    prompt_exec, prompt_rev = _prompts(brief, apercu.lot)
    echange.deposer_texte(destination, "prompt-executant.txt", prompt_exec)
    echange.deposer_texte(destination, "prompt-relecteur.txt", prompt_rev)

    run = etat.nouveau(
        lot=apercu.lot,
        brief=brief,
        branche=apercu.branche,
        worktree=destination,
        auteur_code=apercu.executant,
        relecteur=apercu.relecteur,
        fichiers=apercu.fichiers,
    )
    etat.sauver(produit.racine, run)
    return run


def fusionner(run: Run) -> None:
    etat.fusionner(run)
    raise FusionInterdite("inatteignable")
