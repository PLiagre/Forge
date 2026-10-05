from atelier import prompts


def test_le_mecanicien_ne_lance_pas_la_suite_entiere(projet):
    # Le 3 octobre 2026, la suite entière a coupé le mécanicien de #235 à 3600 s.
    texte = prompts.mecanicien_conflit(projet, numero=235, branche="lot/235-x", fichiers=["jeu/sim/lieux.py"])
    assert prompts._tests(projet) not in texte
    assert "-m pytest jeu/sim/tests/" in texte and "jamais la suite entière" in texte


def test_le_codeur_ne_lance_pas_la_suite_entiere(projet):
    # Le 4 octobre 2026, la suite entière a coupé les codeurs de #237 et #319 à 3600 s.
    texte = prompts.codeur(projet, numero=237, titre="x", chemin_brief="b.md")
    assert prompts._tests(projet) not in texte
    assert "test_no_hardcoded.py" in texte and "Jamais la suite entière" in texte


def test_le_brief_d_un_lot_unity_dit_ce_que_sa_photo_montre(projet):
    def brief(machine):
        return prompts.chef(projet, numero=293, titre="x", corps="", commentaires="", jalon=4, jalon_titre="J4",
                            machine=machine, chemin_brief="b.md")
    assert "## Photo" in brief("pc") and "sans objet : <raison>" in brief("pc")
    assert "## Photo" not in brief("vps")
