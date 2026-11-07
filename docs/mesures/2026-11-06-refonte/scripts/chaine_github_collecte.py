"""Collecte, en lecture seule, des issues et des PR de PLiagre/Forge.

Usage (depuis n'importe où ; `gh` doit être connecté) :

    py chaine_github_collecte.py [--sortie CHEMIN]

Par défaut, écrit C:/Users/liagr/AppData/Local/hermes/cache/scratch/chaine_github_brut.json
(fichier de travail ; les données retenues sont recopiées dans
brut/chaine-github.json par chaine_github_mesure.py).

Ce script n'appelle que `gh api graphql` avec des requêtes `query` (aucune
mutation) et un `gh api` GET : il ne modifie rien sur GitHub.

1. Issues : toutes (ouvertes et fermées), par pages de 50 :
   numéro, titre, état, stateReason, dates, milestone, étiquettes, corps.
2. Timelines des issues, par lots de 10 issues (alias `i<n>: issue(number:n)`),
   restreintes aux types LABELED_EVENT, UNLABELED_EVENT, CLOSED_EVENT,
   REOPENED_EVENT, MILESTONED_EVENT, DEMILESTONED_EVENT ; la suite (> 100
   événements) est relue issue par issue ; puis recomptées par lots de 7, et
   toute issue dont le compte diffère est relue seule.
   Piège constaté le 6 novembre 2026 : `timelineItems(itemTypes: …)` rend des
   timelines TRONQUÉES (totalCount faux, ex. #388 : 4 événements au lieu de 9,
   sans son ClosedEvent ni son étiquette `livre`) quand la requête est grosse :
   posée dans la connexion `issues(first: 50)`, ou à 40-50 alias ; à 1-30
   alias, elle rend ce que rend l'issue seule. Le script vérifie aussi
   len(timeline) == totalCount.
3. PR : toutes, par pages de 25 : additions, suppressions, branche de tête,
   commit de fusion, issues fermées, et la liste des fichiers
   (files(first:100){path additions deletions} ; la suite est relue si besoin).
4. Milestones : `gh api repos/PLiagre/Forge/milestones?state=all`.
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone

PROPRIETAIRE = "PLiagre"
DEPOT = "Forge"
SORTIE_DEFAUT = "C:/Users/liagr/AppData/Local/hermes/cache/scratch/chaine_github_brut.json"

TIMELINE_TYPES = ("[LABELED_EVENT, UNLABELED_EVENT, CLOSED_EVENT, REOPENED_EVENT, "
                  "MILESTONED_EVENT, DEMILESTONED_EVENT]")

TIMELINE_NODES = """
          __typename
          ... on LabeledEvent { createdAt label { name } actor { login } }
          ... on UnlabeledEvent { createdAt label { name } actor { login } }
          ... on ClosedEvent { createdAt stateReason actor { login }
                               closer { __typename ... on PullRequest { number } ... on Commit { oid } } }
          ... on ReopenedEvent { createdAt actor { login } }
          ... on MilestonedEvent { createdAt milestoneTitle actor { login } }
          ... on DemilestonedEvent { createdAt milestoneTitle actor { login } }
"""

Q_ISSUES = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    issues(first: 50, after: $cursor, orderBy: {field: CREATED_AT, direction: ASC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number title state stateReason createdAt closedAt
        author { login }
        milestone { number title }
        labels(first: 30) { nodes { name } }
        body
      }
    }
  }
  rateLimit { remaining resetAt cost }
}
"""

# Une timeline, posée sous un alias par issue.
FRAGMENT_TIMELINE = """
    i%(n)d: issue(number: %(n)d) {
      number
      timelineItems(first: 100, itemTypes: %(types)s) {
        totalCount
        pageInfo { hasNextPage endCursor }
        nodes { %(nodes)s }
      }
    }
"""

Q_TIMELINE_SUITE = """
query($owner: String!, $name: String!, $number: Int!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    issue(number: $number) {
      timelineItems(first: 100, after: $cursor, itemTypes: %s) {
        pageInfo { hasNextPage endCursor }
        nodes { %s }
      }
    }
  }
}
""" % (TIMELINE_TYPES, TIMELINE_NODES)

Q_PRS = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequests(first: 25, after: $cursor, orderBy: {field: CREATED_AT, direction: ASC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number title state createdAt mergedAt closedAt
        headRefName baseRefName
        additions deletions changedFiles
        author { login }
        mergeCommit { oid messageHeadline }
        closingIssuesReferences(first: 10) { nodes { number } }
        labels(first: 20) { nodes { name } }
        files(first: 100) {
          totalCount
          pageInfo { hasNextPage endCursor }
          nodes { path additions deletions changeType }
        }
      }
    }
  }
  rateLimit { remaining resetAt cost }
}
"""

Q_FILES_SUITE = """
query($owner: String!, $name: String!, $number: Int!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      files(first: 100, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes { path additions deletions changeType }
      }
    }
  }
}
"""


def graphql(query, **variables):
    """Appelle `gh api graphql --input -` (requête en lecture) et rend `data`.

    Le corps {query, variables} passe par l'entrée standard : une requête à
    50 alias dépasse la longueur de ligne de commande de Windows.
    """
    vars_ = {"owner": PROPRIETAIRE, "name": DEPOT}
    vars_.update({k: v for k, v in variables.items() if v is not None})
    corps = json.dumps({"query": query, "variables": vars_})
    cmd = ["gh", "api", "graphql", "--input", "-"]
    for essai in range(4):
        proc = subprocess.run(cmd, input=corps, capture_output=True, text=True, encoding="utf-8")
        if proc.returncode == 0:
            reponse = json.loads(proc.stdout)
            if "errors" in reponse:
                raise RuntimeError(json.dumps(reponse["errors"], ensure_ascii=False))
            return reponse["data"]
        print(f"  essai {essai + 1} raté : {proc.stderr.strip()[:300]}", file=sys.stderr)
        time.sleep(5 * (essai + 1))
    raise RuntimeError("gh api graphql a échoué quatre fois")


def collecter_issues():
    issues, curseur, page = [], None, 0
    while True:
        page += 1
        data = graphql(Q_ISSUES, cursor=curseur)
        bloc = data["repository"]["issues"]
        for n in bloc["nodes"]:
            n["labels"] = [l["name"] for l in n["labels"]["nodes"]]
            issues.append(n)
        print(f"issues page {page} : {len(issues)} (quota restant {data['rateLimit']['remaining']})",
              file=sys.stderr)
        if not bloc["pageInfo"]["hasNextPage"]:
            return issues
        curseur = bloc["pageInfo"]["endCursor"]


def requete_timelines(lot, noeuds=TIMELINE_NODES):
    corps = "".join(FRAGMENT_TIMELINE % {"n": n, "types": TIMELINE_TYPES, "nodes": noeuds} for n in lot)
    return ("query($owner: String!, $name: String!) { repository(owner: $owner, name: $name) {"
            + corps + "} rateLimit { remaining } }")


def collecter_timelines(numeros, taille_lot=10):
    """Timelines par lots de `taille_lot` issues, via des alias issue(number:).

    Mesuré le 6 novembre 2026 sur les 50 issues #331 à #409 : par lots de 2 à
    30 alias, les totalCount sont ceux d'une issue seule ; par lots de 40 ou
    50, onze sont faux (tronqués). D'où des lots de 10, et la vérification de
    `verifier_timelines`.
    """
    timelines = {}
    for debut in range(0, len(numeros), taille_lot):
        lot = numeros[debut:debut + taille_lot]
        data = graphql(requete_timelines(lot))
        for n in lot:
            noeud = data["repository"][f"i{n}"]
            tl = noeud["timelineItems"]
            evenements = list(tl["nodes"])
            suite = tl["pageInfo"]
            while suite["hasNextPage"]:
                d2 = graphql(Q_TIMELINE_SUITE, number=n, cursor=suite["endCursor"])
                t2 = d2["repository"]["issue"]["timelineItems"]
                evenements += t2["nodes"]
                suite = t2["pageInfo"]
            if len(evenements) != tl["totalCount"]:
                raise RuntimeError(f"timeline de #{n} incomplète : {len(evenements)} / {tl['totalCount']}")
            timelines[n] = {"total": tl["totalCount"], "evenements": evenements}
        if (debut // taille_lot) % 10 == 0 or debut + taille_lot >= len(numeros):
            print(f"timelines : {len(timelines)} / {len(numeros)} "
                  f"(quota restant {data['rateLimit']['remaining']})", file=sys.stderr)
    return timelines


def verifier_timelines(timelines, taille_lot=7):
    """Recompte les timelines par un autre découpage (lots de 7, totalCount
    seul) ; toute issue dont le compte diffère est relue seule, et c'est
    cette lecture seule qui est gardée. Rend la liste des issues relues."""
    numeros = sorted(timelines)
    ecarts = []
    for debut in range(0, len(numeros), taille_lot):
        lot = numeros[debut:debut + taille_lot]
        data = graphql(requete_timelines(lot, "__typename"))
        for n in lot:
            if data["repository"][f"i{n}"]["timelineItems"]["totalCount"] != timelines[n]["total"]:
                ecarts.append(n)
    for n in ecarts:
        timelines.update(collecter_timelines([n], taille_lot=1))
    print(f"vérification des timelines : {len(ecarts)} écart(s) relu(s) seul(s) {ecarts}", file=sys.stderr)
    return ecarts


def collecter_prs():
    prs, curseur, page = [], None, 0
    while True:
        page += 1
        data = graphql(Q_PRS, cursor=curseur)
        bloc = data["repository"]["pullRequests"]
        for p in bloc["nodes"]:
            fichiers = list(p["files"]["nodes"]) if p["files"] else []
            info = p["files"]["pageInfo"] if p["files"] else {"hasNextPage": False}
            while info["hasNextPage"]:
                d2 = graphql(Q_FILES_SUITE, number=p["number"], cursor=info["endCursor"])
                f2 = d2["repository"]["pullRequest"]["files"]
                fichiers += f2["nodes"]
                info = f2["pageInfo"]
            p["filesTotal"] = p["files"]["totalCount"] if p["files"] else None
            p["files"] = fichiers
            p["labels"] = [l["name"] for l in p["labels"]["nodes"]]
            p["closingIssues"] = [x["number"] for x in p["closingIssuesReferences"]["nodes"]]
            del p["closingIssuesReferences"]
            prs.append(p)
        print(f"PR page {page} : {len(prs)} (quota restant {data['rateLimit']['remaining']})", file=sys.stderr)
        if not bloc["pageInfo"]["hasNextPage"]:
            return prs
        curseur = bloc["pageInfo"]["endCursor"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sortie", default=SORTIE_DEFAUT)
    args = ap.parse_args()
    debut = datetime.now(timezone.utc).isoformat(timespec="seconds")
    issues = collecter_issues()
    timelines = collecter_timelines([i["number"] for i in issues])
    relues = verifier_timelines(timelines)
    for i in issues:
        i["timeline"] = timelines[i["number"]]["evenements"]
        i["timelineTotal"] = timelines[i["number"]]["total"]
    prs = collecter_prs()
    milestones = json.loads(subprocess.run(
        ["gh", "api", f"repos/{PROPRIETAIRE}/{DEPOT}/milestones?state=all&per_page=100"],
        capture_output=True, text=True, encoding="utf-8", check=True).stdout)
    milestones = [{k: m[k] for k in ("number", "title", "state", "open_issues", "closed_issues",
                                     "created_at", "closed_at")} for m in milestones]
    brut = {
        "depot": f"{PROPRIETAIRE}/{DEPOT}",
        "collecte_debut_utc": debut,
        "collecte_fin_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "timelines_relues_seules": relues,
        "milestones": milestones,
        "issues": issues,
        "prs": prs,
    }
    with open(args.sortie, "w", encoding="utf-8") as f:
        json.dump(brut, f, ensure_ascii=False, indent=1)
    print(f"écrit {args.sortie} : {len(issues)} issues, {len(prs)} PR", file=sys.stderr)


if __name__ == "__main__":
    main()
