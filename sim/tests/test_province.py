"""
La province est une vue dérivée, jamais une donnée stockée.

Ce que ce fichier protège :
  - une seule source de vérité : aucune entité ne porte de champ province ;
    la vue ne transporte que des identifiants, jamais une cellule modifiable ;
  - invariant : chaque cellule relève d'exactement une province ;
  - déterminisme : à égalité de distance, le plus petit identifiant gagne,
    et la dérivation ne modifie aucune entrée.

Fusion des anciens fichiers province_aggregation, redessin_province et
adr_compliance (dont les cas nominatifs étaient déjà couverts ici).
"""

from sim.aggregation import repartition_bourg_de_cellule_consultation

import ast
import dataclasses
import hashlib
import inspect
import json
import pathlib
import pytest
import subprocess
import sys
import tempfile
import sim.aggregation as agregation
import sim.model as modele
from sim.aggregation import (
    PositionCelluleInconnue,
    agregat_depuis_monde,
    appartenance_depuis_regroupements,
    bourg_depuis_monde,
    charger_centres,
    charger_latitude_moyenne,
    charger_positions,
    facteur_de_projection,
    habitants_des_champs_de_cellule,
    habitants_du_bourg_de_cellule,
    identifiant_de_province_de_cellule,
    nom_de_province_de_cellule,
    positions_du_monde,
    projeter,
    province_de_cellule,
    regroupements_non_vides,
    repartition_bourg_de_cellule,
    repartitions_avec_bourg,
)
from sim.model import Cell, _NoBadSpatialField
from sim.world import World
RNG_SEED = 42
_RACINE_DEPOT = pathlib.Path(__file__).parent.parent.parent
_CHEMIN_STATS = _RACINE_DEPOT / "data" / "world-1400.json"
_CHEMIN_CENTRES = (
    _RACINE_DEPOT / "data" / "province-centres-1400.json"
)
_FICHIERS_PRODUCTION = [
    pathlib.Path(agregation.__file__),
    pathlib.Path(agregation.__file__).parent / "world.py",
]
_PREFIXE_INTERDIT = _NoBadSpatialField._FORBIDDEN_PREFIX
_PREFIXES_BOURG_INTERDITS = ("bourg", "ville", "city")
_NOMS_VUE_BOURG = frozenset(
    {
        "bourg_depuis_monde",
        "RepartitionBourg",
        "repartition_bourg_de_cellule",
        "repartitions_avec_bourg",
        "habitants_du_bourg_de_cellule",
        "habitants_des_champs_de_cellule",
        "repartition_bourg_de_cellule_consultation",
    }
)
def _dataclasses_du_module(module):
    """Découvre par introspection les dataclasses déclarées par un module."""
    trouvees = []
    for _nom, obj in inspect.getmembers(module, inspect.isclass):
        if dataclasses.is_dataclass(obj) and obj.__module__ == module.__name__:
            trouvees.append(obj)
    return trouvees
def _normaliser(nom: str) -> str:
    return nom.lower().replace("_", "")
def _sites_de_construction(fichiers, nom_classe: str, champs: set) -> set:
    """Champs passés en argument nommé à un constructeur de la classe."""
    trouves: set = set()
    for chemin in fichiers:
        arbre = ast.parse(chemin.read_text(encoding="utf-8"), filename=str(chemin))
        for noeud in ast.walk(arbre):
            if not isinstance(noeud, ast.Call):
                continue
            fonction = noeud.func
            appelee = (
                fonction.id
                if isinstance(fonction, ast.Name)
                else getattr(fonction, "attr", None)
            )
            if appelee != nom_classe:
                continue
            for mot_cle in noeud.keywords:
                if mot_cle.arg in champs:
                    trouves.add(mot_cle.arg)
    return trouves
def _sites_de_lecture(fichiers, champs: set) -> set:
    """Champs lus (`objet.champ` en contexte Load) dans le code de production."""
    trouves: set = set()
    for chemin in fichiers:
        arbre = ast.parse(chemin.read_text(encoding="utf-8"), filename=str(chemin))
        for noeud in ast.walk(arbre):
            if (
                isinstance(noeud, ast.Attribute)
                and noeud.attr in champs
                and not isinstance(noeud.ctx, ast.Store)
            ):
                trouves.add(noeud.attr)
    return trouves
from sim.aggregation import (
    agregat_depuis_monde,
    appartenance_depuis_regroupements,
    charger_centres,
    charger_positions,
)
def _releve_attributs(monde) -> dict:
    """Contenu complet des attributs d'instance de chaque cellule."""
    return {cell_id: dict(vars(cellule)) for cell_id, cellule in monde.cells.items()}
def _champs_declares(cellule) -> set:
    return {champ.name for champ in dataclasses.fields(cellule)}


# --- test_province_aggregation.py ---
def test_province_couverture_totale_monde_reel():
    """
    sur le monde réel, chaque cellule chargée relève d'exactement une
    province. Aucun nombre de cellules n'est écrit en dur : tout est dérivé
    des fichiers.

    Compteurs : cellules_chargees_g3, centroides_lus, cellules_avec_province,
    cellules_sans_province, cellules_position_absente, provinces_non_vides.
    """
    monde = World.charger(rng_seed=RNG_SEED)
    positions = charger_positions()
    centres = charger_centres()

    cell_count_fichier = len(
        json.loads(_CHEMIN_STATS.read_text(encoding="utf-8"))["cellules"]
    )
    centroides_fichier = len(
        json.loads(_CHEMIN_CENTRES.read_text(encoding="utf-8"))["coordinates"]
    )

    cellules_chargees_g3 = len(monde.cells)
    centroides_lus = len(centres)
    cellules_position_absente = sum(
        1 for cell_id in monde.cells if cell_id not in positions
    )

    regroupements = agregat_depuis_monde(monde, positions=positions, centres=centres)

    # « Exactement une » : ni zéro, ni deux. On compte les occurrences de
    # chaque cellule dans l'ensemble des regroupements.
    occurrences: dict = {}
    for regroupement in regroupements:
        for cell_id in regroupement.cell_ids:
            occurrences[cell_id] = occurrences.get(cell_id, 0) + 1

    cellules_avec_province = sum(
        1 for cell_id in monde.cells if occurrences.get(cell_id, 0) == 1
    )
    cellules_sans_province = sum(
        1 for cell_id in monde.cells if occurrences.get(cell_id, 0) == 0
    )
    cellules_en_double = sum(
        1 for cell_id in monde.cells if occurrences.get(cell_id, 0) > 1
    )
    provinces_non_vides = len(regroupements_non_vides(regroupements))

    print(f"cellules_chargees_g3 = {cellules_chargees_g3} / {cell_count_fichier} (cell_count de stats_g3.json)")
    print(f"centroides_lus = {centroides_lus} / {centroides_fichier} (longueur du tableau coordinates)")
    print(f"cellules_avec_province = {cellules_avec_province} / {cellules_chargees_g3}")
    print(f"cellules_sans_province = {cellules_sans_province} / {cellules_chargees_g3} (zero = mesure reelle, sentinelle = -1)")
    print(f"cellules_position_absente = {cellules_position_absente} / {cellules_chargees_g3}")
    print(f"cellules_en_double = {cellules_en_double} / {cellules_chargees_g3}")
    print(f"provinces_non_vides = {provinces_non_vides} / {centroides_lus} (fait mesure, aucun plancher exige)")

    assert cellules_chargees_g3 == cell_count_fichier
    assert centroides_lus == centroides_fichier
    assert cellules_position_absente == 0
    assert cellules_sans_province == 0
    assert cellules_en_double == 0
    assert cellules_avec_province == cellules_chargees_g3
    # D6 : le nombre de provinces peuplées est rapporté, jamais imposé. La
    # seule borne est celle du réel : il ne peut pas y en avoir plus que de
    # centres lus, et une couverture totale en impose au moins une.
    assert 0 < provinces_non_vides <= centroides_lus


# --- test_province_aggregation.py ---
def test_province_consultation_rend_le_centre_le_plus_proche():
    """
    la consultation de production rend bien le centre le plus proche,
    re-dérivé indépendamment pour un échantillon de cellules.
    """
    monde = World.charger(rng_seed=RNG_SEED)
    positions = charger_positions()
    centres = charger_centres()
    latitude_moyenne = charger_latitude_moyenne()
    facteur = facteur_de_projection(latitude_moyenne)

    regroupements = agregat_depuis_monde(monde, positions=positions, centres=centres)

    verifiees = 0
    for cell_id in sorted(monde.cells):
        latitude, longitude = positions[cell_id]
        abscisse, ordonnee = projeter(latitude, longitude, facteur)

        attendu = min(
            centres,
            key=lambda centre: (
                (abscisse - projeter(centre.lat, centre.lon, facteur)[0]) ** 2
                + (ordonnee - projeter(centre.lat, centre.lon, facteur)[1]) ** 2,
                centre.id,
            ),
        )
        assert identifiant_de_province_de_cellule(cell_id, regroupements) == attendu.id
        assert nom_de_province_de_cellule(cell_id, regroupements) == attendu.name
        verifiees += 1

    print(f"cellules_reverifiees_par_recalcul_independant = {verifiees} / {len(monde.cells)}")
    assert verifiees == len(monde.cells)


# --- test_province_aggregation.py ---
def test_province_refus_position_absente():
    """
    une cellule chargée sans position connue fait lever une erreur
    explicite qui nomme la cellule. Pas de province par défaut, pas d'écart
    silencieux.

    Compteur : refus_position_absente_leve.
    """
    monde = World.charger(rng_seed=RNG_SEED)
    positions = charger_positions()

    cellule_retiree = sorted(monde.cells)[0]
    positions_amputees = dict(positions)
    del positions_amputees[cellule_retiree]

    with pytest.raises(PositionCelluleInconnue) as capture:
        positions_du_monde(monde, positions_amputees)

    message = str(capture.value)
    refus_position_absente_leve = int(str(cellule_retiree) in message)

    print(f"cellule retiree en memoire : {cellule_retiree}")
    print(f"message : {message}")
    print(f"refus_position_absente_leve = {refus_position_absente_leve} / 1")

    assert refus_position_absente_leve == 1

    # L'agrégat complet refuse pour la même raison : le refus n'est pas
    # cantonné à la fonction interne.
    with pytest.raises(PositionCelluleInconnue):
        agregat_depuis_monde(monde, positions=positions_amputees)


# --- test_province_aggregation.py ---
def test_province_aucun_champ_province_sur_entites():
    """
    par introspection : aucune dataclass de `sim.model` ni du module
    d'agrégation ne déclare de champ dont le nom normalisé commence par le
    préfixe interdit.

    Le contrôle ne nomme aucune classe : `Person`, `Family` et `Building`
    n'existent pas encore, et un contrôle nommé d'après sa cible les
    laisserait passer.

    Compteurs : champs_province_sur_entites, dataclasses_inspectees.
    """
    classes = _dataclasses_du_module(modele) + _dataclasses_du_module(agregation)

    champs_inspectes = 0
    fautifs = []
    for classe in classes:
        for champ in dataclasses.fields(classe):
            champs_inspectes += 1
            if _normaliser(champ.name).startswith(_PREFIXE_INTERDIT):
                fautifs.append(f"{classe.__name__}.{champ.name}")

    dataclasses_inspectees = len(classes)
    champs_province_sur_entites = len(fautifs)

    print(f"classes inspectees : {[c.__name__ for c in classes]}")
    print(f"prefixe interdit derive de la garde : {_PREFIXE_INTERDIT!r}")
    print(f"dataclasses_inspectees = {dataclasses_inspectees} / {dataclasses_inspectees}")
    print(f"champs_province_sur_entites = {champs_province_sur_entites} / {champs_inspectes}")

    assert dataclasses_inspectees > 0, "introspection vide : rien n'a ete controle"
    assert champs_inspectes > 0, "denominateur nul : aucun champ regarde"
    assert champs_province_sur_entites == 0, f"champs interdits : {fautifs}"


# --- test_province_aggregation.py ---
def test_province_garde_prefixe_variantes_rouges():
    """
    la garde `_NoBadSpatialField` est exercée : chaque variante de nom
    interdit lève une `TypeError` qui nomme la clé spatiale unique.

    Compteur : garde_prefixe_variantes_rouges.
    """
    variantes = ["province_id", "ProvinceId", "province", "province_code", "provinceCode"]

    levees = 0
    for variante in variantes:
        classe = dataclasses.make_dataclass(
            "Sonde",
            [("cell_id", int), (variante, str)],
            bases=(_NoBadSpatialField,),
        )
        with pytest.raises(TypeError, match="seule clé spatiale"):
            classe(**{"cell_id": 1, variante: "X"})
        levees += 1

    print(f"variantes essayees : {variantes}")
    print(f"garde_prefixe_variantes_rouges = {levees} / {len(variantes)}")
    assert levees == len(variantes)


# --- test_province_aggregation.py ---
def test_province_champs_vue_couverts():
    """
    mode d'échec n° 2 appliqué à la vue dérivée : chaque champ déclaré
    par le module d'agrégation a au moins un site de construction ET au moins
    un site de lecture dans le code de production.

    Les types sont découverts par introspection du module, jamais listés à la
    main. Un champ sans lecteur de production doit être supprimé.

    Compteur : champs_vue_couverts.
    """
    classes = _dataclasses_du_module(agregation)
    assert classes, "aucun type declare par le module d'agregation"

    champs_declares = 0
    champs_vue_couverts = 0
    manquants = []

    for classe in classes:
        champs = {champ.name for champ in dataclasses.fields(classe)}
        constructions = _sites_de_construction(_FICHIERS_PRODUCTION, classe.__name__, champs)
        lectures = _sites_de_lecture(_FICHIERS_PRODUCTION, champs)

        for champ in sorted(champs):
            champs_declares += 1
            if champ in constructions and champ in lectures:
                champs_vue_couverts += 1
            else:
                manquants.append(
                    f"{classe.__name__}.{champ} "
                    f"(construction={champ in constructions}, lecture={champ in lectures})"
                )

        print(f"{classe.__name__} : champs={sorted(champs)} construits={sorted(constructions)} lus={sorted(lectures & champs)}")

    print(f"fichiers de production : {[p.name for p in _FICHIERS_PRODUCTION]}")
    print(f"champs_vue_couverts = {champs_vue_couverts} / {champs_declares}")

    assert champs_declares > 0
    assert champs_vue_couverts == champs_declares, f"champs non couverts : {manquants}"


# --- test_province_aggregation.py ---
def test_province_egalites_de_distance_monde_reel():
    """
    nombre de cellules du monde réel dont la distance minimale est
    atteinte par au moins deux centres (égalité exacte en flottant). Ce
    compteur peut légitimement valoir 0 : c'est un fait mesuré, pas une
    sentinelle.

    Compteur : egalites_de_distance_monde_reel.
    """
    monde = World.charger(rng_seed=RNG_SEED)
    positions = charger_positions()
    centres = charger_centres()
    facteur = facteur_de_projection(charger_latitude_moyenne())

    centres_projetes = [
        (centre.id, *projeter(centre.lat, centre.lon, facteur)) for centre in centres
    ]

    egalites = 0
    for cell_id in sorted(monde.cells):
        latitude, longitude = positions[cell_id]
        abscisse, ordonnee = projeter(latitude, longitude, facteur)
        carres = [
            (abscisse - cx) ** 2 + (ordonnee - cy) ** 2 for _cid, cx, cy in centres_projetes
        ]
        minimum = min(carres)
        if carres.count(minimum) > 1:
            egalites += 1

    print(f"egalites_de_distance_monde_reel = {egalites} / {len(monde.cells)} (fait mesure, peut valoir 0)")
    assert egalites >= 0


# --- test_province_aggregation.py ---
def test_province_agregation_ne_reference_aucune_cellule_modifiable():
    """
    la vue dérivée ne transporte que des identifiants : jamais un objet
    `Cell` modifiable. Un agrégat qui référencerait des cellules rouvrirait la
    porte à leur réécriture.
    """
    monde = World.charger(rng_seed=RNG_SEED)
    regroupements = agregat_depuis_monde(monde)

    types_transportes = set()
    for regroupement in regroupements:
        for cell_id in regroupement.cell_ids:
            types_transportes.add(type(cell_id))

    print(f"types transportes par cell_ids : {sorted(t.__name__ for t in types_transportes)}")
    assert types_transportes == {int}
    assert province_de_cellule(sorted(monde.cells)[0], regroupements) is not None

    appartenance = appartenance_depuis_regroupements(regroupements)
    assert set(appartenance) == set(monde.cells)


# --- test_redessin_province.py ---
def test_redessin_change_agregat_sans_reecrire_les_cellules():
    """
    les deux faits sont vérifiés ensemble : l'agrégat bouge ET les
    cellules ne bougent pas. Vérifier l'un sans l'autre ne prouverait rien.
    """
    monde = World.charger(rng_seed=RNG_SEED)
    positions = charger_positions()
    centres = charger_centres()

    regroupements_a = agregat_depuis_monde(monde, positions=positions, centres=centres)
    appartenance_a = appartenance_depuis_regroupements(regroupements_a)

    serialisation_avant = json.dumps(monde.to_dict(), sort_keys=True)
    attributs_avant = _releve_attributs(monde)
    octets_avant = _CHEMIN_CENTRES.read_bytes()

    # Le centre de plus petit id est déplacé sur la position exacte d'une
    # cellule qui relève actuellement d'un autre centre : à distance nulle il
    # gagne, et une éventuelle égalité serait tranchée en sa faveur par D4.
    centre_deplace = min(centres, key=lambda centre: centre.id)
    cible = next(
        cell_id
        for cell_id in sorted(appartenance_a)
        if appartenance_a[cell_id] != centre_deplace.id
    )
    latitude_cible, longitude_cible = positions[cible]

    centres_redessines = [
        dataclasses.replace(centre, lat=latitude_cible, lon=longitude_cible)
        if centre.id == centre_deplace.id
        else centre
        for centre in centres
    ]

    regroupements_b = agregat_depuis_monde(
        monde, positions=positions, centres=centres_redessines
    )
    appartenance_b = appartenance_depuis_regroupements(regroupements_b)

    serialisation_apres = json.dumps(monde.to_dict(), sort_keys=True)
    attributs_apres = _releve_attributs(monde)
    octets_apres = _CHEMIN_CENTRES.read_bytes()

    cellules_changeant = sum(
        1 for cell_id in appartenance_a if appartenance_a[cell_id] != appartenance_b[cell_id]
    )
    redessin_change_agregat = int(cellules_changeant > 0)

    attributs_dynamiques = sum(
        1
        for cell_id, cellule in monde.cells.items()
        if set(vars(cellule)) - _champs_declares(cellule)
    )

    redessin_cellules_intactes = int(
        serialisation_avant == serialisation_apres and attributs_avant == attributs_apres
    )
    fichier_centroides_inchange = int(octets_avant == octets_apres)

    total = len(monde.cells)
    print(f"centre deplace : id={centre_deplace.id} nom={centre_deplace.name}")
    print(f"cellule cible : {cible} (relevait du centre {appartenance_a[cible]})")
    print(f"redessin_change_agregat = {redessin_change_agregat} / 1")
    print(f"cellules_changeant_de_province_apres_redessin = {cellules_changeant} / {total}")
    print(f"redessin_cellules_intactes = {redessin_cellules_intactes} / 1 ({total} cellules comparees)")
    print(f"attributs_dynamiques_sur_cellules = {attributs_dynamiques} / {total}")
    print(f"fichier_centroides_inchange_apres_redessin = {fichier_centroides_inchange} / 1")

    assert redessin_change_agregat == 1, (
        "Le redessin ne change aucune appartenance : la province n'est pas "
        "derivee, elle est figee."
    )
    assert cellules_changeant > 0
    assert appartenance_b[cible] == centre_deplace.id, (
        "A distance nulle, le centre deplace doit gagner."
    )
    assert attributs_dynamiques == 0, (
        "Au moins une cellule a acquis un attribut d'instance : "
        "l'appartenance a ete estampillee sur les cellules."
    )
    assert redessin_cellules_intactes == 1, (
        "La serialisation ou les attributs des cellules ont change pendant le "
        "redessin : la province a ete reecrite sur les habitants."
    )
    assert fichier_centroides_inchange == 1, (
        "Le fichier de centres a change sur le disque : le lot est en lecture "
        "seule sur les donnees geographiques."
    )


# --- test_redessin_province.py ---
def test_redessin_naffecte_pas_les_enregistrements_lus():
    """
    le redessin produit de nouveaux enregistrements de centres ; il ne
    réécrit pas ceux qui ont été lus du fichier.
    """
    centres = charger_centres()
    avant = [dataclasses.astuple(centre) for centre in centres]

    centre_deplace = min(centres, key=lambda centre: centre.id)
    redessines = [
        dataclasses.replace(centre, lat=centre.lat + 1.0, lon=centre.lon + 1.0)
        if centre.id == centre_deplace.id
        else centre
        for centre in centres
    ]

    apres = [dataclasses.astuple(centre) for centre in centres]
    modifies = sum(1 for a, b in zip(avant, apres) if a != b)
    rang = centres.index(centre_deplace)

    print(f"enregistrements_de_centres_modifies = {modifies} / {len(centres)}")
    assert modifies == 0
    assert redessines[rang] != centres[rang]


def _modules_sim_hors_tests() -> list[pathlib.Path]:
    """Modules de sim/ hors tests ; le dénominateur se dérive du répertoire."""
    sim_dir = pathlib.Path(agregation.__file__).parent
    return sorted(
        p
        for p in sim_dir.rglob("*.py")
        if "tests" not in p.relative_to(sim_dir).parts
    )


_REF_MASTER: list[str] = []


def _ref_master() -> str:
    """Réf git de master, fetchée si le clone ne la porte pas."""
    if _REF_MASTER:
        return _REF_MASTER[0]
    for ref in ("origin/master", "master"):
        probe = subprocess.run(
            ["git", "rev-parse", "--verify", ref],
            cwd=_RACINE_DEPOT,
            capture_output=True,
            text=True,
        )
        if probe.returncode == 0:
            _REF_MASTER.append(ref)
            return ref
    fetched = subprocess.run(
        ["git", "fetch", "--depth=1", "origin", "master:refs/remotes/origin/master"],
        cwd=_RACINE_DEPOT,
        capture_output=True,
        text=True,
    )
    assert fetched.returncode == 0, (
        "impossible de rejouer master : "
        f"git fetch origin master a échoué ({fetched.stderr.strip()})"
    )
    _REF_MASTER.append("origin/master")
    return _REF_MASTER[0]


def _dataclasses_ast_modules(modules: list[pathlib.Path]) -> list[tuple[str, list[str]]]:
    """Découvre par AST les dataclasses et leurs champs déclarés."""
    trouvees: list[tuple[str, list[str]]] = []
    for chemin in modules:
        arbre = ast.parse(chemin.read_text(encoding="utf-8"), filename=str(chemin))
        for noeud in arbre.body:
            if not isinstance(noeud, ast.ClassDef):
                continue
            est_dataclass = any(
                (isinstance(dec, ast.Name) and dec.id == "dataclass")
                or (isinstance(dec, ast.Attribute) and dec.attr == "dataclass")
                or (
                    isinstance(dec, ast.Call)
                    and (
                        (isinstance(dec.func, ast.Name) and dec.func.id == "dataclass")
                        or (
                            isinstance(dec.func, ast.Attribute)
                            and dec.func.attr == "dataclass"
                        )
                    )
                )
                for dec in noeud.decorator_list
            )
            if not est_dataclass:
                continue
            champs: list[str] = []
            for item in noeud.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    champs.append(item.target.id)
            trouvees.append((f"{chemin.stem}.{noeud.name}", champs))
    return trouvees


def _champs_prefixe_interdit(classes, prefixes: tuple[str, ...]) -> list[str]:
    fautifs: list[str] = []
    for nom_classe, champs in classes:
        for champ in champs:
            if _normaliser(champ).startswith(prefixes):
                fautifs.append(f"{nom_classe}.{champ}")
    return fautifs


def _agreger_gisements_carte(carte_doc: dict) -> int:
    """Nombre de cellules porteuses d'au moins un gisement complet."""
    cellules = 0
    for raw in carte_doc["cellules"]:
        gisements = raw.get("gisements") or []
        complets = [
            g
            for g in gisements
            if isinstance(g, dict)
            and g.get("ressource") is not None
            and g.get("richesse") is not None
        ]
        if complets:
            cellules += 1
    return cellules


def _sortie_sim_json(ticks: int, seed: int, cwd: pathlib.Path) -> bytes:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "sim",
            "--ticks",
            str(ticks),
            "--seed",
            str(seed),
            "--json",
        ],
        cwd=cwd,
        capture_output=True,
        check=True,
    )
    return proc.stdout


def _gisements_complets(raw: dict) -> list:
    return [
        g
        for g in (raw.get("gisements") or [])
        if isinstance(g, dict)
        and g.get("ressource") is not None
        and g.get("richesse") is not None
    ]


# --- Brief 047 : le bourg est une agrégation dérivée ---


def test_bourg_vue_pure_sans_mutation_monde():
    """
    SC1 — Deux appels successifs rendent un résultat égal, et le monde en
    sort inchangé.
    """
    monde = World.charger(rng_seed=RNG_SEED)

    serialisation_avant = json.dumps(monde.to_dict(), sort_keys=True)
    attributs_avant = _releve_attributs(monde)

    repartitions_a = bourg_depuis_monde(monde)
    repartitions_b = bourg_depuis_monde(monde)

    serialisation_apres = json.dumps(monde.to_dict(), sort_keys=True)
    attributs_apres = _releve_attributs(monde)

    cellules_comparees = len(monde.cells)
    vue_egale = int(repartitions_a == repartitions_b)
    monde_inchange = int(
        serialisation_avant == serialisation_apres and attributs_avant == attributs_apres
    )

    print(f"cellules_comparees = {cellules_comparees} / {cellules_comparees}")
    print(f"vue_egale = {vue_egale} / 1")
    print(f"monde_inchange = {monde_inchange} / 1")

    assert cellules_comparees > 0, "échantillon vide : aucune cellule chargée"
    assert vue_egale == 1
    assert monde_inchange == 1


def test_bourg_aucune_seconde_cle_spatiale():
    """
    SC2 — Aucune entité ne déclare de champ bourg / ville / city ; le
    contrôle rougit sur une sonde délibérée.
    """
    modules = _modules_sim_hors_tests()
    classes = _dataclasses_ast_modules(modules)
    dataclasses_inspectees = len(classes)
    assert dataclasses_inspectees > 0, "introspection vide : rien n'a été contrôlé"

    fautifs = _champs_prefixe_interdit(classes, _PREFIXES_BOURG_INTERDITS)
    champs_bourg_sur_entites = len(fautifs)

    print(f"dataclasses_inspectees = {dataclasses_inspectees}")
    print(f"prefixes_interdits = {_PREFIXES_BOURG_INTERDITS!r}")
    print(f"champs_bourg_sur_entites = {champs_bourg_sur_entites}")

    assert champs_bourg_sur_entites == 0, f"champs interdits : {fautifs}"

    sonde = dataclasses.make_dataclass(
        "SondeBourg",
        [("cell_id", int), ("bourg_id", int)],
        bases=(_NoBadSpatialField,),
    )
    classes_avec_sonde = classes + [("SondeBourg", ["cell_id", "bourg_id"])]
    fautifs_sonde = _champs_prefixe_interdit(classes_avec_sonde, _PREFIXES_BOURG_INTERDITS)
    garde_prefixe_bourg_rouge = len(fautifs_sonde)

    print(f"garde_prefixe_bourg_rouge = {garde_prefixe_bourg_rouge}")
    assert garde_prefixe_bourg_rouge > 0, (
        "le contrôle ne rougit pas sur une entité d'épreuve portant bourg_id"
    )


def test_bourg_tick_ne_consulte_pas_la_vue():
    """
    SC3 — Le moteur n'importe pas sim.aggregation et ne référence pas la vue.
    """
    modules = _modules_sim_hors_tests()
    modules_parcourus = len(modules)
    assert modules_parcourus > 0, "échantillon vide : aucun module de sim/ hors tests"

    engine_path = pathlib.Path(agregation.__file__).parent / "engine.py"
    arbre = ast.parse(engine_path.read_text(encoding="utf-8"), filename=str(engine_path))

    references_interdites: list[str] = []
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.Import):
            for alias in noeud.names:
                if alias.name == "sim.aggregation" or alias.name.endswith(".aggregation"):
                    references_interdites.append(f"import {alias.name}")
        elif isinstance(noeud, ast.ImportFrom):
            if noeud.module and noeud.module.endswith("aggregation"):
                references_interdites.append(f"from {noeud.module}")
        elif isinstance(noeud, ast.Name) and noeud.id in _NOMS_VUE_BOURG:
            references_interdites.append(f"nom {noeud.id}")
        elif isinstance(noeud, ast.Attribute) and noeud.attr in _NOMS_VUE_BOURG:
            references_interdites.append(f"attribut {noeud.attr}")

    references_moteur = len(references_interdites)
    print(f"modules_parcourus = {modules_parcourus}")
    print(f"references_moteur = {references_moteur} {references_interdites}")

    assert references_moteur == 0, (
        "le tick consulte la vue bourg : " + ", ".join(references_interdites)
    )


def test_bourg_echantillon_non_vide():
    """
    SC4 — Sur le monde réel, au moins une cellule compte un bourg non nul.
    Rapporte aussi les cellules porteuses de gisement sur la carte.
    """
    monde = World.charger(rng_seed=RNG_SEED)
    repartitions = bourg_depuis_monde(monde)
    cellules_chargees = len(monde.cells)
    assert cellules_chargees > 0, "échantillon vide : aucune cellule chargée"

    cellules_avec_bourg = len(repartitions_avec_bourg(repartitions))
    cellules_porteuses_carte = _agreger_gisements_carte(World.lire_carte())

    print(
        f"cellules_avec_bourg = {cellules_avec_bourg} / {cellules_chargees} "
        f"cellules_porteuses_carte = {cellules_porteuses_carte}"
    )

    assert cellules_avec_bourg > 0, (
        "échantillon vide : aucune part non agricole — le lot 044 n'est pas fusionné"
    )


def test_bourg_richesse_ordonne_habitants():
    """
    SC5 (ordre) — À population égale, le bourg suit l'ordre des richesses
    dérivé de la carte : majeure > notable > mineure.
    """
    from sim import constants as _k

    facteurs = _k.facteurs_richesse_extraction()
    par_classe: dict[str, list] = {}
    for raw in World.lire_carte()["cellules"]:
        complets = _gisements_complets(raw)
        if len(complets) != 1:
            continue
        richesse = complets[0]["richesse"]
        if richesse in facteurs and richesse not in par_classe:
            par_classe[richesse] = complets

    assert set(par_classe) == set(facteurs), (
        f"classe manquante dans l'échantillon : {set(facteurs) - set(par_classe)}"
    )

    population_egale = 10000
    cellule = Cell(cell_id=1, area_km2=1.0, population=population_egale)
    comptes = {
        richesse: repartition_bourg_de_cellule(cellule, gisements).habitants_du_bourg
        for richesse, gisements in par_classe.items()
    }

    print(
        f"bourg_majeure={comptes['majeure']} bourg_notable={comptes['notable']} "
        f"bourg_mineure={comptes['mineure']} population={population_egale}"
    )
    assert comptes["majeure"] > comptes["notable"] > comptes["mineure"]


def test_bourg_une_seule_definition_part_non_agricole():
    """
    SC5 (unicité) — La part non agricole n'est calculée qu'une fois ; aucun
    second jeu de facteurs de richesse n'apparaît dans sim/aggregation.py.
    """
    from sim import constants as _k

    modules = _modules_sim_hors_tests()
    n_modules = len(modules)
    assert n_modules > 0, "échantillon vide : aucun module de sim/ hors tests"

    noms_part = {"PART_MINIERE_PAR_GISEMENT", "PART_MINIERE_MAXIMALE"}
    classes_carte = set(_k.facteurs_richesse_extraction())

    lecteurs_part_agregation: set[str] = set()
    jeux_richesse_agregation = 0
    chemin_agregation = pathlib.Path(agregation.__file__)
    source = chemin_agregation.read_text(encoding="utf-8")
    arbre = ast.parse(source, filename=str(chemin_agregation))

    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.FunctionDef):
            lus = {
                enfant.id
                for enfant in ast.walk(noeud)
                if isinstance(enfant, ast.Name) and not isinstance(enfant.ctx, ast.Store)
            }
            attrs = {
                enfant.attr
                for enfant in ast.walk(noeud)
                if isinstance(enfant, ast.Attribute) and not isinstance(enfant.ctx, ast.Store)
            }
            if lus & noms_part or attrs & noms_part:
                lecteurs_part_agregation.add(noeud.name)
        if isinstance(noeud, ast.Dict):
            cles = {
                cle.value
                for cle in noeud.keys
                if isinstance(cle, ast.Constant) and isinstance(cle.value, str)
            }
            if classes_carte and classes_carte <= cles:
                jeux_richesse_agregation += 1

    definisseurs_part: set[str] = set()
    for fichier in modules:
        texte = fichier.read_text(encoding="utf-8")
        arbre_f = ast.parse(texte, filename=str(fichier))
        for noeud in ast.walk(arbre_f):
            if not isinstance(noeud, ast.FunctionDef):
                continue
            lus = {
                enfant.id
                for enfant in ast.walk(noeud)
                if isinstance(enfant, ast.Name) and not isinstance(enfant.ctx, ast.Store)
            }
            attrs = {
                enfant.attr
                for enfant in ast.walk(noeud)
                if isinstance(enfant, ast.Attribute) and not isinstance(enfant.ctx, ast.Store)
            }
            if lus & noms_part or attrs & noms_part:
                definisseurs_part.add(f"{fichier.name}:{noeud.name}")

    n_lecteurs_agregation = len(lecteurs_part_agregation)
    n_definisseurs_part = len(definisseurs_part)

    print(f"modules_parcourus={n_modules}")
    print(f"lecteurs_part_agregation={n_lecteurs_agregation} {sorted(lecteurs_part_agregation)}")
    print(f"jeux_richesse_agregation={jeux_richesse_agregation}")
    print(f"definisseurs_part={n_definisseurs_part} {sorted(definisseurs_part)}")

    assert n_lecteurs_agregation == 0, (
        "sim/aggregation.py duplique la formule de part non agricole : "
        f"{sorted(lecteurs_part_agregation)}"
    )
    assert jeux_richesse_agregation == 0, (
        f"un second jeu de facteurs de richesse apparaît : {jeux_richesse_agregation}"
    )
    assert n_definisseurs_part == 1, (
        f"plus d'une définition de part non agricole : {sorted(definisseurs_part)}"
    )


def test_bourg_somme_exacte_par_cellule():
    """
    SC6 — Pour toute cellule : habitants_du_bourg + habitants_des_champs
    == population, sans tolérance.
    """
    monde = World.charger(rng_seed=RNG_SEED)
    repartitions = bourg_depuis_monde(monde)
    cellules_sommees = len(repartitions)
    assert cellules_sommees > 0, "échantillon vide : aucune cellule sommée"

    ecarts = 0
    for repartition in repartitions:
        somme = repartition.habitants_du_bourg + repartition.habitants_des_champs
        population = monde.cells[repartition.cell_id].population
        if somme != population:
            ecarts += 1

    print(f"ecarts_somme = {ecarts} / {cellules_sommees}")
    assert ecarts == 0


def test_bourg_ne_change_pas_sortie_sim(monkeypatch):
    """Consulter le bourg ne change ni le résumé ni l'état de la même course."""
    import json
    from sim import __main__ as cli
    from sim import aggregation
    from sim import constants

    ticks = constants.CALENDAR_DAYS_PER_YEAR // constants.TICK_DURATION_DAYS
    assert ticks > 0
    sans_vue, monde_sans_vue = cli._simulate(ticks, constants.DEFAULT_CLI_SEED)
    assert monde_sans_vue.cells
    tick_original = cli.tick
    consultations = []

    def tick_avec_consultation(world, rng, numero_tick):
        kg = tick_original(world, rng, numero_tick)
        repartitions = aggregation.bourg_depuis_monde(world)
        assert len(repartitions) == len(world.cells) > 0
        consultations.append(numero_tick)
        return kg

    monkeypatch.setattr(cli, "tick", tick_avec_consultation)
    avec_vue, monde_avec_vue = cli._simulate(ticks, constants.DEFAULT_CLI_SEED)
    assert len(consultations) == ticks
    assert json.dumps(avec_vue, sort_keys=True) == json.dumps(sans_vue, sort_keys=True)
    assert monde_avec_vue.to_dict() == monde_sans_vue.to_dict()
    assert monde_avec_vue.stocks_mer == monde_sans_vue.stocks_mer


def test_bourg_consultation_par_cell_id():
    """Les helpers de consultation rendent la répartition attendue."""
    monde = World.charger(rng_seed=RNG_SEED)
    repartitions = bourg_depuis_monde(monde)
    cell_id = sorted(monde.cells)[0]
    repartition = repartitions[0]

    assert habitants_du_bourg_de_cellule(cell_id, repartitions) == repartition.habitants_du_bourg
    assert (
        habitants_des_champs_de_cellule(cell_id, repartitions)
        == repartition.habitants_des_champs
    )


def test_bourg_cellule_inconnue_n_est_pas_un_zero():
    """Une cellule absente de la vue n'a pas 0 habitant au bourg : l'absence se déclare."""
    monde = World.charger(rng_seed=RNG_SEED)
    repartitions = bourg_depuis_monde(monde)
    assert monde.cells, "échantillon vide : aucune cellule chargée"
    inconnu = max(int(cid) for cid in monde.cells) + 1
    assert inconnu not in monde.cells
    assert repartition_bourg_de_cellule_consultation(inconnu, repartitions) is None
    assert habitants_du_bourg_de_cellule(inconnu, repartitions) is None
    assert habitants_des_champs_de_cellule(inconnu, repartitions) is None


def test_bourg_sans_gisement_est_toute_campagne():
    """Sans métier, tout le monde cultive : le bourg vaut zéro, la campagne est le reste."""
    cellule = Cell(cell_id=1, area_km2=1.0, population=100)
    repartition = repartition_bourg_de_cellule(cellule, [])
    assert repartition.habitants_du_bourg == 0
    assert repartition.habitants_des_champs == 100
    assert (
        repartition.habitants_du_bourg + repartition.habitants_des_champs
        == cellule.population
    )
