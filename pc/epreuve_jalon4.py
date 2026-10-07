"""Prouve les gestes par leur rejeu CLI exact et, avec Unity, par le redessin de la ville."""
import argparse, hashlib, json, os, subprocess, sys, threading, time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
JEU = Path(__file__).resolve().parents[1] / "jeu"
if str(JEU) not in sys.path: sys.path.insert(0, str(JEU))
from sim import constants as constantes, service
MONDES = ("monde-service.json", "monde-rejoue.json", "monde-sans-gestes.json")
ADRESSE = (service.SERVICE_HOST, service.DEFAULT_SERVICE_PORT)
DELAI_HTTP, DELAI_CLI, DELAI_ARRET, DELAI_UNITY = 10, 60, 5, 900
RECETTE_UNITY = (0, 10, 1175)
STATUTS = ("égalité du monde", "relancement", "sans geste", "foyers", "gestes")
MARGE_RAPPORT = 2

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

def juger(servi, rejoue, temoin, journal, ticks):
    exiger(isinstance(journal, list) and bool(journal), "journal vide ou invalide")
    types = {entree["intention"]["type"] for entree in journal}
    exiger(types == {"tracer_route", "decouper_parcelle", "poser_batiment"}, "journal : type absent ou inattendu")
    numeros = [entree["tick"] for entree in journal]
    exiger(all(type(n) is int and 0 <= n < ticks for n in numeros) and numeros == sorted(numeros),
           "journal : ticks invalides")
    mondes = [json.loads(octets) for octets in (servi, rejoue, temoin)]
    for monde in mondes:
        exiger(isinstance(monde, dict) and bool(monde.get("cells")) and bool(monde.get("plans")), "monde vide")
        exiger(isinstance(monde["cells"], dict) and isinstance(monde["plans"], dict), "monde : collections invalides")
        exiger(monde.get("ticks_ecoules") == ticks, "monde : ticks écoulés différents")
        exiger(set(monde["cells"]) == set(monde["plans"]) == set(mondes[0]["cells"]), "monde : cellules et plans différents")
        exiger(all(str(c["cell_id"]) == cid for cid, c in monde["cells"].items()), "monde : cell_id différent")
        controler_foyers(monde)
    exiger(servi == rejoue, "octets : écart entre monde servi et monde rejoué")
    exiger(rejoue != temoin, "témoin : aucun effet des gestes")
    bilan = {"cellules_controlees": len(mondes[0]["cells"]), "gestes_acceptes": len(journal)}
    for collection, nom in (("cells", "cellules_modifiees"), ("plans", "plans_modifies")):
        bilan[nom] = [cid for cid, valeur in mondes[1][collection].items() if valeur != mondes[2][collection][cid]]
    return bilan

def http(chemin, document=None):
    requete = Request(f"http://{ADRESSE[0]}:{ADRESSE[1]}{chemin}",
                      data=None if document is None else serialiser(document),
                      headers={"Content-Type": "application/json"})
    with urlopen(requete, timeout=DELAI_HTTP) as reponse: return reponse.read()

@contextmanager
def lancer_service(sortie, seed, sourd):
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
    for nom, gestes in ((MONDES[1], True), (MONDES[2], False)):
        commande = [sys.executable, "-m", "sim", "--ticks", str(ticks), "--seed", str(seed),
                    "--monde-json", str(sortie / nom)]
        if gestes: commande += ["--gestes", str(sortie / "journal.json")]
        fait = subprocess.run(commande, cwd=JEU, capture_output=True, timeout=DELAI_CLI)
        if fait.returncode: raise OSError(f"rejeu CLI refusé : {fait.stderr.decode('utf-8', errors='replace')}")

def charger_aides():
    """Les aides 3D ne se chargent que pour --avec-unity : les tests HTTP n'en dépendent pas."""
    trois_d = Path(__file__).resolve().parents[1] / "3d"
    if str(trois_d) not in sys.path: sys.path.insert(0, str(trois_d))
    from local3d.atelier_alpin import UNITY
    from local3d.atelier_citadelle import prepare_terrain_sample
    from local3d.atelier_desert import PREUVE, RECIPE
    from local3d.desert import terrain
    from local3d.desert.routes import ecrire_gestes
    return {"unity": UNITY, "preuve": PREUVE, "disposition": RECIPE["dispositions"][0],
            "ecrire": ecrire_gestes, "sorties": terrain.SORTIES, "projet": trois_d / "unity",
            "terrain": prepare_terrain_sample}

def version_unity(projet):
    try: lignes = (projet / "ProjectSettings" / "ProjectVersion.txt").read_text(encoding="utf-8").splitlines()
    except OSError: return "inconnue"
    for ligne in lignes:
        if ligne.startswith("m_EditorVersion:"): return ligne.split(":", 1)[1].strip()
    return "inconnue"

def revision_eprouvee():
    fait = subprocess.run(["git", "rev-parse", "HEAD"], cwd=JEU.parent, capture_output=True, text=True, timeout=DELAI_HTTP)
    return fait.stdout.strip() if fait.returncode == 0 and fait.stdout.strip() else "inconnue"

def port_occupe():
    import socket
    with socket.socket() as prise:
        prise.settimeout(1)
        return prise.connect_ex(ADRESSE) == 0

def verifier_prealables(aides):
    if not Path(aides["unity"]).is_file(): raise OSError(f"Unity introuvable : {aides['unity']}")
    ident = aides["disposition"]["id"]
    scene = aides["projet"] / "Assets/ForgeLocal3D/Desert/Scenes" / f"Forge_Desert_Ville_{ident}.unity"
    if not scene.is_file(): raise OSError(f"scène absente : {scene}")
    donnees = aides["sorties"] / ident
    manquantes = [nom for nom in ("terrain.json", "hauteurs.f32") if not (donnees / nom).is_file()]
    if manquantes:
        raise OSError("données locales absentes (" + ", ".join(manquantes) + ") : lancer py local3d/atelier_desert.py terrain")
    if (aides["projet"] / "Temp" / "UnityLockfile").exists():
        raise OSError("Unity est ouvert : fermer l'éditeur")

def preparer_sessions(aides, ville_locale):
    ident = aides["disposition"]["id"]
    aides["ecrire"](ident, aides["disposition"]["seed"])
    sorties = aides["sorties"]
    (sorties / "selection.json").write_text(json.dumps({"implantations": [ident]}), encoding="utf-8")
    dossier = sorties / ident / "preuve"
    dossier.mkdir(parents=True, exist_ok=True)
    for chemin in dossier.glob("*.json"): chemin.unlink()
    (dossier / "consigne.json").write_text(json.dumps({"ville_locale": bool(ville_locale)}), encoding="utf-8")
    return dossier

def appeler_unity(aides, nom, sortie):
    methode = dict(aides["preuve"])[nom]
    log = sortie / "logs" / f"{nom}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    if not Path(aides["unity"]).is_file(): raise OSError(f"Unity introuvable : {aides['unity']}")
    try: aides["terrain"]()
    except RuntimeError as exc: raise OSError(str(exc)) from exc
    commande = [str(aides["unity"]), "-batchmode", "-projectPath", str(aides["projet"]),
                "-executeMethod", methode, "-logFile", str(log)]
    proc = subprocess.Popen(commande, cwd=str(aides["projet"].parent),
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    try: return proc.wait(timeout=DELAI_UNITY)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, timeout=30)
        else: proc.kill()
        proc.wait(timeout=30)
        raise OSError(f"délai Unity dépassé ({DELAI_UNITY} s)")

def lire_session(dossier, nom, debut, code_unity):
    chemin = dossier / f"{nom}.json"
    if not chemin.is_file():
        raise OSError(f"session en erreur : {nom}" if code_unity not in (0, 1) else f"rapport absent : {nom}")
    if chemin.stat().st_mtime + MARGE_RAPPORT < debut: raise OSError(f"rapport ancien : {nom}")
    if code_unity not in (0, 1): raise OSError(f"session en erreur : {nom}, Unity a rendu {code_unity}")
    return json.loads(chemin.read_text(encoding="utf-8-sig"))

def juger_recus(journal, gestes):
    exiger(isinstance(gestes, list) and len(gestes) == len(journal), "reçu Unity différent du journal")
    for entree, geste in zip(journal, gestes):
        exiger(entree.get("tick") == geste.get("apres_le_tick")
               and entree.get("intention", {}).get("type") == geste.get("type"), "reçu Unity différent du journal")

def juger_monde_relance(avant, apres, journal_avant, journal_apres):
    exiger(avant == apres, "monde changé pendant la relance")
    exiger(journal_avant == journal_apres, "journal changé pendant la relance")

def fautes_dessin(jouer, relance, vierge, ticks):
    fautes = []
    j, r, v = jouer["ville"], relance["ville"], vierge["ville"]
    if not (j["tick"] == ticks and len(j["rues"]) == 1 and j["rues"] == j["rues_posees"]):
        fautes.append("jouer : une rue au tick de la recette")
    if not (len(j["parcelles_plan"]) == 1 and j["parcelles_plan"][0]["etat"] == "bornes"):
        fautes.append("jouer : parcelle aux bornes")
    if not (len(j["batiments_plan"]) == 1 and j["batiments_plan"][0]["nature"] == "scierie"
            and j["batiments_plan"][0]["etat"] == "piquets"):
        fautes.append("bâtiment absent")
    if j["pieces_parcelles"] != 1 or j["pieces_batiments"] != 1:
        fautes.append("jouer : une pièce de chaque type")
    for nom in ("rues", "rues_posees", "parcelles", "batiments", "pieces_parcelles", "pieces_batiments",
                "empreinte_rues", "empreinte_parcelles", "empreinte_batiments"):
        if j.get(nom) != r.get(nom):
            message = f"empreinte de relance différente : {nom}" if nom.startswith("empreinte") else f"relance : {nom}"
            if nom == "empreinte_rues" and (jouer.get("ville_locale") or relance.get("ville_locale")):
                message += " ; c'est le redessin qui échoue ; l'égalité Python peut rester vraie"
            fautes.append(message)
    if v["tick"] != 0 or v["rues"] or v["parcelles_plan"] or v["batiments_plan"]:
        fautes.append("vierge : le plan n'est pas vide")
    if v["pieces_parcelles"] != 0 or v["pieces_batiments"] != 0:
        fautes.append("pièce dans le rapport vierge")
    if v["empreinte_rues"] != vierge["vierge"]:
        fautes.append("vierge : empreinte des rues différente du terrain vierge")
    vide = hashlib.sha256(b"").hexdigest()
    if v["empreinte_parcelles"] != vide or v["empreinte_batiments"] != vide:
        fautes.append("vierge : dessin non vide")
    return fautes

def juger_dessin(jouer, relance, vierge, ticks):
    fautes = fautes_dessin(jouer, relance, vierge, ticks)
    exiger(not fautes, " ; ".join(fautes))

def poser(statuts, nom, fautes, tenu):
    statuts[nom] = ["violé", " ; ".join(fautes)] if fautes else ["tenu", tenu]

def plan_vide(monde):
    return all(not plan.get("rues") and not plan.get("parcelles") and not plan.get("batiments")
               for plan in monde["plans"].values())

def juger_essai(args, sortie, statuts, ident, rapports, avant, apres, journal_avant, journal_apres):
    jouer, relance, vierge = (rapports[nom] for nom in ("jouer", "relance", "vierge"))
    relance_fautes, vierge_fautes = [], []
    for nom, rapport in rapports.items():
        if rapport.get("session") != nom or rapport.get("cell") != args.cellule or rapport.get("port") != ADRESSE[1]:
            relance_fautes.append(f"{nom} : session, cellule ou port inattendus")
        if rapport.get("implantation") != ident:
            relance_fautes.append(f"{nom} : implantation {rapport.get('implantation')}")
        if rapport.get("defauts"):
            (vierge_fautes if nom == "vierge" else relance_fautes).append(f"{nom} : {len(rapport['defauts'])} défaut(s)")
    try: juger_monde_relance(avant, apres, journal_avant, journal_apres)
    except ValueError as exc: relance_fautes.append(str(exc))
    for faute in fautes_dessin(jouer, relance, vierge, args.ticks):
        (vierge_fautes if faute.startswith("vierge") or faute.startswith("pièce") else relance_fautes).append(faute)
    poser(statuts, "relancement", relance_fautes, "mêmes identifiants, états, pièces et empreintes")
    if vierge_fautes: poser(statuts, "sans geste", vierge_fautes, "")
    try:
        journal = json.loads((sortie / "journal.json").read_bytes())
        juger_recus(journal, jouer.get("gestes") or [])
        exiger([geste.get("apres_le_tick") for geste in jouer.get("gestes") or []] == [0, 1, 2],
               "gestes : ticks attendus 0, 1 et 2")
        statuts["gestes"] = ["tenu", "journal identique aux reçus, ticks 0, 1 et 2"]
    except (ValueError, KeyError, TypeError) as exc:
        statuts["gestes"] = ["violé", str(exc)]
    ticks = json.loads(apres)["ticks_ecoules"]
    exiger(type(ticks) is int and ticks >= 1, "monde : ticks écoulés absents")
    rejouer(sortie, ticks, args.seed)
    octets = [sortie.joinpath(nom).read_bytes() for nom in MONDES]
    mondes = [json.loads(document) for document in octets]
    try:
        for monde in mondes: controler_foyers(monde)
        statuts["foyers"] = ["tenu", f"{len(mondes[0]['cells'])} cellules, personnes conservées"]
    except (ValueError, KeyError, TypeError) as exc:
        statuts["foyers"] = ["violé", str(exc)]
    if octets[0] == octets[1] and octets[1] != octets[2]:
        statuts["égalité du monde"] = ["tenu", f"octets égaux sur {ticks} ticks"]
    elif octets[0] != octets[1]:
        statuts["égalité du monde"] = ["violé", "écart entre monde servi et monde rejoué"]
    else:
        statuts["égalité du monde"] = ["violé", "témoin : aucun effet des gestes"]
    try:
        bilan = juger(*octets, json.loads((sortie / "journal.json").read_bytes()), ticks)
        if not bilan["cellules_modifiees"] or not bilan["plans_modifies"]:
            statuts["égalité du monde"] = ["violé", "échantillon vide"]
    except (ValueError, KeyError, TypeError) as exc:
        if statuts["égalité du monde"][0] == "tenu": statuts["égalité du monde"] = ["violé", str(exc)]
        bilan = None
    if not plan_vide(mondes[2]) or mondes[2].get("ticks_ecoules") != ticks:
        vierge_fautes.append("témoin : le plan n'est pas vide au tick servi")
    if vierge_fautes: poser(statuts, "sans geste", vierge_fautes, "")
    elif statuts["sans geste"][0] != "violé":
        statuts["sans geste"] = ["tenu", f"plan vide au tick 0, témoin sans geste au tick {ticks}"]
    if any(etat[0] == "violé" for etat in statuts.values()): return 1
    if any(etat[0] != "tenu" for etat in statuts.values()): return 2
    (sortie / "bilan.json").write_bytes(serialiser(bilan))
    return 0

def ecrire_verdict(sortie, args, code, statuts, version, revision, motif):
    lignes = [("preuve valide", "invariant violé", "essai impossible")[code],
              "commande : py pc/epreuve_jalon4.py --avec-unity --sortie " + str(args.sortie)
              + (" --service-sourd" if args.service_sourd else "")
              + (" --ville-locale" if args.ville_locale else ""),
              "date : " + datetime.now().astimezone().isoformat(timespec="seconds"),
              "révision : " + revision, "unity : " + version, f"code : {code}"]
    for nom in STATUTS:
        etat, pourquoi = statuts[nom]
        lignes.append(f"{nom} : {etat} — {pourquoi}")
    if motif: lignes.append("motif : " + motif)
    texte = "\n".join(lignes) + "\n"
    (sortie / "verdict.txt").write_text(texte, encoding="utf-8")
    print(texte, end="")

def epreuve_unity(args):
    """Jouer puis relancer sur le service journalisé, vierge sur un second service jamais sourd."""
    sortie = args.sortie.resolve()
    sortie.mkdir(parents=True, exist_ok=True)
    statuts = {nom: ["non exécuté", "contrôle non exécuté"] for nom in STATUTS}
    version, revision, motif, code = "inconnue", revision_eprouvee(), "", 2
    try:
        if (args.seed, args.ticks, args.cellule) != RECETTE_UNITY:
            raise OSError("la recette Unity fixe la graine 0, la cellule 1175 et 10 ticks")
        aides = charger_aides()
        version = version_unity(aides["projet"])
        verifier_prealables(aides)
        if port_occupe(): raise OSError(f"port {ADRESSE[0]}:{ADRESSE[1]} indisponible")
        for nom in (*MONDES, "journal.json", "bilan.json", "verdict.txt", "jouer.json", "relance.json", "vierge.json"):
            (sortie / nom).unlink(missing_ok=True)
        dossier = preparer_sessions(aides, args.ville_locale)
        debut = time.time()
        with lancer_service(sortie, args.seed, args.service_sourd):
            jouer = lire_session(dossier, "jouer", debut, appeler_unity(aides, "jouer", sortie))
            avant = http("/monde-complet")
            journal_avant = (sortie / "journal.json").read_bytes()
            relance = lire_session(dossier, "relance", debut, appeler_unity(aides, "relance", sortie))
            apres = http("/monde-complet")
            journal_apres = (sortie / "journal.json").read_bytes()
            (sortie / MONDES[0]).write_bytes(apres)
        (sortie / "service-vierge").mkdir(parents=True, exist_ok=True)
        with lancer_service(sortie / "service-vierge", args.seed, False):
            vierge = lire_session(dossier, "vierge", debut, appeler_unity(aides, "vierge", sortie))
        for nom, rapport in (("jouer", jouer), ("relance", relance), ("vierge", vierge)):
            (sortie / f"{nom}.json").write_bytes((dossier / f"{nom}.json").read_bytes())
        code = juger_essai(args, sortie, statuts, aides["disposition"]["id"],
                           {"jouer": jouer, "relance": relance, "vierge": vierge},
                           avant, apres, journal_avant, journal_apres)
        if code:
            choix = "violé" if code == 1 else "non exécuté"
            motif = " ; ".join(f"{nom} — {etat[1]}" for nom, etat in statuts.items() if etat[0] == choix)
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        code, motif = 2, str(exc)
    except (ValueError, KeyError, TypeError) as exc:
        code, motif = 1, str(exc)
    ecrire_verdict(sortie, args, code, statuts, version, revision, motif)
    if code == 0: return 0
    print(("Invariant violé : " if code == 1 else "Essai impossible : ") + motif, file=sys.stderr)
    return code

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sortie", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--ticks", type=int, default=10)
    parser.add_argument("--cellule", type=int, default=1175)
    parser.add_argument("--service-sourd", action="store_true")
    parser.add_argument("--avec-unity", action="store_true")
    parser.add_argument("--ville-locale", action="store_true")
    args = parser.parse_args(argv)
    if args.ville_locale and not args.avec_unity:
        print("Essai impossible : --ville-locale n'est admis qu'avec --avec-unity", file=sys.stderr)
        return 2
    if args.avec_unity: return epreuve_unity(args)
    sortie = args.sortie.resolve()
    try:
        sortie.mkdir(parents=True, exist_ok=True)
        for nom in (*MONDES, "journal.json", "bilan.json"): (sortie / nom).unlink(missing_ok=True)
        if args.ticks <= 5: raise OSError("la recette exige au moins 6 ticks")
        if port_occupe(): raise OSError(f"port {ADRESSE[0]}:{ADRESSE[1]} indisponible")
        with lancer_service(sortie, args.seed, args.service_sourd):
            ecoules = 0
            chemin = f"/plan?cell={args.cellule}"
            for numero, collection, intention in recette(args.cellule):
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
        rejouer(sortie, args.ticks, args.seed)
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
