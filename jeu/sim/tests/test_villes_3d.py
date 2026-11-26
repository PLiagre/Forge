"""La donnée des villes bâties en 3D : son chargeur, ses scènes, son accord avec Unity."""

import json
import pathlib
import re

import pytest

from sim.villes_3d import (
    VilleEn3DInvalide,
    VillesEn3D,
    charger_villes_3d,
    raison_sans_ville,
)

_RACINE = pathlib.Path(__file__).parents[3]
_DONNEE = _RACINE / "jeu" / "data" / "villes-3d.json"
_CAPITALE_CS = _RACINE / "3d" / "unity" / "Assets" / "ForgeLocal3D" / "Pont" / "CapitaleDuJoueur.cs"
_SCENE_INEXISTANTE = "3d/unity/Assets/ForgeLocal3D/Desert/Scenes/Inexistante.unity"


def _verifier_scenes(villes: VillesEn3D, racine: pathlib.Path) -> None:
    assert villes.capitales, "aucune ville déclarée"
    for ville in villes.capitales:
        assert (racine / ville.scene).is_file(), f"{ville.maison} : scène absente ({ville.scene})"


def _copie_alteree(tmp_path, alterer) -> pathlib.Path:
    document = json.loads(_DONNEE.read_text(encoding="utf-8"))
    alterer(document)
    chemin = tmp_path / "villes-3d.json"
    chemin.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return chemin


def test_les_scenes_existent():
    villes = charger_villes_3d()
    assert len(villes.capitales) >= 1
    _verifier_scenes(villes, _RACINE)


def test_contre_epreuve_une_scene_inexistante_est_refusee(tmp_path):
    chemin = _copie_alteree(
        tmp_path,
        lambda d: d["villes"].append({"maison": "seigneurie-1", "scene": _SCENE_INEXISTANTE}),
    )
    villes = charger_villes_3d(chemin)
    assert len(villes.capitales) == len(charger_villes_3d().capitales) + 1
    with pytest.raises(AssertionError):
        _verifier_scenes(villes, _RACINE)


def test_memes_maisons_qu_unity():
    source = _CAPITALE_CS.read_text(encoding="utf-8")
    debut = source.index("class TerresAvecKit")
    bloc = source[debut:source.index("enum ", debut)]
    couples = dict(re.findall(r'\["([^"]+)"\]\s*=\s*"([^"]+)"', bloc))
    assert couples, "aucun couple lu dans TerresAvecKit"
    villes = charger_villes_3d()
    assert set(couples) == {v.maison for v in villes.capitales}
    for ville in villes.capitales:
        assert couples[ville.maison] == pathlib.Path(ville.scene).stem


def _vider_villes(d):
    d["villes"] = []


def _retirer_villes(d):
    del d["villes"]


def _maison_vide(d):
    d["villes"][0]["maison"] = "  "


def _scene_vide(d):
    d["villes"][0]["scene"] = ""


def _doublon(d):
    d["villes"].append(dict(d["villes"][0]))


def _raison_sans_siege(d):
    d["raison_sans_ville"] = "aucune ville bâtie, sauf {baties}"


def _raison_cle_inconnue(d):
    d["raison_sans_ville"] = "la ville de {siege} et {ville} ; seule {baties} l'est"


def _raison_absente(d):
    del d["raison_sans_ville"]


def _raison_designee_absente(d):
    del d["raison_sans_ville_designee"]


def _raison_designee_sans_siege(d):
    d["raison_sans_ville_designee"] = "aucun siège bâti, sauf {baties}"


def _entree_pas_un_objet(d):
    d["villes"].append("seigneurie-1")


@pytest.mark.parametrize(
    "alterer, fragment",
    [
        (_vider_villes, "champ villes : liste absente ou vide"),
        (_retirer_villes, "champ villes : liste absente ou vide"),
        (_entree_pas_un_objet, "objet attendu"),
        (_maison_vide, "champ maison : texte absent ou vide"),
        (_scene_vide, "ville seigneurie-6, champ scene : texte absent ou vide"),
        (_doublon, "ville seigneurie-6, champ maison : maison dupliquée"),
        (_raison_absente, "champ raison_sans_ville : texte absent ou vide"),
        (_raison_sans_siege, "{siege}"),
        (_raison_cle_inconnue, "champ raison_sans_ville"),
        (_raison_designee_absente, "champ raison_sans_ville_designee : texte absent ou vide"),
        (_raison_designee_sans_siege, "champ raison_sans_ville_designee : {siege}"),
    ],
)
def test_le_chargeur_refuse(tmp_path, alterer, fragment):
    chemin = _copie_alteree(tmp_path, alterer)
    with pytest.raises(VilleEn3DInvalide) as erreur:
        charger_villes_3d(chemin)
    assert fragment in str(erreur.value)


def test_la_raison_se_formate():
    texte = raison_sans_ville(charger_villes_3d(), "Bar-le-Duc", "Biskra")
    assert "Bar-le-Duc" in texte
    assert "Biskra" in texte
    # Un siège désigné n'est jamais appelé ville.
    designe = raison_sans_ville(charger_villes_3d(), "la campagne de Borgund, au nord-ouest", "Biskra", designe=True)
    assert "la campagne de Borgund, au nord-ouest" in designe and "Biskra" in designe and "ville" not in designe
