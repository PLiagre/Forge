from atelier import prompts


def test_le_mecanicien_ne_lance_pas_la_suite_entiere(projet):
    # Le 3 octobre 2026, la suite entière a coupé le mécanicien de #235 à 3600 s.
    texte = prompts.mecanicien_conflit(projet, numero=235, branche="lot/235-x", fichiers=["jeu/sim/lieux.py"])
    assert prompts._tests(projet) not in texte
    assert "-m pytest jeu/sim/tests/" in texte and "jamais la suite entière" in texte
