"""Le journal du matin et la boussole de la semaine.

Les faits se relèvent en Python — sur GitHub et dans le journal du pilote :
ce que chaque lot livré a changé (le compte rendu du codeur, le verdict du
relecteur, ses captures), ce que la chaîne a vécu (attentes et leur raison,
découpes, reprises), ce qui est bloqué ou en cours, ce que le propriétaire
doit faire, le jalon et son pourcentage. Le chroniqueur en fait un récit ;
s'il ne répond pas, les faits bruts sont publiés tels quels. Un journal ne se
tait jamais.

Tout va dans une seule issue, épinglée : « Journal de Forge ».
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import tempfile

from . import agents as agents_mod
from . import captures, lots, prompts
from .depot import Depot
from .github import GitHub
from .projet import Projet

TITRE_JOURNAL = "Journal de Forge"
_IMAGE = re.compile(r"!\[[^\]]*\]\((https://raw\.githubusercontent\.com/[^)]+)\)")
# Ce que le pilote écrit sur la machine qui le fait tourner (le VPS).
JOURNAL_LOCAL = Path.home() / ".atelier" / "journal.jsonl"
VEILLE = Path.home() / ".atelier" / "veille.txt"
# Une session à rouvrir, et le geste qui la rouvre.
_SESSION = re.compile(r"\b(claude|codex|cursor)/[\w.-]+ : session expirée ou absente")
GESTES_SESSION = {
    "claude": "claude setup-token, puis ranger le jeton dans ~/.atelier/claude.token (mode 600)",
    "codex": "codex login",
    "cursor": "cursor-agent login",
}
_PLAFOND = re.compile(r"spend limit|plafond de dépense", re.I)


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


def _compte_rendu(commentaires: list[dict], lignes_max: int = 25) -> str:
    """Le dernier compte rendu du codeur, sans marque ni image : ce que le
    lot a fait, dans ses mots."""
    for c in reversed(commentaires):
        if any(m.get("role") in lots.ROLES_CODEURS and m.get("etat") == "fait" for m in lots.marques([c])):
            corps = lots._MARQUE.sub("", c.get("body") or "")
            utiles = [l.rstrip() for l in corps.splitlines()[1:] if l.strip() and not _IMAGE.search(l)]
            return "\n".join(utiles[:lignes_max])
    return ""


def _lot_livre(gh: GitHub, p: dict) -> list[str]:
    commentaires = gh.pr(p["number"]).get("comments") or []
    liste = lots.marques(commentaires)
    passages = sum(1 for m in liste if m.get("role") in lots.ROLES_CODEURS and m.get("etat") in ("fait", "echec"))
    verdicts = [m for m in liste if m.get("role") == "relecteur" and m.get("verdict")]
    relu = f"{verdicts[-1]['verdict']} par {verdicts[-1].get('agent', '?')}" if verdicts else "sans relecture écrite"
    lignes = [f"- PR #{p['number']} « {p['title']} » ({p['url']}) — {passages} passage(s) du codeur, relu : {relu}"]
    rendu = _compte_rendu(commentaires)
    if rendu:
        lignes.append("  Ce que dit le codeur :")
        lignes += [f"    {l}" for l in rendu.splitlines()]
    vues: list[str] = []
    for c in commentaires:
        vues += [u for u in _IMAGE.findall(c.get("body") or "") if u not in vues]
    lignes += [f"  ![capture]({u})" for u in vues]
    return lignes


def _vecu(chemin: Path, depuis: datetime) -> tuple[list[str], list[str]]:
    """Ce que le pilote a fait, lot par lot, d'après son journal ; et les
    raisons de ses attentes (pour « À faire »)."""
    par_lot: dict[str, list[dict]] = {}
    try:
        texte = chemin.read_text(encoding="utf-8")
    except OSError:
        return [f"- journal du pilote illisible ({chemin})"], []
    for ligne in texte.splitlines():
        try:
            e = json.loads(ligne)
            quand = datetime.fromisoformat(e["quand"])
        except (ValueError, KeyError, TypeError):
            continue
        if quand >= depuis:
            par_lot.setdefault(str(e.get("lot")), []).append(e)
    lignes, raisons = [], []
    ordre = sorted(par_lot, key=lambda n: (not n.isdigit(), int(n) if n.isdigit() else 0, n))
    for lot in ordre:
        evenements = par_lot[lot]
        compte = Counter(e["action"] for e in evenements)
        dernier = {e["action"]: e.get("detail") or "" for e in evenements}
        morceaux = [f"{a} ×{n}" if n > 1 or a.startswith("attendre") else (f"{a} ({dernier[a]})" if dernier[a] else a)
                    for a, n in compte.items()]
        lignes.append(f"- #{lot} : " + ", ".join(morceaux))
        soucis = [e for e in evenements
                  if e["action"] in ("attente", "secours", "erreur", "bloqué") or "échec" in e["action"]]
        if soucis:
            lignes.append(f"  dernière raison : {(soucis[-1].get('detail') or '')[:400]}")
            raisons += [e.get("detail") or "" for e in soucis]
    return lignes or ["- rien dans le journal du pilote"], raisons


def _etat_en_cours(commentaires: list[dict]) -> tuple[str, str | None]:
    """La dernière chose que la chaîne a écrite sur une PR en cours, en une
    ligne, et sa date (marque `quand`) quand elle en a une."""
    for c in reversed(commentaires):
        liste = lots.marques([c])
        if liste:
            premiere = lots._MARQUE.sub("", c.get("body") or "").strip().splitlines()[0]
            return premiere[:400], liste[-1].get("quand")
    return "", None


def _attentes_depuis(commentaires: list[dict], depuis: datetime) -> list[str]:
    """Le texte des attentes écrites sur une PR depuis `depuis`."""
    textes = []
    for c in commentaires:
        for m in lots.marques([c]):
            quand = m.get("quand")
            if m.get("etat") == "attente" and quand and datetime.fromisoformat(quand) >= depuis:
                textes.append(lots._MARQUE.sub("", c.get("body") or "").strip())
    return textes


def _a_faire(raisons_vps: list[str], raisons_pc: list[str], veille: Path, bloques: list) -> list[str]:
    gestes = []
    for machine, raisons in (("VPS", raisons_vps), ("PC", raisons_pc)):
        for outil in sorted({m.group(1) for r in raisons for m in _SESSION.finditer(r)}):
            gestes.append(f"- {machine} : la session {outil} est expirée ou absente → {GESTES_SESSION[outil]}")
    if any(_PLAFOND.search(r) for r in raisons_vps + raisons_pc):
        gestes.append("- Claude a atteint son plafond de dépense mensuel : le relever sur claude.ai/settings/usage, "
                      "ou attendre que la limite se rouvre (la chaîne attend, elle ne perd rien)")
    try:
        gestes += [f"- veille du VPS : {l.strip()}" for l in veille.read_text(encoding="utf-8").splitlines()
                   if l.startswith("FAIL")]
    except OSError:
        pass
    gestes += [f"- #{l.numero} bloqué : lire sa raison, corriger (mode direct si c'est la chaîne), remettre « pret »"
               for l in bloques]
    return gestes or ["- rien"]


def faits(gh: GitHub, projet: Projet, maintenant: datetime, *, heures: int = 24,
          journal_local: Path | None = None, veille: Path | None = None) -> str:
    depuis = maintenant - timedelta(hours=heures)
    lignes = []
    livres = fusionnees_depuis(gh, depuis)
    des_lots = [p for p in livres if (p.get("headRefName") or "").startswith(projet.prefixe_branche)]
    machine = [p for p in livres if p not in des_lots]
    lignes.append(f"LOTS LIVRÉS DEPUIS {depuis:%Y-%m-%d %H:%M} UTC ({len(des_lots)}) :")
    for p in des_lots:
        lignes += _lot_livre(gh, p)
    lignes.append(f"\nLA MACHINE, CHANGÉE EN MODE DIRECT ({len(machine)}) :")
    lignes += [f"- PR #{p['number']} « {p['title']} »" for p in machine]
    vecu, raisons_vps = _vecu(journal_local or JOURNAL_LOCAL, depuis)
    lignes.append("\nCE QUE LA CHAÎNE A VÉCU (journal du pilote, par lot) :")
    lignes += vecu
    ouvertes = [lots.Lot.de(i) for i in gh.issues("open")]
    bloques = [l for l in ouvertes if l.etat == "bloque"]
    lignes.append(f"\nBLOQUÉS ({len(bloques)}) :")
    for l in bloques:
        lignes.append(f"- #{l.numero} « {l.titre} » : {_raison_du_blocage(gh, l.numero)}")
    en_cours = [l for l in ouvertes if l.etat == "en-cours"]
    lignes.append(f"\nEN COURS ({len(en_cours)}) :")
    lues: dict[int, list[dict]] = {}
    for l in en_cours:
        resume = gh.pr_de_branche(l.branche(projet.prefixe_branche))
        ligne = f"- #{l.numero} « {l.titre} » ({l.machine})" + (f", PR #{resume['number']}" if resume else "")
        if resume:
            lues[l.numero] = gh.pr(resume["number"]).get("comments") or []
            dernier, _ = _etat_en_cours(lues[l.numero])
            if dernier:
                ligne += f" — dernier état : {dernier}"
        lignes.append(ligne)
    # Le PC dit ses attentes sur la PR du lot, pas dans le journal du VPS :
    # on les lit sur chaque lot du PC qui a une PR, en cours ou non.
    raisons_pc = []
    for l in ouvertes:
        if l.machine != "pc" or "lot" not in l.etiquettes or l.etat == "idee":
            continue
        if l.numero not in lues:
            resume = gh.pr_de_branche(l.branche(projet.prefixe_branche))
            lues[l.numero] = (gh.pr(resume["number"]).get("comments") or []) if resume else []
        raisons_pc += _attentes_depuis(lues[l.numero], depuis)
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
    lignes.append("\nÀ FAIRE PAR LE PROPRIÉTAIRE :")
    lignes += _a_faire(raisons_vps, raisons_pc, veille or VEILLE, bloques)
    return "\n".join(lignes)


def _publier(gh: GitHub, texte: str) -> int:
    numero = issue_du_journal(gh)
    if numero is None:
        numero = gh.creer_issue(TITRE_JOURNAL, "Le journal de la chaîne : un commentaire chaque matin, "
                                             "la boussole chaque lundi.", ["journal"])
    gh.commenter_issue(numero, texte)
    return numero


def photo_du_monde(gh: GitHub, projet: Projet, maintenant: datetime) -> list[str]:
    """La carte du monde tel que master le simule ce matin : chaque journal
    porte au moins une image, même un jour sans lot livré."""
    with tempfile.TemporaryDirectory(prefix="journal-") as tmp:
        carte = captures.carte_du_monde(projet.racine, Path(tmp))
        if carte is None:
            return []
        nommee = Path(tmp) / f"monde-{maintenant:%Y-%m-%d}.png"
        carte.rename(nommee)
        try:
            return captures.publier(Depot(projet.racine, projet.branche_base), gh.depot, [nommee],
                                    f"{maintenant:%Y-%m-%d}")
        except Exception:  # noqa: BLE001 — une photo manquée ne retient pas le journal
            return []


def ecrire(gh: GitHub, projet: Projet, *, maintenant: datetime | None = None, publier: bool = True,
           executeur=agents_mod.executer, dossier: Path | None = None, photographe=photo_du_monde) -> str:
    maintenant = maintenant or datetime.now(timezone.utc)
    releve = faits(gh, projet, maintenant)
    images = photographe(gh, projet, maintenant) if publier else []
    if images:
        photos = "".join(f"![le monde]({url})\n" for url in images)
        releve = f"LE MONDE CE MATIN (master, 30 jours simulés) :\n{photos}\n{releve}"
    res = agents_mod.invoquer(projet.poste("chroniqueur"), prompts.chroniqueur(faits=releve),
                              dossier or projet.racine, projet.delai("chroniqueur"), executeur=executeur)
    if res.reussi and res.texte.strip():
        corps = f"## Journal du {maintenant:%d/%m/%Y}\n\n{res.texte.strip()}\n\n<sub>Écrit par {res.agent}.</sub>"
    else:
        raison = "; ".join(res.essais) or f"code {res.code}"
        # Les faits bruts restent du markdown : leurs images s'affichent.
        corps = (f"## Journal du {maintenant:%d/%m/%Y} (faits bruts)\n\nLe chroniqueur n'a pas répondu ({raison}).\n\n"
                 f"{releve}")
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
