"""Le palier se déclenche sur une mesure, jamais sur une intention."""

import subprocess
import sys


from dataclasses import dataclass, field

import pytest

from outils import palier



def test_un_slug_bis_ou_ter_reste_un_palier():
    """Une réparation de brief (`-bis`, `-ter`) reste un palier : le
    reconnaître autrement, c'est redéposer la même couche à chaque fusion."""
    assert palier.couche_stabilisee("briefs/043-bis-stabilisation-couche-1.md") == "1"
    assert palier.couche_stabilisee("briefs/043-ter-stabilisation-couche-2.md") == "2"
    assert palier.couche_stabilisee("briefs/043-bis-un-lot.md") is None


def test_un_palier_bis_couvre_les_lots_qu_il_nomme():
    fiches = [
        FicheFactice("046", "livre", "1"),
        stabilisation("055-bis", "1", "livre", couvre=("046",)),
    ]
    assert palier.couche_stabilisee(fiches[1].chemin) == "1"
    assert palier.due(fiches) is None
    assert palier.etapes(fiches)[0].couverts == ("046",)


class _FeuilleFactice:
    """Ce que `registre.feuille` rend, réduit à ce que la CLI lit."""

    def __init__(self, fiches, chemin):
        self.fiches = fiches
        self.chemin = chemin


def _cli_palier(tmp_path, monkeypatch, capsys, fiches, ecrire=False):
    """La ligne que le workflow découpe, sans l'atelier ni GitHub."""
    from outils import registre
    from outils.__main__ import main

    chemin = tmp_path / "ROADMAP.md"
    if not chemin.exists():
        chemin.write_text("# titre\n\n<!-- lots:debut -->\n", encoding="utf-8")
    monkeypatch.setattr(
        registre, "branchement",
        lambda _r: {"feuille": "ROADMAP.md", "base": "master", "briefs": "briefs"},
    )
    monkeypatch.setattr(
        registre, "feuille", lambda _r: _FeuilleFactice(fiches, chemin)
    )

    class _Atelier:
        REPERE_DEBUT = "<!-- lots:debut -->"

    monkeypatch.setattr(registre, "atelier", lambda: _Atelier)
    argv = ["palier", "--projet", str(tmp_path)]
    if ecrire:
        argv.append("--ecrire")
    code = main(argv)
    return code, capsys.readouterr(), chemin


def test_cli_palier_imprime_rien_quand_aucune_couche_n_attend(tmp_path, monkeypatch, capsys):
    """Le workflow compare stdout à `RIEN`. Une autre casse ouvrirait une PR."""
    fiches = [
        FicheFactice("046", "livre", "1"),
        FicheFactice("050", "pret", "1"),
    ]
    code, io, chemin = _cli_palier(tmp_path, monkeypatch, capsys, fiches)
    assert code == 0
    assert io.out == "RIEN\n"
    assert chemin.read_text(encoding="utf-8") == "# titre\n\n<!-- lots:debut -->\n"


def test_cli_palier_imprime_le_format_que_le_workflow_decoupe(tmp_path, monkeypatch, capsys):
    """`cut -d' ' -f2/f3/f4` : `palier N slug couche=C`, quatre champs, rien d'autre."""
    fiches = [
        FicheFactice("046", "livre", "1"),
        FicheFactice("050", "livre", "1"),
    ]
    code, io, chemin = _cli_palier(tmp_path, monkeypatch, capsys, fiches)
    assert code == 0
    champs = io.out.strip().split(" ")
    assert champs == ["palier", "051", "051-stabilisation-couche-1", "couche=1"]
    assert champs[3].split("=", 1)[1] == "1"
    assert chemin.read_text(encoding="utf-8") == "# titre\n\n<!-- lots:debut -->\n"
    assert "sans --ecrire" in io.err


def test_cli_palier_ecrire_pose_la_fiche_en_tete(tmp_path, monkeypatch, capsys):
    """`--ecrire` est le seul geste qui touche le registre. Sans lui, rien n'est écrit ;
    avec lui, la fiche entre en tête — c'est ce que le workflow commit ensuite."""
    fiches = [
        FicheFactice("046", "livre", "1"),
        FicheFactice("050", "livre", "1"),
    ]
    avant = "# titre\n\n<!-- lots:debut -->\n\n### [046 — La mer](briefs/046-la-mer.md)\n"
    chemin_avant = tmp_path / "ROADMAP.md"
    chemin_avant.write_text(avant, encoding="utf-8")

    code, io, chemin = _cli_palier(
        tmp_path, monkeypatch, capsys, fiches, ecrire=False
    )
    assert code == 0
    assert chemin.read_text(encoding="utf-8") == avant

    code, io, chemin = _cli_palier(
        tmp_path, monkeypatch, capsys, fiches, ecrire=True
    )
    assert code == 0
    assert io.out == "palier 051 051-stabilisation-couche-1 couche=1\n"
    texte = chemin.read_text(encoding="utf-8")
    assert texte.startswith("# titre\n\n<!-- lots:debut -->\n\n### [051 —")
    assert "stabilisation-couche-1.md" in texte
    assert "dépend de : 046, 050" in texte
    assert "### [046 — La mer]" in texte
    assert texte.index("### [051 —") < texte.index("### [046 — La mer]")


def test_cli_palier_sans_branchement_n_imprime_pas_rien(tmp_path):
    """Un FAIL lu sur stdout comme une ligne de palier ouvrirait une PR.
    Il va sur stderr, le code n'est pas 0, stdout reste vide — pas `RIEN`."""
    proc = subprocess.run(
        [sys.executable, "-m", "outils", "palier", "--projet", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    assert "FAIL" in proc.stderr
    assert proc.stdout == ""


@dataclass(frozen=True)
class FicheFactice:
    """Ce que le lecteur de l'atelier rend, réduit à ce que le palier lit."""

    numero: str
    etat: str
    couche: str | None = None
    chemin: str = ""
    depend_de: tuple[str, ...] = field(default=())

    def __post_init__(self) -> None:
        if not self.chemin:
            object.__setattr__(self, "chemin", f"briefs/{self.numero}-un-lot.md")


def stabilisation(numero: str, couche: str, etat: str, couvre=()):
    return FicheFactice(
        numero=numero,
        etat=etat,
        couche=couche,
        chemin=f"briefs/{numero}-stabilisation-couche-{couche}.md",
        depend_de=tuple(couvre),
    )


def test_une_couche_dont_un_lot_avance_n_est_pas_finie():
    fiches = [
        FicheFactice("046", "livre", "1"),
        FicheFactice("050", "pret", "1"),
    ]
    assert palier.due(fiches) is None


def test_une_couche_entierement_livree_appelle_son_palier():
    fiches = [
        FicheFactice("046", "livre", "1"),
        FicheFactice("050", "livre", "1"),
    ]
    etape = palier.due(fiches)
    assert etape is not None
    assert etape.couche == "1"
    assert etape.a_couvrir == ("046", "050")


def test_un_lot_abandonne_ne_retient_pas_la_couche_et_ne_se_couvre_pas():
    fiches = [
        FicheFactice("046", "livre", "1"),
        FicheFactice("050", "abandonne", "1"),
    ]
    etape = palier.due(fiches)
    assert etape is not None
    assert etape.a_couvrir == ("046",)


def test_une_couche_sans_rien_de_livre_n_est_pas_une_couche_finie():
    """Un échantillon vide échoue : il ne passe pas."""
    fiches = [FicheFactice("050", "abandonne", "1")]
    assert palier.due(fiches) is None
    assert palier.etapes(fiches)[0].finie is False


def test_le_palier_ne_se_redeclenche_pas_sur_les_lots_qu_il_couvre():
    fiches = [
        FicheFactice("046", "livre", "1"),
        FicheFactice("050", "livre", "1"),
        stabilisation("055", "1", "livre", couvre=("046", "050")),
    ]
    assert palier.due(fiches) is None


def test_un_lot_livre_apres_le_palier_en_appelle_un_autre():
    fiches = [
        FicheFactice("046", "livre", "1"),
        FicheFactice("050", "livre", "1"),
        stabilisation("055", "1", "livre", couvre=("046", "050")),
        FicheFactice("058", "livre", "1"),
    ]
    etape = palier.due(fiches)
    assert etape is not None
    assert etape.a_couvrir == ("058",)
    assert etape.couverts == ("046", "050")


def test_un_palier_en_attente_retient_sa_couche():
    """La fiche déposée est elle-même de la couche : tant qu'elle n'est
    pas livrée, la couche n'est pas finie — c'est ce qui empêche la
    boucle de déposer deux fois le même palier."""
    fiches = [
        FicheFactice("046", "livre", "1"),
        stabilisation("055", "1", "a-briefer", couvre=("046",)),
    ]
    assert palier.due(fiches) is None


def test_les_couches_partent_dans_l_ordre():
    fiches = [
        FicheFactice("047", "livre", "2"),
        FicheFactice("046", "livre", "1"),
    ]
    etape = palier.due(fiches)
    assert etape is not None
    assert etape.couche == "1"


def test_une_fiche_sans_couche_n_appartient_a_aucun_palier():
    fiches = [FicheFactice("048", "livre", None), FicheFactice("054", "livre", None)]
    assert palier.etapes(fiches) == ()
    assert palier.due(fiches) is None


def test_le_numero_est_le_premier_libre_au_dessus_du_plus_grand():
    fiches = [FicheFactice("046", "livre", "1"), FicheFactice("054", "idee", "2")]
    assert palier.numero_libre(fiches) == "055"


def test_un_suffixe_bis_ne_compte_pas_pour_un_numero_de_plus():
    fiches = [FicheFactice("043-bis", "archive", "1"), FicheFactice("043", "archive", "1")]
    assert palier.numero_libre(fiches) == "044"


def test_un_registre_vide_refuse_de_rendre_un_numero():
    with pytest.raises(ValueError):
        palier.numero_libre([])


def test_la_fiche_ecrite_est_relue_par_le_lecteur_du_registre():
    """La preuve qui compte : ce qu'on écrit, l'atelier le relit.

    Sans lui, ce contrôle ne se joue pas — et il le dit, il ne passe
    pas en silence.
    """
    feuille = pytest.importorskip(
        "atelier.feuille",
        reason="ForgeAtelier hors du PYTHONPATH : le lecteur du registre manque",
    )
    fiches = [FicheFactice("046", "livre", "1"), FicheFactice("050", "livre", "1")]
    etape = palier.due(fiches)
    texte = (
        "# titre\n\n"
        f"{feuille.REPERE_DEBUT}\n\n"
        "### [046 — La mer](briefs/046-la-mer.md)\n"
        "état : livre · couche : 1 · dépend de : — · PR : 206\n\n"
        "### [050 — La migration](briefs/050-la-migration.md)\n"
        "état : livre · couche : 1 · dépend de : — · PR : 210\n\n"
        f"{feuille.REPERE_FIN}\n"
    )
    nouveau = palier.inserer(texte, palier.fiche(etape, "055"), feuille.REPERE_DEBUT)
    relu = feuille.lire_texte(nouveau)
    fiche = relu.fiche("055")
    assert fiche is not None
    assert fiche.etat == "a-briefer"
    assert fiche.couche == "1"
    assert fiche.depend_de == ("046", "050")
    assert fiche.prs == ()
    # L'ordre est la priorité : le palier passe devant ce qui attend.
    assert relu.fiches[0].numero == "055"


def test_la_fiche_d_un_palier_se_reconnait_a_son_chemin():
    assert palier.couche_stabilisee("briefs/055-stabilisation-couche-1.md") == "1"
    assert palier.couche_stabilisee("briefs/049-fabriquer.md") is None


def test_on_n_ecrit_pas_un_palier_qui_ne_couvre_rien():
    etape = palier.Etape(couche="1", en_cours=(), couverts=("046",), a_couvrir=())
    with pytest.raises(ValueError):
        palier.fiche(etape, "055")


def test_inserer_refuse_un_registre_sans_repere():
    with pytest.raises(ValueError):
        palier.inserer("# rien\n", "### [055 — x](briefs/055-x.md)", "<!-- lots:debut -->")


def test_un_lot_archive_ne_reclame_pas_de_palier():
    """Son brief et ses preuves vivent au tag : aucun lot de
    stabilisation ne pourrait les citer. Il ne retient rien, il
    n'appelle rien."""
    fiches = [FicheFactice("033", "archive", "1"), FicheFactice("038", "archive", "1")]
    etape = palier.etapes(fiches)[0]
    assert etape.finie
    assert etape.a_couvrir == ()
    assert palier.due(fiches) is None


def test_un_lot_livre_a_cote_d_archives_appelle_seul_le_palier():
    fiches = [FicheFactice("033", "archive", "1"), FicheFactice("046", "livre", "1")]
    etape = palier.due(fiches)
    assert etape is not None
    assert etape.a_couvrir == ("046",)
    assert etape.couverts == ("033",)


def test_232_deux_attributions_reservent_des_numeros_distincts():
    fiches = [FicheFactice("054", "idee")]
    reserves = ["055", "058", "060"]  # PR ouverte, branche seule, palier en attente
    premier = palier.numero_libre(fiches, reserves)
    second = palier.numero_libre(fiches, [*reserves, premier])
    assert int(premier) > max(map(int, reserves))
    assert int(second) > int(premier)
