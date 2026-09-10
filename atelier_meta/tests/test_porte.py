"""La porte refuse un brief infirme, et un échantillon vide échoue."""

from pathlib import Path

from atelier.porte import inspecter, passer


def _ecrire(tmp_path: Path, corps: str) -> Path:
    cible = tmp_path / "brief.md"
    cible.write_text(corps, encoding="utf-8")
    return cible


BRIEF_SAIN = """# Brief 001 — un changement

## But
Après ce lot, une commande mesure autre chose.

## Règle du monde
Aucun fondement produit. Ce lot ne change aucun nombre du monde.

## Périmètre
Écriture autorisée : `src/foo.py`. Tout le reste est interdit.

## Conditions de succès

### SC1 — la commande échoue tant que ce n'est pas là

```bash
python3 -m pytest tests/test_foo.py -q
```

## Hors périmètre
Pas de fusion, pas d'autre fichier.
"""


def test_brief_sain_passe(tmp_path: Path):
    assert passer(_ecrire(tmp_path, BRIEF_SAIN))


def test_sans_perimetre_echoue(tmp_path: Path):
    texte = BRIEF_SAIN.replace("## Périmètre\nÉcriture autorisée : `src/foo.py`. Tout le reste est interdit.\n", "## Périmètre\nrien\n")
    constats = {c.nom: c for c in inspecter(_ecrire(tmp_path, texte))}
    assert not constats["perimetre_fichiers"].ok


def test_sans_commande_echoue(tmp_path: Path):
    texte = BRIEF_SAIN.replace("```bash\npython3 -m pytest tests/test_foo.py -q\n```", "le code est propre")
    constats = {c.nom: c for c in inspecter(_ecrire(tmp_path, texte))}
    assert not constats["criteres_commandes"].ok


def test_fichier_absent_echoue(tmp_path: Path):
    constats = inspecter(tmp_path / "nexiste-pas.md")
    assert constats[0].nom == "fichier"
    assert not constats[0].ok
    assert not passer(tmp_path / "nexiste-pas.md")


def test_section_vide_echoue(tmp_path: Path):
    texte = BRIEF_SAIN.replace("Après ce lot, une commande mesure autre chose.", "")
    constats = {c.nom: c for c in inspecter(_ecrire(tmp_path, texte))}
    assert not constats["section:But"].ok
