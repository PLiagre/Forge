"""Charger la porte seule, sans rendre la racine du dépôt importable.

Appel : python3 -I -S .github/scripts/decider-integration.py --depot O/R
Les options isolent Python de PYTHONPATH, du dossier courant et de sitecustomize.
Le paquet est chargé par son chemin exact ; ses dépendances sont protégées.
"""

import sys

if not sys.flags.isolated or not sys.flags.no_site:
    raise SystemExit("la porte exige Python isolé : options -I -S")

from pathlib import Path
from types import ModuleType

racine = Path(__file__).resolve().parents[2]


def charger(nom, chemin, paquet=None):
    """La source exacte, jamais un paquet homonyme ni un .pyc du dépôt."""
    module = ModuleType(nom)
    module.__file__ = str(chemin)
    module.__package__ = "outils"
    if paquet is None:
        # Aucun autre fichier du dossier n'est importable par cette porte.
        module.__path__ = []
    sys.modules[nom] = module
    if paquet is not None:
        setattr(paquet, nom.rsplit(".", 1)[1], module)
    exec(compile(chemin.read_bytes(), str(chemin), "exec"), module.__dict__)
    return module


paquet = charger("outils", racine / "outils/__init__.py")
# L'ordre suit les dépendances. Modifier cette frontière exige le propriétaire.
for nom in ("integration", "registre", "demandes", "relecture", "github", "porte"):
    charger(f"outils.{nom}", racine / "outils" / f"{nom}.py", paquet)

from outils.porte import main

if __name__ == "__main__":
    raise SystemExit(main())
