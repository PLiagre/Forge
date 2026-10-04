"""Le côté PC d'un lot « machine : pc » : ce qu'il répond au pilote du VPS,
et ce que les workflows du PC donnent au service qui le fait tourner."""

from __future__ import annotations

from pathlib import Path

import pytest

from atelier import pc
from atelier.depot import DepotErreur
from atelier.lots import marque, marques

from conftest import RACINE, Agents

BRANCHE = "lot/118-le-contrat-ville-parle-en-cell-id"
ENVOI = marque(role="codeur_3d", etat="envoye", essai=1, action="coder", quand="2026-09-28T07:40:00+00:00")


def _lot_pc(gh):
    gh.ajouter_issue(118, "Le contrat ville parle en cell_id", ("lot", "en-cours", "pc"))
    return gh.ajouter_pr(174, BRANCHE, brouillon=True, commentaires=[ENVOI])


class _Unity:
    """Unity en batch, dicté : compile ou non, et rend une image."""

    def __init__(self, ok=True, fin=""):
        self.ok, self.fin, self.appels = ok, fin, 0

    def __call__(self, chantier: Path, sortie: Path, **_):
        self.appels += 1
        sortie.mkdir(parents=True, exist_ok=True)
        image = sortie / "desert.png"
        image.write_bytes(b"png")
        return self.ok, [image], self.fin


def _travailler(projet, gh, depot, agents, unity, publier=lambda *a: []):
    return pc.travailler(projet, gh, depot, issue=118, branche=BRANCHE, pr=174, essai=0, action="coder",
                         executeur_agents=agents, unity=unity, publier=publier)


def test_le_pc_sans_agent_marque_l_attente_et_ne_lance_pas_unity(projet, gh, depot):
    # Tous les agents du PC en attente : sans marque, le pilote attendait
    # 24 h avant de renvoyer. La marque d'attente ne compte pas comme essai.
    _lot_pc(gh)
    unity = _Unity()
    agents = Agents((1, "You've hit your usage limit"), (127, "binaire introuvable : cursor-agent"))
    _travailler(projet, gh, depot, agents, unity)
    derniere = marques(gh.prs_[174]["comments"])[-1]
    assert (derniere["role"], derniere["etat"]) == ("codeur_3d", "attente") and derniere["quand"]
    corps = gh.prs_[174]["comments"][-1]["body"]
    assert "quota épuisé" in corps and "introuvable" in corps
    assert unity.appels == 0


def test_le_pc_joint_le_verdict_d_unity_au_compte_rendu_du_codeur(projet, gh, depot):
    # Le relecteur, sur le VPS, ne peut pas lancer Unity : il lit ce que le
    # PC a mesuré dans le compte rendu du codeur, sur la même révision.
    _lot_pc(gh)
    unity = _Unity(ok=False, fin="Assets/X.cs(3,1): error CS1002: ; expected")
    agents = Agents((0, "Contrat en cell_id.", {"3d/unity/Assets/X.cs": "code"}))
    _travailler(projet, gh, depot, agents, unity, publier=lambda *a: ["https://raw.example/desert.png"])
    assert len(gh.prs_[174]["comments"]) == 2
    corps = gh.prs_[174]["comments"][-1]["body"]
    m = marques([{"body": corps}])[0]
    assert (m["etat"], m["unity"], m["sha"]) == ("fait", "rouge", "b" * 40)
    assert "error CS1002" in corps and "https://raw.example/desert.png" in corps


def test_le_pc_qui_casse_avant_l_agent_marque_l_attente(projet, gh, depot):
    _lot_pc(gh)

    def casse(nom, branche):
        raise DepotErreur("git worktree add : un verrou traîne")

    depot.preparer = casse
    with pytest.raises(DepotErreur):
        _travailler(projet, gh, depot, Agents(), _Unity())
    derniere = marques(gh.prs_[174]["comments"])[-1]
    assert derniere["etat"] == "attente"
    assert "un verrou traîne" in gh.prs_[174]["comments"][-1]["body"]


def test_les_workflows_du_pc_mettent_les_agents_au_path():
    # Le service ne voit pas le PATH de la session. cursor-agent vit dans
    # %LOCALAPPDATA%\cursor-agent : absent du PATH, trois 127 le 27 septembre.
    for nom in ("lot-pc.yml", "sonde-pc.yml"):
        texte = (RACINE / ".github" / "workflows" / nom).read_text(encoding="utf-8")
        ligne = next(l for l in texte.splitlines() if "$env:PATH =" in l)
        for dossier in (r"$env:USERPROFILE\.local\bin", r"$env:APPDATA\npm", r"$env:LOCALAPPDATA\cursor-agent"):
            assert dossier in ligne, (nom, dossier)


def test_aucun_travail_du_pc_ne_peut_en_annuler_un_autre():
    # Un groupe de concurrence n'admet qu'un travail en attente : le build de
    # la nuit, en file pendant que le PC dort, annulait l'envoi d'un lot, et
    # le pilote attendait 24 h une réponse qui ne viendrait pas. Le runner
    # unique enchaîne déjà les travaux un par un.
    for nom in ("lot-pc.yml", "sonde-pc.yml", "build-nuit.yml"):
        texte = (RACINE / ".github" / "workflows" / nom).read_text(encoding="utf-8")
        assert "\nconcurrency:" not in texte, nom


class _UnityQuiPhotographie:
    """Unity dicté : le plan fixe, et les photos des scénarios du lot."""

    def __init__(self, scenarios=None):
        self.scenarios, self.lots = scenarios or {}, []

    def __call__(self, chantier: Path, sortie: Path, *, lot=None, **_):
        self.lots.append(lot)
        sortie.mkdir(parents=True, exist_ok=True)
        (sortie / "desert.png").write_bytes(b"plan fixe")
        for nom, ecart in self.scenarios.items():
            (sortie / f"desert--{nom}.png").write_bytes(b"photo")
            if ecart is not None:
                (sortie / f"desert--{nom}.ecart.txt").write_text(str(ecart), encoding="utf-8")
        return True, sorted(sortie.glob("*.png")), ""


@pytest.mark.parametrize("scenarios, photo, dit", [
    ({}, "absente", "aucune photo propre au lot"),
    ({"route": 0.004}, "identique", "« route » (0.4% des pixels changés)"),
    ({"route": None}, "identique", "« route » (écart non mesuré)"),
    ({"route": 0.31}, "propre", "propre au lot, « route » (31% des pixels changés)"),
])
def test_le_pc_dit_si_la_photo_est_propre_au_lot(projet, gh, depot, scenarios, photo, dit):
    # Du 30 septembre au 3 octobre 2026, treize captures de lots Unity étaient
    # le même plan fixe à l'octet près.
    _lot_pc(gh)
    unity = _UnityQuiPhotographie(scenarios)
    _travailler(projet, gh, depot, Agents((0, "Fait.", {"3d/unity/Assets/X.cs": "code"})), unity)
    assert unity.lots == [118], "Unity joue les scénarios du lot"
    corps = gh.prs_[174]["comments"][-1]["body"]
    assert marques([{"body": corps}])[0]["photo"] == photo and dit in corps


def test_la_capture_passe_le_lot_a_unity(tmp_path, monkeypatch):
    vus = []
    monkeypatch.setattr(pc, "unity_de", lambda projet: Path("Unity.exe"))
    monkeypatch.setattr(pc.subprocess, "run", lambda argv, **kw: vus.append(argv) or pc.subprocess.CompletedProcess(argv, 0))
    pc.compiler_et_photographier(tmp_path, tmp_path / "sortie", lot=235)
    assert vus[0][vus[0].index("-forgeLot") + 1] == "235"
