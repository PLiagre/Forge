"""Autoriser et préparer une demande. Lectures GitHub seules, aucun geste distant."""

from __future__ import annotations

import base64
import re

from . import palier, registre, saisie

# Associations accordées par GitHub, jamais par le texte du formulaire.
# CONTRIBUTOR et FIRST_TIME_CONTRIBUTOR ne donnent aucun droit.
CONFIANCE = frozenset({"OWNER", "MEMBER", "COLLABORATOR"})
BOT = "github-actions[bot]"


def autorisee(evenement: dict) -> bool:
    issue = evenement.get("issue") or {}
    return (
        evenement.get("action") == "opened"
        and issue.get("author_association") in CONFIANCE
        and bool((issue.get("user") or {}).get("login"))
        and (evenement.get("sender") or {}).get("login") == issue["user"]["login"]
        and any(l.get("name") == "lot" for l in issue.get("labels", []))
    )


def interne(gh, pr):
    """Un préfixe de branche ne suffit pas : une fourche ne réserve rien ici."""
    depot_tete = ((pr.get("head") or {}).get("repo") or {}).get("full_name", "")
    return bool(depot_tete) and depot_tete.casefold() == gh.depot.casefold()


def reservations(gh, fiches, branches=None, prs=None):
    """Numéros des branches distantes et des fiches de PR feuille ouvertes.

    Une erreur de lecture interrompt l'attribution. Une réservation ne
    disparaît pas parce que sa PR a été fermée : la branche la conserve.
    """
    branches = gh.liste("branches") if branches is None else branches
    prs = gh.liste("pulls", state="open") if prs is None else prs
    numeros = {f.numero for f in fiches}
    for branche in branches:
        trouve = re.search(r"/(\d{3})(?:-|$)", branche["name"])
        if trouve:
            numeros.add(trouve.group(1))
    for pr in prs:
        if not interne(gh, pr) or pr.get("state", "open") != "open" or not pr["head"]["ref"].startswith("feuille/"):
            continue
        brut = gh.get("contents/ROADMAP.md", ref=pr["head"]["sha"])
        texte = base64.b64decode(brut["content"]).decode("utf-8")
        feuille = registre.atelier().lire_texte(texte)
        numeros.update(f.numero for f in feuille.fiches)
    return numeros


def preparer(gh, evenement, fiches, briefs="briefs"):
    """Un plan rejouable, lié au numéro d'issue et à une branche durable."""
    if not autorisee(evenement):
        return {"action": "RIEN", "raison": "demande non autorisée ou événement déjà couvert"}
    issue = gh.get(f"issues/{int(evenement['issue']['number'])}")
    if issue.get("author_association") not in CONFIANCE:
        return {"action": "RIEN", "raison": "association de confiance retirée"}
    if issue["state"] != "open":
        return {"action": "RIEN", "raison": "demande déjà fermée"}
    numero_issue = issue["number"]
    suffixe = f"-demande-{numero_issue}"
    branches = gh.liste("branches")
    prs = [p for p in gh.liste("pulls", state="all") if interne(gh, p)]
    anciennes = [p for p in prs if p["head"]["ref"].startswith("feuille/")
                 and p["head"]["ref"].endswith(suffixe)]
    reservees = [b["name"] for b in branches
                if b["name"].startswith("feuille/") and b["name"].endswith(suffixe)]
    noms = set(reservees) | {p["head"]["ref"] for p in anciennes}
    if len(noms) > 1 or len(anciennes) > 1:
        raise saisie.DemandeIllisible("plusieurs réservations pour cette demande : intervention requise")
    precedente = anciennes[0] if anciennes else None
    if precedente and precedente["state"] != "open":
        return {"action": "RIEN", "raison": f"PR {precedente['number']} déjà fermée ou fusionnée"}
    commentaire = f"<!-- demande-lot:{numero_issue}:succes -->"
    reponse = any((c.get("user") or {}).get("login") == BOT and commentaire in c.get("body", "")
                  for c in gh.liste(f"issues/{numero_issue}/comments"))
    texte = ""
    if noms:
        branche = next(iter(noms))
        numero = branche.split("/")[1][:3]
        if not reservees and precedente:
            raise saisie.DemandeIllisible("PR ouverte sans sa branche réservée")
    else:
        demande = saisie.lire(issue["body"])
        connus = {f.numero for f in fiches}
        if any(dep not in connus for dep in demande.depend_de):
            raise saisie.DemandeIllisible("dépendance sans fiche : on ne dépend pas d'un fantôme")
        numero = palier.numero_libre(fiches, reservations(gh, fiches, branches, prs))
        branche = f"feuille/{saisie.souche(demande, numero)}{suffixe}"
        texte = saisie.fiche(demande, numero, briefs)
    return {
        "action": "deposer", "numero": numero, "branche": branche,
        "issue": numero_issue, "pr": precedente["number"] if precedente else 0,
        "reservee": bool(reservees), "reponse": reponse, "fiche": texte,
    }
