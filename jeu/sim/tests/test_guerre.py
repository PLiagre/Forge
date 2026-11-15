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
import math
import random
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
                              brut["siege"]["jours_de_faim_avant_la_chute"])
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
    with pytest.raises(IntentionRefusee, match=f"la levée est fermée : aucune caserne achevée dans la capitale "
                                               rf"\(cellule {cid}\)"):
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
    with pytest.raises(IntentionRefusee, match=rf"le bourg de la capitale \(cellule {cid}\) est à 'grande-3'"):
        recevoir_intention(monde, _levee(cid))


# --- La part et les autres refus ----------------------------------------------------

def test_un_lieu_ne_donne_que_sa_part(depart, regles):
    monde = _avec_caserne(depart)
    cid = _capitale(monde)
    lieu = monde.cells[cid].lieux[1]
    maximum = math.floor(regles.part_maximale_levee * lieu.population)
    assert maximum > 0 and G.levee_maximale(monde, cid, 1, regles) == maximum
    with pytest.raises(IntentionRefusee, match=f"peut en donner {maximum}, {maximum + 1} demandés"):
        recevoir_intention(monde, _levee(cid, {1: maximum + 1}))
    recevoir_intention(monde, _levee(cid, {1: maximum - 3}, vivres=0))
    # Une levée déjà déposée compte : il ne reste que trois hommes à ce lieu.
    with pytest.raises(IntentionRefusee, match="peut en donner 3, 4 demandés"):
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
        (_levee(cid, vivres=1000.5), "grenier insuffisant : 1000.5 kg de vivres demandés, 1000 kg"),
        ({"type": "lever_armee", "maison": BAR, "lieux": [[cid, autre.rang, 1]], "vivres_kg": 0},
         f"ce lieu n'est pas à toi : \\({cid}, {autre.rang}\\) est à '{autre.maitre}'"),
        ({"type": "lever_armee", "maison": BAR, "lieux": [[cid, 99, 1]], "vivres_kg": 0}, "lieu inconnu"),
        ({"type": "declarer_guerre", "maison": BAR, "cible": BAR}, "à soi-même"),
        ({"type": "declarer_guerre", "maison": BAR, "cible": "maison-inventee"}, "cible inconnue"),
        ({"type": "declarer_guerre", "maison": "maison-inventee", "cible": cible}, "maison inconnue"),
        ({"type": "marcher", "maison": BAR, "armee": 0, "cell": voisine, "rang": 0}, "armée inconnue : 0"),
        ({"type": "assieger", "maison": BAR, "armee": True}, "armée invalide"),
        ({"type": "renvoyer_armee", "maison": BAR, "armee": 7}, "armée inconnue : 7"),
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
    with pytest.raises(IntentionRefusee, match=f"pas assez de paysans : 15 hommes demandés dans la cellule {cid}, 0"):
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
    with pytest.raises(IntentionRefusee, match="cette place est à toi"):
        recevoir_intention(monde, {"type": "assieger", "maison": BAR, "armee": 0})
    # Une autre maison ne commande pas l'armée de Bar.
    with pytest.raises(IntentionRefusee, match=f"cette armée n'est pas à toi : elle est à {BAR}"):
        recevoir_intention(monde, {"type": "renvoyer_armee", "maison": cible, "armee": 0})
    # Un seul geste par armée et par jour.
    recevoir_intention(monde, {"type": "marcher", "maison": BAR, "armee": 0, "cell": voisine, "rang": 0})
    with pytest.raises(IntentionRefusee, match="déjà déposé pour l'armée 0"):
        recevoir_intention(monde, {"type": "renvoyer_armee", "maison": BAR, "armee": 0})
    _appliquer(monde)
    armee = monde.armees[0]
    assert armee.destination == (voisine, 0) and armee.route == (voisine,)
    with pytest.raises(IntentionRefusee, match="marche encore"):
        recevoir_intention(monde, {"type": "assieger", "maison": BAR, "armee": 0})
    # Arrivée (le maillon de la marche la pose là) : pas encore en guerre avec le maître.
    G._remplacer(monde, G.replace(armee, cell_id=voisine, rang=0, destination=None, route=()))
    with pytest.raises(IntentionRefusee, match=f"pas en guerre avec le maître de la place : '{cible}'"):
        recevoir_intention(monde, {"type": "assieger", "maison": BAR, "armee": 0})
    recevoir_intention(monde, {"type": "declarer_guerre", "maison": BAR, "cible": cible})
    with pytest.raises(IntentionRefusee, match=f"déjà en guerre avec {BAR}"):
        recevoir_intention(monde, {"type": "declarer_guerre", "maison": cible, "cible": BAR})
    # La déclaration déposée vaut pour le siège déposé après elle.
    recevoir_intention(monde, {"type": "assieger", "maison": BAR, "armee": 0})
    _appliquer(monde)
    assert [g.en_document() for g in monde.guerres] == [
        {"identifiant": 0, "agresseur": BAR, "defenseur": cible, "debut": monde.ticks_ecoules}]
    assert monde.armees[0].siege == voisine
    with pytest.raises(IntentionRefusee, match="assiège déjà"):
        recevoir_intention(monde, {"type": "assieger", "maison": BAR, "armee": 0})
    # Un lieu qui n'est pas un bourg n'est pas une place.
    G._remplacer(monde, G.replace(monde.armees[0], rang=1, siege=None))
    with pytest.raises(IntentionRefusee, match="n'est pas un bourg"):
        recevoir_intention(monde, {"type": "assieger", "maison": BAR, "armee": 0})


def test_sans_chemin_terrestre_l_armee_ne_marche_pas(depart):
    monde = _avec_caserne(depart)
    cid = _capitale(monde)
    recevoir_intention(monde, _levee(cid))
    _appliquer(monde)
    terrestres = {x for e in monde.adjacency for x in (e["a"], e["b"])
                  if e["a"] in monde.cells and e["b"] in monde.cells}
    ile = min(set(monde.cells) - terrestres)
    with pytest.raises(IntentionRefusee, match=f"aucun chemin terrestre de la cellule {cid} à la cellule {ile}"):
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
    with pytest.raises(IntentionRefusee, match="19500 kg disponibles"):
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
