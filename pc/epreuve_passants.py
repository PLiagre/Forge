"""L'épreuve des passants (lot #898) : 0 égalité, 1 écart, 2 impossible.   py pc\\epreuve_passants.py --sortie D [--seed S] [--unity CHEMIN] [--contre en-trop|ailleurs|anciens]
Unity joue la session #897 sur son service d'épreuve ; un service d'épreuve neuf de même graine (#896, déterministe) rejoue ensuite ses gestes et sert la référence. `juger` compte lui-même les passants de `liste` contre le bourg et le plan servis ; le drapeau `contre_epreuve` du rapport n'est qu'affiché."""
import argparse, collections, http.client, importlib.util, json, math, subprocess, sys, time, urllib.error, urllib.request  # noqa: F401 (subprocess : les tests y vérifient que rien n'est lancé)
from pathlib import Path
_spec = importlib.util.spec_from_file_location("epreuve_vie_bourg", Path(__file__).with_name("epreuve_vie_bourg.py")); VIE = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(VIE)
CAPITALE, JALON1, JOUER, HOTE, PORT, _valider, _ecrire, _arreter = VIE.CAPITALE, VIE.JALON1, VIE.JOUER, VIE.HOTE, VIE.PORT, VIE._valider, VIE._ecrire, VIE._arreter
EGALITE, ECART, IMPOSSIBLE, _entier, _texte, _liste, _objet, _nombre, _cause = VIE.EGALITE, VIE.ECART, VIE.IMPOSSIBLE, VIE._entier, VIE._texte, VIE._liste, VIE._objet, VIE._nombre, VIE._cause
# Les gestes de Lot897.cs, recopiés : le siège, trois routes de (0 ; d) à (40 ; d) larges de 4 m, le chantier relevé au tick 5, le bourg vidé un tick plus tard.
SIEGE, ORDONNEES, LONGUEUR, LARGEUR, TICK_CHANTIER = "Biskra", (0, 8, 16), 40, 4, 5
ETATS, IMAGES, RAPPORT, TOLERANCE_M, PAYSANS, OUVRIERS = ("chantier", "vide"), ("01-ouvriers-au-chantier", "02-bourg-vide"), "passants-bourg.json", 0.05, "paysans", "ouvriers"
CONTRE = {"en-trop": "-forge897PassantEnTrop", "ailleurs": "-forge897OuvriersAilleurs", "anciens": "-forge897GarderAnciens"}
HAUT = (("cellule", _entier), ("port", _entier), ("contre_epreuve", _texte), ("defaut", _cause), ("etats", _liste))
ETAT = (("nom", _texte), *((k, _entier) for k in ("tick_lieu", "tick_plan", "tick_applique", "bourg", "passants")), ("liste", _liste), ("camera", lambda v: _liste(v) and len(v) == 16 and all(map(_nombre, v))))
PASSANT = (("id", _entier), ("metier", _texte), ("destination", _texte), ("x", _nombre), ("y", _nombre))  # un id d'instance Unity peut valoir −1 : pas de _valider ici
def _rapport(r):
    """Le rapport #897, types stricts : un défaut, un −1 ou d'autres états que « chantier » puis « vide » rendent l'épreuve impossible."""
    _valider(r, HAUT, "rapport")
    if r["defaut"] is not None: raise ValueError(f"défaut de session : {r['defaut']}")
    for e in r["etats"]:
        _valider(e, ETAT, f"état {e.get('nom') if _objet(e) else e!r}")
        if not all(_objet(p) and all(k in p and bon(p[k]) for k, bon in PASSANT) for p in e["liste"]): raise ValueError(f"état {e['nom']} : passant illisible dans liste")
    if (noms := [e["nom"] for e in r["etats"]]) != list(ETATS): raise ValueError(f"états {noms}, attendu {list(ETATS)}")
    return dict(zip(ETATS, r["etats"]))
def passants_attendus(lieu):
    """La règle de #784 (PassantsDuBourg.Projeter) sur un /lieu servi : bourg // 10 passants, partagés par plus grands restes puis par nom ordinal. Pure."""
    if (b := lieu["bourg"]["population"]) == 0: return {}
    autres = {m: f["personnes"] for m, f in lieu["foyers"].items() if m != PAYSANS}; poids = {m: p for m, p in (*autres.items(), (PAYSANS, max(0, b - sum(autres.values())))) if p > 0}
    n, total = b // 10, sum(poids.values()); parts = {m: n * p // total for m, p in poids.items()}
    for m in sorted(poids, key=lambda m: (-(n * poids[m] % total), m))[:n - sum(parts.values())]: parts[m] += 1
    return parts
def _servi(refs):
    """La référence : Biskra partout, les ticks 5 puis 6, des métiers qui font la cellule, un chantier de rue à bras et un ouvrier attendus, puis le bourg vidé."""
    try:
        c, vus = refs["cellule"], {}
        if not _entier(c) or refs["vider"] != {"cell_id": c, "tick": TICK_CHANTIER}: raise ValueError(f"référence : vider-bourg rend {refs['vider']!r}, attendu la cellule {c!r} au tick {TICK_CHANTIER}")
        for s, tick in zip(ETATS, (TICK_CHANTIER, TICK_CHANTIER + 1)):
            lieu, plan = refs[s]["lieu"], refs[s]["plan"]; b, pop = lieu["bourg"]["population"], lieu["population"]
            if (cellules := {lieu["cell_id"], plan["cell_id"]}) != {c}: raise ValueError(f"référence {s} : cellules {sorted(cellules)} pour {c}")
            if (ticks := {lieu["tick"], lieu["bourg"]["tick"], plan["tick"]}) != {tick}: raise ValueError(f"référence {s} : ticks discordants {sorted(ticks)}, attendu {tick}")
            if (somme := sum(f["personnes"] for f in lieu["foyers"].values())) != pop or not 0 <= b <= pop: raise ValueError(f"référence {s} inutilisable : métiers {somme}, cellule {pop}, bourg {b}")
            rues = {u["identifiant"]: u["points"] for u in plan["rues"]}; vus[s] = {"tick": tick, "bourg": b, "attendus": passants_attendus(lieu), "bras": {x["identifiant"]: rues[x["identifiant"]] for x in plan["chantiers_du_jour"] if x["nature"] == "rue" and x["bras"] > 0}}
    except (KeyError, TypeError, AttributeError) as exc: raise ValueError(f"référence illisible : {exc!r}") from None
    if vus["vide"]["bourg"] != 0: raise ValueError(f"référence vide inutilisable : bourg vidé à {vus['vide']['bourg']} habitants")
    if not vus["chantier"]["bras"] or not vus["chantier"]["attendus"].get(OUVRIERS): raise ValueError(f"échantillon vide au tick {TICK_CHANTIER} : chantiers de rue à bras {sorted(vus['chantier']['bras'])}, ouvriers attendus {vus['chantier']['attendus'].get(OUVRIERS, 0)}")
    return vus
def _ecart(x, y, pts):
    """Distance horizontale d'un point du plan à une polyligne servie (Lot897.Ecart) ; l'infini sans segment."""
    return min((math.hypot(x - ax - t * dx, y - ay - t * dy) for (ax, ay), (bx, by) in zip(pts, pts[1:]) for dx, dy in [(bx - ax, by - ay)] for t in [min(1, max(0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy))) if dx or dy else 0]), default=math.inf)
def juger(rapport, refs) -> tuple[int, list[str]]:
    """Code 0, 1 ou 2, et les lignes. Fonction pure : les passants se comptent dans `liste`, les attendus viennent de la référence servie, jamais du rapport ni de son drapeau."""
    try: etats, servi = _rapport(rapport), _servi(refs)
    except ValueError as exc: return IMPOSSIBLE, [str(exc)]
    c, ids, parts = refs["cellule"], {s: collections.Counter(p["id"] for p in e["liste"]) for s, e in etats.items()}, lambda d: "{" + ", ".join(f"{m} {n}" for m, n in sorted(d.items())) + "}"
    lignes, comparaisons = [f"Biskra servie : cellule {c} · drapeau contre_epreuve du rapport : {rapport['contre_epreuve'] or 'aucun'} (affiché, jamais jugé)"], [("cellule", rapport["cellule"], c, rapport["cellule"] == c)]
    for s, e in etats.items():
        v, vus, att = servi[s], dict(collections.Counter(p["metier"] for p in e["liste"])), {m: n for m, n in servi[s]["attendus"].items() if n}
        comparaisons += [(f"{s} {k}", e[k], v["tick"], e[k] == v["tick"]) for k in ("tick_lieu", "tick_plan", "tick_applique")] + [(f"{s} bourg", e["bourg"], v["bourg"], e["bourg"] == v["bourg"]), (f"{s} nombre", parts(vus), parts(att), vus == att), (f"{s} passants", e["passants"], f"{len(e['liste'])}, la longueur de liste", e["passants"] == len(e["liste"])), (f"{s} id en double", sorted(i for i, k in ids[s].items() if k > 1), [], len(ids[s]) == len(e["liste"]))]
        texte = f"{s} : tick {e['tick_applique']} · bourg {e['bourg']} · {len(e['liste'])} passants vus {parts(vus)} · {sum(att.values())} attendus {parts(att)}"
        if s == "chantier":
            ouvriers = [p for p in e["liste"] if p["metier"] == OUVRIERS]; rue = lambda p: int(p["destination"][4:]) if p["destination"][:4] == "rue " and p["destination"][4:].isdigit() else None  # noqa: E731
            distances = {p["id"]: _ecart(p["x"], p["y"], v["bras"][rue(p)]) if rue(p) in v["bras"] else None for p in ouvriers}
            hors = [f"id {p['id']} vers « {p['destination']} » " + (f"à {d:.2f} m" if (d := distances[p["id"]]) is not None else "sans chantier à bras servi") for p in ouvriers if distances[p["id"]] is None or distances[p["id"]] > TOLERANCE_M]
            comparaisons.append(("chantier ouvrier hors chantier", "; ".join(hors), f"chaque ouvrier à {TOLERANCE_M} m au plus de sa rue à bras {sorted(v['bras'])}", not hors)); texte += f" · ouvriers sur un chantier {len(ouvriers) - len(hors)}/{len(ouvriers)}"
        else: comparaisons.append(("vide anciens objets maintenus", sorted(set(ids["vide"]) & set(ids["chantier"])), [], not set(ids["vide"]) & set(ids["chantier"])))
        lignes.append(texte + f" — servi : tick {v['tick']} · bourg {v['bourg']}")
    a, b = (e["camera"] for e in etats.values()); comparaisons.append(("caméra", "identique" if a == b else "changée entre les deux états", "identique", a == b))
    ecarts = [f"{nom} : {vu} · attendu {attendu} · ÉCART" for nom, vu, attendu, egal in comparaisons if not egal]
    return (ECART if ecarts else EGALITE), lignes + (ecarts or ["comparés : cellule, ticks, bourg, nombre par métier, id, ouvriers au chantier, vidage, caméra · égal"])
def _requete(port, methode, chemin, corps=None):
    """Une requête bornée ; un refus HTTP se dit avec son statut et son corps, une panne avec son délai."""
    try:
        with urllib.request.urlopen(urllib.request.Request(f"http://{HOTE}:{port}{chemin}", data=json.dumps(corps).encode() if corps is not None else b"" if methode == "POST" else None, method=methode, headers={"Content-Type": "application/json"}), timeout=JOUER.DELAI_REQUETE_S) as reponse: return json.loads(reponse.read())
    except urllib.error.HTTPError as exc: raise RuntimeError(f"{methode} {chemin} : HTTP {exc.code} « {exc.read().decode('utf-8', 'replace')} »") from None
    except OSError as exc: raise RuntimeError(f"{methode} {chemin} : {exc} (requête bornée à {JOUER.DELAI_REQUETE_S} s)") from None
def references(port):
    """Les gestes de Lot897.cs rejoués, le lieu et le plan au chantier, un seul POST /epreuve/vider-bourg, un tick, puis les mêmes lectures."""
    departs = _requete(port, "GET", "/departs")
    trouves = [d for d in (departs.get("departs") if _objet(departs) and _liste(departs.get("departs")) else []) if _objet(d) and _objet(d.get("siege")) and d["siege"].get("nom") == SIEGE]
    if len(trouves) != 1 or not _entier(c := trouves[0].get("cell_id")) or not _entier(sid := trouves[0].get("id")): raise ValueError(f"/departs : {len(trouves)} départ(s) au siège {SIEGE}, attendu un seul")
    def deposer(geste):
        if not _objet(r := _requete(port, "POST", "/intention", geste)) or r.get("acceptee") is not True: raise ValueError(f"intention {geste['type']} non acceptée : {r!r}")
    tick, lire = lambda: _requete(port, "POST", "/tick?n=1"), lambda: {"lieu": _requete(port, "GET", f"/lieu?cell={c}&bourg=1"), "plan": _requete(port, "GET", f"/plan?cell={c}")}  # noqa: E731
    deposer({"type": "choisir_depart", "seigneurie": sid}); tick(); [deposer({"type": "tracer_route", "maison": f"seigneurie-{sid}", "cell": c, "points": [[0, d], [LONGUEUR, d]], "largeur_m": LARGEUR}) for d in ORDONNEES]; [tick() for _ in range(TICK_CHANTIER - 1)]
    chantier = lire(); vider = _requete(port, "POST", f"/epreuve/vider-bourg?cell={c}"); tick(); return {"cellule": c, "chantier": chantier, "vider": vider, "vide": lire()}
def _reference(graine):
    """Le service de référence de #782 (même commande `--epreuve`, arrêté dans un finally), qui joue ici `references` de ce lot : VIE est un module chargé pour nous seuls."""
    VIE.references = references; return VIE._reference(graine)
def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Les passants de Biskra suivent-ils le bourg et les chantiers servis, puis le bourg vidé ?")
    parser.add_argument("--sortie", type=Path, required=True); parser.add_argument("--seed", type=JALON1._entier_positif, default=0); parser.add_argument("--unity", type=Path); parser.add_argument("--contre", choices=sorted(CONTRE))
    args = parser.parse_args(argv); (sortie := args.sortie.resolve()).mkdir(parents=True, exist_ok=True); rapport, journal = sortie / RAPPORT, sortie / "unity.log"
    for ancien in [sortie / "verdict.txt", rapport, *(p for i in IMAGES for p in sortie.glob(f"*--{i}.png"))]: ancien.unlink(missing_ok=True)
    drapeau = [CONTRE[args.contre]] if args.contre else []; entete = [f"graine {args.seed} · drapeau transmis à la session : {drapeau[0] if drapeau else 'aucun'}"]
    try:
        if not (unity := args.unity or JALON1._unity_par_defaut()).is_file(): raise RuntimeError(f"Unity absent : {unity}")
        if JOUER._repond(PORT): raise RuntimeError(f"le port {HOTE}:{PORT} répond déjà")
        debut, code = time.time(), JALON1._unity([str(unity), "-batchmode", "-projectPath", str(CAPITALE.PROJET), "-executeMethod", "ForgeLocal3D.Capture.Photographier", "-forgeLot", "897", "-forgeSeed", str(args.seed), "-forgeTicks", "0", "-forgeServiceEpreuve", "-forgeCaptures", str(sortie), "-logFile", str(journal), *drapeau])
        if (pid := JALON1._couper_service_residuel(sortie)) is not None: entete.append(f"service de la session resté ouvert, coupé (pid {pid})")
        if code != 0: raise RuntimeError(f"Unity a rendu {code} ; fin du journal :\n" + "\n".join((journal.read_text(encoding="utf-8", errors="replace").splitlines() if journal.is_file() else [])[-JALON1.LIGNES_JOURNAL_CITEES:]))
        neuf = lambda p: p.is_file() and p.stat().st_size > 0 and p.stat().st_mtime + JALON1.MARGE_HORODATAGE_S >= debut  # noqa: E731
        if (manque := [f"*--{i}.png" for i in IMAGES if not any(map(neuf, sortie.glob(f"*--{i}.png")))] + [rapport.name] * (not neuf(rapport))): raise RuntimeError(f"absent, vide ou antérieur à cet essai : {', '.join(manque)}")
        try: lu = json.loads(rapport.read_text(encoding="utf-8-sig"))
        except ValueError as exc: raise RuntimeError(f"rapport illisible : {exc}") from None
        refs = _reference(args.seed)
    except (RuntimeError, OSError, ValueError, http.client.HTTPException) as exc: return _ecrire(sortie, IMPOSSIBLE, entete + [str(exc)])  # IncompleteRead n'est pas une OSError
    code, lignes = juger(lu, refs); return _ecrire(sortie, code, entete + lignes)
if __name__ == "__main__": sys.exit(main(sys.argv[1:]))
