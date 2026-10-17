"""GitHub, par `gh` : lire l'état d'un lot, faire les gestes du pilote.

C'est le seul module qui parle à GitHub. Il lit toujours en JSON (le `gh`
2.45 du VPS échoue sans `--json` sur plusieurs commandes, mesuré le
20 septembre 2026) et il reçoit son exécuteur : les tests lui donnent un
faux GitHub, le pilote le vrai.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any, Callable, Iterable

# Les contrôles que la protection de master exige. Une PR est verte quand
# chacun l'est sur sa révision courante ; un contrôle absent n'est pas vert.
CONTROLES_EXIGES = ("tests", "gitleaks")
# Le contrôle exigé qui agrège un workflow, et ce workflow : `tests` ne naît
# qu'une fois tous les travaux de `tests.yml` finis, et il est rouge dès que
# l'un l'est. Un travail de ce workflow déjà rouge le rend donc rouge
# d'avance. Le 11 octobre 2026, #573 a attendu 6 h une tranche bloquée
# alors que trois travaux étaient rouges depuis le matin : le codeur ne
# l'a pas su.
AGREGATS = {"tests": "tests"}

# La variable d'Actions du dépôt qui met le PC en pause pour la chaîne : « non »
# l'arrête, tout le reste (absente comprise) la laisse travailler. Le
# propriétaire la bascule dans GitHub (Settings → Secrets and variables →
# Actions → Variables) ou par la fenêtre `pc\Disponibilite.cmd`.
VARIABLE_PC = "PC_ACTIF"

Executeur = Callable[[list[str], str | None], tuple[int, str, str]]


class GitHubErreur(RuntimeError):
    pass


def executer(argv: list[str], entree: str | None) -> tuple[int, str, str]:
    fini = subprocess.run(argv, input=entree, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=120)
    return fini.returncode, fini.stdout, fini.stderr


class GitHub:
    def __init__(self, depot: str, executeur: Executeur = executer):
        self.depot = depot
        self._executer = executeur

    # --------------------------------------------------------------- bas
    def gh(self, *args: str, entree: str | None = None) -> str:
        code, out, err = self._executer(["gh", *args], entree)
        if code != 0:
            raise GitHubErreur(f"gh {' '.join(args[:3])} : {(err or out).strip()[:400]}")
        return out

    def json(self, *args: str) -> Any:
        sortie = self.gh(*args)
        return json.loads(sortie) if sortie.strip() else None

    # ------------------------------------------------------------ issues
    def issues(self, etat: str = "open") -> list[dict]:
        return self.json("issue", "list", "-R", self.depot, "--state", etat, "--limit", "500",
                         "--json", "number,title,body,labels,milestone,state,createdAt,closedAt") or []

    def issue(self, numero: int) -> dict:
        return self.json("issue", "view", str(numero), "-R", self.depot, "--json",
                         "number,title,body,labels,milestone,state,comments,url")

    def creer_issue(self, titre: str, corps: str, etiquettes: Iterable[str] = (),
                    jalon: str | None = None) -> int:
        argv = ["issue", "create", "-R", self.depot, "--title", titre, "--body-file", "-"]
        for e in etiquettes:
            argv += ["--label", e]
        if jalon:
            argv += ["--milestone", jalon]
        url = self.gh(*argv, entree=corps).strip().splitlines()[-1]
        return int(url.rstrip("/").rsplit("/", 1)[-1])

    def commenter_issue(self, numero: int, texte: str) -> None:
        self.gh("issue", "comment", str(numero), "-R", self.depot, "--body-file", "-", entree=texte)

    def corps_de(self, numero: int, texte: str) -> None:
        self.gh("issue", "edit", str(numero), "-R", self.depot, "--body-file", "-", entree=texte)

    def epingler(self, numero: int) -> None:
        self.gh("issue", "pin", str(numero), "-R", self.depot)

    def desepingler(self, numero: int) -> None:
        self.gh("issue", "unpin", str(numero), "-R", self.depot)

    def etiqueter(self, numero: int, ajouter: Iterable[str] = (), retirer: Iterable[str] = ()) -> None:
        argv = ["issue", "edit", str(numero), "-R", self.depot]
        ajouter, retirer = list(ajouter), list(retirer)
        if ajouter:
            argv += ["--add-label", ",".join(ajouter)]
        if retirer:
            argv += ["--remove-label", ",".join(retirer)]
        if ajouter or retirer:
            self.gh(*argv)

    def jalon_de(self, numero: int, titre_jalon: str) -> None:
        self.gh("issue", "edit", str(numero), "-R", self.depot, "--milestone", titre_jalon)

    def sortir_du_jalon(self, numero: int) -> None:
        # Par l'API : `gh issue edit --remove-milestone` n'existe pas dans le
        # gh 2.45 du VPS (le 4 octobre 2026, chaque tour du pilote s'arrêtait là).
        self.gh("api", "-X", "PATCH", f"repos/{self.depot}/issues/{numero}", "--input", "-",
                entree=json.dumps({"milestone": None}))

    def fermer_issue(self, numero: int, commentaire: str | None = None, *, abandon: bool = False) -> None:
        argv = ["issue", "close", str(numero), "-R", self.depot,
                "--reason", "not planned" if abandon else "completed"]
        if commentaire:
            argv += ["--comment", commentaire]
        self.gh(*argv)

    # ----------------------------------------------------------- jalons
    def jalons(self) -> list[dict]:
        return self.json("api", f"repos/{self.depot}/milestones?state=all&per_page=100") or []

    def fermer_jalon(self, numero: int) -> None:
        self.gh("api", "-X", "PATCH", f"repos/{self.depot}/milestones/{numero}", "-f", "state=closed")

    def creer_jalon(self, titre: str) -> None:
        self.gh("api", "-X", "POST", f"repos/{self.depot}/milestones", "-f", f"title={titre}")

    def renommer_jalon(self, numero: int, titre: str) -> None:
        self.gh("api", "-X", "PATCH", f"repos/{self.depot}/milestones/{numero}", "-f", f"title={titre}")

    # --------------------------------------------------------------- PR
    def pr_de_branche(self, branche: str) -> dict | None:
        prs = self.json("pr", "list", "-R", self.depot, "--head", branche, "--state", "all",
                        "--json", "number,state,isDraft,headRefOid,url,title,mergedAt") or []
        ouvertes = [p for p in prs if p["state"] == "OPEN"]
        return (ouvertes or sorted(prs, key=lambda p: p["number"], reverse=True) or [None])[0]

    def pr(self, numero: int) -> dict:
        return self.json("pr", "view", str(numero), "-R", self.depot, "--json",
                         "number,state,isDraft,headRefName,headRefOid,mergeable,comments,"
                         "statusCheckRollup,url,title,body,autoMergeRequest,mergedAt")

    def prs_ouvertes(self) -> list[dict]:
        return self.json("pr", "list", "-R", self.depot, "--state", "open", "--limit", "100",
                         "--json", "number,headRefName,isDraft,title,url") or []

    def creer_pr(self, branche: str, base: str, titre: str, corps: str, *, brouillon: bool = True) -> int:
        argv = ["pr", "create", "-R", self.depot, "--base", base, "--head", branche,
                "--title", titre, "--body-file", "-"]
        if brouillon:
            argv.append("--draft")
        url = self.gh(*argv, entree=corps).strip().splitlines()[-1]
        return int(url.rstrip("/").rsplit("/", 1)[-1])

    def pr_prete(self, numero: int) -> None:
        self.gh("pr", "ready", str(numero), "-R", self.depot)

    def commenter_pr(self, numero: int, texte: str) -> None:
        self.gh("pr", "comment", str(numero), "-R", self.depot, "--body-file", "-", entree=texte)

    def fusion_auto(self, numero: int, tete: str | None = None) -> None:
        """Fusion (squash) dès que les contrôles exigés sont verts, de la
        révision `tete` seulement : celle que le relecteur a jugée.

        Une PR déjà fusionnable refuse l'auto-fusion (« clean status », mesuré
        le 28 septembre 2026 sur la PR #174 : le pilote échouait à chaque tour).
        On la fusionne alors tout de suite : c'est ce que l'auto-fusion aurait
        fait, et la protection de master s'applique pareil."""
        garde = ["--match-head-commit", tete] if tete else []
        try:
            self.gh("pr", "merge", str(numero), "-R", self.depot, "--auto", "--squash", *garde)
        except GitHubErreur as e:
            if "clean status" not in str(e):
                raise
            self.gh("pr", "merge", str(numero), "-R", self.depot, "--squash", *garde)

    def fermer_pr(self, numero: int, commentaire: str) -> None:
        self.gh("pr", "close", str(numero), "-R", self.depot, "--comment", commentaire)

    # --------------------------------------------------------- variables
    def variable(self, nom: str) -> str | None:
        """La valeur d'une variable d'Actions du dépôt, `None` si elle n'existe pas."""
        try:
            lue = self.json("api", f"repos/{self.depot}/actions/variables/{nom}")
        except GitHubErreur as e:
            if "404" in str(e) or "Not Found" in str(e):
                return None
            raise
        return lue.get("value") if isinstance(lue, dict) else None

    def pc_actif(self) -> bool:
        """Le PC travaille-t-il pour la chaîne ? Oui, sauf si `PC_ACTIF` vaut
        « non ». Une variable illisible (jeton sans droit de lecture, GitHub
        qui ne répond pas) ne met jamais le PC en pause : la pause se pose,
        elle ne s'invente pas."""
        try:
            valeur = self.variable(VARIABLE_PC)
        except GitHubErreur:
            return True
        return (valeur or "").strip().lower() != "non"

    # --------------------------------------------------------------- CI
    def dernier_run(self, workflow: str, branche: str) -> dict | None:
        runs = self.json("run", "list", "-R", self.depot, "--workflow", workflow, "--branch", branche,
                         "--limit", "1", "--json", "status,conclusion,headSha,databaseId,url,event") or []
        return runs[0] if runs else None

    def rejouer_les_echecs(self, run: int) -> None:
        """Rejoue les travaux en échec d'un run fini, et ceux qui les attendent."""
        self.gh("run", "rerun", str(run), "-R", self.depot, "--failed")

    def fichiers_de_pr(self, numero: int) -> list[str]:
        return [f["path"] for f in (self.json("pr", "view", str(numero), "-R", self.depot, "--json", "files")
                                    or {}).get("files") or []]

    def lancer_workflow(self, workflow: str, reference: str, champs: dict[str, str]) -> None:
        argv = ["workflow", "run", workflow, "-R", self.depot, "--ref", reference]
        for cle, valeur in champs.items():
            argv += ["-f", f"{cle}={valeur}"]
        self.gh(*argv)


def _controles(pr: dict) -> dict[str, dict[str, str]]:
    """Chaque contrôle de la révision courante de la PR, à son dernier
    passage : son état (`attente`, `vert`, `rouge`), la date où il est parti,
    son workflow et l'adresse de son travail."""
    vus: dict[str, dict[str, str]] = {}
    for c in pr.get("statusCheckRollup") or []:
        nom = c.get("name") or c.get("context") or ""
        if c.get("__typename") == "StatusContext":
            etat = {"SUCCESS": "vert", "PENDING": "attente", "EXPECTED": "attente"}.get(c.get("state", ""), "rouge")
        elif c.get("status") != "COMPLETED":
            etat = "attente"
        else:
            etat = "vert" if c.get("conclusion") in ("SUCCESS", "NEUTRAL", "SKIPPED") else "rouge"
        # Un même nom revient quand un travail est rejoué : c'est le passage
        # le plus récent qui dit l'état, pas le premier ni le pire.
        date = c.get("startedAt") or c.get("completedAt") or ""
        if nom not in vus or date >= vus[nom]["date"]:
            vus[nom] = {"etat": etat, "date": date, "workflow": c.get("workflowName") or "",
                        "adresse": c.get("detailsUrl") or ""}
    return vus


def travaux(pr: dict, workflow: str) -> dict[str, dict[str, str]]:
    """Les travaux d'un workflow sur la révision courante de la PR, comme
    `_controles` les décrit."""
    return {nom: c for nom, c in _controles(pr).items() if c["workflow"] == workflow}


def etat_des_controles(pr: dict, exiges: Iterable[str] = CONTROLES_EXIGES,
                       agregats: dict[str, str] = AGREGATS) -> tuple[str, dict[str, str]]:
    """`attente`, `vert` ou `rouge`, sur la révision courante de la PR.

    Un contrôle exigé absent retient (attente), il ne passe pas ; un travail
    rouge du workflow qu'il agrège le rend rouge sans attendre les autres.
    """
    controles = _controles(pr)
    vus = {nom: c["etat"] for nom, c in controles.items()}
    workflows = {nom: c["workflow"] for nom, c in controles.items()}
    exiges = list(exiges)
    etats = [vus.get(nom, "attente") for nom in exiges]
    agreges = {agregats[nom] for nom in exiges if nom in agregats}
    if "rouge" in etats or any(etat == "rouge" and workflows[nom] in agreges for nom, etat in vus.items()):
        return "rouge", vus
    if "attente" in etats:
        return "attente", vus
    return "vert", vus
