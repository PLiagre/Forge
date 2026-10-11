"""Prouve les gestes HTTP par leur rejeu CLI exact et la conservation des foyers."""
import argparse, json, subprocess, sys, threading
import hashlib, math, os, time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
JEU = Path(__file__).resolve().parents[1] / "jeu"
if str(JEU) not in sys.path: sys.path.insert(0, str(JEU))
from sim import constants as constantes, service, ville1400
from sim.seigneuries import cellule_du_siege, charger_seigneuries, identifiant_de_seigneurie
from sim.world import World
MONDES = ("monde-service.json", "monde-rejoue.json", "monde-sans-gestes.json")
CONSTRUCTIONS = {"tracer_route", "decouper_parcelle", "poser_batiment"}
ADRESSE = (service.SERVICE_HOST, service.DEFAULT_SERVICE_PORT)
DELAI_HTTP, DELAI_CLI, DELAI_ARRET = 10, 60, 5
DELAI_UNITY, MARGE_RAPPORT = 900, 2
# La recette Unity : graine et ticks ; sa cellule est celle de Biskra, lue dans la table. Choix au tick 0,
# gestes aux ticks 1, 2 et 3, scierie appliquée au tick 4, sept ticks de plus.
TICKS_PYTHON, GRAINE_UNITY, TICKS_UNITY = 10, 0, 11
CHRONOLOGIE_UNITY = (0, 1, 2, 3)
# La route qui traverse une maison de 1400 : un segment droit par le centre de l'emprise, un cap tous les 15°.
LONGUEUR_SUR_MAISON, CAPS_SUR_MAISON, MARGE_RELIEF = 40.0, range(0, 180, 15), .02
STATUTS = ("égalité du monde", "relancement", "sans geste", "foyers", "gestes")

def serialiser(document):
    return json.dumps(document, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode("utf-8")

def exiger(condition, message):
    if not condition: raise ValueError(message)

def controler_foyers(monde):
    """Désagrège les foyers sans appeler le rangement qui les a produits."""
    for cid, cellule in monde["cells"].items():
        erreur = f"foyers cellule {cid} : conservation des personnes"
        metiers, population = cellule.get("foyers"), cellule.get("population")
        exiger(type(population) is int and population >= 0 and isinstance(metiers, dict), erreur)
        personnes = desagregees = 0
        for nom, foyer in metiers.items():
            exiger(isinstance(nom, str) and bool(nom.strip()) and isinstance(foyer, dict), erreur)
            n, complets, dernier = (foyer.get(champ) for champ in ("personnes", "complets", "dernier"))
            exiger(all(type(v) is int for v in (n, complets, dernier)), erreur + f", métier {nom}")
            exiger(n > 0 and complets >= 0 and 0 <= dernier < constantes.TAILLE_FOYER, erreur)
            total = complets * constantes.TAILLE_FOYER + dernier
            exiger(total == n, erreur + f", métier {nom}")
            personnes += n
            desagregees += total
        exiger(personnes == desagregees == population, erreur)

def depart_biskra():
    """Terre, maison du registre et cellule du siège nommé Biskra, lues dans les tables."""
    if depart_biskra.memo is not None: return depart_biskra.memo
    monde = World.charger(0)
    zab = next((s for s in charger_seigneuries() if s.siege.nom == "Biskra"), None)
    if zab is None: raise ValueError("siège absent : Biskra")
    depart_biskra.memo = (zab.id, identifiant_de_seigneurie(zab.id), cellule_du_siege(zab, monde.carte))
    return depart_biskra.memo
depart_biskra.memo = None

def juger(servi, rejoue, temoin, journal, ticks, chronologie=(0, 2, 3, 5)):
    exiger(isinstance(journal, list) and bool(journal), "journal vide ou invalide")
    types = {entree["intention"]["type"] for entree in journal}
    exiger(types == CONSTRUCTIONS | {"choisir_depart"}, "journal : type absent ou inattendu")
    numeros = [entree["tick"] for entree in journal]
    exiger(numeros == list(chronologie) and all(type(n) is int and 0 <= n < ticks for n in numeros),
           "journal : ticks invalides")
    attendu, maison, cellule = depart_biskra()
    choix = [entree for entree in journal if entree["intention"]["type"] == "choisir_depart"]
    seigneurie = choix[0]["intention"].get("seigneurie") if len(choix) == 1 else None
    gestes = [entree for entree in journal if entree not in choix]
    exiger(len(choix) == 1 and choix[0]["tick"] == 0 and type(seigneurie) is int and seigneurie == attendu
           and len(gestes) == len(CONSTRUCTIONS) and all(entree["intention"].get("cell") == cellule for entree in gestes),
           "journal : faux choix")
    mondes = [json.loads(octets) for octets in (servi, rejoue, temoin)]
    for monde in mondes:
        exiger(isinstance(monde, dict) and bool(monde.get("cells")) and bool(monde.get("plans")), "monde vide")
        exiger(isinstance(monde["cells"], dict) and isinstance(monde["plans"], dict), "monde : collections invalides")
        exiger(monde.get("ticks_ecoules") == ticks, "monde : ticks écoulés différents")
        exiger(set(monde["cells"]) == set(monde["plans"]) == set(mondes[0]["cells"]), "monde : cellules et plans différents")
        exiger(all(str(c["cell_id"]) == cid for cid, c in monde["cells"].items()), "monde : cell_id différent")
        controler_foyers(monde)
    for rang, monde in enumerate(mondes):
        tenue = monde.get("maison_du_joueur")
        exiger(tenue is not None, ("maison absente", "maison absente", "témoin sans départ")[rang])
        exiger(tenue == maison, ("départ différent", "départ différent", "témoin : autre départ")[rang])
    exiger(servi == rejoue, "octets : écart entre monde servi et monde rejoué")
    exiger(rejoue != temoin, "témoin : aucun effet des gestes")
    bilan = {"cellules_controlees": len(mondes[0]["cells"]), "gestes_acceptes": len(journal)}
    for collection, nom in (("cells", "cellules_modifiees"), ("plans", "plans_modifies")):
        bilan[nom] = [cid for cid, valeur in mondes[1][collection].items() if valeur != mondes[2][collection][cid]]
    exiger(bilan["cellules_modifiees"] and bilan["plans_modifies"], "échantillon vide")
    return bilan

def http(chemin, document=None):
    requete = Request(f"http://{ADRESSE[0]}:{ADRESSE[1]}{chemin}",
                      data=None if document is None else serialiser(document),
                      headers={"Content-Type": "application/json"})
    with urlopen(requete, timeout=DELAI_HTTP) as reponse: return reponse.read()

def choisir(seigneurie):
    """Le choix du départ par HTTP : reçu au tick 0, appliqué au tick 1, maison de Biskra tenue."""
    recu = json.loads(http("/intention", {"type": "choisir_depart", "seigneurie": seigneurie}))
    exiger(recu == {"acceptee": True, "appliquee_au_tick": 0}, "reçu : départ non accepté au tick 0")
    exiger(json.loads(http("/tick?n=1", {}))["tick"] == 1, "horloge : tick inattendu")
    exiger(json.loads(http("/monde")).get("maison_du_joueur") == depart_biskra()[1], "départ non appliqué")

@contextmanager
def lancer_service(sortie, seed, sourd, depart=None):
    class Serveur(service.ServeurMonde):
        def server_close(self):
            # Une liaison refusée ferme la socket avant que l'horloge existe.
            if hasattr(self, "condition_vitesse"): super().server_close()
            else: service.ThreadingHTTPServer.server_close(self)
    try: serveur = Serveur(ADRESSE, seed, 0, ia=False)
    except OSError as exc: raise OSError(f"port {ADRESSE[0]}:{ADRESSE[1]} indisponible : {exc}") from exc
    journal, original = [], service.recevoir_intention
    class Requetes(service.RequetesMonde):
        def do_GET(self):
            if self.path != "/monde-complet": return super().do_GET()
            with self.server.verrou_tick: corps = serialiser(self.server.world.to_dict())
            self._repondre_octets(200, corps)
    def recevoir(monde, intention):
        pose = original(monde, intention)
        if monde is serveur.world:
            # Le handler existant tient déjà verrou_tick ; un refus n'atteint pas ce point.
            journal.append({"tick": monde.ticks_ecoules, "intention": json.loads(serialiser(intention))})
            (sortie / "journal.json").write_bytes(serialiser(journal))
            if sourd and intention["type"] == "poser_batiment": monde.intentions_en_attente.remove(pose)
        return pose
    serveur.RequestHandlerClass = Requetes
    fil = threading.Thread(target=serveur.serve_forever, daemon=True)
    fil.start()
    try:
        (sortie / "journal.json").write_bytes(serialiser(journal))
        service.recevoir_intention = recevoir
        # Le journal porte alors le choix au tick 0 ; le monde est au tick 1.
        if depart is not None: choisir(depart)
        yield serveur
    finally:
        try:
            try: serveur.shutdown()
            finally:
                try: serveur.server_close()
                finally:
                    fil.join(DELAI_ARRET)
                    serveur._fil_horloge.join(DELAI_ARRET)
            if fil.is_alive() or serveur._fil_horloge.is_alive(): raise OSError("arrêt du service inachevé")
        finally: service.recevoir_intention = original

def recette(cellule):
    return [(2, "rues", dict(type="tracer_route", cell=cellule, points=[[0, 0], [40, 0]], largeur_m=4)),
            (3, "parcelles", dict(type="decouper_parcelle", cell=cellule, rue=0, segment=0,
                                  debut_m=5, facade_m=10, profondeur_m=20, cote="gauche")),
            (5, "batiments", dict(type="poser_batiment", cell=cellule, parcelle=0, nature="maison"))]

def rejouer(sortie, ticks, seed):
    """Le rejeu complet reprend tout le journal ; le témoin, le choix seul, comme le parcours Python."""
    journal = json.loads((sortie / "journal.json").read_bytes())
    (sortie / "journal-temoin.json").write_bytes(serialiser([e for e in journal if e["intention"]["type"] == "choisir_depart"]))
    for nom, gestes in ((MONDES[1], "journal.json"), (MONDES[2], "journal-temoin.json")):
        cmd = [sys.executable, "-m", "sim", "--ticks", str(ticks), "--seed", str(seed), "--monde-json", str(sortie / nom), "--gestes", str(sortie / gestes)]
        fait = subprocess.run(cmd, cwd=JEU, capture_output=True, timeout=DELAI_CLI)
        if fait.returncode: raise OSError("rejeu CLI refusé : " + fait.stderr.decode("utf-8", errors="replace"))
def module_routes():
    """Le module des routes du désert (numpy) : chargé seulement quand une route se cherche."""
    racine = Path(__file__).resolve().parents[1] / "3d"
    if str(racine) not in sys.path: sys.path.insert(0, str(racine))
    from local3d.desert import routes
    return routes
def route_sur_une_maison(base, h, largeur, P):
    """Maison par maison, un segment droit par le centre de l'emprise : les premiers points que la garde
    des maisons de 1400 touche et que le relief accepte, ou None."""
    import numpy as np
    routes = module_routes(); k = round(1 / P["arrondi"]); arrondi = lambda v: round(v * k) / k; demi = LONGUEUR_SUR_MAISON / 2
    for maison in base["maisons"]:
        cx, cy = (sum(p[i] for p in maison["emprise"]) / len(maison["emprise"]) for i in (0, 1))
        for cap in CAPS_SUR_MAISON:
            ux, uy = math.cos(math.radians(cap)), math.sin(math.radians(cap))
            points = [[arrondi(cx + t * ux), arrondi(cy + t * uy)] for t in (-demi, 0, demi)]
            if ville1400.maison_touchee(base, [ville1400.emprise_de_rue(s, largeur) for s in zip(points, points[1:])]) is None: continue
            r = routes.essai(h, np.asarray(points, dtype=float), largeur, P)
            if r["decision"] == "acceptee" and routes.marge(r) > MARGE_RELIEF: return points
    return None
def ecrire_route(dossier, points, largeur):
    """Ajoute la route à la consigne écrite par preparer_sessions : la session jouer la clique au lieu de la plaine."""
    chemin = dossier / "consigne.json"; consigne = json.loads(chemin.read_text(encoding="utf-8"))
    consigne["route"] = {"x": [p[0] for p in points], "y": [p[1] for p in points], "largeur": largeur}
    chemin.write_text(json.dumps(consigne), encoding="utf-8")
def poser_route_sur_une_maison(aides, dossier, cellule):
    """--sur-une-maison : la base servie de Biskra, la largeur et les paramètres de la route plaine du jeu de gestes."""
    base = json.loads(http(f"/plan?cell={cellule}"))["base"]; ident = aides["disposition"]["id"]
    gestes = json.loads((aides["sorties"] / ident / "routes" / "gestes.json").read_text(encoding="utf-8"))
    plaine = next(g for g in gestes["routes"] if g["famille"] == "plaine")
    points = route_sur_une_maison(base, aides["grille"](ident), plaine["largeur"], gestes["parametres"])
    if points is None: raise OSError("aucune route sur une maison que le relief accepte")
    ecrire_route(dossier, points, plaine["largeur"])
def charger_aides():
    """Les aides 3D ne se chargent que pour --avec-unity : les tests HTTP n'en dépendent pas."""
    racine = Path(__file__).resolve().parents[1] / "3d"
    if str(racine) not in sys.path: sys.path.insert(0, str(racine))
    from local3d.atelier_alpin import UNITY; from local3d.atelier_citadelle import prepare_terrain_sample
    from local3d.atelier_desert import PREUVE, RECIPE; from local3d.desert import terrain; from local3d.desert.routes import ecrire_gestes, grille
    return {"unity": UNITY, "preuve": dict(PREUVE), "disposition": RECIPE["dispositions"][0], "ecrire": ecrire_gestes, "sorties": terrain.SORTIES, "projet": racine / "unity", "terrain": prepare_terrain_sample, "grille": grille}
def version_unity(projet):
    try: return next((l.split(":", 1)[1].strip() for l in (projet / "ProjectSettings" / "ProjectVersion.txt").read_text(encoding="utf-8").splitlines() if l.startswith("m_EditorVersion:")), "inconnue")
    except OSError: return "inconnue"
def revision_eprouvee():
    git = lambda *a: subprocess.run(("git", *a), cwd=JEU.parent, capture_output=True, text=True, timeout=DELAI_HTTP)
    tete, blob, commis = git("rev-parse", "HEAD"), git("hash-object", "--", "pc/epreuve_jalon4.py"), git("rev-parse", "HEAD:pc/epreuve_jalon4.py")
    base = tete.stdout.strip() if tete.returncode == 0 and tete.stdout.strip() else "inconnue"
    return base if blob.returncode or commis.returncode or blob.stdout.strip() == commis.stdout.strip() else base + " " + blob.stdout.strip()
def port_occupe():
    import socket; prise = socket.socket(); prise.settimeout(1); occupe = prise.connect_ex(ADRESSE) == 0; prise.close(); return occupe
def verifier_prealables(aides):
    if not Path(aides["unity"]).is_file(): raise OSError(f"Unity introuvable : {aides['unity']}")
    ident, projet = aides["disposition"]["id"], aides["projet"]; scene = projet / f"Assets/ForgeLocal3D/Desert/Scenes/Forge_Desert_Ville_{ident}.unity"
    if not scene.is_file(): raise OSError("scène absente")
    manquantes = [n for n in ("terrain.json", "hauteurs.f32") if not (aides["sorties"] / ident / n).is_file()]
    if manquantes: raise OSError("données locales absentes (" + ", ".join(manquantes) + ") : lancer py local3d/atelier_desert.py terrain")
    if (projet / "Temp" / "UnityLockfile").exists(): raise OSError("Unity est ouvert : fermer l'éditeur")
def preparer_sessions(aides, ville_locale):
    ident = aides["disposition"]["id"]; aides["ecrire"](ident, aides["disposition"]["seed"]); dossier = aides["sorties"] / ident / "preuve"
    (aides["sorties"] / "selection.json").write_text(json.dumps({"implantations": [ident]}), encoding="utf-8"); dossier.mkdir(parents=True, exist_ok=True)
    for chemin in dossier.glob("*.json"): chemin.unlink()
    (dossier / "consigne.json").write_text(json.dumps({"ville_locale": bool(ville_locale)}), encoding="utf-8"); return dossier
def appeler_unity(aides, nom, sortie, cellule):
    log = sortie / "logs" / f"{nom}.log"; log.parent.mkdir(parents=True, exist_ok=True)
    try: aides["terrain"]()
    except RuntimeError as exc: raise OSError(str(exc)) from exc
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    proc = subprocess.Popen([str(aides["unity"]), "-batchmode", "-projectPath", str(aides["projet"]), "-executeMethod", aides["preuve"][nom], "-logFile", str(log), "-forgeCell", str(cellule)], cwd=str(aides["projet"].parent), creationflags=flags)
    try: return proc.wait(timeout=DELAI_UNITY)
    except subprocess.TimeoutExpired:
        (subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, timeout=30) if os.name == "nt" else proc.kill())
        proc.wait(timeout=30); raise OSError(f"délai Unity dépassé ({DELAI_UNITY} s)")
def lire_defauts(nom, rapport):
    brut = rapport.get("defauts") if isinstance(rapport, dict) else None
    exiger(isinstance(brut, list) and all(type(d) is str for d in brut), f"{nom} : défauts absents"); return brut
def lire_session(dossier, nom, debut, code):
    chemin = dossier / f"{nom}.json"
    if not chemin.is_file(): raise OSError(("session en erreur : " if code not in (0, 1) else "rapport absent : ") + nom)
    if chemin.stat().st_mtime + MARGE_RAPPORT < debut: raise OSError("rapport ancien : " + nom)
    if code not in (0, 1): raise OSError(f"session en erreur : {nom}, Unity a rendu {code}")
    rapport = json.loads(chemin.read_text(encoding="utf-8-sig")); pannes = [d for d in lire_defauts(nom, rapport) if "exception :" in d]
    if pannes: raise OSError(" ; ".join(pannes))
    return rapport
def juger_recus(journal, gestes):
    # Unity ne dépose que les constructions : le choix du départ est celui du script.
    journal = [e for e in journal if e.get("intention", {}).get("type") in CONSTRUCTIONS]
    pareil =isinstance(gestes, list) and len(gestes) == len(journal) and all(e.get("tick") == g.get("apres_le_tick") and e.get("intention", {}).get("type") == g.get("type") for e, g in zip(journal, gestes))
    exiger(pareil, "reçu Unity différent du journal")
def juger_monde_relance(avant, apres, journal_avant, journal_apres):
    exiger(avant == apres, "monde changé pendant la relance"); exiger(journal_avant == journal_apres, "journal changé pendant la relance")
def fautes_dessin(jouer, relance, vierge, ticks):
    j, r, v = jouer["ville"], relance["ville"], vierge["ville"]; bat, vide = j["batiments_plan"], hashlib.sha256(b"").hexdigest()
    gardes = [(not (j["tick"] == ticks and len(j["rues"]) == 1 and j["rues"] == j["rues_posees"]), "jouer : une rue au tick de la recette"), (not (len(j["parcelles_plan"]) == 1 and j["parcelles_plan"][0]["etat"] == "bornes"), "jouer : parcelle aux bornes"),
              (not (len(bat) == 1 and bat[0]["nature"] == "scierie" and bat[0]["etat"] == "piquets"), "bâtiment absent"), (j["pieces_parcelles"] != 1 or j["pieces_batiments"] != 1, "jouer : une pièce de chaque type")]
    fautes = [message for garde, message in gardes if garde]; locale = jouer.get("ville_locale") or relance.get("ville_locale")
    for nom in ("rues", "rues_posees", "parcelles", "batiments", "pieces_parcelles", "pieces_batiments", "empreinte_rues", "empreinte_parcelles", "empreinte_batiments"):
        if j.get(nom) == r.get(nom): continue
        message = "empreinte de relance différente : empreinte des rues" if nom == "empreinte_rues" else f"empreinte de relance différente : {nom}" if nom.startswith("empreinte") else f"relance : {nom}"
        fautes.append(message + (" ; c'est le redessin qui échoue ; l'égalité Python peut rester vraie" if nom == "empreinte_rues" and locale else ""))
    if v["tick"] != 0 or v["rues"] or v["parcelles_plan"] or v["batiments_plan"]: fautes.append("vierge : le plan n'est pas vide")
    if v["pieces_parcelles"] != 0 or v["pieces_batiments"] != 0: fautes.append("pièce dans le rapport vierge")
    if v["empreinte_rues"] != vierge["vierge"]: fautes.append("vierge : empreinte des rues différente du terrain vierge")
    if v["empreinte_parcelles"] != vide or v["empreinte_batiments"] != vide: fautes.append("vierge : dessin non vide")
    return fautes
def juger_dessin(jouer, relance, vierge, ticks):
    fautes = fautes_dessin(jouer, relance, vierge, ticks); exiger(not fautes, " ; ".join(fautes))
def poser(statuts, nom, fautes, tenu): statuts[nom] = ["violé", " ; ".join(fautes)] if fautes else ["tenu", tenu]
def plan_vide(monde): return all(not plan.get(cle) for plan in monde["plans"].values() for cle in ("rues", "parcelles", "batiments"))
def juger_essai(args, sortie, statuts, ident, rapports, avant, apres, journal_avant, journal_apres):
    jouer, relance, vierge = (rapports[n] for n in ("jouer", "relance", "vierge")); relance_fautes, vierge_fautes, pannes = [], [], []
    for nom, rapport in rapports.items():
        if (rapport.get("session"), rapport.get("cell"), rapport.get("port")) != (nom, args.cellule, ADRESSE[1]): relance_fautes.append(f"{nom} : session, cellule ou port inattendus")
        if rapport.get("implantation") != ident: relance_fautes.append(f"{nom} : implantation {rapport.get('implantation')}")
        brut = lire_defauts(nom, rapport); pannes += [d for d in brut if "exception :" in d]
        if brut and not any("exception :" in d for d in brut): (vierge_fautes if nom == "vierge" else relance_fautes).append(f"{nom} : {len(brut)} défaut(s) : " + " ; ".join(brut))
    if pannes: [statuts.__setitem__(cle, ["non exécuté", " ; ".join(pannes)]) for cle in STATUTS]; return 2
    try: juger_monde_relance(avant, apres, journal_avant, journal_apres)
    except ValueError as exc: relance_fautes.append(str(exc))
    ticks = json.loads(apres)["ticks_ecoules"]; exiger(type(ticks) is int and ticks >= 1, "monde : ticks écoulés absents"); horloge = []
    if not args.service_sourd and ticks != args.ticks: horloge.append(f"le normal exige {args.ticks} ticks")
    if jouer["ville"].get("tick") != ticks or relance["ville"].get("tick") != ticks: horloge.append("tick des rapports différent du monde servi")
    if horloge and not args.service_sourd: relance_fautes.extend(horloge); poser(statuts, "relancement", relance_fautes, ""); return 1
    relance_fautes.extend(horloge)
    for faute in fautes_dessin(jouer, relance, vierge, args.ticks): (vierge_fautes if faute.startswith(("vierge", "pièce")) else relance_fautes).append(faute)
    poser(statuts, "relancement", relance_fautes, "mêmes identifiants, états, pièces et empreintes")
    if vierge_fautes: poser(statuts, "sans geste", vierge_fautes, "")
    try: journal, recus = json.loads((sortie / "journal.json").read_bytes()), jouer.get("gestes") or []; juger_recus(journal, recus); exiger([g.get("apres_le_tick") for g in recus] == list(CHRONOLOGIE_UNITY[1:]), "gestes : ticks attendus 1, 2 et 3"); statuts["gestes"] = ["tenu", "journal identique aux reçus, ticks 1, 2 et 3"]
    except (ValueError, KeyError, TypeError) as exc: statuts["gestes"] = ["violé", str(exc)]
    rejouer(sortie, ticks, args.seed); octets = [(sortie / nom).read_bytes() for nom in MONDES]; mondes = [json.loads(d) for d in octets]
    try: [controler_foyers(monde) for monde in mondes]; statuts["foyers"] = ["tenu", f"{len(mondes[0]['cells'])} cellules, personnes conservées"]
    except (ValueError, KeyError, TypeError) as exc: statuts["foyers"] = ["violé", str(exc)]
    if octets[0] == octets[1] != octets[2]: statuts["égalité du monde"] = ["tenu", f"octets égaux sur {ticks} ticks"]
    elif octets[0] != octets[1]: statuts["égalité du monde"] = ["violé", "écart entre monde servi et monde rejoué"]
    else: statuts["égalité du monde"] = ["violé", "témoin : aucun effet des gestes"]
    try: bilan = juger(*octets, json.loads((sortie / "journal.json").read_bytes()), ticks, CHRONOLOGIE_UNITY); statuts.__setitem__("égalité du monde", ["violé", "échantillon vide"]) if not bilan["cellules_modifiees"] or not bilan["plans_modifies"] else None
    except (ValueError, KeyError, TypeError) as exc: bilan = None; statuts.update({"égalité du monde": ["violé", str(exc)]}) if statuts["égalité du monde"][0] == "tenu" else None
    if not plan_vide(mondes[2]) or mondes[2].get("ticks_ecoules") != ticks: vierge_fautes.append("témoin : le plan n'est pas vide au tick servi")
    if vierge_fautes: poser(statuts, "sans geste", vierge_fautes, "")
    elif statuts["sans geste"][0] != "violé": statuts["sans geste"] = ["tenu", f"plan vide au tick 0, témoin sans geste au tick {ticks}"]
    if any(e[0] == "violé" for e in statuts.values()): return 1
    if any(e[0] != "tenu" for e in statuts.values()): return 2
    (sortie / "bilan.json").write_bytes(serialiser(bilan)); return 0
def ecrire_verdict(sortie, args, code, statuts, version, revision, motif):
    drapeau = (" --service-sourd" if args.service_sourd else "") + (" --ville-locale" if args.ville_locale else "") + (" --sur-une-maison" if args.sur_une_maison else "")
    lignes = [("preuve valide", "invariant violé", "essai impossible")[code], "commande : py pc/epreuve_jalon4.py --avec-unity --sortie " + str(args.sortie) + drapeau, "date : " + datetime.now().astimezone().isoformat(timespec="seconds"), "révision : " + revision, "unity : " + version, f"code : {code}"]
    lignes += [f"{nom} : {statuts[nom][0]} — {statuts[nom][1]}" for nom in STATUTS]
    if motif: lignes.append("motif : " + motif)
    texte = "\n".join(lignes) + "\n"; (sortie / "verdict.txt").write_text(texte, encoding="utf-8"); print(texte, end="")
def epreuve_unity(args):
    sortie = args.sortie.resolve(); sortie.mkdir(parents=True, exist_ok=True); statuts = {nom: ["non exécuté", "contrôle non exécuté"] for nom in STATUTS}
    version, revision, motif, code = "inconnue", revision_eprouvee(), "", 2
    try:
        # La recette lit la table : la cellule est celle du siège de Biskra, le départ l'émirat du Zab.
        seigneurie, _, biskra = depart_biskra()
        if args.ticks is None: args.ticks = TICKS_UNITY
        if args.cellule is None: args.cellule = biskra
        if (args.seed, args.ticks, args.cellule) != (GRAINE_UNITY, TICKS_UNITY, biskra): raise OSError("la recette Unity fixe la graine 0, la cellule de Biskra et 11 ticks")
        aides = charger_aides(); version = version_unity(aides["projet"]); verifier_prealables(aides)
        if port_occupe(): raise OSError(f"port {ADRESSE[0]}:{ADRESSE[1]} indisponible")
        for nom in (*MONDES, "journal.json", "journal-temoin.json", "bilan.json", "verdict.txt", "jouer.json", "relance.json", "vierge.json"): (sortie / nom).unlink(missing_ok=True)
        dossier, debut = preparer_sessions(aides, args.ville_locale), time.time()
        with lancer_service(sortie, args.seed, args.service_sourd, seigneurie):
            if args.sur_une_maison: poser_route_sur_une_maison(aides, dossier, args.cellule)
            jouer = lire_session(dossier, "jouer", debut, appeler_unity(aides, "jouer", sortie, args.cellule)); avant, journal_avant = http("/monde-complet"), (sortie / "journal.json").read_bytes()
            relance = lire_session(dossier, "relance", debut, appeler_unity(aides, "relance", sortie, args.cellule)); apres, journal_apres = http("/monde-complet"), (sortie / "journal.json").read_bytes(); (sortie / MONDES[0]).write_bytes(apres)
        (sortie / "service-vierge").mkdir(parents=True, exist_ok=True)
        with lancer_service(sortie / "service-vierge", args.seed, False): vierge = lire_session(dossier, "vierge", debut, appeler_unity(aides, "vierge", sortie, args.cellule))
        for nom in ("jouer", "relance", "vierge"): (sortie / f"{nom}.json").write_bytes((dossier / f"{nom}.json").read_bytes())
        code = juger_essai(args, sortie, statuts, aides["disposition"]["id"], {"jouer": jouer, "relance": relance, "vierge": vierge}, avant, apres, journal_avant, journal_apres)
        if code: motif = " ; ".join(f"{nom} — {etat[1]}" for nom, etat in statuts.items() if etat[0] == ("violé" if code == 1 else "non exécuté"))
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc: code, motif = 2, str(exc)
    except (ValueError, KeyError, TypeError) as exc: code, motif = 1, str(exc)
    ecrire_verdict(sortie, args, code, statuts, version, revision, motif)
    if code: print(("Invariant violé : " if code == 1 else "Essai impossible : ") + motif, file=sys.stderr)
    return code

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sortie", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=0)
    # Sans valeur donnée, chaque parcours résout les siennes : 10 ticks en Python, 11 et Biskra avec Unity.
    parser.add_argument("--ticks", type=int, default=None)
    parser.add_argument("--cellule", type=int, default=None)
    parser.add_argument("--service-sourd", action="store_true")
    parser.add_argument("--avec-unity", action="store_true"); parser.add_argument("--ville-locale", action="store_true")
    parser.add_argument("--sur-une-maison", action="store_true")
    args = parser.parse_args(argv)
    for drapeau in ("ville_locale", "sur_une_maison"):
        if getattr(args, drapeau) and not args.avec_unity:
            print(f"Essai impossible : --{drapeau.replace('_', '-')} n'est admis qu'avec --avec-unity", file=sys.stderr); return 2
    if args.avec_unity: return epreuve_unity(args)
    if args.ticks is None: args.ticks = TICKS_PYTHON
    sortie = args.sortie.resolve()
    try:
        sortie.mkdir(parents=True, exist_ok=True)
        for nom in (*MONDES, "journal.json", "journal-temoin.json", "bilan.json"): (sortie / nom).unlink(missing_ok=True)
        if args.ticks <= 5: raise OSError("la recette exige au moins 6 ticks")
        if port_occupe(): raise OSError(f"port {ADRESSE[0]}:{ADRESSE[1]} indisponible")
        # Le parcours Python bâtit au siège de Biskra, comme la recette Unity.
        seigneurie, maison, cellule = depart_biskra()
        with lancer_service(sortie, args.seed, args.service_sourd):
            ecoules = 0
            chemin = f"/plan?cell={cellule}"
            avant = json.loads(http(chemin))
            recu = json.loads(http("/intention", {"type": "choisir_depart", "seigneurie": seigneurie}))
            exiger(recu == {"acceptee": True, "appliquee_au_tick": 0}, "reçu : départ non accepté au tick 0")
            exiger(json.loads(http(chemin)) == avant, "plan : changement avant le tick suivant")
            apres_tick = json.loads(http("/tick?n=1", {}))
            ecoules = 1
            exiger(apres_tick["tick"] == ecoules, "horloge : tick inattendu")
            exiger(json.loads(http("/monde")).get("maison_du_joueur") == maison, "départ non appliqué")
            for numero, collection, intention in recette(cellule):
                if numero > ecoules: http(f"/tick?n={numero - ecoules}", {})
                avant = json.loads(http(chemin))
                recu = json.loads(http("/intention", intention))
                exiger(recu == {"acceptee": True, "appliquee_au_tick": numero}, "reçu : dépôt non accepté au tick attendu")
                exiger(json.loads(http(chemin)) == avant, "plan : changement avant le tick suivant")
                apres_tick = json.loads(http("/tick?n=1", {}))
                ecoules = numero + 1
                exiger(apres_tick["tick"] == ecoules, "horloge : tick inattendu")
                apres = json.loads(http(chemin))
                attendu = len(avant[collection]) + (0 if args.service_sourd and collection == "batiments" else 1)
                exiger(len(apres[collection]) == attendu, f"plan : {collection} absents après application")
            if args.ticks > ecoules: http(f"/tick?n={args.ticks - ecoules}", {})
            (sortie / MONDES[0]).write_bytes(http("/monde-complet"))
        journal = json.loads((sortie / "journal.json").read_bytes())
        choix = [entree for entree in journal if entree["intention"]["type"] == "choisir_depart"]
        (sortie / "journal-temoin.json").write_bytes(serialiser(choix))
        for nom, gestes in ((MONDES[1], "journal.json"), (MONDES[2], "journal-temoin.json")):
            commande = [sys.executable, "-m", "sim", "--ticks", str(args.ticks), "--seed", str(args.seed),
                        "--monde-json", str(sortie / nom), "--gestes", str(sortie / gestes)]
            fait = subprocess.run(commande, cwd=JEU, capture_output=True, timeout=DELAI_CLI)
            if fait.returncode: raise OSError(f"rejeu CLI refusé : {fait.stderr.decode('utf-8', errors='replace')}")
        bilan = juger(*(sortie.joinpath(nom).read_bytes() for nom in MONDES),
                      json.loads((sortie / "journal.json").read_bytes()), args.ticks)
        (sortie / "bilan.json").write_bytes(serialiser(bilan))
        print("Preuve valide : " + serialiser(bilan).decode("utf-8"))
        return 0
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"Essai impossible : {exc}", file=sys.stderr)
        return 2
    except (ValueError, KeyError, TypeError) as exc:
        print(f"Invariant violé : {exc}", file=sys.stderr)
        return 1
if __name__ == "__main__": sys.exit(main())
