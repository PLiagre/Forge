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

    # --------------------------------------------------------------- CI
    def dernier_run(self, workflow: str, branche: str) -> dict | None:
        runs = self.json("run", "list", "-R", self.depot, "--workflow", workflow, "--branch", branche,
                         "--limit", "1", "--json", "status,conclusion,headSha,databaseId,url,event") or []
        return runs[0] if runs else None

    def lancer_workflow(self, workflow: str, reference: str, champs: dict[str, str]) -> None:
        argv = ["workflow", "run", workflow, "-R", self.depot, "--ref", reference]
        for cle, valeur in champs.items():
            argv += ["-f", f"{cle}={valeur}"]
        self.gh(*argv)


def etat_des_controles(pr: dict, exiges: Iterable[str] = CONTROLES_EXIGES) -> tuple[str, dict[str, str]]:
    """`attente`, `vert` ou `rouge`, sur la révision courante de la PR.

    Un contrôle exigé absent retient (attente), il ne passe pas.
    """
    vus: dict[str, str] = {}
    dates: dict[str, str] = {}
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
        if nom not in vus or date >= dates[nom]:
            vus[nom], dates[nom] = etat, date
    exiges = list(exiges)
    etats = [vus.get(nom, "attente") for nom in exiges]
    if "rouge" in etats:
        return "rouge", vus
    if "attente" in etats:
        return "attente", vus
    return "vert", vus
