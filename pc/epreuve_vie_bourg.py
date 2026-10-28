"""L'épreuve de la vie du bourg (lot #782) : 0 égalité, 1 écart, 2 impossible.   py pc\\epreuve_vie_bourg.py --sortie D [--seed S] [--unity CHEMIN] [--garder-etal-plein]
Unity joue la session #781 sur son service d'épreuve ; un service d'épreuve neuf de même graine (#777, déterministe) sert ensuite la référence. `juger` confronte les deux états relevés au bourg et à l'occupation servis ; le drapeau `contre_epreuve` du rapport n'est qu'affiché."""
import argparse, collections, http.client, importlib.util, json, math, os, subprocess, sys, threading, time, urllib.error, urllib.request
from pathlib import Path
_spec = importlib.util.spec_from_file_location("epreuve_transition", Path(__file__).with_name("epreuve_transition.py"))
TRANSITION = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(TRANSITION)
CAPITALE, JALON1, JOUER, HOTE, PORT = TRANSITION.CAPITALE, TRANSITION.JALON1, TRANSITION.JOUER, TRANSITION.HOTE, TRANSITION.PORT
_ecrire, _arreter = CAPITALE._ecrire, CAPITALE._arreter; EGALITE, ECART, IMPOSSIBLE = CAPITALE.EGALITE, CAPITALE.ECART, CAPITALE.IMPOSSIBLE
SIEGE, VIVRES, HEURE, ETATS, IMAGES, GARDER = "Biskra", "nourriture", 19.6, ("nourrie", "affamee"), ("01-place-nourrie", "02-place-affamee"), "-forgeGarderEtalPlein"
_entier, _bool, _texte, _liste, _objet = (lambda v: type(v) is int), (lambda v: type(v) is bool), (lambda v: type(v) is str), (lambda v: type(v) is list), (lambda v: isinstance(v, dict))  # noqa: E731
_nombre, _cause = (lambda v: type(v) is int or type(v) is float and math.isfinite(v)), (lambda v: v is None or type(v) is str)  # noqa: E731
HAUT = (("cellule", _entier), ("port", _entier), ("contre_epreuve", _bool), ("defaut", _cause), ("etats", _liste))
ETAT = (("nom", _texte), ("tick", _entier), ("tick_local", _entier), ("heure", _nombre), ("population", _entier), ("nourriture_kg", _nombre), ("faim_ticks", _entier), ("camera", lambda v: _liste(v) and len(v) == 16 and all(map(_nombre, v))),
        ("maisons", _liste), ("etals", _liste), ("garnitures_visibles", _entier), ("causes", lambda v: _liste(v) and all(map(_texte, v))))
SCHEMAS = {"maisons": (("rang", _entier), ("indice", _entier), ("emission", _bool), ("particules", _entier), ("lampe_active", _bool), ("intensite", _nombre), ("cause", _cause)),
           "etals": (("marchandise", _texte), ("reference_kg", _nombre), ("rapport", _nombre), ("hauteur", _nombre), ("visible", _bool), ("comptoir", _bool), ("cause", _cause))}

def _valider(objet, schema, nom):
    for cle, bon in schema:
        if not _objet(objet) or cle not in objet or not bon(v := objet[cle]): raise ValueError(f"{nom} : champ absent ou illisible : {cle}")
        if type(v) in (int, float) and v == -1: raise ValueError(f"{nom} : {cle} non mesuré (−1)")

def _rapport(r):
    """Le rapport #781, types stricts : un défaut, un −1 ou un échantillon vide rendent l'épreuve impossible."""
    _valider(r, HAUT, "rapport")
    if r["defaut"] is not None: raise ValueError(f"défaut de session : {r['defaut']}")
    for e in r["etats"]: _valider(e, ETAT, f"état {e.get('nom') if _objet(e) else e!r}")
    if (noms := [e["nom"] for e in r["etats"]]) != list(ETATS): raise ValueError(f"états {noms}, attendu {list(ETATS)}")
    for e in r["etats"]:
        for quoi, schema in SCHEMAS.items():
            if not e[quoi]: raise ValueError(f"{e['nom']} : échantillon vide : aucune entrée dans {quoi}")
            for i, x in enumerate(e[quoi]): _valider(x, schema, f"{e['nom']}.{quoi}[{i}]")
        if not any(x["marchandise"] == VIVRES for x in e["etals"]): raise ValueError(f"{e['nom']} : échantillon vide : aucun étal {VIVRES}")
    return dict(zip(ETATS, r["etats"]))

def _servi(refs):
    """La référence : un seul tick, la cellule de Biskra partout, une base habitée, le bourg nourri puis vidé."""
    try:
        c, vus = refs["cellule"], {}
        for s in ETATS:
            lieu, occ = refs[s]["lieu"], refs[s]["occupation"]; b = lieu["bourg"]; kg, faim = b["stocks"].get(VIVRES), b["duree_faim_ticks"]
            if not _liste(base := occ["base"]) or not base: raise ValueError(f"référence {s} : base d'occupation vide")
            if not all(_objet(m) and _entier(m.get("rang")) and _entier(m.get("foyers")) and m["foyers"] >= 1 for m in base): raise ValueError(f"référence {s} : base d'occupation illisible")
            if (cellules := {lieu["cell_id"], occ["cell_id"], *([refs["vider"]["cell_id"]] if s == "affamee" else [])}) != {c} or not _entier(c): raise ValueError(f"référence {s} : cellules {sorted(cellules)} pour {c!r}")
            vus[s] = {"tick": lieu["tick"], "ticks": {lieu["tick"], b["tick"], occ["tick"], *([refs["vider"]["tick"]] if s == "affamee" else [])}, "population": b["population"], "kg": kg, "faim": faim,
                      "maisons": {(m["rang"], j) for m in base for j in range(m["foyers"])}, "foyers": sum(m["foyers"] for m in base)}
            if not (_nombre(kg) and _entier(faim) and (kg > 0 and faim == 0 if s == "nourrie" else kg == 0 and faim > 0)): raise ValueError(f"référence {s} inutilisable : {VIVRES} {kg!r} kg, faim {faim!r} tick(s)")
    except (KeyError, TypeError, AttributeError) as exc: raise ValueError(f"référence illisible : {exc!r}") from None
    if len(ticks := vus["nourrie"]["ticks"] | vus["affamee"]["ticks"]) != 1 or not all(map(_entier, ticks)): raise ValueError(f"référence : ticks discordants {sorted(ticks, key=str)}")
    return vus

def juger(rapport, refs) -> tuple[int, list[str]]:
    """Code 0, 1 ou 2, et les lignes. Fonction pure : les attendus viennent de la référence servie, jamais du rapport ni de son drapeau."""
    try: etats, servi = _rapport(rapport), _servi(refs)
    except ValueError as exc: return IMPOSSIBLE, [str(exc)]
    c, (n, a) = refs["cellule"], etats.values()
    lignes, comparaisons = [f"Biskra servie : cellule {c} · drapeau contre_epreuve du rapport : {rapport['contre_epreuve']} (affiché, jamais jugé)"], [("cellule", rapport["cellule"], c, rapport["cellule"] == c)]
    for s, e in etats.items():
        v, m = servi[s], servi[s]["foyers"]; cles = collections.Counter((x["rang"], x["indice"]) for x in e["maisons"]); vivres = [x for x in e["etals"] if x["marchandise"] == VIVRES]
        fument, g, montre = sum(x["emission"] and x["particules"] > 0 if s == "nourrie" else x["emission"] or x["particules"] > 0 for x in e["maisons"]), e["garnitures_visibles"], any(x["visible"] for x in vivres)
        comparaisons += [(f"{s} {k}", e[k], v[w], e[k] == v[w]) for k, w in (("tick", "tick"), ("tick_local", "tick"), ("population", "population"), ("nourriture_kg", "kg"), ("faim_ticks", "faim"))]
        comparaisons += [(f"{s} maisons {k}", x, [], not x) for k, x in (("manquantes", sorted(v["maisons"] - set(cles))), ("en double", sorted(k for k, i in cles.items() if i > 1)), ("inconnues", sorted(set(cles) - v["maisons"])))]
        comparaisons += [(f"{s} fumées", f"{fument}/{m}", f"{m if s == 'nourrie' else 0}/{m}", fument == (m if s == "nourrie" else 0)), (f"{s} causes", e["causes"], [], not e["causes"]), (f"{s} heure", e["heure"], HEURE, e["heure"] == HEURE)]
        vu = f"{g} garniture(s) visible(s), étal {VIVRES} {'visible' if montre else 'caché'}, référence {sorted({x['reference_kg'] for x in vivres})} kg"
        if s == "nourrie": comparaisons.append(("nourrie étal", vu, f"garniture visible, étal {VIVRES} visible, référence [{v['kg']!r}] kg", g > 0 and montre and all(x["reference_kg"] == v["kg"] for x in vivres)))
        else: comparaisons.append(("affamee étal", ("étal plein en famine : " if g or montre else "") + vu, f"0 garniture visible, étal {VIVRES} caché, {VIVRES} servie {v['kg']!r} kg", g == 0 and not montre))
        lignes.append(f"{s} : tick {e['tick']} (local {e['tick_local']}) · {e['population']} habitants · {e['nourriture_kg']!r} kg · faim {e['faim_ticks']} · {len(e['maisons'])} maisons · fumées {fument}/{m} · étal {'garni' if g else 'vide'}, {g} garniture(s) visible(s)"
                      f" — servi : tick {v['tick']} · {v['population']} habitants · {v['kg']!r} kg · faim {v['faim']} · {m} foyers")
    lampes = {k: [{(x["rang"], x["indice"]): x for x in e["maisons"]}.get(k) for e in (n, a)] for k in {(x["rang"], x["indice"]) for e in (n, a) for x in e["maisons"]}}
    eteintes = sorted(k for k, (x, y) in lampes.items() if not (x and y and x["lampe_active"] and y["lampe_active"] and x["intensite"] > 0 and x["intensite"] == y["intensite"]))
    comparaisons += [("lampes éteintes ou changées", eteintes, [], not eteintes), ("caméra", "identique" if n["camera"] == a["camera"] else "changée entre les deux états", "identique", n["camera"] == a["camera"])]
    ecarts = [f"{nom} : {vu} · attendu {attendu} · ÉCART" for nom, vu, attendu, egal in comparaisons if not egal]
    return (ECART if ecarts else EGALITE), lignes + (ecarts or ["comparés : cellule, ticks, bourg, maisons, fumées, causes, heure, étal, lampes, caméra · égal"])

def _requete(port, methode, chemin):
    """Une requête bornée ; un refus HTTP se dit avec son statut et son corps, une panne avec son délai."""
    demande = urllib.request.Request(f"http://{HOTE}:{port}{chemin}", data=b"" if methode == "POST" else None, method=methode)
    try:
        with urllib.request.urlopen(demande, timeout=JOUER.DELAI_REQUETE_S) as reponse: return json.loads(reponse.read())
    except urllib.error.HTTPError as exc: raise RuntimeError(f"{methode} {chemin} : HTTP {exc.code} « {exc.read().decode('utf-8', 'replace')} »") from None
    except OSError as exc: raise RuntimeError(f"{methode} {chemin} : {exc} (requête bornée à {JOUER.DELAI_REQUETE_S} s)") from None

def references(port):
    """Biskra par /departs, son bourg et son occupation, un seul POST /epreuve/vider-panier, puis les mêmes lectures."""
    departs = _requete(port, "GET", "/departs")
    trouves = [d.get("cell_id") for d in (departs.get("departs") if _objet(departs) and _liste(departs.get("departs")) else []) if _objet(d) and _objet(d.get("siege")) and d["siege"].get("nom") == SIEGE]
    if len(trouves) != 1 or not _entier(c := trouves[0]): raise ValueError(f"/departs : {len(trouves)} départ(s) au siège {SIEGE}, attendu un seul")
    lire = lambda: {"lieu": _requete(port, "GET", f"/lieu?cell={c}&bourg=1"), "occupation": _requete(port, "GET", f"/occupation?cell={c}")}  # noqa: E731
    nourrie = lire(); vider = _requete(port, "POST", f"/epreuve/vider-panier?cell={c}")
    return {"cellule": c, "nourrie": nourrie, "vider": vider, "affamee": lire()}

def _reference(graine):
    """Le service de référence, arrêté quoi qu'il arrive, même s'il ne devient jamais prêt."""
    service, stderr = subprocess.Popen([sys.executable, "-m", "sim.service", "--epreuve", "--seed", str(graine), "--jours-par-seconde", "0"], cwd=JOUER.JEU_PY, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, encoding="utf-8", errors="replace", env=os.environ | {"PYTHONIOENCODING": "utf-8"}), collections.deque(maxlen=JOUER.LIGNES_STDERR_GARDEES)
    try: threading.Thread(target=JOUER._lire_flux, args=(service.stderr, stderr.append), daemon=True).start(); JOUER._attendre_pret(service, f"service prêt sur {HOTE}:{PORT}", stderr); return references(PORT)
    finally: _arreter(service)

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Les signes de vie de Biskra suivent-ils le bourg servi, nourri puis affamé ?")
    parser.add_argument("--sortie", type=Path, required=True); parser.add_argument("--seed", type=JALON1._entier_positif, default=0); parser.add_argument("--unity", type=Path); parser.add_argument("--garder-etal-plein", action="store_true")
    args = parser.parse_args(argv); (sortie := args.sortie.resolve()).mkdir(parents=True, exist_ok=True); rapport, journal = sortie / "vie-bourg.json", sortie / "unity.log"
    for ancien in [sortie / "verdict.txt", rapport, *(p for i in IMAGES for p in sortie.glob(f"*--{i}.png"))]: ancien.unlink(missing_ok=True)
    entete = [f"graine {args.seed} · drapeau transmis à la session : {GARDER if args.garder_etal_plein else 'aucun'}"]
    try:
        if not (unity := args.unity or JALON1._unity_par_defaut()).is_file(): raise RuntimeError(f"Unity absent : {unity}")
        if JOUER._repond(PORT): raise RuntimeError(f"le port {HOTE}:{PORT} répond déjà")
        debut = time.time()
        code = JALON1._unity([str(unity), "-batchmode", "-projectPath", str(CAPITALE.PROJET), "-executeMethod", "ForgeLocal3D.Capture.Photographier", "-forgeLot", "781", "-forgeSeed", str(args.seed), "-forgeTicks", "0",
                              "-forgeServiceEpreuve", "-forgeCaptures", str(sortie), "-logFile", str(journal), *([GARDER] if args.garder_etal_plein else [])])
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
