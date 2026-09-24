"""Charger la porte seule, sans rendre la racine du dépôt importable.

Appel : python3 -I -S .github/scripts/decider-integration.py --depot O/R
Les options isolent Python de PYTHONPATH, du dossier courant et de sitecustomize.
Le paquet est chargé par son chemin exact ; ses dépendances sont protégées.
"""

import sys

if not sys.flags.isolated or not sys.flags.no_site:
    raise SystemExit("la porte exige Python isolé : options -I -S")

import importlib.util
from pathlib import Path

racine = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("outils", racine / "outils/__init__.py")
paquet = importlib.util.module_from_spec(spec)
sys.modules["outils"] = paquet
spec.loader.exec_module(paquet)

from outils.porte import main

if __name__ == "__main__":
    raise SystemExit(main())
