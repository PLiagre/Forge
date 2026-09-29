"""Le pilote, tour par tour, sur un GitHub en mémoire et des agents dictés."""

from __future__ import annotations

from datetime import datetime, timezone
import json

import pytest

from atelier import lots
from atelier.lots import Lot, marque, marques
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


def test_les_sous_lots_se_suivent_et_ce_qui_attendait_le_lot_decoupe_les_attend(projet, gh, depot, tmp_path):
    # Mesuré le 28 septembre 2026 : #119 découpé en #183 et #184 ; #120, qui
    # « dépend de #119 », devenait libre au tour suivant, avant ses morceaux.
    gh.ajouter_issue(10, "Tout le pont")
    gh.ajouter_issue(20, "Le lanceur", corps="Dépend de : #10")
    texte = "DECISION: DECOUPE\n- Le service :: sim sert un lieu\n- Le panneau :: Unity affiche le lieu\n"
    _pilote(projet, gh, depot, Agents((0, texte)), tmp_path).tour()
    service, panneau = 101, 102
    assert Lot.de(gh.issues_[panneau]).dependances == frozenset({service})
    # Le tour suivant prend le premier sous-lot, jamais le lanceur.
    agents = Agents((0, "DECISION: BRIEF", {"docs/briefs/101-le-service.md": BRIEF_BON}))
    _pilote(projet, gh, depot, agents, tmp_path).tour()
    assert _gestes(gh, "creer_pr")[-1][1] == "lot/101-le-service"


def test_un_lot_attend_les_sous_lots_ouverts_du_lot_dont_il_depend(projet, gh, depot, tmp_path):
    gh.ajouter_issue(10, "Tout le pont", etat="CLOSED")
    gh.ajouter_issue(20, "Le lanceur", corps="Dépend de : #10")
    # Le sous-lot ouvert est sur le PC : la machine du VPS est libre, seule la
    # dépendance retient le lanceur.
    gh.ajouter_issue(30, "Le panneau", ("lot", "en-cours", "pc"), corps="Ce qu'il fait.\n\nDécoupé du lot #10 par le chef.")
    fait_pc = marque(role="codeur_3d", etat="fait", essai=1, agent="claude/opus", sha="a" * 40)
    gh.ajouter_pr(60, "lot/30-le-panneau", ci="attente", commentaires=[fait_pc])
    assert _pilote(projet, gh, depot, Agents(), tmp_path).tour() == ["#30 attendre_ci — PR #60"]
    gh.issues_[30]["state"] = "CLOSED"
    agents = Agents((0, "DECISION: BRIEF", {"docs/briefs/20-le-lanceur.md": BRIEF_BON}))
    _pilote(projet, gh, depot, agents, tmp_path).tour()
    assert _gestes(gh, "creer_pr")[-1][1] == "lot/20-le-lanceur"


def test_un_lot_en_cours_qui_attend_une_dependance_rend_sa_machine(projet, gh, depot, tmp_path):
    # Mesuré le 28 septembre 2026 : #184 (le panneau), pris avant #185 et #186
    # (le client qu'il lit), gardait le PC et brûlait ses essais : le codeur
    # refusait, à raison, de coder sans le client.
    gh.ajouter_issue(10, "Le service lit un lieu", ("lot", "en-cours", "pc"), corps="Dépend de : #11")
    refus = marque(role="codeur_3d", etat="echec", essai=1, agent="claude/opus")
    gh.ajouter_pr(50, BRANCHE, commentaires=[ENVOI_PC, refus])
    gh.ajouter_issue(11, "Le client", ("lot", "pret", "pc"))
    agents = Agents((0, "DECISION: BRIEF", {"docs/briefs/11-le-client.md": BRIEF_BON}))
    _pilote(projet, gh, depot, agents, tmp_path).tour()
    etiquettes = [e["name"] for e in gh.issues_[10]["labels"]]
    assert "pret" in etiquettes and "en-cours" not in etiquettes
    assert "#11" in gh.issues_[10]["comments"][-1]["body"]
    assert not _gestes(gh, "lancer_workflow")
    # La machine rendue, le client est pris.
    assert _gestes(gh, "creer_pr")[-1][1] == "lot/11-le-client"


def test_un_lot_pret_ne_se_reprend_qu_une_fois_ses_dependances_livrees(projet, gh, depot, tmp_path):
    gh.ajouter_issue(10, "Le service lit un lieu", ("lot", "pret", "pc"), corps="Dépend de : #11")
    gh.ajouter_pr(50, BRANCHE, commentaires=[ENVOI_PC, ECHEC_127])
    gh.ajouter_issue(11, "Le client", ("lot", "en-cours"))
    gh.ajouter_pr(51, "lot/11-le-client", ci="attente", commentaires=[FAIT_CODEX])
    _pilote(projet, gh, depot, Agents(), tmp_path).tour()
    assert not any(m.get("etat") == "reprise" for m in marques(gh.prs_[50]["comments"]))
    gh.issues_[11]["state"] = "CLOSED"
    _pilote(projet, gh, depot, Agents(), tmp_path).tour()
    assert any(m.get("etat") == "reprise" for m in marques(gh.prs_[50]["comments"]))
    assert _gestes(gh, "lancer_workflow")[-1][2]["essai"] == "0"


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
    # La fusion ne vaut que pour la révision relue.
    assert gh.tetes_fusionnees == ["a" * 40]


def test_une_pr_deja_fusionnable_est_fusionnee_tout_de_suite_a_la_revision_relue():
    # Mesuré le 28 septembre 2026 sur la PR #174 (lot #118) : relue ACCEPTE,
    # tous ses contrôles verts, GitHub refuse d'armer l'auto-fusion (« clean
    # status ») et le pilote échouait à chaque tour sans jamais fusionner.
    from atelier.github import GitHub
    appels = []

    def faux_gh(argv, entree):
        appels.append(argv[1:])
        if "--auto" in argv:
            return 1, "", "GraphQL: Pull request Pull request is in clean status (enablePullRequestAutoMerge)"
        return 0, "", ""

    GitHub("moi/essai", executeur=faux_gh).fusion_auto(174, "f" * 40)
    assert appels[-1] == ["pr", "merge", "174", "-R", "moi/essai", "--squash", "--match-head-commit", "f" * 40]
    assert "--match-head-commit" in appels[0]


def test_une_autre_erreur_de_fusion_n_est_pas_masquee():
    from atelier.github import GitHub, GitHubErreur
    refus = lambda argv, entree: (1, "", "GraphQL: Base branch was modified")  # noqa: E731
    with pytest.raises(GitHubErreur):
        GitHub("moi/essai", executeur=refus).fusion_auto(174, "f" * 40)


def test_l_auteur_claude_est_relu_par_codex(projet, gh, depot, tmp_path):
    fait_claude = marque(role="codeur", etat="fait", essai=1, agent="claude/opus", sha="a" * 40)
    _en_cours(gh, commentaires=[fait_claude])
    agents = Agents((0, "VERDICT: CORRIGER"))
    _pilote(projet, gh, depot, agents, tmp_path).tour()
    assert agents.outils() == ["codex"]
    assert not _gestes(gh, "fusion_auto")


def test_du_code_ecrit_par_cursor_claude_est_relu_par_codex(projet, gh, depot, tmp_path):
    # L'exclusion se fait par famille de modèle : du code écrit par
    # cursor/claude-opus ne se relit pas par claude/claude-opus.
    fait = marque(role="codeur_3d", etat="fait", essai=1, agent="cursor/opus-high", sha="a" * 40)
    _en_cours(gh, commentaires=[fait], etiquettes=("lot", "en-cours", "pc"))
    agents = Agents((0, "VERDICT: ACCEPTE"))
    _pilote(projet, gh, depot, agents, tmp_path).tour()
    assert agents.outils() == ["codex"]


def test_un_quota_claude_ne_retient_pas_le_chef(projet, gh, depot, tmp_path):
    gh.ajouter_issue(10, "Le service lit un lieu")
    agents = Agents((1, "Error: You've hit your usage limit"),
                    (0, "DECISION: BRIEF", {"docs/briefs/10-le-service-lit-un-lieu.md": BRIEF_BON}))
    lignes = _pilote(projet, gh, depot, agents, tmp_path).tour()
    assert agents.outils() == ["claude", "cursor-agent"]
    assert any("brief écrit" in l and "cursor/opus-high" in l for l in lignes)


def test_un_secours_qui_repond_laisse_au_journal_la_raison_du_refus(projet, gh, depot, tmp_path):
    gh.ajouter_issue(10, "Le service lit un lieu")
    agents = Agents((1, "You've hit your monthly spend limit · resets 5:50pm"),
                    (0, "DECISION: BRIEF", {"docs/briefs/10-le-service-lit-un-lieu.md": BRIEF_BON}))
    _pilote(projet, gh, depot, agents, tmp_path).tour()
    entrees = [json.loads(l) for l in (tmp_path / "journal.jsonl").read_text(encoding="utf-8").splitlines()]
    secours = [e for e in entrees if e["action"] == "secours"]
    assert secours and "monthly spend limit" in secours[0]["detail"] and secours[0]["lot"] == 10
    assert secours[0]["agent"] == "cursor/opus-high"


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


ENVOI_PC = marque(role="codeur_3d", etat="envoye", essai=1, quand="2026-09-27T13:40:10+00:00")
ECHEC_127 = marque(role="codeur_3d", etat="echec", essai=1, agent="cursor/opus-high")


def test_un_lot_pret_dont_la_pr_est_ouverte_est_repris_sans_le_chef(projet, gh, depot, tmp_path):
    # Le lot #118 : trois 127 l'ont bloqué, le propriétaire le remet « pret ».
    # Relancer le chef coûterait un quota et buterait sur la branche et la
    # PR qui existent déjà : le lot est REPRIS où il en est.
    gh.ajouter_issue(10, "Le service lit un lieu", ("lot", "pret", "pc"))
    gh.issues_[10]["comments"].append({"body": marque(role="pilote", etat="bloque", raison="le codeur a échoué 3 fois")})
    gh.ajouter_pr(50, BRANCHE, brouillon=True, commentaires=[ENVOI_PC, ECHEC_127] * 3)
    agents = Agents()
    lignes = _pilote(projet, gh, depot, agents, tmp_path).tour()
    assert agents.appels == [] and not _gestes(gh, "creer_pr")
    etiquettes = [e["name"] for e in gh.issues_[10]["labels"]]
    assert "en-cours" in etiquettes and "pret" not in etiquettes and "bloque" not in etiquettes
    assert any(m.get("etat") == "reprise" for m in marques(gh.prs_[50]["comments"]))
    envoi = _gestes(gh, "lancer_workflow")[0][2]
    assert (envoi["action"], envoi["essai"]) == ("coder", "0")
    assert any("repris" in l for l in lignes)


def test_le_message_de_blocage_dit_comment_reprendre(projet, gh, depot, tmp_path):
    _en_cours(gh, commentaires=[marque(role="codeur", etat="echec", essai=1, agent="codex/sol")] * 3)
    _pilote(projet, gh, depot, Agents(), tmp_path).tour()
    texte = gh.issues_[10]["comments"][-1]["body"]
    assert "remettre « pret »" in texte and "sans relancer le chef" in texte


def test_l_echec_du_codeur_dit_pourquoi_les_autres_ont_ete_ecartes(projet, gh, depot, tmp_path):
    _en_cours(gh)
    agents = Agents((1, "Error: You've hit your usage limit"), (2, "SyntaxError: invalid syntax"))
    _pilote(projet, gh, depot, agents, tmp_path).tour()
    commentaire = gh.prs_[50]["comments"][-1]["body"]
    assert "codex/sol : quota épuisé" in commentaire and "cursor/grok : code 2" in commentaire
    journal = (tmp_path / "journal.jsonl").read_text(encoding="utf-8")
    assert "quota épuisé" in journal


def test_un_binaire_introuvable_fait_attendre_sans_bruler_d_essai(projet, gh, depot, tmp_path):
    _en_cours(gh)
    agents = Agents((127, "binaire introuvable : codex"), (127, "binaire introuvable : cursor-agent"))
    lignes = _pilote(projet, gh, depot, agents, tmp_path).tour()
    assert gh.prs_[50]["comments"] == []
    assert any("attente" in l and "introuvable" in l for l in lignes)


def test_le_pc_en_attente_est_relance_apres_une_heure(projet, gh, depot, tmp_path):
    attente = marque(role="codeur_3d", etat="attente", quand="2026-09-28T07:30:00+00:00")
    _en_cours(gh, commentaires=[ENVOI_PC, attente], etiquettes=("lot", "en-cours", "pc"))
    _pilote(projet, gh, depot, Agents(), tmp_path).tour()      # 08:00 : trente minutes
    assert not _gestes(gh, "lancer_workflow")
    plus_tard = Pilote(projet, gh, depot, executeur_agents=Agents(), journal=tmp_path / "j.jsonl",
                       maintenant=lambda: datetime(2026, 9, 28, 8, 45, tzinfo=timezone.utc))
    plus_tard.tour()
    envoi = _gestes(gh, "lancer_workflow")[0][2]
    assert (envoi["action"], envoi["essai"]) == ("coder", "0")


def test_relancer_le_pc_renvoie_la_meme_action(projet, gh, depot, tmp_path):
    premier = marque(role="codeur_3d", etat="envoye", essai=1, action="coder", quand="2026-09-26T10:00:00+00:00")
    fait = marque(role="codeur_3d", etat="fait", essai=1, agent="claude/opus", sha="a" * 40)
    envoi = marque(role="codeur_3d", etat="envoye", essai=2, action="corriger_ci",
                   quand="2026-09-27T06:00:00+00:00")
    _en_cours(gh, commentaires=[premier, fait, envoi], ci="rouge", etiquettes=("lot", "en-cours", "pc"))
    _pilote(projet, gh, depot, Agents(), tmp_path).tour()
    assert _gestes(gh, "lancer_workflow")[0][2]["action"] == "corriger_ci"


def test_a_sec_une_reprise_est_suivie_de_ce_qu_elle_declenche(projet, tmp_path, capsys):
    # Le tour à sec lit le vrai GitHub : sans relire ses propres gestes, il
    # annonçait « bloqué » juste après avoir repris le lot.
    from atelier.asec import DepotASec, GitHubASec, executeur_a_sec
    issue = {"number": 10, "title": "Le service lit un lieu", "body": "", "state": "OPEN", "comments": [],
             "labels": [{"name": n} for n in ("lot", "pret", "pc")], "milestone": {"title": "J1 — Le pont"}}
    rollup = [{"__typename": "CheckRun", "name": n, "status": "COMPLETED", "conclusion": "SUCCESS",
               "startedAt": "2026-09-27T10:00:00Z"} for n in ("tests", "gitleaks")]
    pr = {"number": 50, "state": "OPEN", "headRefName": BRANCHE, "headRefOid": "a" * 40, "isDraft": True,
          "mergeable": "MERGEABLE", "statusCheckRollup": rollup, "mergedAt": None, "autoMergeRequest": None,
          "comments": [{"body": c} for c in [ENVOI_PC, ECHEC_127] * 3], "url": "https://x/pull/50", "title": "x"}

    def faux_gh(argv, entree):
        args = argv[1:]
        if args[:2] == ["issue", "list"]:
            return 0, json.dumps([issue] if args[args.index("--state") + 1] == "open" else []), ""
        if args[:2] == ["issue", "view"]:
            return 0, json.dumps(issue), ""
        if args[:2] in (["pr", "list"], ["pr", "view"]):
            return 0, json.dumps(pr if args[1] == "view" else [pr]), ""
        if args[0] == "api":
            return 0, json.dumps([{"number": 1, "title": "J1 — Le pont", "state": "open",
                                   "open_issues": 1, "closed_issues": 0}]), ""
        return 0, "[]", ""

    pilote = Pilote(projet, GitHubASec("moi/essai", executeur=faux_gh), DepotASec(tmp_path, "master"),
                    executeur_agents=executeur_a_sec, journal=tmp_path / "j.jsonl",
                    maintenant=lambda: datetime(2026, 9, 28, 8, 0, tzinfo=timezone.utc))
    pilote.tour()
    dit = capsys.readouterr().out
    assert "lot repris" in dit and "lancer lot-pc.yml" in dit
    assert "+['bloque']" not in dit


def test_un_jalon_sans_lot_ouvert_est_atteint(projet, gh, depot, tmp_path):
    gh.jalons_[0].update(open_issues=0, closed_issues=4)
    _pilote(projet, gh, depot, Agents(), tmp_path).tour()
    assert ("fermer_jalon", 1) in gh.gestes


def test_rien_a_faire_se_dit(projet, gh, depot, tmp_path):
    assert _pilote(projet, gh, depot, Agents(), tmp_path).tour() == ["RIEN"]


CAP_NEUF = """# CAP

## Jalon 1 — Le pont

## Jalon 2 — Le monde de 1400

## Jalon 3 — Le lieu et son maître

## La réserve
"""


def _ecrire_cap(projet, texte=CAP_NEUF):
    (projet.racine / "CAP.md").write_text(texte, encoding="utf-8")


def _etiquettes(gh, numero):
    return {e["name"] for e in gh.issues_[numero]["labels"]}


def test_les_jalons_suivent_cap_et_le_jalon_qui_commence_se_fait_decouper(projet, gh, depot, tmp_path):
    _ecrire_cap(projet)
    gh.jalons_[0]["state"] = "closed"  # le pont est atteint : J2 devient le jalon courant
    _pilote(projet, gh, depot, Agents(), tmp_path).tour()
    assert [j["title"] for j in gh.jalons_] == ["J1 — Le pont", "J2 — Le monde de 1400",
                                                "J3 — Le lieu et son maître", "Réserve"]
    (decoupe,) = [i for i in gh.issues_.values() if i["title"].startswith("Découper le jalon")]
    assert decoupe["title"] == "Découper le jalon J2 — Le monde de 1400"
    assert decoupe["milestone"]["title"] == "J2 — Le monde de 1400"
    assert _etiquettes(gh, decoupe["number"]) == {"lot", "pret"}


def test_le_chef_decoupe_le_jalon_et_chaque_sous_lot_dit_sa_machine(projet, gh, depot, tmp_path):
    _ecrire_cap(projet)
    gh.jalons_[0]["state"] = "closed"
    _pilote(projet, gh, depot, Agents(), tmp_path).tour()
    texte = ("DECISION: DECOUPE\n- La table de 1400 :: les sources publiques, citées\n"
             "- La carte de 1400 :: Unity montre les royaumes :: pc\n")
    _pilote(projet, gh, depot, Agents((0, texte)), tmp_path).tour()
    decoupe, table, carte = 101, 102, 103
    assert gh.issues_[decoupe]["state"] == "CLOSED"
    assert "pc" not in _etiquettes(gh, table) and "pc" in _etiquettes(gh, carte)
    assert gh.issues_[carte]["body"].startswith("Unity montre les royaumes\n")
    assert Lot.de(gh.issues_[carte]).dependances == frozenset({table})
    # Découpé une fois : le tour suivant ne rouvre pas de découpe.
    agents = Agents((0, "DECISION: BRIEF", {"docs/briefs/102-la-table-de-1400.md": BRIEF_BON}))
    _pilote(projet, gh, depot, agents, tmp_path).tour()
    assert len([i for i in gh.issues_.values() if i["title"].startswith("Découper le jalon")]) == 1


def test_un_jalon_deja_lance_ne_se_decoupe_pas(projet, gh, depot, tmp_path):
    _ecrire_cap(projet)
    gh.ajouter_issue(9, "Le contrat parle en cell_id", ("lot", "livre"), etat="CLOSED")
    _pilote(projet, gh, depot, Agents(), tmp_path).tour()
    assert not [i for i in gh.issues_.values() if i["title"].startswith("Découper le jalon J1")]
    # J1 n'a plus rien à prendre : c'est le jalon suivant qui se découpe, en avance.
    assert [i["title"] for i in gh.issues_.values() if i["title"].startswith("Découper le jalon")] == [
        "Découper le jalon J2 — Le monde de 1400"]


def test_la_decoupe_d_un_jalon_passe_apres_ses_lots_deja_ouverts(projet, gh, depot, tmp_path):
    gh.ajouter_issue(20, "La cellule se peuple de lieux", ("lot", "idee"), "J2 — Le geste revient")
    gh.ajouter_issue(21, "Un lot bloqué", ("lot", "bloque"), "J2 — Le geste revient")
    j2 = lots.jalons(gh.jalons_)[1]
    _pilote(projet, gh, depot, Agents(), tmp_path)._faire_decouper(j2, [Lot.de(i) for i in gh.issues("open")])
    decoupe = Lot.de(gh.issues_[101])
    assert decoupe.dependances == frozenset({20}) and decoupe.etat == "pret" and decoupe.jalon == 2


def test_l_etiquette_reserve_range_le_lot_et_le_formulaire_ne_le_rappelle_pas(projet, gh, depot, tmp_path):
    _ecrire_cap(projet)
    gh.ajouter_issue(9, "Le contrat parle en cell_id", ("lot", "livre"), etat="CLOSED")
    gh.ajouter_issue(30, "Audio de ville", ("lot", "idee", "reserve"), "J2 — Le geste revient")
    gh.ajouter_issue(31, "Venu du formulaire", ("lot", "idee"), "Réserve",
                     corps="### Jalon\n\nJ2 — Le monde de 1400")
    gh.ajouter_issue(32, "Rangé d'emblée", ("lot",), None, corps="### Jalon\n\nRéserve")
    _pilote(projet, gh, depot, Agents(), tmp_path).tour()
    assert gh.issues_[30]["milestone"]["title"] == "Réserve" and "reserve" not in _etiquettes(gh, 30)
    assert gh.issues_[31]["milestone"]["title"] == "Réserve"
    assert gh.issues_[32]["milestone"]["title"] == "Réserve"


def test_sans_reserve_dans_cap_l_etiquette_attend(projet, gh, depot, tmp_path):
    gh.ajouter_issue(30, "Audio de ville", ("lot", "idee", "reserve"), "J2 — Le geste revient")
    _pilote(projet, gh, depot, Agents(), tmp_path).tour()
    assert gh.issues_[30]["milestone"]["title"] == "J2 — Le geste revient" and "reserve" in _etiquettes(gh, 30)
    assert not _gestes(gh, "creer_jalon")


# La fenêtre de deux jalons. Le 29 septembre 2026, J1 n'avait plus que des
# lots « pc » (#120 en cours, #121 qui l'attend) : le VPS ne faisait rien
# pendant que le PC finissait, alors que J2 ne demande que `sim/`.

def _j1_occupe_le_pc(gh):
    """J1 n'a plus qu'un lot « pc », en cours, dont le travail est parti sur le PC."""
    _en_cours(gh, commentaires=[ENVOI_PC], etiquettes=("lot", "en-cours", "pc"))


def _brief_du_lot(numero, titre):
    return {f"docs/briefs/{numero}-{lots.slug(titre)}.md": BRIEF_BON}


def test_le_vps_sans_travail_dans_le_jalon_courant_prend_dans_le_suivant(projet, gh, depot, tmp_path):
    _j1_occupe_le_pc(gh)
    gh.ajouter_issue(40, "La table de 1400", ("lot", "pret"), "J2 — Le geste revient")
    agents = Agents((0, "DECISION: BRIEF", _brief_du_lot(40, "La table de 1400")))
    _pilote(projet, gh, depot, agents, tmp_path).tour()
    assert _gestes(gh, "creer_pr")[0][1:] == ("lot/40-la-table-de-1400", "Lot #40 — La table de 1400")
    pr = gh.prs_[max(gh.prs_)]
    assert "Jalon : J2 — Le geste revient" in pr["body"]
    prompt = agents.appels[0][2]
    assert "pris en avance" in prompt and "J1 — Le pont" in prompt


def test_le_jalon_courant_passe_avant_le_suivant(projet, gh, depot, tmp_path):
    # Contre-épreuve : le VPS a encore un lot dans J1, il le prend, et son
    # chef ne se croit pas en avance.
    _j1_occupe_le_pc(gh)
    gh.ajouter_issue(11, "Le panneau lit l'horloge", ("lot", "idee"))
    gh.ajouter_issue(40, "La table de 1400", ("lot", "pret"), "J2 — Le geste revient")
    agents = Agents((0, "DECISION: BRIEF", _brief_du_lot(11, "Le panneau lit l'horloge")))
    _pilote(projet, gh, depot, agents, tmp_path).tour()
    assert _gestes(gh, "creer_pr")[0][2] == "Lot #11 — Le panneau lit l'horloge"
    assert "pris en avance" not in agents.appels[0][2]


def test_la_fenetre_s_arrete_au_jalon_suivant(projet, gh, depot, tmp_path):
    _j1_occupe_le_pc(gh)
    gh.jalons_.append({"number": 3, "title": "J3 — Le lieu et son maître", "state": "open",
                       "open_issues": 1, "closed_issues": 0})
    gh.ajouter_issue(60, "La cellule se peuple de lieux", ("lot", "pret"), "J3 — Le lieu et son maître")
    agents = Agents()
    _pilote(projet, gh, depot, agents, tmp_path).tour()
    assert agents.appels == [] and not _gestes(gh, "creer_pr")


def test_le_jalon_suivant_sans_lot_se_decoupe_en_avance(projet, gh, depot, tmp_path):
    _ecrire_cap(projet)
    gh.ajouter_issue(9, "Le contrat parle en cell_id", ("lot", "livre"), etat="CLOSED")
    _j1_occupe_le_pc(gh)
    _pilote(projet, gh, depot, Agents(), tmp_path).tour()
    (decoupe,) = [i for i in gh.issues_.values() if i["title"].startswith("Découper le jalon")]
    assert decoupe["title"] == "Découper le jalon J2 — Le monde de 1400"
    assert "en avance" in decoupe["body"] and "J1 — Le pont" in decoupe["body"]
    assert lots.jalon_a_decouper_par(Lot.de(decoupe)) == 2
    # Le VPS la prend au tour suivant, et la découpe ne se refait pas.
    texte = "DECISION: DECOUPE\n- La table de 1400 :: les sources publiques, citées\n"
    agents = Agents((0, texte))
    _pilote(projet, gh, depot, agents, tmp_path).tour()
    assert "pris en avance" in agents.appels[0][2]
    assert gh.issues_[decoupe["number"]]["state"] == "CLOSED"
    (table,) = [i for i in gh.issues_.values() if i["title"] == "La table de 1400"]
    assert table["milestone"]["title"] == "J2 — Le monde de 1400"


def test_une_machine_occupee_n_ouvre_pas_la_fenetre(projet, gh, depot, tmp_path):
    # Le PC et le VPS ont chacun leur lot en cours : rien ne se découpe en
    # avance, rien ne se prend.
    _ecrire_cap(projet)
    _j1_occupe_le_pc(gh)
    gh.ajouter_issue(12, "Le service compte ses ticks", ("lot", "en-cours"))
    gh.ajouter_pr(52, "lot/12-le-service-compte-ses-ticks", ci="attente", commentaires=[FAIT_CODEX])
    agents = Agents()
    _pilote(projet, gh, depot, agents, tmp_path).tour()
    assert not [i for i in gh.issues_.values() if i["title"].startswith("Découper le jalon")]
    assert not _gestes(gh, "creer_pr")
