"""Ce qui tient la chronique.

Trois invariants, et rien d'autre :

1. la decoupe ne perd ni n'invente rien — `decor + image` rend la
   photographie de `sim/`, au bit pres ;
2. la liste des champs mobiles est **mesuree**, pas declaree ;
3. la planche refuse de deviner : relief inconnu, echantillon vide,
   marchandise absente.

Le determinisme est verifie ici aussi, parce qu'une chronique est ce
qu'on montre : deux deroulements de la meme graine qui differeraient
feraient mentir la capture d'ecran avant de faire mentir le moteur.
"""

from __future__ import annotations

import copy
import json
import random

import pytest

from vues.chronique.atlas import (
    AtlasError,
    _valeur_nourriture,
    echelles,
    lectures_par_image,
    lire_da,
    rendre,
)
from vues.chronique.capture import (
    CHAMPS_MOBILES,
    CaptureError,
    capturer,
    decouper,
    recomposer,
)
from sim.engine import tick
from sim.snapshot_export import build_snapshot_document
from sim.world import World

# Assez de ticks pour que production, commerce, consommation, faim et
# mortalite aient tous joue : une decoupe juste sur un monde immobile ne
# prouverait rien.
# Assez de ticks pour que la faim ait mordu quelque part.
#
# La sonde valait six ticks quand le monde amorçait plus de bouches que sa
# terre n'en nourrit : la dette alimentaire apparaissait tout de suite. Depuis
# que la population d'une cellule est dérivée de ce qu'elle produit, le monde
# part nourri, et `food_deficit_kg` comme `mortality_remainder` ne bougent plus
# avant la vingtaine de ticks. Mesuré sur la carte figée, graine 0 : les cinq
# champs bougent de 20 à une quarantaine de ticks ; au-delà la dette est
# remboursée et le champ se rassied.
#
# Six ticks feraient donc dire à ce test que la chronique découpe deux champs
# de trop — et la seule façon de le calmer serait de les retirer, ce qui
# perdrait la famine le jour où elle revient. On allonge la sonde ; on ne
# rétrécit pas la chronique.
TICKS_SONDE = 30


def _monde_avance(ticks: int, seed: int = 0) -> World:
    monde = World.charger(rng_seed=seed)
    rng = random.Random(seed)
    for numero in range(ticks):
        tick(monde, rng, numero)
    return monde


def test_la_decoupe_rend_la_photographie_au_bit_pres():
    """`decor + image` est la photographie. Sinon la chronique ment."""
    from vues.chronique.capture import _image_du_monde

    monde = World.charger(rng_seed=0)
    decor, image_zero = decouper(build_snapshot_document(monde, 0, 0))
    assert recomposer(decor, image_zero) == build_snapshot_document(monde, 0, 0)

    rng = random.Random(0)
    for numero in range(TICKS_SONDE):
        tick(monde, rng, numero)
    attendu = build_snapshot_document(monde, 0, TICKS_SONDE)
    obtenu = recomposer(decor, _image_du_monde(monde, TICKS_SONDE))
    assert obtenu == attendu


def test_les_champs_mobiles_sont_mesures_et_pas_declares():
    """La liste des champs mobiles derive du moteur, jamais d'une intention.

    On joue des ticks et on regarde quels champs de la photographie ont
    bouge. Le jour ou le moteur fera bouger un champ de plus — ou cessera
    d'en faire bouger un — ce test rougit, et personne ne peut le calmer
    sans regarder le moteur (regle 7 : la presence n'est pas la fonction).
    """
    monde = World.charger(rng_seed=0)
    avant = build_snapshot_document(monde, 0, 0)
    rng = random.Random(0)
    for numero in range(TICKS_SONDE):
        tick(monde, rng, numero)
    apres = build_snapshot_document(monde, 0, TICKS_SONDE)

    bouges = {
        champ
        for cellule_avant, cellule_apres in zip(avant["cells"], apres["cells"])
        for champ in cellule_avant
        if cellule_avant[champ] != cellule_apres[champ]
    }
    assert bouges, "aucun champ n'a bouge en six ticks : le monde est mort"
    assert bouges == set(CHAMPS_MOBILES), (
        f"le moteur fait bouger {sorted(bouges)}, la chronique decoupe "
        f"{sorted(CHAMPS_MOBILES)}"
    )


def test_une_colonne_de_mauvaise_longueur_est_refusee():
    """Une recomposition impossible se refuse, elle ne se complete pas."""
    monde = World.charger(rng_seed=0)
    decor, image = decouper(build_snapshot_document(monde, 0, 0))
    mutilee = copy.deepcopy(image)
    mutilee["colonnes"]["population"] = mutilee["colonnes"]["population"][:-1]
    with pytest.raises(CaptureError):
        recomposer(decor, mutilee)


def test_deux_chroniques_de_la_meme_graine_sont_identiques():
    """Meme graine, meme chronique — sinon la planche n'est pas une preuve."""
    premiere = capturer(TICKS_SONDE, seed=0, pas=3)
    seconde = capturer(TICKS_SONDE, seed=0, pas=3)
    assert json.dumps(premiere, sort_keys=True) == json.dumps(
        seconde, sort_keys=True
    )


def test_la_capture_refuse_un_pas_nul():
    with pytest.raises(CaptureError):
        capturer(4, seed=0, pas=0)


def test_une_marchandise_absente_se_lit_absente_et_pas_zero():
    """Un panier sans nourriture n'est pas un panier a zero (regle 8)."""
    assert _valeur_nourriture({}) is None
    assert _valeur_nourriture({"minerai": 12.0}) is None
    assert _valeur_nourriture({"nourriture": 0.0}) == 0.0


def _image_plate(**colonnes) -> dict:
    """Une image de test dont chaque lecture vaut ce qu'on lui donne."""
    base = {"population": [0, 0], "nourriture": [0, 0], "faim": [0, 0], "dette": [0, 0]}
    base.update(colonnes)
    base.update(
        {
            "tick": 0,
            "jour": 0,
            "totaux": {"population": 0, "nourriture": 0, "disette": 0, "dette": 0},
        }
    )
    return base


def test_une_lecture_sans_valeur_positive_se_declare_au_lieu_de_valoir_zero():
    """Une lecture jamais mesuree rend `None`, jamais 0 (regles 8 et 10)."""
    mesures = echelles([_image_plate(population=[10, 4])])
    assert mesures["population"] == 10
    assert mesures["dette"] is None
    assert mesures["faim"] is None


def test_une_chronique_sans_aucune_valeur_echoue():
    """Un echantillon entierement vide echoue ; il ne passe pas (regle 6)."""
    with pytest.raises(AtlasError):
        echelles([_image_plate()])


def test_un_relief_inconnu_de_la_direction_artistique_est_refuse():
    """La planche ne devine pas une teinte pour un relief qu'elle ne connait pas."""
    chronique = capturer(1, seed=0, pas=1)
    chronique["decor"]["cellules"][0]["relief"] = "toundra"
    with pytest.raises(AtlasError):
        rendre(chronique, lire_da())


def test_la_planche_se_suffit_a_elle_meme():
    """Une page sans reseau ne demande rien a personne.

    Le controle derive : il compte les schemes d'URL absolus dans la page
    rendue, il ne cherche pas un nom de domaine connu d'avance.
    """
    import re

    chronique = capturer(2, seed=0, pas=2)
    page = rendre(chronique, lire_da(), sans_reseau=True)
    liens = re.findall(r"https?://[^\"'\\s)]+", page)
    assert liens == [], f"la page appelle l'exterieur : {liens[:3]}"
    assert "<svg" in page and 'id="lavis"' in page


def test_la_bobine_refuse_une_lecture_qui_n_existe_pas():
    """Une option ignoree en silence est une option qui ment (regle 10).

    « disette » est l'intitule de l'onglet ; la lecture s'appelle « faim ».
    La bobine a d'abord accepte le premier et filmé le second sans un mot.
    Le nom refuse est verifie AVANT qu'on cherche le navigateur : une
    machine sans Chromium doit quand meme rougir sur le bon motif.
    """
    from vues.chronique.bobine import BobineError, filmer
    from vues.chronique.atlas import LECTURES
    from pathlib import Path as _Path

    with pytest.raises(BobineError) as refus:
        filmer(_Path("/inexistant.html"), _Path("/tmp/inexistant.webm"), 1,
               lecture="disette")
    assert "disette" in str(refus.value)
    for nom in LECTURES:
        assert nom in str(refus.value)


def test_les_totaux_derivent_des_colonnes():
    """Les totaux de la planche se recalculent depuis les colonnes lues.

    La reference est DERIVEE de la chronique elle-meme (regle 2) : aucun
    nombre attendu n'est ecrit ici.
    """
    chronique = capturer(TICKS_SONDE, seed=0, pas=2)
    for image, brute in zip(lectures_par_image(chronique), chronique["images"]):
        assert image["totaux"]["population"] == sum(brute["colonnes"]["population"])
        assert image["totaux"]["disette"] == sum(
            1 for v in brute["colonnes"]["hunger_ticks"] if v is not None and v > 0
        )
