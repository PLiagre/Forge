"""Lire GitHub, et rien d'autre.

Ce module **lit**. Il n'approuve pas, ne fusionne pas, ne pousse rien :
les gestes qui écrivent vivent dans les workflows, où ils se voient dans
un journal. C'est la même séparation que dans le jeu — la vue lit, elle
ne décide jamais — appliquée à l'infrastructure.

Bibliothèque standard seule, comme le moteur.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from .mesure import Lecture

API = "https://api.github.com"

# Ce que GitHub accepte dans la description d'un état de commit. Au-delà,
# l'API refuse tout l'appel : l'état ne serait pas posé, donc absent, donc
# bloquant — et muet sur la raison. La borne se tient ici, en caractères :
# couper des octets casserait un accent en deux.
BORNE_DESCRIPTION = 140


def borner(texte: str, borne: int = BORNE_DESCRIPTION) -> str:
    """Une ligne assez courte pour être posée. Un « … » dit qu'elle a été coupée."""
    ligne = texte.strip().splitlines()[0] if texte.strip() else ""
    return ligne if len(ligne) <= borne else ligne[: borne - 1] + "…"


class GithubErreur(RuntimeError):
    """Un refus de GitHub, et son code.

    Le code voyage avec le message parce que 404 et 403 ne veulent pas
    dire la même chose : le premier est un « ça n'existe pas » mesuré, le
    second un « je ne te le dirai pas ». Les confondre afficherait une
    protection absente là où elle est seulement illisible.
    """

    def __init__(self, message: str, code: int = 0) -> None:
        super().__init__(message)
        self.code = code


class Github:
    def __init__(self, depot: str, jeton: str | None = None, api: str = API) -> None:
        if "/" not in depot:
            raise GithubErreur(f"dépôt attendu sous la forme « proprietaire/nom », reçu « {depot} »")
        self.depot = depot
        self.api = api.rstrip("/")
        self.jeton = jeton if jeton is not None else os.environ.get("GITHUB_TOKEN", "")
        if not self.jeton:
            raise GithubErreur(
                "aucun jeton : poser GITHUB_TOKEN. Sans lui l'API répond 403 sur "
                "les PR, et un 403 lu comme « rien à faire » arrêterait la boucle en silence"
            )

    def _get(self, chemin: str, **params) -> tuple[object, dict[str, str]]:
        url = f"{self.api}/repos/{self.depot}/{chemin.lstrip('/')}"
        if params:
            url += "?" + urllib.parse.urlencode(params)
        requete = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.jeton}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "forgehistory-outils",
            },
        )
        try:
            with urllib.request.urlopen(requete, timeout=30) as reponse:
                return json.loads(reponse.read().decode("utf-8")), dict(reponse.headers)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:400]
            raise GithubErreur(f"{exc.code} sur {url} : {detail}", exc.code) from exc
        except urllib.error.URLError as exc:
            raise GithubErreur(f"GitHub injoignable ({url}) : {exc.reason}") from exc

    def get(self, chemin: str, **params):
        return self._get(chemin, **params)[0]

    def liste(self, chemin: str, limite: int = 0, **params) -> list:
        """Les pages d'une collection. Une page oubliée ment par omission.

        `limite` borne la lecture des collections sans fin — l'historique
        des exécutions en compte des milliers, et les lire toutes pour
        n'en montrer dix coûterait un tour entier. Zéro veut dire « tout »,
        et c'est le défaut : une liste tronquée par surprise est
        exactement le genre d'omission qu'on ne voit pas.
        """
        resultat: list = []
        page = 1
        while True:
            lot, entetes = self._get(chemin, per_page=100, page=page, **params)
            if not isinstance(lot, list):
                raise GithubErreur(f"{chemin} ne rend pas une liste")
            resultat.extend(lot)
            if limite and len(resultat) >= limite:
                return resultat[:limite]
            if len(lot) < 100 or 'rel="next"' not in entetes.get("Link", ""):
                return resultat
            page += 1

    def lire(self, chemin: str, **params) -> Lecture:
        """Une lecture qui a le droit de ne pas aboutir.

        Rend une `Lecture` plutôt que de lever : ce qui se lit ici — une
        protection de branche, l'état de Pages — n'est pas indispensable
        à une décision. Ce qui serait grave, c'est de traduire le refus
        en « absent ». Un 404 est un « ça n'existe pas » et devient une
        valeur connue à `None` ; tout le reste reste inconnu.
        """
        try:
            return Lecture.sue(self.get(chemin, **params))
        except GithubErreur as exc:
            if exc.code == 404:
                return Lecture.sue(None)
            return Lecture.inconnue(borner(str(exc)))


def controles(gh: Github, sha: str) -> list[tuple[str, str, str | None]]:
    """Les contrôles posés sur une révision : (nom, statut, conclusion).

    Les `check-runs` des workflows et les `statuses` d'un outil externe
    sont deux supports du même fait ; en lire un seul laisserait un
    contrôle requis introuvable, donc absent, donc bloquant sans raison.
    """
    trouves: list[tuple[str, str, str | None]] = []
    reponse = gh.get(f"commits/{sha}/check-runs", per_page=100)
    for run in reponse.get("check_runs", []):
        trouves.append((run["name"], run.get("status", ""), run.get("conclusion")))
    etat = gh.get(f"commits/{sha}/status", per_page=100)
    for statut in etat.get("statuses", []):
        brut = statut.get("state", "")
        trouves.append(
            (statut["context"], "completed" if brut != "pending" else "in_progress",
             "success" if brut == "success" else brut)
        )
    return trouves


def auteurs_du_code(gh: Github, numero: int) -> list[str]:
    """Qui a écrit les commits d'une PR — connexions GitHub, pas noms déclarés."""
    logins: list[str] = []
    for commit in gh.liste(f"pulls/{numero}/commits"):
        for cle in ("author", "committer"):
            qui = commit.get(cle) or {}
            login = qui.get("login")
            if login and login not in logins:
                logins.append(login)
    return logins


def revues(gh: Github, numero: int) -> list[dict]:
    return gh.liste(f"pulls/{numero}/reviews")


def retard(gh: Github, base: str, tete: str) -> int:
    """Combien de commits de `base` manquent à `tete`."""
    comparaison = gh.get(f"compare/{urllib.parse.quote(base)}...{urllib.parse.quote(tete)}")
    return int(comparaison.get("behind_by", 0))


def executions(gh: Github, travail: str, limite: int = 100) -> list[dict]:
    """Les exécutions d'un travail, la plus récente d'abord."""
    reponse = gh.get(f"actions/workflows/{travail}/runs", per_page=min(limite, 100))
    return list(reponse.get("workflow_runs", []))[:limite]


def executions_rouges(gh: Github, limite: int = 100) -> list[dict]:
    """Les dernières exécutions en échec, tous travaux confondus."""
    reponse = gh.get("actions/runs", status="failure", per_page=min(limite, 100))
    return list(reponse.get("workflow_runs", []))[:limite]


def protection(gh: Github, branche: str) -> Lecture:
    """La protection de la branche de base, ou l'aveu qu'on ne peut pas la lire.

    L'API la refuse à un jeton qui n'est pas administrateur, et c'est le
    cas ordinaire du jeton d'Actions. Le refus se déclare : une
    protection illisible n'est pas une protection absente.
    """
    return gh.lire(f"branches/{urllib.parse.quote(branche)}/protection")


def pages(gh: Github) -> Lecture:
    """L'état de la publication. Un 404 dit « Pages n'est pas activé »."""
    return gh.lire("pages")


def propositions_fermees(gh: Github, base: str, limite: int) -> list[dict]:
    """Les propositions fermées, la plus récemment touchée d'abord."""
    return gh.liste("pulls", limite=limite, state="closed", base=base,
                    sort="updated", direction="desc")


def commentaires(gh: Github, numero: int, limite: int = 100) -> list[dict]:
    """Les commentaires d'une proposition — pour savoir pourquoi elle a été fermée."""
    return gh.liste(f"issues/{numero}/comments", limite=limite)


def branches(gh: Github, limite: int = 300) -> list[str]:
    """Les noms des branches distantes."""
    return [str(b.get("name", "")) for b in gh.liste("branches", limite=limite)]
