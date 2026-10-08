"""Le zoom du journal : la terre choisie, au centre de son cadre."""

from __future__ import annotations

import pytest

from atelier import captures

Image = pytest.importorskip("PIL.Image")


def _carte(tmp_path, terre=None):
    image = Image.new("RGB", (400, 300), (20, 60, 200))
    if terre:
        x, y = terre
        for dx in range(-5, 6):
            image.putpixel((x + dx, y - 5), captures.LISERE_DE_LA_TERRE)
            image.putpixel((x + dx, y + 5), captures.LISERE_DE_LA_TERRE)
    chemin = tmp_path / "carte.png"
    image.save(chemin)
    return chemin


def test_le_zoom_se_centre_sur_la_terre(tmp_path):
    zoom = captures.zoom_sur_la_terre(_carte(tmp_path, (300, 100)), tmp_path / "zoom.png", largeur=100, hauteur=80)
    image = Image.open(zoom).convert("RGB")
    assert image.size == (100, 80)
    rouges = [(x, y) for x in range(100) for y in range(80) if image.getpixel((x, y)) == captures.LISERE_DE_LA_TERRE]
    assert rouges and {x for x, _ in rouges} == set(range(45, 56)) and {y for _, y in rouges} == {35, 45}


def test_le_zoom_reste_dans_la_carte(tmp_path):
    zoom = captures.zoom_sur_la_terre(_carte(tmp_path, (390, 290)), tmp_path / "zoom.png", largeur=100, hauteur=80)
    image = Image.open(zoom).convert("RGB")
    assert image.size == (100, 80) and image.getpixel((90, 75)) == captures.LISERE_DE_LA_TERRE


def test_sans_terre_choisie_pas_de_zoom(tmp_path):
    assert captures.zoom_sur_la_terre(_carte(tmp_path), tmp_path / "zoom.png") is None
    assert not (tmp_path / "zoom.png").exists()
