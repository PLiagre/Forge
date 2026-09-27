"""Le pilote, tour par tour, sur un GitHub en mémoire et des agents dictés."""

from __future__ import annotations

from datetime import datetime, timezone

from atelier.lots import marque, marques
from atelier.pilote import Pilote

from conftest import Agents

BRIEF_BON = """# Lot #10 — Le service lit un lieu
Jalon : J1 · Machine : vps · Taille prévue : 120 lignes

## But
Unity lit un lieu.
## Règle du monde
sans objet
## Périmètre
jeu/sim/service.py
## Conditions de succès
SC1 : python3 -m pytest jeu -q
## Hors périmètre
Unity.
"""
BRANCHE = "lot/10-le-service-lit-un-lieu"


def _pilote(projet, gh, depot, agents, tmp_path):
    return Pilote(projet, gh, depot, executeur_agents=agents, journal=tmp_path / "journal.jsonl",
                  maintenant=lambda: datetime(2026, 9, 28, 8, 0, tzinfo=timezone.utc))


def _gestes(gh, nom):
    return [g for g in gh.gestes if g[0] == nom]


def test_le_chef_ecrit_le_brief_dans_la_branche_et_ouvre_la_pr(projet, gh, depot, tmp_path):
    gh.ajouter_issue(10, "Le service lit un lieu")
    agents = Agents((0, "J'ai écrit le brief.\nDECISION: BRIEF", {"docs/briefs/10-le-service-lit-un-lieu.md": BRIEF_BON}))
    lignes = _pilote(projet, gh, depot, agents, tmp_path).tour()
    assert agents.outils() == ["claude"]
    assert ("pousser", BRANCHE) in depot.gestes
    assert _gestes(gh, "creer_pr")[0][1:] == (BRANCHE, "Lot #10 — Le service lit un lieu")
    assert ("etiqueter", 10, ("en-cours",), ("pret",)) in gh.gestes
    assert any("brief écrit" in l for l in lignes)
    pr = gh.prs_[max(gh.prs_)]
    assert "Closes #10" in pr["body"]
    assert marques(pr["comments"])[0]["role"] == "chef"


def test_le_chef_ne_garde_que_le_brief(projet, gh, depot, tmp_path):
    gh.ajouter_issue(10, "Le service lit un lieu")
    agents = Agents((0, "DECISION: BRIEF", {"docs/briefs/10-le-service-lit-un-lieu.md": BRIEF_BON,
                                             "jeu/sim/engine.py": "triche"}))
    _pilote(projet, gh, depot, agents, tmp_path).tour()
    assert ("annuler", ("jeu/sim/engine.py",)) in depot.gestes


def test_le_chef_refuse_un_lot_hors_du_jalon(projet, gh, depot, tmp_path):
    gh.ajouter_issue(10, "Des batailles navales")
    _pilote(projet, gh, depot, Agents((0, "DECISION: REFUS :: c'est le jalon 6")), tmp_path).tour()
    etiquettes = [e["name"] for e in gh.issues_[10]["labels"]]
    assert "bloque" in etiquettes and "pret" not in etiquettes
    assert "jalon 6" in gh.issues_[10]["comments"][-1]["body"]
    assert not _gestes(gh, "creer_pr")


def test_le_chef_decoupe_un_lot_trop_gros(projet, gh, depot, tmp_path):
    gh.ajouter_issue(10, "Tout le pont")
    texte = "DECISION: DECOUPE\n- Le service :: sim sert un lieu\n- Le panneau :: Unity affiche le lieu\n"
    _pilote(projet, gh, depot, Agents((0, texte)), tmp_path).tour()
    crees = [g[1] for g in _gestes(gh, "creer_issue")]
    assert crees == ["Le service", "Le panneau"]
    assert ("fermer_issue", 10, True) in gh.gestes
    assert all(i["milestone"]["title"] == "J1 — Le pont" for n, i in gh.issues_.items() if n > 100)


def test_un_brief_trop_gros_est_un_echec_puis_un_blocage(projet, gh, depot, tmp_path):
    gh.ajouter_issue(10, "Le service lit un lieu")
    gros = BRIEF_BON.replace("120 lignes", "450 lignes")
    for _ in range(2):
        _pilote(projet, gh, depot, Agents((0, "DECISION: BRIEF", {"docs/briefs/10-le-service-lit-un-lieu.md": gros})),
                tmp_path).tour()
    assert "trop gros" in gh.issues_[10]["comments"][0]["body"]
    _pilote(projet, gh, depot, Agents(), tmp_path).tour()
    assert "bloque" in [e["name"] for e in gh.issues_[10]["labels"]]


def _en_cours(gh, commentaires=(), ci="vert", etiquettes=("lot", "en-cours")):
    gh.ajouter_issue(10, "Le service lit un lieu", etiquettes)
    return gh.ajouter_pr(50, BRANCHE, brouillon=True, ci=ci, commentaires=commentaires)


def test_le_codeur_code_et_les_chemins_interdits_sont_retires(projet, gh, depot, tmp_path):
    _en_cours(gh)
    agents = Agents((0, "Fait : service écrit, 12 tests verts.",
                     {"jeu/sim/service.py": "code", "atelier/pilote.py": "triche"}))
    _pilote(projet, gh, depot, agents, tmp_path).tour()
    assert agents.outils() == ["codex"]
    assert ("annuler", ("atelier/pilote.py",)) in depot.gestes
    assert ("pousser", BRANCHE) in depot.gestes and ("pr_prete", 50) in gh.gestes
    dernier = gh.prs_[50]["comments"][-1]["body"]
    assert "Changements retirés" in dernier and "`atelier/pilote.py`" in dernier
    assert marques([{"body": dernier}]) == [{"role": "codeur", "etat": "fait", "essai": 1,
                                             "agent": "codex/sol", "sha": "b" * 40}]


def test_un_codeur_qui_ne_change_rien_echoue(projet, gh, depot, tmp_path):
    _en_cours(gh)
    _pilote(projet, gh, depot, Agents((0, "Je n'ai rien trouvé à faire.")), tmp_path).tour()
    assert marques(gh.prs_[50]["comments"])[-1]["etat"] == "echec"
    assert not [g for g in depot.gestes if g[0] == "pousser"]


FAIT_CODEX = marque(role="codeur", etat="fait", essai=1, agent="codex/sol", sha="a" * 40)


def test_le_relecteur_accepte_et_la_fusion_part(projet, gh, depot, tmp_path):
    _en_cours(gh, commentaires=[FAIT_CODEX])
    agents = Agents((0, "Le diff reste dans le périmètre.\nVERDICT: ACCEPTE"))
    _pilote(projet, gh, depot, agents, tmp_path).tour()
    assert agents.outils() == ["claude"]
    revue = gh.prs_[50]["comments"][-1]["body"]
    assert revue.startswith("## Relecture — ACCEPTE") and "VERDICT" not in revue
    assert ("fusion_auto", 50) in gh.gestes


def test_l_auteur_claude_est_relu_par_codex(projet, gh, depot, tmp_path):
    fait_claude = marque(role="codeur", etat="fait", essai=1, agent="claude/opus", sha="a" * 40)
    _en_cours(gh, commentaires=[fait_claude])
    agents = Agents((0, "VERDICT: CORRIGER"))
    _pilote(projet, gh, depot, agents, tmp_path).tour()
    assert agents.outils() == ["codex"]
    assert not _gestes(gh, "fusion_auto")


def test_corriger_donne_la_revue_au_codeur(projet, gh, depot, tmp_path):
    revue = "## Relecture — CORRIGER\n\nLe test SC1 ne peut pas rougir (jeu/sim/tests/x.py:3).\n\n" + marque(
        role="relecteur", verdict="CORRIGER", sha="a" * 40, agent="claude/opus")
    _en_cours(gh, commentaires=[FAIT_CODEX, revue])
    agents = Agents((0, "Corrigé.", {"jeu/sim/tests/x.py": "mieux"}))
    _pilote(projet, gh, depot, agents, tmp_path).tour()
    prompt = agents.appels[0][-1]
    assert "C'EST UNE CORRECTION" in prompt and "ne peut pas rougir" in prompt
    assert marques(gh.prs_[50]["comments"])[-1]["essai"] == 2


def test_sans_agent_disponible_le_lot_attend_sans_bruit(projet, gh, depot, tmp_path):
    _en_cours(gh)
    lignes = _pilote(projet, gh, depot, Agents((1, "429 Too Many Requests"), (1, "usage limit reached")), tmp_path).tour()
    assert gh.prs_[50]["comments"] == []
    assert any("attente" in l for l in lignes)
    assert (tmp_path / "journal.jsonl").read_text(encoding="utf-8").count("attente") == 1


def test_un_seul_agent_par_tour(projet, gh, depot, tmp_path):
    _en_cours(gh)
    gh.ajouter_issue(11, "Le panneau affiche le lieu", ("lot", "en-cours"))
    gh.ajouter_pr(51, "lot/11-le-panneau-affiche-le-lieu", ci="vert")
    agents = Agents((0, "Fait.", {"jeu/sim/service.py": "code"}))
    _pilote(projet, gh, depot, agents, tmp_path).tour()
    assert len(agents.appels) == 1 and gh.prs_[51]["comments"] == []


def test_un_lot_fusionne_est_livre(projet, gh, depot, tmp_path):
    gh.ajouter_issue(10, "Le service lit un lieu", ("lot", "en-cours"), etat="CLOSED")
    pr = gh.ajouter_pr(50, BRANCHE, etat="MERGED")
    pr["mergedAt"] = "2026-09-28T07:00:00Z"
    _pilote(projet, gh, depot, Agents(), tmp_path).tour()
    assert "livre" in [e["name"] for e in gh.issues_[10]["labels"]]
    assert ("retirer", 10) in depot.gestes


def test_un_lot_pc_part_sur_le_pc_sans_agent_local(projet, gh, depot, tmp_path):
    _en_cours(gh, etiquettes=("lot", "en-cours", "pc"))
    agents = Agents()
    _pilote(projet, gh, depot, agents, tmp_path).tour()
    assert agents.appels == []
    envoi = _gestes(gh, "lancer_workflow")[0]
    assert envoi[1] == "lot-pc.yml" and envoi[2]["branche"] == BRANCHE and envoi[2]["action"] == "coder"
    assert marques(gh.prs_[50]["comments"])[-1]["etat"] == "envoye"


def test_un_jalon_sans_lot_ouvert_est_atteint(projet, gh, depot, tmp_path):
    gh.jalons_[0].update(open_issues=0, closed_issues=4)
    _pilote(projet, gh, depot, Agents(), tmp_path).tour()
    assert ("fermer_jalon", 1) in gh.gestes


def test_rien_a_faire_se_dit(projet, gh, depot, tmp_path):
    assert _pilote(projet, gh, depot, Agents(), tmp_path).tour() == ["RIEN"]
