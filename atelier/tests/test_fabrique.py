"""Tests de l'usine d'assets locale `atelier/fabrique/` (zéro API).

Chaque contrôle est prouvé au rouge avant d'être vérifié au vert : planche
d'icônes découpée, alpha strict 0/255 (contre-épreuve sur alpha 254), raccord
sans couture + jeu PBR local, manifeste et CLI.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
import pytest

from atelier.fabrique import CHEMIN_MANIFESTE, enregistrer_asset, ids_existants, machine_pour, procede_pour
from atelier.fabrique.__main__ import main as cli_main
from atelier.fabrique.controle import controler_image, controler_manifeste
from atelier.fabrique.icones import decouper_planche, detourer_fichier, lire_grille, normaliser_alpha
from atelier.fabrique.textures import erreur_couture, generer_pbr, rendre_raccordable


def _planche_3x3(chemin: Path, taille_case: int = 120) -> Path:
    """Fabrique une planche 3x3 sur fond magenta avec filets de grille et 9 motifs distincts."""
    w = h = taille_case * 3
    im = Image.new("RGB", (w, h), (255, 0, 255))
    dessin = ImageDraw.Draw(im)
    couleurs = [
        (190, 145, 70), (120, 130, 140), (140, 90, 50),
        (165, 160, 150), (210, 175, 65), (220, 210, 190),
        (230, 230, 225), (150, 40, 55), (110, 115, 120),
    ]
    for i, col in enumerate(couleurs):
        r, c = divmod(i, 3)
        x0, y0 = c * taille_case, r * taille_case
        dessin.rectangle([x0, y0, x0 + taille_case - 1, y0 + taille_case - 1], outline=(40, 40, 40), width=2)
        dessin.ellipse([x0 + 22, y0 + 22, x0 + taille_case - 22, y0 + taille_case - 22], fill=col)
    im.save(chemin, format="PNG")
    return chemin


# --------------------------------------------------------------- procédés
def test_chaque_type_a_son_procede_et_sa_file():
    assert machine_pour("planche_icones") == "asset"
    assert machine_pour("texture_pbr") == "asset"
    assert machine_pour("prop_3d") == "pc"
    assert "3x3" in procede_pour("planche_icones").consigne()
    with pytest.raises(ValueError, match="type d'asset inconnu"):
        procede_pour("video_4k")


# -------------------------------------------------------- planches & alpha
def test_decouper_planche_produit_des_icones_carrees_a_alpha_strict(tmp_path):
    brut = _planche_3x3(tmp_path / "planche.png")
    noms = ["ble", "fer", "bois", "pierre", "or", "laine", "sel", "vin", "outils"]
    sorties = decouper_planche(brut, tmp_path / "icones", grille=lire_grille("3x3"), noms=noms, taille=128)
    assert len(sorties) == 9
    for chemin in sorties:
        defauts = controler_image(chemin, asset_id="icones-ressources", dimensions=(128, 128), transparent=True)
        assert not defauts, f"{chemin.name} : {defauts}"
        with Image.open(chemin) as im:
            alpha = np.asarray(im, dtype=np.uint8)[:, :, 3]
            assert int(alpha.min()) == 0 and int(alpha.max()) == 255


def test_le_controle_attrape_le_defaut_alpha_254_et_detourer_le_corrige(tmp_path):
    """Contre-épreuve du défaut réel de docs/direction-artistique : alpha plafonné à 254."""
    arr = np.zeros((128, 128, 4), dtype=np.uint8)
    arr[24:104, 24:104, :3] = (180, 60, 50)
    arr[24:104, 24:104, 3] = 254  # translucidité résiduelle
    defectueux = tmp_path / "blason_254.png"
    Image.fromarray(arr, mode="RGBA").save(defectueux, format="PNG")

    defauts = controler_image(defectueux, asset_id="blason-val", dimensions=(128, 128), transparent=True)
    assert any("254 < 255" in d.raison for d in defauts), "le défaut alpha 254 doit faire échouer le contrôle"

    corrige = detourer_fichier(defectueux, tmp_path / "blason_ok.png", taille=128)
    assert not controler_image(corrige, asset_id="blason-val", dimensions=(128, 128), transparent=True)


def test_normaliser_alpha_preserve_un_interieur_de_meme_couleur_que_le_fond():
    """Le remplissage depuis le bord ne perce pas un anneau fermé."""
    arr = np.zeros((64, 64, 3), dtype=np.uint8)  # fond noir
    arr[12:52, 12:52] = (200, 170, 90)           # anneau doré fermé
    arr[24:40, 24:40] = (0, 0, 0)                # trou intérieur noir protégé par l'anneau
    propre = normaliser_alpha(Image.fromarray(arr, mode="RGB"), mode="fond", seuil=20.0)
    alpha = np.asarray(propre, dtype=np.uint8)[:, :, 3]
    assert int(alpha[0, 0]) == 0 and int(alpha[32, 32]) == 255


# ----------------------------------------------------------- textures PBR
def test_rendre_raccordable_supprime_une_couture_et_generer_pbr_produit_les_cinq_cartes(tmp_path):
    # Gradient prononcé : forte discontinuité entre gauche et droite avant raccord.
    x = np.linspace(20, 230, 128, dtype=np.float32)
    y = np.linspace(30, 210, 128, dtype=np.float32)
    grille = np.stack([
        np.broadcast_to(x[None, :], (128, 128)),
        np.broadcast_to(y[:, None], (128, 128)),
        np.full((128, 128), 110.0, dtype=np.float32),
    ], axis=2).astype(np.uint8)
    source = tmp_path / "pierre_brut.png"
    im_source = Image.fromarray(grille, mode="RGB")
    im_source.save(source, format="PNG")

    couture_avant = erreur_couture(im_source)
    assert couture_avant > 0.20
    im_racc = rendre_raccordable(im_source)
    couture_apres = erreur_couture(im_racc)
    assert couture_apres < 0.03, f"couture trop forte après raccord : {couture_apres}"

    cartes = generer_pbr(source, tmp_path / "pbr", nom="pierre", taille=128, raccorder=True)
    assert set(cartes) == {"albedo", "height", "normal", "roughness", "ao"}
    for chemin in cartes.values():
        assert chemin.is_file()
    with Image.open(cartes["normal"]) as norm:
        bleu = np.asarray(norm, dtype=np.uint8)[:, :, 2]
        assert float(bleu.mean()) > 180.0, "une normal map tangent-space pointe vers +Z (bleu élevé)"
    with Image.open(cartes["roughness"]) as rug:
        val = np.asarray(rug, dtype=np.uint8) / 255.0
        assert float(val.min()) >= 0.40 and float(val.max()) <= 0.94


# --------------------------------------------------- manifeste & contrôles
def test_controler_manifeste_refuse_les_fautes_et_accepte_un_asset_valide(tmp_path):
    # Absent non strict : vert ; strict : échoue (principe n° 8).
    assert not controler_manifeste(tmp_path)
    assert controler_manifeste(tmp_path, exiger_non_vide=True)

    # Jeu PBR incomplet → refusé.
    brut = _planche_3x3(tmp_path / "planche.png")
    pbr_dir = tmp_path / "assets" / "pbr"
    cartes = generer_pbr(brut, pbr_dir, nom="mur", taille=128, raccorder=True)
    enregistrer_asset(
        tmp_path / CHEMIN_MANIFESTE, asset_id="mur-pierre", type_asset="texture_pbr",
        fichiers=[str(cartes["albedo"].relative_to(tmp_path))], dimensions="128x128",
    )
    defauts = controler_manifeste(tmp_path, exiger_non_vide=True)
    assert any("cartes PBR manquantes" in d.raison for d in defauts)

    # Jeu PBR complet → vert.
    enregistrer_asset(
        tmp_path / CHEMIN_MANIFESTE, asset_id="mur-pierre", type_asset="texture_pbr",
        fichiers=[str(p.relative_to(tmp_path)) for p in cartes.values()], dimensions="128x128",
    )
    assert not controler_manifeste(tmp_path, exiger_non_vide=True)
    assert "mur-pierre" in ids_existants(tmp_path / CHEMIN_MANIFESTE)


def test_cli_fabrique_de_bout_en_bout(tmp_path):
    brut = _planche_3x3(tmp_path / "planche.png")
    out = tmp_path / "out" / "icones"
    assert cli_main(["decouper-planche", str(brut), "--grille", "3x3",
                     "--noms", "a,b,c,d,e,f,g,h,i", "--sortie", str(out), "--taille", "64"]) == 0
    manifeste = tmp_path / "assets" / "manifeste.json"
    fichiers = [f"out/icones/{n}.png" for n in "abcdefghi"]
    assert cli_main(["enregistrer", "--manifeste", str(manifeste), "--id", "icones-test",
                     "--type", "planche_icones", "--dimensions", "64x64", "--fichiers", *fichiers]) == 0
    assert cli_main(["controler", "--racine", str(tmp_path), "--manifeste", str(manifeste), "--strict"]) == 0
    assert cli_main(["procede", "texture_pbr"]) == 0
