"""
Ce qui tient la carte de statistique.

Ce fichier protège trois choses, et aucune ne demande de GPU :

  - **invariant de lecture** : une absence n'est jamais peinte comme un zéro,
    et une grandeur qu'aucune cellule ne porte échoue au lieu de rendre une
    carte uniforme ;
  - **règle visible** : le dégradé est séquentiel — une seule teinte, du clair
    au foncé, clarté strictement décroissante ;
  - **le refus** : une lecture inconnue, une photographie vide, un rendu sans
    GPU disent lequel des trois a manqué.

Le rendu forge3d lui-même n'est pas testé ici : il demande un adaptateur. Ce
qui est testé, c'est que son absence est un refus propre et pas une image
fausse.
"""

import json
import math

import numpy as np
import pytest

from vues.relief.lectures import (
    ECHELLES,
    LECTURES,
    RAMPE,
    Lecture,
    LectureErreur,
    couleurs_de,
    lecture_de,
    normaliser,
)
from vues.relief.raster import RasterErreur
from vues.relief.statistique import (
    altitudes_de,
    carte_de_statistique,
    plan,
    plan_avec_legende,
    resume,
)


def _cellule(cell_id: int, x: float, **champs) -> dict:
    """Une cellule carrée d'un degré, avec ce qu'on veut lui faire porter."""
    base = {
        "cell_id": cell_id,
        "area_km2": 100.0,
        "relief": "plaine",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[x, 0.0], [x + 1.0, 0.0], [x + 1.0, 1.0], [x, 1.0], [x, 0.0]]],
        },
    }
    base.update(champs)
    return base


def _document(cellules: list[dict], tick: int = 0, seed: int = 0) -> dict:
    return {"cells": cellules, "tick": tick, "seed": seed}


# --- le dégradé -------------------------------------------------------------

def _clarte_oklab(hexa: str) -> float:
    def canal(v):
        v /= 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4

    h = hexa.lstrip("#")
    r, g, b = (canal(int(h[i:i + 2], 16)) for i in (0, 2, 4))
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s


def test_le_degrade_est_sequentiel_clair_vers_fonce():
    """
    Un dégradé séquentiel se lit à la clarté, jamais à la teinte.

    Ce test rougirait si quelqu'un remplaçait la rampe par un arc-en-ciel, ou
    en réordonnait les pas : deux fautes qui rendent une carte jolie et
    illisible, et qu'aucun autre contrôle ne verrait.
    """
    clartes = [_clarte_oklab(pas) for pas in RAMPE]
    for precedent, suivant in zip(clartes, clartes[1:]):
        assert suivant < precedent, (
            f"clarté non décroissante : {clartes} — le dégradé n'ordonne plus rien."
        )
    amplitude = clartes[0] - clartes[-1]
    assert amplitude >= 0.45, (
        f"amplitude de clarté {amplitude:.3f} < 0,45 : les deux bouts du "
        "dégradé se ressemblent trop pour qu'on les distingue."
    )


def test_les_couleurs_suivent_la_valeur():
    """0 rend le pas le plus clair, 1 le plus foncé, et l'ordre tient entre."""
    couleurs = couleurs_de(np.array([0.0, 0.5, 1.0]))
    clartes = [_clarte_oklab("#%02x%02x%02x" % tuple(c)) for c in couleurs]
    assert clartes[0] > clartes[1] > clartes[2]


# --- absence contre zéro ----------------------------------------------------

def test_une_absence_n_est_pas_un_zero():
    """
    Règle 8, vue de la carte. Une cellule sans la grandeur est hachurée en
    gris ; une cellule qui porte zéro est peinte au clair du dégradé. Les
    confondre ferait passer un trou de données pour une mesure.
    """
    document = _document([
        _cellule(1, 0.0, population=0),
        _cellule(2, 2.0),                 # aucune clé population
        _cellule(3, 4.0, population=100),
    ])
    carte = carte_de_statistique(document, lecture="population", largeur=64)

    assert carte.cellules_mesurees == 2, "la cellule sans population est comptée mesurée"
    assert carte.cellules - carte.cellules_mesurees == 1

    image = plan(carte)
    non_mesuree = carte.masque_terre & ~carte.mesuree
    assert bool(non_mesuree.any()), "aucun pixel non mesuré : l'échantillon ne prouve rien"

    # Le gris de « non mesuré » a une chroma quasi nulle ; un pas du dégradé, non.
    pixels = image[non_mesuree][:, :3].astype(float)
    ecart_canaux = pixels.max(axis=1) - pixels.min(axis=1)
    assert float(ecart_canaux.mean()) < 20.0, (
        "les pixels non mesurés sont colorés : ils se lisent comme une valeur."
    )


def test_une_grandeur_que_personne_ne_porte_echoue():
    """
    Règle 6 : un échantillon vide échoue, il ne rend pas une carte uniforme.

    C'est ce qui arrive aujourd'hui à la lecture « bourg » : le snapshot ne la
    porte pas encore. Elle refuse en le disant, et elle deviendra verte toute
    seule le jour où le champ arrivera.
    """
    document = _document([_cellule(1, 0.0, population=10)])
    with pytest.raises(LectureErreur, match="échantillon vide"):
        carte_de_statistique(document, lecture="bourg", largeur=32)


def test_la_lecture_bourg_est_declaree_mais_pas_inventee():
    """Elle existe au catalogue — sinon personne ne saurait qu'elle manque."""
    assert "bourg" in LECTURES
    assert LECTURES["bourg"].valeur({"population": 10}) is None


# --- les refus --------------------------------------------------------------

def test_une_lecture_inconnue_dit_lesquelles_existent():
    with pytest.raises(LectureErreur, match="connues"):
        lecture_de("prosperite")


def test_une_photographie_sans_cellule_echoue():
    with pytest.raises(RasterErreur, match="échantillon vide"):
        carte_de_statistique(_document([]), lecture="population", largeur=32)


# --- les échelles -----------------------------------------------------------

def test_l_echelle_par_rang_emploie_tout_le_degrade():
    """
    La raison d'être de l'échelle par rang, et sa preuve.

    Avec des valeurs très étalées, linéaire et logarithme tassent toutes les
    cellules d'un même côté du dégradé : la carte devient d'une seule couleur.
    Le rang garantit que les deux bouts sont atteints.
    """
    valeurs = [5.0, 40.0, 60.0, 80.0, 100.0, 268922.0]
    lecture = Lecture("essai", "Essai", "u", "quantile", lambda c: c["v"])
    t, _mesurees, _bornes = normaliser(valeurs, lecture)
    assert math.isclose(float(t.min()), 0.0, abs_tol=1e-6)
    assert math.isclose(float(t.max()), 1.0, abs_tol=1e-6)

    lineaire = Lecture("essai", "Essai", "u", "lineaire", lambda c: c["v"])
    t_lin, _m, _b = normaliser(valeurs, lineaire)
    tassees = int((t_lin < 0.01).sum())
    assert tassees >= len(valeurs) - 1, (
        "l'échantillon ne montre pas le tassement que le rang existe pour corriger"
    )


def test_toutes_les_echelles_des_lectures_existent():
    for lecture in LECTURES.values():
        assert lecture.echelle in ECHELLES, (
            f"« {lecture.cle} » demande une échelle {lecture.echelle!r} qui n'existe pas"
        )


# --- la grandeur devient le relief ------------------------------------------

def test_la_grandeur_devient_le_terrain():
    """
    Ce qui fait la carte de statistique en 3D : la valeur est la hauteur.

    La mer et les cellules non mesurées restent à zéro — elles ne portent
    aucune valeur, donc elles ne s'élèvent pas.
    """
    document = _document([
        _cellule(1, 0.0, population=1),
        _cellule(2, 2.0, population=1000),
        _cellule(3, 4.0),
    ])
    carte = carte_de_statistique(document, lecture="population", largeur=96)
    altitudes = altitudes_de(carte)

    assert float(altitudes[~carte.masque_terre].max(initial=0.0)) == 0.0, "la mer s'élève"
    non_mesuree = carte.masque_terre & ~carte.mesuree
    assert float(altitudes[non_mesuree].max(initial=0.0)) == 0.0, "le non-mesuré s'élève"
    assert float(altitudes[carte.mesuree].max()) > 0.0, "rien ne s'élève : il n'y a pas de relief"


# --- le compte rendu --------------------------------------------------------

def test_le_compte_rendu_dit_ce_qui_manque():
    """Une carte doit dire combien de cellules elle n'a pas pu mesurer."""
    document = _document([
        _cellule(1, 0.0, population=10),
        _cellule(2, 2.0),
    ], tick=7, seed=3)
    carte = carte_de_statistique(document, lecture="population", largeur=64)
    r = resume(carte)
    assert r["cellules"] == 2
    assert r["cellules_mesurees"] == 1
    assert r["cellules_non_mesurees"] == 1
    assert r["tick"] == 7 and r["seed"] == 3


def test_la_legende_ajoute_une_bande_au_dessus_de_la_carte():
    document = _document([_cellule(1, 0.0, population=10), _cellule(2, 2.0, population=20)])
    carte = carte_de_statistique(document, lecture="population", largeur=120)
    nu = plan(carte)
    habille = plan_avec_legende(carte)
    assert habille.shape[0] > nu.shape[0], "la légende n'a rien ajouté"
    assert habille.shape[1] == nu.shape[1]
