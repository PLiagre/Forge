"""Les doublures des tests de la chaîne : un GitHub en mémoire, un dépôt qui
ne touche à rien, des agents qui rendent ce qu'on leur dicte.

Aucun test ne parle au vrai GitHub, n'invoque un vrai agent, ni n'écrit dans
le vrai `~/.atelier` : le dossier personnel est remplacé par un dossier
temporaire pour chaque test.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import pytest

RACINE = Path(__file__).resolve().parents[2]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

from atelier import agents as agents_mod  # noqa: E402
from atelier.depot import Depot  # noqa: E402
from atelier.github import GitHub  # noqa: E402
from atelier.pilote import Photos, Pilote  # noqa: E402
from atelier.projet import charger  # noqa: E402

TOML = """
[projet]
nom = "Essai"
depot = "moi/essai"
branche_base = "master"
prefixe_branche = "lot/"
proprietaire = "moi"
interdits = ["atelier/", ".github/", "atelier.toml"]
coeur = ["jeu/sim/engine.py"]
pistes = ["monde", "ville", "interface"]
corrections_max = 2
coupures_max = 3
deblocages_max = 2

[agents]
cto         = "claude/fable@high"
chef        = "claude/opus@high"
developpeur = "claude/sonnet@high"
relecteur   = "claude/opus@high"
lecteur     = "claude/haiku@medium"
"""

PALIER = "Palier 1 — La première guerre"
MAINTENANT = datetime(2026, 11, 16, 10, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def sans_le_vrai_dossier_personnel(tmp_path, monkeypatch):
    """Aucun test n'écrit dans le vrai `~/.atelier` : ni journal, ni trace
    d'appel, ni verrou. Le dossier personnel est un dossier du test."""
    chez_soi = tmp_path / "chez-soi"
    chez_soi.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: chez_soi))
    for variable in ("ATELIER_JOURNAL", "ATELIER_APPELS", "ATELIER_VERROUS", "ATELIER_PROJET"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setattr(agents_mod, "FICHIER_JETON_CLAUDE", chez_soi / ".atelier" / "claude.token")
    return chez_soi


@pytest.fixture
def projet(tmp_path):
    (tmp_path / "atelier.toml").write_text(TOML, encoding="utf-8")
    return charger(tmp_path)


@dataclass
class FauxGitHub(GitHub):
    """Un GitHub en mémoire : issues, jalons, PR et commentaires."""

    depot: str = "moi/essai"
    issues_: dict[int, dict] = field(default_factory=dict)
    jalons_: list[dict] = field(default_factory=list)
    prs_: dict[int, dict] = field(default_factory=dict)
    gestes: list[tuple] = field(default_factory=list)
    tetes_fusionnees: list = field(default_factory=list)
    variables_: dict[str, str] = field(default_factory=dict)
    travaux_: dict[str, dict[str, str]] = field(default_factory=dict)
    etapes_: dict[int, list[dict]] = field(default_factory=dict)
    run_master: dict = field(default_factory=lambda: {"status": "completed", "conclusion": "success",
                                                      "databaseId": 1, "url": "https://x/run/1"})
    table_ci: str = ""
    suivant: int = 100

    def __post_init__(self):
        GitHub.__init__(self, self.depot, executeur=lambda argv, entree: (1, "", "pas de vrai gh ici"))

    # issues
    def ajouter_issue(self, numero, titre, etiquettes=("lot", "pret", "monde"), jalon=PALIER, corps="", etat="OPEN"):
        self.issues_[numero] = {"number": numero, "title": titre, "body": corps, "state": etat,
                                "labels": [{"name": e} for e in etiquettes],
                                "milestone": {"title": jalon} if jalon else None, "comments": []}
        return self.issues_[numero]

    def commentaire_humain(self, numero, texte, auteur="moi"):
        self.issues_[numero]["comments"].append({"body": texte, "author": {"login": auteur},
                                                 "createdAt": MAINTENANT.isoformat()})

    def issues(self, etat="open"):
        voulu = "OPEN" if etat == "open" else "CLOSED"
        return [dict(i) for i in self.issues_.values() if i["state"] == voulu]

    def issue(self, numero):
        return self.issues_[numero]

    def creer_issue(self, titre, corps, etiquettes=(), jalon=None):
        self.suivant += 1
        self.ajouter_issue(self.suivant, titre, tuple(etiquettes), jalon, corps)
        self.gestes.append(("creer_issue", titre))
        return self.suivant

    def commenter_issue(self, numero, texte):
        self.issues_[numero]["comments"].append({"body": texte, "author": {"login": "pilote"},
                                                 "createdAt": MAINTENANT.isoformat()})
        self.gestes.append(("commenter_issue", numero, texte))

    def corps_de(self, numero, texte):
        self.issues_[numero]["body"] = texte
        self.gestes.append(("corps_de", numero))

    def epingler(self, numero):
        self.gestes.append(("epingler", numero))

    def desepingler(self, numero):
        self.gestes.append(("desepingler", numero))

    def etiqueter(self, numero, ajouter=(), retirer=()):
        noms = [e["name"] for e in self.issues_[numero]["labels"] if e["name"] not in retirer]
        noms += [a for a in ajouter if a not in noms]
        self.issues_[numero]["labels"] = [{"name": n} for n in noms]
        self.gestes.append(("etiqueter", numero, tuple(ajouter), tuple(retirer)))

    def etiquettes(self, numero):
        return [e["name"] for e in self.issues_[numero]["labels"]]

    def fermer_issue(self, numero, commentaire=None, *, abandon=False):
        self.issues_[numero]["state"] = "CLOSED"
        self.gestes.append(("fermer_issue", numero, abandon))

    # jalons
    def jalons(self):
        return self.jalons_

    def fermer_jalon(self, numero):
        for j in self.jalons_:
            if j["number"] == numero:
                j["state"] = "closed"
        self.gestes.append(("fermer_jalon", numero))

    def creer_jalon(self, titre):
        numero = max((j["number"] for j in self.jalons_), default=0) + 1
        self.jalons_.append({"number": numero, "title": titre, "state": "open"})
        self.gestes.append(("creer_jalon", titre))

    # PR
    def ajouter_pr(self, numero, branche, *, sha="a" * 40, brouillon=False, ci="vert", commentaires=(),
                   etat="OPEN", mergeable="MERGEABLE"):
        self.prs_[numero] = {"number": numero, "headRefName": branche, "headRefOid": sha, "isDraft": brouillon,
                             "state": etat, "mergeable": mergeable, "statusCheckRollup": [],
                             "comments": [{"body": c, "createdAt": MAINTENANT.isoformat()} for c in commentaires],
                             "url": f"https://x/pull/{numero}", "title": branche, "body": "",
                             "autoMergeRequest": None, "mergedAt": None}
        self.ci(numero, ci)
        return self.prs_[numero]

    def ci(self, numero, etat, travaux=None):
        """Pose l'état des contrôles d'une PR : `vert`, `rouge` ou `attente`."""
        conclusion = {"vert": "SUCCESS", "rouge": "FAILURE"}.get(etat)
        noms = travaux or {"tests": etat, "gitleaks": "vert" if etat == "rouge" else etat}
        self.prs_[numero]["statusCheckRollup"] = [
            {"__typename": "CheckRun", "name": n, "workflowName": "security" if n == "gitleaks" else "tests",
             "status": "COMPLETED" if e in ("vert", "rouge") else "IN_PROGRESS",
             "conclusion": {"vert": "SUCCESS", "rouge": "FAILURE"}.get(e, ""),
             "startedAt": "2026-11-16T09:00:00Z",
             "detailsUrl": f"https://x/actions/runs/7/job/{i + 1}"} for i, (n, e) in enumerate(noms.items())]
        return conclusion

    def pr_de_branche(self, branche):
        for p in self.prs_.values():
            if p["headRefName"] == branche:
                return {"number": p["number"], "state": p["state"], "mergedAt": p["mergedAt"]}
        return None

    def pr(self, numero):
        return self.prs_[numero]

    def prs_ouvertes(self):
        return [p for p in self.prs_.values() if p["state"] == "OPEN"]

    def creer_pr(self, branche, base, titre, corps, *, brouillon=True):
        self.suivant += 1
        self.ajouter_pr(self.suivant, branche, brouillon=brouillon, ci="attente")
        self.prs_[self.suivant]["body"] = corps
        self.gestes.append(("creer_pr", branche, titre))
        return self.suivant

    def corps_de_pr(self, numero, texte):
        self.prs_[numero]["body"] = texte
        self.gestes.append(("corps_de_pr", numero))

    def pr_prete(self, numero):
        self.prs_[numero]["isDraft"] = False
        self.gestes.append(("pr_prete", numero))

    def commenter_pr(self, numero, texte):
        self.prs_[numero]["comments"].append({"body": texte, "createdAt": MAINTENANT.isoformat()})
        self.gestes.append(("commenter_pr", numero, texte))

    def fusion_auto(self, numero, tete=None):
        self.prs_[numero]["autoMergeRequest"] = {"mergeMethod": "SQUASH"}
        self.gestes.append(("fusion_auto", numero))
        self.tetes_fusionnees.append(tete)

    def fermer_pr(self, numero, commentaire):
        self.prs_[numero]["state"] = "CLOSED"
        self.gestes.append(("fermer_pr", numero))

    def rejouer_les_echecs(self, run):
        self.gestes.append(("rejouer_les_echecs", run))

    def etapes_du_travail(self, travail):
        """Sans `etapes_`, un travail rouge n'a pas d'étape lisible : ce n'est pas une panne."""
        return self.etapes_.get(travail, [])

    def dernier_run(self, workflow, branche):
        return self.run_master

    def base_de_fusion(self, base, tete):
        return "c" * 40

    def travaux_du_commit(self, reference):
        """Sans `travaux_`, la base n'a aucun rouge : le meneur corrige."""
        return self.travaux_.get(reference, {})

    def lancer_workflow(self, workflow, reference, champs):
        self.gestes.append(("lancer_workflow", workflow, dict(champs)))

    def variable(self, nom):
        return self.variables_.get(nom)

    def gh(self, *args, entree=None):
        """`gh pr checks` : ce que dit la CI, tel que le test le dicte."""
        return self.table_ci

    def json(self, *args):
        return []

    def noms_des_gestes(self):
        return [g[0] for g in self.gestes]

    def dits(self, numero, *, pr=False):
        """Le texte de tous les commentaires d'une issue ou d'une PR."""
        source = self.prs_ if pr else self.issues_
        return "\n\n".join(c["body"] for c in source[numero]["comments"])


class FauxDepot(Depot):
    """Un dépôt dont chaque chantier est un dossier temporaire ; rien de git.
    Un fichier présent dans le chantier est un changement à enregistrer."""

    def __init__(self, racine: Path):
        super().__init__(racine, "master", executeur=lambda argv, cwd: (0, "", ""))
        self.gestes: list[tuple] = []
        self.tete_ = "a" * 40
        self.etats_: list[tuple[str, str]] = []
        self.fichiers_: list[str] = []
        self.conflits_: list[str] = []
        self.retard_ = False
        self.revisions = 0
        self.gh = None

    def tete(self, chemin):
        return self.tete_

    def fetch(self):
        pass

    def preparer(self, nom, branche):
        chemin = self.racine / "chantiers" / str(nom)
        chemin.mkdir(parents=True, exist_ok=True)
        self.gestes.append(("preparer", nom, branche))
        return chemin

    def retirer(self, nom):
        self.gestes.append(("retirer", nom))

    def changements(self, chemin):
        base = Path(chemin)
        return sorted(str(p.relative_to(base)).replace("\\", "/") for p in base.rglob("*") if p.is_file())

    def annuler(self, chemin, fichiers):
        for f in fichiers:
            (Path(chemin) / f).unlink()
        self.gestes.append(("annuler", tuple(fichiers)))

    def enregistrer(self, chemin, message, *, vide=False):
        self.gestes.append(("enregistrer", message.splitlines()[0]))
        for p in sorted(Path(chemin).rglob("*"), reverse=True):
            if p.is_file():
                p.unlink()
        self.revisions += 1
        self.tete_ = f"{self.revisions:040x}"
        return self.tete_

    def conclure_fusion(self, chemin):
        return self.enregistrer(chemin, "fusion de la base")

    def pousser(self, chemin, branche):
        """La PR de la branche suit la révision poussée, comme sur GitHub."""
        self.gestes.append(("pousser", branche))
        for pr in getattr(self.gh, "prs_", {}).values():
            if pr["headRefName"] == branche:
                pr["headRefOid"] = self.tete_

    def en_retard(self, chemin):
        return self.retard_

    def fusionner_base(self, chemin):
        self.gestes.append(("fusionner_base",))
        return list(self.conflits_)

    def marqueurs_restants(self, chemin, fichiers):
        return []

    def fichiers_du_lot(self, chemin):
        return list(self.fichiers_)

    def etats_du_lot(self, chemin):
        return list(self.etats_)

    def noms_des_gestes(self):
        return [g[0] for g in self.gestes]


@pytest.fixture
def gh():
    faux = FauxGitHub()
    faux.jalons_ = [{"number": 1, "title": PALIER, "state": "open"}]
    return faux


@pytest.fixture
def depot(tmp_path):
    return FauxDepot(tmp_path / "depot")


def flux(*, texte: str = "", sortie: dict | None = None, cout: float = 0.5, session: str = "s-1",
         modeles: dict | None = None, cinq_heures: float = 0.2, semaine: float = 0.05, coupe: bool = False,
         erreur: bool = False) -> str:
    """Ce que Claude Code écrit en flux pour un appel : ses limites, puis son
    message « result » ; un appel coupé n'a que ses messages et leurs jetons."""
    lignes = [{"type": "system", "subtype": "init", "session_id": session},
              {"type": "rate_limit_event", "rate_limit_info": {"unifiedWindows": {
                  "five_hour": {"utilization": cinq_heures}, "seven_day": {"utilization": semaine}}}},
              {"type": "assistant", "message": {"id": "m1", "model": "claude-opus-5-5", "usage": {
                  "input_tokens": 10, "output_tokens": 200, "cache_read_input_tokens": 3000,
                  "cache_creation_input_tokens": 400}, "content": [{"type": "text", "text": texte or "je travaille"}]}}]
    if not coupe:
        lignes.append({"type": "result", "result": texte, "structured_output": sortie, "total_cost_usd": cout,
                       "num_turns": 4, "duration_ms": 90000, "is_error": erreur, "session_id": session,
                       "modelUsage": modeles or {"claude-opus-5-5": {"inputTokens": 10, "outputTokens": 200,
                                                                     "cacheReadInputTokens": 3000,
                                                                     "cacheCreationInputTokens": 400, "costUSD": cout}}})
    return "\n".join(json.dumps(l, ensure_ascii=False) for l in lignes)


class Agents:
    """Des agents dictés : chaque appel rend la réponse suivante de la liste,
    et peut écrire des fichiers dans le dossier du lot.

    Une réponse est un dictionnaire : `sortie` (l'objet structuré rendu),
    `texte`, `fichiers` (nom → contenu, écrits dans le chantier), `code`,
    `coupe` (l'appel est coupé par son délai), `erreur` (ce que dit le
    harnais), `cout`."""

    def __init__(self, *reponses):
        self.reponses = list(reponses)
        self.appels: list[dict] = []

    def __call__(self, argv, cwd, env, delai, consigne, trace):
        reponse = dict(self.reponses.pop(0))
        session = next((argv[i + 1] for i, a in enumerate(argv) if a in ("--resume", "--session-id")), "")
        self.appels.append({"argv": argv, "cwd": Path(cwd), "env": env, "consigne": consigne, "trace": trace,
                            "modele": argv[argv.index("--model") + 1], "reprise": "--resume" in argv,
                            "session": session})
        for nom, contenu in (reponse.get("fichiers") or {}).items():
            cible = Path(cwd) / nom
            cible.parent.mkdir(parents=True, exist_ok=True)
            cible.write_text(contenu, encoding="utf-8")
        coupe = bool(reponse.get("coupe"))
        ecrit = flux(texte=reponse.get("texte", ""), sortie=reponse.get("sortie"), cout=reponse.get("cout", 0.5),
                     session=session or "s-1", coupe=coupe, modeles=reponse.get("modeles"))
        if reponse.get("brut") is not None:
            ecrit = reponse["brut"]
        if trace is not None:
            Path(trace).parent.mkdir(parents=True, exist_ok=True)
            Path(trace).write_text(ecrit, encoding="utf-8")
        code = agents_mod.CODE_COUPE if coupe else reponse.get("code", 0)
        return code, ecrit, reponse.get("erreur", f"délai dépassé après {delai} s" if coupe else "")

    def modeles(self):
        """Qui a été appelé : le modèle de chaque appel."""
        return [a["modele"] for a in self.appels]


def piloter(projet, gh, depot, agents, tmp_path, **plus) -> Pilote:
    """Un pilote de test : son journal est un fichier du test."""
    pilote = Pilote(projet, gh, depot, executeur_agents=agents, journal=tmp_path / "journal.jsonl",
                    maintenant=lambda: MAINTENANT, **plus)
    depot.gh = gh
    # La photo du monde lance une vraie simulation : les tests du pilote s'en passent.
    pilote._photographier = lambda chemin, lot, sha: Photos()
    return pilote
