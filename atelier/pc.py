"""Le côté PC d'un lot « machine : pc » (Unity, Blender).

Le pilote du VPS envoie le travail par `workflow_dispatch` au runner du PC
(`.github/workflows/lot-pc.yml`), jamais par `pull_request` : une fourche
ne lance rien sur le PC. Le runner appelle `python -m atelier pc`, qui fait
le même passage de codeur que sur le VPS, avec le poste `codeur_3d`, dans le
worktree persistant de D:\\Forge : `.atelier/chantiers/pc`. Sa `Library`
Unity y reste chaude d'un lot à l'autre ; les packs de l'Asset Store y sont
reliés par une jonction vers ceux de D:\\Forge, jamais copiés dans git.

Puis Unity compile la révision poussée et photographie la scène du désert en
batch ; ce qu'il a vu entre dans le compte rendu du codeur (le relecteur, sur
le VPS, n'a pas Unity), et les images sur la branche `journal`.

Le pilote du VPS attend une réponse sur la PR : un compte rendu (fait,
échec) ou une attente. La partie PC n'avance que quand le PC est allumé.
"""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import tempfile

from . import agents as agents_mod
from . import captures, lots
from .depot import Depot
from .github import GitHub
from .lots import Lot
from .pilote import Photos, Pilote
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


def regarder_avec_unity(chantier: Path, numero: int, sha: str, date: str, *, unity, publier) -> Photos:
    """Unity sur la révision poussée : compile-t-il, et que montre la scène ?
    Une panne d'Unity ne perd jamais le travail du codeur : elle se dit."""
    with tempfile.TemporaryDirectory(prefix="unity-") as tmp:
        try:
            ok, images, fin = unity(chantier, Path(tmp))
        except Exception as e:  # noqa: BLE001
            return Photos(note=f"⚠️ **Unity** n'a pas tourné sur le PC : {e}", marque={"unity": "absent"})
        nommees = []
        for i, image in enumerate(images):
            nom = Path(tmp) / f"lot-{numero}-{sha[:7]}-{i}-{image.name}"
            image.rename(nom)
            nommees.append(nom)
        try:
            urls = publier(nommees, date) if nommees else []
        except Exception:  # noqa: BLE001 — une capture manquée ne retient pas le lot
            urls = []
    if ok:
        return Photos(urls=urls, marque={"unity": "vert"},
                      note="✅ **Unity** compile cette révision sur le PC" + ("." if urls else ", sans rendre d'image."))
    return Photos(urls=urls, marque={"unity": "rouge"},
                  note=f"⚠️ **Unity** ne compile pas cette révision sur le PC, ou n'a pas rendu :\n\n```\n{fin}\n```")


def travailler(projet: Projet, gh: GitHub, depot: Depot, *, issue: int, branche: str, pr: int,
               essai: int, action: str, vendor: Path | None = None,
               executeur_agents: agents_mod.Executeur = agents_mod.executer,
               unity=compiler_et_photographier, publier=captures.publier) -> list[str]:
    """Un passage du codeur sur le PC ; il répond toujours au pilote du VPS.

    Tout ce qui casse avant la réponse est une attente : ni le codeur ni le
    lot n'y sont pour rien, et sans marque le VPS attendrait un jour."""
    pilote = Pilote(projet, gh, depot, executeur_agents=executeur_agents)
    date = f"{pilote.maintenant():%Y-%m-%d}"

    def photographe(chemin: Path, lot: Lot, sha: str) -> Photos:
        carte = pilote._photographier(chemin, lot, sha)
        vu = regarder_avec_unity(chemin, lot.numero, sha, date, unity=unity,
                                 publier=lambda fichiers, jour: publier(depot, gh.depot, fichiers, jour))
        return Photos(urls=vu.urls + carte.urls, note=vu.note, marque=vu.marque)

    try:
        lot = Lot.de(gh.issue(issue))
        detail = gh.pr(pr)
        liste = lots.marques(detail.get("comments") or [])
        depot.fetch()
        chemin = depot.preparer("pc", branche)
        if vendor is not None:
            lier_vendor(chemin, vendor)
        pilote._coder(lot, detail, branche, lots.Action(action, essai=essai), liste, role="codeur_3d",
                      chantier="pc", photographe=photographe, marquer_attente=True)
    except Exception as e:
        try:
            pilote.marquer_attente(pr, "codeur_3d", f"le passage du PC a cassé avant de répondre : "
                                                    f"`{type(e).__name__}: {str(e)[:300]}`")
        except Exception:  # noqa: BLE001 — GitHub injoignable : le VPS renverra au bout d'un jour
            pass
        raise
    return pilote.lignes
