import subprocess

from atelier import captures


def _commande(tmp_path, monkeypatch, **options):
    (tmp_path / "jeu").mkdir()
    vues = []

    def run(argv, **kw):
        vues.append(argv)
        return subprocess.CompletedProcess(argv, 1, "", "")

    monkeypatch.setattr(captures.subprocess, "run", run)
    assert captures.carte_du_monde(tmp_path, tmp_path / "sortie", **options) is None
    return vues[0]


def test_la_capture_choisit_une_terre_de_depart_pour_montrer_sa_fiche(tmp_path, monkeypatch):
    # #214 : la preuve du jalon 2 montre la fiche de la terre choisie au journal.
    argv = _commande(tmp_path, monkeypatch)
    assert argv[argv.index("--depart") + 1] == "1"


def test_une_capture_peut_se_passer_de_terre_de_depart(tmp_path, monkeypatch):
    assert "--depart" not in _commande(tmp_path, monkeypatch, depart=None)
