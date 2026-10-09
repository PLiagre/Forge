"""L'épreuve de la carte dans Unity (lot #527) : la carte du joueur dit-elle le monde servi ?

    py pc\\epreuve_carte.py --sortie D [--seed S] [--ticks N] [--cellule C] [--decalage K]
                            [--retirer-une-cellule] [--sans-service] [--unity CHEMIN]

Le script lance le service de sim/ (graine S, en pause, poussé au tick N) et lit `/carte` et
`/monde` : c'est la référence. Avec `--decalage K`, il pousse ensuite le service de K ticks ;
avec `--sans-service`, il l'arrête. Puis Unity ouvre la scène de la carte en Play
(`ForgeLocal3D.EpreuveCarte.Jouer`) : la carte se pose, la cellule C est survolée, et un
rapport dit les cellules posées et servies et le texte de la fiche. Le verdict compare, nombre
par nombre : autant de cellules dessinées que `/carte` en sert ; la fiche égale `/carte`
(villes, puissance, maison) et `/monde` au même tick (habitants, faim, dette).
`--retirer-une-cellule` fait retirer à Unity une cellule du dessin (contre-épreuve).
Sortie : 0 égalité, 1 écart, 2 épreuve impossible.
"""
from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]


def _charger(nom: str, chemin: Path):
    spec = importlib.util.spec_from_file_location(nom, chemin)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# pc/jouer.py met jeu/ sur le chemin d'import ; l'épreuve du jalon 1 sait trouver Unity et couper un service resté ouvert.
JOUER = _charger("jouer", RACINE / "pc" / "jouer.py")
JALON1 = _charger("epreuve_jalon1", RACINE / "pc" / "epreuve_jalon1.py")
from sim.service import DEFAULT_SERVICE_PORT, SERVICE_HOST  # noqa: E402

JEU = JOUER.JEU_PY
PROJET_UNITY = RACINE / "3d" / "unity"
METHODE = "ForgeLocal3D.EpreuveCarte.Jouer"
GRAINE_PAR_DEFAUT = 0
TICKS_PAR_DEFAUT = 30
DELAI_REQUETE_S = 60
DELAI_UNITY_S = 1800
EGALITE, ECART, IMPOSSIBLE = 0, 1, 2
# Les libellés de FicheDeCellule.Decrire, tels quels.
AUCUNE = "aucune, le monde n'en nomme pas"
NON_CALCULEE = "non calculée"
_TETE = re.compile(r"Cellule (\d+)(?: · (.+))?")
_HABITANTS = re.compile(r"Habitants : (\S+) au tick (\S+)")
_FAIM = re.compile(r"Faim : (?:(\S+) ticks de manque|" + re.escape(NON_CALCULEE) + ")")
_DETTE = re.compile(r"Dette de nourriture : (?:(\S+) kg|" + re.escape(NON_CALCULEE) + ")")


def _illisible(texte: str, raison: str) -> ValueError:
    return ValueError(f"fiche illisible : {raison} ; texte : {texte!r}")


def lire_fiche(texte: str) -> dict:
    """Le texte de la fiche → ses champs. Une absence (« Habitants et faim : … ») ou une ligne inconnue lève ValueError :
    une fiche qui ne dit pas le monde n'est jamais lue comme des zéros."""
    lignes = texte.split("\n")
    if len(lignes) != 6:
        raise _illisible(texte, f"{len(lignes)} ligne(s), il en faut 6")
    tete = _TETE.fullmatch(lignes[0])
    if not tete:
        raise _illisible(texte, f"en-tête inconnu {lignes[0]!r}")
    lu = {"cellule": int(tete[1]), "villes": tete[2].split(", ") if tete[2] else []}
    for ligne, champ in ((lignes[1], "puissance"), (lignes[2], "maison")):
        prefixe = f"{champ.capitalize()} : "
        if not ligne.startswith(prefixe):
            raise _illisible(texte, f"ligne {ligne!r} au lieu de {prefixe!r}")
        nom = ligne[len(prefixe):]
        lu[champ] = None if nom == AUCUNE else nom
    habitants, faim, dette = _HABITANTS.fullmatch(lignes[3]), _FAIM.fullmatch(lignes[4]), _DETTE.fullmatch(lignes[5])
    if not (habitants and faim and dette):
        raise _illisible(texte, "habitants, faim ou dette absents")
    try:
        lu |= {"population": int(habitants[1]), "tick": int(habitants[2]),
               "hunger_ticks": -1 if faim[1] is None else int(faim[1]),
               "food_deficit_kg": -1.0 if dette[1] is None else float(dette[1])}
    except ValueError:
        raise _illisible(texte, "un nombre n'en est pas un") from None
    return lu


def references(carte: dict, monde: dict, cellule: int) -> dict:
    """Ce que la fiche de `cellule` doit dire, tiré de `/carte` et de `/monde` tels que servis."""
    servie = next((c for c in carte["cells"] if c["cell_id"] == cellule), None)
    vivante = next((c for c in monde["cells"] if c["cell_id"] == cellule), None)
    if servie is None or vivante is None:
        raise ValueError(f"cell_id {cellule} absent de " + ("/carte" if servie is None else "/monde"))
    nom = lambda identite: None if identite is None else identite["nom"]  # noqa: E731
    return {"cellule": cellule, "villes": [v["nom"] for v in servie["villes"]], "puissance": nom(servie["puissance"]),
            "maison": nom(servie["maison"]), "tick": monde["tick"],
            **{champ: vivante[champ] for champ in ("population", "hunger_ticks", "food_deficit_kg")}}


def juger(rapport: dict, carte: dict, monde: dict, cellule: int) -> tuple[bool, list[str]]:
    """(égalité, lignes du verdict) : les cellules, puis la fiche, champ par champ, les deux valeurs citées."""
    servies = len(carte["cells"])
    lignes = [f"cellules dessinées : carte {rapport['cellules_posees']} · /carte {servies}",
              f"cellules servies selon la carte : {rapport['cellules_servies']} · /carte {servies}"]
    egal = rapport["cellules_posees"] == servies and rapport["cellules_servies"] == servies
    if rapport["cellules_servies"] < 0:
        return False, lignes + [f"la carte ne s'est pas posée : {rapport['carte']!r}"]
    if rapport.get("defaut"):
        return False, lignes + [f"défaut : {rapport['defaut']}"]
    if rapport["survolee"] != cellule:
        return False, lignes + [f"cellule survolée {rapport['survolee']}, il fallait {cellule}"]
    try:
        fiche = lire_fiche(rapport["fiche"])
    except ValueError as exc:
        return False, lignes + [str(exc)]
    attendu = references(carte, monde, cellule)
    for champ, valeur in attendu.items():
        vu = fiche[champ]
        egal &= vu == valeur
        lignes.append(f"{champ} : fiche {vu!r} · service {valeur!r} · {'égal' if vu == valeur else 'ÉCART'}")
    return egal, lignes


def _requete(methode: str, chemin: str) -> dict:
    demande = urllib.request.Request(f"http://{SERVICE_HOST}:{DEFAULT_SERVICE_PORT}{chemin}", method=methode,
                                     data=b"" if methode == "POST" else None)
    with urllib.request.urlopen(demande, timeout=DELAI_REQUETE_S) as reponse:
        return json.loads(reponse.read())


def _lancer_service(graine: int):
    stderr: collections.deque = collections.deque(maxlen=JOUER.LIGNES_STDERR_GARDEES)
    service = subprocess.Popen([sys.executable, "-m", "sim.service", "--seed", str(graine), "--port", str(DEFAULT_SERVICE_PORT),
                                "--jours-par-seconde", "0"], cwd=JEU, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, encoding="utf-8", errors="replace", env=os.environ | {"PYTHONIOENCODING": "utf-8"})
    import threading
    threading.Thread(target=JOUER._lire_flux, args=(service.stderr, stderr.append), daemon=True).start()
    JOUER._attendre_pret(service, f"service prêt sur {SERVICE_HOST}:{DEFAULT_SERVICE_PORT}", stderr)
    return service


def _arreter(service) -> None:
    if service is None or service.poll() is not None:
        return
    service.terminate()
    try:
        service.wait(timeout=JOUER.DELAI_ARRET_S)
    except subprocess.TimeoutExpired:
        service.kill()
        service.wait()


def _impossible(message: str) -> int:
    print(f"épreuve impossible : {message}", file=sys.stderr)
    return IMPOSSIBLE


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="La carte d'Unity dit-elle le monde servi ?")
    parser.add_argument("--sortie", type=Path, required=True)
    parser.add_argument("--seed", type=JALON1._entier_positif, default=GRAINE_PAR_DEFAUT)
    parser.add_argument("--ticks", type=JALON1._entier_positif, default=TICKS_PAR_DEFAUT)
    parser.add_argument("--cellule", type=JOUER._cellule)
    parser.add_argument("--decalage", type=JALON1._entier_positif, default=0)
    parser.add_argument("--retirer-une-cellule", action="store_true")
    parser.add_argument("--sans-service", action="store_true")
    parser.add_argument("--unity", type=Path)
    args = parser.parse_args(argv)
    sortie = args.sortie.resolve()
    cellule = JOUER._regle().charger_et_choisir() if args.cellule is None else args.cellule
    try:
        unity = args.unity or JALON1._unity_par_defaut()
    except (OSError, ValueError) as exc:
        return _impossible(f"version d'Unity illisible : {exc}")
    if not unity.is_file():
        return _impossible(f"Unity introuvable : {unity}")
    if JOUER._repond(DEFAULT_SERVICE_PORT):
        return _impossible(f"le port {SERVICE_HOST}:{DEFAULT_SERVICE_PORT} répond déjà")
    sortie.mkdir(parents=True, exist_ok=True)
    rapport, verdict, journal = sortie / "rapport.json", sortie / "verdict.txt", sortie / "unity.log"
    for ancien in (rapport, verdict):
        if ancien.is_file():
            ancien.unlink()

    service = None
    try:
        try:
            service = _lancer_service(args.seed)
            if args.ticks:
                _requete("POST", f"/tick?n={args.ticks}")
            carte, monde = _requete("GET", "/carte"), _requete("GET", "/monde")
            references(carte, monde, cellule)
            if args.decalage:
                _requete("POST", f"/tick?n={args.decalage}")
        except (RuntimeError, OSError, ValueError, urllib.error.URLError) as exc:
            return _impossible(f"la référence n'a pas pu être lue au service : {exc}")
        if args.sans_service:
            _arreter(service)
        commande = [str(unity), "-batchmode", "-projectPath", str(PROJET_UNITY), "-executeMethod", METHODE,
                    "-logFile", str(journal), "-forgeEpreuve", str(rapport), "-forgeCell", str(cellule),
                    *(["-forgeEpreuveRetirer"] if args.retirer_une_cellule else [])]
        debut = time.time()
        try:
            code = JALON1._unity(commande)
        except OSError as exc:
            return _impossible(f"Unity n'a pas démarré : {exc}")
        if code != 0:
            fin = journal.read_text(encoding="utf-8", errors="replace").splitlines() if journal.is_file() else []
            return _impossible(f"Unity a rendu {code} ; fin du journal :\n" + "\n".join(fin[-JALON1.LIGNES_JOURNAL_CITEES:]))
        if not rapport.is_file() or rapport.stat().st_mtime + JALON1.MARGE_HORODATAGE_S < debut:
            return _impossible(f"rapport absent ou antérieur à cet essai : {rapport}")
        lu = json.loads(rapport.read_text(encoding="utf-8"))
    finally:
        _arreter(service)

    entete = [f"graine {args.seed}", f"ticks {args.ticks} (référence), {args.ticks + args.decalage} (service lu par Unity)",
              f"cellule {cellule}", f"décalage {args.decalage}", f"cellule retirée {lu.get('retiree', -1)}",
              f"service {'arrêté avant Unity' if args.sans_service else 'ouvert'}"]
    egal, corps = juger(lu, carte, monde, cellule)
    texte = ["ÉGALITÉ" if egal else "ÉCART", *entete, *corps]
    verdict.write_text("\n".join(texte) + "\n", encoding="utf-8")
    print("\n".join(texte))
    return EGALITE if egal else ECART


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
