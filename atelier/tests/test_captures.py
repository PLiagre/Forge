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
    # La preuve montre la fiche de la terre choisie au journal.
    argv = _commande(tmp_path, monkeypatch)
    assert argv[argv.index("--depart") + 1] == "1"


def test_une_capture_peut_se_passer_de_terre_de_depart(tmp_path, monkeypatch):
    assert "--depart" not in _commande(tmp_path, monkeypatch, depart=None)


# ------------------------------------------------- les images pour le relecteur
def _cite(*adresses):
    return {"body": "\n\n".join(f"📷 ![capture]({a})" for a in adresses)}


JOURNAL = "https://raw.githubusercontent.com/moi/essai/journal"


def test_les_images_du_lot_se_lisent_dans_les_commentaires_de_sa_pr():
    commentaires = [_cite(f"{JOURNAL}/captures/2026-11-15/lot-10-aaa-carte.png"), {"body": "sans image"},
                    _cite(f"{JOURNAL}/captures/2026-11-16/lot-10-bbb-guerre.png", f"{JOURNAL}/captures/2026-11-16/vue.jpg")]
    assert captures.du_lot(commentaires, "moi/essai") == [
        "captures/2026-11-15/lot-10-aaa-carte.png", "captures/2026-11-16/lot-10-bbb-guerre.png",
        "captures/2026-11-16/vue.jpg"]


def test_seules_comptent_les_images_de_la_branche_journal_de_ce_depot():
    ailleurs = _cite("https://raw.githubusercontent.com/autre/depot/journal/captures/x.png",
                     "https://raw.githubusercontent.com/moi/essai/master/captures/x.png",
                     f"{JOURNAL}/captures/../../secret.png", f"{JOURNAL}/README.md")
    assert captures.du_lot([ailleurs], "moi/essai") == []


def test_une_image_republiee_ne_compte_qu_a_sa_derniere_citation_et_les_plus_recentes_restent():
    republiee = [_cite(f"{JOURNAL}/captures/2026-11-15/vue.png"), _cite(f"{JOURNAL}/captures/2026-11-15/autre.png"),
                 _cite(f"{JOURNAL}/captures/2026-11-16/vue.png")]
    assert captures.du_lot(republiee, "moi/essai") == ["captures/2026-11-15/autre.png", "captures/2026-11-16/vue.png"]
    beaucoup = [_cite(f"{JOURNAL}/captures/j/image-{k:02d}.png") for k in range(captures.IMAGES_MAX + 3)]
    gardees = captures.du_lot(beaucoup, "moi/essai")
    assert len(gardees) == captures.IMAGES_MAX and gardees[-1].endswith(f"image-{captures.IMAGES_MAX + 2:02d}.png")
    assert gardees[0].endswith("image-03.png")


def test_les_images_se_rangent_dans_le_chantier_et_une_image_manquee_se_dit(tmp_path):
    def lire(chemin):
        if "perdue" in chemin:
            raise OSError("pas sur la branche")
        return chemin.encode()

    lisibles, illisibles = captures.rendre_lisibles(
        tmp_path, ["captures/j/vue.png", "captures/j/perdue.png"], lire)
    assert lisibles == [".atelier/captures/vue.png"] and illisibles == ["perdue.png (pas sur la branche)"]
    assert (tmp_path / ".atelier" / "captures" / "vue.png").read_bytes() == b"captures/j/vue.png"
    assert captures.rendre_lisibles(tmp_path, [], lire) == ([], [])
