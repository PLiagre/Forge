"""Le pays d'un seul tenant et ses quatre jauges (CAP.md, jalon 6 ; VISION.md, décisions 36, 38 et 39).

- Le pays : les pays sans suzerain se partagent tous les lieux tenus du monde,
  chacun une fois ; un vassal compté deux fois se voit ; les totaux d'un pays
  sont la somme de ses lieux ; `/pays` sert le même document.
- Les jauges : leurs règles viennent des données et refusent ce qui n'y tient
  pas ; les points naissent des compétences du chef, une fois par mois ; un
  mois de famine ôte de la Concorde, et une Concorde basse pose ses départs au
  pays, dans le registre des modificateurs ; un geste dépense ses points et se
  refuse avec sa raison ; l'IA le dépose par le même chemin que le joueur, et
  les deux donnent le même monde.
- Le mois des jauges se joue hors du tick, avant lui, comme l'IA : les trois
  boucles (service, `python -m sim`, `python -m forge`) l'appellent.
"""
import copy
import json
import random

import pytest

import sim.constants as c
from sim import engine, jauges as J, modificateurs as M, pays as P
from sim.intentions import IntentionRefusee, recevoir_intention
from sim.world import World


@pytest.fixture(scope="module")
def depart():
    return World.charger(rng_seed=0)


@pytest.fixture(scope="module")
def regles():
    return J.charger_regles()


def _tenus(monde):
    return sorted((cid, lieu.rang) for cid, cell in monde.cells.items() for lieu in cell.lieux if lieu.maitre is not None)


def _jouer(monde, rng, numero):
    """Un tour de boucle de jeu, sans l'IA : le mois des jauges, puis le tick."""
    J.avant_le_tick(monde)
    engine.tick(monde, rng, numero)


def _lieux_du_pays(document):
    return sorted((l["cell_id"], l["rang"]) for l in document["lieux"] + document["lieux_des_vassaux"])


# --- Le pays -------------------------------------------------------------------

def test_les_pays_sans_suzerain_font_tous_les_lieux_tenus(depart):
    index = P.index_des_pays(depart)
    racines = P.pays_sans_suzerain(depart)
    assert racines
    vus = [cle for racine in racines for cle in _lieux_du_pays(P.pays(depart, racine, index))]
    assert vus and sorted(vus) == _tenus(depart) and len(vus) == len(set(vus))
    # Contre-épreuve : un vassal compté deux fois (sous deux suzerains) donne un doublon.
    tenus, vassaux = index
    vassal = next(v for vs in vassaux.values() for v in vs if tenus.get(v))
    autre = next(r for r in racines if vassal not in P._descendants(r, vassaux))
    double = (tenus, {**vassaux, autre: [*vassaux.get(autre, []), vassal]})
    vus = [cle for racine in racines for cle in _lieux_du_pays(P.pays(depart, racine, double))]
    with pytest.raises(AssertionError):
        assert len(vus) == len(set(vus))


def test_les_totaux_d_un_pays_sont_la_somme_de_ses_lieux(depart):
    monde = copy.deepcopy(depart)
    rng = random.Random(0)
    for numero in range(31):
        engine.tick(monde, rng, numero)
    france = P.pays(monde, "grande-3")
    lieux = _lieux_du_pays(france)
    assert lieux and france["suzerain"] is None and france["maison"]["nom"]
    assert france["totaux"]["lieux"] == len(lieux)
    assert france["totaux"]["habitants"] == sum(monde.cells[cid].lieux[rang].population for cid, rang in lieux)
    recolte = sum(jour.recoltes[cid][rang] for jour in monde.flux.jours.values()
                  if jour.recoltes for cid, rang in lieux if cid in jour.recoltes)
    assert france["totaux"]["recolte_30j_kg"] == pytest.approx(recolte) and recolte > 0
    vassal = next(m for m in monde.maisons if m.suzerain == "grande-3" and P.pays(monde, m.id)["lieux"])
    assert vassal.id in france["vassaux"] and vassal.id in france["vassaux_tous"]
    assert set(_lieux_du_pays(P.pays(monde, vassal.id))) <= set(lieux)
    with pytest.raises(P.PaysInconnu):
        P.pays(monde, "maison-inventee")


# --- Les jauges : les règles ----------------------------------------------------

def test_les_regles_viennent_des_donnees(regles):
    assert set(regles.jauges) == {"concorde", "renom", "droit"}
    assert set(regles.points) == {"plume", "sceau", "epee"}
    assert (regles.jauges["concorde"]["minimum"], regles.jauges["concorde"]["maximum"]) == (-3, 3)
    assert {p["domaine"] for p in regles.points.values()} == set(regles.domaines)


@pytest.mark.parametrize("chemin, valeur, motif", [
    (("jauges", "concorde", "modificateurs"), {"nourriture_kg": 0.1}, "ne lit pas"),
    (("jauges", "concorde", "modificateurs"), {"levee": 0.1}, "ne lit pas"),
    (("jauges", "concorde", "depart"), 9, "entre minimum et maximum"),
    (("points", "plume", "domaine"), "astrologie", "domaines"),
    (("gestes", "affermir_la_concorde", "cout"), {"grain": 50}, "Plume"),
    (("gestes", "affermir_la_concorde", "effet"), {"concorde": 0}, "écart non nul"),
])
def test_une_regle_qui_ne_tient_pas_est_refusee(chemin, valeur, motif):
    import tomllib
    with open(J._CHEMIN, "rb") as fichier:
        document = tomllib.load(fichier)
    cible = document
    for cle in chemin[:-1]:
        cible = cible[cle]
    cible[chemin[-1]] = valeur
    with pytest.raises(J.JaugeInvalide, match=motif):
        J.lire_regles(document)


def test_les_competences_des_chefs_de_1400(depart, regles):
    vues = {m.id: J.competences(depart, m.id, regles) for m in depart.maisons}
    connues = {k: v for k, v in vues.items() if v is not None}
    assert len(connues) > len(depart.maisons) // 2
    assert all(set(v) == set(regles.domaines) and all(regles.competence_min <= x <= regles.competence_max
                                                       for x in v.values()) for v in connues.values())
    autre_graine = World.charger(rng_seed=42)
    assert vues == {m.id: J.competences(autre_graine, m.id, regles) for m in depart.maisons}
    sans_chef = [m.id for m in depart.maisons if not (depart.chefs.get(m.id) or {}).get("personnage")]
    assert all(vues[m] is None for m in sans_chef)
    if sans_chef:
        assert J.document_des_jauges(depart, sans_chef[0], regles)["absents"]["competences"]


# --- Les jauges : le mois, les causes, les modificateurs --------------------------

def test_le_premier_mois_ne_change_rien_avant_son_terme(depart):
    """Avant le premier mois, ni jauge écrite ni modificateur posé : le monde est celui d'avant."""
    monde, temoin = copy.deepcopy(depart), copy.deepcopy(depart)
    with pytest.MonkeyPatch.context() as ctx:
        ctx.setattr(J, "mettre_a_jour", lambda *a, **k: pytest.fail("jauges avant le mois"))
        rng = random.Random(0)
        for numero in range(c.FENETRE_FLUX_TICKS):
            _jouer(temoin, rng, numero)
    rng = random.Random(0)
    for numero in range(c.FENETRE_FLUX_TICKS):
        engine.tick(monde, rng, numero)
    assert monde.jauges == {} and monde.to_dict() == temoin.to_dict()
    # Le mois venu, la boucle le joue ; le tick nu, jamais.
    assert J.mois_ecoule(temoin)
    nu = copy.deepcopy(temoin)
    engine.tick(nu, random.Random(0), nu.ticks_ecoules)
    assert nu.jauges == {}
    _jouer(temoin, random.Random(0), temoin.ticks_ecoules)
    assert temoin.jauges


def test_les_points_naissent_chaque_mois_des_competences(depart, regles):
    monde = copy.deepcopy(depart)
    rng = random.Random(0)
    for numero in range(2 * c.FENETRE_FLUX_TICKS + 1):
        _jouer(monde, rng, numero)
    for maison in ("grande-3", "grande-1", "seigneurie-1"):
        comp = J.competences(monde, maison, regles)
        valeurs = J.etat(monde, maison, regles)
        for nom, reserve in regles.points.items():
            assert valeurs[nom] == pytest.approx(2 * comp[reserve["domaine"]] * reserve["par_point_de_competence_par_mois"])
    assert all(v["plume"] >= 0 for v in monde.jauges.values())


def test_les_chefs_du_maghreb_gagnent_leurs_points(depart, regles, tmp_path):
    """Tlemcen et le Zab ont un chef (#1052) ; `grande-21`, sans chef, garde « aucun point »."""
    from sim import personnages as perso
    monde = copy.deepcopy(depart)
    rng = random.Random(0)
    for numero in range(2 * c.FENETRE_FLUX_TICKS + 1):
        _jouer(monde, rng, numero)
    for maison in ("grande-24", "seigneurie-6"):
        comp = J.competences(monde, maison, regles)
        assert comp is not None
        valeurs = J.etat(monde, maison, regles)
        for nom, reserve in regles.points.items():
            assert valeurs[nom] == pytest.approx(2 * comp[reserve["domaine"]] * reserve["par_point_de_competence_par_mois"])
        assert J.document_des_jauges(monde, maison, regles)["absents"] == {}
        assert sum(valeurs[nom] for nom in regles.points) > 0
    # Contre-épreuve : une maison sans chef n'a ni compétence ni point, et le dit.
    assert J.competences(monde, "grande-21", regles) is None
    assert all(J.etat(monde, "grande-21", regles)[nom] == 0 for nom in regles.points)
    assert J.document_des_jauges(monde, "grande-21", regles)["absents"]["competences"]
    # Contre-épreuve du chargement : un chef nommé sans source est refusé.
    catalogue = json.loads(perso.CHEMIN.read_text(encoding="utf-8"))
    for maison in ("seigneurie-6", "grande-24"):
        copie = copy.deepcopy(catalogue)
        fiche = next(f for f in copie["chefs"] if f["maison"] == maison)
        assert fiche["nom"]
        fiche["sources"]["identite"] = None
        chemin = tmp_path / f"{maison}.json"
        chemin.write_text(json.dumps(copie), encoding="utf-8")
        with pytest.raises(ValueError):
            perso.charger_catalogue(depart.maisons, chemin)


def test_un_mois_de_famine_ote_de_la_concorde_et_pose_ses_departs(depart, regles):
    monde = copy.deepcopy(depart)
    rng = random.Random(0)
    for numero in range(c.FENETRE_FLUX_TICKS):
        engine.tick(monde, rng, numero)
    # Le mois écoulé : tous les lieux de la maison Bar notés affamés chaque jour.
    bar = "seigneurie-1"
    lieux = [(cid, l.rang) for cid, cell in monde.cells.items() for l in cell.lieux if l.maitre == bar]
    assert lieux
    for jour in monde.flux.jours.values():
        jour.affames.update(lieux)
    raisons = {}
    J.mettre_a_jour(monde, regles, raisons)
    assert J.etat(monde, bar, regles)["concorde"] == regles.causes["famine_concorde"]
    assert raisons[bar]["affames"] == len(lieux)
    poses = [p for p in monde.modificateurs if p.source == f"jauge:concorde:{bar}"]
    assert len(poses) == 1 and poses[0].grandeur == "departs" and poses[0].cible == ("pays", bar)
    assert poses[0].valeur == pytest.approx(regles.causes["famine_concorde"] * regles.jauges["concorde"]["modificateurs"]["departs"])
    facteurs = M.facteurs_du_monde(monde)["departs"]
    assert all(facteurs[cle] == pytest.approx(1 + poses[0].valeur) for cle in lieux)
    # Une maison sans famine garde sa Concorde, et ne reçoit rien.
    assert J.etat(monde, "grande-3", regles)["concorde"] == 0
    assert not [p for p in monde.modificateurs if p.source == "jauge:concorde:grande-3"]


# --- Les gestes ----------------------------------------------------------------

def _monde_au_mois(depart, regles, maison, **valeurs):
    monde = copy.deepcopy(depart)
    rng = random.Random(0)
    for numero in range(c.FENETRE_FLUX_TICKS):
        engine.tick(monde, rng, numero)
    etat = J.etat(monde, maison, regles) | valeurs
    monde.jauges[maison] = etat
    J.poser_les_modificateurs(monde, regles)
    return monde, rng


def test_un_geste_depense_ses_points_ou_se_refuse(depart, regles):
    bar = "seigneurie-1"
    pauvre, _ = _monde_au_mois(depart, regles, bar, concorde=-2, plume=10.0)
    with pytest.raises(IntentionRefusee, match="pas assez de points de Plume"):
        recevoir_intention(pauvre, {"type": "depenser_jauge", "maison": bar, "geste": "affermir_la_concorde"})
    for faux, motif in (({"maison": "maison-inventee"}, "maison inconnue"), ({"geste": "conquerir"}, "geste inconnu")):
        intention = {"type": "depenser_jauge", "maison": bar, "geste": "affermir_la_concorde"} | faux
        with pytest.raises(IntentionRefusee, match=motif):
            recevoir_intention(pauvre, intention)
    riche, rng = _monde_au_mois(depart, regles, bar, concorde=-2, plume=120.0)
    recevoir_intention(riche, {"type": "depenser_jauge", "maison": bar, "geste": "affermir_la_concorde"})
    recevoir_intention(riche, {"type": "depenser_jauge", "maison": bar, "geste": "affermir_la_concorde"})
    with pytest.raises(IntentionRefusee, match="pas assez de points de Plume"):
        recevoir_intention(riche, {"type": "depenser_jauge", "maison": bar, "geste": "affermir_la_concorde"})
    assert J.mois_ecoule(riche)  # ce tour ouvre aussi le mois : la Plume reçoit son mois avant le tick
    mois = J.competences(riche, bar, regles)["gestion"] * regles.points["plume"]["par_point_de_competence_par_mois"]
    _jouer(riche, rng, riche.ticks_ecoules)
    valeurs = J.etat(riche, bar, regles)
    assert valeurs["concorde"] == 0 and valeurs["plume"] == pytest.approx(120.0 + mois - 2 * 50)
    assert not [p for p in riche.modificateurs if p.source == f"jauge:concorde:{bar}"]
    pleine, _ = _monde_au_mois(depart, regles, bar, concorde=3, plume=500.0)
    with pytest.raises(IntentionRefusee, match="déjà à sa borne"):
        recevoir_intention(pleine, {"type": "depenser_jauge", "maison": bar, "geste": "affermir_la_concorde"})


def test_l_ia_depense_ses_jauges_par_le_meme_chemin(depart, regles):
    from sim import ia
    from sim.capitales import toutes_les_maisons_de_l_ia
    cle = "seigneurie-1"
    monde, rng = _monde_au_mois(depart, regles, cle, concorde=-1, plume=60.0)
    maisons = toutes_les_maisons_de_l_ia(monde)
    jour = next(t for t in range(monde.ticks_ecoules, monde.ticks_ecoules + c.FENETRE_FLUX_TICKS)
                if ia._jour_de_la_part(cle, t))
    while monde.ticks_ecoules < jour:
        _jouer(monde, rng, monde.ticks_ecoules)
    J.avant_le_tick(monde)
    joueur = copy.deepcopy(monde)
    releve = []
    ia.jouer_ia(monde, releve, maisons)
    gestes = [e for e in releve if e["intention"]["type"] == "depenser_jauge"]
    assert [g["intention"] for g in gestes if g["intention"]["maison"] == cle] == [
        {"type": "depenser_jauge", "maison": cle, "geste": "affermir_la_concorde"}]
    gestes_bar = [g for g in gestes if g["intention"]["maison"] == cle]
    assert gestes_bar[0]["raison"]["regle"] == "concorde_sous_son_neutre" and "refus" not in gestes_bar[0]
    # Le joueur qui dépose les mêmes intentions obtient le même monde.
    for entree in releve:
        if "refus" not in entree:
            recevoir_intention(joueur, entree["intention"])
    rng_joueur = copy.deepcopy(rng)
    engine.tick(monde, rng, monde.ticks_ecoules)
    engine.tick(joueur, rng_joueur, joueur.ticks_ecoules)
    assert json.dumps(monde.to_dict(), sort_keys=True) == json.dumps(joueur.to_dict(), sort_keys=True)
    assert J.etat(monde, cle, regles)["concorde"] == 0


# --- Le geste de points du mois de l'IA : au plus un, dans l'ordre -----------------

_GESTES_DE_POINTS = ("depenser_jauge", "ameliorer_une_province")
_SEIGNEURIE = "seigneurie-1"


@pytest.fixture(scope="module")
def au_jour_de_part(depart, regles):
    """`seigneurie-1` à son jour de part du premier mois, le mois des jauges joué, et les maisons de l'IA."""
    from sim import ia
    from sim.capitales import toutes_les_maisons_de_l_ia
    monde, rng = _monde_au_mois(depart, regles, _SEIGNEURIE)
    maisons = toutes_les_maisons_de_l_ia(monde)
    jour = next(t for t in range(monde.ticks_ecoules, monde.ticks_ecoules + c.FENETRE_FLUX_TICKS)
                if ia._jour_de_la_part(_SEIGNEURIE, t))
    while monde.ticks_ecoules < jour:
        _jouer(monde, rng, monde.ticks_ecoules)
    J.avant_le_tick(monde)
    return monde, rng, maisons


def _gestes_de_points(propositions):
    return [p for p in propositions
            if p["intention"]["maison"] == _SEIGNEURIE and p["intention"]["type"] in _GESTES_DE_POINTS]


def _points_au_jour(au_jour_de_part, regles, monde=None, **valeurs):
    """Une copie du monde du jour, ses jauges posées, et les gestes de points que l'IA propose à `seigneurie-1`."""
    from sim import ia
    depart_du_jour, _, maisons = au_jour_de_part
    copie = copy.deepcopy(depart_du_jour if monde is None else monde)
    copie.jauges[_SEIGNEURIE] = J.etat(copie, _SEIGNEURIE, regles) | valeurs
    J.poser_les_modificateurs(copie, regles)
    return copie, _gestes_de_points(ia.decider_intentions(copie, [], maisons))


def _bourgs_de(monde):
    return sorted(cid for cid, cell in monde.cells.items()
                  for lieu in cell.lieux if lieu.rang == 0 and lieu.maitre == _SEIGNEURIE)


def _moins_chere(monde, regles):
    """La province dont le niveau suivant coûte le moins, relue sur le monde (la plus petite cell_id à égalité)."""
    table = regles.amelioration
    return min(_bourgs_de(monde), key=lambda cid: (
        table["cout_premier_niveau"] * table["facteur_par_niveau"] ** monde.niveaux_de_province.get(cid, 0), cid))


def _monde_a_trois_provinces(au_jour_de_part):
    """Deux bourgs d'autres maisons passés à `seigneurie-1` à la main : l'amorçage n'en donne qu'un à chacune."""
    monde = copy.deepcopy(au_jour_de_part[0])
    for cid in [cid for cid in sorted(monde.cells) if cid not in _bourgs_de(monde)][:2]:
        next(lieu for lieu in monde.cells[cid].lieux if lieu.rang == 0).maitre = _SEIGNEURIE
    assert len(_bourgs_de(monde)) == 3
    return monde


def _controler_concorde(au_jour_de_part, regles):
    _, propositions = _points_au_jour(au_jour_de_part, regles, concorde=-1, plume=60.0, sceau=40.0, droit=50)
    assert len(propositions) == 1
    assert propositions[0]["intention"] == {"type": "depenser_jauge", "maison": _SEIGNEURIE, "geste": "affermir_la_concorde"}
    assert propositions[0]["raison"]["regle"] == "concorde_sous_son_neutre"


def _controler_droit(au_jour_de_part, regles):
    _, propositions = _points_au_jour(au_jour_de_part, regles, concorde=0, plume=60.0, sceau=40.0, droit=50)
    assert len(propositions) == 1
    intention, raison = propositions[0]["intention"], propositions[0]["raison"]
    assert intention == {"type": "depenser_jauge", "maison": _SEIGNEURIE, "geste": "asseoir_le_droit"}
    assert raison["regle"] == "droit_sous_son_maximum"
    assert (raison["droit"], raison["maximum"], raison["sceau"]) == (50, 100, 40.0)
    assert raison["cout"] == regles.gestes["asseoir_le_droit"]["cout"]
    assert (raison["concorde"], raison["plume"]) == (0, 60.0)


def _controler_province(au_jour_de_part, regles):
    riche = _monde_a_trois_provinces(au_jour_de_part)
    cellules = _bourgs_de(riche)
    choisies = []
    for niveaux in ({}, {min(cellules): 1}):
        riche.niveaux_de_province = dict(niveaux)
        attendue = _moins_chere(riche, regles)
        _, propositions = _points_au_jour(au_jour_de_part, regles, riche, concorde=0, droit=100, plume=20.0, sceau=7.0)
        assert len(propositions) == 1
        intention, raison = propositions[0]["intention"], propositions[0]["raison"]
        assert intention == {"type": "ameliorer_une_province", "maison": _SEIGNEURIE, "cell": attendue}
        niveau = niveaux.get(attendue, 0)
        assert raison == {"regle": "province_la_moins_chere", "cell_id": attendue, "niveau": niveau,
                          "cout": regles.amelioration["cout_premier_niveau"] * regles.amelioration["facteur_par_niveau"] ** niveau,
                          "plume": 20.0, "concorde": 0, "droit": 100, "sceau": 7.0}
        choisies.append(attendue)
    # Un niveau posé sur la première renvoie le choix à la suivante la moins chère.
    assert choisies[0] == min(cellules) and choisies[1] == sorted(cellules)[1]


def _controler_plume_gardee(au_jour_de_part, regles):
    _, aucun = _points_au_jour(au_jour_de_part, regles, concorde=-1, plume=20.0, sceau=0.0, droit=50)
    assert aucun == []
    _, droit = _points_au_jour(au_jour_de_part, regles, concorde=-1, plume=20.0, sceau=40.0, droit=50)
    assert [p["raison"]["regle"] for p in droit] == ["droit_sous_son_maximum"]


def _controler_au_plus_un(au_jour_de_part, regles):
    # Le Droit et la province sont payables ensemble : un seul geste.
    _, propositions = _points_au_jour(au_jour_de_part, regles, concorde=0, plume=60.0, sceau=40.0, droit=50)
    assert len(propositions) == 1


def test_l_ia_points_un_seul_geste_dans_l_ordre(au_jour_de_part, regles):
    _controler_concorde(au_jour_de_part, regles)
    _controler_droit(au_jour_de_part, regles)
    _controler_province(au_jour_de_part, regles)
    _controler_plume_gardee(au_jour_de_part, regles)
    _controler_au_plus_un(au_jour_de_part, regles)


def test_l_ia_points_aucun_geste_un_autre_jour(au_jour_de_part, regles):
    from sim import ia
    monde, rng, maisons = au_jour_de_part
    suivant = copy.deepcopy(monde)
    engine.tick(suivant, copy.deepcopy(rng), suivant.ticks_ecoules)
    assert not ia._jour_de_la_part(_SEIGNEURIE, suivant.ticks_ecoules)
    suivant.jauges[_SEIGNEURIE] = J.etat(suivant, _SEIGNEURIE, regles) | {"concorde": -1, "plume": 60.0, "sceau": 40.0}
    assert _gestes_de_points(ia.decider_intentions(suivant, [], maisons)) == []


def test_l_ia_points_contre_epreuves(au_jour_de_part, regles, monkeypatch):
    from sim import ia
    originale, originale_decider, originale_province = ia._proposition_de_points, ia.decider_intentions, ia._proposition_de_province
    # L'ancienne règle, la concorde seule : les cas du Droit et de la province échouent.
    monkeypatch.setattr(ia, "_proposition_de_points", lambda monde, maison, cle, regles_: ia._proposition_de_concorde(
        monde, maison, cle, regles_, J.etat(monde, cle, regles_)))
    _controler_concorde(au_jour_de_part, regles)
    with pytest.raises(AssertionError):
        _controler_droit(au_jour_de_part, regles)
    with pytest.raises(AssertionError):
        _controler_province(au_jour_de_part, regles)
    monkeypatch.setattr(ia, "_proposition_de_points", originale)

    # Une version qui rend tous les gestes payables : « au plus un » échoue.
    def tous(monde, releve, maisons=None):
        propositions = originale_decider(monde, releve, maisons)
        maison = next(m for m in maisons if ia._cle_du_grenier(m) == _SEIGNEURIE)
        valeurs = J.etat(monde, _SEIGNEURIE, regles)
        for proposer in (ia._proposition_de_droit, ia._proposition_de_province):
            proposition = proposer(monde, maison, _SEIGNEURIE, regles, valeurs)
            if proposition is not None:
                propositions.append(proposition)
        return propositions

    monkeypatch.setattr(ia, "decider_intentions", tous)
    with pytest.raises(AssertionError):
        _controler_au_plus_un(au_jour_de_part, regles)
    monkeypatch.setattr(ia, "decider_intentions", originale_decider)

    # Une version sans la Plume gardée : la province passe avec la Concorde basse.
    def sans_plume_gardee(monde, maison, cle, regles_, valeurs):
        neutre = regles_.jauges["concorde"]["neutre"]
        return originale_province(monde, maison, cle, regles_, valeurs | {"concorde": max(valeurs["concorde"], neutre)})

    monkeypatch.setattr(ia, "_proposition_de_province", sans_plume_gardee)
    with pytest.raises(AssertionError):
        _controler_plume_gardee(au_jour_de_part, regles)


def _riche_au_jour(au_jour_de_part, regles):
    riche = _monde_a_trois_provinces(au_jour_de_part)
    riche.jauges[_SEIGNEURIE] = J.etat(riche, _SEIGNEURIE, regles) | {"concorde": 0, "droit": 100, "plume": 20.0}
    J.poser_les_modificateurs(riche, regles)
    return riche


def test_l_ia_points_meme_chemin_meme_monde(au_jour_de_part, regles):
    from sim import ia
    from sim.tests.test_intentions import _controle_chemin_unique
    _, rng, maisons = au_jour_de_part
    riche = _riche_au_jour(au_jour_de_part, regles)
    _controle_chemin_unique(riche, lambda m, releve: ia.jouer_ia(m, releve, maisons), "ameliorer_une_province")
    joueur = copy.deepcopy(riche)
    releve = []
    ia.jouer_ia(riche, releve, maisons)
    acceptees = [e["intention"] for e in releve if "refus" not in e]
    choisie = next(i["cell"] for i in acceptees if i["type"] == "ameliorer_une_province" and i["maison"] == _SEIGNEURIE)
    for intention in acceptees:
        recevoir_intention(joueur, intention)
    rng_joueur = copy.deepcopy(rng)
    engine.tick(riche, rng, riche.ticks_ecoules)
    engine.tick(joueur, rng_joueur, joueur.ticks_ecoules)
    assert json.dumps(riche.to_dict(), sort_keys=True) == json.dumps(joueur.to_dict(), sort_keys=True)
    assert riche.niveaux_de_province[choisie] == 1 and joueur.niveaux_de_province[choisie] == 1

    # Contre-épreuve : une IA qui améliore dans le monde au lieu de déposer l'intention échoue.
    def tricher(m, releve_):
        for proposition in ia.decider_intentions(m, releve_, maisons):
            intention = proposition["intention"]
            if intention["type"] == "ameliorer_une_province":
                J.appliquer_amelioration(m, intention["maison"], intention["cell"])
            releve_.append({"tick": m.ticks_ecoules, **proposition})

    with pytest.raises(AssertionError):
        _controle_chemin_unique(_riche_au_jour(au_jour_de_part, regles), tricher, "ameliorer_une_province")


def test_le_service_sert_le_pays_et_ses_jauges(depart):
    from sim.service import ServeurMonde
    with ServeurMonde(("127.0.0.1", 0), 0, 0) as serveur:
        document = json.loads(serveur.octets_du_pays("grande-3"))
        attendu = P.pays(serveur.world, "grande-3")
        # Les jauges, la date et les bâtiments s'ajoutent au pays ; les bâtiments ont leurs épreuves (test_batiments.py).
        assert {k: v for k, v in document.items() if k not in ("jauges", "date", "batiments")} == json.loads(json.dumps(attendu))
        assert set(document["jauges"]["jauges"]) == {"concorde", "renom", "droit"}
        assert set(document["jauges"]["points"]) == {"plume", "sceau", "epee"}
        with pytest.raises(P.PaysInconnu):
            serveur.octets_du_pays("maison-inventee")


def test_le_service_dit_les_jauges_et_ce_qu_elles_posent(depart, regles):
    from sim.service import ServeurMonde
    with ServeurMonde(("127.0.0.1", 0), 0, 0) as serveur:
        document = json.loads(serveur.octets_du_pays("seigneurie-1"))["jauges"]
    # Les mots des données : le `dit` de chaque jauge et de chaque réserve.
    assert {n: j["dit"] for n, j in document["jauges"].items()} == {n: j["dit"] for n, j in regles.jauges.items()}
    assert {n: p["dit"] for n, p in document["points"].items()} == {n: p["dit"] for n, p in regles.points.items()}
    assert all(j["dit"] for j in (*document["jauges"].values(), *document["points"].values()))
    # Le nom de chaque grandeur sur laquelle une jauge pose, relu dans les données des modificateurs.
    grandeurs = M.charger_donnees().grandeurs
    assert document["grandeurs"] == {"commerce": "Commerce", "departs": "Départs", "prelevement": "Prélèvement"}
    assert all(document["grandeurs"][g] == grandeurs[g].nom for g in document["grandeurs"])
    # Après un geste, chaque grandeur posée a son nom.
    monde = copy.deepcopy(depart)
    monde.jauges["seigneurie-1"] = J.etat(monde, "seigneurie-1", regles) | {"sceau": 31.5}
    J.appliquer_geste(monde, "seigneurie-1", "asseoir_le_droit", regles)
    servi = J.document_des_jauges(monde, "seigneurie-1", regles)
    assert servi["modificateurs"] and all(m["grandeur"] in servi["grandeurs"] for m in servi["modificateurs"])
    assert {m["grandeur"] for m in servi["modificateurs"]} == {"prelevement"}


def test_les_trois_boucles_jouent_le_mois(monkeypatch, tmp_path):
    """Le service, `python -m sim` (rejeu compris) et `python -m forge` comptent le mois avant le tick."""
    from forge.__main__ import _simuler
    from sim.__main__ import _simulate
    from sim.service import ServeurMonde
    vus = []
    vrai = J.mettre_a_jour
    monkeypatch.setattr(J, "mettre_a_jour", lambda monde, *a, **k: (vus.append(monde.ticks_ecoules), vrai(monde, *a, **k)))
    ticks = c.FENETRE_FLUX_TICKS + 1
    _, monde = _simulate(ticks, 0)
    assert vus == [c.FENETRE_FLUX_TICKS] and monde.jauges
    vus.clear()
    with ServeurMonde(("127.0.0.1", 0), 0, 0) as serveur:
        for _ in range(ticks):
            serveur.jouer_un_tick()
        assert vus == [c.FENETRE_FLUX_TICKS] and serveur.world.jauges == monde.jauges
    vus.clear()
    _simuler(ticks, 0, tmp_path / "monde.json")
    assert vus == [c.FENETRE_FLUX_TICKS]


def test_les_raisons_d_un_geste_s_ecrivent_en_points(depart, regles):
    """Les deux raisons d'un geste disent leurs nombres en points, au dixième, avec leur accord (le panneau du pays les lit telles quelles)."""
    import re
    bar = "seigneurie-1"
    concorde, droit = "affermir_la_concorde", "asseoir_le_droit"
    plume = "pas assez de points de Plume : 50 points demandés, "
    cas = [
        ({"concorde": -2, "plume": 10.0}, concorde, [], plume + "10 points disponibles"),
        ({"concorde": -2, "plume": 1.5}, concorde, [], plume + "1,5 point disponible"),
        ({"concorde": -2, "plume": 0.0}, concorde, [], plume + "0 point disponible"),
        ({"concorde": -2, "plume": 35.04}, concorde, [], plume + "35 points disponibles"),
        ({"sceau": 31.5}, droit, [droit], "pas assez de points de Sceau : 30 points demandés, 1,5 point disponible"),
        ({"concorde": 3, "plume": 500.0}, concorde, [], "Concorde déjà à sa borne : 3 points"),
    ]
    for valeurs, geste, engages, attendu in cas:
        monde, _ = _monde_au_mois(depart, regles, bar, **valeurs)
        texte = J.verifier_geste(monde, bar, geste, regles, engages)
        assert texte == attendu
        if not engages:  # `/pays` ne compte pas les gestes déjà déposés
            assert J.document_des_jauges(monde, bar, regles)["gestes"][geste]["refus"] == attendu
        nombres = list(re.finditer(r"(?<![\d,])\d+(?:,\d+)?(?![\d,])", texte))
        assert nombres
        assert all(texte[n.end():].startswith((" point", " points")) for n in nombres), texte
    assert J._points(-3) == "-3 points"
    assert J._points(0.05) == "0,1 point"
    assert J._points(-0.04) == "0 point"
    assert J._accord(1.5, "demandé") == "demandé" and J._accord(2, "demandé") == "demandés"


def test_un_geste_du_panneau_donne_le_meme_monde_qu_a_la_main(regles):
    """Le panneau du pays dépose `depenser_jauge` par `POST /intention` : mêmes octets, ou écrits à la main, même monde."""
    import threading
    from sim.service import ServeurMonde
    from sim.tests.test_monde import requete_service
    bar = "seigneurie-1"
    panneau = b'{"type":"depenser_jauge","maison":"seigneurie-1","geste":"asseoir_le_droit"}'
    main = json.dumps({"geste": "asseoir_le_droit", "maison": bar, "type": "depenser_jauge"}, indent=1).encode()
    serveurs, fils = [], []
    try:
        for _ in range(2):
            serveur = ServeurMonde(("127.0.0.1", 0), 0, 0)
            serveurs.append(serveur)
            fil = threading.Thread(target=serveur.serve_forever)
            fil.start()
            fils.append(fil)
            with serveur.verrou_tick:
                serveur.world.jauges[bar] = J.etat(serveur.world, bar, regles) | {"sceau": 31.5}
                J.poser_les_modificateurs(serveur.world, regles)
        (a, b) = serveurs
        recu = {"acceptee": True, "appliquee_au_tick": 0}
        assert requete_service(a.server_port, "/intention", "POST", panneau)[:2] == (200, recu)
        assert requete_service(b.server_port, "/intention", "POST", main)[:2] == (200, recu)
        avant = json.dumps(a.world.to_dict(), sort_keys=True)
        attente = list(a.world.intentions_en_attente)
        statut, refus, _ = requete_service(a.server_port, "/intention", "POST", panneau)
        assert statut == 400 and refus == {
            "acceptee": False, "erreur": "pas assez de points de Sceau : 30 points demandés, 1,5 point disponible"}
        assert json.dumps(a.world.to_dict(), sort_keys=True) == avant and a.world.intentions_en_attente == attente
        for serveur in serveurs:
            assert requete_service(serveur.server_port, "/tick?n=1", "POST")[0] == 200
        assert json.dumps(a.world.to_dict(), sort_keys=True) == json.dumps(b.world.to_dict(), sort_keys=True)
        assert requete_service(a.server_port, f"/pays?maison={bar}")[2] == requete_service(b.server_port, f"/pays?maison={bar}")[2]
        valeurs = J.etat(a.world, bar, regles)
        assert valeurs["sceau"] == pytest.approx(1.5) and valeurs["droit"] == 60
        assert avant != json.dumps(a.world.to_dict(), sort_keys=True)
    finally:
        for serveur in serveurs:
            serveur.shutdown()
        for fil in fils:
            fil.join()
        for serveur in serveurs:
            serveur.server_close()


# --- Améliorer une province (lot #1053) -----------------------------------------
#
# Le geste qui ne s'épuise jamais : de la Plume contre un niveau de plus à une
# cellule de la maison, de plus en plus cher, et de vrais kilos de plus à sa récolte.

NOURRITURE = c.MARCHANDISE_NOURRITURE
AMELIORER = {"type": "ameliorer_une_province"}
CONCORDE = {"type": "depenser_jauge", "geste": "affermir_la_concorde"}


def _octets(monde):
    return json.dumps(monde.to_dict(), sort_keys=True, ensure_ascii=False)


def _bourgs_tenus(monde, maison):
    return sorted(cid for cid, cell in monde.cells.items() if any(l.rang == 0 and l.maitre == maison for l in cell.lieux))


def _avec_plume(depart, maison, plume):
    monde = copy.deepcopy(depart)
    monde.jauges[maison] = J.etat(monde, maison, J.charger_regles()) | {"plume": plume}
    return monde


def _ameliorer(maison, cell):
    return {**AMELIORER, "maison": maison, "cell": cell}


def _concorde(maison):
    return {**CONCORDE, "maison": maison}


def _couts_croissants(regles, niveaux=20):
    """Les niveaux 1 à `niveaux` de `regles` : le premier coûte le prix des données, chacun plus que le précédent."""
    import types
    vide = types.SimpleNamespace(niveaux_de_province={})
    couts = [J.cout_du_niveau_suivant(vide, 0, regles, deja_deposees=k) for k in range(niveaux)]
    assert couts[0] == regles.amelioration["cout_premier_niveau"] == 6
    for k in range(niveaux - 1):
        assert couts[k + 1] > couts[k], f"le niveau {k + 2} ne coûte pas plus que le niveau {k + 1}"
    return couts


def _maison_de_gestion_un(monde, regles):
    """Une maison dont le chef a une gestion de 1 et qui tient le bourg d'une cellule, dérivée des données."""
    echantillon = [(m.id, _bourgs_tenus(monde, m.id)) for m in monde.maisons
                   if (J.competences(monde, m.id, regles) or {}).get("gestion") == 1]
    echantillon = [(maison, cells[0]) for maison, cells in echantillon if cells]
    assert echantillon, "aucune maison de gestion 1 qui tienne un bourg : l'échantillon est vide"
    return echantillon[0]


def _autre_maitre(monde, maison):
    """Une cellule dont le bourg est tenu par une autre maison, et cette maison."""
    cid = next(cid for cid in sorted(monde.cells) if monde.cells[cid].lieux[0].maitre != maison)
    return cid, monde.cells[cid].lieux[0].maitre


def _paris(monde):
    cid = monde.attribution_villes.placees["Paris"]
    return cid, monde.cells[cid].lieux[0].maitre


def _recoltes_versees(monde, alea, monkeypatch):
    """Joue un tick ; rend la récolte versée à chaque cellule (la mesure de `_verser_recolte` du moulin)."""
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


def _nouvelles_poses(apres, avant):
    return [p for p in apres.modificateurs if p not in avant.modificateurs]


# SC1 — Les données

def test_amelioration_donnees_les_regles_viennent_des_donnees(regles):
    table = regles.amelioration
    assert (table["reserve"], table["cout_premier_niveau"], table["facteur_par_niveau"], table["modificateur"]) == (
        "plume", 6, 1.5, "amelioration_de_province")
    assert table["nom"] == "Améliorer une province" and table["dit"]
    definition = M.charger_donnees().definitions["amelioration_de_province"]
    assert (definition.grandeur, definition.valeur, definition.portee, definition.duree_jours) == ("recolte", 0.02, "cellule", 0)
    assert definition.nom == "Province améliorée"
    # Le panneau du pays (#1046) ne la voit pas parmi ses gestes.
    assert set(regles.gestes) == {"affermir_la_concorde", "asseoir_le_droit"}


def _cas_de_donnees():
    def table(**champs):
        return lambda document, donnees: document["amelioration_de_province"].update(champs)

    def modificateur(**champs):
        def change(document, donnees):
            definition = M.Definition(**{"identifiant": "jauge-epreuve", "nom": "Épreuve", "grandeur": "recolte",
                                         "valeur": 0.02, "portee": "cellule", "duree_jours": 0, **champs})
            document["amelioration_de_province"]["modificateur"] = "jauge-epreuve"
            return M.Donnees(donnees.sources, donnees.grandeurs, {**donnees.definitions, "jauge-epreuve": definition})
        return change

    def une_jauge_province(document, donnees):
        document["jauges"]["province"] = dict(document["jauges"]["concorde"])

    return [
        (table(facteur_par_niveau=1), "coût croissant"),
        (table(facteur_par_niveau=0.5), "coût croissant"),
        (table(cout_premier_niveau=0), "cout_premier_niveau"),
        (table(cout_premier_niveau=-6), "cout_premier_niveau"),
        (table(reserve="grain"), "réserve"),
        (table(modificateur="province-inventee"), "absent des données"),
        (modificateur(portee="pays"), "se pose sur un pays"),
        (modificateur(grandeur="levee"), "que le moteur ne lit pas"),
        (une_jauge_province, "nom réservé"),
    ]


@pytest.mark.parametrize("change, motif", _cas_de_donnees())
def test_amelioration_donnees_une_regle_qui_ne_tient_pas_est_refusee(change, motif):
    import tomllib
    with open(J._CHEMIN, "rb") as fichier:
        document = tomllib.load(fichier)
    donnees = M.charger_donnees()
    donnees = change(document, donnees) or donnees
    with pytest.raises(J.JaugeInvalide, match=motif):
        J.lire_regles(document, donnees)
    # Contre-épreuve : le document du dépôt passe.
    assert J.charger_regles().amelioration["cout_premier_niveau"] == 6


# SC2 — De plus en plus cher, et le premier niveau payable en un an

def test_amelioration_cher_chaque_niveau_coute_plus_que_le_precedent(regles):
    assert _couts_croissants(regles)[:4] == [6, 9, 13.5, 20.25]
    import dataclasses
    plat = dataclasses.replace(regles, amelioration={**regles.amelioration, "facteur_par_niveau": 1.0})
    with pytest.raises(AssertionError):
        _couts_croissants(plat)


def test_amelioration_cher_le_premier_niveau_est_payable_en_un_an(depart, regles):
    maison, cid = _maison_de_gestion_un(depart, regles)
    monde = copy.deepcopy(depart)
    for _ in range(365 // c.FENETRE_FLUX_TICKS - 1):
        J.mettre_a_jour(monde, regles)
    assert J.etat(monde, maison, regles)["plume"] == 5.5
    avant = _octets(monde)
    with pytest.raises(IntentionRefusee) as refus:
        recevoir_intention(monde, _ameliorer(maison, cid))
    assert str(refus.value) == "pas assez de points de Plume : 6 points demandés, 5,5 points disponibles"
    assert _octets(monde) == avant and monde.intentions_en_attente == []
    J.mettre_a_jour(monde, regles)
    assert J.etat(monde, maison, regles)["plume"] == 6.0
    recevoir_intention(monde, _ameliorer(maison, cid))
    assert len(monde.intentions_en_attente) == 1


# SC3 — Les refus, avec leur raison, sans toucher au monde

def test_amelioration_refus_chaque_raison_mot_pour_mot(depart):
    bar = "seigneurie-1"
    (cid,) = _bourgs_tenus(depart, bar)
    monde = _avec_plume(depart, bar, 5.0)
    autre, maitre = _autre_maitre(monde, bar)
    cas = [
        (_ameliorer("x", cid), "maison inconnue ou mal formée : 'x'"),
        (_ameliorer(7, cid), "maison inconnue ou mal formée : 7"),
        (_ameliorer(bar, True), "cell invalide : entier attendu, reçu True"),
        (_ameliorer(bar, "10"), "cell invalide : entier attendu, reçu '10'"),
        (_ameliorer(bar, -1), "cellule inconnue : -1"),
        (_ameliorer(bar, autre), f"pas sur vos terres : le bourg de la cellule {autre} est à {maitre!r}"),
        (_ameliorer(bar, cid), "pas assez de points de Plume : 6 points demandés, 5 points disponibles"),
    ]
    avant = _octets(monde)
    for intention, attendu in cas:
        with pytest.raises(IntentionRefusee) as refus:
            recevoir_intention(monde, intention)
        assert str(refus.value) == attendu
        assert _octets(monde) == avant and monde.intentions_en_attente == []
    with pytest.raises(IntentionRefusee, match="champ manquant : cell"):
        recevoir_intention(monde, {**AMELIORER, "maison": bar})
    # Contre-épreuve : avec 6 points, le même premier dépôt passe : c'est bien la Plume qui refuse.
    riche = _avec_plume(depart, bar, 6.0)
    recevoir_intention(riche, _ameliorer(bar, cid))
    assert len(riche.intentions_en_attente) == 1


def test_amelioration_refus_la_plume_engagee_compte_les_deux_gestes(depart):
    bar = "seigneurie-1"
    (cid,) = _bourgs_tenus(depart, bar)
    # Une amélioration d'abord : « Affermir la concorde » ne trouve plus que 49 points.
    monde = _avec_plume(depart, bar, 55.0)
    recevoir_intention(monde, _ameliorer(bar, cid))
    with pytest.raises(IntentionRefusee) as refus:
        recevoir_intention(monde, _concorde(bar))
    assert str(refus.value) == "pas assez de points de Plume : 50 points demandés, 49 points disponibles"
    assert len(monde.intentions_en_attente) == 1
    # Dans l'autre ordre, sur une copie : la concorde passe, l'amélioration ne trouve plus que 5 points.
    autre = _avec_plume(depart, bar, 55.0)
    recevoir_intention(autre, _concorde(bar))
    with pytest.raises(IntentionRefusee) as refus:
        recevoir_intention(autre, _ameliorer(bar, cid))
    assert str(refus.value) == "pas assez de points de Plume : 6 points demandés, 5 points disponibles"
    assert len(autre.intentions_en_attente) == 1
    # Deux améliorations de la même cellule : 6 puis 9 ; la troisième (13,5) ne trouve plus rien.
    deux = _avec_plume(depart, bar, 15.0)
    recevoir_intention(deux, _ameliorer(bar, cid))
    recevoir_intention(deux, _ameliorer(bar, cid))
    avant = _octets(deux)
    with pytest.raises(IntentionRefusee) as refus:
        recevoir_intention(deux, _ameliorer(bar, cid))
    assert str(refus.value) == "pas assez de points de Plume : 13,5 points demandés, 0 point disponible"
    assert _octets(deux) == avant and len(deux.intentions_en_attente) == 2
    # Contre-épreuve : avec 21 points de plus de Plume, la troisième passe.
    trois = _avec_plume(depart, bar, 28.5)
    for _ in range(3):
        recevoir_intention(trois, _ameliorer(bar, cid))
    assert len(trois.intentions_en_attente) == 3


def test_amelioration_refus_le_tick_ne_leve_pas_jauge_invalide(depart):
    """Les deux gestes déposés dans les limites de la Plume s'appliquent tous deux, sans `JaugeInvalide`."""
    bar = "seigneurie-1"
    (cid,) = _bourgs_tenus(depart, bar)
    monde = _avec_plume(depart, bar, 56.0)
    recevoir_intention(monde, _ameliorer(bar, cid))
    recevoir_intention(monde, _concorde(bar))
    engine.tick(monde, random.Random(0), 0)
    valeurs = J.etat(monde, bar, J.charger_regles())
    assert valeurs["plume"] == 0.0 and monde.niveaux_de_province == {cid: 1}


# SC4 — Le niveau, la pose, et la récolte de la cellule en vrais kilos

def test_amelioration_kilos_le_niveau_la_pose_et_la_recolte_de_la_cellule(depart, regles, monkeypatch):
    cid, maison = _paris(depart)
    monde = _avec_plume(depart, maison, 20.0)
    temoin = copy.deepcopy(monde)
    recevoir_intention(monde, _ameliorer(maison, cid))
    alea = random.Random(0)
    avant = copy.deepcopy(monde)
    engine.tick(monde, alea, 0)
    engine.tick(temoin, random.Random(0), 0)
    assert monde.niveaux_de_province == {cid: 1}
    assert J.etat(monde, maison, regles)["plume"] == 14.0
    poses = _nouvelles_poses(monde, avant)
    assert [(p.identifiant, p.grandeur, p.valeur, p.cible, p.source) for p in poses] == [
        ("amelioration_de_province", "recolte", 0.02, ("cellule", cid), f"jauge:province:{cid}-1")]
    assert "niveaux_de_province" in monde.to_dict() and "niveaux_de_province" not in temoin.to_dict()
    # Le geste ne crée ni ne coûte un kilo : le grenier ne diffère du même tick sans geste que par la
    # récolte en plus de la pose, qui agit dès le tick où le geste s'applique ; posée à la main, la même
    # pose donne le même grenier.
    a_la_main = copy.deepcopy(avant)
    a_la_main.intentions_en_attente.clear()
    a_la_main.jauges = copy.deepcopy(temoin.jauges)
    M.poser(a_la_main, "amelioration_de_province", f"jauge:province:{cid}-1", {"cellule": cid})
    engine.tick(a_la_main, random.Random(0), 0)
    assert monde.greniers[maison] == a_la_main.greniers[maison]
    # Au tick suivant : la cellule reçoit exactement 1,02 fois ce que reçoit le même monde sans la pose.
    sans = copy.deepcopy(monde)
    assert M.retirer(sans, f"jauge:province:{cid}-1") == 1
    verse = _recoltes_versees(monde, copy.deepcopy(alea), monkeypatch)
    verse_sans = _recoltes_versees(sans, copy.deepcopy(alea), monkeypatch)
    assert verse[cid] > 0 and verse[cid] == pytest.approx(verse_sans[cid] * 1.02, rel=1e-12)
    assert all(verse[x] == verse_sans[x] for x in verse_sans if x != cid)
    # Contre-épreuve : contre un monde qui garde la pose, la récolte est la même.
    garde = copy.deepcopy(monde)
    verse_garde = _recoltes_versees(garde, copy.deepcopy(alea), monkeypatch)
    with pytest.raises(AssertionError):
        assert verse[cid] == pytest.approx(verse_garde[cid] * 1.02, rel=1e-12)


def test_amelioration_kilos_un_second_niveau_coute_plus_et_recolte_plus(depart, regles, monkeypatch):
    cid, maison = _paris(depart)
    monde = _avec_plume(depart, maison, 20.0)
    rng = random.Random(0)
    recevoir_intention(monde, _ameliorer(maison, cid))
    engine.tick(monde, rng, 0)
    premier = J.etat(monde, maison, regles)["plume"]
    assert premier == 14.0
    recevoir_intention(monde, _ameliorer(maison, cid))
    engine.tick(monde, rng, 1)
    assert premier - J.etat(monde, maison, regles)["plume"] == 9.0 > 20.0 - premier
    assert monde.niveaux_de_province == {cid: 2}
    assert sorted(p.source for p in monde.modificateurs) == [f"jauge:province:{cid}-1", f"jauge:province:{cid}-2"]
    sans = copy.deepcopy(monde)
    assert M.retirer(sans, f"jauge:province:{cid}-1") + M.retirer(sans, f"jauge:province:{cid}-2") == 2
    verse = _recoltes_versees(monde, copy.deepcopy(rng), monkeypatch)
    verse_sans = _recoltes_versees(sans, copy.deepcopy(rng), monkeypatch)
    assert M.facteurs_du_monde(copy.deepcopy(monde))["recolte"][(cid, 0)] == pytest.approx(1.04)
    assert verse[cid] == pytest.approx(verse_sans[cid] * 1.04, rel=1e-12)
    assert all(verse[x] == verse_sans[x] for x in verse_sans if x != cid)


def test_amelioration_kilos_la_pose_survit_au_mois_et_aux_gestes(depart, regles, monkeypatch):
    cid, maison = _paris(depart)
    monde = _avec_plume(depart, maison, 70.0)
    recevoir_intention(monde, _ameliorer(maison, cid))
    engine.tick(monde, random.Random(0), 0)
    source = f"jauge:province:{cid}-1"
    vivante = lambda m: [p for p in m.modificateurs if p.source == source]
    assert len(vivante(monde)) == 1
    J.mettre_a_jour(monde, regles)
    assert len(vivante(monde)) == 1
    recevoir_intention(monde, _concorde(maison))
    engine.tick(monde, random.Random(0), 1)
    assert len(vivante(monde)) == 1
    assert J.etat(monde, maison, regles)["concorde"] == 1
    # Contre-épreuve : l'ancien retrait (toute source « jauge: ») fait disparaître la pose après le mois.
    def ancien_retrait(monde, regles):
        autres = [p for p in monde.modificateurs if not p.source.startswith(f"{J.SOURCE}:")]
        neuves = [pose for m in sorted(monde.jauges)
                  for pose in J.modificateurs_de(m, monde.jauges[m], regles, monde.ticks_ecoules)]
        monde.modificateurs = sorted(autres + neuves, key=M._ordre)

    monkeypatch.setattr(J, "poser_les_modificateurs", ancien_retrait)
    J.mettre_a_jour(monde, regles)
    with pytest.raises(AssertionError):
        assert len(vivante(monde)) == 1


# SC5 — Le joueur et l'IA, même monde, octet pour octet

def _maison_de_l_ia_a_sa_capitale(monde):
    from sim import ia
    from sim.capitales import toutes_les_maisons_de_l_ia
    maisons = toutes_les_maisons_de_l_ia(monde)
    for maison in maisons:
        cle = ia._cle_du_grenier(maison)
        if cle and maison.cell_id is not None and monde.cells[maison.cell_id].lieux[0].maitre == cle:
            return maisons, maison, cle
    pytest.fail("aucune maison de l'IA ne tient le bourg de sa capitale : l'échantillon est vide")


def test_amelioration_meme_monde_l_ia_et_le_joueur(depart, regles, monkeypatch):
    from sim import ia
    maisons, maison, cle = _maison_de_l_ia_a_sa_capitale(depart)
    cid = maison.cell_id
    base = _avec_plume(depart, cle, 20.0)
    intention = _ameliorer(cle, cid)
    # Côté IA : la seule proposition de la maison, déposée par `jouer_ia`.
    chez_l_ia = copy.deepcopy(base)
    monkeypatch.setattr(ia, "decider_intentions", lambda monde, releve, maisons=None: [
        {"maison": {"sorte": maison.sorte, "id": maison.id}, "intention": intention,
         "raison": {"regle": "epreuve"}}])
    releve = []
    ia.jouer_ia(chez_l_ia, releve, maisons)
    assert len(releve) == 1 and "refus" not in releve[0] and releve[0]["intention"] == intention
    monkeypatch.undo()
    # Côté joueur : la même intention par la porte de `POST /intention`.
    chez_le_joueur = copy.deepcopy(base)
    recevoir_intention(chez_le_joueur, intention)
    alea = random.Random(0)
    engine.tick(chez_l_ia, copy.deepcopy(alea), 0)
    engine.tick(chez_le_joueur, copy.deepcopy(alea), 0)
    assert _octets(chez_l_ia) == _octets(chez_le_joueur)
    assert chez_l_ia.to_dict()["niveaux_de_province"] == {cid: 1}
    # Même graine et mêmes gestes, sur 35 ticks : même monde.
    mondes = []
    for _ in range(2):
        monde = copy.deepcopy(base)
        recevoir_intention(monde, intention)
        rng = random.Random(0)
        for numero in range(35):
            J.avant_le_tick(monde)
            engine.tick(monde, rng, numero)
        mondes.append(_octets(monde))
    assert mondes[0] == mondes[1]
    # Contre-épreuve : améliorer une autre cellule de la même maison donne d'autres octets.
    autre = next(x for x in sorted(depart.cells) if x != cid)
    deux = copy.deepcopy(base)
    deux.cells[autre].lieux[0].maitre = cle
    ailleurs = copy.deepcopy(deux)
    recevoir_intention(deux, intention)
    recevoir_intention(ailleurs, _ameliorer(cle, autre))
    engine.tick(deux, copy.deepcopy(alea), 0)
    engine.tick(ailleurs, copy.deepcopy(alea), 0)
    assert _octets(deux) != _octets(ailleurs)


# SC6 — Servi dans /pays, sous jauges, sans changer les gestes du panneau

def test_amelioration_service_pays_et_intention(regles):
    import threading
    from sim.service import ServeurMonde
    from sim.tests.test_monde import requete_service
    bar = "seigneurie-1"
    with ServeurMonde(("127.0.0.1", 0), 0, 0) as serveur:
        fil = threading.Thread(target=serveur.serve_forever)
        fil.start()
        try:
            port = serveur.server_port
            (cid,) = _bourgs_tenus(serveur.world, bar)
            autre, maitre = _autre_maitre(serveur.world, bar)
            with serveur.verrou_tick:
                serveur.world.jauges[bar] = J.etat(serveur.world, bar, regles) | {"plume": 5.0}

            def jauges():
                return json.loads(serveur.octets_du_pays(bar))["jauges"]

            avant = jauges()
            amelioration = avant["amelioration"]
            table, definition = regles.amelioration, M.charger_donnees().definitions["amelioration_de_province"]
            assert (amelioration["nom"], amelioration["dit"], amelioration["reserve"]) == (
                table["nom"], table["dit"], "plume")
            assert amelioration["modificateur"] == {"nom": "Province améliorée", "grandeur": "recolte",
                                                    "grandeur_nom": "Récolte", "valeur": definition.valeur}
            tenues = _bourgs_tenus(serveur.world, bar)
            assert [p["cell_id"] for p in amelioration["provinces"]] == tenues == [cid]
            trop_chere = {"cell_id": cid, "niveau": 0, "cout": 6,
                          "refus": "pas assez de points de Plume : 6 points demandés, 5 points disponibles"}
            assert amelioration["provinces"] == [trop_chere]
            assert set(avant["gestes"]) == {"affermir_la_concorde", "asseoir_le_droit"}
            # Refusée : `POST /intention` redit, mot pour mot, le refus que `/pays` servait.
            corps = json.dumps(_ameliorer(bar, cid)).encode()
            statut, refus, _ = requete_service(port, "/intention", "POST", corps)
            assert statut == 400 and refus == {"acceptee": False, "erreur": trop_chere["refus"]}
            # La province d'un autre maître n'est pas servie, et son dépôt est refusé.
            assert autre not in [p["cell_id"] for p in amelioration["provinces"]]
            statut, refus, _ = requete_service(port, "/intention", "POST", json.dumps(_ameliorer(bar, autre)).encode())
            assert statut == 400 and refus["erreur"] == f"pas sur vos terres : le bourg de la cellule {autre} est à {maitre!r}"
            # Payable : acceptée, puis un tick plus tard `/pays` sert le niveau 1 et le coût de 9.
            with serveur.verrou_tick:
                serveur.world.jauges[bar] = J.etat(serveur.world, bar, regles) | {"plume": 6.0}
            statut, reponse, _ = requete_service(port, "/intention", "POST", corps)
            assert statut == 200 and reponse == {"acceptee": True, "appliquee_au_tick": 0}
            assert requete_service(port, "/tick?n=1", "POST")[0] == 200
            apres = jauges()
            assert apres["amelioration"]["provinces"] == [
                {"cell_id": cid, "niveau": 1, "cout": 9,
                 "refus": "pas assez de points de Plume : 9 points demandés, 0 point disponible"}]
            assert apres["gestes"].keys() == avant["gestes"].keys()
            assert apres["grandeurs"] == avant["grandeurs"] and apres["modificateurs"] == avant["modificateurs"]
        finally:
            serveur.shutdown()
            fil.join()


def test_amelioration_service_les_provinces_relues_sur_le_monde(depart, regles):
    """Un monde où la maison tient deux bourgs sert les deux, triés, chacune avec son niveau et son coût."""
    bar = "seigneurie-1"
    monde = _avec_plume(depart, bar, 8.0)
    (cid,) = _bourgs_tenus(monde, bar)
    deuxieme = next(x for x in sorted(monde.cells) if x > cid)
    monde.cells[deuxieme].lieux[0].maitre = bar
    monde.niveaux_de_province[deuxieme] = 2
    provinces = J.document_des_jauges(monde, bar, regles)["amelioration"]["provinces"]
    assert [p["cell_id"] for p in provinces] == _bourgs_tenus(monde, bar) == sorted([cid, deuxieme])
    par_cell = {p["cell_id"]: p for p in provinces}
    assert (par_cell[cid]["niveau"], par_cell[cid]["cout"], par_cell[cid]["refus"]) == (0, 6, None)
    assert (par_cell[deuxieme]["niveau"], par_cell[deuxieme]["cout"]) == (2, 13.5)
    assert par_cell[deuxieme]["refus"] == "pas assez de points de Plume : 13,5 points demandés, 8 points disponibles"
