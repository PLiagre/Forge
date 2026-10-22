"""L'épreuve de la ville de 1400 (lot #740) : 0 égalité, 1 écart, 2 impossible.   py pc\\epreuve_ville1400.py --sortie D [--seed S] [--unity CHEMIN] [--sauter | --ajouter]
Deux services neufs de même graine, en pause ; sur chacun, Unity joue la session #739 (Jouer, puis Relancer) et Python lit les quatre `/plan`.
`juger` attend un couple (rang, indice) par foyer de `plan.base.maisons`, jamais des rapports ni du drapeau."""
import argparse, collections, hashlib, http.client, importlib.util, json, math, os, re, subprocess, sys, threading, time
from pathlib import Path
_spec = importlib.util.spec_from_file_location("epreuve_transition", Path(__file__).with_name("epreuve_transition.py"))
TRANSITION = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(TRANSITION)
CAPITALE, JALON1, JOUER, HOTE, PORT = TRANSITION.CAPITALE, TRANSITION.JALON1, TRANSITION.JOUER, TRANSITION.HOTE, TRANSITION.PORT
_http, _ecrire, _arreter = TRANSITION._http, CAPITALE._ecrire, CAPITALE._arreter; EGALITE, ECART, IMPOSSIBLE = CAPITALE.EGALITE, CAPITALE.ECART, CAPITALE.IMPOSSIBLE
CELLULES, BISKRA, SESSIONS, TOL = (10103, 1175, 1232, 10337), 10103, ("jouer", "relance"), 0.05  # le contrat #739 : l'échantillon, jamais les attendus
METHODES = {"jouer": "ForgeLocal3D.EpreuveVille1400.Jouer", "relance": "ForgeLocal3D.EpreuveVille1400.Relancer"}
CHAMPS = (*((c, "texte") for c in ("session", "contre_epreuve", "absence", "empreinte", "empreinte_rues", "defaut")), *((c, "entier") for c in ("cellule", "tick", "foyers", "posees", "rues_dessinees", "images")), ("duree_dessin_ms", "nombre"), ("image_ms", "nombre"), ("refus", "textes"), ("maisons", "textes"))
COMPARES = ("tick", "foyers", "posees", "refus", "maisons", "empreinte", "rues_dessinees", "empreinte_rues")
_nombre, _objet = (lambda v: type(v) is int or type(v) is float and math.isfinite(v)), (lambda v: isinstance(v, dict))  # noqa: E731
BONS = {"texte": lambda v: type(v) is str, "entier": lambda v: type(v) is int, "nombre": _nombre, "textes": lambda v: type(v) is list and all(type(t) is str for t in v)}
_REFUS, _ENTIER = re.compile(r"Maison (\d{1,9}) indice (\d{1,9}) : (\S.*)"), re.compile(r"-?\d{1,9}")
_croix = lambda a, b, c: (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])  # noqa: E731
empreinte = lambda lignes: hashlib.sha256("".join(l + "\n" for l in lignes).encode("utf-8")).hexdigest()  # noqa: E731

def _plan(plan, c, s):
    base, nom = plan.get("base") if _objet(plan) else None, f"/plan?cell={c} ({s})"
    if not _objet(plan) or type(plan.get("cell_id")) is not int or plan["cell_id"] != c: raise ValueError(f"{nom} : cell_id absent ou autre")
    if type(plan.get("tick")) is not int or plan["tick"] < 0: raise ValueError(f"{nom} : tick absent ou non mesuré")
    if not _objet(base) or type(base.get("cell_id")) is not int or base["cell_id"] != c or type(base.get("maisons")) is not list or not base["maisons"]: raise ValueError(f"{nom} : base absente, vide ou d'une autre cellule")
    for i, m in enumerate(base["maisons"]):
        e = m.get("emprise") if _objet(m) else None
        if not _objet(m) or type(m.get("foyers")) is not int or m["foyers"] < 1: raise ValueError(f"{nom} : maison {i}, foyers absents ou < 1")
        if type(e) is not list or len(e) < 3 or not all(type(p) is list and len(p) == 2 and all(map(_nombre, p)) for p in e): raise ValueError(f"{nom} : maison {i}, emprise illisible")
        tours = [math.atan2(_croix(a, b, c), (b[0] - a[0]) * (c[0] - b[0]) + (b[1] - a[1]) * (c[1] - b[1])) for a, b, c in zip(e, e[1:] + e[:1], e[2:] + e[:2])]  # angles strictement d'un même sens et un seul tour : un pentagramme en fait deux
        if not (all(0 < t < math.pi for t in tours) or all(-math.pi < t < 0 for t in tours)) or abs(sum(tours)) > 3 * math.pi: raise ValueError(f"{nom} : maison {i}, emprise non convexe ou dégénérée")

def _maison(ligne, nom):
    v = ligne.split(" ")
    try:
        if len(v) != 7 or not all(_ENTIER.fullmatch(t) for t in v[:3]) or not all(map(math.isfinite, reels := [float(t) for t in v[3:]])): raise ValueError
    except ValueError: raise ValueError(f"{nom} : ligne de maison illisible : {ligne!r}") from None
    if min(entiers := [int(t) for t in v[:3]]) < 0: raise ValueError(f"{nom} : maison non mesurée (−1) : {ligne!r}")
    return (*entiers, *reels)

def _rapport(r, c, s):
    nom = f"{c}/{s}"
    if not _objet(r) or not r: raise ValueError(f"{nom} : rapport absent ou vide")
    if (cle := next((cle for cle, genre in CHAMPS if cle not in r or not BONS[genre](r[cle])), None)): raise ValueError(f"{nom} : champ absent ou illisible : {cle}")
    if (cle := next((c for c in ("defaut", "absence") if r[c]), None)): raise ValueError(f"{nom} : {'défaut de session' if cle == 'defaut' else 'absence déclarée'} : {r[cle]}")
    if (cle := next((c for c in ("cellule", "tick", "foyers", "posees", "rues_dessinees") if r[c] < 0), None)): raise ValueError(f"{nom} : {cle} non mesuré : {r[cle]}")
    if r["images"] <= 0 or r["duree_dessin_ms"] <= 0 or r["image_ms"] <= 0: raise ValueError(f"{nom} : temps non mesuré : dessin {r['duree_dessin_ms']} ms, {r['images']} images à {r['image_ms']} ms")
    if (cle := next((k for k in ("empreinte", "empreinte_rues") if not re.fullmatch(r"[0-9a-f]{64}", r[k])), None)): raise ValueError(f"{nom} : {cle} illisible : {r[cle]!r}")
    refus = [(int(m[1]), int(m[2]), m[3]) if (m := _REFUS.fullmatch(t)) else None for t in r["refus"]]
    if None in refus: raise ValueError(f"{nom} : refus illisible : {r['refus'][refus.index(None)]!r}")
    return [_maison(l, nom) for l in r["maisons"]], refus

def _dedans(x, y, e):
    signe, bords = (1 if sum(_croix(e[k], e[(k + 1) % len(e)], e[(k + 2) % len(e)]) for k in range(len(e))) > 0 else -1), list(zip(e, e[1:] + e[:1]))
    if all(signe * _croix(a, b, (x, y)) >= 0 for a, b in bords): return True
    def distance(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]; t = max(0, min(1, ((x - a[0]) * dx + (y - a[1]) * dy) / (dx * dx + dy * dy))); return math.hypot(x - a[0] - t * dx, y - a[1] - t * dy)
    return min(distance(a, b) for a, b in bords) <= TOL

def juger(jouer, relance, plans_jouer, plans_relance) -> tuple[int, list[str]]:
    rapports, plans, lus = dict(zip(SESSIONS, (jouer, relance))), dict(zip(SESSIONS, (plans_jouer, plans_relance))), {}
    try:
        for s in SESSIONS:
            for quoi, ens in (("rapports", rapports[s]), ("références", plans[s])):
                if not _objet(ens) or set(ens) != set(CELLULES): raise ValueError(f"{s} : {quoi} des cellules {sorted(ens) if _objet(ens) else ens!r}, attendu {list(CELLULES)}")
            for c in CELLULES: _plan(plans[s][c], c, s); lus[c, s] = _rapport(rapports[s][c], c, s)
    except ValueError as exc: return IMPOSSIBLE, [str(exc)]
    lignes, ecart = [], False
    for c in CELLULES:
        for s in SESSIONS:
            r, plan, (maisons, refus) = rapports[s][c], plans[s][c], lus[c, s]; base = plan["base"]["maisons"]; f = sum(m["foyers"] for m in base)
            attendus, vus = {(i, j) for i, m in enumerate(base) for j in range(m["foyers"])}, collections.Counter([m[:2] for m in maisons] + [x[:2] for x in refus])
            comparaisons = [("libellé de session", r["session"], s), ("cellule", r["cellule"], c), ("tick", r["tick"], plan["tick"]), ("foyers", r["foyers"], f), ("posées", r["posees"], len(maisons)), ("posées + refus", r["posees"] + len(refus), f), ("doublons", sorted(k for k, n in vus.items() if n > 1), []), ("couples inconnus", sorted(set(vus) - attendus), []), ("couples manquants", sorted(attendus - set(vus)), []), ("refus à Biskra", len(refus) if c == BISKRA else 0, 0), ("variante", [m[:3] for m in maisons if m[2] != (m[0] + m[1]) % 6], []), ("hors emprise", [m[:2] + tuple(m[3:5]) for m in maisons if m[0] < len(base) and not _dedans(m[3], m[4], base[m[0]]["emprise"])], []), ("empreinte recalculée", empreinte(r["maisons"]), r["empreinte"])]
            lignes.append(f"{c}/{s} : foyers attendus du plan {f} · posées {r['posees']} · refus {len(refus)}" + "".join(f" — {t}" for t in r["refus"]) + f" · dessin {r['duree_dessin_ms']:.1f} ms · {1000 / r['image_ms']:.1f} images/s sur {r['images']} images" + (f" · drapeau {r['contre_epreuve']}" if r["contre_epreuve"] else ""))
            ajouts = [f"{c}/{s} {nom} : {vu} · attendu {attendu} · ÉCART · référence /plan?cell={c} ({s}, tick {plan['tick']})" for nom, vu, attendu in comparaisons if vu != attendu]
            if ajouts: ecart = True; lignes.extend(ajouts)
        a, b = rapports["jouer"][c], rapports["relance"][c]
        differents = [k for k in COMPARES if a[k] != b[k]] + (["références"] if plans_jouer[c] != plans_relance[c] else [])
        for k in differents: ecart, vu = True, (sorted(set(a[k]) ^ set(b[k]))[:3] if k == "maisons" else None); lignes.append(f"{c} relance {k} : " + (f"lignes différentes, dont {vu}" if vu is not None else "les deux /plan diffèrent" if k == "références" else f"jouer {a[k]} · relance {b[k]}") + " · ÉCART")
        if not differents: lignes.append(f"{c} jouer/relance : références, {', '.join(COMPARES)} · égal")
    return (ECART if ecart else EGALITE), lignes

def _ouvrir(graine, garde):
    stderr = collections.deque(maxlen=JOUER.LIGNES_STDERR_GARDEES)
    garde.append(service := subprocess.Popen([sys.executable, "-m", "sim.service", "--seed", str(graine), "--jours-par-seconde", "0"], cwd=JOUER.JEU_PY, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", env=os.environ | {"PYTHONIOENCODING": "utf-8"}))
    threading.Thread(target=JOUER._lire_flux, args=(service.stderr, stderr.append), daemon=True).start(); JOUER._attendre_pret(service, f"service prêt sur {HOTE}:{PORT}", stderr)

def _essai(unity, sortie, session, graine, drapeau):
    garde = []
    try:
        _ouvrir(graine, garde); debut = time.time()
        commande = [str(unity), "-batchmode", "-projectPath", str(CAPITALE.PROJET), "-executeMethod", METHODES[session], "-forgeEpreuve", str(sortie), "-logFile", str(sortie / f"unity-{session}.log")]
        if (code := JALON1._unity(commande + ([drapeau] if drapeau and session == "jouer" else []))) != 0: raise RuntimeError(f"Unity ({session}) a rendu {code}")
        plans = {c: _http("GET", f"/plan?cell={c}") for c in CELLULES}
    finally:
        for service in garde: _arreter(service)
    lus = {}
    for c in CELLULES:
        if not (f := sortie / f"{session}-{c}.json").is_file() or f.stat().st_mtime + JALON1.MARGE_HORODATAGE_S < debut: raise RuntimeError(f"rapport absent ou antérieur à cet essai : {f.name}")
        try: lus[c] = json.loads(f.read_text(encoding="utf-8"))
        except ValueError as exc: raise RuntimeError(f"rapport invalide {f.name} : {exc}") from None
    return lus, plans

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Unity relancé redessine-t-il la même ville de 1400 d'après le monde ?")
    parser.add_argument("--sortie", type=Path, required=True); parser.add_argument("--seed", type=JALON1._entier_positif, default=0); parser.add_argument("--unity", type=Path)
    (contre := parser.add_mutually_exclusive_group()).add_argument("--sauter", action="store_true"); contre.add_argument("--ajouter", action="store_true")
    args = parser.parse_args(argv); (sortie := args.sortie.resolve()).mkdir(parents=True, exist_ok=True)
    drapeau = "-forgeSauter" if args.sauter else "-forgeAjouter" if args.ajouter else ""
    for ancien in ["verdict.txt", *(f"{s}-{c}.json" for s in SESSIONS for c in CELLULES)]: (sortie / ancien).unlink(missing_ok=True)
    entete, essais = [f"graine {args.seed} · drapeau transmis à Jouer : {drapeau or 'aucun'}"], {}
    try:
        if not (unity := args.unity or JALON1._unity_par_defaut()).is_file(): raise RuntimeError(f"Unity absent : {unity}")
        entete.append(f"Unity {unity}")
        for s in SESSIONS:
            if JOUER._repond(PORT): raise RuntimeError(f"le port {HOTE}:{PORT} répond déjà")
            essais[s] = _essai(unity, sortie, s, args.seed, drapeau)
    except (RuntimeError, OSError, ValueError, http.client.HTTPException) as exc: return _ecrire(sortie, IMPOSSIBLE, entete + [str(exc)])  # IncompleteRead n'est pas une OSError
    code, lignes = juger(essais["jouer"][0], essais["relance"][0], essais["jouer"][1], essais["relance"][1]); return _ecrire(sortie, code, entete + lignes)

if __name__ == "__main__": sys.exit(main(sys.argv[1:]))
