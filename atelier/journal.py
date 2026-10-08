"""Le journal du matin et la boussole de la semaine.

Les faits se relèvent en Python — sur GitHub et dans le journal du pilote :
ce que chaque lot livré a changé (le compte rendu du codeur, le verdict du
relecteur, ses captures), ce que la chaîne a vécu (attentes et leur raison,
découpes, reprises), ce qui est bloqué ou en cours, ce que le propriétaire
doit faire, le jalon et son pourcentage ; pour chaque lot livré, la
section « Le joueur » de son brief. Le chroniqueur en fait un récit court,
en langage de jeu (un bandeau, ce qui a changé, aujourd'hui) ; le pilote y
ajoute lui-même l'avancement du jalon et les détails repliés.

Les images viennent du monde que master joue pendant un an : la terre du
joueur parmi ses voisins, la faim en Europe, et pour un lot qui parle de
grenier, de dette ou de population, la carte de cette lecture. La carte
que le pilote prend de chaque lot (`-carte.png`) ne s'y montre plus : c'est
la même Europe en densité, quel que soit le lot. Une image déjà
montrée — mêmes octets que la photo du monde, ou qu'une capture précédente —
est omise : le 2 octobre 2026, six cartes de lots et trois photos du ksar
étaient le même fichier. Si le chroniqueur se tait, sort du gabarit ou cite
ce que les faits ne disent pas, le pilote écrit le journal seul. Un journal
ne se tait jamais.

Chaque journal est sa propre issue, épinglée ; celle de la veille se ferme.
La boussole fait de même.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import tempfile
import urllib.request

from . import agents as agents_mod
from . import captures, lots, prompts
from .depot import Depot
from .github import GitHub
from .projet import Projet
from .verrous import Verrous

_IMAGE = re.compile(r"!\[[^\]]*\]\((https://raw\.githubusercontent\.com/[^)]+)\)")
# Ce que le pilote écrit sur la machine qui le fait tourner (le VPS).
JOURNAL_LOCAL = Path.home() / ".atelier" / "journal.jsonl"
VEILLE = Path.home() / ".atelier" / "veille.txt"
# Une session à rouvrir, et le geste qui la rouvre.
_SESSION = re.compile(r"\b(claude|codex|cursor)/[\w.@-]+ : session expirée ou absente")
GESTES_SESSION = {
    "claude": "claude setup-token, puis ranger le jeton dans ~/.atelier/claude.token (mode 600)",
    "codex": "codex login",
    "cursor": "cursor-agent login",
}
_PLAFOND = re.compile(r"spend limit|plafond de dépense", re.I)
# Un harnais qui refuse l'appel tel que la chaîne le construit (agents._APPEL).
_APPEL_REFUSE = re.compile(r"\b((?:claude|codex|cursor)/[\w.@-]+) : refuse l'appel")
# Une raison d'attente se coupe devant chaque agent qu'elle nomme : « chef :
# claude/… : quota épuisé (…) · cursor/… : session expirée ». La citation de
# l'erreur peut elle-même contenir « · » : on coupe devant l'agent, pas là.
_DEVANT_AGENT = re.compile(r"(?=\b(?:claude|codex|cursor)/[\w.@-]+ : )")
_AGENT = re.compile(r"\b(claude|codex|cursor)/[\w.@-]+ : ")
_ORIGINE = datetime.min.replace(tzinfo=timezone.utc)


def _date(texte: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat((texte or "").replace("Z", "+00:00"))
    except ValueError:
        return None


def _encore_vraies(raisons: list[tuple[datetime, str]], reponses: dict[str, datetime]) -> list[str]:
    """Les agents qu'une raison dit empêchés, et qu'aucune réponse plus récente
    du même outil, sur la même machine, n'a démentis : le journal du 29
    septembre 2026 demandait encore de relever le plafond de Claude, qui codait
    depuis la veille. Un agent écarté (sa famille a écrit le lot) n'est pas
    empêché."""
    vraies = []
    for quand, texte in raisons:
        for morceau in _DEVANT_AGENT.split(texte):
            m = _AGENT.match(morceau)
            if m and "écarté" not in morceau and reponses.get(m.group(1), _ORIGINE) <= quand:
                vraies.append(morceau)
    return vraies


def _repondre(reponses: dict[str, datetime], agent: str | None, quand: datetime | None) -> None:
    outil = (agent or "").split("/")[0]
    if outil and quand is not None and quand > reponses.get(outil, _ORIGINE):
        reponses[outil] = quand


def _reponses_du_pc(commentaires: list[dict], reponses: dict[str, datetime]) -> None:
    """Les réponses des agents du PC (le codeur_3d), datées par leur commentaire."""
    for c in commentaires:
        for m in lots.marques([c]):
            if m.get("role") == "codeur_3d" and m.get("agent"):
                _repondre(reponses, m["agent"], _date(c.get("createdAt")) or _date(m.get("quand")))


@dataclass
class Releve:
    """Les faits du matin : `texte` pour le chroniqueur et la boussole, et
    leurs morceaux pour ce que le pilote écrit lui-même (l'avancement du
    jalon, les détails, et le journal entier quand le chroniqueur fait défaut)."""
    texte: str
    livres: list[dict] = field(default_factory=list)
    machine: list[dict] = field(default_factory=list)
    vecu: list[str] = field(default_factory=list)
    bloques: list[tuple[lots.Lot, str]] = field(default_factory=list)
    en_cours: list[str] = field(default_factory=list)
    aujourd_hui: list[str] = field(default_factory=list)
    a_faire: list[str] = field(default_factory=list)
    jalon: str = ""
    avancement: list[str] = field(default_factory=list)


def fusionnees_depuis(gh: GitHub, depuis: datetime) -> list[dict]:
    jour = depuis.strftime("%Y-%m-%d")
    prs = gh.json("pr", "list", "-R", gh.depot, "--state", "merged", "--search", f"merged:>={jour}",
                  "--limit", "100", "--json", "number,title,url,mergedAt,headRefName") or []
    return [p for p in prs if (p.get("mergedAt") or "") >= depuis.strftime("%Y-%m-%dT%H:%M:%S")]


def _blocage(gh: GitHub, numero: int) -> dict:
    """La dernière marque « bloque » du pilote sur l'issue : sa raison, et la
    question du chef s'il en a posé une ; {} pour un lot bloqué à la main."""
    issue = gh.issue(numero)
    for m in reversed(lots.marques(issue.get("comments") or [])):
        if m.get("etat") == "bloque" and m.get("raison"):
            return m
    return {}


def _raison_du_blocage(gh: GitHub, numero: int) -> str:
    return _blocage(gh, numero).get("raison") or "raison non écrite par le pilote (bloqué à la main ?)"


def _compte_rendu(commentaires: list[dict], lignes_max: int = 25) -> str:
    """Le dernier compte rendu du codeur, sans marque ni image : ce que le
    lot a fait, dans ses mots."""
    for c in reversed(commentaires):
        if any(m.get("role") in lots.ROLES_CODEURS and m.get("etat") == "fait" for m in lots.marques([c])):
            corps = lots._MARQUE.sub("", c.get("body") or "")
            utiles = [l.rstrip() for l in corps.splitlines()[1:] if l.strip() and not _IMAGE.search(l)]
            return "\n".join(utiles[:lignes_max])
    return ""


def _capture_finale(commentaires: list[dict]) -> str | None:
    """La première image du dernier commentaire qui en porte : la révision
    fusionnée. Le journal du 29 septembre 2026 montrait aussi les captures des
    révisions d'avant, et on ne savait plus laquelle était neuve."""
    for c in reversed(commentaires):
        images = _IMAGE.findall(c.get("body") or "")
        if images:
            return images[0]
    return None


def _le_joueur(racine: Path | None, numero: str | None) -> str:
    """La section « Le joueur » du brief du lot, en un paragraphe : ce que le
    joueur y gagne, dans les mots du jeu. Vide si le brief n'est pas sur master."""
    if racine is None or numero is None:
        return ""
    for brief in sorted((Path(racine) / "docs" / "briefs").glob(f"{numero}-*.md")):
        m = _SECTION_JOUEUR.search(brief.read_text(encoding="utf-8"))
        if m:
            return " ".join(m.group(1).split())
    return ""


def _theme(texte: str) -> str | None:
    """La lecture de carte qui montre le sujet d'un lot, ou None."""
    bas = texte.lower()
    return next((lecture for lecture, mots in _THEMES if any(mot in bas for mot in mots)), None)


def _lot_livre(p: dict, commentaires: list[dict], racine: Path | None = None) -> tuple[dict, list[str]]:
    liste = lots.marques(commentaires)
    passages = sum(1 for m in liste if m.get("role") in lots.ROLES_CODEURS and m.get("etat") in ("fait", "echec"))
    verdicts = [m for m in liste if m.get("role") == "relecteur" and m.get("verdict")]
    relu = f"{verdicts[-1]['verdict']} par {verdicts[-1].get('agent', '?')}" if verdicts else "sans relecture écrite"
    lignes = [f"- PR #{p['number']} « {p['title']} » ({p['url']}) — {passages} passage(s) du codeur, relu : {relu}"]
    # « Lot #185 — Unity lit… » : le propriétaire connaît le lot, pas la PR.
    m = _TITRE_DE_LOT.match(p["title"])
    nom = f"#{m.group(1)} {m.group(2)}" if m else p["title"]
    joueur = _le_joueur(racine, m.group(1) if m else None)
    if joueur:
        lignes.append(f"  Ce que le joueur y gagne (le brief) : {joueur}")
    rendu = _compte_rendu(commentaires)
    if rendu:
        lignes.append("  Ce que dit le codeur (technique : à traduire en jeu, jamais à recopier) :")
        lignes += [f"    {l}" for l in rendu.splitlines()]
    capture = _capture_finale(commentaires)
    # La carte que le pilote prend de chaque lot est la même Europe en
    # densité, quel que soit le lot : elle ne montre pas ce qu'il change.
    if capture and capture.endswith(_CARTE_GENERIQUE):
        capture = None
    if capture:
        lignes.append(f"  ![capture]({capture})")
    lecture = None if capture else _theme(f"{nom} {joueur}")
    livre = {"numero": p["number"], "nom": nom, "url": p["url"], "rendu": rendu, "capture": capture,
             "joueur": joueur, "lecture": lecture}
    return livre, lignes


_TITRE_DE_LOT = re.compile(r"Lot #(\d+) — (.+)")
_SECTION_JOUEUR = re.compile(r"^## Le joueur\s*\n(.*?)(?=^## |\Z)", re.S | re.M)
_CARTE_GENERIQUE = "-carte.png"
# Le sujet d'un lot, reconnu à ses mots, et la lecture de carte qui le montre.
_THEMES = (
    ("faim", ("faim", "famine", "disette", "affam")),
    ("nourriture", ("grenier", "grain", "blé", "récolte", "moisson", "vivres", "nourri")),
    ("dette", ("dette",)),
    ("population", ("population", "habitant", "naissance", "migr")),
)
# Ce que montre chaque image du matin, dit au joueur, par le début du nom de
# son fichier : (texte de l'image, légende).
VUES = {
    "terre": ("ta terre", "Ta terre, cerclée de rouge, parmi ses voisins après un an de jeu : "
                          "plus le bleu est foncé, plus les gens y vivent serrés."),
    "faim": ("la faim", "Où l'on a faim en Europe après un an de jeu : plus c'est foncé, "
                        "plus la faim dure depuis longtemps."),
    "nourriture": ("les réserves", "Les réserves de nourriture après un an de jeu : plus c'est foncé, "
                                   "plus il reste de vivres."),
    "dette": ("le manque", "Ce qui manque pour nourrir chacun après un an de jeu : plus c'est foncé, "
                           "plus le manque est lourd."),
    "population": ("les gens", "Où vivent les gens après un an de jeu : plus c'est foncé, plus il y a de monde."),
    "monde": ("le monde", "Le monde ce matin, simulé depuis master."),
}
# Les images de chaque matin, dans l'ordre ; les autres lectures ne se
# rendent que pour un lot livré qui en parle.
VUES_DU_MATIN = ("terre", "faim")
ANNEE_DE_JEU = 365


def _vue(url: str) -> str:
    """La vue d'une image du matin, par le nom de son fichier (« terre-2026-10-08.png »)."""
    nom = url.rsplit("/", 1)[-1]
    return next((cle for cle in VUES if nom.startswith(f"{cle}-")), "monde")


def _attend(lot: lots.Lot, bloq: frozenset[int], ouverts: set[int], enfants: dict[int, list[int]]) -> list[int]:
    """Les lots ouverts qu'attend ce lot : un lot découpé, déjà fermé, se
    remplace par ses morceaux encore ouverts (#120 attend #184 et #186, pas
    #119 et #183, fermés depuis leur découpe)."""
    attendus: set[int] = set()
    a_voir, vus = sorted(lot.dependances & bloq), set()
    while a_voir:
        n = a_voir.pop()
        if n in vus:
            continue
        vus.add(n)
        if n in ouverts:
            attendus.add(n)
        else:
            a_voir += enfants.get(n, [])
    return sorted(attendus)


def _avancement(lot: lots.Lot, ouvert: bool, enfants: dict[int, list[int]], attendus: list[int],
                raisons: dict[int, str]) -> str:
    """Une ligne de la liste du jalon : ce lot est-il fait, et sinon, qu'attend-il ?"""
    nom = f"#{lot.numero} {lot.titre}"
    if not ouvert:
        if lot.etat == "livre":
            return f"- [x] {nom}"
        morceaux = sorted(enfants.get(lot.numero, []))
        return f"- ~~{nom}~~ — " + (f"découpé en {', '.join(f'#{n}' for n in morceaux)}" if morceaux else "abandonné")
    ou = "sur le PC" if lot.machine == "pc" else "sur le VPS"
    if lot.etat == "bloque":
        quoi = f"**bloqué** : {raisons.get(lot.numero, '')}"
    elif lot.etat == "en-cours":
        quoi = f"en cours {ou}"
    elif attendus:
        quoi = "attend " + ", ".join(f"#{n}" for n in attendus)
    else:
        quoi = "prêt" if lot.etat == "pret" else "idée, pas encore prête"
    return f"- [ ] {nom} — {quoi}"


def _vecu(chemin: Path, depuis: datetime) -> tuple[list[str], list[str]]:
    """Ce que le pilote a fait, lot par lot, d'après son journal ; et les
    raisons de ses attentes que rien n'a démenties depuis (pour « À faire »)."""
    par_lot: dict[str, list[dict]] = {}
    reponses: dict[str, datetime] = {}
    try:
        texte = chemin.read_text(encoding="utf-8")
    except OSError:
        return [f"- journal du pilote illisible ({chemin})"], []
    for ligne in texte.splitlines():
        try:
            e = json.loads(ligne)
            e["_quand"] = datetime.fromisoformat(e["quand"])
        except (ValueError, KeyError, TypeError):
            continue
        if e["_quand"] >= depuis:
            par_lot.setdefault(str(e.get("lot")), []).append(e)
            _repondre(reponses, e.get("agent"), e["_quand"])
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
            dernier_souci = soucis[-1]
            ligne = f"  dernière raison ({dernier_souci['_quand']:%d/%m %H:%M} UTC) : {(dernier_souci.get('detail') or '')[:400]}"
            detail = dernier_souci.get("detail") or ""
            empeches = _encore_vraies([(_ORIGINE, detail)], {})
            if empeches and not _encore_vraies([(dernier_souci["_quand"], detail)], reponses):
                ligne += " — LEVÉE DEPUIS : ces agents ont répondu ensuite"
            lignes.append(ligne)
            raisons += [(e["_quand"], e.get("detail") or "") for e in soucis]
    return lignes or ["- rien dans le journal du pilote"], _encore_vraies(raisons, reponses)


def _etat_en_cours(commentaires: list[dict]) -> tuple[str, str | None]:
    """La dernière chose que la chaîne a écrite sur une PR en cours, en une
    ligne, et sa date (marque `quand`) quand elle en a une."""
    for c in reversed(commentaires):
        liste = lots.marques([c])
        if liste:
            premiere = lots._MARQUE.sub("", c.get("body") or "").strip().splitlines()[0]
            return premiere[:400], liste[-1].get("quand")
    return "", None


def _attentes_depuis(commentaires: list[dict], depuis: datetime) -> list[tuple[datetime, str]]:
    """Les attentes écrites sur une PR depuis `depuis`, avec leur date."""
    textes = []
    for c in commentaires:
        for m in lots.marques([c]):
            quand = _date(m.get("quand"))
            if m.get("etat") == "attente" and quand and quand >= depuis:
                textes.append((quand, lots._MARQUE.sub("", c.get("body") or "").strip()))
    return textes


def _a_faire(raisons_vps: list[str], raisons_pc: list[str], veille: Path, bloques: list,
             questions: dict | None = None) -> list[str]:
    gestes = []
    for machine, raisons in (("VPS", raisons_vps), ("PC", raisons_pc)):
        for outil in sorted({m.group(1) for r in raisons for m in _SESSION.finditer(r)}):
            gestes.append(f"- {machine} : la session {outil} est expirée ou absente → {GESTES_SESSION[outil]}")
    for machine, raisons in (("VPS", raisons_vps), ("PC", raisons_pc)):
        for agent in sorted({m.group(1) for r in raisons for m in _APPEL_REFUSE.finditer(r)}):
            gestes.append(f"- {machine} : {agent} refuse l'appel tel que la chaîne le construit (option, effort "
                          "ou réglage) → corriger sa ligne dans atelier.toml, ou mettre le harnais à jour ; "
                          "`python3 -m atelier sonde` le prouve")
    if any(_PLAFOND.search(r) for r in raisons_vps + raisons_pc):
        gestes.append("- Claude a atteint son plafond de dépense mensuel : le relever sur claude.ai/settings/usage, "
                      "ou attendre que la limite se rouvre (la chaîne attend, elle ne perd rien)")
    try:
        gestes += [f"- veille du VPS : {l.strip()}" for l in veille.read_text(encoding="utf-8").splitlines()
                   if l.startswith("FAIL")]
    except OSError:
        pass
    # Une question du chef se pose ici telle qu'il l'a écrite : le
    # propriétaire répond d'un commentaire sur l'issue, sans chercher.
    questions = questions or {}
    for l in bloques:
        if l.numero in questions:
            gestes.append(f"- #{l.numero} « {l.titre} » attend ta décision : {questions[l.numero].en_une_ligne()} "
                          f"Réponds par un commentaire sur l'issue #{l.numero} (une lettre suffit) : le pilote "
                          "reprend le lot au tour suivant")
        else:
            gestes.append(f"- #{l.numero} bloqué : lire sa raison, corriger (mode direct si c'est la chaîne), puis "
                          "répondre par un commentaire sur l'issue : le pilote reprend le lot au tour suivant")
    return gestes or ["- rien"]


def faits(gh: GitHub, projet: Projet, maintenant: datetime, *, heures: int = 24,
          journal_local: Path | None = None, veille: Path | None = None) -> str:
    return releve(gh, projet, maintenant, heures=heures, journal_local=journal_local, veille=veille).texte


def releve(gh: GitHub, projet: Projet, maintenant: datetime, *, heures: int = 24,
           journal_local: Path | None = None, veille: Path | None = None) -> Releve:
    r = Releve("")
    depuis = maintenant - timedelta(hours=heures)
    lignes = []
    livres = fusionnees_depuis(gh, depuis)
    des_lots = [p for p in livres if (p.get("headRefName") or "").startswith(projet.prefixe_branche)]
    machine = [p for p in livres if p not in des_lots]
    lignes.append(f"LOTS LIVRÉS DEPUIS {depuis:%Y-%m-%d %H:%M} UTC ({len(des_lots)}) :")
    reponses_pc: dict[str, datetime] = {}
    for p in des_lots:
        commentaires = gh.pr(p["number"]).get("comments") or []
        _reponses_du_pc(commentaires, reponses_pc)
        livre, faits_du_lot = _lot_livre(p, commentaires, projet.racine)
        r.livres.append(livre)
        lignes += faits_du_lot
    lignes.append(f"\nLA MACHINE, CHANGÉE EN MODE DIRECT ({len(machine)}) :")
    lignes += [f"- PR #{p['number']} « {p['title']} »" for p in machine]
    r.machine = machine
    vecu, raisons_vps = _vecu(journal_local or JOURNAL_LOCAL, depuis)
    r.vecu = vecu
    lignes.append("\nCE QUE LA CHAÎNE A VÉCU (journal du pilote, par lot) :")
    lignes += vecu
    ouvertes = [lots.Lot.de(i) for i in gh.issues("open")]
    bloques = [l for l in ouvertes if l.etat == "bloque"]
    lignes.append(f"\nBLOQUÉS ({len(bloques)}) :")
    questions = {}
    for l in bloques:
        blocage = _blocage(gh, l.numero)
        r.bloques.append((l, blocage.get("raison") or "raison non écrite par le pilote (bloqué à la main ?)"))
        question = lots.Question.de_marque(blocage)
        if question:
            questions[l.numero] = question
        lignes.append(f"- #{l.numero} « {l.titre} » : {r.bloques[-1][1]}")
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
        r.en_cours.append(ligne)
        r.aujourd_hui.append(f"#{l.numero} {l.titre} : en cours sur le {'PC' if l.machine == 'pc' else 'VPS'}.")
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
    for commentaires in lues.values():
        _reponses_du_pc(commentaires, reponses_pc)
    jalons = lots.jalons(gh.jalons())
    courant = lots.jalon_courant(jalons)
    if courant is None:
        lignes.append("\nJALON : aucun jalon ouvert.")
    else:
        # L'ordre du pilote : `pret` avant `idee`, par numéro, et un lot dont
        # une dépendance est encore ouverte attend (lots.a_prendre).
        fermees = [lots.Lot.de(i) for i in gh.issues("closed")]
        bloq = lots.bloquantes(ouvertes, fermees)
        candidats = [l for l in sorted(ouvertes, key=lambda l: (l.etat != "pret", l.numero))
                     if l.jalon == courant.numero and l.etat in ("pret", "idee") and "lot" in l.etiquettes]
        suivants = [l for l in candidats if not l.dependances & bloq][:3]
        attendent = [l for l in candidats if l.dependances & bloq]
        enfants: dict[int, list[int]] = {}
        for l in (*ouvertes, *fermees):
            if l.decoupe_de is not None:
                enfants.setdefault(l.decoupe_de, []).append(l.numero)
        ouverts = {l.numero for l in ouvertes}
        attendus = {l.numero: _attend(l, bloq, ouverts, enfants) for l in ouvertes}
        lignes.append(f"\nJALON EN COURS : {courant.titre} — {courant.pourcentage} % "
                      f"({courant.fermees} lot(s) fermé(s) sur {courant.ouvertes + courant.fermees}).")
        lignes.append("PROCHAINS LOTS : " + (", ".join(f"#{l.numero} « {l.titre} »" for l in suivants) or "aucun"))
        if attendent:
            lignes.append("EN ATTENTE DE LEURS DÉPENDANCES : " + ", ".join(
                f"#{l.numero} « {l.titre} » (attend {', '.join(f'#{n}' for n in attendus[l.numero])})"
                for l in attendent))
        r.aujourd_hui += [f"#{l.numero} {l.titre} : prêt, il part dès qu'une machine est libre." for l in suivants]
        # La fenêtre de deux jalons : une machine qui n'a plus rien dans le
        # jalon courant prend dans le suivant (Pilote.tour).
        apres = lots.jalon_suivant(jalons, courant)
        en_avance = [l for l in sorted(ouvertes, key=lambda l: (l.etat != "pret", l.numero))
                     if apres is not None and l.jalon == apres.numero and l.etat in ("pret", "idee")
                     and "lot" in l.etiquettes and lots.ETIQUETTE_RESERVE not in l.etiquettes
                     and not l.dependances & bloq][:3]
        if en_avance:
            lignes.append(f"EN AVANCE, DU JALON SUIVANT ({apres.titre}) : " + ", ".join(
                f"#{l.numero} « {l.titre} » ({l.machine})" for l in en_avance))
        r.aujourd_hui += [f"#{l.numero} {l.titre} : jalon suivant, il part quand le {'PC' if l.machine == 'pc' else 'VPS'} "
                          f"n'a plus rien dans {courant.titre}." for l in en_avance]
        # La fenêtre a trois jalons (Pilote._plus_loin).
        loin = lots.troisieme_jalon(jalons, courant)
        plus_loin = [l for l in sorted(ouvertes, key=lambda l: (l.etat != "pret", l.numero))
                     if loin is not None and l.jalon == loin.numero
                     and l.etat in ("pret", "idee") and "lot" in l.etiquettes
                     and lots.ETIQUETTE_RESERVE not in l.etiquettes and not l.dependances & bloq][:3]
        if plus_loin:
            lignes.append(f"EN AVANCE, DU TROISIÈME JALON ({loin.titre}) : " + ", ".join(
                f"#{l.numero} « {l.titre} » ({l.machine})" for l in plus_loin))
        r.aujourd_hui += [f"#{l.numero} {l.titre} : il part quand le {'PC' if l.machine == 'pc' else 'VPS'} "
                          f"n'a plus rien dans {courant.titre} ni dans {apres.titre}." for l in plus_loin]
        r.aujourd_hui += [f"#{l.numero} {l.titre} : attend {', '.join(f'#{n}' for n in attendus[l.numero])}."
                          for l in attendent]
        r.jalon = f"{courant.titre} — {courant.pourcentage} %"
        raisons = {l.numero: raison for l, raison in r.bloques}
        du_jalon = sorted([(l, True) for l in ouvertes] + [(l, False) for l in fermees], key=lambda x: x[0].numero)
        r.avancement = [_avancement(l, ouvert, enfants, attendus.get(l.numero, []), raisons)
                        for l, ouvert in du_jalon if l.jalon == courant.numero and "lot" in l.etiquettes]
        lignes.append("AVANCEMENT DU JALON (le pilote l'ajoute lui-même sous le journal) :")
        lignes += r.avancement
    lignes.append("\nÀ FAIRE PAR LE PROPRIÉTAIRE :")
    r.a_faire = _a_faire(raisons_vps, _encore_vraies(raisons_pc, reponses_pc), veille or VEILLE, bloques, questions)
    lignes += r.a_faire
    r.texte = "\n".join(lignes)
    return r


def _publier(gh: GitHub, titre: str, corps: str, famille: str) -> int:
    """Une issue par journal, épinglée ; celles d'avant de la même famille
    (« Journal », « Boussole ») se désépinglent et se ferment : l'issue ouverte
    est toujours la dernière. Un commentaire au bas d'une issue unique ne se
    trouvait pas (29 septembre 2026)."""
    anciennes = [i["number"] for i in gh.issues("open")
                 if i["title"].startswith(famille) and "journal" in {e["name"] for e in i.get("labels") or []}]
    numero = gh.creer_issue(titre, corps, ["journal"])
    for n in anciennes:
        try:
            gh.desepingler(n)
        except Exception:  # noqa: BLE001 — une issue jamais épinglée ne retient pas le journal
            pass
        gh.fermer_issue(n, f"Le suivant : #{numero}.")
    try:
        gh.epingler(numero)
    except Exception:  # noqa: BLE001 — trois issues déjà épinglées ne retiennent pas le journal
        pass
    return numero


_ENTETES = ("> **Avancé** :", "> **Bloqué** :", "> **À faire** :", "### Ce qui a changé dans le jeu", "### Aujourd'hui")
_NUMERO = re.compile(r"#(\d+)")
_TOUTE_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def _infidele(texte: str, faits_du_matin: str) -> str | None:
    """Pourquoi le texte du chroniqueur ne peut pas paraître, ou None : il
    suit le gabarit, et chaque image et chaque numéro qu'il cite est dans les
    faits. Un journal qui invente ne paraît pas ; ceux du pilote le remplacent."""
    manquants = [e for e in _ENTETES if e not in texte]
    if manquants:
        return f"il manque {', '.join(f'« {e} »' for e in manquants)}"
    inventees = [u for u in _TOUTE_IMAGE.findall(texte) if u not in faits_du_matin]
    if inventees:
        return f"image absente des faits : {inventees[0]}"
    connus = set(_NUMERO.findall(faits_du_matin))
    inventes = sorted({n for n in _NUMERO.findall(texte) if n not in connus}, key=int)
    if inventes:
        return f"numéro absent des faits : #{inventes[0]}"
    return None


def _redaction_du_pilote(r: Releve, monde: list[str]) -> str:
    """Le journal écrit par le pilote seul, dans le gabarit du chroniqueur :
    moins bien tourné, jamais faux."""
    avance = " ; ".join(f"{l['nom']} est livré" for l in r.livres) or "aucun lot livré depuis hier"
    bloque = " ; ".join(f"#{l.numero} {l.titre} ({raison})" for l, raison in r.bloques) or "rien"
    gestes = [g.removeprefix("- ") for g in r.a_faire if g != "- rien"]
    lignes = [f"> **Avancé** : {avance}.", f"> **Bloqué** : {bloque}.",
              f"> **À faire** : {' ; '.join(gestes) or 'rien'}.", "", "### Ce qui a changé dans le jeu", ""]
    for url in monde:
        alt, legende = VUES[_vue(url)]
        lignes += [f"*{legende}*", f"![{alt}]({url})", ""]
    for l in r.livres:
        lignes.append(f"**[{l['nom']}]({l['url']})**")
        # Ce que le joueur y gagne, d'après son brief ; à défaut, la première
        # phrase du compte rendu du codeur.
        joueur = l.get("joueur") or ""
        fond = joueur.startswith("Fond.")
        joueur = joueur.removeprefix("Fond.").strip()
        paragraphe = joueur or next((x.strip() for x in (l["rendu"] or "").splitlines()
                                     if x.strip() and not x.startswith("#")), "")
        if paragraphe:
            phrase = paragraphe.split(". ")[0].rstrip(".") + "."
            lignes.append(f"Rien de visible encore, c'est la fondation de la suite : {phrase}" if fond else phrase)
        if l["capture"]:
            alt, legende = VUES[l["vue"]] if l.get("vue") else ("capture", "La capture de la révision livrée.")
            lignes += ["", f"*{legende}*", f"![{alt}]({l['capture']})"]
        lignes.append("")
    if not r.livres:
        lignes += ["Aucun lot livré depuis hier.", ""]
    lignes += ["### Aujourd'hui", "", *[f"- {l}" for l in r.aujourd_hui or ["Rien ne part aujourd'hui."]]]
    return "\n".join(lignes).rstrip()


def _annexe(r: Releve) -> str:
    """Ce que le pilote ajoute sous tout journal : l'avancement du jalon, lot
    par lot, et les détails de la chaîne, repliés."""
    lignes = []
    if r.jalon:
        lignes += [f"### Jalon {r.jalon}", "", *r.avancement, ""]
    lignes += ["<details><summary>Détails de la chaîne</summary>", "", "**Ce que la chaîne a vécu**", "", *r.vecu, ""]
    if r.machine:
        lignes += ["**La machine, changée en mode direct**", "",
                   *[f"- PR #{p['number']} {p['title']}" for p in r.machine], ""]
    if r.en_cours:
        lignes += ["**En cours**", "", *r.en_cours, ""]
    lignes.append("</details>")
    return "\n".join(lignes)


def _lire_image(url: str) -> bytes:
    """Le contenu d'une capture déjà publiée. Seules les adresses de la
    branche `journal` passent : on ne suit pas un lien inventé."""
    if not url.startswith("https://raw.githubusercontent.com/"):
        raise ValueError(url)
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read()


def _dedupliquer_images(texte: str, livres: list[dict], *, lire, cache: dict | None = None) -> str:
    """Retire du texte (et des lots) une image déjà montrée : mêmes octets
    que la photo du monde, ou qu'une capture précédente. Une image qu'on
    n'a pas pu lire reste : on ne devine pas qu'elle double une autre."""
    cache = cache if cache is not None else {}
    vus: set[str] = set()

    def garder(url: str) -> bool:
        if url not in cache:
            try:
                cache[url] = hashlib.sha256(lire(url)).hexdigest()
            except Exception:  # noqa: BLE001 — illisible ≠ identique
                cache[url] = None
        empreinte = cache[url]
        if empreinte is None:
            return True
        if empreinte in vus:
            return False
        vus.add(empreinte)
        return True

    def remplacer(m) -> str:
        return m.group(0) if garder(m.group(1)) else ""

    texte = _IMAGE.sub(remplacer, texte)
    restantes = set(_IMAGE.findall(texte))
    for lot in livres:
        if lot.get("capture") and lot["capture"] not in restantes:
            lot["capture"] = None
    return texte


def photo_du_monde(gh: GitHub, projet: Projet, maintenant: datetime, lectures: tuple[str, ...] = ()) -> list[str]:
    """Le monde tel que master le joue pendant un an : la terre du joueur
    parmi ses voisins, la faim en Europe, puis la carte de chaque `lectures`
    qu'un lot livré demande. Chaque journal porte au moins une image, même
    un jour sans lot livré : si aucune ne se rend, la carte d'avant."""
    jour = f"{maintenant:%Y-%m-%d}"
    with tempfile.TemporaryDirectory(prefix="journal-") as tmp:
        tmp = Path(tmp)
        fichiers = []
        grande = captures.carte_du_monde(projet.racine, tmp / "terre", ticks=ANNEE_DE_JEU, largeur=2400)
        zoom = grande and captures.zoom_sur_la_terre(grande, tmp / f"terre-{jour}.png")
        if zoom:
            fichiers.append(zoom)
        for lecture in dict.fromkeys(("faim", *lectures)):
            carte = captures.carte_du_monde(projet.racine, tmp / lecture, ticks=ANNEE_DE_JEU, lecture=lecture)
            if carte is not None:
                fichiers.append(carte.rename(tmp / f"{lecture}-{jour}.png"))
        if not fichiers:
            carte = captures.carte_du_monde(projet.racine, tmp / "monde")
            if carte is None:
                return []
            fichiers.append(carte.rename(tmp / f"monde-{jour}.png"))
        try:
            # Le journal partage la branche des captures avec les tours du pilote.
            depot = Depot(projet.racine, projet.branche_base, verrous=Verrous())
            return captures.publier(depot, gh.depot, fichiers, jour)
        except Exception:  # noqa: BLE001 — une photo manquée ne retient pas le journal
            return []


def _ranger_les_images(monde: list[str], livres: list[dict]) -> tuple[list[str], list[str]]:
    """Les images du matin en tête du journal, et celles d'une lecture
    demandée par un lot, à ce lot. Rend (en tête, lignes des faits)."""
    en_tete, par_vue = [], {}
    demandees = {l["lecture"] for l in livres if l.get("lecture")}
    for url in monde:
        vue = _vue(url)
        if vue in demandees and vue not in VUES_DU_MATIN:
            par_vue[vue] = url
        else:
            en_tete.append(url)
    lignes = []
    for l in livres:
        url = None if l.get("capture") else par_vue.get(l.get("lecture"))
        if url:
            l["capture"], l["vue"] = url, l["lecture"]
            alt, legende = VUES[l["vue"]]
            lignes.append(f"- {l['nom']} : ![{alt}]({url}) — {legende}")
    return en_tete, lignes


def ecrire(gh: GitHub, projet: Projet, *, maintenant: datetime | None = None, publier: bool = True,
           executeur=agents_mod.executer, dossier: Path | None = None, photographe=photo_du_monde,
           lire_image=None) -> str:
    maintenant = maintenant or datetime.now(timezone.utc)
    r = releve(gh, projet, maintenant)
    lectures = tuple(sorted({l["lecture"] for l in r.livres if l.get("lecture")}))
    monde = photographe(gh, projet, maintenant, lectures) if publier else []
    monde, des_lots = _ranger_les_images(monde, r.livres)
    texte = r.texte
    if des_lots:
        texte += "\n\nIMAGES DES LOTS (rendues ce matin sur master, une par lot qui en parle) :\n" + "\n".join(des_lots)
    if monde:
        photos = "".join(f"![{VUES[_vue(url)][0]}]({url}) — {VUES[_vue(url)][1]}\n" for url in monde)
        texte = f"LES IMAGES DU MATIN (master, le monde joué) :\n{photos}\n{texte}"
    lire = lire_image or _lire_image
    cache: dict[str, str | None] = {}
    texte = _dedupliquer_images(texte, r.livres, lire=lire, cache=cache)
    res = agents_mod.invoquer(projet.poste("chroniqueur"), prompts.chroniqueur(faits=texte),
                              dossier or projet.racine, projet.delai("chroniqueur"), executeur=executeur)
    if not (res.reussi and res.texte.strip()):
        pourquoi = f"Le chroniqueur n'a pas répondu ({'; '.join(res.essais) or f'code {res.code}'})"
    else:
        pourquoi = _infidele(res.texte, texte)
        pourquoi = pourquoi and f"Le texte du chroniqueur ({res.agent}) est écarté : {pourquoi}"
    if pourquoi:
        redaction, signature = _redaction_du_pilote(r, monde), f"{pourquoi}. Écrit par le pilote, à partir des faits."
    else:
        redaction, signature = res.texte.strip(), f"Écrit par {res.agent}."
    # Une même image collée deux fois (faits ou texte du chroniqueur) n'apparaît qu'une.
    redaction = _dedupliquer_images(redaction, [], lire=lire, cache=cache)
    corps = f"{redaction}\n\n{_annexe(r)}\n\n<sub>{signature}</sub>"
    if publier:
        _publier(gh, f"Journal du {maintenant:%d/%m/%Y}", corps, "Journal")
    return corps


def boussole(gh: GitHub, projet: Projet, *, maintenant: datetime | None = None, publier: bool = True,
             executeur=agents_mod.executer) -> str:
    maintenant = maintenant or datetime.now(timezone.utc)
    releve = faits(gh, projet, maintenant, heures=24 * 7)
    cap = (projet.racine / "CAP.md").read_text(encoding="utf-8")
    res = agents_mod.invoquer(projet.poste("boussole"), prompts.boussole(cap=cap, faits=releve),
                              projet.racine, projet.delai("boussole"), executeur=executeur)
    if res.reussi and res.texte.strip():
        corps = f"{res.texte.strip()}\n\n<sub>Écrit par {res.agent}.</sub>"
    else:
        corps = (f"La boussole n'a pas répondu ({'; '.join(res.essais) or res.code}). Les faits :\n\n"
                 f"```\n{releve}\n```")
    if publier:
        _publier(gh, f"Boussole de la semaine du {maintenant:%d/%m/%Y}", corps, "Boussole")
    return corps
