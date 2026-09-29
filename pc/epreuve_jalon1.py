"""L'épreuve du jalon 1 : le panneau d'Unity égale la photographie de sim/ (lot #121).

    py pc\\epreuve_jalon1.py --sortie D [--seed S] [--ticks N] [--cellule C] [--decalage K] [--unity CHEMIN]

La capture Unity lance le service (graine S, poussé au tick N+K), ouvre la scène du
désert en Play et écrit le texte du panneau ; on le compare, nombre par nombre, à
`py -m sim --ticks N --seed S --snapshot-json`. Sortie : 0 égalité, 1 écart,
2 épreuve impossible (Unity introuvable, port pris, photographie ou capture absente).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import signal
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]


def _charger(nom: str, chemin: Path):
    spec = importlib.util.spec_from_file_location(nom, chemin)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# pc/jouer.py met jeu/ sur le chemin d'import : sim/ se lit ensuite comme lui.
JOUER = _charger("jouer", RACINE / "pc" / "jouer.py")
from sim.constants import date_de_tick  # noqa: E402
from sim.service import DEFAULT_SERVICE_PORT, SERVICE_HOST  # noqa: E402

JEU = JOUER.JEU_PY
PROJET_UNITY = RACINE / "3d" / "unity"
VERSION_UNITY = PROJET_UNITY / "ProjectSettings" / "ProjectVersion.txt"
EDITEURS_UNITY = Path(r"C:\Program Files\Unity\Hub\Editor")
SCENE = "Forge_Desert_Ville_ksar_des_sept_puits"
GRAINE_PAR_DEFAUT = 0
TICKS_PAR_DEFAUT = 30
DELAI_UNITY_S = 1800
LIGNES_JOURNAL_CITEES = 30
DEBUT_CITE = 120
EGALITE, ECART, IMPOSSIBLE = 0, 1, 2
NOURRITURE = "nourriture"
ABSENTE = "absente du panier"
# Les libellés de PanneauLieu.Decrire, tels quels : le test vérifie qu'ils y figurent.
LIBELLES = ("Cellule ", " · tick ", "Date : jour ", " de ", "Habitants : ", "Nourriture : ",
            ABSENTE, "Faim : ", " ticks de manque", "Dette de nourriture : ", " kg")
MARQUES_ABSENCE = ("service absent", "lieu illisible")
_N = r"(\S+)"
_LIGNES = (  # (motif, champs) ; l'ordre compte : la dette avant une marchandise quelconque
    (re.compile(re.escape("Cellule ") + _N + re.escape(" · tick ") + _N), (("cellule", int), ("tick", int))),
    (re.compile(re.escape("Date : jour ") + _N + re.escape(" de ") + _N), (("jour", int), ("annee", int))),
    (re.compile(re.escape("Habitants : ") + _N), (("population", int),)),
    (re.compile(re.escape("Nourriture : " + ABSENTE)), ()),
    (re.compile(re.escape("Faim : ") + _N + re.escape(" ticks de manque")), (("hunger_ticks", int),)),
    (re.compile(re.escape("Dette de nourriture : ") + _N + re.escape(" kg")), (("food_deficit_kg", float),)),
)
_MARCHANDISE = re.compile(r"(.+?) : " + _N + re.escape(" kg"))
ETAT = ("population", "hunger_ticks", "food_deficit_kg")  # lus tels quels dans la cellule photographiée
CHAMPS = ("cellule", "tick", "annee", "jour", *ETAT)


def _illisible(texte: str, raison: str) -> ValueError:
    return ValueError(f"panneau illisible : {raison} ; début du texte : {texte[:DEBUT_CITE]!r}")


def lire_panneau(texte: str) -> dict:
    """Le texte du panneau → ses nombres. Une absence ou une ligne inconnue lève ValueError."""
    if not texte.strip():
        raise _illisible(texte, "texte vide")
    if texte.startswith(MARQUES_ABSENCE):
        raise _illisible(texte, "le panneau déclare une absence")
    lu: dict = {"stocks": {}}
    for ligne in texte.split("\n"):
        for motif, champs in _LIGNES:
            trouve = motif.fullmatch(ligne)
            if trouve:
                break
        else:
            champs, trouve = (), _MARCHANDISE.fullmatch(ligne)
            if not trouve:
                raise _illisible(texte, f"ligne inconnue {ligne!r}")
            nom = NOURRITURE if trouve[1] == "Nourriture" else trouve[1]
            if nom in lu["stocks"]:
                raise _illisible(texte, f"marchandise {nom!r} répétée")
            lu["stocks"][nom] = float(trouve[2])
        for (champ, conversion), valeur in zip(champs, trouve.groups()):
            if champ in lu:
                raise _illisible(texte, f"champ {champ} répété")
            try:
                lu[champ] = conversion(valeur)
            except ValueError:
                raise _illisible(texte, f"{champ} n'est pas un nombre : {valeur!r}") from None
    manquants = [champ for champ in CHAMPS if champ not in lu]
    if manquants:
        raise _illisible(texte, f"champs absents : {', '.join(manquants)}")
    return lu


def etat_de_cellule(photographie: dict, cellule: int) -> dict:
    for etat in photographie["cells"]:
        if etat["cell_id"] == cellule:
            return etat
    raise ValueError(f"cell_id {cellule} absent de la photographie")


def champs_compares(panneau: dict, photographie: dict, cellule: int) -> list[tuple[str, object, object]]:
    """(champ, valeur du panneau, valeur de la photographie), le panier clé à clé dans les deux sens."""
    etat = etat_de_cellule(photographie, cellule)
    date = date_de_tick(photographie["tick"])
    attendus = {"cellule": cellule, "tick": photographie["tick"], "annee": date["annee"],
                "jour": date["jour_de_l_annee"]} | {champ: etat[champ] for champ in ETAT}
    lignes = [(champ, panneau[champ], attendus[champ]) for champ in CHAMPS]
    for nom in sorted(set(panneau["stocks"]) | set(etat["stocks"])):
        lignes.append((f"stocks.{nom}", panneau["stocks"].get(nom, ABSENTE), etat["stocks"].get(nom, ABSENTE)))
    return lignes


def comparer(panneau: dict, photographie: dict, cellule: int) -> list[str]:
    return [f"{champ} : panneau {vu!r}, photographie {attendu!r}"
            for champ, vu, attendu in champs_compares(panneau, photographie, cellule) if vu != attendu]


def _entier_positif(valeur: str) -> int:
    if not valeur.isdigit():
        raise argparse.ArgumentTypeError(f"reçu {valeur!r}, attendu un entier ≥ 0")
    return int(valeur)


def _unity_par_defaut() -> Path:
    trouve = re.search(r"m_EditorVersion:\s*(\S+)", VERSION_UNITY.read_text(encoding="utf-8"))
    if trouve is None:
        raise ValueError(f"m_EditorVersion absent de {VERSION_UNITY}")
    return EDITEURS_UNITY / trouve[1] / "Editor" / "Unity.exe"


def _impossible(message: str) -> int:
    print(f"épreuve impossible : {message}", file=sys.stderr)
    return IMPOSSIBLE


def _tuer_pid(texte: str) -> None:
    """Ferme un service resté ouvert, pour que l'essai suivant puisse prendre le port."""
    if not texte.isdigit():
        return
    try:
        os.kill(int(texte), signal.SIGTERM)
    except OSError:
        pass


def _unity(commande: list[str]) -> int | str:
    proc = subprocess.Popen(commande)
    try:
        return proc.wait(timeout=DELAI_UNITY_S)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
        return f"délai de {DELAI_UNITY_S} s dépassé"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Le panneau d'Unity égale-t-il la photographie de sim/ ?")
    parser.add_argument("--sortie", type=Path, required=True)
    parser.add_argument("--seed", type=_entier_positif, default=GRAINE_PAR_DEFAUT)
    parser.add_argument("--ticks", type=_entier_positif, default=TICKS_PAR_DEFAUT)
    parser.add_argument("--cellule", type=JOUER._cellule)
    parser.add_argument("--decalage", type=_entier_positif, default=0)
    parser.add_argument("--unity", type=Path)
    args = parser.parse_args(argv)
    sortie = args.sortie.resolve()
    cellule = JOUER._regle().charger_et_choisir() if args.cellule is None else args.cellule
    try:
        unity = args.unity or _unity_par_defaut()
    except (OSError, ValueError) as exc:
        return _impossible(f"version d'Unity illisible : {exc}")
    if not unity.is_file():
        return _impossible(f"Unity introuvable : {unity}")
    if JOUER._repond(DEFAULT_SERVICE_PORT):
        return _impossible(f"le port {SERVICE_HOST}:{DEFAULT_SERVICE_PORT} répond déjà")
    sortie.mkdir(parents=True, exist_ok=True)

    photo = sortie / f"photo-tick-{args.ticks}.json"
    fait = subprocess.run([sys.executable, "-m", "sim", "--ticks", str(args.ticks), "--seed", str(args.seed),
                           "--snapshot-json", str(photo)], cwd=JEU, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=os.environ |{"PYTHONIOENCODING": "utf-8"})
    if fait.returncode != 0:
        return _impossible(f"photographie refusée (code {fait.returncode}) : {fait.stderr.strip()}")
    photographie = json.loads(photo.read_text(encoding="utf-8"))
    try:
        etat_de_cellule(photographie, cellule)
    except ValueError as exc:
        return _impossible(str(exc))

    journal = sortie / "unity.log"
    commande = [str(unity), "-batchmode", "-projectPath", str(PROJET_UNITY),
                "-executeMethod", "ForgeLocal3D.Capture.Photographier", "-logFile", str(journal),
                "-forgeCaptures", str(sortie), "-forgeCell", str(cellule),
                "-forgeSeed", str(args.seed), "-forgeTicks", str(args.ticks + args.decalage)]
    try:
        code = _unity(commande)
    except OSError as exc:
        return _impossible(f"Unity n'a pas démarré : {exc}")
    if code != 0:
        fin = journal.read_text(encoding="utf-8", errors="replace").splitlines() if journal.exists() else []
        return _impossible(f"Unity a rendu {code} ; fin du journal :\n" + "\n".join(fin[-LIGNES_JOURNAL_CITEES:]))
    if JOUER._repond(DEFAULT_SERVICE_PORT):
        pid = sortie / "service.pid"
        cite = pid.read_text(encoding="utf-8").strip() if pid.exists() else "inconnu"
        _tuer_pid(cite)
        return _impossible(f"service laissé ouvert (pid {cite})")
    image, texte = sortie / f"{SCENE}.png", sortie / f"{SCENE}.panneau.txt"
    manque = []
    if not image.is_file() or image.stat().st_size == 0:
        manque.append(f"{image} (absente ou vide)")
    if not texte.is_file():
        manque.append(f"{texte} (absent)")
    if manque:
        return _impossible(f"capture incomplète : {', '.join(manque)}")

    entete = [f"graine {args.seed}", f"ticks {args.ticks} (photographie), {args.ticks + args.decalage} (service)",
              f"cellule {cellule}", f"décalage {args.decalage}"]
    try:
        lignes = champs_compares(lire_panneau(texte.read_text(encoding="utf-8")), photographie, cellule)
        egal = all(vu == attendu for _, vu, attendu in lignes)
        corps = [f"{champ} : panneau {vu!r} · photographie {attendu!r} · {'égal' if vu == attendu else 'ÉCART'}"
                 for champ, vu, attendu in lignes]
    except ValueError as exc:
        # Un panneau qui déclare une absence n'est jamais lu comme des zéros : l'épreuve échoue en le citant.
        egal, corps = False, [str(exc)]
    verdict = ["ÉGALITÉ" if egal else "ÉCART", *entete, *corps]
    (sortie / "verdict.txt").write_text("\n".join(verdict) + "\n", encoding="utf-8")
    print("\n".join(verdict))
    return EGALITE if egal else ECART


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
