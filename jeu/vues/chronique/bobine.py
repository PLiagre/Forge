"""La bobine : la planche, filmee image par image.

Aucune seconde direction artistique. La video **est** la planche : un
navigateur sans ecran la photographie a chaque instant, `ffmpeg`
assemble. Le jour ou la planche change, la bobine change avec elle,
parce qu'il n'y a qu'un dessin.

    python3 -m chronique --chronique c.json --html p.html --bobine monde.mp4

Deux executables exterieurs, et ils sont declares : un navigateur
Chromium et `ffmpeg`. Ni l'un ni l'autre n'entre dans `sim/`, `viewer/`
ou le reste de `chronique/` — sans eux, la planche marche toujours.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


class BobineError(RuntimeError):
    """Refus de filmer : outil absent ou photographie manquante."""


# Les noms sous lesquels un Chromium sans ecran se presente selon la
# machine. La liste est cherchee dans le PATH, dans cet ordre.
NOMS_CHROMIUM = (
    "chromium",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
)


def trouver_chromium(chemin: str | None = None) -> str:
    """Rend le chemin d'un Chromium, ou refuse en nommant ce qui manque.

    Une impossibilite se constate avant d'etre invoquee : ici, un nom
    d'executable et un message qui dit quoi installer (regle 9).
    """
    if chemin:
        if not Path(chemin).exists():
            raise BobineError(f"navigateur introuvable : {chemin}")
        return chemin
    for nom in NOMS_CHROMIUM:
        trouve = shutil.which(nom)
        if trouve:
            return trouve
    installes = sorted(
        str(candidat)
        for candidat in Path("/opt/pw-browsers").glob("chromium-*/chrome-linux/chrome")
    )
    if installes:
        return installes[-1]
    raise BobineError(
        "aucun navigateur Chromium dans le PATH ("
        + ", ".join(NOMS_CHROMIUM)
        + ") ; passer --chrome <chemin>"
    )


def trouver_ffmpeg(chemin: str | None = None) -> str:
    """Rend le chemin d'un ffmpeg, ou refuse en nommant ce qui manque."""
    if chemin:
        if not Path(chemin).exists():
            raise BobineError(f"ffmpeg introuvable : {chemin}")
        return chemin
    trouve = shutil.which("ffmpeg")
    if trouve:
        return trouve
    # Un Chromium installe par Playwright vient avec son ffmpeg. Il est
    # taille au plus juste — il decode du MJPEG et encode du VP8, rien de
    # plus — et c'est exactement ce dont la bobine a besoin.
    joints = sorted(Path("/opt/pw-browsers").glob("ffmpeg-*/ffmpeg-linux"))
    if joints:
        return str(joints[-1])
    raise BobineError("ffmpeg absent du PATH ; passer --ffmpeg <chemin>")


def filmer(
    page: Path,
    sortie: Path,
    nombre_images: int,
    *,
    lecture: str = "population",
    largeur: int = 1500,
    hauteur: int = 1330,
    images_par_seconde: int = 8,
    chrome: str | None = None,
    ffmpeg: str | None = None,
) -> Path:
    """Photographie la planche a chaque instant, puis encode la bobine."""
    from vues.chronique.atlas import LECTURES

    if lecture not in LECTURES:
        raise BobineError(
            f"lecture inconnue : '{lecture}' ; les lectures sont "
            + ", ".join(LECTURES)
        )
    binaire_chrome = trouver_chromium(chrome)
    binaire_ffmpeg = trouver_ffmpeg(ffmpeg)
    if nombre_images < 1:
        raise BobineError("refus : aucune image a filmer")
    page = Path(page).resolve()
    if not page.exists():
        raise BobineError(f"planche introuvable : {page}")

    with tempfile.TemporaryDirectory(prefix="bobine-") as dossier:
        atelier = Path(dossier)
        vues = []
        for rang in range(nombre_images):
            # JPEG, et pas PNG : le ffmpeg joint a Chromium sait decoder du
            # MJPEG et rien d'autre. On lui donne ce qu'il sait lire plutot
            # que d'exiger une installation de plus.
            vue = atelier / f"{rang:05d}.jpg"
            subprocess.run(
                [
                    binaire_chrome,
                    "--headless=new",
                    "--disable-gpu",
                    "--no-sandbox",
                    "--hide-scrollbars",
                    f"--window-size={largeur},{hauteur}",
                    f"--screenshot={vue}",
                    "--virtual-time-budget=4000",
                    f"file://{page}?image={rang}&lecture={lecture}",
                ],
                check=True,
                capture_output=True,
            )
            if not vue.exists():
                raise BobineError(f"le navigateur n'a rien rendu pour l'image {rang}")
            vues.append(vue)
        sortie = Path(sortie)
        sortie.parent.mkdir(parents=True, exist_ok=True)
        rendu = subprocess.run(
            [
                binaire_ffmpeg,
                "-y",
                "-loglevel", "error",
                "-f", "image2pipe",
                "-vcodec", "mjpeg",
                "-framerate", str(images_par_seconde),
                # `pipe:0`, et pas `-` : le ffmpeg joint a Chromium est
                # compile avec les seuls protocoles `pipe` et `file`, et il
                # ne reconnait pas le tiret comme une entree standard.
                "-i", "pipe:0",
                "-c:v", "libvpx",
                "-b:v", "3M",
                "-pix_fmt", "yuv420p",
                str(sortie),
            ],
            input=b"".join(vue.read_bytes() for vue in vues),
            capture_output=True,
        )
        if rendu.returncode != 0:
            raise BobineError(
                "ffmpeg a refuse la bobine : "
                + rendu.stderr.decode("utf-8", "replace").strip()[:400]
            )
    return sortie
