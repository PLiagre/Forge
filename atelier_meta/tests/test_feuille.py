"""La feuille de route : une seule représentation de l'état d'un lot.

Ce que ces tests protègent : une fiche incohérente échoue (jamais en
silence), une transition interdite échoue, le prochain lot se calcule
sans lire de prose, et rien ne se dépose sans --run ni sans drapeau.
Aucun test n'appelle un vrai agent.
"""

from pathlib import Path
import os
import shutil
import subprocess

import pytest

from atelier import boite, feuille, verrou
from atelier.__main__ import main
from tests.test_porte import BRIEF_SAIN


RACINE = Path(__file__).resolve().parent.parent
PILOTE = RACINE / "crons" / "pilote.sh"
TOUR = RACINE / "crons" / "tour.sh"

besoin_bash = pytest.mark.skipif(shutil.which("bash") is None, reason="bash absent")


# ---------------------------------------------------------------- outils


def _fiche(numero: str, slug: str, etat: str, *, couche: str = "1", depend: str = "—",
           pr: str = "—", chemin: str | None = None, note: str = "") -> str:
    chemin = chemin or f"briefs/{numero}-{slug}.md"
    texte = (
        f"### [{numero} — Titre {numero}]({chemin})\n"
        f"état : {etat} · couche : {couche} · dépend de : {depend} · PR : {pr}\n"
    )
    if note:
        texte += f"note : {note}\n"
    return texte + "\n"


def _feuille(*fiches: str) -> str:
    return (
        "# ROADMAP\n\nDe la prose.\n\n<!-- lots:debut -->\n\n"
        + "".join(fiches)
        + "<!-- lots:fin -->\n\nEncore de la prose.\n"
    )


def _brief(numero: str) -> str:
    return BRIEF_SAIN.replace("# Brief 001", f"# Brief {numero}")


def _produit(tmp_path: Path, texte_feuille: str | None = None, briefs: dict[str, str] | None = None) -> Path:
    racine = tmp_path / "produit"
    (racine / "briefs").mkdir(parents=True, exist_ok=True)
    (racine / "atelier.toml").write_text(
        "[projet]\n"
        'nom = "Produit"\n'
        'briefs = "briefs"\n'
        'tests = "python3 -m pytest -q"\n'
        'fumee = "echo fumee-ok"\n'
        'branche_base = "master"\n'
        'prefixe_branche = "agent/"\n'
        'feuille = "ROADMAP.md"\n'
        "\n[roles]\n"
        'ecriture = "claude"\n'
        'execution = "cursor"\n'
        'controle = "claude"\n',
        encoding="utf-8",
    )
    if texte_feuille is None:
        texte_feuille = _feuille(
            _fiche("044", "mineur", "livre", pr="184"),
            _fiche("046", "mer", "pret"),
            _fiche("047", "bourg", "pret", depend="044"),
            _fiche("048", "route", "a-briefer"),
            _fiche("049", "pont", "idee"),
        )
        briefs = briefs if briefs is not None else {"044-mineur": _brief("044"), "046-mer": _brief("046"), "047-bourg": _brief("047")}
    (racine / "ROADMAP.md").write_text(texte_feuille, encoding="utf-8")
    for nom, corps in (briefs or {}).items():
        (racine / "briefs" / f"{nom}.md").write_text(corps, encoding="utf-8")
    return racine


def _erreurs(racine: Path) -> list[str]:
    f = feuille.lire(racine / "ROADMAP.md")
    return feuille.verifier(f, racine, racine / "briefs") + feuille.verifier_cartes(f, racine)


def _carte(racine: Path, etat: str, lot: str, brief: str | None = None, **kw) -> None:
    boite.deposer(
        racine, etat,
        boite.Carte(lot=lot, brief=brief or f"briefs/{lot}.md", fichiers=kw.pop("fichiers", []), **kw),
    )


def _boite_de(racine: Path, etat: str) -> list[str]:
    dossier = racine / ".atelier" / "boite" / etat
    return sorted(p.stem for p in dossier.glob("*.json")) if dossier.is_dir() else []


# ------------------------------------------------------- lecture stricte


def test_une_feuille_saine_se_lit_et_se_relit_a_l_identique(tmp_path: Path):
    racine = _produit(tmp_path)
    une = feuille.lire(racine / "ROADMAP.md")
    deux = feuille.lire(racine / "ROADMAP.md")
    assert une.fiches, "échantillon vide"
    assert [f.numero for f in une.fiches] == ["044", "046", "047", "048", "049"]
    assert une.fiches == deux.fiches
    assert une.fiche("046").lot == "046-mer"
    assert une.fiche("044").prs == (184,)
    assert une.fiche("047").depend_de == ("044",)


def test_sans_reperes_la_feuille_est_illisible(tmp_path: Path):
    racine = _produit(tmp_path, texte_feuille="# ROADMAP\n\nDe la prose sans registre.\n")
    with pytest.raises(feuille.FeuilleErreur, match="lots:debut"):
        feuille.lire(racine / "ROADMAP.md")


@pytest.mark.parametrize(
    "ligne, attendu",
    [
        ("### 046 — sans lien\nétat : pret · couche : 1 · dépend de : — · PR : —\n\n", "ligne inattendue"),
        ("### [046 — Titre](briefs/046-mer.md)\nétat : pret · couche : 1 · dépend de : —\n\n", "champs manquants"),
        ("### [046 — Titre](briefs/046-mer.md)\nétat : en-cours · couche : 1 · dépend de : — · PR : —\n\n", "état inconnu"),
        ("### [046 — Titre](briefs/046-mer.md)\nétat : pret · couche : 9 · dépend de : — · PR : —\n\n", "couche inconnue"),
        ("### [046 — Titre](briefs/046-mer.md)\nétat : pret · couche : 1 · dépend de : — · PR : #12\n\n", "PR illisible"),
        ("### [046 — Titre](briefs/046-mer.md)\nétat : pret · couche : 1 · dépend de : — · PR : —\n### [047 — T](briefs/047-b.md)\nétat : idee · couche : 1 · dépend de : — · PR : —\n\n", "ligne vide"),
        ("### [046 — Titre](briefs/046-mer.md)\n\n", "sans ligne de champs"),
        ("Un paragraphe de prose dans le registre.\n\n", "ligne inattendue"),
    ],
)
def test_une_fiche_mal_formee_echoue_avec_la_ligne(tmp_path: Path, ligne: str, attendu: str):
    racine = _produit(tmp_path, texte_feuille=_feuille(ligne), briefs={})
    with pytest.raises(feuille.FeuilleErreur) as exc:
        feuille.lire(racine / "ROADMAP.md")
    assert attendu in str(exc.value)
    assert "ROADMAP.md:" in str(exc.value), "l'erreur nomme la ligne"


def test_un_intertitre_est_permis_dans_le_registre(tmp_path: Path):
    texte = _feuille("## Couche 2\n\n" + _fiche("046", "mer", "pret") + "## Archivés\n\n" + _fiche("033", "relief", "archive", pr="137", chemin="https://exemple/tree/tag/033-relief"))
    racine = _produit(tmp_path, texte_feuille=texte, briefs={"046-mer": _brief("046")})
    f = feuille.lire(racine / "ROADMAP.md")
    assert [x.numero for x in f.fiches] == ["046", "033"]
    assert f.fiche("033").lot == "033-relief"
    assert _erreurs(racine) == []


# ------------------------------------------------------------ cohérence


def test_une_feuille_coherente_n_a_aucune_erreur(tmp_path: Path):
    assert _erreurs(_produit(tmp_path)) == []


def test_un_numero_duplique_echoue(tmp_path: Path):
    texte = _feuille(_fiche("046", "mer", "pret"), _fiche("046", "mer-bis", "idee"))
    racine = _produit(tmp_path, texte_feuille=texte, briefs={"046-mer": _brief("046")})
    assert any("numéro dupliqué : 046" in e for e in _erreurs(racine))


def test_un_lot_pret_sans_brief_echoue(tmp_path: Path):
    racine = _produit(tmp_path, texte_feuille=_feuille(_fiche("046", "mer", "pret")), briefs={})
    erreurs = _erreurs(racine)
    assert any("« pret » mais son brief briefs/046-mer.md n'existe pas" in e for e in erreurs)


def test_un_lot_idee_dont_le_brief_existe_echoue(tmp_path: Path):
    racine = _produit(tmp_path, texte_feuille=_feuille(_fiche("046", "mer", "idee")), briefs={"046-mer": _brief("046")})
    assert any("existe déjà" in e for e in _erreurs(racine))


def test_un_brief_orphelin_echoue(tmp_path: Path):
    racine = _produit(tmp_path, texte_feuille=_feuille(_fiche("046", "mer", "pret")),
                      briefs={"046-mer": _brief("046"), "050-fantome": _brief("050")})
    assert any("brief orphelin" in e and "050-fantome" in e for e in _erreurs(racine))


def test_un_brief_qui_ne_porte_pas_son_numero_echoue(tmp_path: Path):
    racine = _produit(tmp_path, texte_feuille=_feuille(_fiche("046", "mer", "pret")), briefs={"046-mer": _brief("099")})
    assert any("se dit « Brief 099 »" in e for e in _erreurs(racine))


def test_un_lot_pret_dont_le_brief_ne_passe_pas_la_porte_echoue(tmp_path: Path):
    racine = _produit(tmp_path, texte_feuille=_feuille(_fiche("046", "mer", "pret")),
                      briefs={"046-mer": "# Brief 046\n\nrien.\n"})
    assert any("ne passe pas la porte" in e for e in _erreurs(racine))


def test_un_lot_livre_sans_pr_echoue(tmp_path: Path):
    racine = _produit(tmp_path, texte_feuille=_feuille(_fiche("044", "mineur", "livre")), briefs={"044-mineur": _brief("044")})
    assert any("« livre » sans numéro de PR" in e for e in _erreurs(racine))


def test_un_lot_pret_avec_pr_echoue(tmp_path: Path):
    racine = _produit(tmp_path, texte_feuille=_feuille(_fiche("046", "mer", "pret", pr="12")), briefs={"046-mer": _brief("046")})
    assert any("porte déjà une PR" in e for e in _erreurs(racine))


@pytest.mark.parametrize(
    "depend, attendu",
    [("099", "dépend de 099, qui n'a pas de fiche"), ("046", "dépend de lui-même")],
)
def test_une_dependance_fantome_ou_sur_soi_echoue(tmp_path: Path, depend: str, attendu: str):
    racine = _produit(tmp_path, texte_feuille=_feuille(_fiche("046", "mer", "pret", depend=depend)), briefs={"046-mer": _brief("046")})
    assert any(attendu in e for e in _erreurs(racine))


def test_des_dependances_circulaires_echouent(tmp_path: Path):
    texte = _feuille(_fiche("046", "mer", "idee", depend="047"), _fiche("047", "bourg", "idee", depend="046"))
    racine = _produit(tmp_path, texte_feuille=texte, briefs={})
    assert any("circulaires" in e for e in _erreurs(racine))


def test_un_lot_livre_qui_depend_d_un_lot_non_livre_echoue(tmp_path: Path):
    texte = _feuille(_fiche("046", "mer", "pret"), _fiche("047", "bourg", "livre", depend="046", pr="12"))
    racine = _produit(tmp_path, texte_feuille=texte, briefs={"046-mer": _brief("046"), "047-bourg": _brief("047")})
    assert any("« livre » mais dépend de 046, qui est « pret »" in e for e in _erreurs(racine))


def test_le_chemin_d_un_lot_vivant_porte_son_numero(tmp_path: Path):
    texte = _feuille(_fiche("046", "mer", "pret", chemin="briefs/mer.md"))
    racine = _produit(tmp_path, texte_feuille=texte, briefs={"mer": _brief("046")})
    assert any("doit s'appeler « briefs/046-" in e for e in _erreurs(racine))


# ------------------------------------------------- feuille contre cartes


def test_une_carte_d_un_lot_inconnu_echoue(tmp_path: Path):
    racine = _produit(tmp_path)
    _carte(racine, "a-coder", "099-fantome")
    assert any("carte 099-fantome dans a-coder — aucune fiche" in e for e in _erreurs(racine))


def test_une_carte_a_coder_pour_un_lot_sans_brief_fusionne_echoue(tmp_path: Path):
    racine = _produit(tmp_path)
    _carte(racine, "a-coder", "048-route")
    assert any("carte 048-route dans a-coder" in e and "a-briefer" in e for e in _erreurs(racine))


def test_une_carte_qui_nomme_un_autre_brief_echoue(tmp_path: Path):
    racine = _produit(tmp_path)
    _carte(racine, "a-coder", "046-mer", brief="briefs/autre.md")
    assert any("nomme le brief briefs/autre.md" in e for e in _erreurs(racine))


def test_une_carte_pour_un_lot_abandonne_echoue(tmp_path: Path):
    texte = _feuille(_fiche("046", "mer", "abandonne", note="on n'y va plus"))
    racine = _produit(tmp_path, texte_feuille=texte, briefs={})
    _carte(racine, "a-coder", "046-mer")
    assert any("« abandonne »" in e for e in _erreurs(racine))


# ------------------------------------------------------------ décision


def test_le_prochain_lot_se_calcule_sans_prose(tmp_path: Path):
    racine = _produit(tmp_path)
    decisions = feuille.decider(feuille.lire(racine / "ROADMAP.md"), racine)
    par_role = {d.role: d for d in decisions}
    assert par_role["coder"].lot == "046-mer"
    assert par_role["coder"].boite == "a-coder"
    assert par_role["coder"].fichiers == ("src/foo.py",)
    assert par_role["briefer"].lot == "048-route"
    assert par_role["briefer"].brief == "briefs/048-route.md"
    assert par_role["briefer"].fichiers == ()


def test_l_ordre_des_fiches_est_la_priorite(tmp_path: Path):
    texte = _feuille(_fiche("047", "bourg", "pret"), _fiche("046", "mer", "pret"))
    racine = _produit(tmp_path, texte_feuille=texte, briefs={"046-mer": _brief("046"), "047-bourg": _brief("047")})
    (coder,) = feuille.decider(feuille.lire(racine / "ROADMAP.md"), racine)
    assert coder.lot == "047-bourg"


def test_un_lot_bloque_par_une_dependance_n_est_pas_depose(tmp_path: Path):
    texte = _feuille(_fiche("047", "bourg", "pret", depend="046"), _fiche("046", "mer", "pret"))
    racine = _produit(tmp_path, texte_feuille=texte, briefs={"046-mer": _brief("046"), "047-bourg": _brief("047")})
    f = feuille.lire(racine / "ROADMAP.md")
    (coder,) = feuille.decider(f, racine)
    assert coder.lot == "046-mer"
    assert "bloqué par 046 (pret)" in feuille.etat_effectif(f.fiche("047"), f, racine)


def test_un_lot_deja_en_carte_n_est_pas_redepose(tmp_path: Path):
    racine = _produit(tmp_path)
    _carte(racine, "a-coder", "046-mer")
    f = feuille.lire(racine / "ROADMAP.md")
    coder = [d for d in feuille.decider(f, racine) if d.role == "coder"]
    assert coder and coder[0].lot == "047-bourg"
    assert feuille.etat_effectif(f.fiche("046"), f, racine) == "en file (a-coder)"


def test_un_lot_en_echec_attend_le_proprietaire(tmp_path: Path):
    racine = _produit(tmp_path)
    _carte(racine, "echec", "046-mer", note="délai dépassé")
    _carte(racine, "a-relire", "047-bourg", pr=12)
    f = feuille.lire(racine / "ROADMAP.md")
    assert [d.role for d in feuille.decider(f, racine)] == ["briefer"]
    assert "en échec : délai dépassé" in feuille.etat_effectif(f.fiche("046"), f, racine)
    assert feuille.etat_effectif(f.fiche("047"), f, racine) == "en relecture (PR 12)"


def test_un_fichier_tenu_par_un_autre_lot_retient_la_carte(tmp_path: Path):
    racine = _produit(tmp_path)
    verrou.poser(racine, "099-autre", ["src/foo.py"])
    f = feuille.lire(racine / "ROADMAP.md")
    assert [d.role for d in feuille.decider(f, racine)] == ["briefer"]
    assert "attend : src/foo.py tenu par 099-autre" in feuille.etat_effectif(f.fiche("046"), f, racine)


def test_sans_lot_admissible_la_decision_est_vide(tmp_path: Path):
    texte = _feuille(_fiche("044", "mineur", "livre", pr="1"), _fiche("049", "pont", "idee"))
    racine = _produit(tmp_path, texte_feuille=texte, briefs={"044-mineur": _brief("044")})
    assert feuille.decider(feuille.lire(racine / "ROADMAP.md"), racine) == []


# ------------------------------------------------------- rapprochements


def test_une_carte_d_un_lot_livre_se_rapproche_et_rend_le_verrou(tmp_path: Path):
    racine = _produit(tmp_path)
    _carte(racine, "faite", "044-mineur", pr=184)
    verrou.poser(racine, "044-mineur", ["src/foo.py"])
    f = feuille.lire(racine / "ROADMAP.md")
    assert _erreurs(racine) == [], "une carte dépassée n'est pas une incohérence : c'est une fusion"
    (r,) = feuille.rapprochements(f, racine)
    assert (r.lot, r.source, r.destination, r.lever_verrou) == ("044-mineur", "faite", "fusionnee", True)
    feuille.appliquer(racine, r)
    assert _boite_de(racine, "faite") == []
    assert _boite_de(racine, "fusionnee") == ["044-mineur"]
    assert verrou.charger(racine).poses == []


def test_le_brief_fusionne_libere_la_carte_du_briefer(tmp_path: Path):
    racine = _produit(tmp_path)
    _carte(racine, boite.SUIVANT["briefer"], "046-mer", pr=7)
    f = feuille.lire(racine / "ROADMAP.md")
    (r,) = feuille.rapprochements(f, racine)
    assert r.lot == "046-mer" and r.destination == "fusionnee" and not r.lever_verrou


def test_le_brief_en_pr_attend_le_proprietaire(tmp_path: Path):
    racine = _produit(tmp_path)
    _carte(racine, boite.SUIVANT["briefer"], "048-route", pr=7)
    f = feuille.lire(racine / "ROADMAP.md")
    assert feuille.rapprochements(f, racine) == []
    assert feuille.etat_effectif(f.fiche("048"), f, racine) == "brief écrit (PR 7) — à fusionner par le propriétaire"
    assert all(d.lot != "048-route" for d in feuille.decider(f, racine))


# ---------------------------------------------------------- transitions


def _transitions(avant: str, apres: str, **kw) -> list[str]:
    return feuille.transitions(feuille.lire_texte(avant), feuille.lire_texte(apres), **kw)


def test_pret_vers_livre_est_permis_et_livre_ne_revient_pas(tmp_path: Path):
    pret = _feuille(_fiche("046", "mer", "pret"))
    livre = _feuille(_fiche("046", "mer", "livre", pr="12"))
    assert _transitions(pret, livre) == []
    erreurs = _transitions(livre, pret)
    assert erreurs and "transition interdite pour le lot 046 : livre → pret" in erreurs[0]


def test_toutes_les_transitions_permises_passent_et_les_autres_echouent():
    for depart in feuille.ETATS:
        for arrivee in feuille.ETATS:
            if depart == arrivee:
                continue
            avant = _feuille(_fiche("046", "mer", depart, pr="1" if depart in feuille.ETATS_LIVRES else "—"))
            apres = _feuille(_fiche("046", "mer", arrivee, pr="1" if arrivee in feuille.ETATS_LIVRES or depart in feuille.ETATS_LIVRES else "—"))
            erreurs = _transitions(avant, apres)
            permise = arrivee in feuille.TRANSITIONS[depart]
            assert (erreurs == []) == permise, (depart, arrivee, erreurs)


def test_une_fiche_ne_disparait_pas(tmp_path: Path):
    avant = _feuille(_fiche("046", "mer", "pret"), _fiche("047", "bourg", "idee"))
    apres = _feuille(_fiche("046", "mer", "pret"))
    assert any("le lot 047 a disparu" in e for e in _transitions(avant, apres))


def test_un_lot_n_entre_jamais_livre(tmp_path: Path):
    avant = _feuille(_fiche("046", "mer", "pret"))
    apres = _feuille(_fiche("046", "mer", "pret"), _fiche("047", "bourg", "livre", pr="3"))
    assert any("entre dans la feuille « livre »" in e for e in _transitions(avant, apres))
    assert _transitions(avant, _feuille(_fiche("046", "mer", "pret"), _fiche("047", "bourg", "idee"))) == []


def test_la_pr_d_un_lot_doit_marquer_sa_fiche_livre_avec_son_numero(tmp_path: Path):
    avant = _feuille(_fiche("046", "mer", "pret"), _fiche("047", "bourg", "pret"))
    kw = dict(prefixe_branche="agent/", branche="agent/046-mer", pr=12)
    oubli = _transitions(avant, avant, **kw)
    assert any("ne marque pas le lot « livre »" in e for e in oubli)
    mauvais_numero = _transitions(avant, _feuille(_fiche("046", "mer", "livre", pr="11"), _fiche("047", "bourg", "pret")), **kw)
    assert any("la PR 12 du lot 046 n'est pas dans" in e for e in mauvais_numero)
    autre_fiche = _transitions(avant, _feuille(_fiche("046", "mer", "livre", pr="12"), _fiche("047", "bourg", "abandonne")), **kw)
    assert any("change aussi l'état de : 047" in e for e in autre_fiche)
    juste = _transitions(avant, _feuille(_fiche("046", "mer", "livre", pr="12"), _fiche("047", "bourg", "pret")), **kw)
    assert juste == []


def test_une_branche_de_lot_sans_fiche_echoue(tmp_path: Path):
    avant = _feuille(_fiche("046", "mer", "pret"))
    erreurs = _transitions(avant, avant, prefixe_branche="agent/", branche="agent/099-fantome")
    assert any("agent/099-fantome porte le lot 099-fantome, qui n'a aucune fiche" in e for e in erreurs)


# --------------------------------------------------------------- marquer


def test_marquer_ne_touche_que_la_ligne_de_champs(tmp_path: Path):
    texte = _feuille(_fiche("046", "mer", "pret"), _fiche("047", "bourg", "pret", depend="044"))
    nouveau = feuille.marquer(texte, "046", "livre", (12,))
    avant, apres = texte.splitlines(), nouveau.splitlines()
    assert len(avant) == len(apres)
    differentes = [i for i, (a, b) in enumerate(zip(avant, apres)) if a != b]
    assert len(differentes) == 1
    assert apres[differentes[0]] == "état : livre · couche : 1 · dépend de : — · PR : 12"
    assert feuille.lire_texte(nouveau).fiche("047").depend_de == ("044",)


def test_marquer_livre_sans_pr_refuse(tmp_path: Path):
    with pytest.raises(feuille.FeuilleErreur, match="sans numéro de PR"):
        feuille.marquer(_feuille(_fiche("046", "mer", "pret")), "046", "livre")


def test_marquer_refuse_une_transition_interdite_et_un_lot_inconnu(tmp_path: Path):
    texte = _feuille(_fiche("044", "mineur", "livre", pr="1"))
    with pytest.raises(feuille.FeuilleErreur, match="transition interdite"):
        feuille.marquer(texte, "044", "pret")
    with pytest.raises(feuille.FeuilleErreur, match="aucune fiche pour le lot 099"):
        feuille.marquer(texte, "099", "pret")


def test_marquer_accepte_le_slug_et_cumule_les_pr(tmp_path: Path):
    texte = _feuille(_fiche("044", "mineur", "livre", pr="184"))
    nouveau = feuille.marquer(texte, "044-mineur", "livre", (188,))
    assert feuille.lire_texte(nouveau).fiche("044").prs == (184, 188)


# ------------------------------------------------------------------- CLI


def test_cli_valider_passe_sur_une_feuille_coherente(tmp_path: Path, capsys):
    racine = _produit(tmp_path)
    assert main(["feuille", "valider", "--projet", str(racine)]) == 0
    assert "PASS" in capsys.readouterr().out


def test_cli_valider_echoue_et_dit_pourquoi(tmp_path: Path, capsys):
    racine = _produit(tmp_path, texte_feuille=_feuille(_fiche("046", "mer", "pret")), briefs={})
    assert main(["feuille", "valider", "--projet", str(racine)]) == 1
    assert "FAIL" in capsys.readouterr().err


def test_cli_valider_refuse_un_registre_vide(tmp_path: Path, capsys):
    racine = _produit(tmp_path, texte_feuille=_feuille(), briefs={})
    assert main(["feuille", "valider", "--projet", str(racine)]) == 1
    assert "aucune fiche" in capsys.readouterr().err


def test_cli_valider_sans_feuille_dans_le_branchement_refuse(tmp_path: Path, capsys):
    racine = _produit(tmp_path)
    toml = racine / "atelier.toml"
    toml.write_text(toml.read_text(encoding="utf-8").replace('feuille = "ROADMAP.md"\n', ""), encoding="utf-8")
    assert main(["feuille", "valider", "--projet", str(racine)]) == 1
    assert "[projet].feuille" in capsys.readouterr().err


def test_cli_valider_contre_une_base_git(tmp_path: Path, capsys):
    racine = _produit(tmp_path)
    git = ["git", "-C", str(racine)]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "-c", "user.email=t@t", "-c", "user.name=t", "add", "."], check=True)
    subprocess.run([*git, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base"], check=True)
    chemin = racine / "ROADMAP.md"
    chemin.write_text(feuille.marquer(chemin.read_text(encoding="utf-8"), "046", "livre", (12,)), encoding="utf-8")
    assert main(["feuille", "valider", "--projet", str(racine), "--base", "HEAD", "--branche", "agent/046-mer", "--pr", "12"]) == 0
    assert main(["feuille", "valider", "--projet", str(racine), "--base", "HEAD", "--branche", "agent/046-mer", "--pr", "13"]) == 1
    assert "la PR 13 du lot 046" in capsys.readouterr().err
    # La base sans registre : première feuille, on le dit, on ne fait pas semblant.
    subprocess.run([*git, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qam", "livre"], check=True)
    subprocess.run([*git, "mv", "ROADMAP.md", "VIEUX.md"], check=True)
    (racine / "ROADMAP.md").write_text("# rien\n", encoding="utf-8")
    subprocess.run([*git, "add", "."], check=True)
    subprocess.run([*git, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "sans registre"], check=True)
    (racine / "ROADMAP.md").write_text((racine / "VIEUX.md").read_text(encoding="utf-8"), encoding="utf-8")
    assert main(["feuille", "valider", "--projet", str(racine), "--base", "HEAD"]) == 0
    assert "première feuille" in capsys.readouterr().out


def test_cli_etat_montre_chaque_lot(tmp_path: Path, capsys):
    racine = _produit(tmp_path)
    assert main(["feuille", "etat", "--projet", str(racine)]) == 0
    sortie = capsys.readouterr().out
    assert "044-mineur" in sortie and "livré (PR 184)" in sortie
    assert "049-pont" in sortie and "idée" in sortie


def test_cli_marquer_reecrit_la_feuille(tmp_path: Path, capsys):
    racine = _produit(tmp_path)
    assert main(["feuille", "marquer", "--projet", str(racine), "--lot", "046-mer", "--etat", "livre", "--pr", "12"]) == 0
    assert feuille.lire(racine / "ROADMAP.md").fiche("046").etat == "livre"
    assert main(["feuille", "marquer", "--projet", str(racine), "--lot", "046", "--etat", "pret"]) == 1
    assert "transition interdite" in capsys.readouterr().err


def test_cli_piloter_a_sec_n_ecrit_rien(tmp_path: Path, capsys):
    racine = _produit(tmp_path)
    assert main(["piloter", "--projet", str(racine)]) == 0
    sortie = capsys.readouterr().out
    assert "déposer" in sortie and "046-mer" in sortie and "048-route" in sortie
    assert not (racine / ".atelier").exists()


def test_cli_piloter_run_depose_une_carte_par_role(tmp_path: Path, capsys):
    racine = _produit(tmp_path)
    assert main(["piloter", "--projet", str(racine), "--run"]) == 0
    assert _boite_de(racine, "a-coder") == ["046-mer"]
    assert _boite_de(racine, "a-briefer") == ["048-route"]
    assert boite.lire(racine, "a-coder", "046-mer").fichiers == ["src/foo.py"]
    # Le lendemain : 046 a sa carte, 047 est le suivant ; 048 attend son briefer.
    assert main(["piloter", "--projet", str(racine), "--run"]) == 0
    assert _boite_de(racine, "a-coder") == ["046-mer", "047-bourg"]
    assert _boite_de(racine, "a-briefer") == ["048-route"]
    assert main(["piloter", "--projet", str(racine), "--run"]) == 0
    assert capsys.readouterr().out.strip().splitlines()[-1] == "RIEN"


def test_cli_piloter_refuse_de_deposer_sur_une_feuille_incoherente(tmp_path: Path, capsys):
    racine = _produit(tmp_path, texte_feuille=_feuille(_fiche("046", "mer", "pret"), _fiche("048", "route", "a-briefer")), briefs={})
    assert main(["piloter", "--projet", str(racine), "--run"]) == 1
    assert "aucune carte déposée" in capsys.readouterr().err
    assert not (racine / ".atelier").exists()


def test_cli_piloter_run_rapproche_avant_de_decider(tmp_path: Path, capsys):
    racine = _produit(tmp_path)
    _carte(racine, "faite", "044-mineur", pr=184)
    verrou.poser(racine, "044-mineur", ["src/foo.py"])
    assert main(["piloter", "--projet", str(racine), "--run"]) == 0
    sortie = capsys.readouterr().out
    assert "rapproché  044-mineur : faite → fusionnee" in sortie and "verrou levé" in sortie
    assert _boite_de(racine, "fusionnee") == ["044-mineur"]
    # Le verrou rendu, 046 (qui touche le même fichier) part le jour même.
    assert _boite_de(racine, "a-coder") == ["046-mer"]


def test_cli_reprendre_retire_la_carte_d_echec(tmp_path: Path, capsys):
    racine = _produit(tmp_path)
    _carte(racine, "echec", "046-mer", note="délai dépassé")
    assert main(["reprendre", "--projet", str(racine), "--lot", "046-mer"]) == 0
    assert "délai dépassé" in capsys.readouterr().out
    assert _boite_de(racine, "echec") == []
    assert main(["reprendre", "--projet", str(racine), "--lot", "046-mer"]) == 1


def test_le_prompt_du_pilote_porte_la_decision_et_n_invente_rien(tmp_path: Path, capsys):
    racine = _produit(tmp_path)
    main(["invocation", "--role", "pilote", "--projet", str(racine), "--decision", "déposer a-coder 046-mer"])
    sortie = capsys.readouterr().out
    assert "déposer a-coder 046-mer" in sortie
    # shlex protège l'apostrophe : on cherche le fragment sans elle.
    assert "inventes ni numéro de lot" in sortie
    assert "Lis ROADMAP" not in sortie


def test_le_prompt_du_coder_fait_avancer_la_fiche(tmp_path: Path, capsys):
    racine = _produit(tmp_path)
    main(["invocation", "--role", "coder", "--projet", str(racine), "--lot", "046-mer", "--brief", "briefs/046-mer.md"])
    sortie = capsys.readouterr().out
    assert "feuille marquer --projet . --lot 046-mer --etat livre" in sortie
    assert "ROADMAP.md" in sortie
    main(["invocation", "--role", "briefer", "--projet", str(racine), "--lot", "048-route", "--brief", "briefs/048-route.md"])
    sortie = capsys.readouterr().out
    assert "--etat pret" in sortie and "pr.txt" in sortie


# ------------------------------------------------------------ les crons


def _env(racine: Path, faux: Path, verrous: Path, **extra: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("ATELIER_")}
    env["PATH"] = f"{faux}:{env.get('PATH', '')}"
    env["ATELIER_PROJET"] = str(racine)
    env["ATELIER_ROOT"] = str(RACINE)
    env["ATELIER_VERROUS"] = str(verrous)
    env["ATELIER_INVOQUER"] = "0"
    env["ATELIER_SANS_PULL"] = "1"
    env.update(extra)
    return env


def _faux(dossier: Path, nom: str, corps: str) -> Path:
    dossier.mkdir(parents=True, exist_ok=True)
    cible = dossier / nom
    cible.write_text("#!/usr/bin/env bash\n" + corps, encoding="utf-8")
    cible.chmod(0o755)
    return cible


def _lancer(script: Path, env: dict[str, str], *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(script), *args], env=env, text=True, capture_output=True, timeout=60)


@besoin_bash
def test_le_pilote_a_sec_montre_la_decision_et_ne_depose_rien(tmp_path: Path):
    racine = _produit(tmp_path)
    faux, verrous = tmp_path / "bin", tmp_path / "verrous"
    temoin = tmp_path / "hermes.txt"
    _faux(faux, "hermes", f'printf "%s\\n" "$*" >> "{temoin}"\n')
    r = _lancer(PILOTE, _env(racine, faux, verrous))
    assert r.returncode == 0, r.stderr
    assert "déposer" in r.stdout and "046-mer" in r.stdout
    assert "aucune carte déposée" in r.stdout
    assert not (racine / ".atelier").exists()
    assert not temoin.exists()


@besoin_bash
def test_le_pilote_sous_drapeau_depose_puis_dit_a_hermes_ce_qu_il_a_fait(tmp_path: Path):
    racine = _produit(tmp_path)
    faux, verrous = tmp_path / "bin", tmp_path / "verrous"
    temoin = tmp_path / "hermes.txt"
    _faux(faux, "hermes", f'printf "%s\\n" "$*" >> "{temoin}"\n')
    r = _lancer(PILOTE, _env(racine, faux, verrous, ATELIER_INVOQUER="1"))
    assert r.returncode == 0, r.stderr
    assert _boite_de(racine, "a-coder") == ["046-mer"]
    assert _boite_de(racine, "a-briefer") == ["048-route"]
    trace = temoin.read_text(encoding="utf-8")
    assert "déposé" in trace and "046-mer" in trace
    assert "tu ne déposes ni ne déplaces aucune carte" in trace


@besoin_bash
def test_le_pilote_ne_paie_pas_hermes_pour_rien(tmp_path: Path):
    texte = _feuille(_fiche("044", "mineur", "livre", pr="1"))
    racine = _produit(tmp_path, texte_feuille=texte, briefs={"044-mineur": _brief("044")})
    faux, verrous = tmp_path / "bin", tmp_path / "verrous"
    temoin = tmp_path / "hermes.txt"
    _faux(faux, "hermes", f'printf "%s\\n" "$*" >> "{temoin}"\n')
    r = _lancer(PILOTE, _env(racine, faux, verrous, ATELIER_INVOQUER="1"))
    assert r.returncode == 0, r.stderr
    assert "RIEN" in r.stdout
    assert not temoin.exists()


@besoin_bash
def test_le_pilote_sur_une_feuille_incoherente_ne_depose_rien_et_le_dit(tmp_path: Path):
    racine = _produit(tmp_path, texte_feuille=_feuille(_fiche("046", "mer", "pret")), briefs={})
    faux, verrous = tmp_path / "bin", tmp_path / "verrous"
    temoin = tmp_path / "hermes.txt"
    _faux(faux, "hermes", f'printf "%s\\n" "$*" >> "{temoin}"\n')
    r = _lancer(PILOTE, _env(racine, faux, verrous, ATELIER_INVOQUER="1"))
    assert r.returncode == 1
    assert not (racine / ".atelier").exists()
    trace = temoin.read_text(encoding="utf-8")
    assert "FAIL" in trace and "n'existe pas" in trace


@besoin_bash
def test_le_briefer_range_sa_carte_avec_le_numero_de_sa_pr(tmp_path: Path):
    racine = _produit(tmp_path)
    _carte(racine, "a-briefer", "048-route")
    faux, verrous = tmp_path / "bin", tmp_path / "verrous"
    _faux(faux, "claude", "mkdir -p atelier-echange && echo 7 > atelier-echange/pr.txt\n")
    r = _lancer(TOUR, _env(racine, faux, verrous, ATELIER_INVOQUER="1"), "briefer")
    assert r.returncode == 0, r.stderr
    assert _boite_de(racine, "a-briefer") == []
    assert _boite_de(racine, "a-coder") == [], "le coder ne trouverait pas un brief encore en PR"
    (carte,) = boite.lister(racine, boite.SUIVANT["briefer"])
    assert carte.lot == "048-route" and carte.pr == 7
    assert not (racine / "atelier-echange" / "pr.txt").exists()
