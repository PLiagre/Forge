"""Les événements à choix nés d'une cause du monde (lot #1038 ; MODELE.md, « Les événements à choix »).

- Les données : `data/evenements.toml` décrit la famine qui dure et ses trois choix ; un choix
  ne peut imposer aucune issue (ni stock, ni mort, ni fin de famine).
- La cause : un événement s'ouvre aux bornes de mois, pour la maison dont un lieu porte la pose
  `famine` et dont le dernier jour de faim tombe dans le mois écoulé.
- Les effets : chaque choix change exactement ce qu'il dit, au tick de son application.
- Le défaut : sans réponse au bout du délai, « laisser faire » s'applique, jamais par-dessus une réponse.
- L'IA répond par le même chemin que le joueur, et le joueur au même choix obtient le même monde.
- Le service : `GET /evenement` sert l'événement et ses choix, `POST /intention` reçoit la réponse.

Le décor est celui des épreuves d'après le lot #1071 : une ville affamée n'appelle rien
(`couper_l_appel_des_villes`), comme dans les épreuves qui mesurent les premières famines.
"""
import copy
import json
import math
import random
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest

import sim.constants as c
from sim import engine, evenements as E, jauges as J, modificateurs as M
from sim.intentions import IntentionRefusee, OuvrirGrenier, DepenserJauge, recevoir_intention
from sim.tests.amorcage_d_avant import couper_la_famine, couper_l_appel_des_villes
from sim.world import World

MAISON = "plausible-10391-0"
OUVRIR, TAXE, LAISSER = "ouvrir_les_greniers", "lever_une_taxe_de_disette", "laisser_faire"
_DONNEES = Path(__file__).parents[2] / "data" / "evenements.toml"
NOURRITURE = c.MARCHANDISE_NOURRITURE


@pytest.fixture(scope="module", autouse=True)
def _decor():
    with pytest.MonkeyPatch.context() as patch:
        couper_l_appel_des_villes(patch)
        yield


def _reponse(choix, maison=MAISON):
    return {"type": "repondre_evenement", "maison": maison, "choix": choix}


def _json(monde):
    return json.dumps(monde.to_dict(), sort_keys=True)


def _jouer_jusqu_a(monde, rng, tick):
    """Joue le monde jusqu'à juste après le `avant_le_tick` du tick donné, comme les trois boucles."""
    while monde.ticks_ecoules < tick:
        engine.tick(monde, rng, monde.ticks_ecoules)
        J.avant_le_tick(monde)


def _monde_au_tick(tick):
    monde, rng = World.charger(rng_seed=0), random.Random(0)
    avant = None
    for numero in range(tick):
        J.avant_le_tick(monde)
        if numero == tick - 1:
            avant = (dict(monde.evenements), any(p.identifiant == "famine" for p in monde.modificateurs))
        engine.tick(monde, rng, numero)
    J.avant_le_tick(monde)
    return monde, rng, avant


@pytest.fixture(scope="module")
def W30(_decor):
    """La graine 0 sans IA, arrêtée juste après le `avant_le_tick` du tick 30 : l'événement de `plausible-10391-0`."""
    monde, rng, au_29 = _monde_au_tick(c.FENETRE_FLUX_TICKS)
    return SimpleNamespace(monde=monde, rng=rng, evenements_au_29=au_29[0], famine_posee_au_29=au_29[1])


def _copie(monde):
    return copy.deepcopy(monde)


def _cause_de(monde, maison, tick=None):
    """Relit la cause sur le registre des modificateurs, sans `sim/evenements.py` : les lieux de la maison
    dont la pose `famine` finit au plus 365 jours après un dernier jour de faim du mois écoulé."""
    t = monde.ticks_ecoules if tick is None else tick
    duree = M.charger_donnees().definitions["famine"].duree_jours // c.TICK_DURATION_DAYS
    lieux = sorted([p.cible[1], p.cible[2]] for p in monde.modificateurs
                   if p.identifiant == "famine" and p.cible[0] == "lieu"
                   and p.fin - duree >= t - c.FENETRE_FLUX_TICKS
                   and monde.cells[p.cible[1]].lieux[p.cible[2]].maitre == maison)
    assert lieux, f"aucune famine de {maison} dans le mois écoulé"
    return lieux


def _controler_les_causes(monde):
    for maison, evenement in monde.evenements.items():
        assert evenement["lieux"] == _cause_de(monde, maison, evenement["ouvert"])


# --- Les données ---------------------------------------------------------------

def _document():
    with open(_DONNEES, "rb") as fichier:
        return tomllib.load(fichier)


def test_donnees_les_evenements_viennent_des_donnees():
    lus = E.charger_evenements()
    assert list(lus) == ["famine"]
    famine = lus["famine"]
    assert (famine.cause, famine.delai_jours, famine.par_defaut) == ("famine", 30, LAISSER)
    assert [choix.identifiant for choix in famine.choix] == [OUVRIR, TAXE, LAISSER]
    assert all(choix.modificateurs or choix.jauges for choix in famine.choix)
    ouvrir, taxe, laisser = famine.choix
    assert (ouvrir.grenier, ouvrir.jauges, ouvrir.modificateurs) == (0.25, {"concorde": 1}, ())
    assert (taxe.grenier, taxe.jauges, taxe.modificateurs) == (None, {"concorde": -1}, ("taxe_de_disette",))
    assert (laisser.grenier, laisser.jauges, laisser.modificateurs) == (None, {"droit": -5}, ())
    definition = M.charger_donnees().definitions["taxe_de_disette"]
    assert (definition.grandeur, definition.valeur, definition.portee, definition.duree_jours) == (
        "prelevement", 0.25, "pays", 90)
    # Les mots viennent des données : ceux du fichier, pas du code.
    brut = _document()["evenements"]["famine"]
    assert (famine.nom, famine.dit) == (brut["nom"], brut["dit"])
    assert [choix.nom for choix in famine.choix] == [choix["nom"] for choix in brut["choix"]]


def _donnees_avec_levee():
    donnees = M.charger_donnees()
    definition = M.Definition("epreuve_levee", "Levée d'épreuve", "levee", 0.1, "pays", 0)
    return M.Donnees(donnees.sources, donnees.grandeurs, {**donnees.definitions, "epreuve_levee": definition})


def _cas_donnees():
    def choix(document, rang=0):
        return document["evenements"]["famine"]["choix"][rang]

    def sans_effet(document):
        del choix(document, 2)["jauges"]

    def champ(nom, valeur):
        return lambda document: choix(document).__setitem__(nom, valeur)

    def levee(document):
        choix(document, 1)["modificateurs"] = ["epreuve_levee"]

    def quatre(document):
        document["evenements"]["famine"]["choix"].append(dict(choix(document, 2), id="fuir"))

    def un_seul(document):
        del document["evenements"]["famine"]["choix"][1:]

    def doublon(document):
        choix(document, 1)["id"] = OUVRIR

    def evenement(nom, valeur):
        return lambda document: document["evenements"]["famine"].__setitem__(nom, valeur)

    def seconde_cause(document):
        document["evenements"]["autre"] = dict(document["evenements"]["famine"])

    return [
        (sans_effet, "ni modificateur ni jauge", None),
        (champ("population", -100), "champ inconnu 'population'", None),
        (champ("fin_de_la_famine", True), "champ inconnu 'fin_de_la_famine'", None),
        (champ("stock", {"nourriture": 100}), "champ inconnu 'stock'", None),
        (levee, "grandeur 'levee' que le moteur ne lit pas", _donnees_avec_levee),
        (champ("modificateurs", ["inconnu"]), "'inconnu' absent des données des modificateurs", None),
        (champ("modificateurs", ["moulin"]), "moulin se pose sur un cellule, un pays attendu", None),
        (champ("grenier", 0), "grenier : part du grenier dans ]0, 1] attendue, reçu 0", None),
        (champ("grenier", 1.5), "grenier : part du grenier dans ]0, 1] attendue, reçu 1.5", None),
        (champ("grenier", True), "grenier : nombre fini attendu", None),
        (champ("jauges", {"prestige": 1}), "jauges : 'prestige' absente des jauges", None),
        (champ("jauges", {"concorde": 0}), "jauges.concorde : écart non nul attendu", None),
        (champ("jauges", {"concorde": float("nan")}), "jauges.concorde : nombre fini attendu", None),
        (quatre, "choix : de 2 à 3 choix attendus, reçu 4", None),
        (un_seul, "choix : de 2 à 3 choix attendus, reçu 1", None),
        (doublon, "choix[1].id : 'ouvrir_les_greniers' déjà pris par un autre choix", None),
        (evenement("par_defaut", "fuir"), "par_defaut : un des choix attendu", None),
        (evenement("cause", "peste"), "cause : 'peste' inconnue (famine)", None),
        (evenement("delai_jours", 0), "delai_jours : entier ≥ 1 attendu, reçu 0", None),
        (evenement("delai_jours", 1.5), "delai_jours : entier ≥ 1 attendu, reçu 1.5", None),
        (evenement("delai_jours", True), "delai_jours : entier ≥ 1 attendu, reçu True", None),
        (evenement("delai_jours", "30"), "delai_jours : entier ≥ 1 attendu, reçu '30'", None),
        (evenement("nom", " "), "evenements.famine.nom : texte non vide attendu", None),
        (evenement("effet", 1), "champ inconnu 'effet'", None),
        (seconde_cause, "cause : 'famine' est déjà celle de autre", None),
    ]


@pytest.mark.parametrize("change, motif, donnees", _cas_donnees())
def test_donnees_un_evenement_qui_pose_une_issue_ou_ne_tient_pas_est_refuse(change, motif, donnees):
    document = _document()
    E.lire_evenements(copy.deepcopy(document))  # la copie intacte est lue
    change(document)
    with pytest.raises(E.EvenementInvalide) as refus:
        E.lire_evenements(document, None if donnees is None else donnees())
    assert motif in str(refus.value)


def test_donnees_le_document_vide_ou_sans_choix_est_refuse():
    for document in ({}, {"evenements": {}}, {"evenements": []}):
        with pytest.raises(E.EvenementInvalide, match="evenements : table d'événements attendue"):
            E.lire_evenements(document)
    document = _document()
    del document["evenements"]["famine"]["choix"]
    with pytest.raises(E.EvenementInvalide, match="choix : de 2 à 3 choix attendus"):
        E.lire_evenements(document)


# --- La cause ------------------------------------------------------------------

def test_cause_l_evenement_n_apparait_qu_avec_sa_cause(W30):
    monde = W30.monde
    assert monde.evenements == {MAISON: {"identifiant": "famine", "ouvert": 30, "lieux": [[10391, 0]]}}
    # Ses lieux portent la pose `famine`, que le registre des modificateurs redit.
    assert _cause_de(monde, MAISON) == monde.evenements[MAISON]["lieux"]
    for cid, rang in monde.evenements[MAISON]["lieux"]:
        assert any(p.identifiant == "famine" and p.cible == ("lieu", cid, rang) for p in monde.modificateurs)
    _controler_les_causes(monde)
    assert monde.to_dict()["evenements"] == monde.evenements
    # Au tick 29, la famine est posée (depuis le tick 25) mais aucun événement ne naît : ils ne naissent qu'au mois.
    assert W30.famine_posee_au_29 and W30.evenements_au_29 == {}
    assert min(p.debut for p in monde.modificateurs if p.identifiant == "famine") == 25


def test_cause_sans_famine_aucun_evenement(monkeypatch):
    couper_la_famine(monkeypatch)
    monde, _, _ = _monde_au_tick(c.FENETRE_FLUX_TICKS)
    assert monde.evenements == {}
    assert "evenements" not in monde.to_dict()


def test_cause_un_evenement_sans_cause_est_refuse_au_controle(W30):
    monde = _copie(W30.monde)
    monde.evenements["grande-3"] = {"identifiant": "famine", "ouvert": 30, "lieux": [[0, 0]]}
    with pytest.raises(AssertionError):
        _controler_les_causes(monde)


def test_cause_une_ouverture_qui_ne_lit_pas_la_pose_echoue_au_controle(W30, monkeypatch):
    def au_mois_sans_cause(monde, regles=None):
        for maison in monde.maisons:
            if any(lieu.maitre == maison.id for cellule in monde.cells.values() for lieu in cellule.lieux):
                monde.evenements.setdefault(maison.id, {"identifiant": "famine", "ouvert": monde.ticks_ecoules,
                                                        "lieux": [[0, 0]]})
    monde = _copie(W30.monde)
    monde.evenements.clear()
    monkeypatch.setattr(E, "au_mois", au_mois_sans_cause)
    E.au_mois(monde)
    assert len(monde.evenements) > 1
    with pytest.raises(AssertionError):
        _controler_les_causes(monde)


def test_cause_une_reponse_sans_evenement_est_refusee(W30):
    monde = _copie(W30.monde)
    avant = _json(monde)
    with pytest.raises(IntentionRefusee) as refus:
        recevoir_intention(monde, _reponse(LAISSER, "grande-3"))
    assert str(refus.value) == "aucun événement en attente : grande-3"
    assert _json(monde) == avant and monde.intentions_en_attente == []


def test_cause_un_lieu_affame_depuis_peu_ne_fait_pas_la_cause(W30):
    """Une pose sans dernier jour de faim dans le mois écoulé n'ouvre rien ; on lit la pose, jamais la faim brute."""
    monde = _copie(W30.monde)
    monde.evenements.clear()
    monde.ticks_ecoules = 30 + c.FENETRE_FLUX_TICKS + 1  # le dernier jour de faim (25) n'est plus dans le mois
    assert E.lieux_en_cause(monde) == {}
    E.au_mois(monde)
    assert monde.evenements == {}
    monde.ticks_ecoules = 30
    assert E.lieux_en_cause(monde) == {MAISON: [[10391, 0]]}
    # La faim brute d'un lieu sans pose ne suffit pas.
    monde.modificateurs = [p for p in monde.modificateurs if p.identifiant != "famine"]
    assert next(l for l in monde.cells[10391].lieux if l.rang == 0).duree_faim_ticks > 0
    assert E.lieux_en_cause(monde) == {}


# --- Chaque choix change exactement ce qu'il dit ----------------------------------

def _appliquer(monde):
    engine._appliquer_intentions(monde)


def _cles_differentes(a, b):
    da, db = a.to_dict(), b.to_dict()
    return {cle for cle in da.keys() | db.keys() if da.get(cle) != db.get(cle)}


def _poses(monde):
    return [p.en_document() for p in monde.modificateurs]


def _total_secours(monde):
    return sum(kg for charges in monde.secours.values() for kg in charges.values())


def _controler_l_effet(choix, a, b):
    """`a` a reçu la réponse et joué l'étape des intentions, `b` rien : exactement ce que dit le choix change."""
    cles = _cles_differentes(a, b)
    ja, jb = a.jauges[MAISON], b.jauges[MAISON]
    en_a, en_b = _poses(a), _poses(b)
    nouvelles, perdues = [p for p in en_a if p not in en_b], [p for p in en_b if p not in en_a]
    autres = {m for m in a.jauges.keys() | b.jauges.keys() if a.jauges.get(m) != b.jauges.get(m)}
    assert autres == {MAISON}
    ecarts = {k for k in ja.keys() | jb.keys() if ja.get(k) != jb.get(k)}
    if choix == OUVRIR:
        assert cles == {"evenements", "jauges", "modificateurs", "greniers", "secours"}
        assert ecarts == {"concorde"} and ja["concorde"] == min(3, jb["concorde"] + 1)
        assert nouvelles + perdues and {p["source"] for p in nouvelles + perdues} == {f"jauge:concorde:{MAISON}"}
        gb = b.greniers[MAISON][NOURRITURE]
        kg = 0.25 * gb
        assert a.greniers[MAISON][NOURRITURE] == gb - kg
        assert {m for m in a.greniers if a.greniers[m] != b.greniers.get(m)} == {MAISON}
        assert math.isclose(_total_secours(a) - _total_secours(b), kg)
        assert _total_secours(a) - _total_secours(b) > 0
    elif choix == TAXE:
        assert cles == {"evenements", "jauges", "modificateurs"}
        assert ecarts == {"concorde"} and ja["concorde"] == max(-3, jb["concorde"] - 1)
        assert len(en_a) == len(en_b) + 1
        taxe = [p for p in nouvelles if p["identifiant"] == "taxe_de_disette"]
        assert len(taxe) == 1 and all(p["source"] == f"jauge:concorde:{MAISON}" for p in nouvelles if p not in taxe)
        assert (taxe[0]["grandeur"], taxe[0]["valeur"], taxe[0]["cible"]) == ("prelevement", 0.25, {"pays": MAISON})
        assert taxe[0]["source"] == f"evenement:taxe_de_disette:{MAISON}"
        assert (taxe[0]["debut"], taxe[0]["fin"]) == (30, 120)
    else:
        assert cles == {"evenements", "jauges", "modificateurs"}
        assert ecarts == {"droit"} and ja["droit"] == max(0, jb["droit"] - 5)
        assert perdues == [] and len(nouvelles) == 1
        assert nouvelles[0]["source"] == f"jauge:droit:{MAISON}" and nouvelles[0]["grandeur"] == "prelevement"
        assert math.isclose(nouvelles[0]["valeur"], -0.01)
    assert MAISON not in a.evenements and MAISON in b.evenements


def _deux_copies(W30, choix):
    a, b = _copie(W30.monde), _copie(W30.monde)
    avant = _json(a)
    recevoir_intention(a, _reponse(choix))
    assert _json(a) == avant  # le dépôt ne change pas `to_dict()`
    assert len(a.intentions_en_attente) == 1
    _appliquer(a)
    _appliquer(b)
    return a, b


@pytest.mark.parametrize("choix", [OUVRIR, TAXE, LAISSER])
def test_exactement_chaque_choix_change_ce_qu_il_dit(W30, choix):
    a, b = _deux_copies(W30, choix)
    _controler_l_effet(choix, a, b)


def test_exactement_l_ouverture_garde_ses_kilos_du_depot(W30):
    monde = _copie(W30.monde)
    retenue = recevoir_intention(monde, _reponse(OUVRIR))
    assert retenue.kg == 0.25 * monde.greniers[MAISON][NOURRITURE] and retenue.kg > 0
    assert (retenue.maison, retenue.choix) == (MAISON, OUVRIR)
    taxe = recevoir_intention(_copie(W30.monde), _reponse(TAXE))
    assert taxe.kg == 0


def test_exactement_la_taxe_pese_sur_le_prelevement_puis_expire(W30):
    a, b = _deux_copies(W30, TAXE)
    tenus = [(cid, lieu.rang) for cid, cellule in a.cells.items() for lieu in cellule.lieux if lieu.maitre == MAISON]
    assert tenus
    for cid, rang in tenus:
        assert math.isclose(M.facteur(a, "prelevement", cid, rang), M.facteur(b, "prelevement", cid, rang) + 0.25)
    # Elle compte du tick 30 au tick 119 ; `expirer` l'ôte au début du tick 120.
    def taxes(monde):
        return [p for p in monde.modificateurs if p.identifiant == "taxe_de_disette"]
    a.ticks_ecoules = 119
    M.expirer(a)
    assert len(taxes(a)) == 1
    a.ticks_ecoules = 120
    assert [p.identifiant for p in M.expirer(a)] == ["taxe_de_disette"]
    assert taxes(a) == []


def test_exactement_une_seconde_taxe_renouvelle_la_premiere(W30):
    a, _ = _deux_copies(W30, TAXE)
    a.ticks_ecoules = 40
    a.evenements[MAISON] = {"identifiant": "famine", "ouvert": 40, "lieux": [[10391, 0]]}
    recevoir_intention(a, _reponse(TAXE))
    _appliquer(a)
    (taxe,) = [p for p in a.modificateurs if p.identifiant == "taxe_de_disette"]
    assert (taxe.debut, taxe.fin) == (40, 130)
    tenus = [(cid, lieu.rang) for cid, cellule in a.cells.items() for lieu in cellule.lieux if lieu.maitre == MAISON]
    assert all(math.isclose(M.facteur(a, "prelevement", cid, rang) - 1,
                            sum(p.valeur for p in a.modificateurs
                                if p.grandeur == "prelevement" and ("pays", MAISON) == p.cible)) for cid, rang in tenus)
    assert math.isclose(sum(p.valeur for p in a.modificateurs if p.identifiant == "taxe_de_disette"), 0.25)


def test_exactement_une_reponse_trop_tard_manque_son_effet(W30):
    a, b = _copie(W30.monde), _copie(W30.monde)
    _appliquer(a)  # l'étape des intentions passe avant le dépôt : l'effet manque au tick 30
    recevoir_intention(a, _reponse(TAXE))
    _appliquer(b)
    with pytest.raises(AssertionError):
        _controler_l_effet(TAXE, a, b)


def test_exactement_une_ouverture_qui_saute_le_secours_echoue(W30, monkeypatch):
    def au_panier(self, monde):
        panier = monde.greniers[self.maison]
        panier[NOURRITURE] -= self.kg
        monde.cells[10391].stocks[NOURRITURE] = monde.cells[10391].stocks.get(NOURRITURE, 0.0) + self.kg
    monkeypatch.setattr(OuvrirGrenier, "appliquer", au_panier)
    a, b = _deux_copies(W30, OUVRIR)
    with pytest.raises(AssertionError):
        _controler_l_effet(OUVRIR, a, b)


def test_exactement_une_taxe_a_trente_pour_cent_echoue(W30, monkeypatch):
    donnees = M.charger_donnees()
    plus_lourde = M.Definition("taxe_de_disette", "Taxe de disette", "prelevement", 0.30, "pays", 90)
    faux = M.Donnees(donnees.sources, donnees.grandeurs, {**donnees.definitions, "taxe_de_disette": plus_lourde})
    monkeypatch.setattr(M, "charger_donnees", lambda chemin=None: faux)
    a, b = _deux_copies(W30, TAXE)
    with pytest.raises(AssertionError):
        _controler_l_effet(TAXE, a, b)


def test_exactement_une_concorde_deplacee_de_deux_echoue(W30, monkeypatch):
    vrais = E.charger_evenements()
    choix = tuple(E.Choix(x.identifiant, x.nom, x.dit, x.grenier, {"concorde": 2}, x.modificateurs)
                  if x.identifiant == OUVRIR else x for x in vrais["famine"].choix)
    faux = {"famine": E.Evenement("famine", vrais["famine"].nom, vrais["famine"].dit, "famine", 30, LAISSER, choix)}
    monkeypatch.setattr(E, "charger_evenements", lambda *a, **k: faux)
    a, b = _deux_copies(W30, OUVRIR)
    with pytest.raises(AssertionError):
        _controler_l_effet(OUVRIR, a, b)


def _refus_de(monde, intention):
    avant, file = _json(monde), list(monde.intentions_en_attente)
    with pytest.raises(IntentionRefusee) as refus:
        recevoir_intention(monde, intention)
    assert _json(monde) == avant and monde.intentions_en_attente == file
    return str(refus.value)


def _forcer_concorde(monde, valeur):
    monde.jauges[MAISON] = J.etat(monde, MAISON, J.charger_regles()) | {"concorde": valeur}


def test_exactement_les_refus_mot_pour_mot(W30):
    monde = _copie(W30.monde)
    assert _refus_de(monde, _reponse(LAISSER, "nulle-part")) == "maison inconnue ou mal formée : 'nulle-part'"
    assert _refus_de(monde, _reponse(LAISSER, 7)) == "maison inconnue ou mal formée : 7"
    assert _refus_de(monde, _reponse(LAISSER, "grande-3")) == "aucun événement en attente : grande-3"
    assert _refus_de(monde, _reponse("fuir")) == (
        "choix inconnu : 'fuir' (laisser_faire, lever_une_taxe_de_disette, ouvrir_les_greniers)")
    assert _refus_de(monde, _reponse(["fuir"])).startswith("choix inconnu : ['fuir'] (")
    assert _refus_de(monde, dict(_reponse(LAISSER), kg=5)) == "champ inconnu : kg"
    assert _refus_de(monde, {"type": "repondre_evenement", "maison": MAISON}) == "champ manquant : choix"
    # Une réponse déposée ferme la porte à une seconde, quel que soit son choix.
    recevoir_intention(monde, _reponse(TAXE))
    for choix in (TAXE, OUVRIR, LAISSER):
        assert _refus_de(monde, _reponse(choix)) == f"réponse déjà déposée : {MAISON}"


def test_exactement_le_grenier_vide_refuse_l_ouverture(W30):
    monde = _copie(W30.monde)
    monde.greniers[MAISON][NOURRITURE] = 0
    assert _refus_de(monde, _reponse(OUVRIR)) == f"grenier vide : rien à ouvrir pour {MAISON}"
    # Les autres choix ne touchent pas au grain : ils restent payables.
    recevoir_intention(monde, _reponse(TAXE))


def test_exactement_une_jauge_deja_au_minimum_refuse_la_baisse_et_le_defaut_la_borne(W30):
    monde = _copie(W30.monde)
    _forcer_concorde(monde, -3)
    assert _refus_de(monde, _reponse(TAXE)) == "Concorde déjà à sa borne : -3 points" == (
        f"Concorde déjà à sa borne : {J._points(-3)}")
    recevoir_intention(monde, _reponse(OUVRIR))  # une hausse n'est jamais refusée
    # Le choix par défaut n'est jamais refusé pour sa jauge : il est borné.
    monde = _copie(W30.monde)
    monde.jauges[MAISON] = J.etat(monde, MAISON, J.charger_regles()) | {"droit": 0}
    recevoir_intention(monde, _reponse(LAISSER))
    _appliquer(monde)
    assert monde.jauges[MAISON]["droit"] == 0 and MAISON not in monde.evenements
    # Une hausse au-delà du maximum est bornée, elle non plus n'est pas refusée.
    monde = _copie(W30.monde)
    _forcer_concorde(monde, 3)
    recevoir_intention(monde, _reponse(OUVRIR))
    _appliquer(monde)
    assert monde.jauges[MAISON]["concorde"] == 3


def test_exactement_le_grenier_ne_paie_jamais_deux_fois(W30):
    monde = _copie(W30.monde)
    g = monde.greniers[MAISON][NOURRITURE]
    recevoir_intention(monde, _reponse(OUVRIR))  # engage 0,25 g
    refus = _refus_de(monde, {"type": "ouvrir_grenier", "maison": MAISON, "kg": 0.8 * g})
    assert refus == f"grenier insuffisant : {0.8 * g} kg demandés, {g - 0.25 * g} kg disponibles"
    recevoir_intention(monde, {"type": "ouvrir_grenier", "maison": MAISON, "kg": 0.7 * g})
    # Et réciproquement : un ouvrir_grenier déposé d'abord réduit les kilos de la réponse.
    monde = _copie(W30.monde)
    recevoir_intention(monde, {"type": "ouvrir_grenier", "maison": MAISON, "kg": 0.8 * g})
    retenue = recevoir_intention(monde, _reponse(OUVRIR))
    assert retenue.kg == 0.25 * (g - 0.8 * g) and 0 < retenue.kg < 0.25 * g
    # Un grenier tout engagé ne laisse rien à ouvrir.
    monde = _copie(W30.monde)
    recevoir_intention(monde, {"type": "ouvrir_grenier", "maison": MAISON, "kg": g})
    assert _refus_de(monde, _reponse(OUVRIR)) == f"grenier vide : rien à ouvrir pour {MAISON}"
    # Le total versé aux lieux ne dépasse jamais le grenier.
    monde = _copie(W30.monde)
    recevoir_intention(monde, {"type": "ouvrir_grenier", "maison": MAISON, "kg": 0.8 * g})
    recevoir_intention(monde, _reponse(OUVRIR))
    _appliquer(monde)
    assert monde.greniers[MAISON][NOURRITURE] >= 0


def test_exactement_la_concorde_engagee_par_la_reponse_refuse_le_geste_qui_la_depasse(W30):
    monde = _copie(W30.monde)
    monde.jauges[MAISON] = J.etat(monde, MAISON, J.charger_regles()) | {"concorde": 2, "plume": 100.0}
    recevoir_intention(monde, _reponse(OUVRIR))  # la Concorde passe à 3
    assert _refus_de(monde, {"type": "depenser_jauge", "maison": MAISON, "geste": "affermir_la_concorde"}) == (
        "Concorde déjà à sa borne : 3 points")
    # Sans ce refus, l'étape des intentions lèverait JaugeInvalide.
    sans_refus = _copie(monde)
    sans_refus.intentions_en_attente.append(DepenserJauge(MAISON, "affermir_la_concorde"))
    with pytest.raises(J.JaugeInvalide):
        _appliquer(sans_refus)
    # Dans l'autre ordre, le geste d'abord, la réponse ensuite est bornée : l'étape des intentions passe.
    monde = _copie(W30.monde)
    monde.jauges[MAISON] = J.etat(monde, MAISON, J.charger_regles()) | {"concorde": 2, "plume": 100.0}
    recevoir_intention(monde, {"type": "depenser_jauge", "maison": MAISON, "geste": "affermir_la_concorde"})
    recevoir_intention(monde, _reponse(OUVRIR))
    _appliquer(monde)
    assert monde.jauges[MAISON]["concorde"] == 3


def test_exactement_les_gestes_et_la_reponse_se_jouent_dans_l_ordre_du_depot(W30):
    """La réponse baisse la Concorde de 3 à 2, un premier geste la remonte, un second serait refusé : l'ordre porte."""
    monde = _copie(W30.monde)
    monde.jauges[MAISON] = J.etat(monde, MAISON, J.charger_regles()) | {"concorde": 3, "plume": 200.0}
    recevoir_intention(monde, _reponse(TAXE))
    recevoir_intention(monde, {"type": "depenser_jauge", "maison": MAISON, "geste": "affermir_la_concorde"})
    assert _refus_de(monde, {"type": "depenser_jauge", "maison": MAISON, "geste": "affermir_la_concorde"}) == (
        "Concorde déjà à sa borne : 3 points")
    _appliquer(monde)
    assert monde.jauges[MAISON]["concorde"] == 3


# --- Sans réponse, le choix par défaut ------------------------------------------

@pytest.fixture(scope="module")
def D60(W30):
    """Trois mondes à la borne du tick 60 : sans réponse, avec « ouvrir » déposé au tick 59, et avant le mois du tick 60."""
    monde, rng = _copie(W30.monde), copy.deepcopy(W30.rng)
    _jouer_jusqu_a(monde, rng, 59)
    avant_59 = (_copie(monde), copy.deepcopy(rng))
    sans = SimpleNamespace(monde=monde, rng=rng)
    _jouer_jusqu_a(sans.monde, sans.rng, 60)
    # Réponse déposée au tick 59 : l'étape des intentions du tick 59 la joue.
    au_59 = SimpleNamespace(monde=_copie(avant_59[0]), rng=copy.deepcopy(avant_59[1]))
    recevoir_intention(au_59.monde, _reponse(OUVRIR))
    _jouer_jusqu_a(au_59.monde, au_59.rng, 60)
    # Réponse déposée au tick 60, avant le mois : elle attend dans la file quand le mois se joue.
    avant_mois = SimpleNamespace(monde=_copie(avant_59[0]), rng=copy.deepcopy(avant_59[1]))
    engine.tick(avant_mois.monde, avant_mois.rng, 59)
    recevoir_intention(avant_mois.monde, _reponse(OUVRIR))
    J.avant_le_tick(avant_mois.monde)
    return SimpleNamespace(sans=sans, au_59=au_59, avant_mois=avant_mois)


def test_defaut_sans_reponse_laisser_faire_s_applique_au_mois_suivant(W30, D60):
    sans = D60.sans.monde
    assert sans.ticks_ecoules == 60
    assert sans.jauges[MAISON]["droit"] == 45
    # La cause tient encore (sa famine dure au tick 60) : un nouvel événement remplace le premier.
    assert sans.evenements == {MAISON: {"identifiant": "famine", "ouvert": 60, "lieux": [[10391, 0]]}}
    _controler_les_causes(sans)
    assert W30.monde.jauges[MAISON]["droit"] == 50
    # Le choix par défaut passe par la même fonction que la réponse déposée : même pose de Droit.
    (droit,) = [p for p in sans.modificateurs if p.source == f"jauge:droit:{MAISON}"]
    assert math.isclose(droit.valeur, -0.01) and droit.grandeur == "prelevement"


def test_defaut_une_reponse_deposee_au_tick_59_n_est_pas_fermee_par_defaut(D60):
    sans, repondu = D60.sans.monde, D60.au_59.monde
    assert repondu.jauges[MAISON]["droit"] == 50 and sans.jauges[MAISON]["droit"] == 45
    assert repondu.jauges[MAISON]["concorde"] == sans.jauges[MAISON]["concorde"] + 1
    assert not [p for p in repondu.modificateurs if p.source == f"jauge:droit:{MAISON}"]


def test_defaut_une_reponse_qui_attend_le_mois_n_est_jamais_recouverte(D60):
    monde, rng = D60.avant_mois.monde, D60.avant_mois.rng
    sans = D60.sans.monde
    # Au mois du tick 60, la réponse attend dans la file : l'événement du tick 30 n'est pas fermé par défaut.
    assert monde.jauges[MAISON]["droit"] == 50
    assert monde.evenements[MAISON]["ouvert"] == 30
    assert len(monde.intentions_en_attente) == 1
    concorde_avant = monde.jauges[MAISON]["concorde"]
    engine.tick(monde, rng, 60)
    assert MAISON not in monde.evenements
    assert monde.jauges[MAISON]["concorde"] == min(3, concorde_avant + 1)
    assert monde.jauges[MAISON]["droit"] == 50 and monde.jauges[MAISON]["concorde"] == sans.jauges[MAISON]["concorde"] + 1
    # Aucun nouvel événement ne s'ouvre avant le tick 90 (aucun mois ne passe), ni à celui-ci.
    _jouer_jusqu_a(monde, rng, 90)
    assert monde.evenements == {} and monde.jauges[MAISON]["droit"] == 50


def test_defaut_un_autre_choix_par_defaut_s_applique_avec_ses_kilos(W30, monkeypatch):
    """Un autre choix par défaut s'applique, et ses kilos se comptent comme au dépôt."""
    document = _document()
    document["evenements"]["famine"]["par_defaut"] = OUVRIR
    monkeypatch.setattr(E, "charger_evenements",
                        lambda chemin=None, modificateurs=None, regles=None: E.lire_evenements(document, modificateurs, regles))
    monde = _copie(W30.monde)
    g = monde.greniers[MAISON][NOURRITURE]
    monde.ticks_ecoules = 60
    E.au_mois(monde)
    assert monde.greniers[MAISON][NOURRITURE] == g - 0.25 * g
    assert monde.jauges[MAISON]["concorde"] == W30.monde.jauges[MAISON]["concorde"] + 1
    assert MAISON not in monde.evenements  # fermé ; le dernier jour de faim (25) n'est plus dans le mois du tick 60


def test_defaut_une_maison_sans_lieu_ne_verse_rien_par_defaut(W30, monkeypatch):
    """Un choix par défaut qui verse du grain sur une maison que le secours ne sert pas n'est pas refusé : il ne verse rien."""
    document = _document()
    document["evenements"]["famine"]["par_defaut"] = OUVRIR
    monkeypatch.setattr(E, "charger_evenements",
                        lambda chemin=None, modificateurs=None, regles=None: E.lire_evenements(document, modificateurs, regles))
    monde = _copie(W30.monde)
    g = monde.greniers[MAISON][NOURRITURE]
    monde.greniers[MAISON][NOURRITURE] = 0
    monde.ticks_ecoules = 60
    E.au_mois(monde)
    assert monde.greniers[MAISON][NOURRITURE] == 0 and g > 0
    assert monde.jauges[MAISON]["concorde"] == W30.monde.jauges[MAISON]["concorde"] + 1


# --- L'IA répond par le même chemin, le joueur au même choix obtient le même monde ---

def _reserve_lue(monde, maison):
    """La réserve voulue d'une maison, relue sans `sim/ia.py` : ses habitants, ses salaires dus."""
    from sim.chantiers import salaire_journee_kg
    routes = monde.routes_des_lieux
    indice = routes.noms.index(maison)
    lieux = [(cid, rang) for cid, rang, idx in zip(routes.cids, routes.rangs, routes.maitre_idx) if idx == indice]
    habitants = sum(monde.cells[cid].lieux[rang].population for cid, rang in lieux)
    bourgs = sorted({cid for cid, rang in lieux if rang == 0})
    salaires = 0
    for cid in bourgs:
        plan = monde.plans[cid]
        journees = sum(o.travail_requis - o.travail_fourni for o in (*plan.rues, *plan.parcelles, *plan.batiments)
                       if o.en_chantier)
        salaires += journees * (salaire_journee_kg(monde, cid) if monde.modificateurs else c.SALAIRE_JOURNEE_KG)
    if monde.batiments_de_province and bourgs:
        from sim import batiments
        maitre = monde.cells[bourgs[0]].lieux[0].maitre
        salaires += sum(j * salaire_journee_kg(monde, cid)
                        for cid, j in batiments.journees_restantes(monde, maitre).items())
    return (c.consommation_kg_par_habitant_par_tick(NOURRITURE) * (c.RESERVE_VOULUE_JOURS / c.TICK_DURATION_DAYS)
            * habitants * c.RESERVE_VOULUE_PART_DES_HABITANTS) + salaires


def _lire_reponse(monde, maison, intention):
    """La raison de la réponse de l'IA, lue sur le monde au moment du dépôt, sans `sim/ia.py`."""
    regles = J.charger_regles()
    attente = monde.evenements[maison]
    part = _document()["evenements"]["famine"]["choix"][0]["grenier"]
    grenier, reserve = monde.greniers[maison].get(NOURRITURE, 0), _reserve_lue(monde, maison)
    concorde, minimum = J.etat(monde, maison, regles)["concorde"], regles.jauges["concorde"]["minimum"]
    base = {"evenement": attente["identifiant"], "ouvert": attente["ouvert"], "grenier_nourriture_kg": grenier,
            "reserve_voulue_kg": reserve, "part_du_grenier": part}
    if intention["choix"] == OUVRIR:
        return {"regle": "grenier_au_dessus_de_sa_reserve", **base}
    regle = "grenier_sous_sa_reserve" if intention["choix"] == TAXE else "ni_grain_ni_concorde"
    return {"regle": regle, **base, "concorde": concorde, "minimum": minimum}


def _controler_les_reponses(releve, lectures):
    """Au moins une réponse de l'IA, aucune refusée, chacune avec la raison que le monde donne et sa règle qui tient."""
    reponses = [e for e in releve if e["intention"]["type"] == "repondre_evenement"]
    assert reponses and not [e for e in reponses if "refus" in e]
    for entree in reponses:
        raison, (lue, cause, lieux) = entree["raison"], lectures[(entree["tick"], entree["intention"]["maison"])]
        assert raison == lue
        assert cause and set(lieux) <= {tuple(lieu) for lieu in cause}
        part = raison["part_du_grenier"]
        grenier, reserve = raison["grenier_nourriture_kg"], raison["reserve_voulue_kg"]
        choix = entree["intention"]["choix"]
        if raison["regle"] == "grenier_au_dessus_de_sa_reserve":
            assert choix == OUVRIR and grenier * (1 - part) >= reserve
        elif raison["regle"] == "grenier_sous_sa_reserve":
            assert choix == TAXE and grenier < reserve and raison["concorde"] > raison["minimum"]
        elif raison["regle"] == "ni_grain_ni_concorde":
            assert choix == LAISSER and not (grenier * (1 - part) >= reserve)
            assert not (grenier < reserve and raison["concorde"] > raison["minimum"])
        else:
            raise AssertionError(f"règle inconnue : {raison['regle']!r}")
        assert raison["ouvert"] <= entree["tick"] and raison["evenement"] == "famine"
    return reponses


@pytest.fixture(scope="module")
def IA420(_decor):
    """`_simulate(420, 0, ia=True)` : le relevé, la raison lue au dépôt de chaque réponse, et le monde juste avant la première."""
    from sim import __main__ as cli
    from sim import ia as moteur_ia
    lectures, gardee = {}, {}
    reel = cli.jouer_ia

    def enveloppe(monde, releve, maisons=None):
        if "monde" not in gardee and any(p["intention"]["type"] == "repondre_evenement"
                                         for p in moteur_ia.decider_intentions(monde, releve, maisons)):
            gardee["monde"] = copy.deepcopy(monde)
        deja = len(releve)
        reel(monde, releve, maisons)
        for entree in releve[deja:]:
            if entree["intention"]["type"] == "repondre_evenement":
                maison = entree["intention"]["maison"]
                ouvert = monde.evenements[maison]["ouvert"]
                lectures[(entree["tick"], maison)] = (
                    _lire_reponse(monde, maison, entree["intention"]), _cause_de(monde, maison, ouvert),
                    [tuple(lieu) for lieu in monde.evenements[maison]["lieux"]])

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(cli, "jouer_ia", enveloppe)
        resume, monde = cli._simulate(420, 0, ia=True)
    assert "monde" in gardee, "aucune maison de l'IA n'a répondu dans les 420 jours"
    return SimpleNamespace(resume=resume, monde=monde, releve=resume["ia"]["releve"], lectures=lectures,
                           avant=gardee["monde"])


def test_ia_et_joueur_l_ia_repond_par_le_depot_avec_sa_raison(IA420):
    reponses = _controler_les_reponses(IA420.releve, IA420.lectures)
    print("\nréponses de l'IA : " + "; ".join(
        f"{e['intention']['maison']} → {e['intention']['choix']} (tick {e['tick']})" for e in reponses))
    # Les événements viennent des données : les maisons de l'IA répondent à ceux que le monde a ouverts.
    assert {e["intention"]["maison"] for e in reponses} <= {m.id for m in IA420.monde.maisons}
    assert {e["intention"]["choix"] for e in reponses} <= {OUVRIR, TAXE, LAISSER}


def test_ia_et_joueur_une_raison_faussee_ou_une_regle_inconnue_echoue(IA420):
    reponses = [e for e in IA420.releve if e["intention"]["type"] == "repondre_evenement"]
    faux = copy.deepcopy(reponses[0])
    faux["raison"]["grenier_nourriture_kg"] += 1
    with pytest.raises(AssertionError):
        _controler_les_reponses([faux], IA420.lectures)
    inconnue = copy.deepcopy(reponses[0])
    inconnue["raison"]["regle"] = "au_hasard"
    with pytest.raises(AssertionError):
        _controler_les_reponses([inconnue], IA420.lectures)
    with pytest.raises(AssertionError):
        _controler_les_reponses([], IA420.lectures)


def test_ia_et_joueur_le_joueur_au_meme_choix_obtient_le_meme_monde(IA420):
    from sim import __main__ as cli
    par_tick = {}
    for entree in IA420.releve:
        if "refus" not in entree:
            par_tick.setdefault(entree["tick"], []).append(entree["intention"])

    def joueur(monde, releve_vide, maisons=None):
        for intention in par_tick.get(monde.ticks_ecoules, ()):
            recevoir_intention(monde, copy.deepcopy(intention))

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(cli, "jouer_ia", joueur)
        _, monde_joueur = cli._simulate(420, 0, ia=True)
    assert _json(monde_joueur) == _json(IA420.monde)
    assert IA420.monde.evenements  # des événements ouverts à la borne du jour 420


def test_ia_et_joueur_un_releve_sans_sa_premiere_reponse_donne_un_autre_monde(IA420):
    """Sur le monde juste avant la première réponse : le relevé rejoué en entier, puis sans elle, un tick."""
    from sim import ia as moteur_ia
    from sim.capitales import toutes_les_maisons_de_l_ia
    depart = IA420.avant
    releve = []
    avec = _copie(depart)
    moteur_ia.jouer_ia(avec, releve, toutes_les_maisons_de_l_ia(avec))
    premiere = next(e for e in releve if e["intention"]["type"] == "repondre_evenement")
    sans = _copie(depart)
    for entree in releve:
        if entree is not premiere and "refus" not in entree:
            recevoir_intention(sans, copy.deepcopy(entree["intention"]))
    engine.tick(avec, random.Random(0), avec.ticks_ecoules)
    engine.tick(sans, random.Random(0), sans.ticks_ecoules)
    assert _json(avec) != _json(sans)
    maison = premiere["intention"]["maison"]
    assert maison not in avec.evenements and maison in sans.evenements


def test_ia_et_joueur_une_ia_qui_ecrit_sa_reponse_dans_le_monde_laisse_le_releve_sans_reponse(IA420):
    from sim import ia as moteur_ia
    from sim.capitales import toutes_les_maisons_de_l_ia
    monde = _copie(IA420.avant)
    releve = []

    def ia_qui_ecrit(monde, releve, maisons=None):
        for proposition in moteur_ia.decider_intentions(monde, releve, maisons):
            if proposition["intention"]["type"] == "repondre_evenement":
                intention = proposition["intention"]
                E.appliquer_choix(monde, intention["maison"], intention["choix"], 0)

    ia_qui_ecrit(monde, releve, toutes_les_maisons_de_l_ia(monde))
    assert releve == [] and monde.intentions_en_attente == []
    with pytest.raises(AssertionError):
        _controler_les_reponses(releve, IA420.lectures)


@pytest.mark.parametrize("facteur, concorde, attendu", [
    (4.0, None, OUVRIR),       # grenier forcé à 4 × la réserve
    (0.5, 0, TAXE),            # grenier forcé à la moitié de la réserve, Concorde au neutre
    (0.5, -3, LAISSER),        # même grenier, Concorde à son minimum
])
def test_ia_et_joueur_les_trois_regles_donnent_le_meme_monde(IA420, facteur, concorde, attendu):
    from sim import ia as moteur_ia
    from sim.capitales import toutes_les_maisons_de_l_ia
    premiere = next(e for e in IA420.releve if e["intention"]["type"] == "repondre_evenement")
    cle = premiere["intention"]["maison"]

    def forcer(monde):
        monde.greniers[cle][NOURRITURE] = facteur * _reserve_lue(monde, cle)
        if concorde is not None:
            monde.jauges[cle] = J.etat(monde, cle, J.charger_regles()) | {"concorde": concorde}
        return monde

    par_l_ia = forcer(_copie(IA420.avant))
    releve = []
    moteur_ia.jouer_ia(par_l_ia, releve, toutes_les_maisons_de_l_ia(par_l_ia))
    reponse = next(e for e in releve if e["intention"]["type"] == "repondre_evenement" and e["intention"]["maison"] == cle)
    assert "refus" not in reponse and reponse["intention"]["choix"] == attendu
    assert reponse["raison"] == _lire_reponse(par_l_ia, cle, reponse["intention"])
    par_le_joueur = forcer(_copie(IA420.avant))
    for entree in releve:
        if "refus" not in entree:
            recevoir_intention(par_le_joueur, copy.deepcopy(entree["intention"]))
    engine.tick(par_l_ia, random.Random(0), par_l_ia.ticks_ecoules)
    engine.tick(par_le_joueur, random.Random(0), par_le_joueur.ticks_ecoules)
    assert _json(par_l_ia) == _json(par_le_joueur)
    assert cle not in par_l_ia.evenements


# --- Le service ----------------------------------------------------------------

def _poster(port, chemin, corps):
    from sim.tests.test_monde import requete_service
    return requete_service(port, chemin, "POST", json.dumps(corps).encode())


def test_service_refuse_la_reponse_avant_le_depart_et_pour_une_autre_maison():
    from sim.tests.test_monde import _service_epreuve
    with _service_epreuve(epreuve=True) as (serveur, port):
        statut, refus, _ = _poster(port, "/intention", _reponse(LAISSER, "grande-3"))
        assert statut == 400 and refus == {
            "acceptee": False, "erreur": "départ non appliqué : choisir une terre avant de répondre à un événement"}
        assert serveur.world.intentions_en_attente == []


def _faire_famine_au_bar(port, serveur):
    """Le joueur choisit `seigneurie-1` ; au tick 25, la faim de son bourg passe le seuil du secours et la famine se pose.

    `POST /epreuve/vider-panier` ne suffit pas : chaque jour, le lieu mange sa récolte au tick et sa faim retombe à 0
    avant d'avoir passé une semaine. Le montage écrit donc la faim et pose la famine par la fonction du moteur
    (`poser_les_famines`), sous le verrou du tick, comme les autres épreuves de ce service qui écrivent dans le monde.
    """
    from sim.tests.test_monde import requete_service
    cid = next(d["cell_id"] for d in serveur.document_departs()["departs"] if d["id"] == 1)
    assert _poster(port, "/intention", {"type": "choisir_depart", "seigneurie": 1})[0] == 200
    assert requete_service(port, "/tick?n=25", "POST")[0] == 200
    with serveur.verrou_tick:
        bourg = next(lieu for lieu in serveur.world.cells[cid].lieux if lieu.rang == 0)
        assert bourg.maitre == "seigneurie-1"
        bourg.duree_faim_ticks = c.FAIM_AVANT_SECOURS_JOURS // c.TICK_DURATION_DAYS + 1
        assert E.poser_les_famines(serveur.world, {(cid, 0)}) == [(cid, 0)]
    assert requete_service(port, f"/tick?n={c.FENETRE_FLUX_TICKS - 25}", "POST")[1]["tick"] == c.FENETRE_FLUX_TICKS
    assert serveur.world.evenements == {}  # le mois se joue au début du tick suivant
    # L'événement s'ouvre au tick 30, publié avec le tick 31.
    assert requete_service(port, "/tick?n=1", "POST")[1]["tick"] == c.FENETRE_FLUX_TICKS + 1
    return cid


def test_service_sert_l_evenement_ses_choix_et_recoit_la_reponse():
    from sim.tests.test_monde import _service_epreuve, requete_service
    bar = "seigneurie-1"
    with _service_epreuve(epreuve=True) as (serveur, port):
        _faire_famine_au_bar(port, serveur)
        statut, document, _ = requete_service(port, f"/evenement?maison={bar}")
        assert statut == 200 and document["maison"] == bar and document["tick"] == 31
        assert document["date"] == serveur.world.date_simulation
        evenement = document["evenement"]
        donnees = E.charger_evenements()["famine"]
        assert [evenement[k] for k in ("identifiant", "nom", "dit", "ouvert", "ferme_au_tick", "par_defaut")] == [
            "famine", donnees.nom, donnees.dit, 30, 60, LAISSER]
        assert evenement["ouvert_date"] == c.date_de_tick(30)
        assert [x["id"] for x in evenement["choix"]] == [OUVRIR, TAXE, LAISSER]
        grenier = requete_service(port, f"/pays?maison={bar}")[1]["totaux"]["grenier_nourriture_kg"]
        ouvrir, taxe, laisser = evenement["choix"]
        assert grenier > 0 and ouvrir["grenier_kg"] == 0.25 * grenier
        assert taxe["grenier_kg"] is None and laisser["grenier_kg"] is None
        assert (ouvrir["jauges"], taxe["jauges"], laisser["jauges"]) == ({"concorde": 1}, {"concorde": -1}, {"droit": -5})
        assert ouvrir["modificateurs"] == laisser["modificateurs"] == []
        assert taxe["modificateurs"] == [{"nom": "Taxe de disette", "grandeur": "prelevement",
                                          "grandeur_nom": "Prélèvement", "valeur": 0.25, "portee": "pays",
                                          "duree_jours": 90}]
        assert [x["refus"] for x in evenement["choix"]] == [None, None, None]
        assert [x["nom"] for x in evenement["choix"]] == [x.nom for x in donnees.choix]
        # Ses lieux portent bien la pose `famine` dans `/modificateurs`.
        poses = requete_service(port, "/modificateurs")[1]["poses"]
        for cid, rang in evenement["lieux"]:
            assert any(p["identifiant"] == "famine" and p["cible"] == {"lieu": [cid, rang]} for p in poses)
        assert evenement["lieux"]
        # Une autre maison n'a pas d'événement ; les paramètres invalides reçoivent leur code.
        assert requete_service(port, "/evenement?maison=grande-3")[1]["evenement"] is None
        assert requete_service(port, "/evenement?maison=")[0] == 400
        assert requete_service(port, "/evenement")[0] == 400
        assert requete_service(port, "/evenement?maison=inconnue")[0] == 404
        # Seule la maison du joueur répond à ses événements.
        statut, refus, _ = _poster(port, "/intention", _reponse(LAISSER, "grande-3"))
        assert statut == 400 and refus == {
            "acceptee": False, "erreur": "maison interdite : seule la maison du joueur répond à ses événements"}
        # La réponse du joueur : acceptée, puis une seconde refusée avant le tick.
        statut, reponse, _ = _poster(port, "/intention", _reponse(TAXE, bar))
        assert statut == 200 and reponse == {"acceptee": True, "appliquee_au_tick": 31}
        statut, refus, _ = _poster(port, "/intention", _reponse(OUVRIR, bar))
        assert statut == 400 and refus == {"acceptee": False, "erreur": f"réponse déjà déposée : {bar}"}
        refus_vu = requete_service(port, f"/evenement?maison={bar}")[1]["evenement"]["choix"]
        assert {x["id"]: x["refus"] for x in refus_vu}[OUVRIR] == f"réponse déjà déposée : {bar}"
        assert requete_service(port, "/tick?n=1", "POST")[0] == 200
        assert requete_service(port, f"/evenement?maison={bar}")[1]["evenement"] is None
        poses = requete_service(port, "/modificateurs")[1]["poses"]
        (taxe_posee,) = [p for p in poses if p["identifiant"] == "taxe_de_disette"]
        assert taxe_posee["cible"] == {"pays": bar} and taxe_posee["source"] == f"evenement:taxe_de_disette:{bar}"
        assert taxe_posee["nom"] == "Taxe de disette" and taxe_posee["fin"] == taxe_posee["debut"] + 90
        lignes = [ligne for lieu in requete_service(port, "/modificateurs")[1]["lieux"]
                  for ligne in lieu["grandeurs"].get("prelevement", {}).get("lignes", [])
                  if ligne["identifiant"] == "taxe_de_disette"]
        assert lignes and all(ligne["fin_date"] == c.date_de_tick(taxe_posee["fin"]) for ligne in lignes)


def test_service_une_ia_qui_echoue_apres_le_mois_defait_les_evenements(monkeypatch):
    from sim import service
    from sim.tests.test_monde import _service_ia_en_processus, requete_service
    ouverts = {}
    with _service_ia_en_processus() as (serveur, port):
        monkeypatch.setattr(service, "jouer_ia", lambda monde, releve, maisons=None: None)
        assert requete_service(port, f"/tick?n={c.FENETRE_FLUX_TICKS}", "POST")[0] == 200
        avant = (_json(serveur.world), list(serveur.world.modificateurs), dict(serveur.world.jauges))
        assert serveur.world.evenements == {}

        def echouer(monde, releve, maisons=None):
            ouverts.update(monde.evenements)  # le mois a ouvert l'événement avant l'IA
            raise ValueError("ia en panne")

        monkeypatch.setattr(service, "jouer_ia", echouer)
        statut, corps, _ = requete_service(port, "/tick?n=1", "POST")
        assert statut == 500 and corps == {"erreur": "ia : ia en panne"}
        assert ouverts and set(ouverts) == {MAISON}
        assert serveur.world.evenements == {} and "evenements" not in serveur.world.to_dict()
        assert (_json(serveur.world), list(serveur.world.modificateurs), dict(serveur.world.jauges)) == avant
        # Le tick suivant, l'IA rétablie, rejoue le mois et ouvre le même événement.
        monkeypatch.setattr(service, "jouer_ia", lambda monde, releve, maisons=None: None)
        assert requete_service(port, "/tick?n=1", "POST")[0] == 200
        assert serveur.world.evenements == ouverts
