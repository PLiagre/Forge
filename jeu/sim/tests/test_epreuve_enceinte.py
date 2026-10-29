"""Preuve de bout en bout de l'enceinte du jalon 4 : gestes, salaires, achèvement, portes, même monde.

Biskra (cellule 10103, maître seigneurie-6), graine 0, six ticks. Le monde se calcule une fois par
fixture de module : une simulation de six ticks coûte de 15 à 35 s.
"""

import copy
from dataclasses import FrozenInstanceError, replace
import json
import math
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

import sim.__main__ as cli
from sim import constants, service
from sim.chantiers import travail_requis_de_enceinte
from sim.intentions import IntentionRefusee, recevoir_intention
from sim.plan import Enceinte
from sim.portes import PorteSansRue, controler_portes, portes_de_l_enceinte
from sim.service import ServeurMonde
from sim.ville1400 import base_de_cellule
from sim.world import World

CELLULE, MAISON, JEUX = 10103, "seigneurie-6", Path(__file__).parents[2]
CONSTANTE_REDUITE = 0.01
ROUTE = {"type": "tracer_route", "maison": MAISON, "cell": CELLULE,
         "points": [[-66, 2.2], [-120, 2.2]], "largeur_m": 4}
CARRE = [[-80, -80], [80, -80], [80, 80], [-80, 80]]
ENCEINTE = {"type": "tracer_enceinte", "maison": MAISON, "cell": CELLULE, "points": CARRE, "foyers": 2}
CROISEE = ENCEINTE | {"points": [[-80, -80], [80, 80], [80, -80], [-80, 80]]}
JOURNAL = [{"tick": 0, "intention": ROUTE}, {"tick": 0, "intention": ENCEINTE}]
PORTES = [{"point": [-80.0, 2.2], "rue": "plan", "identifiant": 0, "largeur_m": 4}]
PORTE_DE_BASE = {"point": [-80.0, 2.2], "rue": "base", "identifiant": 3, "largeur_m": 4}
CLE_ROUTE, CLE_ENCEINTE = (CELLULE, 0), (CELLULE, "enceinte", 0)


def _octets(monde):
    return json.dumps(monde.to_dict(), sort_keys=True).encode()


def _depot_sans_effet(monde, intention, recevoir=recevoir_intention):
    """Un dépôt accepté se gèle en file : le plan et le monde ne bougent qu'au tick suivant."""
    avant, plan = _octets(monde), monde.plans[CELLULE]
    recu = recevoir(monde, copy.deepcopy(intention))
    assert monde.plans[CELLULE] is plan and plan.enceinte is None and _octets(monde) == avant
    return recu


def _refus_sans_effet(monde, intention, motif, recevoir=recevoir_intention):
    avant, file = _octets(monde), list(monde.intentions_en_attente)
    with pytest.raises(IntentionRefusee, match=motif):
        recevoir(monde, copy.deepcopy(intention))
    assert _octets(monde) == avant and monde.intentions_en_attente == file


def test_depot_et_refus(tmp_path, capsys):
    monde = World.charger(0)
    recues = [_depot_sans_effet(monde, intention) for intention in (ROUTE, ENCEINTE)]
    assert monde.intentions_en_attente == recues and len(recues) == 2
    for recue in recues:
        with pytest.raises(FrozenInstanceError):
            recue.cell_id = 0
    neuf = World.charger(0)
    refus = [(CROISEE, "enceinte : contour qui se croise"),
             (ENCEINTE | {"cell": 10322, "points": [[-2000, -2000], [2000, -2000], [2000, 2000], [-2000, 2000]]},
              "ce lieu n'est pas à toi : grande-3")]
    for intention, motif in refus:
        _refus_sans_effet(neuf, intention, motif)
    assert len(refus) == 2 and not neuf.intentions_en_attente
    # Contre-épreuves : un dépôt qui touche au plan, un refus qui laisse une intention en file.
    def modifie_le_plan(monde, intention):
        monde.plans[CELLULE] = replace(monde.plans[CELLULE], enceinte=Enceinte(CARRE))
    def garde_en_file(monde, intention):
        monde.intentions_en_attente.append(intention)
        raise IntentionRefusee("enceinte : contour qui se croise")
    with pytest.raises(AssertionError):
        _depot_sans_effet(neuf, ENCEINTE, modifie_le_plan)
    neuf.plans[CELLULE] = replace(neuf.plans[CELLULE], enceinte=None)
    with pytest.raises(AssertionError):
        _refus_sans_effet(neuf, CROISEE, "contour qui se croise", garde_en_file)
    neuf.intentions_en_attente.clear()
    # La vraie entrée : l'erreur nomme l'entrée refusée et le monde n'est pas écrit.
    gestes, sortie = tmp_path / "gestes.json", tmp_path / "monde.json"
    gestes.write_text(json.dumps([JOURNAL[0], {"tick": 0, "intention": CROISEE}]))
    code = cli.main(["--ticks", "6", "--seed", "0", "--gestes", str(gestes), "--monde-json", str(sortie)])
    assert code == 2 and not sortie.exists() and "entrée 2" in capsys.readouterr().err


def _jouer(dossier, nom, gestes, constante=CONSTANTE_REDUITE, releves=None):
    """Rejoue le journal par la vraie entrée en processus ; retourne les octets du monde."""
    fichier, sortie = dossier / f"{nom}-gestes.json", dossier / f"{nom}.json"
    fichier.write_text(json.dumps(gestes))
    original = cli.tick
    def espion(world, rng, numero):
        avant, grenier = world.plans[CELLULE].enceinte, dict(world.greniers.get(MAISON, {}))
        resultat = original(world, rng, numero)
        releves.append(SimpleNamespace(
            numero=numero, avant=avant, grenier_avant=grenier.get("nourriture", 0), monde=world,
            apres=world.plans[CELLULE].enceinte,
            entrees={cle: dict(v) for cle, v in world.chantiers_du_jour.items() if cle[0] == CELLULE}))
        return resultat
    with pytest.MonkeyPatch.context() as sonde:
        sonde.setattr(constants, "TRAVAIL_ENCEINTE_JOURNEES_PAR_M", constante)
        if releves is not None:
            sonde.setattr(cli, "tick", espion)
        assert cli.main(["--ticks", "6", "--seed", "0", "--gestes", str(fichier), "--monde-json", str(sortie)]) == 0
    return sortie.read_bytes()


@pytest.fixture(scope="module")
def avec(tmp_path_factory):
    releves = []
    octets = _jouer(tmp_path_factory.mktemp("avec"), "avec", JOURNAL, releves=releves)
    return SimpleNamespace(octets=octets, monde=json.loads(octets), releves=releves)


@pytest.fixture(scope="module")
def sans(tmp_path_factory):
    octets = _jouer(tmp_path_factory.mktemp("sans"), "sans", [])
    return SimpleNamespace(octets=octets, monde=json.loads(octets))


def _en_sous_processus(dossier, gestes):
    commande = [sys.executable, "-m", "sim", "--ticks", "6", "--seed", "0", "--monde-json", str(dossier / "monde.json")]
    if gestes is not None:
        (dossier / "gestes.json").write_text(json.dumps(gestes))
        commande += ["--gestes", str(dossier / "gestes.json")]
    resultat = subprocess.run(commande, cwd=JEUX, capture_output=True, text=True)
    assert resultat.returncode == 0, resultat.stderr
    return (dossier / "monde.json").read_bytes()


def test_chantier_paye(avec, sans, tmp_path, monkeypatch):
    releves, salaire = avec.releves, constants.SALAIRE_JOURNEE_KG
    assert len(releves) == 6 and releves[0].avant is None
    contour = tuple(tuple(p) for p in CARRE)
    monkeypatch.setattr(constants, "TRAVAIL_ENCEINTE_JOURNEES_PAR_M", CONSTANTE_REDUITE)
    requis = travail_requis_de_enceinte(contour)
    monkeypatch.undo()
    assert requis == math.ceil(640 * CONSTANTE_REDUITE) == 7
    premiere = releves[0].apres
    assert (premiere.en_chantier, premiere.travail_fourni, premiere.travail_requis) == (True, 0, requis)
    fournis = [r.apres.travail_fourni for r in releves]
    assert fournis == sorted(fournis) and fournis[-1] == requis
    jours = [(r, r.entrees.get(CLE_ENCEINTE)) for r in releves]
    bras = [e["bras"] for _, e in jours if e]
    assert sum(bras) == requis and bras and bras[-1] > 0
    for r, entree in jours:
        route = r.entrees.get(CLE_ROUTE)
        for e in filter(None, (route, entree)):
            assert e["grain_paye_kg"] == e["bras"] * salaire
        if entree is None:
            continue
        if r.grenier_avant < salaire:
            assert entree["bras"] == 0 and entree["motif_arret"] == "sans_grain"
        if entree["bras"]:
            assert route["bras"] > 0
    # Un grenier vide ne paie rien, puis la route passe avant l'enceinte.
    assert [e["bras"] for _, e in jours[:2]] == [0, 0] and jours[2][1]["bras"] > 0
    assert releves[2].entrees[CLE_ROUTE]["bras"] == 5 and jours[2][1]["bras"] == 1
    # L'enceinte s'achève le jour où le requis est atteint et quitte le journal le lendemain.
    fin = next(r.numero for r in releves if not r.apres.en_chantier)
    assert fin == 4 and releves[fin].entrees.get(CLE_ENCEINTE) is not None
    assert all(CLE_ENCEINTE not in r.entrees for r in releves[fin + 1:]) and fin + 1 < len(releves)
    # Le grenier finit plus bas que sans gestes : les salaires, moins les pertes évitées.
    paye = sum(e["grain_paye_kg"] for r in releves for k, e in r.entrees.items())
    ecart = (sans.monde["greniers"][MAISON]["nourriture"] - avec.monde["greniers"][MAISON]["nourriture"])
    pertes = sans.monde.get("pertes_kg", 0) - avec.monde.get("pertes_kg", 0)
    assert paye == 81 and ecart == pytest.approx(paye - pertes, abs=1e-6) and 0 < pertes < 1
    # Contre-épreuve : à la vraie constante, la même commande laisse l'enceinte en chantier.
    reel = json.loads(_en_sous_processus(tmp_path, JOURNAL))["plans"][str(CELLULE)]["enceinte"]
    assert reel["en_chantier"] and reel["travail_requis"] == 19200 and reel["travail_fourni"] < reel["travail_requis"]


def test_portes_aux_croisements(avec):
    monde = avec.releves[-1].monde
    plan, rues_de_base = monde.plans[CELLULE], base_de_cellule(monde, CELLULE)["rues"]
    contour = plan.enceinte.contour
    assert portes_de_l_enceinte(contour, plan.rues, rues_de_base) == PORTES
    controler_portes(contour, PORTES, plan.rues, rues_de_base)
    for fausse in ({"point": [80.0, 0.0], "rue": "plan", "identifiant": 0, "largeur_m": 4}, PORTE_DE_BASE):
        with pytest.raises(PorteSansRue):
            controler_portes(contour, [*PORTES, fausse], plan.rues, rues_de_base)
    def cles(valeur):
        if isinstance(valeur, dict):
            return set(valeur) | {c for v in valeur.values() for c in cles(v)}
        return {c for v in valeur for c in cles(v)} if isinstance(valeur, list) else set()
    assert "portes" not in cles(monde.to_dict()) and "portes" not in cles(avec.monde)
    serveur = ServeurMonde(("127.0.0.1", 0), 0, 0)
    try:
        serveur.world.plans[CELLULE] = plan
        publie = json.loads(serveur.octets_plan(serveur._construire_etat(0, -1), CELLULE))
        assert publie["portes"] == PORTES and publie["enceinte"]["en_chantier"] is False
        with pytest.MonkeyPatch.context() as sonde:
            sonde.setattr(service, "portes_de_l_enceinte", lambda *a: [*portes_de_l_enceinte(*a), PORTE_DE_BASE])
            with pytest.raises(PorteSansRue):
                serveur._construire_etat(0, -1)
    finally:
        serveur.server_close()


def _ecarts(a, b):
    """Chemins qui diffèrent entre deux mondes : clé de tête, puis sous-clé des tables par cellule."""
    chemins = set()
    for cle in a.keys() | b.keys():
        if a.get(cle) == b.get(cle):
            continue
        if isinstance(a.get(cle), dict) and isinstance(b.get(cle), dict):
            chemins |= {f"{cle}/{sous}" for sous in a[cle].keys() | b[cle].keys() if a[cle].get(sous) != b[cle].get(sous)}
        else:
            chemins.add(cle)
    return chemins


def test_meme_monde(avec, sans, tmp_path):
    rejeu = _jouer(tmp_path, "rejeu", JOURNAL)
    assert rejeu == avec.octets
    assert _en_sous_processus(tmp_path, None) == sans.octets
    attendus = {f"cells/{CELLULE}", f"plans/{CELLULE}", f"greniers/{MAISON}", "pertes_kg"}
    assert _ecarts(avec.monde, sans.monde) == attendus
    # Contre-épreuves : une autre cellule touchée, ou un seul octet changé, fait échouer la comparaison.
    autre = next(c for c in avec.monde["cells"] if c != str(CELLULE))
    stock = copy.deepcopy(avec.monde)
    stock["cells"][autre]["food_stock_kg"] += 1
    plan = copy.deepcopy(avec.monde)
    plan["plans"][autre]["rues"] = [{"identifiant": 0}]
    for monde in (stock, plan):
        assert _ecarts(monde, sans.monde) != attendus
    octets = bytearray(rejeu)
    octets[-2] ^= 1
    assert bytes(octets) != avec.octets
