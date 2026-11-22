"""La guerre (`sim/guerre.py`, `data/guerre.toml`) : les données, les cinq gestes et leurs refus.

- Les données : des taux et des jours de niveau 2, et un bâtiment de levée qui
  existe parmi les bâtiments de province ; une donnée qui ne tient pas se refuse.
- Le refus : sans caserne achevée dans sa capitale tenue, la levée est refusée
  et dit pourquoi ; avec elle, la même levée passe.
- La part : un lieu ne donne pas plus que sa part de ses habitants sous les
  armes, levées déjà déposées comprises ; le modificateur « levee » la change.
- La conservation : la levée retire les hommes des lieux et des paysans et les
  vivres du grenier, le renvoi les rend ; personne ni aucun kilo ne se crée.
"""
import copy
import json
import math
import random
import re
import tomllib

import pytest

import sim.constants as c
from sim import batiments as B, engine, guerre as G, modificateurs as M
from sim.intentions import IntentionRefusee, grain_libre, recevoir_intention
from sim.model import lire_habitants_par_metier
from sim.world import World

NOURRITURE = c.MARCHANDISE_NOURRITURE
BAR = "seigneurie-1"


@pytest.fixture(scope="module")
def depart():
    return World.charger(rng_seed=0)


@pytest.fixture
def regles():
    return G.charger_regles()


def _capitale(monde, maison=BAR):
    return next(m for m in monde.maisons if m.id == maison).cell_id


def _avec_caserne(depart, maison=BAR, grain=20000.0):
    """Le monde de départ, une caserne achevée dans la capitale de la maison et du grain au grenier."""
    monde = copy.deepcopy(depart)
    cid = _capitale(monde, maison)
    regles = G.charger_regles()
    journees = B.charger_types()[regles.batiment_de_levee].journees
    monde.batiments_de_province = [B.BatimentDeProvince(0, regles.batiment_de_levee, cid, maison, journees, journees,
                                                        False, 0, 0)]
    monde.greniers[maison][NOURRITURE] = grain
    return monde


def _levee(cid, hommes=None, maison=BAR, vivres=500.0):
    """La levée de `hommes` (rang → hommes ; dix au bourg et cinq au rang 1 sans eux) dans la cellule `cid`."""
    hommes = {0: 10, 1: 5} if hommes is None else hommes
    return {"type": "lever_armee", "maison": maison, "lieux": [[cid, rang, n] for rang, n in sorted(hommes.items())],
            "vivres_kg": vivres}


def _voisine(monde, cid):
    """La première voisine terrestre, par cell_id, et le maître de son bourg."""
    voisines = sorted({e["b"] if e["a"] == cid else e["a"] for e in monde.adjacency
                       if cid in (e["a"], e["b"]) and e["a"] in monde.cells and e["b"] in monde.cells})
    assert voisines, f"cellule {cid} sans voisine terrestre : échantillon vide"
    return voisines[0], monde.cells[voisines[0]].lieux[0].maitre


def _appliquer(monde):
    engine._appliquer_intentions(monde)


def _comptes(monde):
    """Les habitants des lieux et des cellules, les paysans et le grain des greniers, armées comprises."""
    lieux = sum(l.population for cel in monde.cells.values() for l in cel.lieux)
    cellules = sum(cel.population for cel in monde.cells.values())
    paysans = sum(lire_habitants_par_metier(cel).get(c.METIER_PAYSANS, 0) for cel in monde.cells.values())
    soldats = sum(a.hommes for a in monde.armees)
    grain = math.fsum(p.get(NOURRITURE, 0.0) for p in monde.greniers.values())
    vivres = math.fsum(a.vivres_kg for a in monde.armees)
    return {"habitants": lieux + soldats, "cellules": cellules + soldats, "paysans": paysans + soldats,
            "grain": grain + vivres}


# --- Les données -------------------------------------------------------------

def test_les_regles_viennent_des_donnees(regles):
    with open(G._CHEMIN, "rb") as fichier:
        brut = tomllib.load(fichier)
    assert regles == G.Regles(brut["levee"]["part_maximale"], brut["levee"]["batiment"], brut["marche"]["km_par_jour"],
                              brut["vivres"]["ration_kg_par_homme_par_jour"], brut["vivres"]["part_prise_par_jour"],
                              brut["siege"]["jours_de_faim_avant_la_chute"], brut["ia"]["jours_de_marche_max"],
                              brut["ia"]["jours_de_siege_voulus"], brut["ia"]["hommes_minimum"])
    caserne = B.charger_types()[regles.batiment_de_levee]
    assert caserne.modificateurs == () and caserne.pieces == 0 and caserne.un_par_cellule
    assert M.charger_donnees().grandeurs[G.GRANDEUR_LEVEE].lue


@pytest.mark.parametrize("chemin, valeur, motif", [
    (("levee", "part_maximale"), 0, "part_maximale"),
    (("levee", "part_maximale"), 1.5, "part_maximale"),
    (("levee", "part_maximale"), True, "nombre fini"),
    (("levee", "batiment"), "donjon", "absent des bâtiments"),
    (("marche", "km_par_jour"), -2, "km_par_jour"),
    (("vivres", "part_prise_par_jour"), 2, "part_prise_par_jour"),
    (("siege", "jours_de_faim_avant_la_chute"), 0, "entier au moins égal à 1"),
    (("siege", "jours_de_faim_avant_la_chute"), 2.5, "entier au moins égal à 1"),
    (("ia", "jours_de_marche_max"), 0, "entier au moins égal à 1"),
    (("ia", "hommes_minimum"), True, "entier au moins égal à 1"),
    (("vivres", "kg"), 100, "champs"),
    (("solde", "pieces"), 3, "section inconnue"),
])
def test_une_donnee_qui_ne_tient_pas_est_refusee(chemin, valeur, motif):
    with open(G._CHEMIN, "rb") as fichier:
        document = tomllib.load(fichier)
    document.setdefault(chemin[0], {})[chemin[1]] = valeur
    with pytest.raises(G.GuerreInvalide, match=motif):
        G.lire_regles(document)
    # Contre-épreuve : le document du dépôt passe.
    assert G.charger_regles().batiment_de_levee == "caserne"


# --- Le refus sans caserne -------------------------------------------------------

def test_sans_caserne_achevee_la_levee_est_refusee_et_dit_pourquoi(depart):
    monde = copy.deepcopy(depart)
    cid = _capitale(monde)
    monde.greniers[BAR][NOURRITURE] = 20000.0
    with pytest.raises(IntentionRefusee, match="^la levée est fermée : aucune caserne achevée dans votre capitale$"):
        recevoir_intention(monde, _levee(cid))
    # Une caserne en chantier ne l'ouvre pas encore.
    journees = B.charger_types()["caserne"].journees
    monde.batiments_de_province = [B.BatimentDeProvince(0, "caserne", cid, BAR, journees, journees - 1, True, 0)]
    with pytest.raises(IntentionRefusee, match="aucune caserne achevée"):
        recevoir_intention(monde, _levee(cid))
    assert monde.intentions_en_attente == []
    # Son dernier jour de chantier l'achève : la même levée passe.
    engine.tick(monde, random.Random(0), monde.ticks_ecoules)
    assert not monde.batiments_de_province[0].en_chantier
    geste = recevoir_intention(monde, _levee(cid))
    assert monde.intentions_en_attente == [geste]


def test_une_capitale_qui_n_est_plus_tenue_ferme_la_levee(depart):
    monde = _avec_caserne(depart)
    cid = _capitale(monde)
    recevoir_intention(monde, _levee(cid))
    monde.intentions_en_attente.clear()
    monde.cells[cid].lieux[0].maitre = "grande-3"
    with pytest.raises(IntentionRefusee, match="^la levée est fermée : le bourg de votre capitale n'est plus à vous$"):
        recevoir_intention(monde, _levee(cid))


# --- La part et les autres refus ----------------------------------------------------

def test_un_lieu_ne_donne_que_sa_part(depart, regles):
    monde = _avec_caserne(depart)
    cid = _capitale(monde)
    lieu = monde.cells[cid].lieux[1]
    maximum = math.floor(regles.part_maximale_levee * lieu.population)
    assert maximum > 0 and G.levee_maximale(monde, cid, 1, regles) == maximum
    with pytest.raises(IntentionRefusee, match=f"peut en donner {G.ecrire_nombre(maximum)} hommes, "
                                               f"{G.ecrire_nombre(maximum + 1)} hommes demandés \\(au plus 10 %"):
        recevoir_intention(monde, _levee(cid, {1: maximum + 1}))
    recevoir_intention(monde, _levee(cid, {1: maximum - 3}, vivres=0))
    # Une levée déjà déposée compte : il ne reste que trois hommes à ce lieu.
    with pytest.raises(IntentionRefusee, match="peut en donner 3 hommes, 4 hommes demandés"):
        recevoir_intention(monde, _levee(cid, {1: 4}, vivres=0))
    recevoir_intention(monde, _levee(cid, {1: 3}, vivres=0))
    _appliquer(monde)
    # Levés, ils comptent encore dans la part : le lieu ne donne plus rien.
    assert G.levee_maximale(monde, cid, 1, regles) == 0
    # Le modificateur « levee » du lieu change la part.
    donnees = M.charger_donnees()
    definition = M.Definition("epreuve", "Épreuve", G.GRANDEUR_LEVEE, 0.5, "cellule", 0)
    M.poser(monde, "epreuve", "loi:levee", {"cellule": cid},
            M.Donnees(donnees.sources, donnees.grandeurs, {**donnees.definitions, "epreuve": definition}))
    leves = maximum
    assert G.levee_maximale(monde, cid, 1, regles) == math.floor(
        regles.part_maximale_levee * 1.5 * (lieu.population + leves)) - leves > 0


def test_les_refus_des_gestes_de_guerre(depart):
    monde = _avec_caserne(depart, grain=1000.0)
    cid = _capitale(monde)
    voisine, cible = _voisine(monde, cid)
    autre = next(l for l in monde.cells[cid].lieux if l.maitre != BAR)
    cas = [
        ({"type": "lever_armee", "maison": BAR, "lieux": [], "vivres_kg": 0}, "liste non vide"),
        ({"type": "lever_armee", "maison": BAR, "lieux": [[cid, 0]], "vivres_kg": 0}, "entiers attendus"),
        ({"type": "lever_armee", "maison": BAR, "lieux": [[cid, 0, 0]], "vivres_kg": 0}, "au moins un homme"),
        ({"type": "lever_armee", "maison": BAR, "lieux": [[cid, 0, 1], [cid, 0, 2]], "vivres_kg": 0}, "deux fois"),
        (_levee(cid, vivres=-1), "vivres_kg invalide"),
        (_levee(cid, vivres=1000.5), "^grenier insuffisant : 1 000,5 kg de vivres demandés, 1 000 kg disponibles$"),
        ({"type": "lever_armee", "maison": BAR, "lieux": [[cid, autre.rang, 1]], "vivres_kg": 0},
         "^ce lieu n'est pas à vous$"),
        ({"type": "lever_armee", "maison": BAR, "lieux": [[cid, 99, 1]], "vivres_kg": 0},
         "^ce lieu n'existe pas sur la carte$"),
        ({"type": "declarer_guerre", "maison": BAR, "cible": BAR}, "à soi-même"),
        ({"type": "declarer_guerre", "maison": BAR, "cible": "maison-inventee"}, "cible inconnue"),
        ({"type": "declarer_guerre", "maison": "maison-inventee", "cible": cible}, "maison inconnue"),
        ({"type": "marcher", "maison": BAR, "armee": 0, "cell": voisine, "rang": 0}, "^cette armée n'existe plus$"),
        ({"type": "assieger", "maison": BAR, "armee": True}, "armée invalide"),
        ({"type": "renvoyer_armee", "maison": BAR, "armee": 7}, "^cette armée n'existe plus$"),
        ({"type": "lever_armee", "maison": BAR, "lieux": [[cid, 0, 1]], "vivres_kg": 0, "jour": 3}, "champ inconnu"),
        ({"type": "marcher", "maison": BAR, "armee": 0, "cell": voisine}, "champ manquant : rang"),
    ]
    for intention, motif in cas:
        with pytest.raises(IntentionRefusee, match=motif):
            recevoir_intention(monde, intention)
    assert monde.intentions_en_attente == []
    # Les paysans : une cellule sans paysans ne lève personne, même dans sa part.
    sans = copy.deepcopy(monde)
    metiers = lire_habitants_par_metier(sans.cells[cid])
    paysans = metiers.pop(c.METIER_PAYSANS)
    metiers[c.METIER_OUVRIERS] = paysans
    sans.cells[cid].habitants_par_metier = metiers
    with pytest.raises(IntentionRefusee, match="^pas assez de paysans : 15 hommes demandés sur cette terre, 0 paysans$"):
        recevoir_intention(sans, _levee(cid, vivres=0))


def test_la_guerre_se_declare_puis_l_armee_marche_et_assiege(depart):
    monde = _avec_caserne(depart)
    cid = _capitale(monde)
    voisine, cible = _voisine(monde, cid)
    recevoir_intention(monde, _levee(cid))
    _appliquer(monde)
    armee = monde.armees[0]
    assert (armee.identifiant, armee.maison, armee.cell_id, armee.rang) == (0, BAR, cid, 0)
    # L'armée n'assiège pas sa propre place, ni une place d'une maison avec qui elle n'est pas en guerre.
    with pytest.raises(IntentionRefusee, match="^cette place est à vous$"):
        recevoir_intention(monde, {"type": "assieger", "maison": BAR, "armee": 0})
    # Une autre maison ne commande pas l'armée de Bar.
    with pytest.raises(IntentionRefusee, match="^cette armée n'est pas à vous$"):
        recevoir_intention(monde, {"type": "renvoyer_armee", "maison": cible, "armee": 0})
    # Un seul geste par armée et par jour.
    recevoir_intention(monde, {"type": "marcher", "maison": BAR, "armee": 0, "cell": voisine, "rang": 0})
    with pytest.raises(IntentionRefusee, match="^un ordre est déjà donné à cette armée aujourd'hui$"):
        recevoir_intention(monde, {"type": "renvoyer_armee", "maison": BAR, "armee": 0})
    _appliquer(monde)
    armee = monde.armees[0]
    assert armee.destination == (voisine, 0) and armee.route == (voisine,)
    with pytest.raises(IntentionRefusee, match="^l'armée marche encore : elle assiège une fois arrivée$"):
        recevoir_intention(monde, {"type": "assieger", "maison": BAR, "armee": 0})
    # Arrivée (le maillon de la marche la pose là) : pas encore en guerre avec le maître.
    G._remplacer(monde, G.replace(armee, cell_id=voisine, rang=0, destination=None, route=()))
    with pytest.raises(IntentionRefusee, match="^vous n'êtes pas en guerre avec le maître de cette place$"):
        recevoir_intention(monde, {"type": "assieger", "maison": BAR, "armee": 0})
    recevoir_intention(monde, {"type": "declarer_guerre", "maison": BAR, "cible": cible})
    with pytest.raises(IntentionRefusee, match="^vous êtes déjà en guerre avec cette maison$"):
        recevoir_intention(monde, {"type": "declarer_guerre", "maison": cible, "cible": BAR})
    # La déclaration déposée vaut pour le siège déposé après elle.
    recevoir_intention(monde, {"type": "assieger", "maison": BAR, "armee": 0})
    _appliquer(monde)
    assert [g.en_document() for g in monde.guerres] == [
        {"identifiant": 0, "agresseur": BAR, "defenseur": cible, "debut": monde.ticks_ecoules}]
    assert monde.armees[0].siege == voisine
    with pytest.raises(IntentionRefusee, match="^l'armée assiège déjà cette place$"):
        recevoir_intention(monde, {"type": "assieger", "maison": BAR, "armee": 0})
    # Un lieu qui n'est pas un bourg n'est pas une place.
    G._remplacer(monde, G.replace(monde.armees[0], rang=1, siege=None))
    with pytest.raises(IntentionRefusee, match="^ce lieu n'est pas une place : l'armée n'est pas dans un bourg$"):
        recevoir_intention(monde, {"type": "assieger", "maison": BAR, "armee": 0})


def test_sans_chemin_terrestre_l_armee_ne_marche_pas(depart):
    monde = _avec_caserne(depart)
    cid = _capitale(monde)
    recevoir_intention(monde, _levee(cid))
    _appliquer(monde)
    terrestres = {x for e in monde.adjacency for x in (e["a"], e["b"])
                  if e["a"] in monde.cells and e["b"] in monde.cells}
    ile = min(set(monde.cells) - terrestres)
    with pytest.raises(IntentionRefusee, match="^aucun chemin terrestre jusqu'à ce lieu$"):
        recevoir_intention(monde, {"type": "marcher", "maison": BAR, "armee": 0, "cell": ile, "rang": 0})
    # Contre-épreuve : vers une voisine, la route existe.
    assert G.chemin(monde, cid, _voisine(monde, cid)[0]) is not None


# --- La conservation ------------------------------------------------------------

def _verifier_conservation(monde, avant):
    assert _comptes(monde) == avant


def test_la_levee_puis_le_renvoi_conservent_habitants_et_kilos(depart, monkeypatch):
    monde = _avec_caserne(depart)
    cid = _capitale(monde)
    avant, document_avant = _comptes(monde), monde.to_dict()
    lieux_avant = [l.population for l in monde.cells[cid].lieux]
    recevoir_intention(monde, _levee(cid, vivres=500.0))
    assert grain_libre(monde, BAR) == 20000.0 - 500.0
    # Le grenier ne paie pas deux fois : la seconde levée voit les vivres déjà engagés.
    with pytest.raises(IntentionRefusee, match="19 500 kg disponibles"):
        recevoir_intention(monde, _levee(cid, {2: 1}, vivres=19500.5))
    _appliquer(monde)
    armee = monde.armees[0]
    assert armee.effectifs == ((cid, 0, 10), (cid, 1, 5)) and armee.hommes == 15 and armee.vivres_kg == 500.0
    assert [l.population for l in monde.cells[cid].lieux] == [lieux_avant[0] - 10, lieux_avant[1] - 5,
                                                              *lieux_avant[2:]]
    assert monde.greniers[BAR][NOURRITURE] == 20000.0 - 500.0
    _verifier_conservation(monde, avant)
    document = monde.to_dict()
    assert document["armees"] == [armee.en_document()] and document["armees_levees"] == 1
    recevoir_intention(monde, {"type": "renvoyer_armee", "maison": BAR, "armee": 0})
    _appliquer(monde)
    # Tout revient au départ ; seul reste le compte des armées levées, qui numérote la suivante.
    document = monde.to_dict()
    assert monde.armees == [] and document.pop("armees_levees") == 1 and document == document_avant
    _verifier_conservation(monde, avant)
    # Contre-épreuve : une levée qui ne retire personne des foyers crée des hommes, et se voit.
    monkeypatch.setattr(G, "_changer_paysans", lambda cellule, ecart: None)
    faux = _avec_caserne(depart)
    monkeypatch.setattr(G, "lever", _lever_sans_retirer(G.lever))
    recevoir_intention(faux, _levee(cid))
    _appliquer(faux)
    assert faux.armees
    with pytest.raises(AssertionError):
        _verifier_conservation(faux, avant)


def _lever_sans_retirer(lever):
    """La levée qui forme l'armée sans toucher aux foyers : les lieux gardent leurs habitants."""
    def faux(monde, maison, lieux, vivres_kg):
        habitants = {(cid, rang): monde.cells[cid].lieux[rang].population for cid, rang, _h in lieux}
        armee = lever(monde, maison, lieux, vivres_kg)
        for (cid, rang), population in habitants.items():
            monde.cells[cid].lieux[rang].population = population
        return armee
    return faux


def test_sans_guerre_le_monde_garde_ses_octets(depart):
    monde = copy.deepcopy(depart)
    document = monde.to_dict()
    assert not {"guerres", "armees", "armees_levees", "prises", "morts_des_armees"} & set(document)
    engine.tick(monde, random.Random(0), 0)
    assert not {"guerres", "armees", "armees_levees", "prises", "morts_des_armees"} & set(monde.to_dict())


# --- Le maillon : la marche, le siège, la chute ------------------------------------

JOURS_DE_CAMPAGNE = 100  # la place sans réserve tombe vers le quarantième jour : l'horizon garde de la marge
JOURS_DE_RESERVE = 10  # ce qui reste au bourg de la place quand l'armée part : dix jours de ration
JOUR_DU_SECOURS = 15  # l'armée arrive devant la place vers le dixième jour : la maison visée la secourt après
SECOURS_KG = 5000.0


def _place_sans_reserve(monde, cid, jours=JOURS_DE_RESERVE):
    """Le bourg de la place ne garde que `jours` jours de ration ; sa cellule perd la même nourriture."""
    bourg, cellule = monde.cells[cid].lieux[0], monde.cells[cid]
    garde = bourg.population * c.FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK * jours
    ecart = bourg.stocks[NOURRITURE] - garde
    assert ecart > 0, "la place a déjà moins que sa réserve : échantillon vide"
    bourg.stocks[NOURRITURE] = garde
    cellule.stocks[NOURRITURE] -= ecart


def _recu_du_jour(monde, cid, tick):
    jour = monde.flux.jours.get(tick)
    return 0.0 if jour is None else math.fsum(kg for (_a, b), kg in jour.commerce.items() if b == cid)


def _campagne(depart, assieger=True, ravitailler=False, renvoyer=True, jours=JOURS_DE_CAMPAGNE):
    """Bar lève deux mille hommes, déclare la guerre au maître de sa première voisine, y marche et l'assiège.

    La place n'a que dix jours de ration ; au jour du secours, la maison visée ouvre son grenier pour ses
    lieux. Chaque jour, on relève l'identité des habitants : les lieux,
    les soldats, leurs morts, les morts et les naissances ordinaires (mesurés autour des maillons du
    moteur), qui doit rendre les habitants d'avant. `ravitailler` : chaque jour, la place reçoit
    exactement ce que ses habitants mangent. `renvoyer` : la place prise, l'armée rentre.
    """
    monde = _avec_caserne(depart, grain=200000.0)
    cid = _capitale(monde)
    voisine, cible = _voisine(monde, cid)
    _place_sans_reserve(monde, voisine)
    monde.greniers[cible][NOURRITURE] = 4 * SECOURS_KG
    ordinaires = {"morts": 0, "naissances": 0}
    mortalite, natalite = engine._apply_mortality, engine._apply_natalite

    def compter(original, cle, signe):
        def mesure(cellule, *args):
            avant = cellule.population
            original(cellule, *args)
            ordinaires[cle] += signe * (cellule.population - avant)
        return mesure

    def total(m):
        lieux = sum(l.population for cel in m.cells.values() for l in cel.lieux)
        assert lieux == sum(cel.population for cel in m.cells.values())
        return (lieux + sum(a.hommes for a in m.armees) + m.morts_des_armees
                + ordinaires["morts"] - ordinaires["naissances"])

    releve = {"identites": [], "recus": [], "secourus": [], "assiegee": [], "prise": None, "renvoi": None, "voisine": voisine,
              "cible": cible, "rangs_de_la_cible": [l.rang for l in monde.cells[voisine].lieux if l.maitre == cible]}
    avant = total(monde)
    rng = random.Random(0)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(engine, "_apply_mortality", compter(mortalite, "morts", -1))
        patch.setattr(engine, "_apply_natalite", compter(natalite, "naissances", 1))
        livrer, livres = engine.prelevement._livrer_secours, {}

        def relever_les_secours(m, charges):
            livres[m.ticks_ecoules] = charges.get((voisine, 0), 0.0)
            return livrer(m, charges)

        patch.setattr(engine.prelevement, "_livrer_secours", relever_les_secours)
        recevoir_intention(monde, _levee(cid, {r: 500 for r in range(4)}, vivres=20000.0))
        for numero in range(jours):
            if numero == 1:
                recevoir_intention(monde, {"type": "declarer_guerre", "maison": BAR, "cible": cible})
                recevoir_intention(monde, {"type": "marcher", "maison": BAR, "armee": 0, "cell": voisine, "rang": 0})
            armee = monde.armees[0] if monde.armees else None
            if (assieger and armee is not None and armee.destination is None and armee.siege is None
                    and armee.cell_id == voisine and releve["prise"] is None):
                recevoir_intention(monde, {"type": "assieger", "maison": BAR, "armee": 0})
            if renvoyer and releve["prise"] is not None and monde.armees and releve["renvoi"] is None:
                recevoir_intention(monde, {"type": "renvoyer_armee", "maison": BAR, "armee": 0})
                releve["renvoi"] = numero
            if numero == JOUR_DU_SECOURS:
                recevoir_intention(monde, {"type": "ouvrir_grenier", "maison": cible, "kg": SECOURS_KG})
            if ravitailler:
                bourg, cellule = monde.cells[voisine].lieux[0], monde.cells[voisine]
                ration = bourg.population * c.FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
                bourg.stocks[NOURRITURE] += ration
                cellule.stocks[NOURRITURE] += ration
            engine.tick(monde, rng, numero)
            releve["identites"].append(total(monde) == avant)
            releve["recus"].append(_recu_du_jour(monde, voisine, numero))
            releve["secourus"].append(livres.get(numero, 0.0))
            releve["assiegee"].append(voisine in G.places_assiegees(monde))
            if monde.prises and releve["prise"] is None:
                releve["prise"] = numero
            if releve["renvoi"] is not None and numero > releve["renvoi"]:
                break
    releve["monde"] = monde
    return releve


@pytest.fixture(scope="module")
def campagne(depart):
    return _campagne(depart)


def test_les_habitants_se_conservent_de_la_levee_au_renvoi(campagne, depart, monkeypatch):
    monde = campagne["monde"]
    assert campagne["prise"] is not None and campagne["renvoi"] is not None and monde.armees == []
    assert campagne["identites"] and all(campagne["identites"])
    assert monde.morts_des_armees > 0, "aucun mort sous les armes : la conservation n'éprouve pas les morts"
    # Contre-épreuve : une levée qui ne retire personne des foyers crée des hommes, et se voit dès le premier jour.
    monkeypatch.setattr(G, "lever", _lever_sans_retirer(G.lever))
    monkeypatch.setattr(G, "_changer_paysans", lambda cellule, ecart: None)
    faux = _campagne(depart, assieger=False, jours=3)
    assert faux["identites"] and not any(faux["identites"])


def test_la_place_assiegee_ne_recoit_rien_et_tombe(campagne, depart):
    monde, voisine, cible = campagne["monde"], campagne["voisine"], campagne["cible"]
    jours = [n for n, assiegee in enumerate(campagne["assiegee"]) if assiegee]
    assert jours, "aucun jour de siège : échantillon vide"
    assert JOUR_DU_SECOURS in jours, "le secours ne part pas pendant le siège : échantillon vide"
    assert all(campagne["recus"][n] == 0.0 and campagne["secourus"][n] == 0.0 for n in jours)
    # Le témoin : la même place, la même armée qui ne l'assiège pas, reçoit le secours de sa maison.
    temoin = _campagne(depart, assieger=False, jours=jours[-1] + 1)
    assert temoin["prise"] is None and any(temoin["secourus"][n] > 0 for n in jours)
    # Le siège tenu, la place ne reçoit ni n'envoie rien par ses frontières ni par la mer.
    ravitaillee = _campagne(depart, ravitailler=True, renvoyer=False, jours=jours[0] + 2)
    assiegee = ravitaillee["monde"]
    assert voisine in G.places_assiegees(assiegee)
    capacites = engine._initialiser_capacite_aretes(assiegee)
    ouvertes = dict(capacites)
    engine._fermer_les_places(assiegee, capacites, None)
    touchees = [cle for cle in engine._aretes_par_cellule(assiegee)[voisine] if cle in capacites]
    assert touchees and all(capacites[cle] == 0.0 for cle in touchees) and any(ouvertes[cle] > 0 for cle in touchees)
    assert all(capacites[cle] == ouvertes[cle] for cle in capacites if cle not in touchees)
    # Elle est tombée : ses lieux tenus par la maison visée sont à Bar, la prise est notée.
    prise = monde.prises[0]
    assert (prise["cell_id"], prise["de"], prise["a"], prise["rangs"]) == (voisine, cible, BAR,
                                                                           campagne["rangs_de_la_cible"])
    assert all(monde.cells[voisine].lieux[r].maitre == BAR for r in prise["rangs"])
    assert all(monde.routes_des_lieux[voisine, r].maitre == BAR for r in prise["rangs"])
    # Le prélèvement de ces lieux part désormais vers le grenier de Bar.
    indices = monde.routes_des_lieux.par_cellule[voisine][0]
    assert {indices[r] for r in prise["rangs"]} == {monde.routes_des_lieux.noms.index(BAR)}


def test_la_place_ravitaillee_ne_tombe_pas(campagne, depart):
    ravitaillee = _campagne(depart, ravitailler=True, renvoyer=False)
    assert any(ravitaillee["assiegee"]) and ravitaillee["prise"] is None
    assert len(ravitaillee["assiegee"]) > campagne["prise"] + _regles_du_depot().jours_de_faim_avant_la_chute
    assert ravitaillee["monde"].cells[campagne["voisine"]].lieux[0].maitre == campagne["cible"]


def _regles_du_depot():
    return G.charger_regles()


def _lieu_aux_bras_justes(monde, juillet, regles):
    """Le premier lieu, par (cell_id, rang), d'une maison qui tient le bourg de sa capitale, dont les paysans
    suffisent à la moisson de juillet et ne suffisent plus une fois sa part levée."""
    from sim import foyers, lieux as L
    capitales = {m.id: m.cell_id for m in monde.maisons if m.cell_id is not None}
    for cid, cellule in sorted(monde.cells.items()):
        carte = monde.carte
        km2 = (cellule.area_km2 * engine._facteur_relief_pour_cellule(cellule, carte)
               * engine._facteur_eau_pour_cellule(cellule, carte) * engine._facteur_agricole(cellule, carte)
               * engine._facteur_saison_pour_cellule(cellule, carte, c.jour_de_tick(juillet)))
        besoin_par_km2 = foyers.besoin_bras(km2 / cellule.area_km2)
        surfaces = L.surfaces_des_lieux(cid, cellule.area_km2)
        for lieu in cellule.lieux[1:]:
            capitale = capitales.get(lieu.maitre)
            if capitale is None or monde.cells[capitale].lieux[0].maitre != lieu.maitre:
                continue
            besoin = surfaces[lieu.rang] * besoin_par_km2
            leves = G.levee_maximale(monde, cid, lieu.rang, regles)
            if lieu.population >= besoin > lieu.population - leves:
                return cid, lieu.rang, lieu.maitre, leves
    return None


def test_un_lieu_leve_en_juillet_recolte_moins_que_son_temoin(depart, regles, monkeypatch):
    juillet = next(n for n in range(c.CALENDAR_DAYS_PER_YEAR) if c.date_de_tick(n)["jour_de_l_annee"] > 181)
    choisi = _lieu_aux_bras_justes(depart, juillet, regles)
    assert choisi is not None, "aucun lieu aux bras justes : échantillon vide"
    cid, rang, maison, hommes = choisi
    recoltes = {}
    prelever = engine.prelevement.prelever

    def relever(monde, recoltes_du_jour):
        recoltes[id(monde)] = recoltes_du_jour[cid][rang]
        return prelever(monde, recoltes_du_jour)

    monkeypatch.setattr(engine.prelevement, "prelever", relever)
    mondes = []
    for lever in (False, True):
        monde = _avec_caserne(depart, maison)
        monde.ticks_ecoules = juillet
        if lever:
            recevoir_intention(monde, {"type": "lever_armee", "maison": maison, "lieux": [[cid, rang, hommes]],
                                       "vivres_kg": 0})
        engine.tick(monde, random.Random(0), juillet)
        mondes.append(monde)
    temoin, leve = (recoltes[id(m)] for m in mondes)
    assert mondes[1].armees and mondes[1].armees[0].hommes == hommes
    print(f"lieu {(cid, rang)} de {maison} : {hommes} levés, récolte {leve:.1f} kg contre {temoin:.1f} au témoin")
    assert 0 < leve < temoin


# --- La photographie et le service portent la guerre ----------------------------------

def test_photographie_porte_les_armees_levees_et_se_tait_sans_guerre(depart):
    from sim.snapshot_export import build_snapshot_document, serialize_snapshot
    sans = build_snapshot_document(depart, 0, depart.ticks_ecoules)
    assert not {"guerres", "armees", "prises"} & set(sans)
    assert serialize_snapshot(sans) == serialize_snapshot(
        build_snapshot_document(copy.deepcopy(depart), 0, depart.ticks_ecoules))

    monde = _avec_caserne(depart)
    cid = _capitale(monde)
    recevoir_intention(monde, _levee(cid))
    engine._appliquer_intentions(monde)
    photographie = build_snapshot_document(monde, 0, monde.ticks_ecoules)
    assert photographie["armees"] == G.document_de_la_guerre(monde)["armees"]
    (armee,) = photographie["armees"]
    assert armee["effectifs"] == [[cid, 0, 10], [cid, 1, 5]] and armee["hommes"] == 15
    assert "guerres" not in photographie and "prises" not in photographie


def test_service_sert_les_guerres_et_refuse_les_gestes_d_une_autre_maison():
    import json
    from sim.tests.test_monde import _service_epreuve, requete_service

    def poster(port, corps):
        return requete_service(port, "/intention", "POST", json.dumps(corps).encode())

    with _service_epreuve() as (serveur, port):
        statut, document, _ = requete_service(port, "/guerres")
        assert statut == 200 and document == {
            "tick": 0, "date": c.date_de_tick(0), "guerres": [], "armees": [], "prises": [], "morts_des_armees": 0}

        cible = "seigneurie-2"
        declaration = {"type": "declarer_guerre", "maison": BAR, "cible": cible}
        statut, refus, _ = poster(port, declaration)
        assert statut == 400 and refus == {
            "acceptee": False, "erreur": "départ non appliqué : choisir une terre avant de faire la guerre"}
        assert serveur.world.intentions_en_attente == []

        assert poster(port, {"type": "choisir_depart", "seigneurie": 1})[0] == 200
        assert requete_service(port, "/tick?n=1", "POST")[0] == 200
        assert serveur.world.maison_du_joueur == BAR

        statut, refus, _ = poster(port, {"type": "declarer_guerre", "maison": cible, "cible": BAR})
        assert statut == 400 and refus == {
            "acceptee": False, "erreur": "maison interdite : seule la maison du joueur fait ses guerres"}
        assert serveur.world.intentions_en_attente == [] and serveur.world.guerres == []

        statut, recu, _ = poster(port, declaration)
        assert statut == 200 and recu["acceptee"] is True
        assert requete_service(port, "/tick?n=1", "POST")[0] == 200
        document = requete_service(port, "/guerres")[1]
        assert [(g["agresseur"], g["defenseur"]) for g in document["guerres"]] == [(BAR, cible)]


# --- Ce que l'écran lit : les refus, le devis, les terres --------------------------------

# Les deux juges de l'écran (`TexteDuMonde.Interdit` et `SansUnite`, côté Unity), dans les mêmes termes :
# un mot de mise au point ou un identifiant de lieu, et un nombre sans unité ni place dans une date.
_MOT_INTERDIT = re.compile(r"(?<!\w)(?:cellule|rang|ticks?)(?!\w)", re.IGNORECASE)
_IDENTIFIANT_DE_LIEU = re.compile(r"(?<![^\W_])[0-9]+-[0-9]+(?![^\W_])")
_NOMBRE_ECRIT = re.compile(r"(?<![^\W_])(?:[0-9]{1,3}(?:[   ][0-9]{3})+(?![0-9])|[0-9]+)(?:,[0-9]+)?")
_UNITE = re.compile(r"[  ]?(?:kg|t|%|jours?|ans?|habitants?|foyers?|personnes?|bras|lieux?|maisons?|chantiers?"
                    r"|km|m|points?|hommes?|paysans?)(?![^\W\d_])", re.IGNORECASE)
_DATE_ECRITE = re.compile(r"(?<![^\W_])jour[  ]([0-9]+)[  ]de[  ]([0-9]+)", re.IGNORECASE)


def _illisible(texte, *identifiants):
    """Ce que l'écran refuserait de montrer dans `texte`, ou None : le premier mot interdit, sinon le premier
    nombre sans unité."""
    trouves = [m for m in (_MOT_INTERDIT.search(texte), _IDENTIFIANT_DE_LIEU.search(texte)) if m]
    trouves += [m for i in identifiants if (m := re.search(rf"(?<!\w){re.escape(i)}(?!\w)", texte))]
    if trouves:
        return min(trouves, key=lambda m: m.start()).group()
    dates = {(m.start(g), m.end(g)) for m in _DATE_ECRITE.finditer(texte) for g in (1, 2)}
    for n in _NOMBRE_ECRIT.finditer(texte):
        if (n.start(), n.end()) not in dates and not _UNITE.match(texte, n.end()):
            return n.group()
    return None


def _refus(monde, intention):
    """Le refus que le dépôt rend à l'intention, ou None s'il l'accepte ; le monde est rendu tel quel."""
    attente = list(monde.intentions_en_attente)
    try:
        recevoir_intention(monde, intention)
        return None
    except IntentionRefusee as refus:
        return str(refus)
    finally:
        monde.intentions_en_attente[:] = attente


def test_les_refus_de_guerre_se_lisent_au_joueur(depart):
    monde = _avec_caserne(depart, grain=1000.0)
    cid = _capitale(monde)
    voisine, cible = _voisine(monde, cid)
    autre = next(l for l in monde.cells[cid].lieux if l.maitre != BAR)
    sans_caserne = copy.deepcopy(depart)
    refus = [
        _refus(sans_caserne, _levee(cid)),
        _refus(monde, _levee(cid, vivres=1000.5)),
        _refus(monde, _levee(cid, {1: 10 ** 6})),
        _refus(monde, {"type": "lever_armee", "maison": BAR, "lieux": [[cid, autre.rang, 1]], "vivres_kg": 0}),
        _refus(monde, {"type": "lever_armee", "maison": BAR, "lieux": [[cid, 99, 1]], "vivres_kg": 0}),
        _refus(monde, {"type": "marcher", "maison": BAR, "armee": 0, "cell": voisine, "rang": 0}),
    ]
    recevoir_intention(monde, _levee(cid, vivres=0))
    _appliquer(monde)
    refus += [
        _refus(monde, {"type": "assieger", "maison": BAR, "armee": 0}),
        _refus(monde, {"type": "renvoyer_armee", "maison": cible, "armee": 0}),
        _refus(monde, {"type": "marcher", "maison": BAR, "armee": 0, "cell": cid, "rang": 0}),
    ]
    G._remplacer(monde, G.replace(monde.armees[0], cell_id=voisine, rang=0))
    refus.append(_refus(monde, {"type": "assieger", "maison": BAR, "armee": 0}))
    recevoir_intention(monde, {"type": "declarer_guerre", "maison": BAR, "cible": cible})
    refus += [_refus(monde, {"type": "declarer_guerre", "maison": BAR, "cible": cible}),
              _refus(monde, {"type": "renvoyer_armee", "maison": BAR, "armee": 0}) or "accepté"]
    recevoir_intention(monde, {"type": "renvoyer_armee", "maison": BAR, "armee": 0})
    refus.append(_refus(monde, {"type": "assieger", "maison": BAR, "armee": 0}))
    assert refus.pop(-2) == "accepté" and all(refus) and len(set(refus)) == len(refus), refus
    identifiants = (BAR, cible, autre.maitre, str(cid), str(voisine))
    assert [(r, _illisible(r, *identifiants)) for r in refus if _illisible(r, *identifiants)] == []
    # Contre-épreuve : les textes d'avant montraient la cellule, la maison ou un nombre nu ; le juge les voit.
    anciens = [f"la levée est fermée : aucune caserne achevée dans la capitale (cellule {cid})",
               f"trop d'hommes : ({cid}, 1) peut en donner 42, 43 demandés",
               "grenier insuffisant : 1000.5 kg de vivres demandés, 1000 kg disponibles",
               f"déjà en guerre avec {cible}", "armée inconnue : 7"]
    assert all(_illisible(a, *identifiants) for a in anciens)


def test_le_devis_dit_le_refus_du_depot(depart, regles):
    sans_caserne = copy.deepcopy(depart)
    cid = _capitale(sans_caserne)
    voisine, cible = _voisine(sans_caserne, cid)
    devis = G.devis_des_ordres(sans_caserne, BAR)
    # Sans armée ni terre visée : la levée seule, fermée avec la raison du dépôt.
    assert devis["cible"] is None and devis["armees"] == []
    assert devis["levee"]["refus"] == _refus(sans_caserne, _levee(cid)) is not None

    monde = _avec_caserne(depart)
    avant, attente = monde.to_dict(), list(monde.intentions_en_attente)
    devis = G.devis_des_ordres(monde, BAR, voisine)
    assert monde.to_dict() == avant and monde.intentions_en_attente == attente, "le devis a écrit au monde"
    levee = devis["levee"]
    assert levee["refus"] is None and levee["grain_libre_kg"] == grain_libre(monde, BAR) == 20000.0
    assert levee["ration_kg_par_homme_par_jour"] == regles.ration_kg_par_homme_par_jour
    assert [(l["cell_id"], l["rang"]) for l in levee["lieux"]] == [
        (cid, l.rang) for l in monde.cells[cid].lieux if l.maitre == BAR] and levee["lieux"]
    # Le maximum servi de chaque lieu passe au dépôt, un homme de plus non.
    for lieu in levee["lieux"]:
        n = lieu["hommes_max"]
        assert n == min(levee["paysans"], G.levee_maximale(monde, cid, lieu["rang"], regles)) > 0
        assert _refus(monde, _levee(cid, {lieu["rang"]: n}, vivres=0)) is None
        assert _refus(monde, _levee(cid, {lieu["rang"]: n + 1}, vivres=0)) is not None
    # Une levée déposée compte dans le devis comme au dépôt.
    rang = levee["lieux"][0]["rang"]
    recevoir_intention(monde, _levee(cid, {rang: levee["lieux"][0]["hommes_max"]}, vivres=500.0))
    suivant = G.devis_des_ordres(monde, BAR)["levee"]
    assert suivant["lieux"][0]["hommes_max"] == 0 and suivant["grain_libre_kg"] == 19500.0
    # La déclaration vise le maître du bourg de la terre ; déposée, la seconde est refusée par les deux.
    assert devis["cible"] == {"cell_id": voisine, "maitre": cible, "declaration": {"refus": None}}
    declaration = {"type": "declarer_guerre", "maison": BAR, "cible": cible}
    assert _refus(monde, declaration) is None
    recevoir_intention(monde, declaration)
    assert G.devis_des_ordres(monde, BAR, voisine)["cible"]["declaration"]["refus"] == _refus(monde, declaration)
    assert G.devis_des_ordres(monde, BAR, cid)["cible"]["declaration"]["refus"] == _refus(
        monde, {"type": "declarer_guerre", "maison": BAR, "cible": BAR}) is not None
    _appliquer(monde)

    # Une armée : sa marche, son siège et son renvoi, chacun avec le refus du dépôt.
    (armee,) = G.devis_des_ordres(monde, BAR, voisine)["armees"]
    gestes = {"assieger": {"type": "assieger", "maison": BAR, "armee": armee["identifiant"]},
              "renvoyer": {"type": "renvoyer_armee", "maison": BAR, "armee": armee["identifiant"]}}
    marcher = {"type": "marcher", "maison": BAR, "armee": armee["identifiant"], "cell": voisine, "rang": 0}
    assert armee["marche"]["refus"] is None and _refus(monde, marcher) is None
    assert armee["marche"]["route"] == list(G.chemin(monde, cid, voisine)) == [voisine]
    from sim.convois import _longueur_arete
    assert armee["marche"]["km"] == _longueur_arete(monde, cid, voisine) > 0
    assert armee["marche"]["jours"] == max(1, math.ceil(armee["marche"]["km"] / regles.vitesse_marche_km_par_jour))
    for nom, geste in gestes.items():
        assert armee[nom]["refus"] == _refus(monde, geste), nom
    assert armee["assieger"]["refus"] is not None and armee["renvoyer"]["refus"] is None
    assert (armee["renvoyer"]["hommes"], armee["renvoyer"]["vivres_kg"]) == (monde.armees[0].hommes, 500.0)
    vers_soi = G.devis_des_ordres(monde, BAR, cid)["armees"][0]["marche"]
    assert vers_soi["refus"] == _refus(monde, marcher | {"cell": cid}) is not None and vers_soi["route"] == []
    # Un ordre donné : les trois autres se refusent, au devis comme au dépôt.
    recevoir_intention(monde, marcher)
    (armee,) = G.devis_des_ordres(monde, BAR, voisine)["armees"]
    for nom, geste in gestes.items():
        assert armee[nom]["refus"] == _refus(monde, geste) is not None, nom
    assert armee["marche"]["refus"] == _refus(monde, marcher) is not None
    with pytest.raises(G.GuerreInvalide):
        G.devis_des_ordres(monde, "maison-inventee")


def test_le_devis_dit_le_prix_de_la_caserne_et_le_refus_de_son_depot(depart, regles):
    monde = copy.deepcopy(depart)
    cid = _capitale(monde)
    caserne = B.charger_types()[regles.batiment_de_levee]
    batiment = G.devis_des_ordres(monde, BAR)["levee"]["batiment"]
    # Son prix est celui du dépôt : ses journées au salaire du bourg ; sans grain, le refus du dépôt.
    cout = B.cout_kg(monde, caserne, cid)
    grenier = (monde.greniers.get(BAR) or {}).get(NOURRITURE, 0.0)
    # Le grain qui manque : le coût moins le grenier.
    attendu = {"nature": "caserne", "nom": caserne.nom, "cell_id": cid, "journees": caserne.journees,
               "bras_par_jour": caserne.bras_par_jour, "cout_kg": cout, "manque_kg": cout - grenier}
    assert {k: v for k, v in batiment.items() if k != "refus"} == attendu and attendu["cout_kg"] > 0
    assert batiment["manque_kg"] > 0
    depot = {"type": "batir_dans_une_province", "maison": BAR, "cell": cid, "nature": "caserne"}
    assert batiment["refus"] == _refus(monde, depot) is not None and batiment["refus"].startswith("grenier insuffisant")
    # Le grain au grenier : le devis ne refuse plus, le dépôt passe, rien ne manque ; déposée, la seconde se refuse
    # des deux côtés et le manque compte la caserne déjà déposée.
    monde.greniers[BAR][NOURRITURE] = 20000.0
    batiment = G.devis_des_ordres(monde, BAR)["levee"]["batiment"]
    assert batiment["refus"] is None is _refus(monde, depot) and batiment["manque_kg"] == 0
    recevoir_intention(monde, depot)
    batiment = G.devis_des_ordres(monde, BAR)["levee"]["batiment"]
    assert batiment["refus"] == _refus(monde, depot) and "une seule caserne" in batiment["refus"]
    # Un grenier d'une caserne et demie : sans la caserne déposée, rien ne manquerait ; avec elle, une demi-caserne.
    monde.greniers[BAR][NOURRITURE] = 1.5 * cout
    manque = G.devis_des_ordres(monde, BAR)["levee"]["batiment"]["manque_kg"]
    assert manque == pytest.approx(cout / 2) and manque > 0


def test_le_pays_d_une_terre_change_a_la_chute_et_pas_sans_elle(campagne, depart):
    from types import SimpleNamespace
    from sim.carte_servie import terres_et_pays
    from sim.noms import noms_depuis_monde
    noms = SimpleNamespace(noms=noms_depuis_monde(depart))
    par_id = {m.id: m for m in depart.maisons}

    def pays(monde):
        document = terres_et_pays(monde, noms)
        assert [t["cell_id"] for t in document["terres"]] == sorted(monde.cells)
        assert {p["id"] for p in document["pays"]} == {t["pays"] for t in document["terres"]} - {None}
        return {t["cell_id"]: t["pays"] for t in document["terres"]}, document

    avant, document = pays(depart)
    # Le pays est la racine de la suzeraineté du maître du bourg, nommé comme sa fiche.
    for terre in document["terres"]:
        maitre = depart.cells[terre["cell_id"]].lieux[0].maitre
        assert terre["maitre"] == maitre and terre["pays"] == (None if maitre is None else G.racine(par_id, maitre))
    assert any(t["maitre"] != t["pays"] for t in document["terres"] if t["maitre"]), "aucun vassal : échantillon vide"
    assert all(p["nom"] for p in document["pays"])
    # Une place prise à une maison d'un autre pays passe au pays du preneur, et elle seule.
    monde = copy.deepcopy(depart)
    racine_de_bar = G.racine(par_id, BAR)
    place = next(cid for cid, cel in sorted(monde.cells.items())
                 if cel.lieux[0].maitre is not None and G.racine(par_id, cel.lieux[0].maitre) != racine_de_bar)
    armee = G.Armee(0, BAR, place, 0, ((_capitale(monde), 0, 10),), 0.0, 0, siege=place)
    monde.armees = [armee]
    assert pays(monde)[0] == avant, "une armée devant la place ne change aucun pays"
    G.tomber(monde, armee)
    apres, _ = pays(monde)
    assert {cid for cid in avant if avant[cid] != apres[cid]} == {place} and apres[place] == racine_de_bar
    # Une place prise dans le même pays change de maître, pas de pays : sa couleur reste.
    voisine, cible = campagne["voisine"], campagne["cible"]
    assert G.racine(par_id, cible) == racine_de_bar, "la voisine de Bar a changé de pays : échantillon à revoir"
    document = terres_et_pays(campagne["monde"], noms)
    terre = next(t for t in document["terres"] if t["cell_id"] == voisine)
    assert (terre["maitre"], terre["pays"]) == (BAR, racine_de_bar) and depart.cells[voisine].lieux[0].maitre == cible


def test_le_service_sert_les_terres_les_armees_dessinees_et_le_devis():
    import json
    from sim.places import places_du_monde
    from sim.service import _serialiser
    from sim.tests.test_monde import _service_epreuve, requete_service

    with _service_epreuve() as (serveur, port):
        statut, terres, octets = requete_service(port, "/terres")
        assert statut == 200 and octets == _serialiser(terres)
        assert (terres["tick"], terres["date"]) == (0, serveur.world.date_simulation)
        assert {t["cell_id"]: t["maitre"] for t in terres["terres"]} == {
            cid: c.lieux[0].maitre for cid, c in serveur.world.cells.items()}
        assert requete_service(port, "/guerres/ordres")[0] == 400
        assert requete_service(port, "/guerres/ordres?maison=maison-inventee")[0] == 404
        assert requete_service(port, f"/guerres/ordres?maison={BAR}&cell=sept")[0] == 400
        assert requete_service(port, f"/guerres/ordres?maison={BAR}&cell=999999")[0] == 404

        assert requete_service(port, "/intention", "POST",
                               json.dumps({"type": "choisir_depart", "seigneurie": 1}).encode())[0] == 200
        assert requete_service(port, "/tick?n=1", "POST")[0] == 200
        with serveur.verrou_tick:
            prepare = _avec_caserne(serveur.world)
            serveur.world.batiments_de_province = prepare.batiments_de_province
            serveur.world.greniers[BAR][NOURRITURE] = 20000.0
        cid = _capitale(serveur.world)
        voisine, cible = _voisine(serveur.world, cid)
        statut, devis, _ = requete_service(port, f"/guerres/ordres?maison={BAR}&cell={voisine}")
        with serveur.verrou_tick:
            attendu = json.loads(_serialiser(G.devis_des_ordres(serveur.world, BAR, voisine)))
        assert statut == 200 and devis == attendu and devis["levee"]["refus"] is None
        for corps in (_levee(cid), {"type": "declarer_guerre", "maison": BAR, "cible": cible}):
            assert requete_service(port, "/intention", "POST", json.dumps(corps).encode())[0] == 200
        assert requete_service(port, "/tick?n=1", "POST")[0] == 200
        marche = {"type": "marcher", "maison": BAR, "armee": 0, "cell": voisine, "rang": 0}
        assert requete_service(port, "/intention", "POST", json.dumps(marche).encode())[0] == 200
        assert requete_service(port, "/tick?n=1", "POST")[0] == 200

        (armee,) = requete_service(port, "/guerres")[1]["armees"]
        places = places_du_monde(serveur.world)
        monde_armee = serveur.world.armees[0]
        depart = places[monde_armee.cell_id][monde_armee.rang].en_document()
        if monde_armee.destination is not None:
            assert armee["etapes"] == [places[c][0].en_document() for c in monde_armee.route] != []
            # En marche, elle est dessinée sur son tronçon, avancée de la part qu'elle en a faite.
            assert monde_armee.avance_km > 0, "l'armée n'a pas avancé : échantillon vide"
            part = monde_armee.avance_km / G._troncon_km(serveur.world, monde_armee)[0]
            assert 0 < part < 1 and armee["point"] == {
                cle: depart[cle] + (armee["etapes"][0][cle] - depart[cle]) * part for cle in depart}
        else:
            assert armee["point"] == depart
            assert armee["etapes"] == [] and (monde_armee.cell_id, monde_armee.rang) == (voisine, 0)
        # Le tick a avancé, les terres ne changent pas : seuls le tick et la date se récrivent.
        statut, apres, octets = requete_service(port, "/terres")
        assert octets == _serialiser(apres) and apres["tick"] == 3
        assert (apres["terres"], apres["pays"]) == (terres["terres"], terres["pays"])
        # La photographie garde la guerre sans les places.
        assert "point" not in G.document_de_la_guerre(serveur.world)["armees"][0]


# --- L'IA fait la guerre par les gestes du joueur ----------------------------------------

JOURS_DE_L_IA = 60  # Bar règle sa part dans le mois, puis marche huit jours : l'horizon garde de la marge
GESTES_DE_GUERRE = ("declarer_guerre", "lever_armee", "marcher", "assieger", "renvoyer_armee")


@pytest.fixture(scope="module")
def guerre_de_l_ia(depart):
    """Trente jours du monde, puis Bar avec une caserne achevée et 300 t de grain ; l'IA joue jusqu'au siège de Bar.

    Rend le monde préparé et son aléa (avant l'IA), le relevé, le monde au jour du siège, et le monde
    que l'IA a lu chaque jour de la part de Bar.
    """
    from sim import ia
    from sim.capitales import toutes_les_maisons_de_l_ia
    monde, rng = copy.deepcopy(depart), random.Random(0)
    for numero in range(c.FENETRE_FLUX_TICKS):
        engine.tick(monde, rng, numero)
    cid = _capitale(monde)
    journees = B.charger_types()["caserne"].journees
    identifiant = max((b.identifiant for b in monde.batiments_de_province), default=-1) + 1
    monde.batiments_de_province = [*monde.batiments_de_province, B.BatimentDeProvince(
        identifiant, "caserne", cid, BAR, journees, journees, False, 0, 0)]
    monde.greniers[BAR][NOURRITURE] = monde.greniers[BAR].get(NOURRITURE, 0.0) + 300000.0
    prepare, alea = copy.deepcopy(monde), copy.deepcopy(rng)
    maisons, releve, lectures = toutes_les_maisons_de_l_ia(monde), [], {}
    for _ in range(JOURS_DE_L_IA):
        deja = len(releve)
        if ia._jour_de_la_part(BAR, monde.ticks_ecoules):
            lectures[monde.ticks_ecoules] = copy.deepcopy(monde)
        ia.jouer_ia(monde, releve, maisons)
        engine.tick(monde, rng, monde.ticks_ecoules)
        if any(e["intention"]["type"] == "assieger" and e["intention"]["maison"] == BAR for e in releve[deja:]):
            break
    return prepare, alea, releve, monde, lectures


def _de_bar(releve):
    return [e for e in releve if e["intention"]["type"] in GESTES_DE_GUERRE and e["intention"]["maison"] == BAR]


def test_l_ia_declare_leve_marche_et_assiege_par_les_gestes_du_joueur(guerre_de_l_ia, regles):
    prepare, alea, releve, monde, lectures = guerre_de_l_ia
    gestes = _de_bar(releve)
    assert [e["intention"]["type"] for e in gestes] == ["declarer_guerre", "lever_armee", "marcher", "assieger"]
    assert all("refus" not in e for e in releve if e["intention"]["type"] in GESTES_DE_GUERRE)
    declaration, levee, marche, siege = gestes
    # La raison de la guerre se lit sur le monde du jour, avant tout dépôt.
    raison, avant = levee["raison"], lectures[levee["tick"]]
    assert declaration["tick"] == levee["tick"] and declaration["raison"] == raison
    assert raison["regle"] == "guerre_a_la_place_voisine" and declaration["intention"]["cible"] == raison["cible"]
    assert avant.cells[raison["place"]].lieux[0].maitre == raison["cible"]
    par_id = {m.id: m for m in avant.maisons}
    assert G.racine(par_id, raison["cible"]) != G.racine(par_id, BAR)
    assert G.place_a_prendre(avant, BAR, _capitale(avant), regles,
                             lambda m: G.racine(par_id, m) != G.racine(par_id, BAR)) == (
        raison["place"], raison["jours_de_marche"], raison["cible"])
    assert raison["hommes"] == sum(n for _c, _r, n in levee["intention"]["lieux"]) >= regles.ia_hommes_minimum
    par_homme = regles.ration_kg_par_homme_par_jour * (raison["jours_de_marche"] + regles.ia_jours_de_siege_voulus)
    assert levee["intention"]["vivres_kg"] == raison["vivres_kg"] == raison["hommes"] * par_homme
    assert raison["grenier_nourriture_kg"] == avant.greniers[BAR][NOURRITURE]
    assert raison["grenier_nourriture_kg"] - raison["reserve_voulue_kg"] >= raison["vivres_kg"]
    assert all(c_ == _capitale(avant) and n <= G.levee_maximale(avant, c_, r, regles)
               for c_, r, n in levee["intention"]["lieux"])
    # Elle marche vers la place, puis l'assiège à son arrivée.
    assert (marche["intention"]["cell"], marche["intention"]["rang"]) == (raison["place"], 0)
    assert marche["tick"] == levee["tick"] + 1 and marche["raison"]["regle"] == "marche_vers_la_place"
    assert siege["raison"]["regle"] == "place_ennemie" and siege["raison"]["cell_id"] == raison["place"]
    armee = next(a for a in monde.armees if a.maison == BAR)
    assert armee.siege == raison["place"] and [g.agresseur for g in monde.guerres if g.defenseur == raison["cible"]] == [BAR]


def test_le_joueur_qui_rejoue_les_gestes_de_l_ia_obtient_le_meme_monde(guerre_de_l_ia):
    prepare, alea, releve, monde, _lectures = guerre_de_l_ia
    par_tick = {}
    for entree in releve:
        if "refus" not in entree:
            par_tick.setdefault(entree["tick"], []).append(entree["intention"])
    joueur = copy.deepcopy(prepare)
    while joueur.ticks_ecoules < monde.ticks_ecoules:
        for intention in par_tick.get(joueur.ticks_ecoules, ()):
            recevoir_intention(joueur, copy.deepcopy(intention))
        engine.tick(joueur, alea, joueur.ticks_ecoules)
    egaux = json.dumps(joueur.to_dict(), sort_keys=True) == json.dumps(monde.to_dict(), sort_keys=True)
    assert egaux and joueur.armees


def test_l_ia_rentre_quand_la_place_est_prise_ou_l_armee_affamee(guerre_de_l_ia, regles):
    from sim import ia
    monde = guerre_de_l_ia[3]
    maison = next(m for m in ia.maisons_de_l_ia(monde) if m.sorte == "seigneurie" and m.id == 1)
    armee = next(a for a in monde.armees if a.maison == BAR)
    # Devant la place, elle tient le siège : aucun geste.
    assert ia._propositions_des_armees(monde, maison, BAR, regles) == []
    affamee = copy.deepcopy(monde)
    G._remplacer(affamee, G.replace(armee, vivres_kg=0.0, dette_kg=10.0))
    (renvoi,) = ia._propositions_des_armees(affamee, maison, BAR, regles)
    assert renvoi["raison"]["regle"] == "armee_affamee" and renvoi["intention"]["type"] == "renvoyer_armee"
    recevoir_intention(affamee, renvoi["intention"])
    prise = copy.deepcopy(monde)
    G.tomber(prise, next(a for a in prise.armees if a.maison == BAR))
    (renvoi,) = ia._propositions_des_armees(prise, maison, BAR, regles)
    assert (renvoi["raison"]["regle"], renvoi["raison"]["place"]) == ("place_prise", armee.siege)
    recevoir_intention(prise, renvoi["intention"])
    # Contre-épreuve : le siège levé, sans prise ni faim, devant la place ennemie, elle l'assiège de nouveau.
    levee = copy.deepcopy(monde)
    G._remplacer(levee, G.replace(armee, siege=None))
    (geste,) = ia._propositions_des_armees(levee, maison, BAR, regles)
    assert geste["raison"]["regle"] == "place_ennemie"


# --- La preuve de l'IA sur un an -----------------------------------------------------------

def _lire_guerre(monde, cle, regles):
    """La raison de la guerre, lue sur le monde au tick, sans sim/ia.py."""
    from sim.tests.test_monde import _reserve_lue
    par_id = {m.id: m for m in monde.maisons}
    capitale = par_id[cle].cell_id
    sienne = G.racine(par_id, cle)
    cid, jours, maitre = G.place_a_prendre(monde, cle, capitale, regles, lambda m: G.racine(par_id, m) != sienne)
    parts = [G.levee_maximale(monde, capitale, l.rang, regles) for l in monde.cells[capitale].lieux if l.maitre == cle]
    grenier, reserve = monde.greniers[cle].get(NOURRITURE, 0), _reserve_lue(monde, cle)
    par_homme = regles.ration_kg_par_homme_par_jour * c.TICK_DURATION_DAYS * (jours + regles.ia_jours_de_siege_voulus)
    hommes = min(sum(parts), G._paysans(monde.cells[capitale]), int((grenier - reserve) // par_homme))
    return {"regle": "guerre_a_la_place_voisine", "cible": maitre, "place": cid, "jours_de_marche": jours,
            "habitants_de_la_place": monde.cells[cid].lieux[0].population, "hommes": hommes,
            "grenier_nourriture_kg": grenier, "reserve_voulue_kg": reserve, "vivres_kg": hommes * par_homme}


def _lire_armee(monde, cle, identifiant, regles):
    """Le geste du jour d'une armée et sa raison, lus sur le monde au tick, sans sim/ia.py."""
    armee = next(a for a in monde.armees if a.identifiant == identifiant)
    base = {"armee": identifiant, "cell_id": armee.cell_id, "rang": armee.rang, "hommes": armee.hommes,
            "vivres_kg": armee.vivres_kg, "dette_kg": armee.dette_kg}
    prises = [p for p in monde.prises if p["armee"] == identifiant]
    if prises:
        return "renvoyer_armee", {"regle": "place_prise", **base, "place": prises[-1]["cell_id"]}
    if armee.vivres_kg <= 0 and armee.dette_kg > 0:
        return "renvoyer_armee", {"regle": "armee_affamee", **base}
    maitre = monde.cells[armee.cell_id].lieux[0].maitre
    if armee.rang == 0 and maitre != cle and G.en_guerre(monde, cle, maitre):
        return "assieger", {"regle": "place_ennemie", **base, "maitre_de_la_place": maitre}
    place = G.place_a_prendre(monde, cle, armee.cell_id, regles, lambda m: G.en_guerre(monde, cle, m))
    if place is None:
        return "renvoyer_armee", {"regle": "sans_place_a_prendre", **base}
    cid, jours, maitre = place
    return "marcher", {"regle": "marche_vers_la_place", **base, "place": cid, "jours_de_marche": jours,
                       "maitre_de_la_place": maitre}


@pytest.mark.longue
def test_un_an_l_ia_mene_ses_guerres_par_les_gestes_du_joueur(monkeypatch, regles):
    """Un an de la graine 0 avec l'IA : au moins une maison déclare, lève, marche et assiège, chaque raison égale
    au monde de son tick ; le relevé rejoué comme gestes du joueur donne le même monde."""
    from sim import __main__ as cli
    reel, lectures = cli.jouer_ia, {}

    def enveloppe(monde, releve, maisons=None):
        deja = len(releve)
        reel(monde, releve, maisons)
        # Le dépôt ne change pas le monde : il est celui que l'IA a lu.
        for rang, entree in enumerate(releve[deja:], deja):
            intention = entree["intention"]
            if intention["type"] in ("declarer_guerre", "lever_armee"):
                lectures[rang] = (intention["type"], _lire_guerre(monde, intention["maison"], regles))
            elif intention["type"] in GESTES_DE_GUERRE:
                lectures[rang] = _lire_armee(monde, intention["maison"], intention["armee"], regles)

    monkeypatch.setattr(cli, "jouer_ia", enveloppe)
    resume, monde = cli._simulate(c.CALENDAR_DAYS_PER_YEAR, 0, ia=True)
    monkeypatch.setattr(cli, "jouer_ia", reel)
    releve = resume["ia"]["releve"]
    guerre = [(rang, e) for rang, e in enumerate(releve) if e["intention"]["type"] in GESTES_DE_GUERRE]
    assert guerre and all("refus" not in e for _r, e in guerre)
    for rang, entree in guerre:
        type_, raison = lectures[rang]
        assert type_ == entree["intention"]["type"] and raison == entree["raison"], (entree["tick"], entree)
    menees = {}
    for _r, entree in guerre:
        menees.setdefault(entree["intention"]["maison"], set()).add(entree["intention"]["type"])
    completes = sorted(m for m, types in menees.items()
                       if {"declarer_guerre", "lever_armee", "marcher", "assieger"} <= types)
    print(f"{len(completes)} maisons de l'IA mènent une guerre : {completes} ; prises : {len(monde.prises)}, "
          f"morts sous les armes : {monde.morts_des_armees}", flush=True)
    assert completes
    # Le même relevé, rejoué comme gestes du joueur, donne le même monde.
    par_tick = {}
    for entree in releve:
        if "refus" not in entree:
            par_tick.setdefault(entree["tick"], []).append(entree["intention"])

    def joueur(m, _releve, maisons=None):
        for intention in par_tick.get(m.ticks_ecoules, ()):
            recevoir_intention(m, copy.deepcopy(intention))

    monkeypatch.setattr(cli, "jouer_ia", joueur)
    _, rejoue = cli._simulate(c.CALENDAR_DAYS_PER_YEAR, 0, ia=True)
    egaux = json.dumps(rejoue.to_dict(), sort_keys=True) == json.dumps(monde.to_dict(), sort_keys=True)
    assert egaux
