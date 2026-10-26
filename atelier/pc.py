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


def compiler_et_photographier(chantier: Path, sortie: Path, *, delai: int = 1800,
                              lot: int | None = None, drapeaux: tuple[str, ...] = ()) -> tuple[bool, list[Path], str]:
    """Unity en batch : le projet compile-t-il, et que montre la scène ? Le
    plan fixe d'abord, puis une photo par scénario de capture du `lot`
    (`<scène>--<nom>.png`, voir `ScenarioDeCapture.cs`). `drapeaux` : ceux
    que le brief donne à sa capture (`sessions_de_capture`).

    Sans `-nographics` : une caméra doit rendre. Le runner tourne sous la
    session du propriétaire, là où vivent le GPU et la licence Unity.
    """
    projet = chantier / PROJET_UNITY
    journal = sortie / "unity.log"
    sortie.mkdir(parents=True, exist_ok=True)
    # Pas de `-quit` : la capture entre en Play, et c'est elle qui rend la main.
    argv = [str(unity_de(projet)), "-batchmode", "-projectPath", str(projet),
            "-executeMethod", METHODE_CAPTURE, "-logFile", str(journal), "-forgeCaptures", str(sortie),
            *(["-forgeLot", str(lot)] if lot is not None else []), *drapeaux]
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


# La capture que le brief écrit, la chaîne la rejoue telle quelle. Jusqu'au
# 22 octobre 2026, le PC photographiait sans les drapeaux du brief : graine
# et tick par défaut (#624, #657), et sans `-forgeServiceEpreuve`, #781 a
# échoué à sa seconde photo puis s'est bloqué, sa contre-épreuve jamais jouée.
_TABLEAU = re.compile(r"\$(\w+)\s*=\s*@\(([^)]*)\)")
_JETON = re.compile(r"'([^']*)'|\"([^\"]*)\"|([^\s'\"]+)")
# Ce que la chaîne donne elle-même à chaque session.
_DRAPEAUX_DE_LA_CHAINE = ("-forgeLot", "-forgeCaptures")
# La photo et deux contre-épreuves au plus : chaque session coûte un Unity.
SESSIONS_MAX = 3


def _drapeaux(jetons: list[str]) -> dict[str, str | None]:
    """Les drapeaux `-forge…` d'une commande, et la valeur qui suit chacun."""
    vus: dict[str, str | None] = {}
    for i, jeton in enumerate(jetons):
        if jeton.startswith("-forge"):
            suivant = jetons[i + 1] if i + 1 < len(jetons) else None
            vus[jeton] = suivant if suivant is not None and not suivant.startswith("-") else None
    return vus


def sessions_de_capture(brief: str, lot: int) -> list[tuple[str, ...]]:
    """Les sessions de capture que le brief écrit pour ce lot : chaque
    commande de `ForgeLocal3D.Capture.Photographier` qui passe `-forgeLot
    <lot>`, directe ou par un tableau PowerShell (`$commun = @(…)`, puis
    `@commun`), donne ses autres drapeaux `-forge…`. La première session,
    celle qui en a le moins, est la photo ; les suivantes, ses
    contre-épreuves. Une valeur que le brief laisse à remplir (`$dossier`,
    `<cellule>`) ne se rejoue pas : sa commande est écartée. Vide : le brief
    n'écrit aucune capture, le PC photographie comme avant."""
    tableaux: dict[str, list[str]] = {}
    commandes: list[list[str]] = []
    for ligne in brief.splitlines():
        for morceau in re.findall(r"`([^`]+)`", ligne) or [ligne]:
            tableau = _TABLEAU.search(morceau)
            if tableau:
                jetons = [a or b for a, b in re.findall(r"'([^']*)'|\"([^\"]*)\"", tableau.group(2))]
                if METHODE_CAPTURE in jetons:
                    tableaux[tableau.group(1)] = jetons
                    commandes.append(jetons)
                continue
            jetons = []
            for a, b, c in _JETON.findall(morceau):
                jeton = a or b or c
                jetons += tableaux.get(jeton[1:], [jeton]) if jeton.startswith("@") else [jeton]
            if METHODE_CAPTURE in jetons:
                commandes.append(jetons)
    sessions: list[tuple[str, ...]] = []
    for jetons in commandes:
        vus = _drapeaux(jetons)
        if vus.get("-forgeLot") != str(lot):
            continue
        gardes = {d: v for d, v in vus.items() if d not in _DRAPEAUX_DE_LA_CHAINE}
        if any(v is not None and v[:1] in "$<" for v in gardes.values()):
            continue
        session = tuple(j for d, v in gardes.items() for j in ((d,) if v is None else (d, v)))
        if session not in sessions:
            sessions.append(session)
    return sorted(sessions, key=len)[:SESSIONS_MAX]


# La part des pixels qui doivent avoir changé depuis le plan fixe pour qu'une
# photo soit propre au lot. Deux photos de suite ne sont jamais identiques à
# l'octet : le 4 octobre 2026, un scénario dont la caméra n'avait pas bougé a
# rendu une image d'autres octets, et identique à l'œil.
ECART_MIN = 0.02


def _ecart(image: Path) -> float | None:
    """L'écart au plan fixe qu'Unity a mesuré (`<photo>.ecart.txt`) ; None s'il manque."""
    try:
        return float(image.with_suffix(".ecart.txt").read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _photo_du_lot(images: list[Path]) -> tuple[str, str]:
    """Le plan fixe (`<scène>.png`) ne montre rien d'un lot ; une photo propre
    vient d'un de ses scénarios (`<scène>--<nom>.png`), et Unity y mesure au
    moins `ECART_MIN` de pixels changés depuis le plan fixe."""
    propres = [i for i in images if "--" in i.stem]
    if not propres:
        return lots.PHOTO_ABSENTE, "⚠️ **Photo** : aucune photo propre au lot, seulement le plan fixe de la scène."
    ecarts = {i.stem.split("--", 1)[1]: _ecart(i) for i in propres}
    pareilles = [f"« {n} » ({'écart non mesuré' if e is None else f'{e:.1%} des pixels changés'})"
                 for n, e in ecarts.items() if e is None or e < ECART_MIN]
    if pareilles:
        return lots.PHOTO_IDENTIQUE, ("⚠️ **Photo** : identique au plan fixe, il faut au moins "
                                      f"{ECART_MIN:.0%} des pixels changés : " + ", ".join(pareilles) + ".")
    return lots.PHOTO_PROPRE, ("📸 **Photo** : propre au lot, " + ", ".join(f"« {n} » ({e:.0%} des pixels changés)"
                                                                         for n, e in ecarts.items())
                               + ", après le plan fixe.")


_TRACE = re.compile(r"^CAPTURE_\w+.*$", re.M)
# Ce qu'une session joint au compte rendu : le relecteur, sur le VPS, n'a
# que ces lignes pour juger une session qu'il ne peut pas rejouer.
TRACES_MAX, RAPPORT_MAX = 20, 12000


def _ce_qu_elle_a_ecrit(dossier: Path) -> str:
    """Les traces `CAPTURE_…` du journal d'Unity et les rapports `.json` des
    scénarios d'une session, repliés sous un `<details>`."""
    journal = dossier / "unity.log"
    traces = _TRACE.findall(journal.read_text(encoding="utf-8", errors="replace")) if journal.exists() else []
    blocs = []
    if traces:
        blocs.append("Traces d'Unity :\n\n```\n" + "\n".join(traces[-TRACES_MAX:]) + "\n```")
    for rapport in sorted(dossier.glob("*.json")):
        texte = rapport.read_text(encoding="utf-8-sig", errors="replace")
        coupe = f"\n… coupé à {RAPPORT_MAX} caractères sur {len(texte)}" if len(texte) > RAPPORT_MAX else ""
        blocs.append(f"`{rapport.name}` :\n\n```json\n{texte[:RAPPORT_MAX]}{coupe}\n```")
    if not blocs:
        return ""
    return "\n\n<details><summary>Ce que la session a écrit</summary>\n\n" + "\n\n".join(blocs) + "\n\n</details>"


def _en_ligne(drapeaux: tuple[str, ...]) -> str:
    return "`" + " ".join(drapeaux) + "`"


def regarder_avec_unity(chantier: Path, numero: int, sha: str, date: str, *, unity, publier,
                        brief: str = "") -> Photos:
    """Unity sur la révision poussée : compile-t-il, et que montre la scène ?
    La photo se prend comme le brief l'écrit, puis chaque contre-épreuve
    qu'il écrit se joue dans un dossier neuf (`sessions_de_capture`).
    Une panne d'Unity ne perd jamais le travail du codeur : elle se dit."""
    sessions = sessions_de_capture(brief, numero) or [()]
    with tempfile.TemporaryDirectory(prefix="unity-") as tmp:
        jouees = []
        for n, drapeaux in enumerate(sessions):
            dossier = Path(tmp) / f"session-{n}"
            try:
                ok, images, fin = unity(chantier, dossier, lot=numero, drapeaux=drapeaux)
            except Exception as e:  # noqa: BLE001
                if n == 0:
                    return Photos(note=f"⚠️ **Unity** n'a pas tourné sur le PC : {e}", marque={"unity": "absent"})
                ok, images, fin = False, [], f"{type(e).__name__}: {e}"
            jouees.append((drapeaux, ok, images, fin, _ce_qu_elle_a_ecrit(dossier)))
        photo, sur_la_photo = _photo_du_lot(jouees[0][2])
        nommees = []
        for n, (_, _, images, _, _) in enumerate(jouees):
            for i, image in enumerate(images):
                nom = Path(tmp) / (f"lot-{numero}-{sha[:7]}-{i}-{image.name}" if n == 0
                                   else f"lot-{numero}-{sha[:7]}-contre{n}-{i}-{image.name}")
                image.rename(nom)
                nommees.append(nom)
        try:
            urls = publier(nommees, date) if nommees else []
        except Exception:  # noqa: BLE001 — une capture manquée ne retient pas le lot
            urls = []
    drapeaux, ok, _, fin, ecrit = jouees[0]
    capture = f"\n\n🎬 **Capture** : {_en_ligne(drapeaux)}, comme l'écrit le brief." if drapeaux else ""
    contres = "".join(
        f"\n\n🔁 **Contre-épreuve** {_en_ligne(d)} : Unity "
        + ("a fini la session (sortie 0)" if bon else f"n'a pas fini la session :\n\n```\n{dernier}\n```")
        + f", {len(images)} image(s).{texte}"
        for d, bon, images, dernier, texte in jouees[1:])
    if ok:
        return Photos(urls=urls, marque={"unity": "vert", "photo": photo},
                      note="✅ **Unity** compile cette révision sur le PC" + ("." if urls else ", sans rendre d'image.")
                           + f"\n\n{sur_la_photo}{capture}{ecrit}{contres}")
    # Un scénario qui échoue après la compilation n'est pas une erreur de
    # compilation : le 22 octobre 2026, le 404 nommé de #781 se lisait ainsi.
    quoi = ("ne compile pas cette révision sur le PC" if re.search(r"error CS\d+", fin)
            else "compile cette révision sur le PC, mais la capture n'a pas abouti")
    return Photos(urls=urls, marque={"unity": "rouge"},
                  note=f"⚠️ **Unity** {quoi} :\n\n```\n{fin}\n```{capture}{ecrit}{contres}")


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
        brief = chemin / lot.brief(projet.dossier_briefs)
        vu = regarder_avec_unity(chemin, lot.numero, sha, date, unity=unity,
                                 publier=lambda fichiers, jour: publier(depot, gh.depot, fichiers, jour),
                                 brief=brief.read_text(encoding="utf-8") if brief.is_file() else "")
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


def repondre_au_silence(projet: Projet, gh: GitHub, depot: Depot, *, pr: int, raison: str) -> str:
    """Un passage tombé hors de Python (runner coupé, PC en veille, processus
    tué, PowerShell qui casse avant `travailler`) ne laisse aucune marque, et
    le VPS attendrait un jour : lot-pc.yml répond à sa place par une attente.

    Seul un envoi resté sans réponse en reçoit une : ce qui casse en Python,
    `travailler` le marque lui-même, et une réponse déjà écrite se garde."""
    codeur = [m for m in lots.marques(gh.pr(pr).get("comments") or []) if m.get("role") == "codeur_3d"]
    if not codeur or codeur[-1].get("etat") != "envoye":
        return f"RIEN — la PR #{pr} n'attend pas le PC ({codeur[-1].get('etat') if codeur else 'aucun envoi'})"
    Pilote(projet, gh, depot).marquer_attente(pr, "codeur_3d", raison)
    return f"attente marquée sur la PR #{pr}"
