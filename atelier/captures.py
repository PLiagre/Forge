"""Les captures : une image par lot qui touche ce qu'on voit.

Une capture se range sur la branche orpheline `journal`, sous
`captures/<AAAA-MM-JJ>/`, et s'affiche par son adresse
`raw.githubusercontent.com` : c'est ce qu'un commentaire d'issue montre
partout, téléphone compris, sans Pages ni jeton. La branche n'a aucun
contrôle et ne déclenche aucune CI.

Côté VPS, un lot qui touche `jeu/` est photographié par la commande de bout
en bout (`python3 -m forge`), qui rend la carte du monde. Côté PC, le
travail Unity dépose ses images avant de les publier par la même fonction.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from .depot import Depot

BRANCHE = "journal"


def adresse(depot_github: str, chemin: str) -> str:
    return f"https://raw.githubusercontent.com/{depot_github}/{BRANCHE}/{chemin}"


def publier(depot: Depot, depot_github: str, fichiers: list[Path], dossier: str) -> list[str]:
    """Pousse les images sur la branche `journal` ; rend leurs adresses. Une
    publication à la fois (verrou « captures ») : les tours parallèles et le
    journal partagent le même worktree de la branche."""
    fichiers = [Path(f) for f in fichiers if Path(f).is_file()]
    if not fichiers:
        return []
    with depot.verrous.tenir("captures", attente=depot.ATTENTE_GIT):
        return _publier(depot, depot_github, fichiers, dossier)


def _publier(depot: Depot, depot_github: str, fichiers: list[Path], dossier: str) -> list[str]:
    chemin = depot.racine / ".atelier" / "journal"
    depot.git_code("worktree", "prune")
    if not (chemin / ".git").exists():
        chemin.parent.mkdir(parents=True, exist_ok=True)
        if depot.branche_distante(BRANCHE):
            depot.git("worktree", "add", "--force", "-B", BRANCHE, str(chemin), f"origin/{BRANCHE}")
        else:
            # La branche naît vide (git ≥ 2.42) : extraire master pour tout
            # effacer ensuite coûterait le dépôt entier, LFS compris.
            depot.git_code("branch", "-D", BRANCHE)
            depot.git("worktree", "add", "--orphan", "-b", BRANCHE, str(chemin))
            (chemin / "README.md").write_text(
                "# journal\n\nLes captures de la chaîne de Forge, une par lot. Branche orpheline : "
                "aucun code, aucune CI.\n", encoding="utf-8")
    else:
        if depot.branche_distante(BRANCHE):
            depot.git("checkout", "--force", "-B", BRANCHE, f"origin/{BRANCHE}", cwd=chemin)
    cible = chemin / "captures" / dossier
    cible.mkdir(parents=True, exist_ok=True)
    rangees = []
    for f in fichiers:
        shutil.copy2(f, cible / f.name)
        rangees.append(f"captures/{dossier}/{f.name}")
    depot.enregistrer(chemin, f"Captures : {dossier}")
    depot.git("push", "--quiet", "origin", f"HEAD:refs/heads/{BRANCHE}", cwd=chemin)
    return [adresse(depot_github, r) for r in rangees]


def touche_ce_qu_on_voit(fichiers: list[str]) -> bool:
    return any(f.startswith(("jeu/", "3d/")) for f in fichiers)


# La terre de départ que la capture choisit : la carte porte alors sa fiche
# (siège, suzerain, voisins), ce que la preuve du jalon 2 montre au journal
# (#214, le 3 octobre 2026). 1 : le duché de Bar.
TERRE_DE_DEPART = 1


def carte_du_monde(chemin_depot: Path, sortie: Path, *, ticks: int = 30,
                   depart: int | None = TERRE_DE_DEPART, lecture: str | None = None,
                   largeur: int = 900) -> Path | None:
    """La carte que rend `python3 -m forge` sur la révision du lot, avec la
    fiche de la terre `depart` (None : sans terre choisie), coloriée selon
    `lecture` (None : la lecture par défaut de la commande)."""
    sortie.mkdir(parents=True, exist_ok=True)
    if not (Path(chemin_depot) / "jeu").is_dir():
        return None
    try:
        fini = subprocess.run(
            [sys.executable, "-m", "forge", "--ticks", str(ticks), "--seed", "0", "--sortie", str(sortie),
             "--sans-chronique", "--largeur", str(largeur),
             *(["--depart", str(depart)] if depart is not None else []),
             *(["--lecture", lecture] if lecture else [])],
            cwd=Path(chemin_depot) / "jeu", capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=600)
    except (OSError, subprocess.TimeoutExpired):
        return None
    carte = sortie / "carte.png"
    return carte if fini.returncode == 0 and carte.is_file() else None


# Le liseré que la carte trace autour de la terre choisie : doit rester
# `COULEUR_CHOIX` de jeu/vues/relief/carte1400.py.
LISERE_DE_LA_TERRE = (255, 40, 40)


def zoom_sur_la_terre(carte: Path, sortie: Path, *, largeur: int = 800, hauteur: int = 560) -> Path | None:
    """La terre choisie et ses voisins, découpés dans la carte autour de son
    liseré rouge. Une carte sans liseré (aucune terre choisie) n'a pas de
    zoom : on ne devine pas où regarder."""
    try:
        from PIL import Image, ImageChops
    except ImportError:
        return None
    image = Image.open(carte).convert("RGB")
    canaux = [c.point(lambda v, voulu=voulu: 255 if v == voulu else 0)
              for c, voulu in zip(image.split(), LISERE_DE_LA_TERRE)]
    boite = ImageChops.multiply(ImageChops.multiply(canaux[0], canaux[1]), canaux[2]).getbbox()
    if boite is None:
        return None
    cx, cy = (boite[0] + boite[2]) // 2, (boite[1] + boite[3]) // 2
    largeur, hauteur = min(largeur, image.width), min(hauteur, image.height)
    gauche = max(0, min(cx - largeur // 2, image.width - largeur))
    haut = max(0, min(cy - hauteur // 2, image.height - hauteur))
    sortie.parent.mkdir(parents=True, exist_ok=True)
    image.crop((gauche, haut, gauche + largeur, haut + hauteur)).save(sortie)
    return sortie


def photographier_lot(depot: Depot, depot_github: str, chemin: Path, numero: int | str, sha: str,
                      date: str) -> list[str]:
    """Si le lot touche ce qu'on voit, sa carte ; rend les adresses publiées."""
    try:
        fichiers = depot.fichiers_du_lot(chemin)
    except Exception:  # noqa: BLE001 — une capture manquée ne retient pas le lot
        return []
    if not any(f.startswith("jeu/") for f in fichiers):
        return []
    with tempfile.TemporaryDirectory(prefix="capture-") as tmp:
        carte = carte_du_monde(chemin, Path(tmp))
        if carte is None:
            return []
        nommee = Path(tmp) / f"lot-{numero}-{sha[:7]}-carte.png"
        carte.rename(nommee)
        try:
            return publier(depot, depot_github, [nommee], date)
        except Exception:  # noqa: BLE001
            return []
