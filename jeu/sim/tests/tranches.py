"""Le partage des tests du moteur entre les tranches de la CI, d'après leurs durées.

Jusqu'au 11 octobre 2026, les tests se distribuaient à tour de rôle dans l'ordre de collecte :
la tranche 3 finissait en 14 min, les deux autres en 1 h 20, et chaque PR attendait la plus
lente. Le partage suit maintenant les durées que la CI a mesurées (`durees.json`) : le test le
plus long d'abord, dans la tranche la moins chargée, et ainsi de suite.

Un test absent de `durees.json` (un lot l'a ajouté depuis la mesure) compte pour la durée
médiane des tests mesurés : il trouve sa place comme les autres, et aucun ne se perd.

Chaque tranche refait le même calcul sur la même collecte et le même fichier : elles tombent
d'accord sans se parler. Chacune écrit aussi ce qu'elle a mesuré quand `FORGE_DUREES` nomme un
fichier ; la CI le garde en artefact. Remettre `durees.json` à jour, depuis `jeu/` :

    gh run download <run de master> -R PLiagre/Forge -p "durees-*" -D /tmp/durees
    python3 -m sim.tests.tranches /tmp/durees

Bibliothèque standard seule : ce module se charge aussi hors de pytest (atelier/tests/test_ci.py).
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

DUREES = Path(__file__).with_name("durees.json")


def lire_tranche(valeur: str | None) -> tuple[int, int] | None:
    """« k/n » → (k, n) ; None sans valeur. Une valeur fausse est une erreur, jamais « tout jouer »."""
    if valeur is None or valeur == "":
        return None
    morceaux = valeur.split("/")
    if len(morceaux) != 2 or not all(m.isdigit() for m in morceaux):
        raise ValueError(f"{valeur!r} : attendu « k/n », deux entiers")
    k, n = int(morceaux[0]), int(morceaux[1])
    if not 1 <= k <= n:
        raise ValueError(f"{valeur!r} : attendu 1 ≤ k ≤ n")
    return k, n


def lire_durees(chemin: Path = DUREES) -> dict[str, float]:
    """Les durées mesurées, en secondes, par identifiant de test. Un fichier absent ou vide est
    une erreur : sans mesure, le partage n'aurait rien sur quoi s'appuyer."""
    if not chemin.is_file():
        raise ValueError(f"{chemin} absent : le partage des tranches se fait sur les durées mesurées")
    durees = json.loads(chemin.read_text(encoding="utf-8"))
    if not durees:
        raise ValueError(f"{chemin} est vide : aucune durée mesurée")
    return {nom: float(s) for nom, s in durees.items()}


def repartir(noms: list[str], durees: dict[str, float], n: int) -> list[int]:
    """La tranche (1 à n) de chaque test de `noms`, dans le même ordre.

    Le plus long d'abord, chacun dans la tranche la moins chargée (la première, à charge égale).
    Le résultat ne dépend que des noms et des durées : jamais de l'ordre de collecte.
    """
    mediane = statistics.median(durees.values())
    duree = [durees.get(nom, mediane) for nom in noms]
    charges = [0.0] * n
    tranches = [0] * len(noms)
    for i in sorted(range(len(noms)), key=lambda i: (-duree[i], noms[i], i)):
        k = min(range(n), key=lambda j: (charges[j], j))
        tranches[i] = k + 1
        charges[k] += duree[i]
    return tranches


def charges(noms: list[str], durees: dict[str, float], n: int) -> list[float]:
    """Les secondes de tests prévues dans chaque tranche."""
    mediane = statistics.median(durees.values())
    totaux = [0.0] * n
    for nom, k in zip(noms, repartir(noms, durees, n)):
        totaux[k - 1] += durees.get(nom, mediane)
    return totaux


def fusionner(fichiers: list[Path]) -> dict[str, float]:
    """Les durées de plusieurs tranches en une table. Un test mesuré deux fois garde la plus longue."""
    durees: dict[str, float] = {}
    for fichier in fichiers:
        for nom, s in json.loads(fichier.read_text(encoding="utf-8")).items():
            durees[nom] = max(durees.get(nom, 0.0), float(s))
    return durees


def ecrire(durees: dict[str, float], chemin: Path = DUREES) -> None:
    """Une ligne par test, triées : un rafraîchissement se relit en diff."""
    lignes = [f"  {json.dumps(nom, ensure_ascii=False)}: {round(s, 2)}" for nom, s in sorted(durees.items())]
    chemin.write_text("{\n" + ",\n".join(lignes) + "\n}\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    if len(argv) != 1 or not Path(argv[0]).is_dir():
        print("usage : python3 -m sim.tests.tranches <dossier des artefacts durees-*>", file=sys.stderr)
        return 2
    fichiers = sorted(Path(argv[0]).rglob("*.json"))
    durees = fusionner(fichiers)
    if not durees:
        print(f"aucune durée dans {argv[0]}", file=sys.stderr)
        return 1
    ecrire(durees)
    print(f"{len(durees)} tests mesurés, lus dans {len(fichiers)} fichier(s), écrits dans {DUREES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
