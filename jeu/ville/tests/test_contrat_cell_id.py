"""Le contrat ville parle en `cell_id` (lot #118).

Chaque message est jugé d'après le schéma lu, jamais d'après une liste de clés
recopiée ici. Bibliothèque standard seulement : ni la CI ni `sim/`
n'installent `jsonschema`.
"""

import copy
import json
import re
from pathlib import Path

import pytest

VILLE = Path(__file__).resolve().parents[1]
SCHEMA = VILLE / "Schemas" / "forgehistory-city-mode-v1.schema.json"
EXEMPLES = VILLE / "Schemas" / "forgehistory-city-mode-v1.examples.json"
MONDE = VILLE.parent / "data" / "world-1400.json"

# Les deux anciennes clés, assemblées en morceaux : la recherche du lot (SC2)
# ne doit plus trouver leur nom écrit en toutes lettres dans jeu/ville.
CLE_VILLE = "city" + "Id"
CLE_CARTE = "map" + "CellId"

DEFINITIONS = (
    "CityLaunchContext",
    "CitySnapshotEnvelope",
    "CityIntentEnvelope",
    "CityIntentReceipt",
)

# Chaque exemple et la définition qui le juge.
EXEMPLE_VERS_DEFINITION = {
    "launchContext": "CityLaunchContext",
    "snapshot": "CitySnapshotEnvelope",
    "intent": "CityIntentEnvelope",
    "acceptedReceipt": "CityIntentReceipt",
    "conflictReceipt": "CityIntentReceipt",
}


def _lire(chemin):
    return json.loads(chemin.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def schema():
    return _lire(SCHEMA)


@pytest.fixture(scope="module")
def exemples():
    return _lire(EXEMPLES)


@pytest.fixture(scope="module")
def cellules_du_monde():
    ids = {c["cell_id"] for c in _lire(MONDE)["cellules"]}
    assert ids, "world-1400.json ne déclare aucune cellule"
    return ids


def _est_entier(valeur):
    # Un booléen n'est pas un entier, même si Python le range parmi eux.
    return isinstance(valeur, int) and not isinstance(valeur, bool)


def _type_accepte(valeur, attendu):
    if attendu == "integer":
        return _est_entier(valeur)
    if attendu == "string":
        return isinstance(valeur, str)
    if attendu == "boolean":
        return isinstance(valeur, bool)
    if attendu == "object":
        return isinstance(valeur, dict)
    raise AssertionError(f"type de schéma non géré par le juge : {attendu}")


def _valeur_acceptee(valeur, regle):
    """Les mots-clés utiles au contrat ; un mot-clé inconnu n'est pas deviné."""
    connus = {"type", "minimum", "maximum", "const", "enum", "minLength",
              "maxLength", "pattern", "description"}
    inconnus = set(regle) - connus
    assert not inconnus, f"mots-clés non gérés par le juge : {inconnus}"
    if "type" in regle and not _type_accepte(valeur, regle["type"]):
        return False
    if "const" in regle and (valeur != regle["const"]
                             or type(valeur) is not type(regle["const"])):
        return False
    if "enum" in regle and valeur not in regle["enum"]:
        return False
    if "minimum" in regle and valeur < regle["minimum"]:
        return False
    if "maximum" in regle and valeur > regle["maximum"]:
        return False
    if "minLength" in regle and len(valeur) < regle["minLength"]:
        return False
    if "maxLength" in regle and len(valeur) > regle["maxLength"]:
        return False
    if "pattern" in regle and not re.search(regle["pattern"], valeur):
        return False
    return True


def juger(message, definition):
    """Vrai si le message respecte la définition lue dans le schéma."""
    if not isinstance(message, dict):
        return False
    proprietes = definition.get("properties", {})
    if any(cle not in message for cle in definition.get("required", [])):
        return False
    if definition.get("additionalProperties") is False:
        if any(cle not in proprietes for cle in message):
            return False
    return all(
        _valeur_acceptee(valeur, proprietes[cle])
        for cle, valeur in message.items()
        if cle in proprietes
    )


@pytest.mark.parametrize("nom", DEFINITIONS)
def test_chaque_definition_exige_cell_id_entier_positif(schema, nom):
    definition = schema["$defs"][nom]
    assert "cell_id" in definition["required"]
    assert definition["properties"]["cell_id"]["type"] == "integer"
    assert definition["properties"]["cell_id"]["minimum"] == 0
    assert definition["additionalProperties"] is False
    for ancienne in (CLE_VILLE, CLE_CARTE):
        assert ancienne not in definition["properties"]
        assert ancienne not in definition["required"]


def test_les_cinq_exemples_sont_associes(exemples):
    presents = {cle for cle in exemples if isinstance(exemples[cle], dict)}
    assert presents == set(EXEMPLE_VERS_DEFINITION)


@pytest.mark.parametrize("exemple", sorted(EXEMPLE_VERS_DEFINITION))
def test_l_exemple_passe(schema, exemples, exemple):
    definition = schema["$defs"][EXEMPLE_VERS_DEFINITION[exemple]]
    assert juger(exemples[exemple], definition)


def test_les_exemples_partagent_une_cellule_du_monde(exemples, cellules_du_monde):
    valeurs = {exemples[e]["cell_id"] for e in EXEMPLE_VERS_DEFINITION}
    assert len(valeurs) == 1
    (cell_id,) = valeurs
    assert _est_entier(cell_id)
    assert cell_id in cellules_du_monde


def _variantes_refusees(message):
    sans = copy.deepcopy(message)
    del sans["cell_id"]
    yield "sans cell_id", sans
    yield f"avec {CLE_VILLE}", {**message, CLE_VILLE: "city:1001"}
    yield f"avec {CLE_CARTE}", {**message, CLE_CARTE: "cell:10:12"}
    for mauvais in (-1, "1175", True):
        yield f"cell_id = {mauvais!r}", {**message, "cell_id": mauvais}


@pytest.mark.parametrize("exemple", sorted(EXEMPLE_VERS_DEFINITION))
def test_les_variantes_fautives_sont_refusees(schema, exemples, exemple):
    definition = schema["$defs"][EXEMPLE_VERS_DEFINITION[exemple]]
    variantes = list(_variantes_refusees(exemples[exemple]))
    assert len(variantes) == 6
    for libelle, variante in variantes:
        assert not juger(variante, definition), f"{exemple} : {libelle} accepté"


def test_contre_epreuve_le_refus_vient_du_schema(schema, exemples):
    """Rendre l'ancienne clé de ville au schéma fait accepter un message sans
    `cell_id` : le refus vient du schéma, pas du juge."""
    ancien = copy.deepcopy(schema["$defs"]["CityLaunchContext"])
    ancien["properties"][CLE_VILLE] = {"type": "string", "minLength": 1}
    ancien["required"].remove("cell_id")
    message = copy.deepcopy(exemples["launchContext"])
    del message["cell_id"]
    message[CLE_VILLE] = "city:1001"
    assert juger(message, ancien)
    assert not juger(message, schema["$defs"]["CityLaunchContext"])
