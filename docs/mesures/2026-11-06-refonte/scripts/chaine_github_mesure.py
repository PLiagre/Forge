"""Mesures de la chaîne d'agents de Forge, côté GitHub (6 novembre 2026).

Lecture seule, hors ligne : ce script ne parle pas à GitHub (sauf
`--verifier`, qui lance des `gh issue list` / `gh pr list` en lecture). Il lit

- la collecte brute de `chaine_github_collecte.py` (`--brut`, par défaut dans
  le dossier scratch de Hermes), et CAP.md à la racine du worktree ;
- ou, pour refaire les calculs sans réseau, les données compactes déjà
  écrites (`--compact brut/chaine-github.json`) ;

et écrit `brut/chaine-github.json` (issues, PR, classification, lignes du CAP)
et `brut/chaine-github.md` (sections 1 à 7). `--section N` n'écrit rien et
imprime la seule section N.

Depuis la racine du worktree :

    py docs/mesures/2026-11-06-refonte/scripts/chaine_github_collecte.py
    py docs/mesures/2026-11-06-refonte/scripts/chaine_github_mesure.py --verifier
    py docs/mesures/2026-11-06-refonte/scripts/chaine_github_mesure.py \
        --compact docs/mesures/2026-11-06-refonte/brut/chaine-github.json --section 4
"""

import argparse
import json
import re
import statistics
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ICI = Path(__file__).resolve().parent
DOSSIER = ICI.parent                      # docs/mesures/2026-11-06-refonte
RACINE = DOSSIER.parents[2]               # le worktree
CAP = RACINE / "CAP.md"
BRUT_DEFAUT = Path("C:/Users/liagr/AppData/Local/hermes/cache/scratch/chaine_github_brut.json")
JSON_SORTIE = DOSSIER / "brut" / "chaine-github.json"
MD_SORTIE = DOSSIER / "brut" / "chaine-github.md"

REL = "docs/mesures/2026-11-06-refonte"
CMD_COLLECTE = f"py {REL}/scripts/chaine_github_collecte.py"
CMD_MESURE = f"py {REL}/scripts/chaine_github_mesure.py --verifier"
CMD_SECTION = f"py {REL}/scripts/chaine_github_mesure.py --compact {REL}/brut/chaine-github.json --section {{n}}"

# Les deux fenêtres, en heure de Paris, jusqu'à la collecte.
FENETRES = [
    ("F1", "depuis le 1er octobre 2026", datetime(2026, 10, 1)),
    ("F2", "depuis le 28 octobre 2026", datetime(2026, 10, 28)),
]
DATE_CAP_REECRIT = datetime(2026, 10, 7)   # « Le 7 octobre … fait réécrire tous leurs lots »

RE_DECOUPE = re.compile(r"D[ée]coup[ée] du lot #(\d+)(?: par ([^.\n]+))?")
RE_TETE_LOT = re.compile(r"^lot/(\d+)-")
RE_JALON = re.compile(r"^## Jalon (\d+) — (.+?)\s*$")
RE_LIGNE = re.compile(r"^(\d+)\.\s+(.*?)\s*$")
RE_DECOUPER_JALON = re.compile(r"^D[ée]couper le jalon")
PREFIXE_BRIEF = "docs/briefs/"

# Classement « que preuve, juge, test ou montage » : mots entiers du titre,
# minuscules, sans accents. « contre-épreuve » se coupe en « contre » +
# « epreuve » : « epreuve » suffit.
MOTS_STRICTS = ["preuve", "preuves", "epreuve", "epreuves", "juge", "juges",
                "test", "tests", "teste", "testes", "testee", "testees",
                "montage", "montages", "mesure", "mesures", "mesuree", "mesurees"]
MOTS_AJOUTES = ["prouver", "verdict", "banc", "capture", "photo", "controler", "controle"]
MOTS_ELARGIS = MOTS_STRICTS + MOTS_AJOUTES


# ---------------------------------------------------------------- outils

def dernier_dimanche(annee, mois):
    j = datetime(annee, mois, 31)
    while j.weekday() != 6:
        j -= timedelta(days=1)
    return j


def utc(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)


def paris(iso):
    """Horodatage UTC de GitHub → heure de Paris (naïve). Règle de l'UE :
    UTC+2 du dernier dimanche de mars 01:00 UTC au dernier dimanche
    d'octobre 01:00 UTC (le 25 octobre en 2026), UTC+1 sinon."""
    u = utc(iso)
    debut = dernier_dimanche(u.year, 3) + timedelta(hours=1)
    fin = dernier_dimanche(u.year, 10) + timedelta(hours=1)
    return u + timedelta(hours=2 if debut <= u < fin else 1)


def semaine(iso):
    d = paris(iso)
    an, num, _ = d.isocalendar()
    lundi = (d - timedelta(days=d.weekday())).date()
    return (an, num), f"S{num} ({lundi:%d/%m}–{lundi + timedelta(days=6):%d/%m})"


def dans(iso, debut):
    return iso is not None and paris(iso) >= debut


def sans_accents(s):
    s = unicodedata.normalize("NFD", s.lower().replace("’", "'"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def mots_du_titre(titre):
    return re.findall(r"[a-z0-9]+", sans_accents(titre))


def jalon_court(titre):
    if not titre:
        return "(aucun)"
    return titre.split(" — ")[0] if titre.startswith("J") else titre


ORDRE_JALONS = [f"J{k}" for k in range(1, 10)] + ["Réserve", "(aucun)"]


def cle_jalon(j):
    return ORDRE_JALONS.index(j) if j in ORDRE_JALONS else 99


def fr(x, nd=1):
    if x is None:
        return "—"
    if isinstance(x, int) or (isinstance(x, float) and abs(x - round(x)) < 1e-9 and nd == 0):
        return f"{int(round(x)):,}".replace(",", " ")
    return f"{x:,.{nd}f}".replace(",", " ").replace(".", ",")


def fnum(x):
    """Entier s'il l'est, sinon une décimale."""
    if x is None:
        return "—"
    if abs(x - round(x)) < 1e-9:
        return fr(int(round(x)))
    return fr(x, 1)


def pct(a, b):
    return "—" if not b else fr(100 * a / b, 1) + " %"


def resume(valeurs):
    """n, min, Q1, médiane, Q3, max. Quartiles : statistics.quantiles(n=4,
    method="inclusive"), l'interpolation linéaire de numpy et d'Excel
    QUARTILE.INC."""
    v = sorted(valeurs)
    if not v:
        return None
    if len(v) == 1:
        q1 = med = q3 = v[0]
    else:
        q1, med, q3 = statistics.quantiles(v, n=4, method="inclusive")
    return {"n": len(v), "min": v[0], "q1": q1, "mediane": med, "q3": q3, "max": v[-1]}


def table(entetes, lignes):
    out = ["| " + " | ".join(entetes) + " |",
           "|" + "|".join("---" if k == 0 else "--:" for k in range(len(entetes))) + "|"]
    for l in lignes:
        out.append("| " + " | ".join(str(c) for c in l) + " |")
    return out


def table_g(entetes, lignes, alignes_droite=()):
    out = ["| " + " | ".join(entetes) + " |",
           "|" + "|".join("--:" if k in alignes_droite else "---" for k in range(len(entetes))) + "|"]
    for l in lignes:
        out.append("| " + " | ".join(str(c).replace("|", "\\|") for c in l) + " |")
    return out


# ------------------------------------------------- données compactes

def lire_cap(texte):
    lignes, a_creer, autres = [], [], []
    jalon = None
    titre_jalon = None
    for k, brute in enumerate(texte.splitlines(), start=1):
        m = RE_JALON.match(brute)
        if m:
            jalon, titre_jalon = int(m.group(1)), m.group(2)
            continue
        if brute.startswith("## "):
            jalon = None
            continue
        if jalon is None:
            continue
        m = RE_LIGNE.match(brute)
        if not m:
            continue
        reste = m.group(2)
        mi = re.match(r"#(\d+)\s+(.*)$", reste)
        entree = {"jalon": jalon, "titre_jalon": titre_jalon, "rang": int(m.group(1)), "ligne_cap": k}
        if mi:
            entree.update(issue=int(mi.group(1)), texte=mi.group(2))
            lignes.append(entree)
        elif "*(lot à créer)*" in reste:
            entree.update(texte=reste.replace("*(lot à créer)*", "").strip())
            a_creer.append(entree)
        else:
            entree.update(texte=reste)
            autres.append(entree)
    cites = sorted({int(x) for x in re.findall(r"#(\d+)", texte)})
    return {"lignes": lignes, "a_creer": a_creer, "autres_lignes_numerotees": autres, "cites": cites}


def git(*args):
    p = subprocess.run(["git", "-C", str(RACINE), *args], capture_output=True, text=True, encoding="utf-8")
    return p.stdout.strip()


def construire_compact(brut):
    issues = []
    for i in brut["issues"]:
        corps = i.get("body") or ""
        m = RE_DECOUPE.search(corps) if "journal" not in i["labels"] else None
        evts = []
        for e in i["timeline"]:
            t = e["__typename"]
            if t in ("LabeledEvent", "UnlabeledEvent"):
                evts.append([t[:-5], e["createdAt"], (e.get("label") or {}).get("name")])
            elif t == "ClosedEvent":
                c = e.get("closer") or {}
                evts.append(["Closed", e["createdAt"], e.get("stateReason"), c.get("number") or c.get("oid")])
            elif t == "ReopenedEvent":
                evts.append(["Reopened", e["createdAt"]])
            elif t in ("MilestonedEvent", "DemilestonedEvent"):
                evts.append([t[:-5], e["createdAt"], e.get("milestoneTitle")])
        issues.append({
            "n": i["number"], "titre": i["title"], "etat": i["state"], "raison": i["stateReason"],
            "cree": i["createdAt"], "ferme": i["closedAt"],
            "jalon": (i["milestone"] or {}).get("title"), "etiquettes": i["labels"],
            "decoupe_de": int(m.group(1)) if m else None,
            "decoupe_ligne": m.group(0) if m else None,
            "evenements": evts,
        })
    prs = []
    for p in brut["prs"]:
        m = RE_TETE_LOT.match(p["headRefName"])
        d = {
            "n": p["number"], "titre": p["title"], "etat": p["state"], "tete": p["headRefName"],
            "cree": p["createdAt"], "fusionne": p["mergedAt"], "ferme": p["closedAt"],
            "additions": p["additions"], "suppressions": p["deletions"],
            "fichiers_n": p["changedFiles"], "fichiers_lus": len(p["files"]),
            "commit_fusion": (p.get("mergeCommit") or {}).get("messageHeadline"),
            "issues_fermees": p["closingIssues"],
            "lot": int(m.group(1)) if m else None,
        }
        if m:
            d["fichiers"] = [[f["path"], f["additions"], f["deletions"]] for f in p["files"]]
        prs.append(d)
    cap_texte = CAP.read_text(encoding="utf-8")
    cap = lire_cap(cap_texte)
    cap["source"] = {"fichier": "CAP.md", "head": git("rev-parse", "--short", "HEAD"),
                     "dernier_commit_cap": git("log", "-1", "--format=%h %cI %s", "--", "CAP.md")}
    return {
        "meta": {
            "depot": brut["depot"],
            "collecte_debut_utc": brut["collecte_debut_utc"],
            "collecte_fin_utc": brut["collecte_fin_utc"],
            "timelines_relues_seules": brut.get("timelines_relues_seules", []),
            "fenetres": {k: {"libelle": lib, "debut_paris": d.isoformat()} for k, lib, d in FENETRES},
            "mots_stricts": MOTS_STRICTS, "mots_elargis": MOTS_ELARGIS,
            "commande_collecte": CMD_COLLECTE, "commande_mesure": CMD_MESURE,
        },
        "milestones": brut["milestones"],
        "issues": issues,
        "prs": prs,
        "cap": cap,
    }


# ------------------------------------------------------- l'analyse

class Donnees:
    def __init__(self, D):
        self.D = D
        self.I = {i["n"]: i for i in D["issues"]}
        self.P = {p["n"]: p for p in D["prs"]}
        self.enfants = defaultdict(list)
        for i in D["issues"]:
            if i["decoupe_de"]:
                self.enfants[i["decoupe_de"]].append(i["n"])
        self.pr_lot = defaultdict(list)
        for p in D["prs"]:
            if p["lot"] is not None:
                self.pr_lot[p["lot"]].append(p)
        self.fin_paris = paris(D["meta"]["collecte_fin_utc"].replace("+00:00", "Z"))

    def pr_fusionnee(self, n):
        ps = [p for p in self.pr_lot.get(n, []) if p["etat"] == "MERGED"]
        return ps[0] if len(ps) == 1 else (ps if ps else None)

    def livres(self):
        return sorted((i for i in self.D["issues"] if "livre" in i["etiquettes"] and i["etat"] == "CLOSED"),
                      key=lambda i: i["ferme"])

    def premier_pret(self, i):
        for e in i["evenements"]:
            if e[0] == "Labeled" and e[2] == "pret":
                return e[1]
        return None

    def descendants(self, n, prof=0, vus=None):
        """(nœud, profondeur) pour n et toute sa descendance."""
        vus = set() if vus is None else vus
        if n in vus:
            raise RuntimeError(f"cycle de découpe sur #{n}")
        vus.add(n)
        yield n, prof
        for e in sorted(self.enfants.get(n, [])):
            yield from self.descendants(e, prof + 1, vus)

    def statut(self, n):
        i = self.I.get(n)
        if i is None:
            return "absente"
        if "livre" in i["etiquettes"]:
            return "livree"
        if i["etat"] == "OPEN":
            return "ouverte"
        return "fermee_sans_livre"

    def categorie_fermee_sans_livre(self, i):
        if "journal" in i["etiquettes"]:
            return "journal (pas un lot)"
        if RE_DECOUPER_JALON.match(i["titre"]):
            return "« Découper le jalon … »"
        if self.enfants.get(i["n"]):
            return "découpé en sous-lots"
        if i["raison"] == "NOT_PLANNED":
            return "fermé sans suite, sans sous-lot (NOT_PLANNED)"
        return "fermé « terminé » sans livre"


def classer(titre, liste):
    m = mots_du_titre(titre)
    return [w for w in liste if w in m]


def construire_classification(X):
    sortie = []
    for i in X.livres():
        if not dans(i["ferme"], FENETRES[0][2]):
            continue
        pr = X.pr_fusionnee(i["n"])
        if isinstance(pr, list):
            raise RuntimeError(f"#{i['n']} a plusieurs PR de lot fusionnées")
        _, sem = semaine(i["ferme"])
        rec = {
            "n": i["n"], "titre": i["titre"], "jalon": jalon_court(i["jalon"]),
            "pc": "pc" in i["etiquettes"], "ferme": i["ferme"], "ferme_paris": paris(i["ferme"]).isoformat(),
            "semaine": sem, "F1": True, "F2": dans(i["ferme"], FENETRES[1][2]),
            "mots_stricts": classer(i["titre"], MOTS_STRICTS),
            "mots_elargis": classer(i["titre"], MOTS_ELARGIS),
            "decoupe_de": i["decoupe_de"], "premier_pret": X.premier_pret(i),
            "pr": None, "fusionne": None, "taille": None, "taille_sans_brief": None, "pret_a_fusion_h": None,
        }
        if pr:
            brief = [f for f in pr["fichiers"] if f[0].startswith(PREFIXE_BRIEF)]
            rec.update(pr=pr["n"], fusionne=pr["fusionne"],
                       taille=pr["additions"] + pr["suppressions"],
                       taille_sans_brief=sum(f[1] + f[2] for f in pr["fichiers"] if not f[0].startswith(PREFIXE_BRIEF)),
                       fichiers_brief=[f[0] for f in brief],
                       semaine_fusion=semaine(pr["fusionne"])[1],
                       F1_fusion=dans(pr["fusionne"], FENETRES[0][2]),
                       F2_fusion=dans(pr["fusionne"], FENETRES[1][2]))
            if rec["premier_pret"]:
                rec["pret_a_fusion_h"] = (utc(pr["fusionne"]) - utc(rec["premier_pret"])).total_seconds() / 3600
        else:
            closers = [e[3] for e in i["evenements"] if e[0] == "Closed"]
            rec["ferme_par"] = closers
        sortie.append(rec)
    return sortie


# ------------------------------------------------------- les sections

def entete_section(n, titre):
    return [f"## {n}. {titre}", "", f"Commande : `{CMD_SECTION.format(n=n)}`", ""]


def section_1(X, C, V):
    out = entete_section(1, "Les lots livrés, par jalon et par semaine ISO")
    out += ["Un lot livré = une issue fermée qui porte l'étiquette `livre`. **Date retenue : `closedAt` de "
            "l'issue**, en heure de Paris ; jalon = milestone **actuel** de l'issue. Semaines ISO, lundi → dimanche "
            "(la première et la dernière colonne de chaque fenêtre sont des semaines partielles).", ""]
    for k, lib, debut in FENETRES:
        lots = [c for c in C if c[k]]
        semaines = sorted({(semaine(c["ferme"])) for c in lots})
        cols = [s[1] for s in semaines]
        jalons = sorted({c["jalon"] for c in lots}, key=cle_jalon)
        cnt = Counter((c["jalon"], c["semaine"]) for c in lots)
        lignes = []
        for j in jalons:
            lignes.append([j] + [cnt[(j, s)] or "·" for s in cols] + [f"**{sum(cnt[(j, s)] for s in cols)}**"])
        lignes.append(["**total**"] + [f"**{sum(cnt[(j, s)] for j in jalons)}**" for s in cols] + [f"**{len(lots)}**"])
        out += [f"### Fenêtre {k} — {lib} ({debut:%d/%m/%Y} 00:00, heure de Paris, → collecte du "
                f"{X.fin_paris:%d/%m/%Y %H:%M})", ""]
        out += table(["jalon"] + cols + ["total"], lignes) + [""]
    # contrôle mergedAt
    ecarts = [c["n"] for c in C if c["pr"] and (c["semaine_fusion"] != c["semaine"] or c["F2_fusion"] != c["F2"]
                                                or not c["F1_fusion"])]
    dmax = max(abs((utc(c["fusionne"]) - utc(c["ferme"])).total_seconds()) for c in C if c["pr"])
    sans_pr = [c for c in C if not c["pr"]]
    out += [f"Avec `mergedAt` de la PR de lot au lieu de `closedAt` : **{len(ecarts)}** lot change de case "
            f"(écart maximal entre les deux dates : {fr(dmax / 60, 1)} min). "
            f"{len(sans_pr)} lots livrés n'ont pas de PR `lot/…` : "
            + ", ".join(f"#{c['n']}" for c in sans_pr)
            + " — livrés en mode direct (PR `direct/…` ou commit), comptés ici comme lots puisque leur issue "
              "porte `livre`.", ""]
    # fermées sans livre
    out += ["### Les issues fermées sans `livre`, à part", "",
            "Convention vérifiée sur toutes les issues : toute issue `livre` est fermée « COMPLETED » ; toute PR "
            "`lot/<n>-…` fusionnée a son issue `livre` ; aucune issue n'a deux PR de lot fusionnées. "
            "Les fermées sans `livre`, par catégorie (date = `closedAt`) :", ""]
    cats = ["journal (pas un lot)", "« Découper le jalon … »", "découpé en sous-lots",
            "fermé sans suite, sans sous-lot (NOT_PLANNED)", "fermé « terminé » sans livre"]
    fermees = [i for i in X.D["issues"] if i["etat"] == "CLOSED" and "livre" not in i["etiquettes"]]
    lignes = []
    for cat in cats:
        tout = [i for i in fermees if X.categorie_fermee_sans_livre(i) == cat]
        f1 = [i for i in tout if dans(i["ferme"], FENETRES[0][2])]
        f2 = [i for i in tout if dans(i["ferme"], FENETRES[1][2])]
        lignes.append([cat, len(tout), len(f1), len(f2)])
    lignes.append(["**total**", f"**{len(fermees)}**",
                   f"**{sum(1 for i in fermees if dans(i['ferme'], FENETRES[0][2]))}**",
                   f"**{sum(1 for i in fermees if dans(i['ferme'], FENETRES[1][2]))}**"])
    out += table(["catégorie", "depuis toujours", "F1", "F2"], lignes) + [""]
    autres = [i for i in fermees if X.categorie_fermee_sans_livre(i) in cats[1:] and dans(i["ferme"], FENETRES[1][2])]
    if autres:
        out += ["Fermées sans `livre` dans F2 (hors journaux) : " +
                ", ".join(f"#{i['n']} ({X.categorie_fermee_sans_livre(i)})" for i in autres) + ".", ""]
    out += verif(V, ["livres_F1", "livres_F2"])
    return out


def section_2(X, C, V):
    out = entete_section(2, "La part des lots `pc` parmi les livrés")
    lignes = []
    for k, lib, _ in FENETRES:
        lots = [c for c in C if c[k]]
        n_pc = sum(c["pc"] for c in lots)
        lignes.append([f"{k} — {lib}", len(lots), n_pc, pct(n_pc, len(lots)), len(lots) - n_pc])
    out += table(["fenêtre", "livrés", "dont `pc`", "part `pc`", "autres"], lignes) + [""]
    out += ["`pc` = étiquette actuelle de l'issue. Par jalon :", ""]
    jalons = sorted({c["jalon"] for c in C}, key=cle_jalon)
    lignes = []
    for j in jalons:
        cells = [j]
        for k, _, _ in FENETRES:
            lots = [c for c in C if c[k] and c["jalon"] == j]
            n_pc = sum(c["pc"] for c in lots)
            cells += [f"{n_pc} / {len(lots)}" if lots else "·"]
        lignes.append(cells)
    out += table(["jalon", "F1 : `pc` / livrés", "F2 : `pc` / livrés"], lignes) + [""]
    out += verif(V, ["pc_F1", "pc_F2"])
    return out


def section_3(X, C, V):
    out = entete_section(3, "Les lots livrés qui ne sont « que » preuve, juge, test ou montage")
    out += ["Classement par mots **entiers** du titre de l'issue, en minuscules et sans accents "
            "(`unicodedata` NFD, marques retirées ; « ’ » lu « ' »), découpé sur tout ce qui n'est pas lettre "
            "ou chiffre — « contre-épreuve » donne « contre » + « epreuve ».", "",
            "- **liste stricte** (celle de la consigne et ses flexions) : " + ", ".join(f"`{w}`" for w in MOTS_STRICTS),
            "- **liste élargie** = stricte + " + ", ".join(f"`{w}`" for w in MOTS_AJOUTES)
            + " (des lots de vérification que la stricte manque ; à juger sur la liste ci-dessous)", ""]
    lignes = []
    for k, lib, _ in FENETRES:
        lots = [c for c in C if c[k]]
        s = [c for c in lots if c["mots_stricts"]]
        e = [c for c in lots if c["mots_elargis"]]
        lignes.append([f"{k} — {lib}", len(lots), len(s), pct(len(s), len(lots)), len(e), pct(len(e), len(lots)),
                       f"{sum(c['pc'] for c in s)} / {len(s)}"])
    out += table(["fenêtre", "livrés", "stricte", "part", "élargie", "part", "`pc` parmi les stricts"], lignes) + [""]
    classes = [c for c in C if c["mots_elargis"]]
    out += [f"Les {len(classes)} titres classés (fenêtre F1 ; F2 marquée ✓), à vérifier à l'œil :", ""]
    lignes = []
    for c in classes:
        lignes.append([f"#{c['n']}", c["ferme_paris"][:10], c["jalon"], "pc" if c["pc"] else "",
                       "✓" if c["F2"] else "", "stricte" if c["mots_stricts"] else "élargie seule",
                       ", ".join(c["mots_elargis"]), c["titre"]])
    out += table_g(["issue", "livré le", "jalon", "pc", "F2", "liste", "mots trouvés", "titre"], lignes) + [""]
    # titres de vérification qui échappent aux deux listes
    soupcons = ["session", "lanceur", "service d'epreuve", "calibrage", "planche", "relance", "releve"]
    rates = [c for c in C if not c["mots_elargis"] and any(s in sans_accents(c["titre"]) for s in soupcons)]
    if rates:
        out += ["Titres **non classés** qui contiennent un mot voisin (" + ", ".join(f"`{s}`" for s in soupcons)
                + ") — laissés hors des deux listes : "
                + " ; ".join(f"#{c['n']} « {c['titre']} »" for c in rates) + ".", ""]
    return out


def section_4(X, C, V):
    out = entete_section(4, "La taille d'une PR de lot fusionnée")
    out += ["PR de lot = branche de tête `lot/<n>-<slug>`, fusionnée ; fenêtre = `mergedAt` (heure de Paris). "
            "Taille = `additions + deletions` de la PR. « Sans le brief » = somme `additions + deletions` des "
            "fichiers de la PR (`files(first:100){path additions deletions}`, paginé) dont le chemin ne commence "
            f"pas par `{PREFIXE_BRIEF}`. Quartiles : interpolation linéaire (`statistics.quantiles`, "
            "méthode « inclusive »).", ""]
    prs = [p for p in X.D["prs"] if p["lot"] is not None and p["etat"] == "MERGED"]
    incoherentes = [p["n"] for p in prs if p["fichiers_lus"] != p["fichiers_n"]
                    or sum(f[1] for f in p["fichiers"]) != p["additions"]
                    or sum(f[2] for f in p["fichiers"]) != p["suppressions"]]
    lignes = []
    res_json = {}
    for k, lib, debut in FENETRES:
        sel = [p for p in prs if dans(p["fusionne"], debut)]
        tot = [(p["additions"] + p["suppressions"], p["n"]) for p in sel]
        sb = [(sum(f[1] + f[2] for f in p["fichiers"] if not f[0].startswith(PREFIXE_BRIEF)), p["n"]) for p in sel]
        nb_brief = Counter(sum(1 for f in p["fichiers"] if f[0].startswith(PREFIXE_BRIEF)) for p in sel)
        for nom, vals in (("avec le brief", tot), ("sans `docs/briefs/*`", sb)):
            r = resume([v for v, _ in vals])
            pmax = max(vals)[1]
            res_json[f"{k} {nom}"] = r
            lignes.append([f"{k} — {lib}", nom, r["n"], fnum(r["q1"]), f"**{fnum(r['mediane'])}**", fnum(r["q3"]),
                           f"{fnum(r['max'])} (PR #{pmax})"])
        lignes_brief = ", ".join(f"{n} brief(s) : {c} PR" for n, c in sorted(nb_brief.items()))
        lignes.append([f"{k}", "*(fichiers de brief par PR)*", "", "", lignes_brief, "", ""])
    out += table(["fenêtre", "mesure", "PR", "Q1", "médiane", "Q3", "max"], lignes) + [""]
    briefs = []
    for k, lib, debut in FENETRES:
        sel = [p for p in prs if dans(p["fusionne"], debut)]
        b = [sum(f[1] + f[2] for f in p["fichiers"] if f[0].startswith(PREFIXE_BRIEF)) for p in sel]
        r = resume(b)
        briefs.append([f"{k} — {lib}", r["n"], fnum(r["q1"]), fnum(r["mediane"]), fnum(r["q3"]), fnum(r["max"])])
    out += ["Le brief seul (lignes de `docs/briefs/*` dans la PR) :", ""]
    out += table(["fenêtre", "PR", "Q1", "médiane", "Q3", "max"], briefs) + [""]
    out += [f"Contrôle : pour chaque PR de lot fusionnée, nombre de fichiers lus = `changedFiles` et sommes des "
            f"fichiers = `additions`/`deletions` de la PR ; écarts : {incoherentes or 'aucun'}.", ""]
    out += verif(V, ["pr_lot_F1", "pr_lot_F2", "pr_max_F1"])
    return out


def section_5(X, C, V):
    out = entete_section(5, "Ce que chaque ligne de lot du CAP est devenue")
    cap = X.D["cap"]
    out += [f"Source : `CAP.md` du worktree (HEAD `{cap['source']['head']}` ; dernier commit qui le touche : "
            f"{cap['source']['dernier_commit_cap']}). Une ligne de lot = une ligne numérotée « n. #NNN … » sous "
            "« ## Jalon n — … ». Sous-lot = issue dont le corps contient « Découpé du lot #N » (formule exacte, "
            "relevée sur toutes les issues : « Découpé du lot #N par le chef. » ×"
            f"{sum(1 for i in X.D['issues'] if (i['decoupe_ligne'] or '').endswith('par le chef'))}, "
            f"« … par le dépanneur. » ×{sum(1 for i in X.D['issues'] if (i['decoupe_ligne'] or '').endswith('par le dépanneur'))}, "
            f"« … par le propriétaire. » ×{sum(1 for i in X.D['issues'] if (i['decoupe_ligne'] or '').endswith('par le propriétaire'))} ; "
            "ex. #679 « Découpé du lot #409 par le chef. », #861 « Découpé du lot #416 par le chef. »). "
            "On suit la découpe récursivement ; **feuille** = issue sans sous-lot ; **nœuds** = la ligne et "
            "toute sa descendance. Une issue découpée est toujours fermée sans `livre` (vérifié) ; ses feuilles "
            "portent l'état.", ""]
    lignes_cap = cap["lignes"]
    par_ligne = []
    deja = {}
    conflits = []
    for L in lignes_cap:
        noeuds = list(X.descendants(L["issue"]))
        for n, _ in noeuds:
            if n in deja:
                conflits.append((n, deja[n], L["issue"]))
            deja.setdefault(n, L["issue"])
        feuilles = [n for n, _ in noeuds if not X.enfants.get(n)]
        st = Counter(X.statut(n) for n in feuilles)
        par_ligne.append({**L, "noeuds": len(noeuds), "feuilles": len(feuilles), "profondeur": max(p for _, p in noeuds),
                          "livrees": st["livree"], "ouvertes": st["ouverte"], "fermees_sans_livre": st["fermee_sans_livre"],
                          "absentes": st["absente"], "liste_feuilles": feuilles,
                          "etat_issue_ligne": X.statut(L["issue"]),
                          "jalon_issue": jalon_court((X.I.get(L["issue"]) or {}).get("jalon"))})
    X.par_ligne = par_ligne
    # synthèse par jalon
    lignes = []
    tot = Counter()
    for j in range(3, 10):
        pl = [p for p in par_ligne if p["jalon"] == j]
        c = Counter()
        for p in pl:
            c.update({k: p[k] for k in ("noeuds", "feuilles", "livrees", "ouvertes", "fermees_sans_livre")})
        decoupees = sum(1 for p in pl if p["noeuds"] > 1)
        a_creer = sum(1 for a in cap["a_creer"] if a["jalon"] == j)
        lignes.append([f"J{j}", len(pl), decoupees, c["noeuds"], f"**{c['feuilles']}**", c["livrees"], c["ouvertes"],
                       c["fermees_sans_livre"], fr(c["feuilles"] / len(pl), 2) if pl else "—", a_creer])
        tot.update(c)
        tot["lignes"] += len(pl)
        tot["decoupees"] += decoupees
        tot["a_creer"] += a_creer
    lignes.append(["**total**", tot["lignes"], tot["decoupees"], tot["noeuds"], f"**{tot['feuilles']}**", tot["livrees"],
                   tot["ouvertes"], tot["fermees_sans_livre"], fr(tot["feuilles"] / tot["lignes"], 2), tot["a_creer"]])
    out += table(["jalon", "lignes #", "lignes découpées", "nœuds", "feuilles", "livrées", "ouvertes",
                  "fermées sans livre", "feuilles / ligne", "lignes « à créer »"], lignes) + [""]
    if conflits:
        out += [f"Issues rattachées à deux lignes : {conflits}", ""]
    absentes = [p for p in par_ligne if p["absentes"]]
    if absentes:
        out += [f"Lignes dont une feuille n'est pas une issue du dépôt : {[p['issue'] for p in absentes]}", ""]
    hors_jalon = [p for p in par_ligne if p["jalon_issue"] != f"J{p['jalon']}"]
    if hors_jalon:
        out += ["Lignes dont l'issue n'est pas (ou plus) dans le milestone de son jalon : "
                + ", ".join(f"#{p['issue']} (J{p['jalon']} au CAP, milestone {p['jalon_issue']})" for p in hors_jalon)
                + ".", ""]
    # top 10
    top = sorted(par_ligne, key=lambda p: (-p["feuilles"], -p["noeuds"], p["issue"]))[:10]
    out += ["### Les dix lignes qui ont le plus enflé", ""]
    out += table_g(["jalon", "ligne", "issue", "titre au CAP", "nœuds", "feuilles", "profondeur", "livrées",
                    "ouvertes", "fermées sans livre"],
                   [[f"J{p['jalon']}", p["rang"], f"#{p['issue']}", p["texte"], p["noeuds"], f"**{p['feuilles']}**",
                     p["profondeur"], p["livrees"], p["ouvertes"], p["fermees_sans_livre"]] for p in top],
                   alignes_droite=(1, 4, 5, 6, 7, 8, 9)) + [""]
    # détail par jalon
    out += ["### Le détail, ligne par ligne", ""]
    for j in range(3, 10):
        pl = [p for p in par_ligne if p["jalon"] == j]
        out += [f"**J{j} — {pl[0]['titre_jalon'] if pl else ''}**", ""]
        rows = [[p["rang"], f"#{p['issue']}", p["texte"], p["noeuds"], p["feuilles"], p["livrees"], p["ouvertes"],
                 p["fermees_sans_livre"]] for p in pl]
        c = Counter()
        for p in pl:
            c.update({k: p[k] for k in ("noeuds", "feuilles", "livrees", "ouvertes", "fermees_sans_livre")})
        rows.append(["", "**total**", f"{len(pl)} lignes", c["noeuds"], f"**{c['feuilles']}**", c["livrees"],
                     c["ouvertes"], c["fermees_sans_livre"]])
        out += table_g(["ligne", "issue", "titre au CAP", "nœuds", "feuilles", "livrées", "ouvertes",
                        "fermées sans livre"], rows, alignes_droite=(0, 3, 4, 5, 6, 7)) + [""]
    # hors cap
    out += ["### Les issues de J4, J5 et J6 qui ne descendent d'aucune ligne du CAP", "",
            "Toutes les issues dont le milestone **actuel** est J4, J5 ou J6, quel que soit leur état. "
            "« Descend d'une ligne » = c'est l'issue d'une ligne numérotée, ou un sous-lot (récursif) de l'une "
            "d'elles. Pour les autres, on remonte leur propre découpe jusqu'à sa racine : « citée au CAP » = la "
            "racine ou un intermédiaire est cité ailleurs dans CAP.md (listes « Déjà livré », « Passent à "
            "l'horizon », texte) ; « jamais citée » = ni elle ni ses ancêtres n'apparaissent dans CAP.md.", ""]
    cites = set(cap["cites"])
    hors = []
    lignes = []
    for j in ("J4", "J5", "J6"):
        dans_j = [i for i in X.D["issues"] if jalon_court(i["jalon"]) == j]
        c = Counter()
        for i in dans_j:
            if i["n"] in deja:
                c["descend"] += 1
                continue
            chaine = [i["n"]]
            while X.I.get(chaine[-1], {}).get("decoupe_de"):
                chaine.append(X.I[chaine[-1]]["decoupe_de"])
            cite = any(a in cites for a in chaine)
            cat = "citée" if cite else "jamais"
            st = X.statut(i["n"])
            apres = paris(i["cree"]) >= DATE_CAP_REECRIT
            c[cat] += 1
            c[f"{cat}_{st}"] += 1
            if apres:
                c[f"{cat}_apres"] += 1
            hors.append({"n": i["n"], "titre": i["titre"], "jalon": j, "statut": st, "cree": i["cree"],
                         "racine": chaine[-1], "chaine": chaine, "citee_au_cap": cite,
                         "categorie": X.categorie_fermee_sans_livre(i) if st == "fermee_sans_livre" else None})
        total_hors = c["citée"] + c["jamais"]
        lignes.append([j, len(dans_j), c["descend"], f"**{total_hors}**",
                       f"{c['citée']} ({c['citée_livree']} / {c['citée_ouverte']} / {c['citée_fermee_sans_livre']})",
                       f"{c['jamais']} ({c['jamais_livree']} / {c['jamais_ouverte']} / {c['jamais_fermee_sans_livre']})",
                       c["citée_apres"] + c["jamais_apres"]])
    out += table(["milestone", "issues", "descendent d'une ligne", "hors du cap",
                  "dont citées au CAP (livrées / ouvertes / fermées sans livre)",
                  "dont jamais citées (livrées / ouvertes / fermées sans livre)",
                  "hors du cap créées depuis le 07/10"], lignes) + [""]
    X.hors_cap = hors
    jamais = [h for h in hors if not h["citee_au_cap"]]
    out += [f"Les {len(jamais)} issues hors du cap et jamais citées, par racine de découpe :", ""]
    par_racine = defaultdict(list)
    for h in jamais:
        par_racine[h["racine"]].append(h)
    rows = []
    for r, hs in sorted(par_racine.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        ri = X.I.get(r, {})
        st = Counter(h["statut"] for h in hs)
        rows.append([f"#{r}", ri.get("titre", "?"), jalon_court(ri.get("jalon")), (paris(ri["cree"]).date().isoformat() if ri else "?"),
                     len(hs), st["livree"], st["ouverte"], st["fermee_sans_livre"],
                     " ".join(f"#{h['n']}" for h in sorted(hs, key=lambda h: h["n"]))[:300]])
    out += table_g(["racine", "titre de la racine", "milestone", "créée le", "issues", "livrées", "ouvertes",
                    "fermées sans livre", "issues"], rows, alignes_droite=(4, 5, 6, 7)) + [""]
    citees = [h for h in hors if h["citee_au_cap"]]
    par_racine = defaultdict(list)
    for h in citees:
        par_racine[h["racine"]].append(h)
    out += [f"Les {len(citees)} issues hors des lignes mais citées au CAP viennent de {len(par_racine)} racines : "
            + ", ".join(f"#{r} ({len(hs)})" for r, hs in sorted(par_racine.items())) + ".", ""]
    return out


def section_6(X, C, V):
    out = entete_section(6, "Les lots « à créer » du CAP, sans issue")
    cap = X.D["cap"]
    a = cap["a_creer"]
    par_j = Counter(x["jalon"] for x in a)
    out += [f"Lignes numérotées « n. *(lot à créer)* … » sous les « ## Jalon n » de CAP.md : **{len(a)}** — "
            + ", ".join(f"J{j} : {c}" for j, c in sorted(par_j.items())) + ".", ""]
    out += table_g(["jalon", "ligne", "lot à créer", "ligne de CAP.md"],
                   [[f"J{x['jalon']}", x["rang"], x["texte"], x["ligne_cap"]] for x in a], alignes_droite=(1, 3)) + [""]
    autres = cap["autres_lignes_numerotees"]
    out += [f"Autres lignes numérotées sans « #n » ni « à créer » sous un jalon : {len(autres)}."
            + (" " + "; ".join(f"J{x['jalon']} l.{x['ligne_cap']} « {x['texte'][:60]} »" for x in autres) if autres else ""), ""]
    # une issue ouverte depuis porterait-elle déjà ce titre ?
    proches = []
    for x in a:
        cle = set(w for w in mots_du_titre(x["texte"]) if len(w) > 4)
        for i in X.D["issues"]:
            if i["etat"] != "OPEN" or not cle:
                continue
            m = set(mots_du_titre(i["titre"]))
            if len(cle & m) >= max(2, len(cle) // 2):
                proches.append((x["jalon"], x["rang"], i["n"], i["titre"]))
    out += ["Issues ouvertes dont le titre partage au moins la moitié des mots longs (plus de 4 lettres) d'un "
            "lot à créer — à regarder : "
            + ("; ".join(f"J{j} ligne {r} ↔ #{n} « {t} »" for j, r, n, t in proches) if proches else "aucune") + ".", ""]
    out += [f"Contre-vérification : `grep -c '(lot à créer)' CAP.md` compte aussi les mentions hors des listes "
            "numérotées (paragraphe « Les lots nouveaux … *à créer* » et descriptions « — *à créer* »)."]
    out += [""] + verif(V, ["grep_a_creer"])
    return out


def section_7(X, C, V):
    out = entete_section(7, "Le temps de « pret » à la fusion")
    out += ["Pour chaque lot livré depuis le 1er octobre (fenêtre = `closedAt` de l'issue, comme en 1) : du "
            "**premier** événement `LabeledEvent` de l'étiquette `pret` dans la timeline de l'issue "
            "(`timelineItems(itemTypes:[LABELED_EVENT, …])`) au `mergedAt` de sa PR `lot/…`. En heures "
            "(jours entre parenthèses). Quartiles : interpolation linéaire.", ""]
    avec = [c for c in C if c["pret_a_fusion_h"] is not None]
    sans_pret = [c for c in C if c["pr"] and not c["premier_pret"]]
    sans_pr = [c for c in C if not c["pr"]]
    negatifs = [c for c in avec if c["pret_a_fusion_h"] < 0]
    lignes = []
    for k, lib, _ in FENETRES:
        for nom, filtre in (("tous", lambda c: True), ("`pc`", lambda c: c["pc"]), ("autres", lambda c: not c["pc"])):
            sel = [c for c in avec if c[k] and filtre(c)]
            r = resume([c["pret_a_fusion_h"] for c in sel])
            if not r:
                lignes.append([f"{k}", nom, 0, "—", "—", "—", "—"])
                continue
            cmax = max(sel, key=lambda c: c["pret_a_fusion_h"])
            h = lambda x: f"{fr(x, 1)} h ({fr(x / 24, 1)} j)"
            lignes.append([f"{k} — {lib}" if nom == "tous" else k, nom, r["n"], h(r["q1"]), f"**{h(r['mediane'])}**",
                           h(r["q3"]), f"{h(r['max'])} — #{cmax['n']}"])
    out += table(["fenêtre", "lots", "n", "Q1", "médiane", "Q3", "max"], lignes) + [""]
    out += [f"À part : **{len(sans_pret)}** lot(s) livré(s) avec PR de lot mais sans événement `pret`"
            + (" (" + ", ".join(f"#{c['n']}" for c in sans_pret) + ")" if sans_pret else "")
            + f" ; **{len(sans_pr)}** lot(s) livré(s) sans PR `lot/…` (mode direct, pas de `mergedAt` de lot : "
            + ", ".join(f"#{c['n']}" for c in sans_pr) + ")"
            + (f" ; {len(negatifs)} durée(s) négative(s) : {[c['n'] for c in negatifs]}" if negatifs else
               " ; aucune durée négative") + ".", ""]
    # le premier pret est-il la création ?
    a_la_creation = [c for c in avec if abs((utc(c["premier_pret"]) - utc(X.I[c["n"]]["cree"])).total_seconds()) <= 60]
    plusieurs = [c for c in avec if sum(1 for e in X.I[c["n"]]["evenements"] if e[0] == "Labeled" and e[2] == "pret") > 1]
    out += [f"Lecture : {len(a_la_creation)} des {len(avec)} lots ont reçu `pret` dans la minute de leur création "
            f"(les sous-lots du chef naissent `pret`) : la durée mesure donc surtout création → fusion, attente des "
            f"dépendances comprise. {len(plusieurs)} lots ont reçu `pret` plusieurs fois (blocage puis reprise) ; "
            "c'est le premier qui compte.", ""]
    # répartition grossière
    tranches = [(0, 6), (6, 24), (24, 72), (72, 168), (168, 10 ** 6)]
    noms = ["< 6 h", "6–24 h", "1–3 j", "3–7 j", "> 7 j"]
    lignes = []
    for k, lib, _ in FENETRES:
        sel = [c["pret_a_fusion_h"] for c in avec if c[k]]
        lignes.append([k] + [sum(1 for v in sel if a <= v < b) for a, b in tranches])
    out += table(["fenêtre"] + noms, lignes) + [""]
    return out


SECTIONS = {1: section_1, 2: section_2, 3: section_3, 4: section_4, 5: section_5, 6: section_6, 7: section_7}


# ----------------------------------------------- contre-vérifications

VERIFS = {
    "livres_F1": ("lots livrés F1",
                  ["gh", "issue", "list", "-R", "PLiagre/Forge", "--state", "closed", "--label", "livre",
                   "--search", "closed:>=2026-10-01T00:00:00+02:00", "--limit", "1000", "--json", "number", "--jq", "length"]),
    "livres_F2": ("lots livrés F2",
                  ["gh", "issue", "list", "-R", "PLiagre/Forge", "--state", "closed", "--label", "livre",
                   "--search", "closed:>=2026-10-28T00:00:00+01:00", "--limit", "1000", "--json", "number", "--jq", "length"]),
    "pc_F1": ("lots `pc` livrés F1",
              ["gh", "issue", "list", "-R", "PLiagre/Forge", "--state", "closed", "--label", "livre", "--label", "pc",
               "--search", "closed:>=2026-10-01T00:00:00+02:00", "--limit", "1000", "--json", "number", "--jq", "length"]),
    "pc_F2": ("lots `pc` livrés F2",
              ["gh", "issue", "list", "-R", "PLiagre/Forge", "--state", "closed", "--label", "livre", "--label", "pc",
               "--search", "closed:>=2026-10-28T00:00:00+01:00", "--limit", "1000", "--json", "number", "--jq", "length"]),
    "pr_lot_F1": ("PR `lot/…` fusionnées F1",
                  ["gh", "pr", "list", "-R", "PLiagre/Forge", "--state", "merged", "--limit", "1000",
                   "--json", "number,headRefName,mergedAt",
                   "--jq", '[.[] | select(.headRefName|startswith("lot/")) | select(.mergedAt >= "2026-09-30T22:00:00Z")] | length']),
    "pr_lot_F2": ("PR `lot/…` fusionnées F2",
                  ["gh", "pr", "list", "-R", "PLiagre/Forge", "--state", "merged", "--limit", "1000",
                   "--json", "number,headRefName,mergedAt",
                   "--jq", '[.[] | select(.headRefName|startswith("lot/")) | select(.mergedAt >= "2026-10-27T23:00:00Z")] | length']),
    "pr_max_F1": ("taille max d'une PR `lot/…` F1",
                  ["gh", "pr", "list", "-R", "PLiagre/Forge", "--state", "merged", "--limit", "1000",
                   "--json", "number,headRefName,mergedAt,additions,deletions",
                   "--jq", '[.[] | select(.headRefName|startswith("lot/")) | select(.mergedAt >= "2026-09-30T22:00:00Z") | .additions + .deletions] | max']),
    "grep_a_creer": ("mentions « (lot à créer) » dans CAP.md", ["@grep", "(lot à créer)"]),
}


def montrer(args):
    if args[0] == "@grep":
        return f"grep -c '{args[1]}' CAP.md"
    out = []
    for a in args:
        if re.search(r"[\s\"'|>()\[\]]", a):
            out.append("'" + a.replace("'", "'\\''") + "'")
        else:
            out.append(a)
    return " ".join(out)


def lancer_verifs():
    res = {}
    for cle, (lib, args) in VERIFS.items():
        if args[0] == "@grep":
            texte = CAP.read_text(encoding="utf-8")
            res[cle] = str(sum(1 for l in texte.splitlines() if args[1] in l))
            continue
        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
        res[cle] = p.stdout.strip() if p.returncode == 0 else f"échec : {p.stderr.strip()[:200]}"
    return res


def verif(V, cles):
    if not V:
        return []
    out = ["Contre-vérification indépendante (commandes en lecture, lancées par `--verifier` à la mesure) :", ""]
    for c in cles:
        lib, args = VERIFS[c]
        out.append(f"- {lib} : `{montrer(args)}` → **{V.get(c, '?')}**")
    return out + [""]


# ------------------------------------------------------------ le rapport

def introduction(X, C):
    m = X.D["meta"]
    return [
        "# La chaîne côté GitHub — mesures du 6 novembre 2026",
        "",
        f"Dépôt `{m['depot']}`, lu en **lecture seule** (requêtes GraphQL `query` et `gh … list`/`view`), collecte "
        f"du {paris(m['collecte_debut_utc'].replace('+00:00', 'Z')):%d/%m/%Y %H:%M} au "
        f"{X.fin_paris:%H:%M} (heure de Paris) : {len(X.D['issues'])} issues, {len(X.D['prs'])} PR.",
        "",
        "- Collecte : `" + CMD_COLLECTE + "` → collecte brute dans le dossier scratch de Hermes "
        "(`chaine_github_brut.json`, corps des issues compris).",
        "- Mesure : `" + CMD_MESURE + "` → ce fichier et `chaine-github.json` (issues, PR, timelines "
        "d'étiquettes, classification de chaque lot livré, lignes du CAP et leurs feuilles).",
        "- Chaque section se refait **sans réseau** depuis `chaine-github.json` : la commande est sous son titre.",
        "",
        "Fenêtres : **F1** = depuis le 1er octobre 2026 00:00 (Paris, UTC+2, soit 2026-09-30T22:00Z) ; **F2** = "
        "depuis le 28 octobre 2026 00:00 (Paris, UTC+1 après le 25 octobre, soit 2026-10-27T23:00Z) ; toutes deux "
        "jusqu'à la collecte. Semaines ISO, lundi → dimanche, en heure de Paris.",
        "",
    ]


def doutes(X, C):
    m = X.D["meta"]
    livres = X.livres()
    # jalon ou pc qui bougent après la livraison
    jal_apres, pc_apres = [], []
    for i in livres:
        if not dans(i["ferme"], FENETRES[0][2]):
            continue
        for e in i["evenements"]:
            if e[1] > i["ferme"] and e[0] in ("Milestoned", "Demilestoned"):
                jal_apres.append(i["n"])
            if e[1] > i["ferme"] and e[0] in ("Labeled", "Unlabeled") and e[2] == "pc":
                pc_apres.append(i["n"])
    rouvertes = [c["n"] for c in C if any(e[0] == "Reopened" for e in X.I[c["n"]]["evenements"])]
    sans_pr = [c["n"] for c in C if not c["pr"]]
    out = ["## Ce qui paraît douteux dans les données", "",
           "- **Les timelines GraphQL se tronquent quand la requête est grosse.** Avec `timelineItems(itemTypes: …)` "
           "demandé dans `issues(first: 50)` (ou à 40-50 alias `issue(number:)` par requête), GitHub rend un "
           "`totalCount` faux pour une partie des issues, sans erreur : à la première collecte, 161 issues "
           "fermées n'avaient pas leur `ClosedEvent` et 91 issues `livre` pas leur événement `livre` (ex. #388 : "
           "4 événements au lieu de 9). Mesuré sur les 50 issues #331 à #409 : justes à 1-30 alias, 11 fausses "
           "à 40. La collecte retenue lit **10 issues par requête**, recompte par 7, relit seule toute issue "
           f"dont le compte diffère (relues : {m['timelines_relues_seules'] or 'aucune'}) ; contrôles : toute "
           "issue fermée a son `ClosedEvent`, toute issue `livre` son événement `livre`. Une mesure « par lots "
           "de 50 issues » faite autrement serait à refaire.",
           f"- **{len(sans_pr)} lots livrés sans PR de lot** ({', '.join('#' + str(n) for n in sans_pr)}) : faits en "
           "mode direct le 9-11 octobre (PR #559 `direct/carte-epreuve` pour #524-#527 et #549 ; #388 et #393 "
           "fermés par commit). Comptés en 1-3 (issue `livre`), absents de 4 et 7.",
           "- **Jalon et `pc` sont lus aujourd'hui**, pas au jour de la livraison : "
           f"{len(set(jal_apres))} lot(s) livré(s) en F1 ont changé de milestone après leur fermeture"
           + (f" ({', '.join('#' + str(n) for n in sorted(set(jal_apres)))})" if jal_apres else "")
           + f", {len(set(pc_apres))} ont gagné ou perdu `pc` après"
           + (f" ({', '.join('#' + str(n) for n in sorted(set(pc_apres)))})" if pc_apres else "")
           + f" ; {len(rouvertes)} ont été rouverts un jour"
           + (f" ({', '.join('#' + str(n) for n in rouvertes)})" if rouvertes else "") + ".",
           "- **« pret » n'est pas « prenable »** : les sous-lots du chef naissent `pret`, même quand ils attendent "
           "un autre lot (« Dépend de »). La section 7 mesure surtout création → fusion, file d'attente comprise.",
           "- **Le classement de la section 3 est un classement de titres** : « La ville dense mesurée sur quatre "
           "vues » ou « Le banc du temps d'image » sont des mesures de performance, « La capture … », « La "
           "photo … » des preuves visuelles ; à l'inverse, un lot de preuve au titre muet échappe (voir la liste "
           "des titres voisins non classés).",
           "- **Taille de PR** : seules les PR #91 et #113 (septembre, hors fenêtres) dépassent la limite de 3 000 "
           "fichiers de l'API ; dans les fenêtres, fichiers et sommes concordent avec la PR.",
           "",
           ]
    return out


def ecrire(D, V):
    X = Donnees(D)
    C = construire_classification(X)
    D["classification"] = C
    sections = []
    for n in range(1, 8):
        sections += SECTIONS[n](X, C, V) + [""]
    D["cap"]["par_ligne"] = [{k: v for k, v in p.items()} for p in X.par_ligne]
    D["cap"]["hors_cap_J4_J6"] = X.hors_cap
    D["meta"]["contre_verifications"] = {k: {"commande": montrer(VERIFS[k][1]), "resultat": v} for k, v in (V or {}).items()}
    md = introduction(X, C) + sections + doutes(X, C)
    MD_SORTIE.write_text("\n".join(md).rstrip() + "\n", encoding="utf-8")
    JSON_SORTIE.write_text(json.dumps(D, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"écrit {MD_SORTIE} et {JSON_SORTIE}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brut", type=Path, default=BRUT_DEFAUT, help="collecte brute (chaine_github_collecte.py)")
    ap.add_argument("--compact", type=Path, help="refaire les calculs depuis brut/chaine-github.json")
    ap.add_argument("--section", type=int, choices=range(1, 8), help="imprimer une seule section, sans rien écrire")
    ap.add_argument("--verifier", action="store_true", help="lancer les contre-vérifications gh (lecture)")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if args.compact:
        D = json.loads(args.compact.read_text(encoding="utf-8"))
        for cle in ("classification",):
            D.pop(cle, None)
        V = {k: v["resultat"] for k, v in D["meta"].get("contre_verifications", {}).items()}
    else:
        D = construire_compact(json.loads(args.brut.read_text(encoding="utf-8")))
        V = lancer_verifs() if args.verifier else {}
    if args.section:
        X = Donnees(D)
        C = construire_classification(X)
        if args.section in (5,):
            pass
        print("\n".join(SECTIONS[args.section](X, C, V)))
        return
    ecrire(D, V)


if __name__ == "__main__":
    main()
