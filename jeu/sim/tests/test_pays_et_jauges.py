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
            engine.tick(temoin, rng, numero)
    rng = random.Random(0)
    for numero in range(c.FENETRE_FLUX_TICKS):
        engine.tick(monde, rng, numero)
    assert monde.jauges == {} and monde.to_dict() == temoin.to_dict()


def test_les_points_naissent_chaque_mois_des_competences(depart, regles):
    monde = copy.deepcopy(depart)
    rng = random.Random(0)
    for numero in range(2 * c.FENETRE_FLUX_TICKS + 1):
        engine.tick(monde, rng, numero)
    for maison in ("grande-3", "grande-1", "seigneurie-1"):
        comp = J.competences(monde, maison, regles)
        valeurs = J.etat(monde, maison, regles)
        for nom, reserve in regles.points.items():
            assert valeurs[nom] == pytest.approx(2 * comp[reserve["domaine"]] * reserve["par_point_de_competence_par_mois"])
    assert all(v["plume"] >= 0 for v in monde.jauges.values())


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
    assert J.mois_ecoule(riche)  # ce tick ouvre aussi le mois : la Plume reçoit son mois
    mois = J.competences(riche, bar, regles)["gestion"] * regles.points["plume"]["par_point_de_competence_par_mois"]
    engine.tick(riche, rng, riche.ticks_ecoules)
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
        engine.tick(monde, rng, monde.ticks_ecoules)
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


def test_le_service_sert_le_pays_et_ses_jauges(depart):
    from sim.service import ServeurMonde
    with ServeurMonde(("127.0.0.1", 0), 0, 0) as serveur:
        document = json.loads(serveur.octets_du_pays("grande-3"))
        attendu = P.pays(serveur.world, "grande-3")
        assert {k: v for k, v in document.items() if k not in ("jauges", "date")} == json.loads(json.dumps(attendu))
        assert set(document["jauges"]["jauges"]) == {"concorde", "renom", "droit"}
        assert set(document["jauges"]["points"]) == {"plume", "sceau", "epee"}
        with pytest.raises(P.PaysInconnu):
            serveur.octets_du_pays("maison-inventee")
