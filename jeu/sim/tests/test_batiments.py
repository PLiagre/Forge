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
import random
import tomllib

import pytest

import sim.constants as c
from sim import batiments as B, engine, modificateurs as M
from sim.intentions import IntentionRefusee, recevoir_intention
from sim.model import lire_habitants_par_metier, lire_ouvriers_du_jour
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
