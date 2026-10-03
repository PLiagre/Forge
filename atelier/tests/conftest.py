"""Les doublures des tests de la chaîne : un GitHub en mémoire, un dépôt qui
ne touche à rien, des agents qui rendent ce qu'on leur dicte.

Aucun test ne parle au vrai GitHub, ni n'invoque un vrai agent : aucun quota
n'est dépensé ici.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sys

import pytest

RACINE = Path(__file__).resolve().parents[2]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

from atelier.depot import Depot  # noqa: E402
from atelier.github import GitHub  # noqa: E402
from atelier.projet import charger  # noqa: E402

TOML = """
[projet]
nom = "Essai"
depot = "moi/essai"
branche_base = "master"
tests = "python3 -m pytest jeu -q"
interdits = ["atelier/", ".github/", "atelier.toml"]
lignes_max = 300
corrections_max = 2
depannages_max = 2
dossier_briefs = "docs/briefs"
prefixe_branche = "lot/"

[agents]
chef        = "claude/opus | codex/sol"
codeur      = "codex/sol | cursor/grok"
codeur_3d   = "claude/opus | cursor/grok"
renfort     = "codex/astra | codex/sol | cursor/grok"
relecteur   = "claude/opus | codex/sol"
mecanicien  = "cursor/composer"
depanneur   = "claude/opus | codex/sol"
chroniqueur = "cursor/grok"
boussole    = "claude/opus | codex/sol"
"""


@pytest.fixture
def projet(tmp_path):
    (tmp_path / "atelier.toml").write_text(TOML, encoding="utf-8")
    (tmp_path / "CAP.md").write_text("# CAP\n", encoding="utf-8")
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
    suivant: int = 100

    def __post_init__(self):
        GitHub.__init__(self, self.depot, executeur=lambda argv, entree: (1, "", "pas de vrai gh ici"))

    # issues
    def ajouter_issue(self, numero, titre, etiquettes=("lot", "pret"), jalon="J1 — Le pont", corps="", etat="OPEN"):
        self.issues_[numero] = {"number": numero, "title": titre, "body": corps, "state": etat,
                                "labels": [{"name": e} for e in etiquettes],
                                "milestone": {"title": jalon} if jalon else None, "comments": []}
        return self.issues_[numero]

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
        self.issues_[numero]["comments"].append({"body": texte, "author": {"login": "pilote"}})
        self.gestes.append(("commenter_issue", numero, texte))

    def epingler(self, numero):
        self.gestes.append(("epingler", numero))

    def desepingler(self, numero):
        self.gestes.append(("desepingler", numero))

    def etiqueter(self, numero, ajouter=(), retirer=()):
        noms = [e["name"] for e in self.issues_[numero]["labels"] if e["name"] not in retirer]
        noms += [a for a in ajouter if a not in noms]
        self.issues_[numero]["labels"] = [{"name": n} for n in noms]
        self.gestes.append(("etiqueter", numero, tuple(ajouter), tuple(retirer)))

    def jalon_de(self, numero, titre_jalon):
        self.issues_[numero]["milestone"] = {"title": titre_jalon}

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
        self.jalons_.append({"number": numero, "title": titre, "state": "open", "open_issues": 0,
                             "closed_issues": 0})
        self.gestes.append(("creer_jalon", titre))

    def renommer_jalon(self, numero, titre):
        for j in self.jalons_:
            if j["number"] == numero:
                j["title"] = titre
        self.gestes.append(("renommer_jalon", numero, titre))

    # PR
    def ajouter_pr(self, numero, branche, *, sha="a" * 40, brouillon=False, ci="vert", commentaires=(),
                   etat="OPEN", mergeable="MERGEABLE"):
        conclusion = {"vert": "SUCCESS", "rouge": "FAILURE"}.get(ci)
        rollup = [{"__typename": "CheckRun", "name": n, "status": "COMPLETED" if conclusion else "IN_PROGRESS",
                   "conclusion": conclusion or "", "startedAt": "2026-09-27T10:00:00Z"} for n in ("tests", "gitleaks")]
        self.prs_[numero] = {"number": numero, "headRefName": branche, "headRefOid": sha, "isDraft": brouillon,
                             "state": etat, "mergeable": mergeable, "statusCheckRollup": rollup,
                             "comments": [{"body": c} for c in commentaires], "url": f"https://x/pull/{numero}",
                             "title": branche, "autoMergeRequest": None, "mergedAt": None}
        return self.prs_[numero]

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

    def pr_prete(self, numero):
        self.prs_[numero]["isDraft"] = False
        self.gestes.append(("pr_prete", numero))

    def commenter_pr(self, numero, texte):
        self.prs_[numero]["comments"].append({"body": texte})
        self.gestes.append(("commenter_pr", numero, texte))

    def fusion_auto(self, numero, tete=None):
        self.prs_[numero]["autoMergeRequest"] = {"mergeMethod": "SQUASH"}
        self.gestes.append(("fusion_auto", numero))
        self.tetes_fusionnees.append(tete)

    def fermer_pr(self, numero, commentaire):
        self.prs_[numero]["state"] = "CLOSED"
        self.gestes.append(("fermer_pr", numero))

    def dernier_run(self, workflow, branche):
        return {"status": "completed", "conclusion": "success", "databaseId": 1, "url": "https://x/run/1"}

    def lancer_workflow(self, workflow, reference, champs):
        self.gestes.append(("lancer_workflow", workflow, dict(champs)))

    def noms_des_gestes(self):
        return [g[0] for g in self.gestes]


class FauxDepot(Depot):
    """Un dépôt dont chaque chantier est un dossier temporaire ; rien de git."""

    def __init__(self, racine: Path):
        super().__init__(racine, "master", executeur=lambda argv, cwd: (0, "", ""))
        self.gestes: list[tuple] = []
        self.fichiers_changes: dict[str, list[str]] = {}
        self.tete_ = "a" * 40

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

    def enregistrer(self, chemin, message):
        self.gestes.append(("enregistrer", message.splitlines()[0]))
        for p in sorted(Path(chemin).rglob("*"), reverse=True):
            if p.is_file():
                p.unlink()
        self.tete_ = "b" * 40
        return self.tete_

    def pousser(self, chemin, branche):
        self.gestes.append(("pousser", branche))

    def fichiers_du_lot(self, chemin):
        return []

    def noms_des_gestes(self):
        return [g[0] for g in self.gestes]


@pytest.fixture
def gh():
    faux = FauxGitHub()
    faux.jalons_ = [
        {"number": 1, "title": "J1 — Le pont", "state": "open", "open_issues": 2, "closed_issues": 0},
        {"number": 2, "title": "J2 — Le geste revient", "state": "open", "open_issues": 0, "closed_issues": 0},
    ]
    return faux


@pytest.fixture
def depot(tmp_path):
    return FauxDepot(tmp_path / "depot")


class Agents:
    """Des agents dictés : chaque appel rend la réponse suivante de la liste,
    et peut écrire des fichiers dans le dossier du lot."""

    def __init__(self, *reponses):
        self.reponses = list(reponses)
        self.appels: list[list[str]] = []

    def __call__(self, argv, cwd, env, delai):
        self.appels.append(argv)
        reponse = self.reponses.pop(0)
        code, texte, fichiers = (reponse + ({},))[:3] if len(reponse) == 2 else reponse
        for nom, contenu in fichiers.items():
            cible = Path(cwd) / nom
            cible.parent.mkdir(parents=True, exist_ok=True)
            cible.write_text(contenu, encoding="utf-8")
        return code, texte, ""

    def outils(self):
        return [a[0] for a in self.appels]
