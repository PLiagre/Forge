"""Mesure le tick publié (IA, tick et publication) et l'empreinte de chaque jour publié.

Lancé depuis la racine du dépôt :
    py docs/mesures/1075-tick-publie/mesure_tick_publie.py --jeu jeu --ticks 90 --sortie branche.json
    py docs/mesures/1075-tick-publie/mesure_tick_publie.py --comparer master.json branche.json
Il ne lit que des noms qui existent déjà sur master, pour mesurer aussi l'ancien code.
"""

import argparse
import hashlib
import json
import os
import statistics
import sys
import time

TICKS_PAR_DEFAUT = 90
CHAUFFE = 30  # la médiane et le maximum portent sur les ticks 30 à 89


def lire_tout(serveur, etat) -> bytes:
    """Tous les octets d'un état publié, joints dans un ordre fixé."""
    morceaux = [etat.monde, etat.ia or b"", etat.modificateurs]
    for cid in sorted(etat.lieux):
        morceaux.append(etat.lieux[cid])
        morceaux.append(etat.lieux_avec_bourg[cid])
        morceaux.append(serveur.octets_plan(etat, cid))
        morceaux.append(serveur.octets_occupation(etat, cid))
    morceaux.append(serveur.octets_de_maison(etat))
    for maison in sorted(etat.maisons.registre, key=lambda m: m.id):
        morceaux.append(serveur.octets_de_maison(etat, maison.id))
    empreinte = hashlib.sha256()
    for morceau in morceaux:
        empreinte.update(len(morceau).to_bytes(8, "big"))
        empreinte.update(morceau)
    return empreinte.hexdigest()


def mesurer(jeu: str, ticks: int, alterer: int | None) -> dict:
    jeu = os.path.abspath(jeu)
    sys.path.insert(0, jeu)
    os.chdir(jeu)
    from sim.service import ServeurMonde

    serveur = ServeurMonde(("127.0.0.1", 0), 0, 0, ia=True)
    jours = []
    try:
        for jour in range(1, ticks + 1):
            debut = time.perf_counter()
            etat = serveur.jouer_un_tick()
            duree = (time.perf_counter() - debut) * 1000
            if alterer == jour:
                etat = type(etat)(**{**etat.__dict__, "monde": etat.monde + b" "})
            jours.append({"jour": jour, "tick_ms": duree,
                          "duree_dernier_tick_ms": etat.duree_dernier_tick_ms,
                          "empreinte": lire_tout(serveur, etat)})
    finally:
        serveur._arret_horloge = True
        serveur.server_close()
    retenus = jours[CHAUFFE:]
    return {
        "jeu": jeu, "ticks": ticks, "alterer": alterer,
        "mediane_tick_ms": statistics.median(j["tick_ms"] for j in retenus) if retenus else None,
        "maximum_tick_ms": max((j["tick_ms"] for j in retenus), default=None),
        "mediane_duree_dernier_tick_ms":
            statistics.median(j["duree_dernier_tick_ms"] for j in retenus) if retenus else None,
        "jours": jours,
    }


def comparer(a: str, b: str) -> int:
    with open(a, encoding="utf-8") as f:
        premier = {j["jour"]: j["empreinte"] for j in json.load(f)["jours"]}
    with open(b, encoding="utf-8") as f:
        second = {j["jour"]: j["empreinte"] for j in json.load(f)["jours"]}
    for jour in sorted(premier.keys() | second.keys()):
        if jour not in premier or jour not in second:
            print(f"jour {jour} manquant dans {a if jour not in premier else b}")
            return 1
        if premier[jour] != second[jour]:
            print(f"le jour {jour} diffère : {premier[jour][:16]} contre {second[jour][:16]}")
            return 1
    print(f"{len(premier)} jours, mêmes empreintes")
    return 0


def main() -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--jeu", help="dossier jeu à importer")
    parseur.add_argument("--ticks", type=int, default=TICKS_PAR_DEFAUT)
    parseur.add_argument("--sortie", help="fichier JSON écrit")
    parseur.add_argument("--alterer", type=int, help="ajoute un octet au /monde de ce jour avant de hacher")
    parseur.add_argument("--comparer", nargs=2, metavar=("A", "B"))
    args = parseur.parse_args()
    if args.comparer:
        return comparer(*args.comparer)
    if not args.jeu or not args.sortie:
        parseur.error("--jeu et --sortie sont obligatoires hors --comparer")
    sortie = os.path.abspath(args.sortie)
    mesure = mesurer(args.jeu, args.ticks, args.alterer)
    with open(sortie, "w", encoding="utf-8") as f:
        json.dump(mesure, f, indent=1)
    print(f"médiane {mesure['mediane_tick_ms']:.1f} ms, maximum {mesure['maximum_tick_ms']:.1f} ms, "
          f"duree_dernier_tick_ms médiane {mesure['mediane_duree_dernier_tick_ms']:.1f} ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
