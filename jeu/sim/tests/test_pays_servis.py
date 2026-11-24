"""Le pays de chaque terre (`sim/pays_servis.py`) : une puissance de 1400, pas une dynastie.

- Deux terres de la même maison régnante mais de deux puissances (Hollande et Hainaut,
  Aragon et Sicile) sont deux pays ; la Bohême et la Hongrie ont chacune leur maison.
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
    # Un échantillon vide ne prouve rien : les Wittelsbach de Straubing règnent sur la Hollande et le
    # Hainaut, Barcelone sur l'Aragon et la Sicile.
    nommees = {p.nom: p.id for p in s.table.puissances}
    straubing = P.tete_de_puissance(nommees["Hollande"], s.maisons)
    barcelone = P.tete_de_puissance(nommees["Sicile"], s.maisons)
    assert straubing == P.tete_de_puissance(nommees["Hainaut"], s.maisons)
    assert barcelone == P.tete_de_puissance(nommees["Aragon"], s.maisons)
    assert {nommees["Hollande"], nommees["Hainaut"]} <= set(plusieurs.get(straubing, ()))
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
    sans_etat = [f for f in fiches.values() if f["id"].startswith(P.identifiant_de_terre(""))]
    assert sans_etat and len(sans_etat) < len(fiches), "échantillon vide"
    for fiche in fiches.values():
        assert isinstance(fiche["nom"], str) and fiche["nom"].strip(), fiche
        # Une terre sans État n'a pas de maison ; tout autre pays a la sienne, nommée.
        if fiche in sans_etat:
            assert fiche["maison"] is None, fiche
        else:
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
    # Luxembourg règne sur le Saint-Empire, qui ne tient aucune terre, et sur la Bohême ; la Hongrie est
    # à Sigismond.
    luxembourg = par_id[P.tete_de_puissance(nommees["Bohême"], sources.maisons)]
    assert {p["nom"] for p in luxembourg["regne"]} == {"Saint-Empire", "Bohême"}
    assert luxembourg["pays"]["nom"] == "Bohême" and luxembourg["suzerain"] is None
    sigismond = par_id[P.tete_de_puissance(nommees["Hongrie"], sources.maisons)]
    assert sigismond["id"] != luxembourg["id"] and [p["nom"] for p in sigismond["regne"]] == ["Hongrie"]
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
    assert hongrois["suzerain"]["id"] == sigismond["id"] and hongrois["suzerain"]["pays"]["nom"] == "Hongrie"
    hennuyer = next(m for m in jouables if m["sorte"] == "plausible"
                    and m["pays"]["id"] == P.identifiant_de_puissance(nommees["Hainaut"]))
    straubing = P.tete_de_puissance(nommees["Hainaut"], sources.maisons)
    assert hennuyer["suzerain"]["id"] == straubing and hennuyer["suzerain"]["pays"]["nom"] == "Hainaut"
    assert all(m["nom"] and not m["nom"].startswith("plausible-") for m in jouables)


@pytest.fixture(scope="module")
def servie(sources):
    from sim.carte_servie import terres_et_pays
    return terres_et_pays(sources.monde, sources.matiere,
                          P.sources_des_pays(sources.monde, sources.table, sources.vue))


def _pays_plausibles(monde, servie, jouables):
    """Les seigneurs plausibles servis comme un pays : d'une terre, d'un lieu, d'une fiche ou d'un jouable."""
    plausibles = {m.id for m in monde.maisons if m.sorte == "plausible"}
    assert plausibles and servie["terres"] and servie["pays"] and jouables, "échantillon vide"
    terres = servie["terres"]
    servis = ([t["pays"] for t in terres] + [a["pays"] for t in terres for a in t["autres_pays"]]
              + [f["id"] for f in servie["pays"]] + [j["pays"]["id"] for j in jouables]
              + [p["id"] for j in jouables for p in j["regne"]])
    return sorted({p for p in servis if p in plausibles})


def _origine_d_avant(maison, vue, maisons, lieux=None, terres=None):
    """L'ancienne règle : un seigneur dont le lieu n'a pas de puissance est son propre pays."""
    if maison.sorte == "seigneurie":
        return maison.id
    puissance = (None if maison.cell_id is None
                 else P.puissance_du_lieu(maison.cell_id, maison.rang, vue, lieux))
    if puissance is not None:
        return P.identifiant_de_puissance(puissance)
    dirigees = P._dirigees(maisons).get(maison.id)
    return P.identifiant_de_puissance(dirigees[0]) if dirigees else maison.id


def test_aucun_pays_servi_n_est_un_seigneur_plausible(sources, servie, jouables, monkeypatch):
    assert not _pays_plausibles(sources.monde, servie, jouables)
    # Contre-épreuve : avec l'ancienne règle, les seigneurs du désert redeviennent des pays.
    from sim.carte_servie import terres_et_pays
    monkeypatch.setattr(P, "pays_d_origine", _origine_d_avant)
    avant = terres_et_pays(sources.monde, sources.matiere,
                           P.sources_des_pays(sources.monde, sources.table, sources.vue))
    assert _pays_plausibles(sources.monde, avant, jouables)


def _pays_de_chaque_lieu(servie, monde):
    """(cell_id, rang) → pays servi de chaque lieu : celui de sa terre, ou celui que `autres_pays` lui donne."""
    pays = {}
    for terre in servie["terres"]:
        autres = {a["rang"]: a["pays"] for a in terre["autres_pays"]}
        for lieu in monde.cells[terre["cell_id"]].lieux:
            pays[terre["cell_id"], lieu.rang] = autres.get(lieu.rang, terre["pays"])
    return pays


def _terres_declarees(s):
    """(cell_id, rang) → terre sans État que la table déclare à chaque lieu sans puissance : celle de la
    lacune de sa cellule, ou celle de la ville de partage la plus proche de sa place, quand elle est sans pays."""
    from sim.frontieres import frontieres_du_monde
    from sim.places import places_du_monde
    frontieres = frontieres_du_monde(s.monde, s.table)
    places = places_du_monde(s.monde)
    attendues = {}
    for cid in sorted(s.monde.cells):
        for rang, place in enumerate(places[cid]):
            if cid in frontieres.lacunes:
                attendues[cid, rang] = frontieres.terres_des_lacunes[cid]
            elif cid in frontieres.partages:
                villes = frontieres.partages[cid]
                proche = min(range(len(villes)), key=lambda i: (
                    (place.x_m - projeter_epsg3035(villes[i].lat, villes[i].lon)[0]) ** 2
                    + (place.y_m - projeter_epsg3035(villes[i].lat, villes[i].lon)[1]) ** 2, i))
                if villes[proche].pays is None:
                    attendues[cid, rang] = villes[proche].terre
    return frontieres, attendues


def _fautes_des_lieux_sans_puissance(s, servie, attendues):
    par_id = {m.id: m for m in s.monde.maisons}
    servis = _pays_de_chaque_lieu(servie, s.monde)
    fautes = []
    for (cid, rang), terre in sorted(attendues.items()):
        maitre = s.monde.cells[cid].lieux[rang].maitre
        # Une terre de départ garde ses lieux : le Wurtemberg tient quatre lieux de Stuttgart, sans puissance.
        if maitre is not None and par_id[maitre].sorte == "seigneurie":
            continue
        if servis[cid, rang] != P.identifiant_de_terre(terre):
            fautes.append(f"lieu ({cid}, {rang}) : {servis[cid, rang]}, {P.identifiant_de_terre(terre)} attendu")
    return fautes


def test_chaque_lieu_sans_puissance_est_servi_a_sa_terre_sans_etat(sources, servie):
    frontieres, attendues = _terres_declarees(sources)
    assert attendues and frontieres.terres_sans_etat, "échantillon vide"
    assert not _fautes_des_lieux_sans_puissance(sources, servie, attendues)
    # Chaque terre déclarée sert au moins un lieu, sous le nom de la table, sans maison ni suzerain.
    fiches = {f["id"]: f for f in servie["pays"]}
    assert {attendues[k] for k in attendues} == set(frontieres.terres_sans_etat)
    for terre in frontieres.terres_sans_etat.values():
        fiche = fiches[P.identifiant_de_terre(terre.id)]
        assert fiche == {"id": P.identifiant_de_terre(terre.id), "nom": terre.nom, "maison": None,
                         "suzerain": None, "ensemble": None}, fiche
    # Contre-épreuve : un lieu du désert déclaré à une autre terre se voit.
    cle = next(k for k, t in attendues.items() if t != attendues[min(attendues)])
    faux = {**attendues, cle: attendues[min(attendues)]}
    assert _fautes_des_lieux_sans_puissance(sources, servie, faux)


def _fautes_de_tenant(monde, servie):
    """Les terres sans État dont les bourgs de terre ferme ne sont pas d'un seul tenant, et deux terres
    sans État dont les bourgs se touchent. Une cellule sans arête `land-land` est une île, mise à part."""
    prefixe = P.identifiant_de_terre("")
    terre_de = {t["cell_id"]: t["pays"] for t in servie["terres"]
                if t["pays"] is not None and t["pays"].startswith(prefixe)}
    voisins = {}
    for arete in monde.adjacency:
        if arete["kind"] == "land-land":
            voisins.setdefault(arete["a"], set()).add(arete["b"])
            voisins.setdefault(arete["b"], set()).add(arete["a"])
    fautes = sorted({f"{terre_de[a]} touche {terre_de[b]} ({a}, {b})" for a in terre_de
                     for b in voisins.get(a, ()) if b in terre_de and terre_de[b] != terre_de[a]})
    par_terre = {}
    for cid, terre in sorted(terre_de.items()):
        if voisins.get(cid):
            par_terre.setdefault(terre, set()).add(cid)
    for terre, fermes in sorted(par_terre.items()):
        vus, a_voir = set(), [min(fermes)]
        while a_voir:
            cid = a_voir.pop()
            if cid not in vus:
                vus.add(cid)
                a_voir.extend(v for v in voisins[cid] if v in fermes)
        if vus != fermes:
            fautes.append(f"{terre} : {len(fermes) - len(vus)} bourgs hors du tenant de {min(fermes)}")
    return fautes, par_terre


def test_chaque_terre_sans_etat_est_d_un_seul_tenant_et_ne_touche_aucune_autre(sources, servie):
    fautes, par_terre = _fautes_de_tenant(sources.monde, servie)
    assert any(len(fermes) > 1 for fermes in par_terre.values()), "échantillon vide"
    assert not fautes, fautes
    # Contre-épreuve : deux terres de terre ferme fondues sous un seul nom ne sont plus d'un seul tenant.
    premiere, seconde = sorted(par_terre)[:2]
    fondue = {**servie, "terres": [{**t, "pays": premiere} if t["pays"] == seconde else t
                                   for t in servie["terres"]]}
    assert any(premiere in f and "hors du tenant" in f for f in _fautes_de_tenant(sources.monde, fondue)[0])


def test_une_place_prise_passe_au_pays_du_preneur(sources):
    import copy
    monde = copy.deepcopy(sources.monde)
    avant = _pays(sources)
    nommees = {p.nom: p.id for p in sources.table.puissances}
    hollande = P.identifiant_de_puissance(nommees["Hollande"])
    hainaut = next(cid for cid in sorted(avant) if avant[cid] == P.identifiant_de_puissance(nommees["Hainaut"]))
    # La Hollande et le Hainaut ont la même maison : une place du Hainaut prise par le maître
    # d'une place de Hollande reste au Hainaut, puisque la racine règne sur lui.
    hollandaise = next(cid for cid in sorted(avant) if avant[cid] == hollande)
    monde.cells[hainaut].lieux[0].maitre = _maitre_du_bourg(monde, hollandaise)
    assert P.pays_des_terres(monde, sources.vue, sources.maisons)[hainaut] == avant[hainaut]
    # Prise par une terre de départ, elle entre dans son pays, et elle seule change.
    bar = identifiant_de_seigneurie(sources.seigneuries[0].id)
    monde.cells[hainaut].lieux[0].maitre = bar
    apres = P.pays_des_terres(monde, sources.vue, sources.maisons)
    assert {cid for cid in avant if avant[cid] != apres[cid]} == {hainaut} and apres[hainaut] == bar
    # Contre-épreuve : la Bohême et la Hongrie n'ont plus la même maison, une place hongroise prise par
    # le maître d'une place de Bohême passe à la Bohême.
    monde = copy.deepcopy(sources.monde)
    hongrie = next(cid for cid in sorted(avant) if avant[cid] == P.identifiant_de_puissance(nommees["Hongrie"]))
    tcheque = next(cid for cid in sorted(avant) if avant[cid] == P.identifiant_de_puissance(nommees["Bohême"]))
    monde.cells[hongrie].lieux[0].maitre = _maitre_du_bourg(monde, tcheque)
    assert P.pays_des_terres(monde, sources.vue, sources.maisons)[hongrie] == avant[tcheque]
