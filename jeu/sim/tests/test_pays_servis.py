"""Le pays de chaque terre (`sim/pays_servis.py`) : une puissance de 1400, pas une dynastie.

- Deux terres de la même maison régnante mais de deux puissances (Bohême et Hongrie,
  Aragon et Sicile) sont deux pays.
- La cellule de Pampelune est en Navarre ; tout pays servi a un nom.
- Une terre de départ est son propre pays et dit la puissance dont elle relève.
"""
from types import SimpleNamespace

import pytest

from sim import pays_servis as P
from sim.guerre import racine
from sim.maisons import charger_maisons
from sim.noms import noms_depuis_monde
from sim.projection import projeter_epsg3035
from sim.puissances import charger_table, puissances_depuis_monde
from sim.seigneuries import cellule_du_siege, charger_seigneuries, identifiant_de_seigneurie
from sim.villes import point_dans_geometrie
from sim.world import World


@pytest.fixture(scope="module")
def sources():
    monde = World.charger(rng_seed=0)
    table = charger_table()
    return SimpleNamespace(monde=monde, table=table, maisons=charger_maisons(),
                           seigneuries=charger_seigneuries(table=table),
                           vue=puissances_depuis_monde(monde, table=table),
                           matiere=SimpleNamespace(noms=noms_depuis_monde(monde)))


def _pays(s):
    return P.pays_des_terres(s.monde, s.vue, s.maisons)


def _fiches(s, pays):
    return P.fiches_des_pays({p for p in pays.values() if p is not None}, s.monde, s.table,
                             s.maisons, s.seigneuries, s.matiere)


def _maitre_du_bourg(monde, cid):
    return next((l.maitre for l in monde.cells[cid].lieux if l.rang == 0), None)


def _verifier_puissances_distinctes(s, pays):
    """Deux terres de même racine et de puissances différentes ne sont jamais servies sous le même pays."""
    par_id = {m.id: m for m in s.monde.maisons}
    par_racine = {}
    for cid in sorted(s.monde.cells):
        maitre = _maitre_du_bourg(s.monde, cid)
        if maitre is not None and s.vue[cid] is not None:
            par_racine.setdefault(racine(par_id, maitre), {}).setdefault(s.vue[cid], set()).add(pays[cid])
    plusieurs = {r: p for r, p in par_racine.items() if len(p) > 1}
    # Un échantillon vide ne prouve rien : Luxembourg règne sur trois puissances, Barcelone sur deux.
    nommees = {p.nom: p.id for p in s.table.puissances}
    luxembourg = P.tete_de_puissance(nommees["Bohême"], s.maisons)
    barcelone = P.tete_de_puissance(nommees["Sicile"], s.maisons)
    assert luxembourg == P.tete_de_puissance(nommees["Hongrie"], s.maisons)
    assert barcelone == P.tete_de_puissance(nommees["Aragon"], s.maisons)
    assert {nommees["Bohême"], nommees["Hongrie"]} <= set(plusieurs.get(luxembourg, ()))
    assert {nommees["Aragon"], nommees["Sicile"]} <= set(plusieurs.get(barcelone, ()))
    for tenues in plusieurs.values():
        servis = [pays_servis for pays_servis in tenues.values()]
        for i, gauche in enumerate(servis):
            for droite in servis[i + 1:]:
                assert not gauche & droite, f"deux puissances servies sous le même pays : {gauche & droite}"


def test_deux_puissances_d_une_meme_maison_sont_deux_pays(sources):
    _verifier_puissances_distinctes(sources, _pays(sources))


def test_contre_epreuve_le_pays_de_la_racine_confond_boheme_et_hongrie(sources, monkeypatch):
    # L'ancienne règle : le pays d'une terre est la maison au sommet de la suzeraineté de son maître.
    monkeypatch.setattr(P, "_pays_selon", lambda chaine, *_: chaine[-1])
    with pytest.raises(AssertionError):
        _verifier_puissances_distinctes(sources, _pays(sources))


def test_pampelune_est_en_navarre_et_tout_pays_a_un_nom(sources):
    pays = _pays(sources)
    fiches = {f["id"]: f for f in _fiches(sources, pays)}
    assert set(fiches) >= {p for p in pays.values() if p is not None}
    (ancre,) = [a for a in sources.table.ancres if a.nom == "Pampelune"]
    point = projeter_epsg3035(ancre.lat, ancre.lon)
    cid = next(c for c in sorted(sources.monde.carte)
               if point_dans_geometrie(*point, sources.monde.carte[c]["geometry"]))
    assert fiches[pays[cid]]["nom"] == "Navarre"
    for fiche in fiches.values():
        assert isinstance(fiche["nom"], str) and fiche["nom"].strip(), fiche
        assert isinstance(fiche["maison"]["nom"], str) and fiche["maison"]["nom"].strip(), fiche
    # La dynastie vient en second : aucun pays ne porte le nom d'une maison qui règne sur une puissance.
    noms = {f["nom"] for f in fiches.values()}
    assert not noms & {"Luxembourg", "Évreux"}, noms & {"Luxembourg", "Évreux"}
    assert {"Bohême", "Hongrie", "Saint-Empire"} <= noms


def test_une_terre_de_depart_est_son_propre_pays_et_dit_son_suzerain(sources):
    pays = _pays(sources)
    fiches = {f["id"]: f for f in _fiches(sources, pays)}
    puissances = {p.id: p for p in sources.table.puissances}
    assert sources.seigneuries, "échantillon vide"
    for seigneurie in sources.seigneuries:
        identifiant = identifiant_de_seigneurie(seigneurie.id)
        assert pays[cellule_du_siege(seigneurie, sources.monde.carte)] == identifiant
        fiche = fiches[identifiant]
        assert fiche["nom"] == seigneurie.nom and fiche["maison"]["id"] == identifiant
        assert fiches[fiche["suzerain"]]["nom"] == puissances[seigneurie.suzerain].nom
        assert fiches[fiche["suzerain"]]["suzerain"] is None
    (zab,) = [s for s in sources.seigneuries if s.nom == "Émirat du Zab"]
    assert fiches[fiches[identifiant_de_seigneurie(zab.id)]["suzerain"]]["nom"] == "Hafsides"


@pytest.fixture(scope="module")
def jouables(sources):
    from sim.jouables import maisons_jouables
    from sim.pays_servis import sources_des_pays
    return maisons_jouables(sources.monde, sources_des_pays(sources.monde, sources.table, sources.vue),
                            sources.matiere.noms)


def _verifier_villes(jouables, villes, seigneuries):
    """Chaque départ dit si sa capitale est bâtie ; seuls ceux de la donnée le disent, les autres disent pourquoi."""
    departs = [m for m in jouables if m["sorte"] == "seigneurie"]
    assert [m["id"] for m in departs] == [identifiant_de_seigneurie(s.id) for s in seigneuries], "les six départs"
    for depart in departs:
        ville = depart["ville"]
        assert isinstance(ville["batie"], bool), depart["id"]
        if not ville["batie"]:
            assert ville["raison"] and depart["siege"]["nom"] in ville["raison"] and ville["scene"] is None
    assert {m["id"] for m in departs if m["ville"]["batie"]} == {v.maison for v in villes.capitales}
    assert all(m["ville"]["batie"] == (m["id"] in {v.maison for v in villes.capitales}) for m in jouables)


def test_chaque_depart_dit_si_sa_capitale_est_batie(sources, jouables):
    import copy
    from sim.villes_3d import charger_villes_3d
    villes = charger_villes_3d()
    _verifier_villes(jouables, villes, sources.seigneuries)
    # Aujourd'hui, seule la terre dont le siège est Biskra a sa ville.
    (biskra,) = [s for s in sources.seigneuries if s.siege.nom == "Biskra"]
    assert {v.maison for v in villes.capitales} == {identifiant_de_seigneurie(biskra.id)}
    # Contre-épreuve : un départ servi bâti sans entrée dans la donnée.
    faux = copy.deepcopy(jouables)
    autre = next(m for m in faux if m["sorte"] == "seigneurie" and not m["ville"]["batie"])
    autre["ville"] = {"batie": True, "scene": None, "raison": None}
    with pytest.raises(AssertionError):
        _verifier_villes(faux, villes, sources.seigneuries)


def test_un_jouable_dit_son_pays_ses_regnes_son_siege_et_son_suzerain(sources, jouables):
    par_id = {m["id"]: m for m in jouables}
    nommees = {p.nom: p.id for p in sources.table.puissances}
    luxembourg = par_id[P.tete_de_puissance(nommees["Bohême"], sources.maisons)]
    assert {p["nom"] for p in luxembourg["regne"]} == {"Saint-Empire", "Bohême", "Hongrie"}
    assert luxembourg["pays"]["nom"] == "Bohême" and luxembourg["suzerain"] is None
    navarre = par_id[P.tete_de_puissance(nommees["Navarre"], sources.maisons)]
    assert navarre["pays"]["nom"] == "Navarre" and navarre["siege"]["nom"] == "Pampelune"
    puissances = {p.id: p.nom for p in sources.table.puissances}
    for seigneurie in sources.seigneuries:
        depart = par_id[identifiant_de_seigneurie(seigneurie.id)]
        assert depart["pays"]["nom"] == seigneurie.nom and [p["id"] for p in depart["regne"]] == [depart["id"]]
        assert depart["siege"]["nom"] == seigneurie.siege.nom
        assert depart["suzerain"]["pays"]["nom"] == puissances[seigneurie.suzerain]
    # Un seigneur tenu par une maison qui règne sur plusieurs pays relève du pays où il est.
    hongrois = next(m for m in jouables if m["sorte"] == "plausible"
                    and m["pays"]["id"] == P.identifiant_de_puissance(nommees["Hongrie"]))
    assert hongrois["suzerain"]["id"] == luxembourg["id"] and hongrois["suzerain"]["pays"]["nom"] == "Hongrie"
    assert all(m["nom"] and not m["nom"].startswith("plausible-") for m in jouables)


def test_une_place_prise_passe_au_pays_du_preneur(sources):
    import copy
    monde = copy.deepcopy(sources.monde)
    avant = _pays(sources)
    nommees = {p.nom: p.id for p in sources.table.puissances}
    boheme = P.identifiant_de_puissance(nommees["Bohême"])
    hongrie = next(cid for cid in sorted(avant) if avant[cid] == P.identifiant_de_puissance(nommees["Hongrie"]))
    # La Bohême et la Hongrie ont la même maison : une place hongroise prise par le maître
    # d'une place de Bohême reste à la Hongrie, puisque la racine règne sur elle.
    tcheque = next(cid for cid in sorted(avant) if avant[cid] == boheme)
    monde.cells[hongrie].lieux[0].maitre = _maitre_du_bourg(monde, tcheque)
    assert P.pays_des_terres(monde, sources.vue, sources.maisons)[hongrie] == avant[hongrie]
    # Prise par une terre de départ, elle entre dans son pays, et elle seule change.
    bar = identifiant_de_seigneurie(sources.seigneuries[0].id)
    monde.cells[hongrie].lieux[0].maitre = bar
    apres = P.pays_des_terres(monde, sources.vue, sources.maisons)
    assert {cid for cid in avant if avant[cid] != apres[cid]} == {hongrie} and apres[hongrie] == bar
