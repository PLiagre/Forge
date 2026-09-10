"""
Couverture d'écriture : tout champ déclaré a un écrivain et un lecteur.

Vérifie par analyse statique (AST) que :
1. Chaque champ déclaré dans TOUTES les dataclasses de sim.model
   (découvertes par introspection, pas nommées en dur — R2) possède
   au moins un site d'écriture ET au moins un site de lecture.
   La détection de site d'écriture vérifie que la variable cible a un
   nom conventionnel associé à la classe scrutée (ex. 'cell' pour Cell)
   — R3 : une affectation sur un objet d'un type différent ne compte pas.

2. Si une deuxième dataclass est ajoutée sans écrivain, le test échoue.
   (Contre-preuve R2 : introspection attrape les nouvelles dataclasses.)

3. World.adjacency est lu dans au moins un module du moteur.
   (Contre-preuve : si le maillon commerce
   est retiré, la vérification de lecture échoue.)

Deux tests unitaires séparés :
- test_all_dataclass_fields_have_write_and_read_sites (R2 + R3)
- test_adjacency_is_read_by_engine (extension World.adjacency)
- test_write_coverage_counter_etendu (compteur champs_modele_couverts_etendu)
"""

import ast
import dataclasses
import inspect
import pathlib

import sim.model as _sim_model

_SIM_DIR = pathlib.Path(__file__).parent.parent
_ENGINE_FILE = _SIM_DIR / "engine.py"
_WORLD_FILE = _SIM_DIR / "world.py"
_MODEL_FILE = _SIM_DIR / "model.py"

_SIM_SOURCE_FILES = [_ENGINE_FILE, _WORLD_FILE, _MODEL_FILE]


def _discover_dataclasses():
    """
    Découvre par introspection toutes les dataclasses de sim.model.
    R2 : jamais nommées en dur ici.
    Retourne une liste de (nom_classe → nom_conventionnel_variable).
    Convention : variable = nom_classe.lower() (ex. Cell → 'cell').
    """
    result = []
    for _name, obj in inspect.getmembers(_sim_model, inspect.isclass):
        if dataclasses.is_dataclass(obj):
            result.append((obj, obj.__name__.lower()))
    return result


def _scan_writes_typed(files: list, field_names: set, target_var_names: set) -> set:
    """
    Scanne les fichiers Python listés et retourne l'ensemble des noms
    de champs ayant un site d'écriture sur une variable dont le nom
    appartient à target_var_names (R3 : filtre par nom conventionnel).

    Détecte :
    - Affectation d'attribut : VAR.FIELD = expr  (VAR dans target_var_names)
    - Argument nommé du constructeur : ClassName(FIELD=expr)
      → tous les constructeurs des dataclasses de sim.model sont considérés.
    """
    all_writes: set = set()

    for filepath in files:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))

        for node in ast.walk(tree):
            # Site d'écriture 1 : VAR.FIELD = expr, VAR dans target_var_names
            if isinstance(node, (ast.Assign, ast.AugAssign)):
                targets = (
                    node.targets if isinstance(node, ast.Assign) else [node.target]
                )
                for t in targets:
                    if (
                        isinstance(t, ast.Attribute)
                        and t.attr in field_names
                        and isinstance(t.value, ast.Name)
                        and t.value.id in target_var_names
                    ):
                        all_writes.add(t.attr)

            # Site d'écriture 2 : constructeur nommé (ClassName(FIELD=expr))
            if isinstance(node, ast.Call):
                func = node.func
                is_dataclass_ctor = (
                    isinstance(func, ast.Name) and func.id in {
                        cls.__name__
                        for cls, _ in _discover_dataclasses()
                    }
                ) or (
                    isinstance(func, ast.Attribute) and func.attr in {
                        cls.__name__
                        for cls, _ in _discover_dataclasses()
                    }
                )
                if is_dataclass_ctor:
                    for kw in node.keywords:
                        if kw.arg and kw.arg in field_names:
                            all_writes.add(kw.arg)

    return all_writes


def _scan_reads(files: list, field_names: set) -> set:
    """Retourne l'ensemble des noms de champs lus (contexte Load)."""
    all_reads: set = set()
    for filepath in files:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and node.attr in field_names
                and not isinstance(node.ctx, ast.Store)
            ):
                all_reads.add(node.attr)
    return all_reads


def test_all_dataclass_fields_have_write_and_read_sites():
    """
    R2 + R3 : pour chaque dataclass de sim.model (par introspection),
    chaque champ déclaré a au moins un site d'écriture (sur la variable
    conventionnelle, ex. 'cell' pour Cell — R3) ET un site de lecture.

    Ce test va ROUGE si :
    - Un champ est ajouté à une dataclass sans écrivain
    - Une nouvelle dataclass est ajoutée sans aucun site d'écriture
    - Une affectation sur un autre objet est la seule correspondance
      (R3 : filtrage par nom de variable conventionnel)
    """
    discovered = _discover_dataclasses()
    assert discovered, "Aucune dataclass trouvée dans sim.model — bug d'introspection"

    errors = []
    for cls, var_name in discovered:
        field_names = {f.name for f in dataclasses.fields(cls)}
        all_writes = _scan_writes_typed(_SIM_SOURCE_FILES, field_names, {var_name})
        all_reads = _scan_reads(_SIM_SOURCE_FILES, field_names)

        for f in dataclasses.fields(cls):
            if f.name not in all_writes:
                errors.append(
                    f"{cls.__name__}.{f.name} : aucun site d'écriture "
                    f"(variable cible '{var_name}' attendue)"
                )
            if f.name not in all_reads:
                errors.append(f"{cls.__name__}.{f.name} : aucun site de lecture")

        print(f"Classe {cls.__name__} (var='{var_name}'):")
        print(f"  champs : {sorted(field_names)}")
        print(f"  écrits : {sorted(all_writes & field_names)}")
        print(f"  lus    : {sorted(all_reads & field_names)}")

    assert not errors, (
        "Couverture d'écriture incomplète :\n"
        + "\n".join(f"  - {e}" for e in errors)
    )


def test_adjacency_is_read_by_engine():
    """
    World.adjacency est lu dans au moins un
    module du moteur (engine.py ou world.py).

    Ce test va ROUGE si le maillon commerce (_apply_commerce) est retiré
    du moteur et qu'aucun autre code ne lit 'adjacency'.
    """
    found_read = False
    for filepath in _SIM_SOURCE_FILES:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and node.attr == "adjacency"
                and not isinstance(node.ctx, ast.Store)
            ):
                found_read = True
                break
        if found_read:
            break

    print(f"adjacency_lu_dans_moteur = {found_read}")
    assert found_read, (
        "World.adjacency n'est lu dans aucun module du moteur "
        "(engine.py, world.py, model.py). Le maillon commerce a-t-il été retiré ?"
    )


def test_write_coverage_counter_etendu():
    """
    Compteur champs_modele_couverts_etendu.

    = nombre de champs couverts dans toutes les dataclasses de sim.model
      (écriture ET lecture vérifiées) + 1 si World.adjacency est lu.

    Dérivé par parcours — jamais écrit en dur.
    """
    discovered = _discover_dataclasses()

    total_fields = 0
    covered_fields = 0

    for cls, var_name in discovered:
        field_names = {f.name for f in dataclasses.fields(cls)}
        all_writes = _scan_writes_typed(_SIM_SOURCE_FILES, field_names, {var_name})
        all_reads = _scan_reads(_SIM_SOURCE_FILES, field_names)

        for f in dataclasses.fields(cls):
            total_fields += 1
            if f.name in all_writes and f.name in all_reads:
                covered_fields += 1

    # +1 pour World.adjacency
    adjacency_covered = 0
    for filepath in _SIM_SOURCE_FILES:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and node.attr == "adjacency"
                and not isinstance(node.ctx, ast.Store)
            ):
                adjacency_covered = 1
                break
        if adjacency_covered:
            break

    total_denominator = total_fields + 1  # +1 pour adjacency
    champs_modele_couverts_etendu = covered_fields + adjacency_covered

    print(f"dataclasses découvertes : {[cls.__name__ for cls, _ in discovered]}")
    print(f"champs dans dataclasses : {total_fields}")
    print(f"champs couverts (écriture + lecture) : {covered_fields}")
    print(f"adjacency couverte : {adjacency_covered}")
    print(f"champs_modele_couverts_etendu = {champs_modele_couverts_etendu} / {total_denominator}")

    assert champs_modele_couverts_etendu == total_denominator, (
        f"Couverture étendue incomplète : {champs_modele_couverts_etendu}/{total_denominator}"
    )


# --- Une constante que le moteur ne peut pas relire est une variable terminale ---

def _constantes_consultees_par_le_moteur() -> set:
    """
    Dérive, de la source du moteur, l'ensemble des constantes de `sim.constants`
    qu'il consulte. Jamais une liste écrite à la main : ajouter une constante au
    moteur l'ajoute au dénominateur toute seule (règles 2 et 3).
    """
    import sim.constants as _k

    numeriques = {
        nom for nom in dir(_k)
        if nom.isupper() and isinstance(getattr(_k, nom), (int, float))
    }
    tree = ast.parse(_ENGINE_FILE.read_text(encoding="utf-8"), filename=str(_ENGINE_FILE))
    return {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and node.attr in numeriques
        and not isinstance(node.ctx, ast.Store)
    }


class _MondeEpreuve:
    """
    Monde minuscule qui exerce les cinq maillons du tick en même temps :
    une cellule riche et endettée (remboursement de dette, surplus, commerce
    sortant), une cellule pauvre au plafond de mortalité (faim, mort, borne),
    et une troisième voisine avec un fort besoin de commerce (repli arête 1-3).

    Trois cellules plutôt que 596 : ce test répond à « le moteur voit-il cette
    constante ? », pas à « le monde survit-il ? ». Il coûte des millisecondes.
    """

    def __init__(self):
        from sim.model import Cell

        self.cells = {
            1: Cell(cell_id=1, area_km2=100.0, population=10,
                    food_stock_kg=1000.0, hunger_ticks=0,
                    food_deficit_kg=5000.0, mortality_remainder=0.0),
            2: Cell(cell_id=2, area_km2=1.0, population=1000,
                    food_stock_kg=0.0, hunger_ticks=0,
                    food_deficit_kg=100000.0, mortality_remainder=0.5),
            3: Cell(cell_id=3, area_km2=10.0, population=1000,
                    food_stock_kg=12.0, hunger_ticks=0,
                    food_deficit_kg=0.0, mortality_remainder=0.0),
        }
        self.adjacency = [{"a": 1, "b": 2, "shared_length_m": 1000.0}, {"a": 1, "b": 3}]

    def etat(self):
        """Empreinte exacte : `repr` d'un flottant, jamais un arrondi."""
        return [
            (c.cell_id, c.population, repr(c.food_stock_kg), c.hunger_ticks,
             repr(c.food_deficit_kg), repr(c.mortality_remainder),
             repr(c.migration_remainder))
            for c in sorted(self.cells.values(), key=lambda c: c.cell_id)
        ]


def _jouer_le_monde_d_epreuve(n_ticks: int = 3) -> list:
    import random

    from sim import engine

    monde = _MondeEpreuve()
    rng = random.Random(1)
    for _ in range(n_ticks):
        engine.tick(monde, rng)
    return monde.etat()


def test_le_moteur_ne_lie_aucune_constante_par_valeur():
    """
    Mode de défaillance n° 3 (variable terminale) appliqué aux constantes.

    Un nom lié par `from sim.constants import X` est figé au chargement du
    module. Le remplacer en mémoire ne change alors RIEN au moteur — et un
    test de régime croit mesurer un régime alors qu'il mesure un moteur
    inchangé, sans qu'aucune erreur ne soit levée.

    Cinq constantes sur huit étaient dans ce cas : production, consommation,
    les deux bornes de rendement et la capacité de transport. Seules la
    mortalité et le remboursement de la dette atteignaient le moteur, et la
    règle qui les distinguait n'était écrite nulle part.

    Ce test rougit dès qu'un `from sim.constants import ...` réapparaît dans
    le moteur. La référence est dérivée de l'arbre syntaxique, jamais nommée.
    """
    tree = ast.parse(_ENGINE_FILE.read_text(encoding="utf-8"), filename=str(_ENGINE_FILE))
    liees_par_valeur = sorted(
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "sim.constants"
        for alias in node.names
    )
    print(f"constantes_liees_par_valeur = {len(liees_par_valeur)} {liees_par_valeur}")
    assert not liees_par_valeur, (
        "sim/engine.py lie des constantes par valeur : "
        f"{liees_par_valeur}. Les remplacer en mémoire n'atteindrait pas le "
        "moteur. Lire par le module : `_constantes.X`."
    )


def test_chaque_constante_du_moteur_change_le_monde():
    """
    La présence n'est pas la fonction (règle 7) : lire par le module ne suffit
    pas à prouver que la lecture sert. Chaque constante que le moteur consulte
    est remplacée en mémoire, et le monde d'épreuve doit en sortir différent.

    Le balayage essaie plusieurs facteurs, à la hausse ET à la baisse : une
    constante qui est une borne (`min(1.0, ratio)`, plafond de mortalité) ne
    bouge que du côté où la borne cesse de mordre. Un seul facteur à la hausse
    déclarerait ces bornes inertes à tort.

    Portée exacte, dite ici pour que personne ne s'y trompe : le dénominateur
    est dérivé de ce que le moteur consulte. Une constante que le moteur
    CESSE de lire sort donc du dénominateur au lieu de faire rougir — ce
    contrôle-là est `test_aucune_constante_terminale`, dont le dénominateur
    est l'ensemble des constantes déclarées.
    """
    import sim.constants as _k

    # Assez larges pour franchir une borne dans un sens comme dans l'autre.
    facteurs = (0.1, 3.0, 1e6)

    consultees = _constantes_consultees_par_le_moteur()
    assert consultees, (
        "Aucune constante consultée n'a pu être dérivée de sim/engine.py. "
        "Un échantillon vide doit ÉCHOUER, jamais passer en silence (règle 6)."
    )

    reference = _jouer_le_monde_d_epreuve()
    inertes = []
    for nom in sorted(consultees):
        nominal = getattr(_k, nom)
        bouge = False
        for facteur in facteurs:
            setattr(_k, nom, nominal * facteur if nominal else facteur)
            try:
                if _jouer_le_monde_d_epreuve() != reference:
                    bouge = True
                    break
            finally:
                setattr(_k, nom, nominal)
        if not bouge:
            inertes.append(nom)

    print(f"constantes_du_moteur_atteignables = "
          f"{len(consultees) - len(inertes)} / {len(consultees)}")
    assert not inertes, (
        "Remplacer ces constantes en mémoire ne change rien au monde "
        f"d'épreuve : {inertes}. Soit le moteur ne les relit pas, soit "
        "plus personne ne s'en sert."
    )


def test_aucune_constante_terminale():
    """
    Mode de défaillance n° 3, énoncé complètement : une constante déclarée que
    plus personne ne lit est une variable terminale. Elle survit à sa cause,
    elle continue d'être documentée et justifiée, et le jour où quelqu'un la
    modifie il ne se passe rien.

    Le contrôle voisin, `test_chaque_constante_du_moteur_change_le_monde`,
    ne peut pas voir ce cas : son dénominateur est ce que le moteur consulte,
    donc il se rétracte avec sa cible (mode n° 6). Ici le dénominateur est
    l'ensemble des constantes DÉCLARÉES — il ne bouge que si on en supprime
    une, ce qui est précisément l'action que ce test réclame.

    Un test compte comme lecteur : une constante lue seulement par un test qui
    protège un invariant réel fait son travail. Ce qui est refusé, c'est la
    constante que rien ne lit du tout.

    Cas payé : `DEFICIT_ZERO_EPSILON` a survécu deux briefs à la formule
    multiplicative qui l'avait rendue nécessaire, sans qu'aucun contrôle ne
    le signale.
    """
    import sim.constants as _k

    declarees = {
        nom for nom in dir(_k)
        if nom.isupper() and isinstance(getattr(_k, nom), (int, float))
    }
    assert declarees, (
        "Aucune constante déclarée n'a été trouvée dans sim/constants.py : "
        "un échantillon vide doit ÉCHOUER, jamais passer (règle 6)."
    )

    lues = set()
    for fichier in sorted(_SIM_DIR.rglob("*.py")):
        arbre = ast.parse(fichier.read_text(encoding="utf-8"), filename=str(fichier))
        for node in ast.walk(arbre):
            # La déclaration elle-même ne compte pas comme une lecture.
            if fichier.name == "constants.py" and isinstance(node, ast.Assign):
                continue
            if isinstance(node, ast.Attribute) and not isinstance(node.ctx, ast.Store):
                lues.add(node.attr)
            elif isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Store):
                lues.add(node.id)

    terminales = sorted(declarees - lues)
    print(f"constantes_declarees_lues = {len(declarees) - len(terminales)} / {len(declarees)}")
    assert not terminales, (
        f"Constantes déclarées que personne ne lit : {terminales}. "
        "Soit un lecteur a disparu, soit la constante a survécu à sa cause "
        "et doit être retirée."
    )
