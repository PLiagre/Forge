"""Worktree : un agent, un répertoire, une branche."""

from __future__ import annotations

from pathlib import Path
import subprocess


class WorktreeErreur(RuntimeError):
    pass


def _git(racine: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=racine,
        text=True,
        capture_output=True,
        check=False,
    )


def apercu(racine: Path, branche: str, destination: Path) -> str:
    return (
        f"git -C {racine} worktree add {destination} -b {branche} origin/HEAD"
    )


def creer(racine: Path, branche: str, destination: Path, *, base: str = "HEAD") -> Path:
    destination = Path(destination)
    if destination.exists():
        raise WorktreeErreur(f"destination déjà là : {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    resultat = _git(racine, "worktree", "add", str(destination), "-b", branche, base)
    if resultat.returncode != 0:
        raise WorktreeErreur(resultat.stderr.strip() or resultat.stdout.strip())
    return destination


def retirer(racine: Path, destination: Path) -> None:
    resultat = _git(racine, "worktree", "remove", "--force", str(destination))
    if resultat.returncode != 0:
        raise WorktreeErreur(resultat.stderr.strip() or resultat.stdout.strip())


def courante(racine: Path) -> str:
    """La branche extraite. Un HEAD détaché n'en est pas une : on refuse."""
    resultat = _git(racine, "branch", "--show-current")
    nom = resultat.stdout.strip()
    if resultat.returncode != 0 or not nom:
        detail = (resultat.stderr or resultat.stdout).strip() or "HEAD détaché"
        raise WorktreeErreur(
            f"{racine} n'est pas sur une branche nommée ({detail}). "
            "L'atelier n'invoque personne dans cet état."
        )
    return nom


def propre(racine: Path) -> bool:
    """Aucun changement non enregistré, y compris les fichiers non suivis."""
    resultat = _git(racine, "status", "--porcelain")
    if resultat.returncode != 0:
        raise WorktreeErreur(
            f"impossible de lire l'état de {racine} : "
            f"{(resultat.stderr or resultat.stdout).strip()}"
        )
    return resultat.stdout == ""


def ranger(racine: Path, message: str) -> list[str]:
    """Enregistre ce qui traîne dans le worktree, sur la branche courante.

    Un agent rend souvent la main sur un répertoire sale : un fichier
    non suivi, une suppression que `crons/tour.sh` vient de faire. Le
    lot suivant butait alors sur `preparer_lot`, qui refuse — à raison —
    d'effacer du travail, et il fallait qu'une personne commite à la
    main pour débloquer la file. Une cascade, pas une panne isolée.

    Ranger n'efface rien et ne réinitialise rien : c'est l'option
    « enregistre » que le refus proposait déjà, prise toute seule. Le
    travail reste dans l'historique de la branche du lot, daté, et se
    retrouve avec un `git log`.

    Rend la liste des chemins rangés ; vide si le worktree était propre.
    """
    racine = Path(racine)
    dedans = _git(racine, "rev-parse", "--is-inside-work-tree")
    if dedans.returncode != 0:
        # Pas un dépôt git : il n'y a rien à ranger, et ce n'est pas au
        # rangement d'en faire une affaire. `preparer_lot` le dira au
        # coder, qui est le seul à en avoir besoin.
        return []
    etat = _git(racine, "status", "--porcelain")
    if etat.returncode != 0:
        raise WorktreeErreur(
            f"impossible de lire l'état de {racine} : "
            f"{(etat.stderr or etat.stdout).strip()}"
        )
    lignes = [l for l in etat.stdout.splitlines() if l.strip()]
    if not lignes:
        return []
    ajout = _git(racine, "add", "-A")
    if ajout.returncode != 0:
        raise WorktreeErreur(
            f"impossible de ranger {racine} : {(ajout.stderr or ajout.stdout).strip()}"
        )
    commit = _git(
        racine,
        "-c", "user.email=atelier@forge",
        "-c", "user.name=Atelier",
        "-c", "commit.gpgsign=false",
        "commit", "-m", message,
    )
    if commit.returncode != 0:
        raise WorktreeErreur(
            f"impossible d'enregistrer {racine} : "
            f"{(commit.stderr or commit.stdout).strip()}"
        )
    return [l[3:] for l in lignes]


def _existe(racine: Path, ref: str) -> bool:
    return _git(racine, "rev-parse", "--verify", "--quiet", ref).returncode == 0


def _ref_de_base(racine: Path, base: str) -> str:
    """`origin/<base>` si elle est là, sinon `<base>` locale. On ne va pas chercher le réseau."""
    for candidat in (f"refs/remotes/origin/{base}", f"origin/{base}", f"refs/heads/{base}", base):
        if _existe(racine, candidat):
            return candidat
    raise WorktreeErreur(
        f"branche de base introuvable : {base}. "
        f"Ni origin/{base} ni {base} n'existent dans ce worktree."
    )


def _ancetre_commun(racine: Path, a: str, b: str) -> bool:
    return _git(racine, "merge-base", a, b).returncode == 0


def _extraire(racine: Path, *args: str) -> None:
    resultat = _git(racine, "checkout", *args)
    if resultat.returncode != 0:
        raise WorktreeErreur(
            f"impossible d'extraire {' '.join(args)} : "
            f"{(resultat.stderr or resultat.stdout).strip()}. "
            "L'atelier n'a rien effacé ni réinitialisé."
        )


def preparer_lot(worktree: Path, branche: str, base: str) -> str:
    """Place le worktree du rôle sur la branche du lot, sans détruire de travail.

    Le worktree est permanent (`ForgeHistory-coder`). La branche du lot
    est temporaire (`prefixe_branche` + slug). On crée cette branche
    depuis la base du produit, ou on la reprend si elle existe et
    partage un ancêtre avec cette base. On ne fait jamais
    `reset --hard` ni `checkout -f`.
    """
    racine = Path(worktree)
    if not (racine / ".git").exists() and not (racine / ".git").is_file():
        raise WorktreeErreur(
            f"{racine} n'est pas un dépôt git : impossible de préparer {branche}."
        )
    if not propre(racine):
        try:
            actuelle = courante(racine)
        except WorktreeErreur:
            actuelle = "?"
        raise WorktreeErreur(
            f"le worktree {racine} contient des modifications non enregistrées "
            f"(branche {actuelle}). L'atelier ne les efface pas : enregistre, "
            "déplace ou mets de côté ce travail, puis relance."
        )

    ref_base = _ref_de_base(racine, base)
    actuelle = courante(racine)

    if actuelle == branche:
        if not _ancetre_commun(racine, ref_base, "HEAD"):
            raise WorktreeErreur(
                f"la branche {branche} n'a pas d'ancêtre commun avec {base} : "
                "elle est incohérente. L'atelier refuse de la réécrire. "
                "Inspecte-la à la main."
            )
        return actuelle

    if _existe(racine, f"refs/heads/{branche}"):
        if not _ancetre_commun(racine, ref_base, branche):
            raise WorktreeErreur(
                f"la branche {branche} existe mais n'a pas d'ancêtre commun "
                f"avec {base} : elle est incohérente. L'atelier refuse de la "
                "réécrire. Inspecte-la à la main."
            )
        _extraire(racine, branche)
    elif _existe(racine, f"refs/remotes/origin/{branche}"):
        if not _ancetre_commun(racine, ref_base, f"origin/{branche}"):
            raise WorktreeErreur(
                f"origin/{branche} n'a pas d'ancêtre commun avec {base} : "
                "elle est incohérente. L'atelier refuse de la réécrire."
            )
        _extraire(racine, "-b", branche, "--track", f"origin/{branche}")
    else:
        _extraire(racine, "-b", branche, ref_base)

    verifie = courante(racine)
    if verifie != branche:
        raise WorktreeErreur(
            f"après préparation, la branche courante est {verifie}, pas {branche}. "
            "L'atelier n'invoque personne dans cet état."
        )
    return verifie
