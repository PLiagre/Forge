"""Les bâtiments de province (`sim/batiments.py`, `data/batiments.toml`).

- Les données : un bâtiment nomme des modificateurs qui existent et se posent
  sur une cellule ; un coût en pièces, que le moteur ne porte pas, se refuse.
- Le geste : « batir_dans_une_province », refusé avec sa raison hors de ses
  terres, sans grain pour le payer, en double ; même graine et mêmes gestes,
  même monde.
- Le chantier : des paysans de la cellule deviennent ouvriers pour la
  journée, leur salaire quitte le grenier et entre au bourg ; achevé, le
  bâtiment pose ses modificateurs : le moulin récolte vraiment 10 % de grain
  en plus.
- L'IA bâtit par le même chemin, et le joueur qui fait le même geste obtient
  le même monde.
"""
import copy
import json
import math
from pathlib import Path
import random
import tomllib

import pytest

import sim.constants as c
from sim import batiments as B, engine, modificateurs as M
from sim.intentions import IntentionRefusee, recevoir_intention
from sim.model import ecrire_habitants_par_metier, lire_habitants_par_metier, lire_ouvriers_du_jour
from sim.world import World

NOURRITURE = c.MARCHANDISE_NOURRITURE


@pytest.fixture(scope="module")
def depart():
    return World.charger(rng_seed=0)


def _paris(monde):
    cid = monde.attribution_villes.placees["Paris"]
    return cid, monde.cells[cid].lieux[0].maitre


def _moulin(cid, maison):
    return {"type": "batir_dans_une_province", "maison": maison, "cell": cid, "nature": "moulin"}


def _octets(monde):
    return json.dumps(monde.to_dict(), sort_keys=True, ensure_ascii=False)


# --- Les données -------------------------------------------------------------

def test_les_donnees_des_batiments():
    types = B.charger_types()
    moulin = types["moulin"]
    assert (moulin.journees, moulin.bras_par_jour, moulin.pieces, moulin.modificateurs, moulin.un_par_cellule) == (
        600, 20, 0, ("moulin",), True)
    assert M.charger_donnees().definitions["moulin"].portee == "cellule"


@pytest.mark.parametrize("champs, motif", [
    ({"pieces": 40}, "pièces"),
    ({"modificateurs": ["moulin-inventé"]}, "inconnu des données"),
    ({"journees": 0}, "journees"),
    ({"bras_par_jour": True}, "bras_par_jour"),
    ({"kg": 500}, "champs inconnus"),
])
def test_une_donnee_qui_ne_tient_pas_est_refusee(champs, motif):
    with open(B._CHEMIN, "rb") as fichier:
        document = tomllib.load(fichier)
    document["batiments"]["moulin"].update(champs)
    with pytest.raises(B.BatimentInvalide, match=motif):
        B.lire_types(document)
    donnees = M.charger_donnees()
    lieu = M.Donnees(donnees.sources, donnees.grandeurs, {**donnees.definitions, "champ": M.Definition(
        "champ", "Champ", "recolte", 0.1, "lieu", 0)})
    with open(B._CHEMIN, "rb") as fichier:
        document = tomllib.load(fichier)
    document["batiments"]["moulin"]["modificateurs"] = ["champ"]
    with pytest.raises(B.BatimentInvalide, match="ne se pose pas sur une cellule"):
        B.lire_types(document, lieu)


# --- Le geste ----------------------------------------------------------------

def test_un_batiment_qu_on_ne_peut_pas_payer_est_refuse_avec_sa_raison(depart):
    monde = copy.deepcopy(depart)
    cid, maison = _paris(monde)
    avant = _octets(monde)
    refus = [
        (_moulin(cid, maison), "grenier insuffisant : 1800 kg de grain demandés, 0 kg disponibles"),
        (_moulin(cid, "seigneurie-1"), "pas sur vos terres"),
        (_moulin(cid, maison) | {"nature": "cathedrale"}, "bâtiment inconnu"),
        (_moulin(cid, maison) | {"cell": True}, "cell invalide"),
        (_moulin(cid, maison) | {"cell": -1}, "cellule inconnue"),
        (_moulin(cid, maison) | {"maison": "maison-inventee"}, "maison inconnue"),
    ]
    for intention, motif in refus:
        with pytest.raises(IntentionRefusee, match=motif):
            recevoir_intention(monde, intention)
    assert _octets(monde) == avant and monde.intentions_en_attente == []
    # Payable : le second moulin de la province se refuse, déposé ou bâti.
    monde.greniers[maison][NOURRITURE] = 2000.0
    recevoir_intention(monde, _moulin(cid, maison))
    with pytest.raises(IntentionRefusee, match="un seul moulin par province"):
        recevoir_intention(monde, _moulin(cid, maison))


def test_meme_graine_memes_gestes_meme_monde(depart):
    mondes = []
    for _ in range(2):
        monde = copy.deepcopy(depart)
        cid, maison = _paris(monde)
        monde.greniers[maison][NOURRITURE] = 5000.0
        recevoir_intention(monde, _moulin(cid, maison))
        rng = random.Random(0)
        for numero in range(35):
            engine.tick(monde, rng, numero)
        mondes.append(monde)
    assert _octets(mondes[0]) == _octets(mondes[1])
    assert mondes[0].batiments_de_province and "batiments_de_province" in mondes[0].to_dict()


# --- Le chantier et ses vrais coûts ---------------------------------------------

def test_le_chantier_prend_des_bras_et_paie_en_grain(depart):
    monde = copy.deepcopy(depart)
    cid, maison = _paris(monde)
    monde.greniers[maison][NOURRITURE] = 5000.0
    recevoir_intention(monde, _moulin(cid, maison))
    rng = random.Random(0)
    engine.tick(monde, rng, 0)  # l'intention s'applique, le chantier ouvre et travaille son premier jour
    batiment = monde.batiments_de_province[0]
    salaire = c.SALAIRE_JOURNEE_KG
    assert (batiment.travail_requis, batiment.travail_fourni, batiment.en_chantier) == (600, 20, True)
    assert lire_ouvriers_du_jour(monde.cells[cid].lieux[0]) >= 20
    assert lire_habitants_par_metier(monde.cells[cid]).get(c.METIER_OUVRIERS, 0) >= 20
    # Le jour suivant, avant le tick : le grain d'un jour de salaires passe du grenier au bourg.
    cellule = monde.cells[cid]
    grenier_avant = monde.greniers[maison][NOURRITURE]
    bourg_avant = cellule.lieux[0].stocks[NOURRITURE]
    B.avancer(monde)
    assert monde.batiments_de_province[0].travail_fourni == 40
    assert grenier_avant - monde.greniers[maison][NOURRITURE] == pytest.approx(20 * salaire)
    assert cellule.lieux[0].stocks[NOURRITURE] - bourg_avant == pytest.approx(20 * salaire)
    # Sans grain pour payer, le chantier attend : rien ne se crée.
    monde.greniers[maison][NOURRITURE] = salaire - 1
    avant = _octets(monde)
    B.avancer(monde)
    assert _octets(monde) == avant


def test_le_chantier_ne_lit_ni_les_maitres_ni_le_registre(depart, monkeypatch):
    """Un tick avec un bâtiment en chantier, sous la garde des invariants du tick (test_maitre_tick)."""
    from sim import maitres
    from sim.model import EtatDeLieu
    from sim.tests.test_maisons import _tick_sans_lecture_registre
    monde = copy.deepcopy(depart)
    cid, maison = _paris(monde)
    monde.greniers[maison][NOURRITURE] = 5000.0
    recevoir_intention(monde, _moulin(cid, maison))
    engine.tick(monde, random.Random(0), 0)
    fourni = monde.batiments_de_province[0].travail_fourni

    def lire(self):
        raise RuntimeError("maître lu au tick")

    monkeypatch.setattr(EtatDeLieu, "maitre", property(lire))
    monkeypatch.setattr(maitres, "attribuer_maitres", lambda *a: pytest.fail("attribution au tick"))
    _tick_sans_lecture_registre(monkeypatch, monde, engine.tick, monde.ticks_ecoules)
    assert monde.batiments_de_province[0].travail_fourni > fourni


def test_le_moulin_acheve_recolte_dix_pour_cent_de_vrais_kilos_en_plus(depart, monkeypatch):
    monde = copy.deepcopy(depart)
    cid, maison = _paris(monde)
    monde.greniers[maison][NOURRITURE] = 5000.0
    recevoir_intention(monde, _moulin(cid, maison))
    rng = random.Random(0)
    while not monde.batiments_de_province or monde.batiments_de_province[0].en_chantier:
        engine.tick(monde, rng, monde.ticks_ecoules)
    batiment = monde.batiments_de_province[0]
    assert batiment.fin == monde.ticks_ecoules - 1 and batiment.travail_fourni == batiment.travail_requis
    poses = [p for p in monde.modificateurs if p.source == batiment.source]
    assert [(p.identifiant, p.grandeur, p.valeur, p.cible) for p in poses] == [("moulin", "recolte", 0.10, ("cellule", cid))]
    sans = copy.deepcopy(monde)
    assert M.retirer(sans, batiment.source) == 1
    verses = {}
    original = engine._verser_recolte
    for nom, essai, alea in (("moulin", monde, copy.deepcopy(rng)), ("sans", sans, copy.deepcopy(rng))):
        verses[nom] = {}

        def mesurer(cell, recolte, carte, saison, recoltes, facteurs=None, _v=verses[nom]):
            avant = cell.stocks.get(NOURRITURE, 0.0)
            original(cell, recolte, carte, saison, recoltes, facteurs)
            _v[cell.cell_id] = cell.stocks.get(NOURRITURE, 0.0) - avant

        with monkeypatch.context() as ctx:
            ctx.setattr(engine, "_verser_recolte", mesurer)
            engine.tick(essai, alea, essai.ticks_ecoules)
    assert verses["moulin"][cid] == pytest.approx(verses["sans"][cid] * 1.10, rel=1e-12)
    assert all(verses["moulin"][x] == verses["sans"][x] for x in verses["sans"] if x != cid)


# --- L'IA, par le même chemin -------------------------------------------------

def test_l_ia_batit_par_le_meme_chemin(depart):
    from sim import ia
    from sim.capitales import toutes_les_maisons_de_l_ia
    monde = copy.deepcopy(depart)
    rng = random.Random(0)
    for numero in range(c.FENETRE_FLUX_TICKS):
        engine.tick(monde, rng, numero)
    maisons = toutes_les_maisons_de_l_ia(monde)
    grande = next(m for m in maisons if m.sorte == "grande maison" and m.cell_id is not None
                  and monde.cells[m.cell_id].lieux[0].maitre == f"grande-{m.id}")
    cle = f"grande-{grande.id}"
    monde.greniers[cle][NOURRITURE] = 1e8
    jour = next(t for t in range(monde.ticks_ecoules, monde.ticks_ecoules + c.FENETRE_FLUX_TICKS)
                if ia._jour_de_la_part(cle, t))
    while monde.ticks_ecoules < jour:
        engine.tick(monde, rng, monde.ticks_ecoules)
    joueur = copy.deepcopy(monde)
    releve = []
    ia.jouer_ia(monde, releve, maisons)
    batir = [e for e in releve if e["intention"]["type"] == "batir_dans_une_province" and e["intention"]["maison"] == cle]
    assert len(batir) == 1 and "refus" not in batir[0]
    assert batir[0]["intention"] == _moulin(grande.cell_id, cle)
    raison = batir[0]["raison"]
    assert raison["regle"] == "moulin_quand_le_grenier_le_permet" and raison["grenier_nourriture_kg"] > raison["reserve_voulue_kg"] + raison["cout_kg"]
    for entree in releve:
        if "refus" not in entree:
            recevoir_intention(joueur, entree["intention"])
    alea_joueur = copy.deepcopy(rng)
    engine.tick(monde, rng, monde.ticks_ecoules)
    engine.tick(joueur, alea_joueur, joueur.ticks_ecoules)
    assert _octets(monde) == _octets(joueur)
    assert any(b.maison == cle for b in monde.batiments_de_province)
    # Sa réserve compte désormais les salaires du chantier qui reste.
    lieux = ia._lieux_de_la_maison(monde, cle)
    avec = ia._reserve_voulue(monde, lieux)["salaires_a_venir_kg"]
    sans = copy.deepcopy(monde)
    sans.batiments_de_province = []
    assert avec > ia._reserve_voulue(sans, lieux)["salaires_a_venir_kg"]


def test_le_service_sert_les_batiments_du_pays(depart):
    from sim.service import ServeurMonde
    with ServeurMonde(("127.0.0.1", 0), 0, 0) as serveur:
        cid, maison = _paris(serveur.world)
        serveur.world.greniers[maison][NOURRITURE] = 5000.0
        recevoir_intention(serveur.world, _moulin(cid, maison))
        serveur.jouer_un_tick()
        document = json.loads(serveur.octets_du_pays(maison))
        assert [(b["nature"], b["cell_id"], b["nom"], b["en_chantier"]) for b in document["batiments"]] == [
            ("moulin", cid, "Moulin", True)]


# --- La caserne sur une parcelle du plan -------------------------------------------

BAR = "seigneurie-1"


def _rectangle(x, largeur=10.0, profondeur=20.0):
    return ((x, 500.0), (x + largeur, 500.0), (x + largeur, 500.0 + profondeur), (x, 500.0 + profondeur))


def _capitale_avec_parcelles(depart, grain=20000.0):
    """Le monde de départ, et dans la capitale de Bar : la parcelle 0 achevée, la 1 en chantier, la 2 achevée
    et bâtie d'un four, la 3 achevée, plus grande que la 0."""
    from sim.plan import Batiment, Parcelle, Plan
    monde = copy.deepcopy(depart)
    cid = next(m for m in monde.maisons if m.id == BAR).cell_id
    assert monde.cells[cid].lieux[0].maitre == BAR
    parcelles = [Parcelle(0, _rectangle(0.0)), Parcelle(1, _rectangle(20.0), True, 1, 20, 5),
                 Parcelle(2, _rectangle(40.0)), Parcelle(3, _rectangle(60.0, 20.0, 30.0))]
    monde.plans[cid] = Plan(parcelles=parcelles, batiments=[Batiment(0, 2, "four", _rectangle(40.0))])
    monde.greniers[BAR][NOURRITURE] = grain
    return monde, cid


def _caserne(cid, parcelle, maison=BAR):
    return {"type": "batir_dans_une_province", "maison": maison, "cell": cid, "nature": "caserne",
            "parcelle": parcelle}


def test_la_caserne_posee_sur_une_parcelle_s_acheve_et_ouvre_la_levee(depart):
    from sim import guerre as G
    monde, cid = _capitale_avec_parcelles(depart)
    regles = G.charger_regles()
    assert G.raison_levee_fermee(monde, BAR, regles) is not None
    recevoir_intention(monde, _caserne(cid, 0))
    engine._appliquer_intentions(monde)
    caserne = monde.batiments_de_province[0]
    # Un seul chantier, un seul prix : celui de data/batiments.toml, quelle que soit la parcelle.
    assert (caserne.nature, caserne.parcelle, caserne.travail_requis, caserne.en_chantier) == (
        "caserne", 0, B.charger_types()["caserne"].journees, True)
    assert caserne.en_document()["parcelle"] == 0 and monde.plans[cid].batiments[0].parcelle == 2
    assert len(monde.plans[cid].batiments) == 1, "la caserne n'entre pas dans les bâtiments du plan"
    ailleurs, _ = _capitale_avec_parcelles(depart)
    recevoir_intention(ailleurs, _caserne(cid, 3))
    engine._appliquer_intentions(ailleurs)
    assert ailleurs.batiments_de_province[0].travail_requis == caserne.travail_requis
    # Son chantier est celui de batiments.avancer : 25 bras par jour, payés au grenier, jusqu'à l'achèvement.
    rng = random.Random(0)
    while monde.batiments_de_province[0].en_chantier:
        assert G.raison_levee_fermee(monde, BAR, regles) is not None
        avant = monde.batiments_de_province[0].travail_fourni
        engine.tick(monde, rng, monde.ticks_ecoules)
        assert monde.batiments_de_province[0].travail_fourni - avant <= B.charger_types()["caserne"].bras_par_jour
    assert monde.batiments_de_province[0].parcelle == 0
    assert G.raison_levee_fermee(monde, BAR, regles) is None


def test_sans_parcelle_le_batiment_et_ses_octets_ne_changent_pas(depart):
    monde, cid = _capitale_avec_parcelles(depart)
    sans = _caserne(cid, 0)
    del sans["parcelle"]
    geste = recevoir_intention(monde, sans)
    assert geste.parcelle is None
    engine._appliquer_intentions(monde)
    document = monde.batiments_de_province[0].en_document()
    assert "parcelle" not in document and "parcelle" not in monde.to_dict()["batiments_de_province"][0]
    assert sorted(document) == ["cell_id", "debut", "en_chantier", "fin", "identifiant", "maison", "nature",
                                "travail_fourni", "travail_requis"]


def test_une_parcelle_qui_ne_tient_pas_est_refusee_avec_sa_raison(depart):
    from sim.intentions import PoseBatiment
    monde, cid = _capitale_avec_parcelles(depart)
    avant = _octets(monde)
    for parcelle, motif in ((99, "^parcelle absente du plan : 99$"),
                            ("0", "^parcelle invalide : entier attendu, reçu '0'$"),
                            (True, "^parcelle invalide : entier attendu, reçu True$"),
                            (1, r"^parcelle en chantier : 1 \(5/20 journées\)$"),
                            (2, "^parcelle déjà bâtie : 2$")):
        with pytest.raises(IntentionRefusee, match=motif):
            recevoir_intention(monde, _caserne(cid, parcelle))
    assert _octets(monde) == avant and monde.intentions_en_attente == []
    # Une pose déposée la promet : la caserne ne la prend pas.
    monde.intentions_en_attente.append(PoseBatiment(cid, 3, "maison"))
    with pytest.raises(IntentionRefusee, match="^parcelle déjà promise : 3$"):
        recevoir_intention(monde, _caserne(cid, 3))
    # Les autres refus du bâtiment de province passent avant la parcelle.
    with pytest.raises(IntentionRefusee, match="pas sur vos terres"):
        recevoir_intention(monde, _caserne(cid, 0, "seigneurie-2"))
    monde.intentions_en_attente.clear()
    # La caserne déposée promet sa parcelle à la pose d'un bâtiment, puis, posée, l'a bâtie.
    recevoir_intention(monde, _caserne(cid, 0))
    with pytest.raises(IntentionRefusee, match="^parcelle déjà promise : 0$"):
        recevoir_intention(monde, {"type": "poser_batiment", "maison": BAR, "cell": cid, "parcelle": 0,
                                   "nature": "maison"})
    engine._appliquer_intentions(monde)
    with pytest.raises(IntentionRefusee, match="^parcelle déjà bâtie : 0$"):
        recevoir_intention(monde, {"type": "poser_batiment", "maison": BAR, "cell": cid, "parcelle": 0,
                                   "nature": "maison"})
    # Le geste n'admet la parcelle que pour un bâtiment de province.
    with pytest.raises(IntentionRefusee, match="^champ inconnu : parcelle$"):
        recevoir_intention(monde, {"type": "ameliorer_une_province", "maison": BAR, "cell": cid, "parcelle": 0})


def test_aucune_maison_ne_s_ouvre_seule_sous_une_caserne(depart):
    from sim import chantiers
    from sim.plan import Parcelle, Plan
    mondes = {}
    for cas in ("sans caserne", "caserne"):
        monde, cid = _capitale_avec_parcelles(depart)
        monde.plans[cid] = Plan(parcelles=[Parcelle(0, _rectangle(0.0))])
        # Dix artisans sans logis, pris aux paysans : ils ouvriraient leur maison sur la première parcelle libre.
        cellule = monde.cells[cid]
        metiers = lire_habitants_par_metier(cellule)
        ecrire_habitants_par_metier(cellule, {c.METIER_PAYSANS: metiers[c.METIER_PAYSANS] - 10, c.METIER_ARTISANS: 10})
        if cas == "caserne":
            journees = B.charger_types()["caserne"].journees
            monde.batiments_de_province = [B.BatimentDeProvince(0, "caserne", cid, BAR, journees, 0, True, 0,
                                                                parcelle=0)]
        chantiers.avancer_chantiers(monde)
        mondes[cas] = [(b.parcelle, b.nature, b.autoconstruction) for b in monde.plans[cid].batiments]
    # Contre-épreuve : sans la caserne, les artisans sans logis ouvrent leur maison sur la parcelle 0.
    assert mondes == {"sans caserne": [(0, "maison", True)], "caserne": []}


def test_le_plan_sert_les_batiments_de_province_de_sa_cellule(depart):
    from sim.service import ServeurMonde
    from sim.plan import Parcelle, Plan
    with ServeurMonde(("127.0.0.1", 0), 0, 0) as serveur:
        monde = serveur.world
        cid = next(m for m in monde.maisons if m.id == BAR).cell_id
        paris, _ = _paris(monde)
        serveur.jouer_un_tick()
        assert "batiments_de_province" not in json.loads(serveur.octets_plan(serveur.etat_publie, cid))
        monde.plans[cid] = Plan(parcelles=[Parcelle(0, _rectangle(0.0))])
        monde.greniers[BAR][NOURRITURE] = 20000.0
        recevoir_intention(monde, _caserne(cid, 0))
        serveur.jouer_un_tick()
        caserne = next(b for b in monde.batiments_de_province if b.maison == BAR)
        plan = json.loads(serveur.octets_plan(serveur.etat_publie, cid))
        assert plan["batiments_de_province"] == [
            {"identifiant": caserne.identifiant, "nature": "caserne", "parcelle": 0,
             "travail_requis": caserne.travail_requis, "travail_fourni": caserne.travail_fourni,
             "en_chantier": True}]
        assert 0 < caserne.travail_fourni < caserne.travail_requis
        # Une cellule sans bâtiment de province ne porte pas la clé.
        assert all(b.cell_id != paris for b in monde.batiments_de_province)
        assert "batiments_de_province" not in json.loads(serveur.octets_plan(serveur.etat_publie, paris))


def test_le_service_ne_laisse_le_joueur_batir_que_pour_sa_maison():
    import threading
    from sim.service import ServeurMonde
    from sim.tests.test_monde import requete_service
    from sim.plan import Parcelle, Plan

    def poster(intention):
        return requete_service(port, "/intention", "POST", json.dumps(intention).encode())

    serveur = ServeurMonde(("127.0.0.1", 0), 0, 0)
    fil = threading.Thread(target=serveur.serve_forever)
    fil.start()
    port, monde = serveur.server_port, serveur.world
    cid = next(m for m in monde.maisons if m.id == BAR).cell_id
    try:
        monde.plans[cid] = Plan(parcelles=[Parcelle(0, _rectangle(0.0))])
        monde.greniers[BAR][NOURRITURE] = 20000.0
        statut, recu, _ = poster(_caserne(cid, 0))
        assert statut == 400 and "départ non appliqué" in recu["erreur"]
        assert poster({"type": "choisir_depart", "seigneurie": 1})[0] == 200
        requete_service(port, "/tick?n=1", "POST")
        assert monde.maison_du_joueur == BAR
        statut, recu, _ = poster(_caserne(cid, 0, "seigneurie-2"))
        assert statut == 400 and recu["erreur"] == "maison interdite : seule la maison du joueur bâtit dans ses provinces"
        assert not monde.intentions_en_attente
        assert poster(_caserne(cid, 0))[:2] == (200, {"acceptee": True, "appliquee_au_tick": 1})
    finally:
        serveur.shutdown()
        fil.join()
        serveur.server_close()


ZAB, BISKRA = "seigneurie-6", 10103
FIGEES = Path(__file__).parents[3] / "3d/unity/Assets/ForgeLocal3D/Pont/Tests"
ROUTE_EST = {"type": "tracer_route", "maison": ZAB, "cell": BISKRA, "points": [[66, -8], [120, -8]], "largeur_m": 4}
DECOUPE_EST = {"type": "decouper_parcelle", "maison": ZAB, "cell": BISKRA, "rue": 0, "segment": 0, "debut_m": 14,
               "facade_m": 10, "profondeur_m": 20, "cote": "gauche"}


def plans_de_la_caserne_de_biskra():
    """Le joueur du Zab, par le service et ses seuls gestes : la part au plus haut, une route à l'est de la place,
    une parcelle de 10 m × 20 m, puis la caserne sur elle. Rend les octets de `/plan` de Biskra au premier
    jour du chantier puis au jour de son achèvement, avec leurs ticks : les réponses figées du pont."""
    from sim.tests.test_carte_servie import _service_local
    from sim.tests.test_monde import requete_service
    with _service_local() as (serveur, port):
        def deposer(intention):
            statut, recu, _ = requete_service(port, "/intention", "POST", json.dumps(intention).encode())
            assert statut == 200, recu
        tick = lambda: requete_service(port, "/tick?n=1", "POST")  # noqa: E731
        plan = lambda: requete_service(port, f"/plan?cell={BISKRA}")  # noqa: E731
        deposer({"type": "choisir_depart", "seigneurie": 6})
        tick()
        deposer({"type": "fixer_part", "maison": ZAB, "part": c.PART_MAXIMALE})
        deposer(ROUTE_EST)
        tick()
        deposer(DECOUPE_EST)
        tick()
        while plan()[1]["parcelles"][0]["en_chantier"]:
            tick()
        deposer({"type": "batir_dans_une_province", "maison": ZAB, "cell": BISKRA, "nature": "caserne", "parcelle": 0})
        tick()
        _, document, en_chantier = plan()
        tick_en_chantier = document["tick"]
        while plan()[1]["batiments_de_province"][0]["en_chantier"]:
            tick()
        _, document, achevee = plan()
        return tick_en_chantier, en_chantier, document["tick"], achevee


def test_les_plans_figes_de_la_caserne_sont_ceux_du_service():
    """Les octets que lit le pont (`ClientPlanTests`, `PoseDeCaserneTests`) sont ceux que le service rend."""
    tick_chantier, chantier, tick_achevee, achevee = plans_de_la_caserne_de_biskra()
    figee = FIGEES / f"plan-biskra-caserne-graine0-tick{tick_chantier}.json"
    assert figee.read_bytes() == chantier
    assert (FIGEES / f"plan-biskra-caserne-achevee-graine0-tick{tick_achevee}.json").read_bytes() == achevee
    premier, dernier = (json.loads(o)["batiments_de_province"] for o in (chantier, achevee))
    caserne = B.charger_types()["caserne"]
    assert premier == [{"identifiant": premier[0]["identifiant"], "nature": "caserne", "parcelle": 0,
                        "travail_requis": caserne.journees, "travail_fourni": caserne.bras_par_jour, "en_chantier": True}]
    assert dernier[0] | {"travail_fourni": 0, "en_chantier": True} == premier[0] | {"travail_fourni": 0}
    assert dernier[0]["travail_fourni"] == caserne.journees and dernier[0]["en_chantier"] is False


# --- Le marché et la grange : trois bâtiments, un seul grenier ----------------------

def _batir(nature, cid, maison):
    return _moulin(cid, maison) | {"nature": nature}


def test_les_donnees_des_quatre_batiments():
    types = B.charger_types()
    assert sorted(types) == ["caserne", "grange", "marche", "moulin"]
    # La caserne ne pose aucun modificateur : achevée dans la capitale, elle ouvre la levée (sim/guerre.py).
    attendu = {"moulin": (600, 20, 0, ("moulin",), True, "m"), "marche": (900, 30, 0, ("marche",), True, "m"),
               "grange": (400, 20, 0, ("grange",), True, "f"), "caserne": (800, 25, 0, (), True, "f")}
    assert {n: (t.journees, t.bras_par_jour, t.pieces, t.modificateurs, t.un_par_cellule, t.genre)
            for n, t in types.items()} == attendu
    definitions = M.charger_donnees().definitions
    assert [(definitions[n].grandeur, definitions[n].valeur, definitions[n].portee, definitions[n].duree_jours)
            for n in ("moulin", "marche", "grange")] == [
        ("recolte", 0.10, "cellule", 0), ("commerce", 0.20, "cellule", 0), ("departs", -0.25, "cellule", 0)]
    # Au salaire de base : 1800, 2700, 1200 et 2400 kg.
    assert [t.journees * c.SALAIRE_JOURNEE_KG
            for t in (types["moulin"], types["marche"], types["grange"], types["caserne"])] == [1800, 2700, 1200, 2400]


def test_les_donnees_refusent_une_grange_de_lieu_et_un_genre_inconnu():
    donnees = M.charger_donnees()
    lieu = M.Donnees(donnees.sources, donnees.grandeurs, {**donnees.definitions, "grange": M.Definition(
        "grange", "Grange", "departs", -0.25, "lieu", 0)})
    with open(B._CHEMIN, "rb") as fichier:
        document = tomllib.load(fichier)
    with pytest.raises(B.BatimentInvalide, match="ne se pose pas sur une cellule"):
        B.lire_types(document, lieu)
    for genre in ("n", "F", 1, True):
        document["batiments"]["grange"]["genre"] = genre
        with pytest.raises(B.BatimentInvalide, match="genre"):
            B.lire_types(document)
    document["batiments"]["grange"]["genre"] = "m"
    assert B.lire_types(document)["grange"].genre == "m"


def test_un_seul_grenier_paie_les_trois_et_refuse_avec_ses_chiffres(depart):
    monde = copy.deepcopy(depart)
    cid, maison = _paris(monde)
    avant = _octets(monde)
    for nature, kg in (("marche", 2700), ("grange", 1200)):
        with pytest.raises(IntentionRefusee, match=f"grenier insuffisant : {kg} kg de grain demandés, 0 kg disponibles"):
            recevoir_intention(monde, _batir(nature, cid, maison))
    assert _octets(monde) == avant and monde.intentions_en_attente == []
    # 3 000 kg paient le moulin et la grange, pas le marché en plus.
    monde.greniers[maison][NOURRITURE] = 3000.0
    recevoir_intention(monde, _moulin(cid, maison))
    avant = _octets(monde)
    with pytest.raises(IntentionRefusee, match="grenier insuffisant : 2700 kg de grain demandés, 1200 kg disponibles"):
        recevoir_intention(monde, _batir("marche", cid, maison))
    assert _octets(monde) == avant
    recevoir_intention(monde, _batir("grange", cid, maison))
    avant = _octets(monde)
    for nature, motif in (("grange", "une seule grange par province"), ("moulin", "un seul moulin par province"),
                          ("marche", "grenier insuffisant")):
        with pytest.raises(IntentionRefusee, match=motif):
            recevoir_intention(monde, _batir(nature, cid, maison))
    assert _octets(monde) == avant
    # Le même dépôt du marché, avec 4 500 kg : c'est bien le grain qui refusait.
    riche = copy.deepcopy(depart)
    riche.greniers[maison][NOURRITURE] = 4500.0
    recevoir_intention(riche, _moulin(cid, maison))
    recevoir_intention(riche, _batir("marche", cid, maison))
    assert len(riche.intentions_en_attente) == 2


def test_une_cellule_sans_assez_de_paysans_refuse_le_marche_sans_changer_le_monde(depart):
    monde = copy.deepcopy(depart)
    cid, maison = _paris(monde)
    monde.greniers[maison][NOURRITURE] = 1e6
    metiers = dict(lire_habitants_par_metier(monde.cells[cid]))
    metiers[c.METIER_PAYSANS] = 29
    from sim.model import ecrire_habitants_par_metier
    ecrire_habitants_par_metier(monde.cells[cid], metiers)
    avant = _octets(monde)
    with pytest.raises(IntentionRefusee, match="pas assez de bras : 30 paysans par jour demandés"):
        recevoir_intention(monde, _batir("marche", cid, maison))
    assert _octets(monde) == avant
    # La grange ne demande que 20 bras : la même cellule la reçoit.
    recevoir_intention(monde, _batir("grange", cid, maison))


def _jouer_jusqu_a_l_achevement(depart, nature):
    """Joue un bâtiment à Paris jusqu'au tick qui l'achève.

    Rend le monde avant ce tick, le monde après, le hasard d'avant ce tick, la cellule, la maison.
    """
    monde = copy.deepcopy(depart)
    cid, maison = _paris(monde)
    monde.greniers[maison][NOURRITURE] = 1e6
    recevoir_intention(monde, _batir(nature, cid, maison))
    rng = random.Random(0)
    bras = B.charger_types()[nature].bras_par_jour
    engine.tick(monde, rng, monde.ticks_ecoules)
    while True:
        batiment = monde.batiments_de_province[0]
        if batiment.travail_requis - batiment.travail_fourni <= bras:
            break
        engine.tick(monde, rng, monde.ticks_ecoules)
    avant, alea = copy.deepcopy(monde), copy.deepcopy(rng)
    engine.tick(monde, rng, monde.ticks_ecoules)
    assert not monde.batiments_de_province[0].en_chantier
    return avant, monde, alea, cid, maison, rng


def _verser(monde, alea, monkeypatch):
    """Joue un tick ; rend la récolte versée à chaque cellule."""
    verse = {}
    original = engine._verser_recolte

    def mesurer(cell, recolte, carte, saison, recoltes, facteurs=None):
        avant = cell.stocks.get(NOURRITURE, 0.0)
        original(cell, recolte, carte, saison, recoltes, facteurs)
        verse[cell.cell_id] = cell.stocks.get(NOURRITURE, 0.0) - avant

    with monkeypatch.context() as ctx:
        ctx.setattr(engine, "_verser_recolte", mesurer)
        engine.tick(monde, alea, monde.ticks_ecoules)
    return verse


def test_le_marche_acheve_change_le_commerce_de_sa_cellule_au_tick_pres(depart, monkeypatch):
    avant, monde, _, cid, maison, rng = _jouer_jusqu_a_l_achevement(depart, "marche")
    batiment = monde.batiments_de_province[0]
    # Au tick près : aucune entrée `commerce` avant, 1.20 pour chaque lieu de Paris après, et rien d'autre.
    assert "commerce" not in avant.facteurs_du_tick
    lieux = {(cid, lieu.rang) for lieu in monde.cells[cid].lieux}
    assert monde.facteurs_du_tick["commerce"] == {cle: pytest.approx(1.20) for cle in lieux} and len(lieux) >= 2
    assert set(monde.facteurs_du_tick) - set(avant.facteurs_du_tick) == {"commerce"}
    poses = [p for p in monde.modificateurs if p.source == batiment.source]
    assert batiment.source == f"batiment:marche-{batiment.identifiant}"
    assert [(p.identifiant, p.grandeur, p.valeur, p.cible) for p in poses] == [("marche", "commerce", 0.20, ("cellule", cid))]
    sans = copy.deepcopy(monde)
    assert M.retirer(sans, batiment.source) == 1

    def comparer(avec, sans, alea):
        """Les arêtes de Paris ×1.20, les autres identiques ; récolte et prélèvement du jour au kilo."""
        index = engine._index_aretes(avec)
        facteurs = M.facteurs_du_monde
        avec.facteurs_du_tick, sans.facteurs_du_tick = facteurs(avec), facteurs(sans)
        capacites_avec, capacites_sans = engine._capacites_aretes(avec, index), engine._capacites_aretes(sans, index)
        touchees = [cle for cle in capacites_sans if cid in cle]
        assert touchees and all(capacites_avec[cle] == capacites_sans[cle] * 1.20 for cle in touchees)
        assert all(capacites_avec[cle] == capacites_sans[cle] for cle in capacites_sans if cid not in cle)
        t = avec.ticks_ecoules
        verse_avec = _verser(avec, copy.deepcopy(alea), monkeypatch)
        verse_sans = _verser(sans, alea, monkeypatch)
        assert verse_avec == verse_sans
        assert avec.flux.jours[t].preleve == sans.flux.jours[t].preleve

    comparer(copy.deepcopy(monde), copy.deepcopy(sans), copy.deepcopy(rng))
    # Contre-épreuve : avec la pose du moulin à la place de celle du marché, la comparaison échoue.
    moulin = copy.deepcopy(sans)
    M.poser(moulin, "moulin", "batiment:moulin-epreuve", {"cellule": cid})
    with pytest.raises(AssertionError):
        comparer(moulin, copy.deepcopy(sans), copy.deepcopy(rng))


def _vider_le_bourg(monde, cid):
    """Le bourg sans grain, ses champs pleins : ses foyers partent vers le mieux-vivre (test_departs_d_un_lieu)."""
    cellule = monde.cells[cid]
    retire = cellule.lieux[0].stocks[NOURRITURE]
    cellule.lieux[0].stocks[NOURRITURE] = 0.0
    cellule.stocks[NOURRITURE] -= retire


def test_la_grange_achevee_change_les_departs_de_sa_cellule_au_tick_pres(depart, monkeypatch):
    avant, monde, _, cid, maison, rng = _jouer_jusqu_a_l_achevement(depart, "grange")
    batiment = monde.batiments_de_province[0]
    assert "departs" not in avant.facteurs_du_tick
    lieux = {(cid, lieu.rang) for lieu in monde.cells[cid].lieux}
    assert monde.facteurs_du_tick["departs"] == {cle: pytest.approx(0.75) for cle in lieux} and len(lieux) >= 2
    assert set(monde.facteurs_du_tick) - set(avant.facteurs_du_tick) == {"departs"}
    poses = [p for p in monde.modificateurs if p.source == batiment.source]
    assert [(p.identifiant, p.grandeur, p.valeur, p.cible) for p in poses] == [("grange", "departs", -0.25, ("cellule", cid))]
    sans = copy.deepcopy(monde)
    assert M.retirer(sans, batiment.source) == 1

    def comparer(avec, sans, alea):
        for monde_ in (avec, sans):
            _vider_le_bourg(monde_, cid)
        t = avec.ticks_ecoules
        verse_avec = _verser(avec, copy.deepcopy(alea), monkeypatch)
        verse_sans = _verser(sans, alea, monkeypatch)
        partis_avec, partis_sans = avec.flux.jours[t].partis, sans.flux.jours[t].partis
        assert partis_sans.get((cid, 0), 0) > 0
        assert partis_avec.get((cid, 0), 0) < partis_sans[(cid, 0)]
        assert all(partis_avec.get(cle, 0) <= partis_sans.get(cle, 0) for cle in lieux)
        assert {k: v for k, v in partis_avec.items() if k[0] != cid} == {
            k: v for k, v in partis_sans.items() if k[0] != cid}
        assert verse_avec == verse_sans
        assert {k: g.total for k, g in avec.convois.items()} == {k: g.total for k, g in sans.convois.items()}

    comparer(copy.deepcopy(monde), copy.deepcopy(sans), copy.deepcopy(rng))
    # Contre-épreuve : une grange qui ferait fuir (+0,25) ne passe pas la même comparaison.
    donnees = M.charger_donnees()
    fuite = M.Donnees(donnees.sources, donnees.grandeurs, {**donnees.definitions, "fuite": M.Definition(
        "fuite", "Fuite", "departs", 0.25, "cellule", 0)})
    fuyant = copy.deepcopy(sans)
    M.poser(fuyant, "fuite", "batiment:grange-epreuve", {"cellule": cid}, fuite)
    with pytest.raises(AssertionError):
        comparer(fuyant, copy.deepcopy(sans), copy.deepcopy(rng))


# --- L'IA pèse les trois par le même chemin ------------------------------------

def _au_jour_de_sa_part(depart):
    """Une grande maison au grenier de 1e8, au jour de sa part, sa cellule vidée de grain.

    Toute la cellule est vidée (pas seulement son bourg) : sans cela, les foyers
    qui partent vont vers un champ de la même cellule et le solde y reste nul.
    Vide, elle voit partir ses foyers vers ses voisines et reçoit leur grain.
    """
    from sim import ia
    from sim.capitales import toutes_les_maisons_de_l_ia
    monde = copy.deepcopy(depart)
    rng = random.Random(0)
    for numero in range(c.FENETRE_FLUX_TICKS):
        engine.tick(monde, rng, numero)
    maisons = toutes_les_maisons_de_l_ia(monde)
    grande = next(m for m in maisons if m.sorte == "grande maison" and m.cell_id is not None
                  and monde.cells[m.cell_id].lieux[0].maitre == f"grande-{m.id}")
    cle = f"grande-{grande.id}"
    monde.greniers[cle][NOURRITURE] = 1e8
    cellule = monde.cells[grande.cell_id]
    for lieu in cellule.lieux:
        cellule.stocks[NOURRITURE] -= lieu.stocks.get(NOURRITURE, 0.0)
        lieu.stocks[NOURRITURE] = 0.0
    jour = next(t for t in range(monde.ticks_ecoules, monde.ticks_ecoules + c.FENETRE_FLUX_TICKS)
                if ia._jour_de_la_part(cle, t))
    while monde.ticks_ecoules < jour:
        engine.tick(monde, rng, monde.ticks_ecoules)
    return monde, rng, maisons, grande, cle


def _bati(monde, cle, cid, nature):
    """Un bâtiment déjà achevé dans la cellule, avec sa pose (le monde de la maison, sans rejouer son chantier)."""
    type_ = B.charger_types()[nature]
    identifiant = max((b.identifiant for b in monde.batiments_de_province), default=-1) + 1
    batiment = B.BatimentDeProvince(identifiant, nature, cid, cle, type_.journees, type_.journees, False, 0, 1)
    monde.batiments_de_province = [*monde.batiments_de_province, batiment]
    for modificateur in type_.modificateurs:
        M.poser(monde, modificateur, batiment.source, {"cellule": cid})


def _jouer_l_ia(monde, maisons):
    from sim import ia
    releve = []
    ia.jouer_ia(monde, releve, maisons)
    return releve


def _proposees(monde, maisons, cle):
    """Les bâtiments que cette maison dépose ce jour-là."""
    return [e for e in _jouer_l_ia(monde, maisons)
            if e["intention"]["type"] == "batir_dans_une_province" and e["intention"]["maison"] == cle]


def _memes_octets(un, autre):
    egaux = _octets(un) == _octets(autre)  # l'écart de deux mondes est trop long à diffuser par pytest
    assert egaux


def test_l_ia_pese_le_moulin_la_grange_puis_le_marche_par_le_meme_chemin(depart):
    from sim.tests.test_monde import _controler_raisons_du_pays, _lire_batiment
    monde, rng, maisons, grande, cle = _au_jour_de_sa_part(depart)
    cid = grande.cell_id
    t = monde.ticks_ecoules
    # Le moulin d'abord : le grain nourrit tout le reste.
    premiere = _proposees(copy.deepcopy(monde), maisons, cle)
    assert [e["intention"]["nature"] for e in premiere] == ["moulin"]
    # Un moulin achevé, une place à prendre à portée : la caserne, qui ouvre la levée.
    _bati(monde, cle, cid, "moulin")
    seconde = _proposees(copy.deepcopy(monde), maisons, cle)
    assert [(e["intention"]["nature"], e["raison"]["regle"]) for e in seconde] == [
        ("caserne", "caserne_pour_la_guerre")] and "refus" not in seconde[0]
    assert seconde[0]["raison"] == _lire_batiment(copy.deepcopy(monde), cle, seconde[0]["intention"])
    # La caserne achevée, des départs nets sur la fenêtre : la grange.
    _bati(monde, cle, cid, "caserne")
    joueur = copy.deepcopy(monde)
    sans_ia = copy.deepcopy(monde)
    tout = _jouer_l_ia(monde, maisons)
    releve = [e for e in tout if e["intention"]["type"] == "batir_dans_une_province" and e["intention"]["maison"] == cle]
    assert [(e["intention"]["nature"], e["raison"]["regle"]) for e in releve] == [
        ("grange", "grange_quand_les_gens_partent")] and "refus" not in releve[0]
    assert releve[0]["intention"] == _batir("grange", cid, cle)
    raison = releve[0]["raison"]
    assert raison["partis_30j"] > raison["arrives_30j"] > 0
    assert raison == _lire_batiment(sans_ia, cle, releve[0]["intention"])
    lectures = {(t, cle): raison}
    _controler_raisons_du_pays(releve, lectures)
    # Le joueur qui dépose les mêmes intentions obtient le même monde, octet pour octet.
    for entree in tout:
        if "refus" not in entree:
            recevoir_intention(joueur, entree["intention"])
    alea_joueur = copy.deepcopy(rng)
    engine.tick(monde, rng, t)
    engine.tick(joueur, alea_joueur, t)
    _memes_octets(monde, joueur)
    # Contre-épreuve : un foyer de plus dans la raison de la grange, et le contrôleur le voit.
    faux = copy.deepcopy(releve)
    faux[0]["raison"]["partis_30j"] += 1
    with pytest.raises(AssertionError):
        _controler_raisons_du_pays(faux, lectures)

    # Le moulin et la grange achevés : le marché, si la province commerce.
    monde, rng, maisons, grande, cle = _au_jour_de_sa_part(depart)
    _bati(monde, cle, cid, "moulin")
    _bati(monde, cle, cid, "caserne")
    _bati(monde, cle, cid, "grange")
    joueur = copy.deepcopy(monde)
    sans_ia = copy.deepcopy(monde)
    tout = _jouer_l_ia(monde, maisons)
    releve = [e for e in tout if e["intention"]["type"] == "batir_dans_une_province" and e["intention"]["maison"] == cle]
    assert [(e["intention"]["nature"], e["raison"]["regle"]) for e in releve] == [
        ("marche", "marche_quand_la_province_commerce")] and "refus" not in releve[0]
    raison = releve[0]["raison"]
    assert raison["commerce_30j_kg"] > 0
    assert raison == _lire_batiment(sans_ia, cle, releve[0]["intention"])
    lectures = {(t, cle): raison}
    _controler_raisons_du_pays(releve, lectures)
    for entree in tout:
        if "refus" not in entree:
            recevoir_intention(joueur, entree["intention"])
    alea_joueur = copy.deepcopy(rng)
    engine.tick(monde, rng, t)
    engine.tick(joueur, alea_joueur, t)
    _memes_octets(monde, joueur)
    # Contre-épreuve : un kilo de commerce de plus dans la raison du marché, et le contrôleur le voit.
    faux = copy.deepcopy(releve)
    faux[0]["raison"]["commerce_30j_kg"] += 1
    with pytest.raises(AssertionError):
        _controler_raisons_du_pays(faux, lectures)


def test_l_ia_ne_propose_rien_pendant_un_chantier_ni_sans_raison(depart):
    monde, rng, maisons, grande, cle = _au_jour_de_sa_part(depart)
    cid = grande.cell_id
    _bati(monde, cle, cid, "moulin")
    _bati(monde, cle, cid, "caserne")
    # Un chantier de province en cours : un chantier à la fois.
    en_cours = copy.deepcopy(monde)
    B.poser(en_cours, cle, cid, "grange")
    assert _proposees(en_cours, maisons, cle) == []
    # Sans départ net, la grange n'a pas sa raison ; le marché est le suivant.
    sans_depart = copy.deepcopy(monde)
    partis = sans_depart.flux.jours
    for jour in partis.values():
        jour.partis, jour.arrives = {}, {}
    assert [e["intention"]["nature"] for e in _proposees(sans_depart, maisons, cle)] == ["marche"]
    # Sans commerce non plus, avec la grange bâtie : rien.
    sans_commerce = copy.deepcopy(sans_depart)
    _bati(sans_commerce, cle, cid, "grange")
    for jour in sans_commerce.flux.jours.values():
        jour.commerce = {}
    assert _proposees(sans_commerce, maisons, cle) == []
