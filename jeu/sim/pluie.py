"""Vue dérivée de la pluie annuelle reçue par chaque cellule.

Les relevés sont des points documentés. Une cellule reçoit la valeur du
relevé le plus proche selon l'unique règle spatiale de ``sim.aggregation``.
La vue est recalculée à chaque consultation et ne modifie jamais le monde.
"""

import dataclasses
import json
import math
import pathlib

from sim.aggregation import (
    charger_positions,
    derive_appartenance,
    positions_du_monde,
)
from sim.model import _NoBadSpatialField


_RACINE_DEPOT = pathlib.Path(__file__).parent.parent
_CHEMIN_RELEVES = _RACINE_DEPOT / "data" / "pluie-releves-1400.json"

_CLE_CLIMAT_DE_1400 = "climat_de_1400"
_CLE_UNITE = "unite"
_CLE_PROJECTION = "projection"
_CLE_LATITUDE_MOYENNE = "mid_latitude"
_CLE_RELEVES = "releves"
_CLE_IDENTIFIANT = "id"
_CLE_NOM = "nom"
_CLE_LATITUDE = "lat"
_CLE_LONGITUDE = "lon"
_CLE_PLUIE = "mm_par_an"
_CLE_SOURCE = "source"
_UNITE_ATTENDUE = "mm/an"


class ReleveDePluieInvalide(ValueError):
    """Levée quand la table ne permet pas de dériver honnêtement la pluie."""


@dataclasses.dataclass(frozen=True)
class ReleveDePluie(_NoBadSpatialField):
    """Relevé ponctuel documenté de cumul annuel moyen."""

    id: int
    nom: str
    lat: float
    lon: float
    mm_par_an: float
    source: str


@dataclasses.dataclass(frozen=True)
class PluieDeCellule(_NoBadSpatialField):
    """Valeur du relevé le plus proche d'une cellule."""

    cell_id: int
    releve_id: int
    mm_par_an: float


def _lire_document(path=None) -> dict:
    chemin = pathlib.Path(path) if path is not None else _CHEMIN_RELEVES
    return json.loads(chemin.read_text(encoding="utf-8"))


def _refuser_texte_vide(valeur, releve_id, champ: str) -> str:
    if not isinstance(valeur, str) or not valeur.strip():
        raise ReleveDePluieInvalide(
            f"relevé {releve_id!r}, champ {champ} : texte absent ou vide"
        )
    return valeur


def _refuser_nombre_invalide(valeur, releve_id, champ: str):
    if (
        isinstance(valeur, bool)
        or not isinstance(valeur, (int, float))
        or not math.isfinite(valeur)
    ):
        raise ReleveDePluieInvalide(
            f"relevé {releve_id!r}, champ {champ} : nombre fini attendu"
        )
    return valeur


def charger_releves(path=None) -> list:
    """Lit et valide la table documentée des relevés de pluie."""
    document = _lire_document(path)
    climat = document.get(_CLE_CLIMAT_DE_1400)
    if not isinstance(climat, str) or not climat.strip():
        raise ReleveDePluieInvalide(
            f"champ {_CLE_CLIMAT_DE_1400} : déclaration absente ou vide"
        )
    if document.get(_CLE_UNITE) != _UNITE_ATTENDUE:
        raise ReleveDePluieInvalide(
            f"champ {_CLE_UNITE} : {_UNITE_ATTENDUE!r} attendu"
        )

    bruts = document.get(_CLE_RELEVES)
    if not isinstance(bruts, list) or not bruts:
        raise ReleveDePluieInvalide(
            f"champ {_CLE_RELEVES} : la table de relevés est vide"
        )

    vus = set()
    releves = []
    for brut in bruts:
        releve_id = brut.get(_CLE_IDENTIFIANT)
        if isinstance(releve_id, bool) or not isinstance(releve_id, int):
            raise ReleveDePluieInvalide(
                f"relevé {releve_id!r}, champ {_CLE_IDENTIFIANT} : entier attendu"
            )
        if releve_id in vus:
            raise ReleveDePluieInvalide(
                f"relevé {releve_id}, champ {_CLE_IDENTIFIANT} : identifiant dupliqué"
            )
        vus.add(releve_id)

        nom = _refuser_texte_vide(brut.get(_CLE_NOM), releve_id, _CLE_NOM)
        source = _refuser_texte_vide(
            brut.get(_CLE_SOURCE), releve_id, _CLE_SOURCE
        )
        latitude = _refuser_nombre_invalide(
            brut.get(_CLE_LATITUDE), releve_id, _CLE_LATITUDE
        )
        longitude = _refuser_nombre_invalide(
            brut.get(_CLE_LONGITUDE), releve_id, _CLE_LONGITUDE
        )
        pluie = _refuser_nombre_invalide(
            brut.get(_CLE_PLUIE), releve_id, _CLE_PLUIE
        )
        if pluie < 0:
            raise ReleveDePluieInvalide(
                f"relevé {releve_id}, champ {_CLE_PLUIE} : valeur négative"
            )
        releves.append(
            ReleveDePluie(
                id=releve_id,
                nom=nom,
                lat=latitude,
                lon=longitude,
                mm_par_an=pluie,
                source=source,
            )
        )
    return releves


def charger_latitude_moyenne_pluie(path=None) -> float:
    """Lit le paramètre de projection de la table de pluie elle-même."""
    return _lire_document(path)[_CLE_PROJECTION][_CLE_LATITUDE_MOYENNE]


def pluie_par_cellule(positions, releves, latitude_moyenne) -> tuple:
    """Dérive une valeur par cellule, sans modifier aucune entrée."""
    if not releves:
        raise ReleveDePluieInvalide(
            "Aucun relevé de pluie fourni : la vue refuse de deviner."
        )
    appartenance = derive_appartenance(positions, releves, latitude_moyenne)
    valeurs = {releve.id: releve.mm_par_an for releve in releves}
    return tuple(
        PluieDeCellule(
            cell_id=cell_id,
            releve_id=appartenance[cell_id],
            mm_par_an=valeurs[appartenance[cell_id]],
        )
        for cell_id in sorted(appartenance)
    )


def pluie_depuis_monde(
    world, positions=None, releves=None, latitude_moyenne=None
) -> tuple:
    """Restreint les positions au monde chargé et en dérive la pluie."""
    if positions is None:
        positions = charger_positions()
    if releves is None:
        releves = charger_releves()
    if latitude_moyenne is None:
        latitude_moyenne = charger_latitude_moyenne_pluie()
    retenues = positions_du_monde(world, positions)
    return pluie_par_cellule(retenues, releves, latitude_moyenne)


def pluie_de_cellule(cell_id: int, pluies):
    """Rend les millimètres de la cellule, ou ``None`` si elle est absente."""
    for pluie in pluies:
        if pluie.cell_id == cell_id:
            return pluie.mm_par_an
    return None


def releves_sans_cellule(pluies, releves) -> tuple:
    """Rend, triés, les identifiants des relevés que la vue n'a pas retenus."""
    retenus = {pluie.releve_id for pluie in pluies}
    return tuple(sorted(releve.id for releve in releves if releve.id not in retenus))
