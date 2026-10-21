"""L'épreuve de la transition (lot #733) : 0 égalité, 1 écart, 2 impossible.   py pc\\epreuve_transition.py --sortie D [--seed S] [--unity CHEMIN]
Service neuf à 1 j/s, Zab choisi par son nom et appliqué au jour naturel suivant, session #732 sans attendu ; `juger` confronte ses relevés aux réglages et au siège servi."""
import argparse, collections, http.client, importlib.util, json, math, os, subprocess, sys, threading, time, urllib.error, urllib.request
from pathlib import Path

_spec = importlib.util.spec_from_file_location("epreuve_capitale", Path(__file__).with_name("epreuve_capitale.py"))
CAPITALE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CAPITALE)
JALON1, JOUER, HOTE, PORT = CAPITALE.JALON1, CAPITALE.JOUER, CAPITALE.SERVICE_HOST, CAPITALE.DEFAULT_SERVICE_PORT
_fiche, _siege, _ecrire, _arreter = CAPITALE._fiche, CAPITALE._siege, CAPITALE._ecrire, CAPITALE._arreter
EGALITE, ECART, IMPOSSIBLE = CAPITALE.EGALITE, CAPITALE.ECART, CAPITALE.IMPOSSIBLE
METHODE, DEPART, ATTENTE_CHOIX_S, PAS_S = "ForgeLocal3D.EpreuveTransition.Jouer", 1, 30, 0.5
RELEVES, CLES = ("carte_avant", "ville_apres", "ville_avant", "carte_apres"), ("VITESSE_VILLE", "VITESSE_CARTE")
SCENES = (CAPITALE.SCENE_CARTE, CAPITALE.SCENE_VILLE, CAPITALE.SCENE_VILLE, CAPITALE.SCENE_CARTE)
_nombre = lambda v: type(v) is int or type(v) is float and math.isfinite(v)  # noqa: E731
_entier, _texte, _objet = lambda v: type(v) is int, lambda v: type(v) is str, lambda v: isinstance(v, dict)  # noqa: E731

def _reglages(reglages):
    for c in CLES:  # aucun repli : une clé absente, booléenne, nulle ou infinie rend l'épreuve impossible
        if not _nombre(v := reglages.get(c) if _objet(reglages) else None) or v <= 0:
            raise ValueError(f"réglage {c} absent ou invalide : {v!r}, attendu un nombre fini > 0")

def _valider(rapport, reglages, siege):
    """Références puis rapport #732, types stricts : un champ absent n'est jamais zéro ; −1 ou un défaut rendent l'épreuve impossible."""
    _reglages(reglages)
    if type(siege) is not int or siege < 0: raise ValueError(f"siège de référence absent ou invalide : {siege!r}")
    if not _objet(rapport) or not rapport: raise ValueError("rapport absent ou vide")
    for cle, bon in (("cellule", _entier), ("defaut", _texte), *((r, _objet) for r in RELEVES)):
        if cle not in rapport or not bon(rapport[cle]): raise ValueError(f"champ absent ou illisible : {cle}")
    for nom in RELEVES:
        for champ, bon in (("tick", _entier), ("jours_par_seconde", _nombre), ("scene", _texte)):
            if champ not in rapport[nom] or not bon(rapport[nom][champ]): raise ValueError(f"champ absent ou illisible : {nom}.{champ}")
    if rapport["defaut"]: raise ValueError(f"défaut de session : {rapport['defaut']}")
    for nom, v in [("cellule", rapport["cellule"])] + [(f"{r}.{c}", rapport[r][c]) for r in RELEVES for c in ("tick", "jours_par_seconde")]:
        if v < 0: raise ValueError(f"{nom} non mesuré : {v!r}")

def juger(rapport, reglages, siege) -> tuple[int, list[str]]:
    """Code 0, 1 ou 2, et les lignes. Les attendus viennent des réglages et du siège donnés, jamais du rapport."""
    try: _valider(rapport, reglages, siege)
    except ValueError as exc: return IMPOSSIBLE, [str(exc)]
    t, vitesses = [rapport[nom]["tick"] for nom in RELEVES], (DEPART, reglages["VITESSE_VILLE"], reglages["VITESSE_VILLE"], reglages["VITESSE_CARTE"])
    comparaisons = [("cellule", rapport["cellule"], f"siège {siege}", rapport["cellule"] == siege)]
    for nom, scene, v, r in zip(RELEVES, SCENES, vitesses, (rapport[n] for n in RELEVES)):
        comparaisons += [(f"{nom} scène", repr(r["scene"]), repr(scene), r["scene"] == scene), (f"{nom} vitesse", f"{r['jours_par_seconde']!r} j/s", f"{v!r} j/s", r["jours_par_seconde"] == v)]
    comparaisons += [("descente", f"ticks {t[0]} → {t[1]}", "ville_apres > carte_avant", t[1] > t[0]),
                     ("en ville", f"ticks {t[1]} → {t[2]}", "ville_avant ≥ ville_apres", t[2] >= t[1]),
                     ("retour", f"ticks {t[2]} → {t[3]}", "carte_apres > ville_avant", t[3] > t[2])]
    lignes = [f"{nom} : {vu} · attendu {attendu} · {'égal' if egal else 'ÉCART'}" for nom, vu, attendu, egal in comparaisons]
    return (EGALITE if all(c[3] for c in comparaisons) else ECART), lignes

def _http(methode, chemin, corps=None):
    """Une requête bornée ; un refus HTTP se dit avec son statut et son corps."""
    demande = urllib.request.Request(f"http://{HOTE}:{PORT}{chemin}", data=None if corps is None else json.dumps(corps).encode("utf-8"), method=methode, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(demande, timeout=JOUER.DELAI_REQUETE_S) as reponse: return json.loads(reponse.read())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"{methode} {chemin} : HTTP {exc.code} « {exc.read().decode('utf-8', 'replace')} »") from None

def _ouvrir(graine, garde):
    """Le service neuf à DEPART j/s, gardé dès sa création : l'appelant l'arrête même s'il ne devient jamais prêt."""
    stderr = collections.deque(maxlen=JOUER.LIGNES_STDERR_GARDEES)
    garde.append(service := subprocess.Popen(
        [sys.executable, "-m", "sim.service", "--seed", str(graine), "--port", str(PORT), "--jours-par-seconde", str(DEPART)], cwd=JOUER.JEU_PY,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", env=os.environ | {"PYTHONIOENCODING": "utf-8"}))
    threading.Thread(target=JOUER._lire_flux, args=(service.stderr, stderr.append), daemon=True).start()
    JOUER._attendre_pret(service, f"service prêt sur {HOTE}:{PORT}", stderr)

def _attendre_choix(maison):
    """Le jour naturel suivant applique le choix : lectures espacées de `/monde`, ATTENTE_CHOIX_S au plus."""
    echeance = time.monotonic() + ATTENTE_CHOIX_S
    while (vue := (m.get("maison_du_joueur") if _objet(m := _http("GET", "/monde")) else None)) != maison:
        if time.monotonic() >= echeance: raise RuntimeError(f"choix jamais appliqué : maison_du_joueur {vue!r} après {ATTENTE_CHOIX_S} s, attendu {maison}")
        time.sleep(PAS_S)

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="La vitesse suit-elle la vue et l'horloge avance-t-elle à chaque transition ?")
    for option, genre, defaut in (("--sortie", Path, None), ("--seed", JALON1._entier_positif, 0), ("--unity", Path, None)):
        parser.add_argument(option, type=genre, default=defaut, required=option == "--sortie")
    args = parser.parse_args(argv)
    (sortie := args.sortie.resolve()).mkdir(parents=True, exist_ok=True)
    rapport, journal, garde, entete = sortie / "rapport.json", sortie / "unity.log", [], [f"graine {args.seed} · départ {DEPART} j/s"]
    for ancien in (rapport, sortie / "verdict.txt"): ancien.unlink(missing_ok=True)
    try:
        if not (unity := args.unity or JALON1._unity_par_defaut()).is_file(): raise RuntimeError(f"Unity absent : {unity}")
        if JOUER._repond(PORT): raise RuntimeError(f"le port {HOTE}:{PORT} répond déjà")
        _reglages(reglages := json.loads(JOUER.REGLAGES.read_text(encoding="utf-8")))
        entete.append(f"réglages {JOUER.REGLAGES.name} : " + " · ".join(f"{c} {reglages[c]!r}" for c in CLES))
        _ouvrir(args.seed, garde)
        fiche, _t = _fiche(_http("GET", "/departs"), CAPITALE.ZAB)
        recu = _http("POST", "/intention", {"type": "choisir_depart", "seigneurie": fiche["id"]})
        if not _objet(recu) or recu.get("acceptee") is not True: raise RuntimeError(f"choix refusé : {recu!r}")
        _attendre_choix(f"seigneurie-{fiche['id']}")
        siege = _siege(_http("GET", f"/maison?id=seigneurie-{fiche['id']}"), fiche)
        entete.append(f"{CAPITALE.ZAB} : id {fiche['id']} · siège de référence {siege}")
        debut = time.time()
        code = JALON1._unity([str(unity), "-batchmode", "-projectPath", str(CAPITALE.PROJET), "-executeMethod", METHODE, "-forgeEpreuve", str(rapport), "-logFile", str(journal)])
        if code != 0: raise RuntimeError(f"Unity a rendu {code}")
        if not rapport.is_file() or rapport.stat().st_mtime + JALON1.MARGE_HORODATAGE_S < debut: raise RuntimeError(f"rapport absent ou antérieur à cet essai : {rapport.name}")
        try: lu = json.loads(rapport.read_text(encoding="utf-8"))
        except ValueError as exc: raise RuntimeError(f"rapport invalide : {exc}") from None
    except (RuntimeError, OSError, ValueError, http.client.HTTPException) as exc:  # IncompleteRead n'est pas une OSError
        return _ecrire(sortie, IMPOSSIBLE, entete + [str(exc)])
    finally:
        for service in garde: _arreter(service)
    code, lignes = juger(lu, reglages, siege)
    return _ecrire(sortie, code, entete + lignes)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
