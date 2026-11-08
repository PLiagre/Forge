"""Le registre des modificateurs (VISION.md, décisions 34, 35, 37 et 38 ; MODELE.md « Les modificateurs »).

Ce que ces épreuves prouvent, et ce qui les fait échouer :

- sans aucun modificateur, le monde et la photographie à 365 jours sont ceux
  d'avant le registre, octet pour octet (empreintes épinglées) ;
- un +10 % sur la récolte d'une cellule récolte exactement 10 % de grain en
  plus, et ces kilos se retrouvent dans les stocks, les convois et les
  greniers : la masse du monde ne grandit que de la récolte en plus ;
- un modificateur sans source, sur une grandeur que le moteur ne lit pas, ou
  qui porterait des kilos plutôt qu'un taux, est refusé ;
- chaque grandeur lue change son taux dans le bon sens, et l'IA lit les mêmes ;
- le détail de l'infobulle s'additionne dans un ordre fixé, quel que soit
  l'ordre des poses, et le service et la photographie le servent.
"""
import copy
import hashlib
import json
import math
import random
import sys

import pytest

import sim.constants as c
from sim import chantiers, engine, modificateurs as M
from sim.snapshot_export import build_snapshot_document, serialize_snapshot
from sim.world import World

NOURRITURE = c.MARCHANDISE_NOURRITURE

# Empreintes du monde (to_dict canonique) et de la photographie au 365e tick,
# graine 0, sans IA : celles de master juste avant le registre (0930678a, la
# soudure de 1400 comprise), mesurées le 8 novembre 2026. Les flottants de la
# trigonométrie (la durée du jour) diffèrent au dernier bit d'un système à
# l'autre : chaque système a la sienne, et la CI juge sous Linux.
EMPREINTES_365 = {
    "linux": ("cf1785dffe0bb972b5e0092b5992f4e5f785f4417eb0a91c06ed3d86f8f9dce2",
              "e62f70fd48071e5de96bccd286a27512a6a4ec7c7ef8c656347b2e39f1e7ef2e"),
    "win32": ("96f0ad5df50520405574c2b3daf0ae7e3ca159a05356e28e1188e6bd2b183d98",
              "b2befd1bcb466984883c6af9e9ef704546590296e9b6302e9ddf29a9f2e6ddcb"),
}


@pytest.fixture(scope="module")
def donnees():
    return M.charger_donnees()


@pytest.fixture(scope="module")
def depart():
    return World.charger(rng_seed=0)


def _paris(monde):
    return monde.attribution_villes.placees["Paris"]


def _empreintes(monde, ticks):
    texte = json.dumps(monde.to_dict(), sort_keys=True, ensure_ascii=False)
    photo = serialize_snapshot(build_snapshot_document(monde, 0, ticks))
    return hashlib.sha256(texte.encode()).hexdigest(), hashlib.sha256(photo).hexdigest()


def _avec(donnees, **champs):
    """Les données du dépôt, plus une définition d'épreuve."""
    definition = M.Definition(**{"identifiant": "epreuve", "nom": "Épreuve", "portee": "cellule",
                                 "duree_jours": 0, **champs})
    return M.Donnees(donnees.sources, donnees.grandeurs, {**donnees.definitions, "epreuve": definition})


def _masse(monde):
    """Toute la nourriture du monde : paniers des cellules, greniers, convois, mer, et ce qui s'est perdu."""
    cellules = math.fsum(cellule.stocks.get(NOURRITURE, 0.0) for cellule in monde.cells.values())
    greniers = math.fsum(panier.get(NOURRITURE, 0.0) for panier in monde.greniers.values())
    convois = math.fsum(groupe.total for groupe in monde.convois.values())
    return cellules + greniers + convois + monde.stocks_mer.get(NOURRITURE, 0.0) + monde.mange_convois_kg + monde.pertes_kg


def _recoltes_mesurees(monkeypatch):
    """Le grain versé par la récolte, cellule par cellule, tel que le moteur le verse."""
    verse = {}
    original = engine._verser_recolte

    def mesurer(cell, recolte, carte, saison, recoltes, facteurs=None):
        avant = cell.stocks.get(NOURRITURE, 0.0)
        original(cell, recolte, carte, saison, recoltes, facteurs)
        verse[cell.cell_id] = verse.get(cell.cell_id, 0.0) + cell.stocks.get(NOURRITURE, 0.0) - avant

    monkeypatch.setattr(engine, "_verser_recolte", mesurer)
    return verse


# --- Les données -------------------------------------------------------------

def test_les_donnees_disent_les_grandeurs_du_moteur(donnees):
    assert set(donnees.grandeurs) == {"recolte", "prelevement", "natalite", "mortalite", "departs",
                                      "cout_chantier", "duree_chantier", "levee", "commerce"}
    assert {g for g, grandeur in donnees.grandeurs.items() if not grandeur.lue} == {"levee"}
    assert set(donnees.sources) == {"batiment", "loi", "idee", "conseiller", "evenement", "jauge"}
    moulin = donnees.definitions["moulin"]
    assert (moulin.grandeur, moulin.valeur, moulin.portee, moulin.duree_jours) == ("recolte", 0.10, "cellule", 0)


@pytest.mark.parametrize("champs, motif", [
    ({"grandeur": "nourriture_kg"}, "le moteur ne lit que des taux"),
    ({"kg": 500}, "jamais des kilos"),
    ({"pieces": 3}, "jamais des kilos"),
    ({"valeur": -1}, "−100 %"),
    ({"valeur": True}, "nombre fini"),
    ({"valeur": float("nan")}, "nombre fini"),
    ({"portee": "royaume"}, "portee"),
    ({"duree_jours": -3}, "duree_jours"),
])
def test_une_definition_qui_n_est_pas_un_taux_est_refusee(champs, motif):
    with open(M._CHEMIN, "rb") as fichier:
        document = __import__("tomllib").load(fichier)
    document["modificateurs"]["moulin"] = {**document["modificateurs"]["moulin"], **champs}
    with pytest.raises(M.ModificateurInvalide, match=motif):
        M.lire_donnees(document)
    # Contre-épreuve : le document du dépôt passe.
    with open(M._CHEMIN, "rb") as fichier:
        assert M.lire_donnees(__import__("tomllib").load(fichier)).definitions["moulin"]


# --- Les poses ---------------------------------------------------------------

def test_une_pose_sans_source_ou_hors_de_sa_portee_est_refusee(depart, donnees):
    monde = copy.deepcopy(depart)
    paris = _paris(monde)
    for source in (None, "", "moulin", "inconnue:moulin", "batiment:", "batiment: "):
        with pytest.raises(M.ModificateurInvalide, match="source"):
            M.poser(monde, "moulin", source, {"cellule": paris}, donnees)
    with pytest.raises(M.ModificateurInvalide, match="se pose sur un cellule, pas sur un lieu"):
        M.poser(monde, "moulin", "batiment:x", {"lieu": [paris, 0]}, donnees)
    for cible in ({"cellule": -5}, {"cellule": True}, {"lieu": [paris, 999]}, {"pays": "maison-inventee"},
                  {"royaume": 1}, {"cellule": paris, "lieu": [paris, 0]}):
        with pytest.raises(M.ModificateurInvalide, match="cible"):
            M.poser(monde, "moulin", "batiment:x", cible, donnees)
    with pytest.raises(M.ModificateurInvalide, match="inconnu"):
        M.poser(monde, "moulin-inventé", "batiment:x", {"cellule": paris}, donnees)
    levee = _avec(donnees, grandeur="levee", valeur=0.2)
    with pytest.raises(M.ModificateurInvalide, match="jalon 7"):
        M.poser(monde, "epreuve", "loi:levee", {"cellule": paris}, levee)
    assert monde.modificateurs == [] and monde.to_dict() == depart.to_dict()
    pose = M.poser(monde, "moulin", "batiment:moulin-1", {"cellule": paris}, donnees)
    assert monde.modificateurs == [pose] and pose.debut == 0 and pose.fin is None
    assert monde.to_dict()["modificateurs"] == [pose.en_document()]


def test_les_valeurs_s_additionnent_dans_un_ordre_fixe(depart, donnees):
    monde = copy.deepcopy(depart)
    paris = _paris(monde)
    bourg = monde.cells[paris].lieux[0]
    maitre = bourg.maitre
    pays = _avec(donnees, grandeur="recolte", valeur=-0.25, portee="pays")
    lieu = M.Donnees(pays.sources, pays.grandeurs, {**pays.definitions, "champ": M.Definition(
        "champ", "Champ d'épreuve", "recolte", 0.05, "lieu", 0)})
    poses = [("moulin", "batiment:b", {"cellule": paris}), ("epreuve", "evenement:famine", {"pays": maitre}),
             ("champ", "idee:a", {"lieu": [paris, 0]}), ("moulin", "batiment:a", {"cellule": paris})]
    details = []
    for ordre in (poses, poses[::-1], poses[1:] + poses[:1]):
        essai = copy.deepcopy(depart)
        for identifiant, source, cible in ordre:
            M.poser(essai, identifiant, source, cible, lieu)
        details.append(M.detail(essai, paris, 0))
        assert M.facteurs_du_monde(essai)["recolte"][(paris, 0)] == 1 + math.fsum((0.10, 0.10, -0.25, 0.05))
        assert M.facteur(essai, "recolte", paris, 0) == M.facteurs_du_monde(essai)["recolte"][(paris, 0)]
    assert details[0] == details[1] == details[2]
    lignes = details[0]["recolte"]["lignes"]
    assert [ligne["cible"] for ligne in lignes] == [{"pays": maitre}, {"cellule": paris}, {"cellule": paris},
                                                    {"lieu": [paris, 0]}]
    assert [ligne["source"] for ligne in lignes[1:3]] == ["batiment:a", "batiment:b"]
    assert details[0]["recolte"]["total"] == pytest.approx(0.0)
    # Le modificateur du pays touche les lieux de son maître, et ceux-là seuls.
    facteurs = M.facteurs_du_monde(essai)["recolte"]
    champs = [l for l in essai.cells[paris].lieux if l.rang != 0]
    assert champs
    for l in champs:
        assert facteurs[(paris, l.rang)] == pytest.approx(0.95 if l.maitre == maitre else 1.20)
    ailleurs = [(cid, l.rang) for cid, cell in essai.cells.items() if cid != paris for l in cell.lieux]
    assert ailleurs and all((cle in facteurs) == (essai.cells[cle[0]].lieux[cle[1]].maitre == maitre)
                            for cle in ailleurs)
    assert M.facteur(essai, "natalite", paris, 0) == 1.0 and "natalite" not in M.facteurs_du_monde(essai)


def test_une_pose_datee_expire_et_une_source_se_retire(depart, donnees):
    monde = copy.deepcopy(depart)
    paris = _paris(monde)
    famine = _avec(donnees, grandeur="natalite", valeur=-0.5, duree_jours=10)
    M.poser(monde, "epreuve", "evenement:famine", {"cellule": paris}, famine)
    M.poser(monde, "moulin", "batiment:moulin-1", {"cellule": paris}, famine)
    rng = random.Random(0)
    for numero in range(10):
        engine.tick(monde, rng, numero)
        assert len(monde.modificateurs) == 2 and "natalite" in monde.facteurs_du_tick
    engine.tick(monde, rng, 10)
    assert [p.identifiant for p in monde.modificateurs] == ["moulin"]
    assert "natalite" not in monde.facteurs_du_tick and "recolte" in monde.facteurs_du_tick
    assert M.retirer(monde, "batiment:moulin-1") == 1 and monde.modificateurs == []
    engine.tick(monde, rng, 11)
    assert monde.facteurs_du_tick == {} and "modificateurs" not in monde.to_dict()


# --- La preuve : sans pose, rien ne change ; avec, de vrais kilos ---------------

def test_sans_modificateur_la_photographie_a_365_jours_est_celle_d_avant():
    monde, rng = World.charger(0), random.Random(0)
    for numero in range(c.CALENDAR_DAYS_PER_YEAR):
        engine.tick(monde, rng, numero)
        assert monde.facteurs_du_tick == {}
    assert monde.modificateurs == []
    assert sys.platform in EMPREINTES_365, f"empreintes non mesurées pour {sys.platform}"
    assert _empreintes(monde, c.CALENDAR_DAYS_PER_YEAR) == EMPREINTES_365[sys.platform]


def test_un_moulin_recolte_dix_pour_cent_de_vrais_kilos_en_plus(depart, donnees, monkeypatch):
    temoin, moulin = copy.deepcopy(depart), copy.deepcopy(depart)
    paris = _paris(temoin)
    M.poser(moulin, "moulin", "batiment:moulin-de-paris", {"cellule": paris}, donnees)
    masses = {}
    verses = {}
    for nom, monde in (("temoin", temoin), ("moulin", moulin)):
        with monkeypatch.context() as ctx:
            verses[nom] = _recoltes_mesurees(ctx)
            masses[nom] = (_masse(monde), None)
            engine.tick(monde, random.Random(0), 0)
            masses[nom] = (masses[nom][0], _masse(monde))
    # Exactement 10 % de grain récolté en plus à Paris ; rien ailleurs.
    assert verses["moulin"][paris] == pytest.approx(verses["temoin"][paris] * 1.10, rel=1e-12)
    autres = [cid for cid in verses["temoin"] if cid != paris]
    assert autres and all(verses["moulin"][cid] == verses["temoin"][cid] for cid in autres)
    # Ces kilos sont dans le monde, et rien d'autre : stocks, convois, greniers, pertes.
    en_plus = verses["moulin"][paris] - verses["temoin"][paris]
    assert en_plus > 0
    gain = (masses["moulin"][1] - masses["moulin"][0]) - (masses["temoin"][1] - masses["temoin"][0])
    assert gain == pytest.approx(en_plus, rel=1e-9)
    # Les lieux font la cellule, au kilo près.
    cellule = moulin.cells[paris]
    assert math.fsum(l.stocks.get(NOURRITURE, 0.0) for l in cellule.lieux) == pytest.approx(
        cellule.stocks[NOURRITURE], rel=1e-12)
    # Le prélèvement porte la récolte en plus : les convois de Paris en chargent davantage.
    assert math.fsum(g.total for g in moulin.convois.values()) > math.fsum(g.total for g in temoin.convois.values())


def test_un_modificateur_qui_creerait_des_kilos_rompt_la_conservation(depart, donnees, monkeypatch):
    """Contre-épreuve : 10 % ajoutés au panier sans passer par la récolte se voient au bilan."""
    temoin, faux = copy.deepcopy(depart), copy.deepcopy(depart)
    paris = _paris(temoin)
    verses = {}
    bilans = {}
    for nom, monde in (("temoin", temoin), ("faux", faux)):
        with monkeypatch.context() as ctx:
            verses[nom] = _recoltes_mesurees(ctx)
            avant = _masse(monde)
            if nom == "faux":
                cellule = monde.cells[paris]
                cree = cellule.stocks[NOURRITURE] * 0.10
                cellule.stocks[NOURRITURE] += cree
                cellule.lieux[0].stocks[NOURRITURE] += cree
            engine.tick(monde, random.Random(0), 0)
            bilans[nom] = _masse(monde) - avant
    en_plus = verses["faux"][paris] - verses["temoin"][paris]
    with pytest.raises(AssertionError):
        assert bilans["faux"] - bilans["temoin"] == pytest.approx(en_plus, rel=1e-9, abs=1e-6)


# --- Chaque grandeur lue -------------------------------------------------------

def _deux_mondes(depart, donnees, grandeur, valeur, cible_de, portee="cellule"):
    temoin, modifie = copy.deepcopy(depart), copy.deepcopy(depart)
    epreuve = _avec(donnees, grandeur=grandeur, valeur=valeur, portee=portee)
    M.poser(modifie, "epreuve", "loi:epreuve", cible_de(modifie), epreuve)
    return temoin, modifie


def _jouer(monde, ticks):
    rng = random.Random(0)
    for numero in range(ticks):
        engine.tick(monde, rng, numero)


def test_prelevement_d_un_pays(depart, donnees):
    maitre = depart.cells[_paris(depart)].lieux[0].maitre
    temoin, modifie = _deux_mondes(depart, donnees, "prelevement", 0.5, lambda m: {"pays": maitre}, "pays")
    _jouer(temoin, 1)
    _jouer(modifie, 1)
    i = list(temoin.routes_des_lieux.noms).index(maitre)
    jour_t, jour_m = temoin.flux.jours[0], modifie.flux.jours[0]
    assert jour_m.preleve[i] == pytest.approx(jour_t.preleve[i] * 1.5, rel=1e-9)
    autres = [k for k in range(len(jour_t.preleve)) if k != i]
    assert all(jour_m.preleve[k] == jour_t.preleve[k] for k in autres)
    # Jamais plus que la récolte : un prélèvement à +10 000 % prend toute la récolte, pas plus.
    gourmand = copy.deepcopy(depart)
    M.poser(gourmand, "epreuve", "loi:dime", {"pays": maitre},
            _avec(donnees, grandeur="prelevement", valeur=100.0, portee="pays"))
    _jouer(gourmand, 1)
    recoltes = gourmand.flux.jours[0].recoltes
    tenus = [cle for cle, route in gourmand.routes_des_lieux.items() if route.maitre == maitre]
    assert gourmand.flux.jours[0].preleve[i] == pytest.approx(math.fsum(recoltes[cid][rang] for cid, rang in tenus))


def test_natalite_et_mortalite_d_une_cellule(depart, donnees):
    paris = _paris(depart)
    temoin, modifie = _deux_mondes(depart, donnees, "natalite", 1.0, lambda m: {"cellule": paris})
    _jouer(temoin, 20)
    _jouer(modifie, 20)
    assert modifie.cells[paris].population > temoin.cells[paris].population
    # La mortalité : une cellule sans vivres, plus de morts de faim avec +100 %.
    affame = copy.deepcopy(depart)
    for lieu in affame.cells[paris].lieux:
        lieu.stocks[NOURRITURE] = 0.0
    affame.cells[paris].stocks[NOURRITURE] = 0.0
    temoin, modifie = _deux_mondes(affame, donnees, "mortalite", 1.0, lambda m: {"cellule": paris})
    _jouer(temoin, 10)
    _jouer(modifie, 10)
    morts_t = affame.cells[paris].population - temoin.cells[paris].population
    morts_m = affame.cells[paris].population - modifie.cells[paris].population
    assert morts_t > 0 and morts_m > morts_t


def test_departs_d_un_lieu(depart, donnees):
    paris = _paris(depart)
    vide = copy.deepcopy(depart)
    # Le bourg de Paris sans grain, ses champs pleins : ses foyers partent vers le mieux-vivre.
    cellule = vide.cells[paris]
    retire = cellule.lieux[0].stocks[NOURRITURE]
    cellule.lieux[0].stocks[NOURRITURE] = 0.0
    cellule.stocks[NOURRITURE] -= retire
    temoin, modifie = _deux_mondes(vide, donnees, "departs", 1.0, lambda m: {"lieu": [paris, 0]}, "lieu")
    _jouer(temoin, 1)
    _jouer(modifie, 1)
    partis_t = temoin.flux.jours[0].partis.get((paris, 0), 0)
    partis_m = modifie.flux.jours[0].partis.get((paris, 0), 0)
    assert partis_t > 0 and partis_m > partis_t


def test_cout_et_duree_d_un_chantier_et_l_ia_les_lit(donnees):
    from sim import programme_ia
    from sim.tests.test_programme_ia import _monter
    monde, maisons = _monter()
    proposition = next(p for p in (programme_ia.proposer_route_vers_le_champ(monde, m, []) for m in maisons) if p)
    cid = proposition["intention"]["cell"]
    base_journees, base_cout = proposition["raison"]["journees"], proposition["raison"]["cout_kg"]
    assert base_cout == base_journees * c.SALAIRE_JOURNEE_KG
    chantier = _avec(donnees, grandeur="cout_chantier", valeur=1.0, portee="lieu")
    M.poser(monde, "epreuve", "loi:corvee", {"lieu": [cid, 0]}, chantier)
    duree = M.Donnees(chantier.sources, chantier.grandeurs, {**chantier.definitions, "lent": M.Definition(
        "lent", "Chantier lent", "duree_chantier", 0.5, "lieu", 0)})
    M.poser(monde, "lent", "evenement:pluies", {"lieu": [cid, 0]}, duree)
    assert chantiers.salaire_journee_kg(monde, cid) == c.SALAIRE_JOURNEE_KG * 2
    assert M.ajuster_journees(monde, cid, base_journees) == math.ceil(base_journees * 1.5)
    # L'IA lit les mêmes : sa route coûte et dure ce que le joueur paierait (décision 38).
    modifiee = next(p for p in (programme_ia.proposer_route_vers_le_champ(monde, m, []) for m in maisons)
                    if p and p["intention"]["cell"] == cid)
    assert modifiee["raison"]["journees"] == math.ceil(base_journees * 1.5)
    assert modifiee["raison"]["cout_kg"] == modifiee["raison"]["journees"] * c.SALAIRE_JOURNEE_KG * 2


def test_commerce_d_une_cellule(depart, donnees):
    paris = _paris(depart)
    monde = copy.deepcopy(depart)
    index = engine._index_aretes(monde)
    avant = engine._capacites_aretes(monde, index)
    M.poser(monde, "epreuve", "batiment:foire", {"cellule": paris},
            _avec(donnees, grandeur="commerce", valeur=1.0, portee="cellule"))
    monde.facteurs_du_tick = M.facteurs_du_monde(monde)
    apres = engine._capacites_aretes(monde, index)
    touchees = [cle for cle in avant if paris in cle]
    assert touchees and all(apres[cle] == pytest.approx(avant[cle] * 2) for cle in touchees)
    assert all(apres[cle] == avant[cle] for cle in avant if paris not in cle)
    a, b = touchees[0]
    assert engine._capacite_transport_arete_kg(monde, a, b) == pytest.approx(
        engine._capacite_transport_arete_kg(depart, a, b) * 2)


# --- Ce que le joueur en voit -------------------------------------------------

def test_le_service_et_la_photographie_servent_le_detail(depart, donnees):
    from sim.service import ServeurMonde
    monde = copy.deepcopy(depart)
    assert "modificateurs" not in build_snapshot_document(monde, 0, 0)
    paris = _paris(monde)
    M.poser(monde, "moulin", "batiment:moulin-de-paris", {"cellule": paris}, donnees)
    photo = build_snapshot_document(monde, 0, 0)["modificateurs"]
    assert photo["poses"][0]["source"] == "batiment:moulin-de-paris"
    lieu0 = next(l for l in photo["lieux"] if (l["cell_id"], l["rang"]) == (paris, 0))
    assert lieu0["grandeurs"]["recolte"]["facteur"] == pytest.approx(1.10)
    assert len(photo["lieux"]) == len(monde.cells[paris].lieux)
    with ServeurMonde(("127.0.0.1", 0), 0, 0) as serveur:
        vide = json.loads(serveur._construire_etat(0, -1).modificateurs)
        assert vide["poses"] == [] and vide["lieux"] == [] and vide["tick"] == 0
        M.poser(serveur.world, "moulin", "batiment:moulin-de-paris", {"cellule": paris}, donnees)
        servi = json.loads(serveur._construire_etat(0, -1).modificateurs)
        assert servi["poses"] == photo["poses"] and servi["lieux"] == photo["lieux"]
