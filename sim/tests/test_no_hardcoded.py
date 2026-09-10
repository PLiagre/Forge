"""
Absence de littéraux numériques non nommés dans les fonctions de calcul.

Inspecte statiquement les fichiers sim/*.py (non-tests) et vérifie qu'aucune
fonction ne contient de littéral numérique en dehors de l'ensemble structurel
{0, 1, -1} (et leurs équivalents flottants 0.0, 1.0, -1.0).

Compteur : compteurs_en_dur_trouves (doit valoir 0).
"""

import ast
import pathlib

_SIM_DIR = pathlib.Path(__file__).parent.parent
_TESTS_DIR = _SIM_DIR / "tests"

# Parcours récursif des modules du moteur, exclusion par répertoire de tests.
# Ainsi tout futur sous-module de sim/ sera automatiquement inspecté.
_ENGINE_FILES = sorted(
    p for p in _SIM_DIR.rglob("*.py")
    if not p.is_relative_to(_TESTS_DIR)
)

# Littéraux structurels autorisés dans les corps de fonctions
# (valeurs de plancher, sentinelles, incréments minimaux)
_ALLOWED_INT_LITERALS = frozenset({0, 1, -1})
_ALLOWED_FLOAT_LITERALS = frozenset({0.0, 1.0, -1.0})


def _collect_literals_in_functions(filepath: pathlib.Path) -> list:
    """
    Retourne la liste des littéraux numériques non autorisés trouvés
    dans des corps de fonctions du fichier filepath.
    """
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(filepath))

    violations = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        for child in ast.walk(node):
            # Littéral positif simple
            if isinstance(child, ast.Constant) and isinstance(child.value, (int, float)):
                val = child.value
                if isinstance(val, bool):
                    continue  # bool est une sous-classe d'int, l'ignorer
                if isinstance(val, int) and val not in _ALLOWED_INT_LITERALS:
                    violations.append(
                        (str(filepath.name), node.name, child.lineno, val)
                    )
                elif isinstance(val, float) and val not in _ALLOWED_FLOAT_LITERALS:
                    violations.append(
                        (str(filepath.name), node.name, child.lineno, val)
                    )

            # Littéral négatif : UnaryOp(USub, Constant(n))
            if (
                isinstance(child, ast.UnaryOp)
                and isinstance(child.op, ast.USub)
                and isinstance(child.operand, ast.Constant)
                and isinstance(child.operand.value, (int, float))
            ):
                val = -child.operand.value
                if isinstance(val, int) and val not in _ALLOWED_INT_LITERALS:
                    violations.append(
                        (str(filepath.name), node.name, child.lineno, val)
                    )
                elif isinstance(val, float) and val not in _ALLOWED_FLOAT_LITERALS:
                    violations.append(
                        (str(filepath.name), node.name, child.lineno, val)
                    )

    return violations


def test_no_hardcoded_numeric_literals():
    """
    Vérifie l'absence de littéraux numériques non nommés dans
    les corps de fonctions de sim/*.py.
    Compteur : compteurs_en_dur_trouves (attendu = 0).
    """
    all_violations = []
    for filepath in _ENGINE_FILES:
        violations = _collect_literals_in_functions(filepath)
        all_violations.extend(violations)

    compteurs_en_dur_trouves = len(all_violations)
    print(f"fichiers inspectés : {[p.name for p in _ENGINE_FILES]}")
    print(f"compteurs_en_dur_trouves = {compteurs_en_dur_trouves}")
    if all_violations:
        for fname, func, lineno, val in all_violations:
            print(f"  VIOLATION : {fname}:{func}:{lineno} → {val!r}")

    assert compteurs_en_dur_trouves == 0, (
        f"{compteurs_en_dur_trouves} littéral(ux) non nommé(s) trouvé(s) "
        f"dans les fonctions de calcul de sim/ : {all_violations}"
    )
