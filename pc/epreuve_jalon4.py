"""Prouve les gestes HTTP par leur rejeu CLI exact et la conservation des foyers."""
import argparse, json, subprocess, sys, threading
from contextlib import contextmanager
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
JEU = Path(__file__).resolve().parents[1] / "jeu"
if str(JEU) not in sys.path: sys.path.insert(0, str(JEU))
from sim import constants as constantes, service
MONDES = ("monde-service.json", "monde-rejoue.json", "monde-sans-gestes.json")
ADRESSE = (service.SERVICE_HOST, service.DEFAULT_SERVICE_PORT)
DELAI_HTTP, DELAI_CLI, DELAI_ARRET = 10, 60, 5

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

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sortie", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--ticks", type=int, default=10)
    parser.add_argument("--cellule", type=int, default=1175)
    parser.add_argument("--service-sourd", action="store_true")
    args = parser.parse_args(argv)
    sortie = args.sortie.resolve()
    try:
        sortie.mkdir(parents=True, exist_ok=True)
        for nom in (*MONDES, "journal.json", "bilan.json"): (sortie / nom).unlink(missing_ok=True)
        if args.ticks <= 5: raise OSError("la recette exige au moins 6 ticks")
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
        for nom, gestes in ((MONDES[1], True), (MONDES[2], False)):
            commande = [sys.executable, "-m", "sim", "--ticks", str(args.ticks), "--seed", str(args.seed),
                        "--monde-json", str(sortie / nom)]
            if gestes: commande += ["--gestes", str(sortie / "journal.json")]
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
