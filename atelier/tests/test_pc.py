"""Le côté PC d'un lot « machine : pc » : ce qu'il répond au pilote du VPS,
et ce que les workflows du PC donnent au service qui le fait tourner."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import re

import pytest

from atelier import lots, pc
from atelier.depot import DepotErreur
from atelier.lots import marque, marques
from atelier.pilote import Pilote

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


def _marquer_attente(projet, gh, monkeypatch, raison="le passage du PC est tombé"):
    from atelier import __main__ as cli
    monkeypatch.setattr(cli, "GitHub", lambda depot: gh)
    return cli.main(["--projet", str(projet.racine), "marquer-attente", "--pr", "174", "--raison", raison])


def test_un_passage_tombe_hors_de_python_est_renvoye_dans_l_heure(projet, gh, depot, monkeypatch):
    # Le 16 octobre 2026, le runner du PC a perdu GitHub au milieu de #654
    # (run 38864468926) : aucune marque, et toute la file PC de J3 a attendu
    # 24 h. lot-pc.yml répond alors à la place du passage tombé.
    envoi = datetime.now(timezone.utc) - timedelta(minutes=20)
    gh.ajouter_issue(118, "Le contrat ville parle en cell_id", ("lot", "en-cours", "pc"))
    gh.ajouter_pr(174, BRANCHE, brouillon=True, commentaires=[
        marque(role="codeur_3d", etat="envoye", essai=1, action="coder", quand=envoi.isoformat(timespec="seconds"))])
    assert _marquer_attente(projet, gh, monkeypatch, "le runner a perdu GitHub (failure)") == 0
    liste = marques(gh.prs_[174]["comments"])
    assert (liste[-1]["role"], liste[-1]["etat"]) == ("codeur_3d", "attente") and liste[-1]["quand"]
    assert "le runner a perdu GitHub (failure)" in gh.prs_[174]["comments"][-1]["body"]

    attente = datetime.fromisoformat(liste[-1]["quand"])

    def action(marques_, heures_apres_l_attente):
        plus_tard = Pilote(projet, gh, depot, maintenant=lambda: attente + timedelta(hours=heures_apres_l_attente))
        return lots.action_suivante(gh.prs_[174], "vert", marques_, corrections_max=2, role_codeur="codeur_3d",
                                    heures_depuis_envoi_pc=plus_tard._heures_depuis(marques_, "codeur_3d", "envoye"),
                                    heures_depuis_attente_pc=plus_tard._heures_depuis(marques_, "codeur_3d", "attente")).nom

    avant, apres = lots.HEURES_ATTENTE_PC - 0.1, lots.HEURES_ATTENTE_PC + 0.1
    assert action(liste, avant) == "attendre_pc"
    assert action(liste, apres) == "coder", "renvoyé au bout d'une heure, sans compter d'essai"
    # Sans la marque, le pilote attendait le silence de 24 h.
    assert action(liste[:-1], apres) == "attendre_pc"
    assert action(liste[:-1], lots.HEURES_SILENCE_PC) == "relancer_pc"


@pytest.mark.parametrize("reponse", ["attente", "fait", "echec"])
def test_le_workflow_ne_repond_pas_par_dessus_le_pc(projet, gh, monkeypatch, capsys, reponse):
    # Ce qui casse en Python, `travailler` le marque lui-même ; un passage
    # qui a répondu puis cassé garde sa réponse.
    _lot_pc(gh)
    gh.prs_[174]["comments"].append({"body": marque(role="codeur_3d", etat=reponse,
                                                    quand="2026-09-28T07:58:00+00:00")})
    assert _marquer_attente(projet, gh, monkeypatch) == 0
    assert len(gh.prs_[174]["comments"]) == 2
    assert capsys.readouterr().out.startswith("RIEN")


def _travaux(workflow: str) -> dict[str, str]:
    """Les travaux d'un workflow, nom → bloc de texte (la CI de la chaîne n'a pas PyYAML)."""
    texte = (RACINE / ".github" / "workflows" / workflow).read_text(encoding="utf-8")
    blocs = re.split(r"^  ([\w-]+):\n", texte.split("\njobs:\n", 1)[1], flags=re.M)
    return dict(zip(blocs[1::2], blocs[2::2]))


def test_lot_pc_repond_quand_le_passage_tombe_hors_de_python():
    # Le run 38864468926 : « The self-hosted runner lost communication with
    # the server ». Une étape du travail `lot` ne tourne pas quand le runner
    # est tombé ; un travail à part attend son retour, puis répond.
    travaux = _travaux("lot-pc.yml")
    repondre = [bloc for nom, bloc in travaux.items() if "marquer-attente" in bloc]
    assert len(repondre) == 1 and "marquer-attente" not in travaux["lot"]
    bloc = repondre[0]
    assert re.search(r"^    needs: lot$", bloc, re.M)
    assert "if: ${{ always() && needs.lot.result != 'success' }}" in bloc, "échec, annulation et délai dépassé"
    assert "runs-on: [self-hosted, Windows, unity]" in bloc, "le gh de la session du propriétaire"
    assert re.search(r"marquer-attente --pr \$env:PR\b", bloc) and "PR: ${{ inputs.pr }}" in bloc
    assert "secrets." not in bloc and "GH_TOKEN" not in bloc


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


def test_la_capture_passe_les_drapeaux_du_brief_a_unity(tmp_path, monkeypatch):
    vus = []
    monkeypatch.setattr(pc, "unity_de", lambda projet: Path("Unity.exe"))
    monkeypatch.setattr(pc.subprocess, "run", lambda argv, **kw: vus.append(argv) or pc.subprocess.CompletedProcess(argv, 0))
    pc.compiler_et_photographier(tmp_path, tmp_path / "sortie", lot=781, drapeaux=("-forgeTicks", "0", "-forgeServiceEpreuve"))
    assert vus[0][-3:] == ["-forgeTicks", "0", "-forgeServiceEpreuve"]


# La forme du brief de #781 : un tableau PowerShell, puis deux sessions qui le reprennent.
BRIEF_781 = r"""## Conditions de succès
```powershell
$unity = 'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'
$commun = @('-batchmode','-projectPath','3d/unity','-executeMethod','ForgeLocal3D.Capture.Photographier','-forgeLot','781','-forgeSeed','0','-forgeTicks','0','-forgeServiceEpreuve')
```
`NORMAL` : `& $unity @commun -forgeCaptures $normal -logFile "$normal.log"`.
`CONTRE` : `& $unity @commun -forgeGarderEtalPlein -forgeCaptures $contre -logFile "$contre.log"`.
Réutiliser `Capture.Photographier` et son service.
"""


def test_les_sessions_de_capture_se_lisent_dans_le_brief():
    # Le 22 octobre 2026, #781 s'est bloqué : le PC photographiait sans
    # `-forgeServiceEpreuve`, et sa contre-épreuve n'était jamais jouée.
    assert pc.sessions_de_capture(BRIEF_781, 781) == [
        ("-forgeSeed", "0", "-forgeTicks", "0", "-forgeServiceEpreuve"),
        ("-forgeSeed", "0", "-forgeTicks", "0", "-forgeServiceEpreuve", "-forgeGarderEtalPlein")]
    assert pc.sessions_de_capture(BRIEF_781, 780) == [], "les sessions d'un autre lot ne se jouent pas"
    en_ligne = ("SC4 — Commande : `Unity.exe -batchmode -projectPath 3d/unity -executeMethod "
                "ForgeLocal3D.Capture.Photographier -forgeLot 626 -forgeSeed 0 -forgeTicks 3 -forge626RetirerRepere "
                "-forgeCaptures \"$env:TEMP\\lot626-manque\"`, puis la même sans le retrait : `Unity.exe -batchmode "
                "-executeMethod ForgeLocal3D.Capture.Photographier -forgeTicks 3 -forgeLot 626 -forgeSeed 0`.")
    assert pc.sessions_de_capture(en_ligne, 626) == [("-forgeTicks", "3", "-forgeSeed", "0"),
                                                     ("-forgeSeed", "0", "-forgeTicks", "3", "-forge626RetirerRepere")]
    a_remplir = "`Unity.exe -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 5 -forgeCell <cellule>`"
    assert pc.sessions_de_capture(a_remplir, 5) == [], "une valeur à remplir ne se rejoue pas"
    assert pc.sessions_de_capture("`Unity.exe -executeMethod ForgeLocal3D.Capture.Photographier -forgeLot 5`", 5) == [()]


class _UnityDesSessions:
    """Unity dicté, session par session : les drapeaux reçus, et ce que chaque
    session écrit (photos de scénario, rapport, traces)."""

    def __init__(self, ok=(True, True)):
        self.ok, self.drapeaux = list(ok), []

    def __call__(self, chantier: Path, sortie: Path, *, lot=None, drapeaux=(), **_):
        n = len(self.drapeaux)
        self.drapeaux.append(drapeaux)
        sortie.mkdir(parents=True, exist_ok=True)
        (sortie / "desert.png").write_bytes(b"plan fixe")
        for nom in ("01-place-nourrie", "02-place-affamee"):
            (sortie / f"desert--{nom}.png").write_bytes(b"photo")
            (sortie / f"desert--{nom}.ecart.txt").write_text("0.3", encoding="utf-8")
        (sortie / "vie-bourg.json").write_text('{"contre_epreuve": %s}' % ("true" if n else "false"), encoding="utf-8")
        (sortie / "unity.log").write_text(f"bruit\nCAPTURE_SCENARIO_OK desert--02-place-affamee.png session {n}\n",
                                          encoding="utf-8")
        return self.ok[n], sorted(sortie.glob("*.png")), "POST /epreuve/vider-panier?cell=10103 a rendu 404"


def test_le_pc_joue_la_photo_puis_la_contre_epreuve_du_brief(tmp_path):
    unity, publiees = _UnityDesSessions(), []
    vu = pc.regarder_avec_unity(tmp_path, 781, "c" * 40, "2026-10-24", unity=unity, brief=BRIEF_781,
                                publier=lambda fichiers, jour: publiees.extend(f.name for f in fichiers) or ["u"])
    assert unity.drapeaux == pc.sessions_de_capture(BRIEF_781, 781)
    assert vu.marque == {"unity": "vert", "photo": "propre"}
    assert "`-forgeSeed 0 -forgeTicks 0 -forgeServiceEpreuve`, comme l'écrit le brief" in vu.note
    assert "Contre-épreuve** `-forgeSeed 0 -forgeTicks 0 -forgeServiceEpreuve -forgeGarderEtalPlein` : Unity a fini" in vu.note
    assert '{"contre_epreuve": false}' in vu.note and '{"contre_epreuve": true}' in vu.note, "les deux rapports"
    assert "CAPTURE_SCENARIO_OK desert--02-place-affamee.png session 1" in vu.note and "bruit" not in vu.note
    assert len(publiees) == 6 and sum("-contre1-" in n for n in publiees) == 3


def test_une_capture_qui_echoue_apres_la_compilation_ne_se_dit_pas_erreur_de_compilation(tmp_path):
    vu = pc.regarder_avec_unity(tmp_path, 781, "c" * 40, "2026-10-24", unity=_UnityDesSessions(ok=(False,)),
                                publier=lambda fichiers, jour: [])
    assert vu.marque == {"unity": "rouge"}
    assert "mais la capture n'a pas abouti" in vu.note and "ne compile pas" not in vu.note
    assert "a rendu 404" in vu.note and "Contre-épreuve" not in vu.note, "sans brief, une seule session"


def test_le_passage_du_pc_lit_la_capture_dans_le_brief_de_la_branche(projet, gh, depot, monkeypatch):
    _lot_pc(gh)
    monkeypatch.setattr(depot, "enregistrer", lambda chemin, message: "b" * 40)  # le chantier garde ses fichiers
    unity = _UnityDesSessions()
    brief = BRIEF_781.replace("'781'", "'118'")
    agents = Agents((0, "Fait.", {"docs/briefs/118-le-contrat-ville-parle-en-cell-id.md": brief,
                                  "3d/unity/Assets/X.cs": "code"}))
    _travailler(projet, gh, depot, agents, unity)
    assert unity.drapeaux == pc.sessions_de_capture(brief, 118) and len(unity.drapeaux) == 2
