"""Le côté PC d'un lot « machine : pc » (Unity, Blender).

La session du meneur d'un lot `pc` vit sur le PC : c'est là que se font son
plan, ses étapes et ses corrections. Le pilote du VPS envoie chaque passage
par `workflow_dispatch` au runner du PC (`.github/workflows/lot-pc.yml`),
jamais par `pull_request` : une fourche ne lance rien sur le PC. Le runner
appelle `python -m atelier pc`, qui relit GitHub, fait le pas que le lot
attend, et répond toujours : un compte rendu, ou une attente.

Le lot travaille dans le worktree persistant de D:\\Forge,
`.atelier/chantiers/pc` : sa `Library` Unity y reste chaude d'un lot à
l'autre ; les packs de l'Asset Store y sont reliés par une jonction, jamais
copiés dans git.

Quand le plan est fini, Unity juge la révision poussée : le projet
compile-t-il, ses tests EditMode passent-ils, et que montre la scène ? Ce
qu'il a vu entre dans le compte rendu (le relecteur, sur le VPS, n'a pas
Unity), et les images sur la branche `journal`.
"""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from . import agents as agents_mod
from . import captures, lots
from .depot import Depot
from .github import GitHub, etat_des_controles
from .lots import Lot
from .pilote import Photos, Pilote
from .projet import Projet

PROJET_UNITY = Path("3d") / "unity"
METHODE_CAPTURE = "ForgeLocal3D.Capture.Photographier"
# Les assemblies de tests EditMode du projet. La liste se sépare par « ; » :
# avec une virgule, Unity ne joue aucun cas et sort 0.
ASSEMBLIES_DE_TESTS = "Forge.Pont.Tests;Forge.Interface.Tests"
CHANTIER = "pc"


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


def _lancer_unity(argv: list[str], delai: int) -> int:
    """Unity, avec une borne : il peut pendre après avoir fini son travail. On
    l'arrête alors avec tout ce qu'il a lancé, et le résultat se lit dans ce
    qu'il a écrit, pas dans son code de sortie."""
    processus = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        return processus.wait(timeout=delai)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(processus.pid)], capture_output=True, timeout=60)
        processus.wait()
        return 124


def jouer_les_tests(chantier: Path, sortie: Path, *, delai: int = 1800) -> tuple[int, int, str]:
    """Les tests EditMode du projet : (cas joués, cas en échec, ce qui a
    échoué). Le compte se lit dans le XML : zéro cas joué est un échec, pas un
    succès."""
    projet = (chantier / PROJET_UNITY).resolve()
    sortie.mkdir(parents=True, exist_ok=True)
    resultats, journal = (sortie / "tests.xml").resolve(), (sortie / "tests.log").resolve()
    _lancer_unity([str(unity_de(projet)), "-batchmode", "-projectPath", str(projet), "-runTests",
                   "-testPlatform", "EditMode", "-assemblyNames", ASSEMBLIES_DE_TESTS,
                   "-testResults", str(resultats), "-logFile", str(journal)], delai)
    if not resultats.is_file():
        texte = journal.read_text(encoding="utf-8", errors="replace") if journal.is_file() else ""
        erreurs = [l for l in texte.splitlines() if re.search(r"error CS\d+", l)]
        return 0, 0, "\n".join((erreurs or texte.splitlines())[-20:]) or "Unity n'a pas écrit de résultats"
    racine = ET.parse(resultats).getroot()
    joues, echecs = int(racine.get("testcasecount") or 0), int(racine.get("failed") or 0)
    rates = [cas.get("fullname") or cas.get("name") or "?" for cas in racine.iter("test-case")
             if cas.get("result") == "Failed"]
    return joues, echecs, "\n".join(rates[:20])


def compiler_et_photographier(chantier: Path, sortie: Path, *, delai: int = 1800,
                              scenario: str = "") -> tuple[bool, list[Path], str]:
    """Unity sans écran : le projet compile-t-il, et que montre la scène ? Le
    plan fixe d'abord, puis une photo par scénario de capture du groupe
    `scenario`, si le meneur en a nommé un.

    Sans `-nographics` : une caméra doit rendre. Sans `-quit` : la capture
    entre en Play, et c'est elle qui rend la main."""
    projet = (chantier / PROJET_UNITY).resolve()
    sortie = sortie.resolve()
    journal = sortie / "unity.log"
    sortie.mkdir(parents=True, exist_ok=True)
    code = _lancer_unity([str(unity_de(projet)), "-batchmode", "-projectPath", str(projet),
                          "-executeMethod", METHODE_CAPTURE, "-logFile", str(journal), "-forgeCaptures", str(sortie),
                          *(["-forgeScenario", scenario] if scenario else [])], delai)
    texte = journal.read_text(encoding="utf-8", errors="replace") if journal.exists() else ""
    erreurs = [l for l in texte.splitlines() if re.search(r"error CS\d+", l)]
    rate = [l for l in texte.splitlines() if "CAPTURE : le scénario" in l and "a échoué" in l]
    images = sorted(sortie.glob("*.png"))
    fin = "\n".join((erreurs or rate or texte.splitlines())[-30:])
    return code in (0, 124) and not erreurs and not rate and bool(images), images, fin


def regarder_avec_unity(chantier: Path, numero: int, sha: str, date: str, *, tests=jouer_les_tests,
                        unity=compiler_et_photographier, publier, scenario: str = "") -> Photos:
    """Unity sur la révision poussée : ses tests EditMode, puis ce que montre
    la scène. Une panne d'Unity ne perd jamais le travail du meneur : elle se dit."""
    with tempfile.TemporaryDirectory(prefix="unity-", ignore_cleanup_errors=True) as tmp:
        try:
            joues, echecs, rates = tests(chantier, Path(tmp) / "tests")
        except Exception as e:  # noqa: BLE001
            return Photos(note=f"⚠️ **Unity** n'a pas tourné sur le PC : {e}", marque={"unity": "absent"})
        if joues == 0 or echecs:
            quoi = "n'a joué aucun test EditMode" if joues == 0 else f"{echecs} test(s) EditMode en échec sur {joues}"
            return Photos(marque={"unity": "rouge"},
                          note=f"⚠️ **Unity**, sur le PC : {quoi}.\n\n```\n{rates}\n```")
        try:
            ok, images, fin = unity(chantier, Path(tmp) / "captures", scenario=scenario)
        except Exception as e:  # noqa: BLE001
            return Photos(marque={"unity": "vert", "photo": "absente"},
                          note=f"✅ **Unity** : {joues} tests EditMode verts sur le PC. ⚠️ La capture n'a pas tourné : {e}")
        nommees = []
        for i, image in enumerate(images):
            nom = Path(tmp) / f"lot-{numero}-{sha[:7]}-{i}-{image.name}"
            image.rename(nom)
            nommees.append(nom)
        try:
            urls = publier(nommees, date) if nommees else []
        except Exception:  # noqa: BLE001 — une capture manquée ne retient pas le lot
            urls = []
    dit = f"✅ **Unity** : le projet compile et ses {joues} tests EditMode sont verts sur le PC."
    if ok:
        montre = f" Capture « {scenario} » jouée." if scenario else " Plan fixe de la scène seulement."
        return Photos(urls=urls, marque={"unity": "vert", "photo": "propre" if scenario else "plan-fixe"},
                      note=dit + montre + ("" if urls else " Les images n'ont pas pu être publiées."))
    return Photos(urls=urls, marque={"unity": "vert", "photo": "absente"},
                  note=f"{dit} ⚠️ La capture n'a pas abouti :\n\n```\n{fin}\n```")


def travailler(projet: Projet, gh: GitHub, depot: Depot, *, issue: int, journal: Path, vendor: Path | None = None,
               executeur_agents: agents_mod.Executeur = agents_mod.executer,
               unity=compiler_et_photographier, tests=jouer_les_tests, publier=captures.publier) -> list[str]:
    """Un pas du meneur sur le PC ; il répond toujours au pilote du VPS.

    Le pas se relit sur GitHub : le plan si le lot n'a pas de PR, sinon
    l'étape, la correction ou le conflit que le lot attend. Tout ce qui casse
    avant la réponse est une attente : ni le meneur ni le lot n'y sont pour
    rien, et sans marque le VPS attendrait un jour."""
    pilote = Pilote(projet, gh, depot, journal=journal, executeur_agents=executeur_agents, machine="pc")
    date = f"{pilote.maintenant():%Y-%m-%d}"
    numero_pr: int | None = None
    lot: Lot | None = None

    def photographe(chemin: Path, lot: Lot, sha: str) -> Photos:
        return regarder_avec_unity(chemin, lot.numero, sha, date, unity=unity, tests=tests, scenario=pilote.capture,
                                   publier=lambda fichiers, jour: publier(depot, gh.depot, fichiers, jour))

    try:
        lot = Lot.de(gh.issue(issue))
        depot.fetch()
        branche = lot.branche(projet.prefixe_branche)
        resume = gh.pr_de_branche(branche)
        if resume is None:
            chemin = depot.preparer(CHANTIER, branche)
            if vendor is not None:
                lier_vendor(chemin, vendor)
            pilote._planifier(lot, chantier=CHANTIER, marquer_attente=True)
            return pilote.lignes
        numero_pr = resume["number"]
        pr = gh.pr(numero_pr)
        # L'envoi auquel on répond ne compte pas : le pas se décide sans lui.
        liste = [m for m in lots.marques(pr.get("comments") or []) if m.get("etat") != lots.ENVOYE]
        action = lots.action_suivante(pr, etat_des_controles(pr)[0], liste, corrections_max=projet.corrections_max,
                                      coupures_max=projet.coupures_max)
        if action.nom not in ("etape", "corriger_ci", "corriger_relecture", "conflit"):
            # Le lot n'attend plus le PC : la marque le dit, et le VPS reprend la main.
            pilote.marquer_attente(lot, numero_pr, f"le lot n'attend pas un passage du meneur ({action.nom})")
            return pilote.lignes
        chemin = depot.preparer(CHANTIER, branche)
        if vendor is not None:
            lier_vendor(chemin, vendor)
        pilote.passage(lot, pr, action, liste, chantier=CHANTIER, photographe=photographe, marquer_attente=True)
    except Exception as e:
        try:
            if lot is not None:
                pilote.marquer_attente(lot, numero_pr, "le passage du PC a cassé avant de répondre : "
                                                       f"`{type(e).__name__}: {str(e)[:300]}`")
        except Exception:  # noqa: BLE001 — GitHub injoignable : le VPS renverra au bout d'un jour
            pass
        raise
    return pilote.lignes


def repondre_au_silence(projet: Projet, gh: GitHub, depot: Depot, *, issue: int, raison: str, journal: Path) -> str:
    """Un passage tombé hors de Python (runner coupé, PC en veille, processus
    tué) ne laisse aucune marque, et le VPS attendrait un jour : `lot-pc.yml`
    répond à sa place par une attente. Seul un envoi resté sans réponse en
    reçoit une : une réponse déjà écrite se garde."""
    lot = Lot.de(gh.issue(issue))
    resume = gh.pr_de_branche(lot.branche(projet.prefixe_branche))
    commentaires = (gh.pr(resume["number"]) if resume else gh.issue(issue)).get("comments") or []
    siens = lots.du_meneur(lots.marques(commentaires))
    if not siens or siens[-1].get("etat") != lots.ENVOYE:
        return f"RIEN — le lot #{issue} n'attend pas le PC ({siens[-1].get('etat') if siens else 'aucun envoi'})"
    Pilote(projet, gh, depot, journal=journal, machine="pc").marquer_attente(lot, resume["number"] if resume else None, raison)
    return f"attente marquée sur le lot #{issue}"
