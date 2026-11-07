"""Mesure de la chaîne d'agents d'après le journal du pilote (VPS), lecture seule.

Usage : py vps_pilote.py DOSSIER_COLLECTE SORTIE.json > rapport.txt
Entrées (voir vps_pilote_collecte.py) : journal.jsonl, pilote.log, issues.json, timelines.json.
Deux fenêtres : depuis le 1er octobre 2026 (Paris) et depuis le 28 octobre 2026.
"""
import json, re, sys, statistics as st, collections
from datetime import datetime, timedelta, timezone
from pathlib import Path

D = Path(sys.argv[1]); SORTIE = Path(sys.argv[2])
UTC = timezone.utc
FENETRES = {"depuis 1er oct": datetime(2026, 9, 30, 22, tzinfo=UTC),   # 1/10 00:00 CEST
            "depuis 28 oct": datetime(2026, 10, 27, 23, tzinfo=UTC)}   # 28/10 00:00 CET
FIN_ETE = datetime(2026, 10, 25, 1, tzinfo=UTC)


def paris(t):
    return t + timedelta(hours=2 if t < FIN_ETE else 1)


def jour(t): return paris(t).strftime("%Y-%m-%d")


def semaine(t):
    p = paris(t); return (p - timedelta(days=p.weekday())).strftime("%Y-%m-%d")


def dt(s): return datetime.fromisoformat(s.replace("Z", "+00:00"))


def heures(x): return x / 3600


def quartiles(v):
    if not v: return None
    v = sorted(v)
    q = st.quantiles(v, n=4, method="inclusive") if len(v) > 1 else [v[0]] * 3
    return {"n": len(v), "min": v[0], "q1": q[0], "mediane": q[1], "q3": q[2],
            "p90": st.quantiles(v, n=10, method="inclusive")[8] if len(v) > 1 else v[0], "max": v[-1],
            "somme": sum(v)}


def fmt(q, unite="h"):
    if not q: return "n=0"
    return (f"n={q['n']} · min {q['min']:.2f} · Q1 {q['q1']:.2f} · médiane {q['mediane']:.2f} · "
            f"Q3 {q['q3']:.2f} · p90 {q['p90']:.2f} · max {q['max']:.2f} {unite}")


# ----------------------------------------------------------------- journal
ev = []
for l in open(D / "journal.jsonl", encoding="utf-8"):
    d = json.loads(l); d["t"] = dt(d["quand"]); ev.append(d)
ev.sort(key=lambda e: e["t"])
par_lot = collections.defaultdict(list)
for e in ev: par_lot[e["lot"]].append(e)

issues = {i["number"]: i for i in json.load(open(D / "issues.json", encoding="utf-8"))}
tl = {int(k): v for k, v in json.load(open(D / "timelines.json")).items()}
livres_journal = {e["lot"]: e for e in ev if e["action"] == "livré"}


def role_de(e):
    a = e["action"]
    if a == "brief écrit" or a == "chef en échec": return "chef"
    if a == "découpé": return "chef (découpe)"
    if a.startswith("codeur_3d") or a.startswith("codeur_Nd"): return "codeur_3d"
    if a.startswith("codeur") and "en renfort" in a: return "renfort"
    if a.startswith("codeur"): return "codeur"
    if a.startswith("relect"): return "relecteur"
    if a.startswith("dépann") or a.startswith("dépanneur"): return "dépanneur"
    if (a.startswith("mecanicien") or a.startswith("mécanicien") or a.startswith("réparation")
            or a.startswith("rouge, mode direct")):
        return "mécanicien"
    if a == "conflit résolu": return "conflit (résolveur)"
    return None


def modele(agent):
    return (agent or "?").replace("claude/claude-", "claude/")


# --------------------------------------------- reconstruction des tours (log)
ENT = re.compile(r"^=== \w{3} (\w{3})\s+(\d+) (\d\d:\d\d:\d\d) (CEST|CET) (\d{4}) — jour")
FIN = re.compile(r"^=== pilote : code (\d+)")
MOIS = {m: i + 1 for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())}
tours = []
ouverts = []; bloc = []
lignes_log = open(D / "pilote.log", encoding="utf-8", errors="replace").read().splitlines()
journal_par_cle = collections.defaultdict(collections.deque)
for e in ev:
    if e["t"] >= datetime(2026, 9, 30, tzinfo=UTC):
        journal_par_cle[(str(e["lot"]), e["action"])].append(e)


def fusionner(ligne):
    m = re.match(r"^#(\S+) (.+?)(?: \[[^\]]*\])?(?: — .*)?$", ligne)
    if not m: return None
    q = journal_par_cle.get((m.group(1), m.group(2)))
    return q.popleft() if q else None


for ligne in lignes_log:
    m = ENT.match(ligne)
    if m:
        mo, j, h, tz, a = m.groups()
        local = datetime(int(a), MOIS[mo], int(j), *map(int, h.split(":")), tzinfo=UTC)
        debut = local - timedelta(hours=2 if tz == "CEST" else 1)
        ouverts.append({"debut": debut}); continue
    m = FIN.match(ligne)
    if m:
        evs = [x for x in (fusionner(l) for l in bloc if l.startswith("#")) if x]
        rien = any(l.strip() == "RIEN" for l in bloc)
        t_fin = max((x["t"] for x in evs), default=None)
        if ouverts:
            candidats = [o for o in ouverts if t_fin is None or o["debut"] <= t_fin] or ouverts
            agent = any(role_de(x) for x in evs)
            # un appel d'agent est long : il vient du plus ancien tour encore ouvert ;
            # le reste est bref : le plus récent
            o = candidats[0] if (agent and t_fin) else candidats[-1]
            ouverts.remove(o)
            o.update(fin=t_fin, evenements=evs, rien=rien, code=int(m.group(1)))
            tours.append(o)
        bloc = []; continue
    if ligne.strip(): bloc.append(ligne)
tours.sort(key=lambda o: o["debut"])

appels = []
for o in tours:
    evr = [x for x in o["evenements"] if role_de(x)]
    for x in evr:
        appels.append({"t": x["t"], "lot": x["lot"], "action": x["action"], "agent": x["agent"],
                       "role": role_de(x), "duree_s": (x["t"] - o["debut"]).total_seconds(),
                       "seul": len(evr) == 1})

R = {}


def titre(s): print("\n## " + s)


print("# Rapport brut — chaîne d'agents (journal du pilote)")
print(f"Journal : {len(ev)} entrées, du {ev[0]['t'].isoformat()} au {ev[-1]['t'].isoformat()}")
dp = [o["debut"] for o in tours]
print(f"pilote.log : {len(tours)} tours reconstruits, du {min(dp).isoformat()} au {max(dp).isoformat()}")

# ------------------------------------------------ 1. pret -> fusion
titre("1. De `pret` à la fusion")
lots_mesures = []
for n, e in livres_journal.items():
    i = issues.get(n); t = tl.get(n)
    if not i or not t or not i["closedAt"]: continue
    nodes = t["nodes"]
    prets = [dt(x["createdAt"]) for x in nodes if x["__typename"] == "LabeledEvent" and x["label"]["name"] == "pret"]
    encs = [dt(x["createdAt"]) for x in nodes if x["__typename"] == "LabeledEvent" and x["label"]["name"] == "en-cours"]
    if not prets or not encs: continue
    fus = dt(i["closedAt"])
    deps = set()
    corps = i["body"] or ""
    for m in re.finditer(r"^[ \t]*(?:#+[ \t]*)?D[ée]pend de[ \t]*:?[ \t]*(.*)$", corps, re.I | re.M):
        bloc_txt = m.group(0)
        if not re.search(r"#\d+", bloc_txt):
            bloc_txt += " ".join(corps[m.end():].splitlines()[1:6])
        deps |= {int(x) for x in re.findall(r"#(\d+)", bloc_txt)}
    deps.discard(n)
    fermes_deps = [dt(issues[d]["closedAt"]) for d in deps if d in issues and issues[d]["closedAt"]]
    pret = min(prets); pret_eff = max([pret] + [x for x in fermes_deps if x < fus])
    lots_mesures.append({"lot": n, "pret": pret, "pret_eff": pret_eff, "encours": min(encs), "fusion": fus,
                         "pc": any(l["name"] == "pc" for l in i["labels"]),
                         "ndeps": len(deps), "evenements": par_lot[n]})


def h(a, b): return heures((a - b).total_seconds())


def stats_lots(depuis):
    L = [x for x in lots_mesures if x["fusion"] >= depuis]
    out = {"n": len(L)}
    out["pret→fusion (h)"] = quartiles([h(x["fusion"], x["pret"]) for x in L])
    out["pret effectif (dépendances levées)→fusion (h)"] = quartiles([h(x["fusion"], x["pret_eff"]) for x in L])
    out["pret→en-cours (file+chef) (h)"] = quartiles([h(x["encours"], x["pret"]) for x in L])
    out["pret effectif→en-cours (h)"] = quartiles([h(x["encours"], x["pret_eff"]) for x in L])
    out["en-cours→fusion (codeur+CI+relecture+corrections) (h)"] = quartiles([h(x["fusion"], x["encours"]) for x in L])
    for etiq, f in (("vps", lambda x: not x["pc"]), ("pc", lambda x: x["pc"])):
        S = [x for x in L if f(x)]
        out[f"[{etiq}] en-cours→fusion (h)"] = quartiles([h(x["fusion"], x["encours"]) for x in S])
        out[f"[{etiq}] pret effectif→fusion (h)"] = quartiles([h(x["fusion"], x["pret_eff"]) for x in S])
    return out


for nom, depuis in FENETRES.items():
    s = stats_lots(depuis); R.setdefault("pret_fusion", {})[nom] = s
    print(f"\n### {nom} — {s['n']} lots fusionnés")
    for k, v in s.items():
        if k != "n": print(f"- {k} : {fmt(v)}")


def tid(t): return int((t.timestamp() - 60) // 120)


def decomposer(x):
    phases = collections.Counter()
    ev0 = x["evenements"]
    chef_att = [e for e in ev0 if e["action"] == "attente" and (e["detail"] or "").startswith("chef")
                and x["pret"] <= e["t"] <= x["encours"] + timedelta(minutes=5)]
    pre = (x["encours"] - x["pret_eff"]).total_seconds()
    q = len({tid(e["t"]) for e in chef_att if e["t"] >= x["pret_eff"]}) * 120
    phases["avant chef : quota/session (attente du chef)"] = min(q, max(pre, 0))
    phases["avant chef : file + exécution du chef (reste)"] = max(0, pre - phases["avant chef : quota/session (attente du chef)"])
    prev = x["encours"]
    seg = []
    for e in [e for e in ev0 if e["t"] > x["encours"] - timedelta(minutes=1) and e["t"] <= x["fusion"] + timedelta(minutes=5)]:
        if e["action"] in ("attendre_ci", "attendre_pc", "attente", "attendre_fusion", "erreur"):
            seg.append(e); continue
        if e["action"] in ("secours", "envoyé au PC", "base fusionnée", "conflit résolu", "chronometre rejoué",
                           "décision technique", "codeur sans changement", "codeur en échec", "chef en échec",
                           "relecteur en échec", "dépanneur en échec", "rangé dans la réserve", "mécanicien sans réparation"):
            continue  # simple jalon de travail : son temps reste dans l'étape qui suit
        fin = e["t"]; dur = (fin - prev).total_seconds()
        if dur < 0: continue

        def n(act): return len({tid(s["t"]) for s in seg if s["action"] == act and prev <= s["t"] <= fin}) * 120
        ci, pc, at = n("attendre_ci"), n("attendre_pc"), n("attente")
        a = e["action"]
        if a.startswith("relecture"): cat = "relecture"
        elif a.startswith("codeur_3d") or a.startswith("codeur_Nd"): cat = "codeur 3D (PC)"
        elif a.startswith("codeur") and ("correction" in a or "revue" in a): cat = "correction"
        elif a.startswith("codeur"): cat = "codeur"
        elif a == "livré": cat = "fusion (après ACCEPTE)"
        elif a in ("brief écrit", "découpé"): cat = "chef"
        elif a in ("réponse reçue", "remis pret", "repris", "dépanné"): cat = "lot bloqué (attente propriétaire/dépanneur)"
        elif a == "bloqué": cat = "codeur/relecteur jusqu'au blocage"
        else: cat = "autre : " + a.split(" ")[0]
        phases[f"{cat} : CI (attendre_ci)"] += ci
        phases[f"{cat} : PC au travail (attendre_pc)"] += pc
        phases[f"{cat} : quota/session"] += at
        phases[f"{cat} : agent + latence (reste)"] += max(0, dur - ci - pc - at)
        prev = fin; seg = []
    return phases


for nom, depuis in FENETRES.items():
    L = [x for x in lots_mesures if x["fusion"] >= depuis]
    tot = collections.Counter(); grandes = collections.defaultdict(list)
    for x in L:
        ph = decomposer(x)
        agg = collections.Counter()
        for k, v in ph.items():
            tot[k] += v; agg[k.split(" : ")[0]] += v
        for k, v in agg.items():
            if v > 0: grandes[k].append(heures(v))
    total = sum(tot.values()) or 1
    print(f"\n### Décomposition cumulée, {nom} — {len(L)} lots (somme des durées pret effectif→fusion, part en %)")
    rows = []
    for k, v in sorted(tot.items(), key=lambda kv: -kv[1]):
        if v:
            rows.append({"phase": k, "heures": round(heures(v), 1), "part": round(100 * v / total, 1),
                         "par_lot_min": round(v / 60 / max(1, len(L)), 1)})
            print(f"- {k} : {heures(v):.1f} h ({100 * v / total:.1f} %, {v / 60 / len(L):.0f} min par lot)")
    R.setdefault("decomposition", {})[nom] = rows
    print(f"### Durée par grande phase, pour les lots qui la traversent, {nom}")
    R.setdefault("grandes_phases", {})[nom] = {}
    for k, v in sorted(grandes.items(), key=lambda kv: -sum(kv[1])):
        q = quartiles(v); R["grandes_phases"][nom][k] = q
        print(f"- {k} : {fmt(q)}")

# ------------------------------------------------ 2. appels par rôle et modèle
titre("2. Appels d'agents par rôle et par modèle")


def reussite(a): return not (a.endswith("en échec") or "sans changement" in a or "sans réparation" in a)


for nom, depuis in FENETRES.items():
    A = [a for a in appels if a["t"] >= depuis]
    print(f"\n### {nom} — {len(A)} appels de rôle journalisés (succès, échec ou rien produit)")
    t = collections.defaultdict(lambda: {"n": 0, "echecs": 0, "d": []})
    for a in A:
        k = (a["role"], modele(a["agent"])); t[k]["n"] += 1
        if not reussite(a["action"]): t[k]["echecs"] += 1
        if a["seul"] and a["duree_s"] < 4 * 3600: t[k]["d"].append(a["duree_s"] / 60)
    rows = []
    for k, v in sorted(t.items()):
        q = quartiles(v["d"])
        rows.append({"role": k[0], "modele": k[1], "appels": v["n"], "echecs_ou_vides": v["echecs"],
                     "duree_min_mediane": round(q["mediane"], 1) if q else None,
                     "duree_min_total_estimee": round(q["somme"], 0) if q else None, "duree_n": q["n"] if q else 0})
        if q:
            print(f"- {k[0]} · {k[1]} : {v['n']} appels dont {v['echecs']} échec/vide ; durée estimée médiane "
                  f"{q['mediane']:.1f} min, Q3 {q['q3']:.1f}, max {q['max']:.0f} (n={q['n']}), total ≈ {q['somme'] / 60:.1f} h")
        else:
            print(f"- {k[0]} · {k[1]} : {v['n']} appels dont {v['echecs']} échec/vide ; durée non estimable")
    R.setdefault("appels", {})[nom] = rows
    if nom == "depuis 1er oct":
        sem = collections.defaultdict(lambda: collections.defaultdict(int)); dsem = collections.defaultdict(float)
        for a in A:
            sem[semaine(a["t"])][(a["role"], modele(a["agent"]))] += 1
            if a["seul"] and a["duree_s"] < 4 * 3600: dsem[semaine(a["t"])] += a["duree_s"] / 3600
        print("\n### Par semaine (lundi de la semaine, heure de Paris)")
        R["appels_par_semaine"] = {}
        for s in sorted(sem):
            print(f"- semaine du {s} : {sum(sem[s].values())} appels, ≈ {dsem[s]:.1f} h d'agent estimées")
            R["appels_par_semaine"][s] = {f"{r}|{m}": n for (r, m), n in sorted(sem[s].items())}
            for (r, m), n in sorted(sem[s].items(), key=lambda kv: -kv[1]): print(f"    - {r} · {m} : {n}")

gaps = []
for x in lots_mesures:
    evl = x["evenements"]
    b = next((e for e in evl if e["action"] == "brief écrit"), None)
    c1 = next((e for e in evl if e["action"] == "codeur : code" and b and e["t"] > b["t"]), None)
    if b and c1 and not x["pc"] and not any(e["action"] in ("attente", "codeur en échec", "codeur sans changement", "secours")
                                           and b["t"] < e["t"] < c1["t"] for e in evl):
        gaps.append(((c1["t"] - b["t"]).total_seconds() / 60, modele(c1["agent"]), c1["t"]))
print("\n### Contrôle : écart brief écrit → codeur : code (lots VPS sans attente ni échec intercalé), minutes")
for nomf, dep in FENETRES.items():
    for mod in sorted({g[1] for g in gaps}):
        v = [g[0] for g in gaps if g[1] == mod and g[2] >= dep]
        if v:
            q = quartiles(v); print(f"- {nomf} · {mod} : n={q['n']} médiane {q['mediane']:.1f} · Q3 {q['q3']:.1f} · max {q['max']:.0f}")

# ------------------------------------------------ 3. attentes
titre("3. Attentes (quota, session, occupé, PC, CI)")
RAISON = re.compile(r"(claude|codex|cursor)/([\w.@/-]+?) : (quota épuisé|session expirée ou absente|occupé|écarté|ne démarre pas|refuse l'appel)")


def lire_attente(e):
    d = e["detail"] or ""
    return d.split(" : ")[0], [m.groups() for m in RAISON.finditer(d)]


att = [(e, *lire_attente(e)) for e in ev if e["action"] == "attente"]
R["attentes"] = {}
for nom, depuis in FENETRES.items():
    A = [x for x in att if x[0]["t"] >= depuis]
    print(f"\n### {nom} — {len(A)} entrées « attente » (un lot sans agent possible à un tour)")
    tours_att = {tid(x[0]["t"]) for x in A}
    print(f"- tours distincts avec au moins une attente : {len(tours_att)} ≈ {len(tours_att) * 2 / 60:.0f} h de tours")
    cause = collections.defaultdict(set); detail_ent = collections.Counter()
    for e, role, reps in A:
        for outil, mod, raison in reps:
            if raison == "écarté": continue
            key = (f"{outil}/{mod.split('@')[0]}", raison)
            cause[key].add(tid(e["t"])); detail_ent[key] += 1
    rows = []
    print("- par modèle et raison (tours distincts ; entrées ; heures de tours)")
    for key in sorted(cause, key=lambda k: -len(cause[k])):
        tt = cause[key]
        rows.append({"modele": key[0], "raison": key[1], "tours": len(tt), "entrees": detail_ent[key],
                     "heures_de_tours": round(len(tt) * 2 / 60, 1)})
        print(f"    - {key[0]} · {key[1]} : {len(tt)} tours ({detail_ent[key]} entrées) ≈ {len(tt) * 2 / 60:.1f} h")
    pr = collections.defaultdict(set)
    for e, role, reps in A: pr[role].add(tid(e["t"]))
    print("- par rôle bloqué :", ", ".join(f"{r} {len(v)} tours" for r, v in sorted(pr.items(), key=lambda kv: -len(kv[1]))))
    pj = collections.defaultdict(lambda: collections.defaultdict(set))
    for e, role, reps in A:
        for r in {r for (o, m, r) in reps if r != "écarté"}: pj[jour(e["t"])][r].add(tid(e["t"]))
    print("- par jour (heures de tours par raison) :")
    jours = {}
    for j in sorted(pj):
        ligne = {r: round(len(v) * 2 / 60, 1) for r, v in pj[j].items()}
        jours[j] = ligne
        print(f"    - {j} : " + ", ".join(f"{r} {hh} h" for r, hh in sorted(ligne.items(), key=lambda kv: -kv[1])))
    eps = []
    for raison in ("quota épuisé", "session expirée ou absente", "occupé"):
        ts = sorted({tid(e["t"]) for e, role, reps in A if any(r == raison for (_, _, r) in reps)})
        if not ts: continue
        debut = prev = ts[0]
        for t in ts[1:] + [None]:
            if t is None or t - prev > 6:
                eps.append({"raison": raison, "debut": datetime.fromtimestamp(debut * 120 + 60, UTC).isoformat(),
                            "heures": round((prev - debut + 1) * 2 / 60, 1)})
                if t is not None: debut = t
            if t is not None: prev = t
    eps.sort(key=lambda x: -x["heures"])
    print("- épisodes continus (à 12 min près) :")
    for raison in ("quota épuisé", "session expirée ou absente", "occupé"):
        E = [x for x in eps if x["raison"] == raison]
        if E:
            print(f"    - {raison} : {len(E)} épisodes, {sum(x['heures'] for x in E):.1f} h cumulées ; médiane {st.median(x['heures'] for x in E):.1f} h ; "
                  "les plus longs : " + ", ".join(f"{x['heures']} h le {paris(dt(x['debut'])).strftime('%d/%m %Hh%M')}" for x in E[:6]))
    R["attentes"][nom] = {"par_modele_raison": rows, "par_jour": jours, "episodes_top": eps[:15], "tours_distincts": len(tours_att)}

print("\n### Attentes de travail (le lot attend le PC, la CI ou la fusion : pas une panne)")
for nom, depuis in FENETRES.items():
    for a in ("attendre_pc", "attendre_ci", "attendre_fusion"):
        E = [e for e in ev if e["action"] == a and e["t"] >= depuis]
        print(f"- {nom} · {a} : {len(E)} entrées, {len({tid(e['t']) for e in E})} tours distincts, {len({e['lot'] for e in E})} lots")
pause = [e for e in ev if re.search(r"pause|PC_ACTIF", (e["detail"] or "") + e["action"], re.I)]
print(f"- mentions de pause du PC dans le journal : {len(pause)}")

# ------------------------------------------------ 4. le reste
titre("4. Ce qui coûte cher en plus")
for nom, depuis in FENETRES.items():
    print(f"\n### {nom}")
    L = [x for x in lots_mesures if x["fusion"] >= depuis]
    cor = {x["lot"]: sum(1 for e in x["evenements"] if e["action"] == "relecture CORRIGER") for x in L}
    distr = collections.Counter(cor.values())
    print("- relectures CORRIGER avant fusion, par lot livré : " + ", ".join(f"{k} CORRIGER → {v} lots" for k, v in sorted(distr.items())))
    tot_c = sum(cor.values()); print(f"  total {tot_c} CORRIGER pour {len(L)} lots ({tot_c / max(1, len(L)):.2f} par lot)")
    acc = sum(1 for e in ev if e["action"] == "relecture ACCEPTE" and e["t"] >= depuis)
    corr = sum(1 for e in ev if e["action"] == "relecture CORRIGER" and e["t"] >= depuis)
    print(f"- verdicts de relecture : {acc} ACCEPTE, {corr} CORRIGER ({100 * corr / max(1, acc + corr):.0f} % de CORRIGER)")
    for a, lab in (("bloqué", "lots bloqués"), ("codeur en échec", "codeur en échec"), ("codeur sans changement", "codeur sans changement"),
                   ("chef en échec", "chef en échec"), ("relecteur en échec", "relecteur en échec"), ("découpé", "découpes"),
                   ("secours", "secours"), ("chronometre rejoué", "chronomètre rejoué"), ("erreur", "erreurs gh/git")):
        E = [e for e in ev if e["action"] == a and e["t"] >= depuis]
        print(f"- {lab} : {len(E)} entrées, {len({e['lot'] for e in E})} lots distincts")
    bl = collections.Counter(re.sub(r"\d+", "N", (e["detail"] or "")[:70]) for e in ev if e["action"] == "bloqué" and e["t"] >= depuis)
    print("  raisons de blocage :", "; ".join(f"{n}× {k}" for k, n in bl.most_common(5)))
    d124 = [e for e in ev if "124" in (e["detail"] or "") and "en échec" in e["action"] and e["t"] >= depuis]
    print(f"- appels coupés par le délai (code 124) : {len(d124)} — " + ", ".join(f"{k} {v}" for k, v in collections.Counter(role_de(e) for e in d124).items()))

print("\n### Tours du pilote (log)")
for nom, depuis in FENETRES.items():
    T = [o for o in tours if o["debut"] >= depuis]
    rien = sum(1 for o in T if o["rien"]); ag = sum(1 for o in T if any(role_de(x) for x in o["evenements"]))
    ok = sum(1 for o in T if o.get("code") == 0)
    print(f"- {nom} : {len(T)} tours ; RIEN {rien} ({100 * rien / len(T):.0f} %) ; avec un agent qui a répondu {ag} ({100 * ag / len(T):.0f} %) ; code ≠ 0 : {len(T) - ok}")
    R.setdefault("tours", {})[nom] = {"tours": len(T), "rien": rien, "agent": ag, "code_non_nul": len(T) - ok}

print("\n### Lots fusionnés par jour (heure de Paris)")
lj = collections.Counter(jour(x["fusion"]) for x in lots_mesures)
print(" · ".join(f"{j} {lj[j]}" for j in sorted(lj) if j >= "2026-10-01"))
R["livres_par_jour"] = {j: n for j, n in sorted(lj.items()) if j >= "2026-10-01"}
R["lots_livres_mesures"] = len(lots_mesures)
SORTIE.write_text(json.dumps(R, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
