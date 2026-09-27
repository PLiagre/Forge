"""Vérifie les lanceurs de pc/ sans rien lancer : chaque chemin qu'ils nomment
existe-t-il sur cette machine ?

    py pc/verifier_lanceurs.py

Un lanceur dont la cible manque échoue (code 1), sauf le build nocturne de
Jouer.cmd, qui peut ne pas exister encore : il est signalé, pas compté.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
# Ce qui peut manquer sans que le lanceur soit faux : un produit du build nocturne.
ATTENDUS_PLUS_TARD = {"JEU"}


def cibles(texte: str) -> dict[str, str]:
    trouves = {nom: valeur for nom, valeur in re.findall(r'^set "([A-Z]+)=(.+)"\s*$', texte, re.M)}
    for chemin in re.findall(r'-projectPath "([^"]+)"', texte):
        trouves["PROJET"] = chemin
    return trouves


def resoudre(valeur: str) -> Path:
    return Path(valeur.replace("%~dp0", str(ICI) + "\\").replace("\\", "/")).resolve()


def main() -> int:
    lanceurs = sorted(ICI.glob("*.cmd"))
    if not lanceurs:
        print("aucun lanceur dans pc/ : rien n'est vérifié, et c'est un échec")
        return 1
    fautes = 0
    for lanceur in lanceurs:
        texte = lanceur.read_text(encoding="utf-8", errors="replace")
        for nom, valeur in cibles(texte).items():
            chemin = resoudre(valeur)
            if chemin.exists():
                etat = "ok"
            elif nom in ATTENDUS_PLUS_TARD:
                etat = "absent (produit par le build nocturne)"
            else:
                etat = "MANQUANT"
                fautes += 1
            print(f"{lanceur.name:28} {nom:8} {etat:40} {chemin}")
    print(f"{len(lanceurs)} lanceurs, {fautes} cible(s) manquante(s)")
    return 1 if fautes else 0


if __name__ == "__main__":
    sys.exit(main())
