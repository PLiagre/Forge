"""Le journal du matin et la boussole de la semaine.

Les faits se relèvent en Python sur GitHub — ce qui a été fusionné, ce qui
est bloqué et pourquoi, ce qui est en cours, le jalon et son pourcentage. Le
chroniqueur n'en fait que des phrases ; s'il ne répond pas, les faits bruts
sont publiés tels quels. Un journal ne se tait jamais.

Tout va dans une seule issue, épinglée : « Journal de Forge ».
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import re

from . import agents as agents_mod
from . import lots, prompts
from .github import GitHub
from .projet import Projet

TITRE_JOURNAL = "Journal de Forge"
_IMAGE = re.compile(r"!\[[^\]]*\]\((https://raw\.githubusercontent\.com/[^)]+)\)")


def issue_du_journal(gh: GitHub) -> int | None:
    for issue in gh.issues("open"):
        if issue["title"].strip() == TITRE_JOURNAL:
            return issue["number"]
    return None


def fusionnees_depuis(gh: GitHub, depuis: datetime) -> list[dict]:
    jour = depuis.strftime("%Y-%m-%d")
    prs = gh.json("pr", "list", "-R", gh.depot, "--state", "merged", "--search", f"merged:>={jour}",
                  "--limit", "100", "--json", "number,title,url,mergedAt,headRefName") or []
    return [p for p in prs if (p.get("mergedAt") or "") >= depuis.strftime("%Y-%m-%dT%H:%M:%S")]


def _raison_du_blocage(gh: GitHub, numero: int) -> str:
    issue = gh.issue(numero)
    for m in reversed(lots.marques(issue.get("comments") or [])):
        if m.get("etat") == "bloque" and m.get("raison"):
            return m["raison"]
    return "raison non écrite par le pilote (bloqué à la main ?)"


def faits(gh: GitHub, projet: Projet, maintenant: datetime, *, heures: int = 24) -> str:
    depuis = maintenant - timedelta(hours=heures)
    lignes = []
    livres = fusionnees_depuis(gh, depuis)
    lignes.append(f"LIVRÉ DEPUIS {depuis:%Y-%m-%d %H:%M} UTC ({len(livres)}) :")
    for p in livres:
        lignes.append(f"- PR #{p['number']} « {p['title']} » ({p['url']})")
        pr = gh.pr(p["number"])
        for c in pr.get("comments") or []:
            for url in _IMAGE.findall(c.get("body") or ""):
                lignes.append(f"  ![capture]({url})")
    ouvertes = [lots.Lot.de(i) for i in gh.issues("open")]
    bloques = [l for l in ouvertes if l.etat == "bloque"]
    lignes.append(f"\nBLOQUÉS ({len(bloques)}) :")
    for l in bloques:
        lignes.append(f"- #{l.numero} « {l.titre} » : {_raison_du_blocage(gh, l.numero)}")
    en_cours = [l for l in ouvertes if l.etat == "en-cours"]
    lignes.append(f"\nEN COURS ({len(en_cours)}) :")
    for l in en_cours:
        resume = gh.pr_de_branche(l.branche(projet.prefixe_branche))
        lignes.append(f"- #{l.numero} « {l.titre} » ({l.machine})" + (f", PR #{resume['number']}" if resume else ""))
    jalons = lots.jalons(gh.jalons())
    courant = lots.jalon_courant(jalons)
    if courant is None:
        lignes.append("\nJALON : aucun jalon ouvert.")
    else:
        suivants = [l for l in sorted(ouvertes, key=lambda l: l.numero)
                    if l.jalon == courant.numero and l.etat in ("pret", "idee") and "lot" in l.etiquettes][:3]
        lignes.append(f"\nJALON EN COURS : {courant.titre} — {courant.pourcentage} % "
                      f"({courant.fermees} lot(s) fermé(s) sur {courant.ouvertes + courant.fermees}).")
        lignes.append("PROCHAINS LOTS : " + (", ".join(f"#{l.numero} « {l.titre} »" for l in suivants) or "aucun"))
    return "\n".join(lignes)


def _publier(gh: GitHub, texte: str) -> int:
    numero = issue_du_journal(gh)
    if numero is None:
        numero = gh.creer_issue(TITRE_JOURNAL, "Le journal de la chaîne : un commentaire chaque matin, "
                                             "la boussole chaque lundi.", ["journal"])
    gh.commenter_issue(numero, texte)
    return numero


def ecrire(gh: GitHub, projet: Projet, *, maintenant: datetime | None = None, publier: bool = True,
           executeur=agents_mod.executer, dossier: Path | None = None) -> str:
    maintenant = maintenant or datetime.now(timezone.utc)
    releve = faits(gh, projet, maintenant)
    res = agents_mod.invoquer(projet.poste("chroniqueur"), prompts.chroniqueur(faits=releve),
                              dossier or projet.racine, projet.delai("chroniqueur"), executeur=executeur)
    if res.reussi and res.texte.strip():
        corps = f"## Journal du {maintenant:%d/%m/%Y}\n\n{res.texte.strip()}\n\n<sub>Écrit par {res.agent}.</sub>"
    else:
        raison = "; ".join(res.essais) or f"code {res.code}"
        corps = (f"## Journal du {maintenant:%d/%m/%Y} (faits bruts)\n\nLe chroniqueur n'a pas répondu ({raison}).\n\n"
                 f"```\n{releve}\n```")
    if publier:
        _publier(gh, corps)
    return corps


def boussole(gh: GitHub, projet: Projet, *, maintenant: datetime | None = None, publier: bool = True,
             executeur=agents_mod.executer) -> str:
    maintenant = maintenant or datetime.now(timezone.utc)
    releve = faits(gh, projet, maintenant, heures=24 * 7)
    cap = (projet.racine / "CAP.md").read_text(encoding="utf-8")
    res = agents_mod.invoquer(projet.poste("boussole"), prompts.boussole(cap=cap, faits=releve),
                              projet.racine, projet.delai("boussole"), executeur=executeur)
    if res.reussi and res.texte.strip():
        corps = f"## Boussole de la semaine du {maintenant:%d/%m/%Y}\n\n{res.texte.strip()}\n\n<sub>Écrit par {res.agent}.</sub>"
    else:
        corps = (f"## Boussole de la semaine du {maintenant:%d/%m/%Y}\n\nLa boussole n'a pas répondu "
                 f"({'; '.join(res.essais) or res.code}). Les faits :\n\n```\n{releve}\n```")
    if publier:
        _publier(gh, corps)
    return corps
