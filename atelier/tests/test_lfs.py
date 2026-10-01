"""Les fichiers LFS d'un lot, rendus lisibles sans git-lfs."""

from __future__ import annotations

from atelier import lfs

OID = "ab" * 32
POINTEUR = f"version https://git-lfs.github.com/spec/v1\noid sha256:{OID}\nsize 3\n".encode()


def test_un_pointeur_se_reconnait_et_un_vrai_fichier_non():
    assert lfs.pointeur(POINTEUR) == (OID, 3)
    assert lfs.pointeur(POINTEUR.replace(b"\n", b"\r\n")) == (OID, 3)
    assert lfs.pointeur(b"\x89PNG\r\n\x1a\n") is None
    assert lfs.pointeur(POINTEUR.replace(b"sha256:", b"sha1:")) is None


def test_seuls_les_pointeurs_se_telechargent_et_un_echec_se_dit(tmp_path):
    (tmp_path / "a.png").write_bytes(POINTEUR)
    (tmp_path / "b.png").write_bytes(b"\x89PNG vrai")
    (tmp_path / "c.png").write_bytes(POINTEUR.replace(OID.encode(), b"cd" * 32))

    def telechargeur(depot, oid, taille):
        if oid != OID:
            raise RuntimeError("absent du serveur")
        return b"PNG"

    lisibles, illisibles = lfs.rendre_lisibles(tmp_path, ["a.png", "b.png", "c.png", "parti.png"], "moi/essai",
                                               telechargeur=telechargeur)
    assert lisibles == ["a.png"]
    assert illisibles == ["c.png (absent du serveur)"]
    assert (tmp_path / ".atelier" / "lfs" / "a.png").read_bytes() == b"PNG"
    assert (tmp_path / "a.png").read_bytes() == POINTEUR  # le chantier n'est pas touché
