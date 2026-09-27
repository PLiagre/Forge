"""Le côté PC d'un lot « machine : pc » (Unity, Blender).

Le pilote du VPS envoie le travail par `workflow_dispatch` au runner du PC
(`.github/workflows/lot-pc.yml`), jamais par `pull_request` : une fourche
ne lance rien sur le PC. Le runner appelle `python -m atelier pc`, qui fait
le même passage de codeur que sur le VPS, avec le poste `codeur_3d`, dans le
worktree persistant de D:\\Forge : `.atelier/chantiers/pc`. Sa `Library`
Unity y reste chaude d'un lot à l'autre ; les packs de l'Asset Store y sont
reliés par une jonction vers ceux de D:\\Forge, jamais copiés dans git.

Puis Unity compile le projet et photographie la scène du désert en batch ;
les images partent sur la branche `journal` et en commentaire de la PR.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
import subprocess
import tempfile

from . import captures, lots
from .depot import Depot
from .github import GitHub
from .lots import Lot
from .pilote import Pilote
from .projet import Projet

PROJET_UNITY = Path("3d") / "unity"
METHODE_CAPTURE = "ForgeLocal3D.Capture.Photographier"


def unity_de(projet_unity: Path) -> Path:
    version = re.search(r"m_EditorVersion:\s*(\S+)",
                        (projet_unity / "ProjectSettings" / "ProjectVersion.txt").read_text(encoding="utf-8"))
    if not version:
        raise RuntimeError("version d'Unity illisible dans ProjectVersion.txt")
    return Path(r"C:\Program Files\Unity\Hub\Editor") / version.group(1) / "Editor" / "Unity.exe"


def lier_vendor(chantier: Path, source: Path) -> None:
    """Les packs de l'Asset Store, par jonction : ignorés par git, jamais copiés."""
    cible = chantier / PROJET_UNITY / "Assets" / "Vendor"
    if cible.exists() or not source.exists():
        return
    subprocess.run(["cmd", "/c", "mklink", "/J", str(cible), str(source)], check=True,
                   capture_output=True, text=True)
    meta = source.parent / "Vendor.meta"
    if meta.exists() and not (cible.parent / "Vendor.meta").exists():
        (cible.parent / "Vendor.meta").write_bytes(meta.read_bytes())


def compiler_et_photographier(chantier: Path, sortie: Path, *, delai: int = 1800) -> tuple[bool, list[Path], str]:
    """Unity en batch : le projet compile-t-il, et que montre la scène ?

    Sans `-nographics` : une caméra doit rendre. Le runner tourne sous la
    session du propriétaire, là où vivent le GPU et la licence Unity.
    """
    projet = chantier / PROJET_UNITY
    journal = sortie / "unity.log"
    sortie.mkdir(parents=True, exist_ok=True)
    # Pas de `-quit` : la capture entre en Play, et c'est elle qui rend la main.
    argv = [str(unity_de(projet)), "-batchmode", "-projectPath", str(projet),
            "-executeMethod", METHODE_CAPTURE, "-logFile", str(journal), "-forgeCaptures", str(sortie)]
    try:
        fini = subprocess.run(argv, capture_output=True, text=True, timeout=delai)
        code = fini.returncode
    except subprocess.TimeoutExpired:
        code = 124
    texte = journal.read_text(encoding="utf-8", errors="replace") if journal.exists() else ""
    erreurs = [l for l in texte.splitlines() if re.search(r"error CS\d+", l)]
    images = sorted(sortie.glob("*.png"))
    fin = "\n".join((erreurs or texte.splitlines())[-30:])
    return code == 0 and not erreurs, images, fin


def travailler(projet: Projet, gh: GitHub, depot: Depot, *, issue: int, branche: str, pr: int,
               essai: int, action: str, vendor: Path | None = None) -> list[str]:
    pilote = Pilote(projet, gh, depot)
    lot = Lot.de(gh.issue(issue))
    detail = gh.pr(pr)
    liste = lots.marques(detail.get("comments") or [])
    depot.fetch()
    chemin = depot.preparer("pc", branche)
    if vendor is not None:
        lier_vendor(chemin, vendor)
    pilote._coder(lot, detail, branche, lots.Action(action, essai=essai), liste, role="codeur_3d", chantier="pc")
    with tempfile.TemporaryDirectory(prefix="unity-") as tmp:
        ok, images, fin = compiler_et_photographier(chemin, Path(tmp))
        nommees = []
        for i, image in enumerate(images):
            nom = Path(tmp) / f"lot-{issue}-{depot.tete(chemin)[:7]}-{i}-{image.name}"
            image.rename(nom)
            nommees.append(nom)
        date = f"{datetime.now(timezone.utc):%Y-%m-%d}"
        urls = captures.publier(depot, gh.depot, nommees, date) if nommees else []
    if ok:
        photos = "".join(f"\n\n📷 ![capture Unity]({u})" for u in urls) or "\n\n(aucune image rendue)"
        gh.commenter_pr(pr, f"🤖 **PC** : Unity compile le projet.{photos}")
    else:
        gh.commenter_pr(pr, f"🤖 **PC** : ⚠️ Unity ne compile pas, ou n'a pas rendu.\n\n```\n{fin}\n```")
    return pilote.lignes
