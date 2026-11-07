"""Rapatrie, en lecture seule, ce qu'il faut pour mesurer la chaîne d'agents.

Usage : py vps_pilote_collecte.py DOSSIER_DE_TRAVAIL
  - ssh hermes-boost 'cat ~/.atelier/journal.jsonl'      -> journal.jsonl
  - ssh hermes-boost 'cat ~/.atelier/logs/pilote.log'    -> pilote.log
  - gh issue list (lots)                                  -> issues.json
  - gh api graphql, 20 issues par requête (timelines)     -> timelines.json
Rien n'est écrit sur le VPS ni sur GitHub.
"""
import json, subprocess, sys
from pathlib import Path

dossier = Path(sys.argv[1]); dossier.mkdir(parents=True, exist_ok=True)
for distant, local in (("~/.atelier/journal.jsonl", "journal.jsonl"), ("~/.atelier/logs/pilote.log", "pilote.log")):
    with open(dossier / local, "wb") as f:
        subprocess.run(["ssh", "hermes-boost", f"cat {distant}"], stdout=f, check=True)
out = subprocess.run(["gh", "issue", "list", "-R", "PLiagre/Forge", "--label", "lot", "--state", "all",
                      "--limit", "3000", "--json", "number,title,createdAt,closedAt,state,labels,body"],
                     capture_output=True, check=True, encoding="utf-8").stdout
(dossier / "issues.json").write_text(out, encoding="utf-8")
numeros = sorted(i["number"] for i in json.loads(out))
champ = ("timelineItems(first:100,itemTypes:[LABELED_EVENT,UNLABELED_EVENT,CLOSED_EVENT,REOPENED_EVENT])"
         "{pageInfo{hasNextPage} nodes{__typename ... on LabeledEvent{createdAt label{name}} "
         "... on UnlabeledEvent{createdAt label{name}} ... on ClosedEvent{createdAt} ... on ReopenedEvent{createdAt}}}")
resultat = {}
for k in range(0, len(numeros), 20):
    lot = numeros[k:k + 20]
    q = "query{repository(owner:\"PLiagre\",name:\"Forge\"){" + " ".join(
        f"i{n}:issue(number:{n}){{number {champ}}}" for n in lot) + "}}"
    r = subprocess.run(["gh", "api", "graphql", "-f", f"query={q}"], capture_output=True, encoding="utf-8")
    if r.returncode:
        print("échec", lot[0], r.stderr[:200]); continue
    for v in json.loads(r.stdout)["data"]["repository"].values():
        if v:
            resultat[v["number"]] = v["timelineItems"]
(dossier / "timelines.json").write_text(json.dumps(resultat), encoding="utf-8")
tronques = [n for n, t in resultat.items() if t["pageInfo"]["hasNextPage"]]
print(len(resultat), "timelines ; tronquées :", tronques)
