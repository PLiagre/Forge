"""L'épreuve de l'enceinte (lot #938) : 0 égalité, 1 écart, 2 impossible.   py pc\\epreuve_enceinte.py --sortie D [--seed S] [--unity CHEMIN] [--contre ignore|sans-porte]
Unity joue la session #937 sur son service d'épreuve, J journées par mètre ; un service d'épreuve neuf de même graine et même J (#936, déterministe) rejoue ensuite ses gestes et sert la référence. `juger` recompte les portes depuis `portes_dessinees` contre le plan servi, jamais `ecart_porte_m`, `tours` ni `pans` ; le drapeau `contre_epreuve` du rapport n'est qu'affiché."""
import argparse, collections, http.client, importlib.util, json, math, os, subprocess, sys, threading, time
from pathlib import Path
_spec = importlib.util.spec_from_file_location("epreuve_passants", Path(__file__).with_name("epreuve_passants.py")); PASSANTS = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(PASSANTS)
VIE, CAPITALE, JALON1, JOUER, HOTE, PORT, _valider, _ecrire, _arreter, _requete = PASSANTS.VIE, PASSANTS.CAPITALE, PASSANTS.JALON1, PASSANTS.JOUER, PASSANTS.HOTE, PASSANTS.PORT, PASSANTS._valider, PASSANTS._ecrire, PASSANTS._arreter, PASSANTS._requete
EGALITE, ECART, IMPOSSIBLE, _entier, _bool, _texte, _liste, _objet, _nombre, _cause = VIE.EGALITE, VIE.ECART, VIE.IMPOSSIBLE, VIE._entier, VIE._bool, VIE._texte, VIE._liste, VIE._objet, VIE._nombre, VIE._cause
# J, une seule constante, passée telle quelle à Unity (-forgeTravailEnceinte) et à la référence (--travail-enceinte). ROUTE, LARGEUR : la route de l'ouest de Lot937.cs, recopiée, sur laquelle s'ouvre la porte.
TRAVAIL, SIEGE, RAPPORT, IMAGES, SANS_PORTE, TOLERANCE_M, PREMIER, DERNIER, ROUTE, LARGEUR = "0.01", "Biskra", "lot937-enceinte.json", ("1-enceinte-en-chantier", "2-enceinte-finie"), "-forge937SansPorte", 0.05, 3, 14, [[-66, 2.2], [-120, 2.2]], 4
# Le service de référence de --contre ignore : ce lanceur chargé par son chemin, `recevoir_intention` rendue ignorante, puis le service ordinaire.
IGNORANT = "import importlib.util, sys; s = importlib.util.spec_from_file_location('epreuve_enceinte', sys.argv.pop(1)); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); import sim.service as v; v.recevoir_intention = m.ignorante(v.recevoir_intention); v.main(sys.argv[1:])"
HAUT = (("cellule", _entier), ("port", _entier), ("contre_epreuve", _texte), ("travail_enceinte", _texte), ("coins", _liste), ("recu", _objet), ("releves", _liste), ("acheve_au_tick", lambda v: v is None or _entier(v)), ("defaut", _cause))
RELEVE = (("tick", _entier), ("en_chantier", _bool), ("travail_fourni", _entier), ("travail_requis", _entier), ("etape", _texte), ("portes_servies", _liste), ("portes_dessinees", _liste))
PORTES = {"portes_servies": (("x", _nombre), ("y", _nombre), ("rue", _texte), ("identifiant", _entier)), "portes_dessinees": (("x", _nombre), ("y", _nombre))}
def ignorante(recevoir):  # « un moteur qui ignore l'intention » : tracer_enceinte reçue sans effet, toute autre intention transmise à `recevoir`
    return lambda monde, intention: None if intention.get("type") == "tracer_enceinte" else recevoir(monde, intention)
def travail_attendu(coins, travail):  # `travail_requis_de_enceinte` de sim/chantiers.py, recopiée dans le même ordre : périmètre bouclé, puis journées. Pure.
    return max(1, math.ceil(sum(math.dist(a, b) for a, b in zip(coins, (*coins[1:], coins[0]))) * float(travail)))
def _rapport(r, travail):
    """Le rapport #937, types stricts : un défaut, un −1, un reçu autre, un autre J, des ticks qui ne se suivent pas ou un échantillon vide rendent l'épreuve impossible."""
    _valider(r, HAUT, "rapport")
    if r["defaut"] is not None: raise ValueError(f"défaut de session : {r['defaut']}")
    if r["recu"] != {"acceptee": True, "tick": 2} or r["recu"]["acceptee"] is not True or not _entier(r["recu"]["tick"]): raise ValueError(f"reçu {r['recu']!r}, attendu {{acceptee: true, tick: 2}}")
    if r["travail_enceinte"] != travail: raise ValueError(f"travail_enceinte {r['travail_enceinte']!r} dans le rapport, {travail!r} à la référence")
    if len(r["coins"]) < 3 or not all(_liste(c) and len(c) == 2 and all(map(_nombre, c)) for c in r["coins"]): raise ValueError(f"coins {r['coins']!r} : trois coins finis au moins")
    for e in r["releves"]: _valider(e, RELEVE, f"relevé {e.get('tick') if _objet(e) else e!r}"); [_valider(p, schema, f"relevé {e['tick']}, {quoi}[{i}]") for quoi, schema in PORTES.items() for i, p in enumerate(e[quoi])]
    if (ticks := [e["tick"] for e in r["releves"]]) != list(range(PREMIER, PREMIER + len(ticks))) or len(ticks) > DERNIER - PREMIER + 1: raise ValueError(f"ticks des relevés {ticks}, attendu {PREMIER}, {PREMIER + 1}… sans dépasser {DERNIER}")
    if not any(e["portes_servies"] for e in r["releves"]): raise ValueError(f"échantillon vide : {len(ticks)} relevé(s), aucun avec une porte servie")
def _servi(refs):
    """La référence : J en texte, les plans des ticks 3 à 14, tous de la même cellule ; l'enceinte servie ou None, les portes en {x, y, rue, identifiant}."""
    try:
        c, plans = refs["cellule"], refs["plans"]; ticks, cellules = [p["tick"] for p in plans], {p["cell_id"] for p in plans}
        if not _texte(refs["travail"]) or ticks != list(range(PREMIER, DERNIER + 1)): raise ValueError(f"référence : travail {refs['travail']!r}, plans aux ticks {ticks}, attendu {PREMIER} à {DERNIER}")
        if not _entier(c) or cellules != {c}: raise ValueError(f"référence : cellules {sorted(cellules, key=str)} pour {c!r}")
        return {p["tick"]: ({k: e[k] for k in ("contour", "travail_requis", "travail_fourni", "en_chantier")} if (e := p.get("enceinte")) else None,
                            [{"x": q["point"][0], "y": q["point"][1], "rue": q["rue"], "identifiant": q["identifiant"]} for q in p.get("portes") or []]) for p in plans}
    except (KeyError, TypeError, AttributeError, IndexError) as exc: raise ValueError(f"référence illisible : {exc!r}") from None
def juger(rapport, refs) -> tuple[int, list[str]]:
    """Code 0, 1 ou 2, et les lignes. Fonction pure : le travail requis se recalcule, les portes se recomptent dans `portes_dessinees`, l'attendu vient du plan servi, jamais du rapport ni de son drapeau."""
    try: servi = _servi(refs); _rapport(rapport, refs["travail"])
    except ValueError as exc: return IMPOSSIBLE, [str(exc)]
    c, coins, sans = refs["cellule"], rapport["coins"], "aucune enceinte servie"; att = travail_attendu(coins, refs["travail"])
    lignes, comparaisons = [f"Biskra servie : cellule {c} · J {refs['travail']} · {att} journées requises · drapeau contre_epreuve du rapport : {rapport['contre_epreuve'] or 'aucun'} (affiché, jamais jugé)"], [("cellule", rapport["cellule"], c, rapport["cellule"] == c)]
    for e in rapport["releves"]:
        t, (enc, portes), n = e["tick"], servi[e["tick"]], len(e["portes_dessinees"]); vues = [{k: p[k] for k in ("x", "y", "rue", "identifiant")} for p in e["portes_servies"]]
        loin = [(p["x"], p["y"]) for p in portes if not any(math.hypot(p["x"] - d["x"], p["y"] - d["y"]) <= TOLERANCE_M for d in e["portes_dessinees"])]
        comparaisons += [(f"{t} contour", enc["contour"] if enc else sans, coins, bool(enc) and enc["contour"] == coins), (f"{t} travail requis (session)", e["travail_requis"], att, e["travail_requis"] == att),
                         (f"{t} travail requis (servi)", enc["travail_requis"] if enc else sans, att, bool(enc) and enc["travail_requis"] == att), (f"{t} portes servies", vues, portes, vues == portes),
                         (f"{t} portes dessinées", f"{n} dessinée(s)" + (f", servie(s) sans porte dessinée à {TOLERANCE_M} m : {loin}" if loin else ""), f"{len(portes)}, chaque servie à {TOLERANCE_M} m au plus d'une dessinée", n == len(portes) and not loin)]
        # Fourni, chantier et étape se comparent à une enceinte servie ; sans elle, le contour porte déjà l'écart.
        if enc: comparaisons += [(f"{t} {k.replace('_', ' ')}", e[k], enc[k], e[k] == enc[k]) for k in ("travail_fourni", "en_chantier")] + [(f"{t} étape", e["etape"], "autre que fini (servi en chantier)" if enc["en_chantier"] else "fini", (e["etape"] == "fini") != enc["en_chantier"])]
        lignes.append(f"tick {t} · fourni/requis vu {e['travail_fourni']}/{e['travail_requis']}, servi " + (f"{enc['travail_fourni']}/{enc['travail_requis']}" if enc else sans) + f" · étape {e['etape']} · portes dessinées/servies {n}/{len(portes)}")
    fin, dernier = next((t for t, (enc, _) in sorted(servi.items()) if enc and not enc["en_chantier"]), None), rapport["releves"][-1]["tick"]
    comparaisons.append(("achevée", f"acheve_au_tick {rapport['acheve_au_tick']}, dernier relevé au tick {dernier}", f"tick {fin}, le premier servi hors chantier" if fin is not None else "un tick servi hors chantier : aucun", fin is not None and rapport["acheve_au_tick"] == fin == dernier))
    ecarts = [f"{nom} : {vu} · attendu {attendu} · ÉCART" for nom, vu, attendu, egal in comparaisons if not egal]
    return (ECART if ecarts else EGALITE), lignes + ecarts + [f"achevée au tick {rapport['acheve_au_tick']} · servi : {fin if fin is not None else 'aucun achèvement'}" + ("" if ecarts else " · comparés : cellule, contour, travail requis et fourni, chantier, étape, portes servies et dessinées · égal")]
def references(port, coins, travail):
    """Les gestes de Lot937.cs rejoués : le départ au siège, un tick, la route de l'ouest, un tick, l'enceinte sur les coins du rapport (acceptée au tick 2), puis douze fois un tick et /plan."""
    departs = _requete(port, "GET", "/departs"); trouves = [d for d in (departs.get("departs") if _objet(departs) and _liste(departs.get("departs")) else []) if _objet(d) and _objet(d.get("siege")) and d["siege"].get("nom") == SIEGE]
    if len(trouves) != 1 or not _entier(c := trouves[0].get("cell_id")) or not _entier(sid := trouves[0].get("id")): raise ValueError(f"/departs : {len(trouves)} départ(s) au siège {SIEGE}, attendu un seul")
    def deposer(geste, tick=None):
        if not _objet(r := _requete(port, "POST", "/intention", geste)) or r.get("acceptee") is not True or tick is not None and r.get("appliquee_au_tick") != tick: raise ValueError(f"intention {geste['type']} : {r!r}, attendu acceptée" + (f" au tick {tick}" if tick is not None else ""))
    tick, geste = lambda: _requete(port, "POST", "/tick?n=1"), {"maison": f"seigneurie-{sid}", "cell": c}; deposer({"type": "choisir_depart", "seigneurie": sid}); tick(); deposer({"type": "tracer_route", **geste, "points": ROUTE, "largeur_m": LARGEUR}); tick(); deposer({"type": "tracer_enceinte", **geste, "points": coins}, 2)
    return {"cellule": c, "travail": travail, "coins": coins, "plans": [(tick(), _requete(port, "GET", f"/plan?cell={c}"))[1] for _ in range(PREMIER, DERNIER + 1)]}
def commande_reference(graine, ignore):  # même J que la session ; sous --contre ignore, le même service, qui accepte tracer_enceinte sans l'appliquer
    return [sys.executable, *(["-c", IGNORANT, str(Path(__file__).resolve())] if ignore else ["-m", "sim.service"]), "--epreuve", "--travail-enceinte", TRAVAIL, "--seed", str(graine), "--jours-par-seconde", "0"]
def _reference(graine, ignore, coins):
    """Le service de référence sur le port 8000, arrêté quoi qu'il arrive, même s'il ne devient jamais prêt."""
    service, stderr = subprocess.Popen(commande_reference(graine, ignore), cwd=JOUER.JEU_PY, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", env=os.environ | {"PYTHONIOENCODING": "utf-8"}), collections.deque(maxlen=JOUER.LIGNES_STDERR_GARDEES)
    try: threading.Thread(target=JOUER._lire_flux, args=(service.stderr, stderr.append), daemon=True).start(); JOUER._attendre_pret(service, f"service prêt sur {HOTE}:{PORT}", stderr); return references(PORT, coins, TRAVAIL)
    finally: _arreter(service)
def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Le mur servi à Biskra est-il celui des coins cliqués, à son prix, achevé, avec les portes que le monde sert ?")
    parser.add_argument("--sortie", type=Path, required=True); parser.add_argument("--seed", type=JALON1._entier_positif, default=0); parser.add_argument("--unity", type=Path); parser.add_argument("--contre", choices=("ignore", "sans-porte"))
    args = parser.parse_args(argv); (sortie := args.sortie.resolve()).mkdir(parents=True, exist_ok=True); rapport, journal = sortie / RAPPORT, sortie / "unity.log"
    for ancien in [sortie / "verdict.txt", rapport, *(p for i in IMAGES for p in sortie.glob(f"*--{i}.png"))]: ancien.unlink(missing_ok=True)
    drapeau = [SANS_PORTE] if args.contre == "sans-porte" else []; entete = [f"graine {args.seed} · J {TRAVAIL} · drapeau transmis à la session : {drapeau[0] if drapeau else 'aucun'} · référence : " + ("ignorante (tracer_enceinte sans effet)" if args.contre == "ignore" else "service d'épreuve")]
    try:
        if not (unity := args.unity or JALON1._unity_par_defaut()).is_file(): raise RuntimeError(f"Unity absent : {unity}")
        if JOUER._repond(PORT): raise RuntimeError(f"le port {HOTE}:{PORT} répond déjà")
        debut, code = time.time(), JALON1._unity([str(unity), "-batchmode", "-projectPath", str(CAPITALE.PROJET), "-executeMethod", "ForgeLocal3D.Capture.Photographier", "-forgeLot", "937", "-forgeSeed", str(args.seed), "-forgeTicks", "0",
                                                  "-forgeServiceEpreuve", "-forgeTravailEnceinte", TRAVAIL, "-forgeCaptures", str(sortie), "-logFile", str(journal), *drapeau])
        if (pid := JALON1._couper_service_residuel(sortie)) is not None: entete.append(f"service de la session resté ouvert, coupé (pid {pid})")
        if code != 0: raise RuntimeError(f"Unity a rendu {code} ; fin du journal :\n" + "\n".join((journal.read_text(encoding="utf-8", errors="replace").splitlines() if journal.is_file() else [])[-JALON1.LIGNES_JOURNAL_CITEES:]))
        neuf = lambda p: p.is_file() and p.stat().st_size > 0 and p.stat().st_mtime + JALON1.MARGE_HORODATAGE_S >= debut  # noqa: E731
        if (manque := [f"*--{i}.png" for i in IMAGES if not any(map(neuf, sortie.glob(f"*--{i}.png")))] + [rapport.name] * (not neuf(rapport))): raise RuntimeError(f"absent, vide ou antérieur à cet essai : {', '.join(manque)}")
        try: lu = json.loads(rapport.read_text(encoding="utf-8-sig"))
        except ValueError as exc: raise RuntimeError(f"rapport illisible : {exc}") from None
        _rapport(lu, TRAVAIL); refs = _reference(args.seed, args.contre == "ignore", lu["coins"])
    except (RuntimeError, OSError, ValueError, http.client.HTTPException) as exc: return _ecrire(sortie, IMPOSSIBLE, entete + [str(exc)])  # IncompleteRead n'est pas une OSError
    code, lignes = juger(lu, refs); return _ecrire(sortie, code, entete + lignes)
if __name__ == "__main__": sys.exit(main(sys.argv[1:]))
