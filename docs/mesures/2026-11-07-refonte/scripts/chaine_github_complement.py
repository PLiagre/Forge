"""Compléments de la mesure de la chaîne GitHub (7 novembre 2026).

À lancer APRÈS chaine_github_mesure.py (qui réécrit chaine-github.md/json) :

    py docs/mesures/2026-11-07-refonte/scripts/chaine_github_complement.py [--hors-ligne]

Lit brut/chaine-github.json, et ajoute à brut/chaine-github.md (idempotent) :
  3bis  les lots livrés jugés par les FICHIERS de leur PR (tous, puis un
        échantillon de 15 relu par `gh pr diff <n> --name-only`) ;
  5bis  médiane et maximum par ligne du CAP ;
  6bis  recherche d'une issue ouverte au titre approchant de chaque « lot à créer » ;
  7     l'état courant (étiquettes des issues ouvertes par jalon, PR ouvertes) ;
l'ancienne section 7 (délai pret -> fusion) devient la section 8.
Seuls accès réseau : `gh pr diff --name-only` et `gh api` GET (milestones),
sauf --hors-ligne. Aucune mutation.
"""
import argparse
import json
import random
import re
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import chaine_github_mesure as M  # noqa: E402

REL = "docs/mesures/2026-11-07-refonte"
CMD = f"py {REL}/scripts/chaine_github_complement.py"
MARQUE = "<!-- complement -->"

RE_TEST = re.compile(r"(^|/)(tests?|Tests?)/|(^|/)test_[^/]*\.py$|Tests?\.cs$")
RE_EPREUVE = re.compile(r"(^|/)pc/|/Editor/(Captures/|[^/]*(Epreuve|Preuve|Capture|Relance)[^/]*$)|"
                        r"(^|/)(epreuve|preuve)[^/]*$")
HORS_PRODUIT = {"brief", "doc", "test", "epreuve"}


def categorie(chemin):
    if chemin.startswith("docs/briefs/"):
        return "brief"
    if chemin.startswith("docs/") or chemin.endswith(".md"):
        return "doc"
    if RE_TEST.search(chemin):
        return "test"
    if RE_EPREUVE.search(chemin):
        return "epreuve"
    return "produit"


def classer_pr(p):
    cats = Counter(categorie(f[0]) for f in p["fichiers"])
    return cats, all(c in HORS_PRODUIT for c in cats)


def fichiers_gh(n):
    r = subprocess.run(["gh", "pr", "diff", str(n), "--name-only"], capture_output=True, text=True, encoding="utf-8")
    return sorted(l for l in r.stdout.split("\n") if l.strip()) if r.returncode == 0 else None


def section_3bis(D, X, C, hors_ligne):
    out = ["## 3bis. Le même classement par les fichiers de la PR (contrôle de la section 3)", "",
           f"Commande : `{CMD}` (échantillon : `gh pr diff <n> --name-only`).", "",
           "Règle des fichiers, par chemin, dans cet ordre : `brief` = `docs/briefs/` ; `doc` = autre `docs/` ou `*.md` "
           "(`docs/mesures/…` = rendus d'épreuve) ; `test` = dossier `tests/` ou `Tests/`, `test_*.py`, `*Test(s).cs` ; "
           "`epreuve` = `pc/…`, `Editor/Captures/`, `Editor/*Epreuve|Preuve|Capture|Relance*`, fichier nommé "
           "`epreuve*`/`preuve*` ; `produit` = tout le reste (`jeu/sim/*.py`, `3d/unity/Assets/…` hors tests et "
           "Editor-épreuve, `3d/local3d/…`, `jeu/data/…`). Une PR « hors produit » = aucun fichier `produit`.", ""]
    prs = {p["n"]: p for p in D["prs"] if p["lot"] is not None and p["etat"] == "MERGED"}
    res = {}
    lignes = []
    for k, lib, _ in M.FENETRES:
        lots = [c for c in C if c[k] and c["pr"]]
        hp_n = {c["n"] for c in lots if classer_pr(prs[c["pr"]])[1]}
        strict = {c["n"] for c in lots if c["mots_stricts"]}
        elarg = {c["n"] for c in lots if c["mots_elargis"]}
        r = {"lots_avec_pr": len(lots), "hors_produit": len(hp_n), "titre_strict": len(strict),
             "hors_produit_et_titre_strict": len(hp_n & strict), "titre_strict_avec_produit": len(strict - hp_n),
             "hors_produit_titre_muet": len(hp_n - elarg), "titre_elargi": len(elarg),
             "hors_produit_ou_titre_strict": len(hp_n | strict)}
        res[k] = r
        lignes.append([f"{k} — {lib}", r["lots_avec_pr"], f"{r['hors_produit']} ({M.pct(r['hors_produit'], r['lots_avec_pr'])})",
                       f"{r['titre_strict']} ({M.pct(r['titre_strict'], r['lots_avec_pr'])})", r["hors_produit_et_titre_strict"],
                       r["titre_strict_avec_produit"], r["hors_produit_titre_muet"]])
    out += M.table(["fenêtre", "lots avec PR lot/", "PR sans fichier `produit`", "titre classé strict",
                    "les deux", "titre strict mais PR touche du produit", "PR hors produit, titre muet"], lignes) + [""]
    rnd = random.Random(20261107)
    F1 = [c for c in C if c["F1"] and c["pr"]]
    pool_s = sorted(c["n"] for c in F1 if c["mots_stricts"])
    pool_n = sorted(c["n"] for c in F1 if not c["mots_elargis"])
    ech = sorted(rnd.sample(pool_s, 10)) + sorted(rnd.sample(pool_n, 5))
    lot = {c["n"]: c for c in C}
    rows, ecarts, detail = [], 0, []
    for n in ech:
        c = lot[n]
        p = prs[c["pr"]]
        cats, hp = classer_pr(p)
        stock = sorted(f[0] for f in p["fichiers"])
        live = None if hors_ligne else fichiers_gh(p["n"])
        concord = "—" if live is None else ("oui" if live == stock else "NON")
        ecarts += concord == "NON"
        rows.append([f"#{n}", f"#{p['n']}", "strict" if c["mots_stricts"] else "non classé", c["titre"],
                     ", ".join(f"{a} {b}" for a, b in sorted(cats.items())), "oui" if hp else "non", concord])
        detail.append({"lot": n, "pr": p["n"], "titre_strict": bool(c["mots_stricts"]), "categories": dict(cats),
                       "hors_produit": hp, "gh_diff_concorde": concord, "fichiers": stock})
    out += ["### Échantillon de 15 lots (F1, graine `random.Random(20261107)`) : 10 titres stricts + 5 titres non classés", "",
            "Fichiers relus par `gh pr diff <n> --name-only` et comparés à la collecte GraphQL (colonne « gh = collecte »).", ""]
    out += M.table_g(["lot", "PR", "titre", "intitulé", "fichiers par catégorie", "hors produit", "gh = collecte"], rows) + [""]
    ok_s = sum(1 for r in detail if r["titre_strict"] and r["hors_produit"])
    ok_n = sum(1 for r in detail if not r["titre_strict"] and not r["hors_produit"])
    out += [f"Lecture : sur les 10 titres stricts, {ok_s} ont une PR sans fichier `produit` ; sur les 5 non classés, "
            f"{ok_n} touchent bien du produit. Écarts entre `gh pr diff` et la collecte : {ecarts}.", ""]
    res["echantillon"] = detail
    res["echantillon_stats"] = {"stricts_hors_produit": ok_s, "non_classes_avec_produit": ok_n, "ecarts_gh": ecarts}
    muets = [c for c in F1 if classer_pr(prs[c["pr"]])[1] and not c["mots_elargis"]]
    out += [f"PR « hors produit » dont le titre n'a aucun mot de la liste (F1, {len(muets)}) : "
            + " ; ".join(f"#{c['n']} « {c['titre']} »" for c in muets) + ".", ""]
    res["hors_produit_titre_muet_F1"] = [c["n"] for c in muets]
    stricts_produit = [c for c in F1 if c["mots_stricts"] and not classer_pr(prs[c["pr"]])[1]]
    out += [f"Titres stricts dont la PR touche pourtant du produit (F1, {len(stricts_produit)}) : "
            + " ; ".join(f"#{c['n']} « {c['titre']} »" for c in stricts_produit) + ".", ""]
    res["titre_strict_avec_produit_F1"] = [c["n"] for c in stricts_produit]
    return out, res


def section_5bis(D, C):
    pl = D["cap"]["par_ligne"]
    out = ["## 5bis. Médiane et maximum de la découpe, par ligne du CAP", "",
           f"Commande : `{CMD}` (la table par ligne : `chaine_github_mesure.py --compact … --section 5`).", "",
           "Par ligne numérotée (J3 à J9 ; J1 et J2 n'ont pas de ligne « #n »). **nœuds** = l'issue de la ligne + tous ses "
           "sous-lots, récursivement (parents découpés compris) ; **feuilles** = nœuds sans sous-lot (les lots réellement "
           "exécutés) ; livrées = feuilles `livre`. « issue elle-même plus ses sous-lots » = nœuds.", ""]
    lignes, res = [], {}
    groupes = [(f"J{j}", [p for p in pl if p["jalon"] == j]) for j in range(3, 10)] + [("tous", pl)]
    for nom, g in groupes:
        if not g:
            continue
        nd, fe, li = [p["noeuds"] for p in g], [p["feuilles"] for p in g], [p["livrees"] for p in g]
        mx = max(g, key=lambda p: (p["noeuds"], p["feuilles"]))
        res[nom] = {"lignes": len(g), "noeuds_mediane": statistics.median(nd), "noeuds_max": max(nd),
                    "feuilles_mediane": statistics.median(fe), "feuilles_max": max(fe), "livrees_total": sum(li),
                    "ligne_max": mx["issue"]}
        lignes.append([nom, len(g), M.fnum(statistics.median(nd)), max(nd), M.fnum(statistics.median(fe)), max(fe),
                       sum(nd), sum(li), f"#{mx['issue']}"])
    out += M.table(["jalon", "lignes", "médiane nœuds", "max nœuds", "médiane feuilles", "max feuilles", "nœuds (somme)",
                    "feuilles livrées", "ligne la plus enflée"], lignes) + [""]
    fin = [p for p in pl if p["feuilles"] and p["livrees"] == p["feuilles"]]
    nd, fe = [p["noeuds"] for p in fin], [p["feuilles"] for p in fin]
    r = {"lignes": len(fin), "noeuds_mediane": statistics.median(nd), "noeuds_max": max(nd),
         "feuilles_mediane": statistics.median(fe), "feuilles_max": max(fe),
         "decoupees": sum(1 for p in fin if p["noeuds"] > 1)}
    res["lignes_terminees"] = r
    out += [f"Lignes **terminées** (toutes leurs feuilles livrées) : {r['lignes']} ; médiane {M.fnum(r['noeuds_mediane'])} "
            f"nœud(s) et {M.fnum(r['feuilles_mediane'])} feuille(s) ; maximum {r['noeuds_max']} nœuds / {r['feuilles_max']} "
            f"feuilles ; {r['decoupees']} sont découpées. Biais : une ligne ouverte (J6 à J9) n'est pas encore découpée, "
            "donc la médiane globale sous-estime ce qu'elle deviendra ; la médiane des lignes terminées sur-représente "
            "les jalons déjà travaillés.", ""]
    return out, res


def mots_longs(s):
    return {w for w in M.mots_du_titre(s) if len(w) > 4}


def section_6bis(D):
    out = ["## 6bis. Un « lot à créer » a-t-il déjà une issue ouverte au même titre ?", "", f"Commande : `{CMD}`.", "",
           "Pour chaque ligne « à créer » : parmi toutes les issues **ouvertes** (hors journal), meilleur rapport "
           "`difflib.SequenceMatcher` sur le titre en minuscules sans accents, et meilleure part de mots de plus de "
           "4 lettres communs. Seuil « à regarder » : rapport ≥ 0,6 ou ≥ 50 % des mots longs de la ligne.", ""]
    ouvertes = [i for i in D["issues"] if i["etat"] == "OPEN" and "journal" not in i["etiquettes"]]
    lignes, res = [], []
    for a in D["cap"]["a_creer"]:
        t = M.sans_accents(re.sub(r"\s*·\s*pc\s*$", "", a["texte"]))
        mt = mots_longs(t)
        best = max(ouvertes, key=lambda i: SequenceMatcher(None, t, M.sans_accents(i["titre"])).ratio())
        rap = SequenceMatcher(None, t, M.sans_accents(best["titre"])).ratio()
        bm = max(ouvertes, key=lambda i: len(mt & mots_longs(i["titre"])) / max(1, len(mt)))
        part = len(mt & mots_longs(bm["titre"])) / max(1, len(mt))
        suspect = rap >= 0.6 or part >= 0.5
        res.append({"jalon": a["jalon"], "ligne": a["rang"], "titre": a["texte"], "meilleur_rapport": round(rap, 2),
                    "issue_rapport": best["n"], "meilleure_part_mots": round(part, 2), "issue_mots": bm["n"],
                    "a_regarder": suspect})
        lignes.append([f"J{a['jalon']}", a["rang"], a["texte"], f"#{best['n']} {best['titre']} ({rap:.2f})",
                       f"#{bm['n']} {bm['titre']} ({part:.0%})", "à regarder" if suspect else "non"])
    out += M.table_g(["jalon", "ligne", "lot à créer", "titre le plus proche (rapport)", "plus de mots longs communs",
                      "verdict"], lignes) + [""]
    n = sum(r["a_regarder"] for r in res)
    out += [f"{len(res)} lignes ; {n} à regarder ; aucune n'a d'issue ouverte de titre identique.", ""]
    return out, res


def milestones(hors_ligne):
    if hors_ligne:
        return {}
    r = subprocess.run(["gh", "api", "repos/PLiagre/Forge/milestones?state=all&per_page=100"], capture_output=True,
                       text=True, encoding="utf-8")
    return {M.jalon_court(m["title"]): m["state"] for m in json.loads(r.stdout)} if r.returncode == 0 else {}


def section_7(D, X, hors_ligne):
    out = ["## 7. L'état courant", "",
           f"Commande : `{CMD}` ; contrôles : `gh issue list -R PLiagre/Forge --state open --limit 1000 --json "
           "number,labels,milestone` et `gh pr list -R PLiagre/Forge --state open --json "
           "number,title,headRefName,createdAt`.", ""]
    etats = ["pret", "idee", "en-cours", "bloque"]
    par = defaultdict(Counter)
    for i in D["issues"]:
        if i["etat"] != "OPEN":
            continue
        j = M.jalon_court(i["jalon"])
        labs = [e for e in etats if e in i["etiquettes"]]
        cle = "+".join(labs) if labs else ("journal" if "journal" in i["etiquettes"] else "(sans état)")
        par[j][cle] += 1
        par[j]["_total"] += 1
        if "pc" in i["etiquettes"]:
            par[j]["_pc"] += 1
    ms = milestones(hors_ligne)
    autres = sorted({k for c in par.values() for k in c if not k.startswith("_") and k not in etats})
    lignes, res = [], {}
    for j in sorted(par, key=M.cle_jalon):
        c = par[j]
        lignes.append([j, ms.get(j, "?"), *[c[e] or "·" for e in etats], *[c[a] or "·" for a in autres],
                       c["_pc"] or "·", f"**{c['_total']}**"])
        res[j] = dict(c)
    tot = Counter()
    for c in par.values():
        tot.update(c)
    lignes.append(["**total**", "", *[f"**{tot[e]}**" for e in etats], *[f"**{tot[a]}**" for a in autres],
                   f"**{tot['_pc']}**", f"**{tot['_total']}**"])
    out += ["Issues ouvertes par milestone et par étiquette d'état (`pc` = dont étiquette `pc`, comptée à part).", ""]
    out += M.table(["milestone", "état du milestone", *etats, *autres, "dont `pc`", "total ouvertes"], lignes) + [""]
    prs = [p for p in D["prs"] if p["etat"] == "OPEN"]
    out += ["### PR ouvertes", ""]
    lp, rows = [], []
    for p in prs:
        age = (X.fin_paris - M.paris(p["cree"])).total_seconds() / 86400
        iss = X.I.get(p["lot"]) if p["lot"] else None
        rows.append({"pr": p["n"], "titre": p["titre"], "tete": p["tete"], "issue": p["lot"], "cree": p["cree"],
                     "age_jours": round(age, 1), "etiquettes_issue": iss["etiquettes"] if iss else None,
                     "etat_issue": iss["etat"] if iss else None})
        lp.append([f"#{p['n']}", p["tete"], p["titre"], f"#{p['lot']}" if p["lot"] else "—",
                   " ".join(iss["etiquettes"]) if iss else "", f"{M.paris(p['cree']):%d/%m/%Y %H:%M}",
                   M.fr(age, 1) + " j"])
    out += M.table_g(["PR", "branche", "titre", "issue", "étiquettes de l'issue", "ouverte le (Paris)", "âge"], lp) + [""]
    out += [f"{len(prs)} PR ouverte(s) en tout, dont {sum(1 for p in prs if p['lot'])} de branche `lot/`.", ""]
    res["prs_ouvertes"] = rows
    return out, res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hors-ligne", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    jp, mp = M.JSON_SORTIE, M.MD_SORTIE
    D = json.loads(jp.read_text(encoding="utf-8"))
    D.pop("complement", None)
    X = M.Donnees(D)
    C = D["classification"]
    texte = mp.read_text(encoding="utf-8").split(MARQUE)[0]
    texte = texte.replace("## 7. Le temps de « pret » à la fusion", "## 8. Le temps de « pret » à la fusion")
    s3, r3 = section_3bis(D, X, C, args.hors_ligne)
    s5, r5 = section_5bis(D, C)
    s6, r6 = section_6bis(D)
    s7, r7 = section_7(D, X, args.hors_ligne)
    D["complement"] = {"fichiers_vs_titres": r3, "decoupe_mediane": r5, "a_creer_vs_ouvertes": r6, "etat_courant": r7}
    jp.write_text(json.dumps(D, ensure_ascii=False, indent=1), encoding="utf-8")
    mp.write_text(texte.rstrip() + "\n\n" + MARQUE + "\n\n# Compléments (chaine_github_complement.py)\n\n"
                  + "\n".join(s3 + s5 + s6 + s7).rstrip() + "\n", encoding="utf-8")
    print("complément écrit", file=sys.stderr)


if __name__ == "__main__":
    main()
