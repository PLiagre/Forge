"""L'amorçage d'avant la soudure, pour les épreuves dont il est le décor.

Jusqu'au 7 novembre 2026, une cellule partait avec cinq ticks de ration, plus
trente ticks du manque d'une ville, partagés entre ses lieux par surface ;
Paris était vide avant avril 1400. La soudure (`sim.world._seed_food_stock`,
`JOUR_DE_LA_MOISSON`) a remplacé cet amorçage dans le monde.

Certaines épreuves en gardent le décor, et seulement celles-ci :

- les **réponses figées du pont** (`3d/unity/.../Pont/Tests/*.json`) : elles
  éprouvent le contrat de lecture entre le service et Unity, et les tests C#
  qui les lisent en épinglent les chiffres ;
- les **calibrages documentés** dans `sim/MODELE.md` (la part coutumière, les
  départs actifs), mesurés sur ce monde-là et cités au chiffre près ;
- les épreuves d'une **famine précoce** (le programme de l'IA qui réagit à la
  faim du bourg, la distribution intérieure qui coûte, le secours) : elles
  éprouvent la réaction à la faim, pas la date où elle vient.

Le décor d'avant la soudure est aussi celui d'avant la famine (lot #1029,
réponse A du 10 novembre 2026) et d'avant la réserve des villes affamées (lot
#1057) : la famine ne pose rien, une ville affamée n'a que sa ration du tick
pour garde, et ces épreuves gardent leurs octets. Avec cinq jours de stock,
toute ville affamée de ce décor serait sous sa réserve et cesserait d'exporter.
Chaque usage le dit dans son test. Le monde du jeu, lui, n'a
plus que la soudure : cette aide ne vit que sous `sim/tests/`.
"""
import sim.constants as _constantes
import sim.evenements as _evenements
import sim.world as _monde
from sim.model import ecrire_stock_marchandise

# Les deux constantes retirées du moteur le 7 novembre 2026, gardées ici seules.
RESERVE_D_AVANT_TICKS = 5
RESERVE_DES_VILLES_D_AVANT_TICKS = 30


def _enveloppe(amorcer_lieux):
    """`amorcer_lieux` précédé de l'ancien stock de la cellule (cinq ticks, plus un mois du manque d'une ville)."""
    lecture = {}

    def amorcer(cellule):
        if not lecture:
            from sim.engine import population_soutenable_de
            from sim.villes import attribuer_villes, charger_villes
            document = _monde.World.lire_carte()
            lecture["carte"] = {int(brute["cell_id"]): brute for brute in document["cellules"]}
            lecture["villes"] = set(attribuer_villes(document, charger_villes()).placees.values())
            lecture["soutenable"] = population_soutenable_de
        ration = _constantes.FOOD_CONSUMPTION_KG_PER_PERSON_PER_TICK
        stock = cellule.population * ration * RESERVE_D_AVANT_TICKS
        if cellule.cell_id in lecture["villes"]:
            soutenable = lecture["soutenable"](cellule, lecture["carte"])
            manque_kg = max(0.0, cellule.population - soutenable) * ration
            stock = round(stock + manque_kg * RESERVE_DES_VILLES_D_AVANT_TICKS,
                          _constantes.SNAPSHOT_FLOAT_DECIMALS)
        ecrire_stock_marchandise(cellule, _constantes.MARCHANDISE_NOURRITURE, stock)
        return amorcer_lieux(cellule)

    return amorcer


def _ne_pose_aucune_famine(monde, affames, donnees=None):
    return []


def couper_la_famine(monkeypatch):
    """Pour la durée d'un test : un lieu affamé ne reçoit plus la famine (le monde d'avant le lot #1029)."""
    monkeypatch.setattr(_evenements, "poser_les_famines", _ne_pose_aucune_famine)


def _reserve_d_avant(chemin=None):
    return 1


def _charger_sans_releve_des_champs(charger):
    """`World.charger` d'avant : le monde rendu n'a pas de relevé des champs, donc pas de ville affamée."""
    def charger_d_avant(cls, *args, **kwargs):
        monde = charger.__func__(cls, *args, **kwargs)
        monde.populations_soutenables = None
        return monde

    return classmethod(charger_d_avant)


def garder_le_commerce_d_avant(monkeypatch):
    """Pour la durée d'un test : une ville affamée garde sa ration du tick, comme avant le lot #1057.

    Deux gestes, parce que les épreuves chargent le monde sous ce décor mais le
    jouent après l'avoir quitté (un `MonkeyPatch.context()` qui ne couvre que le
    chargement) : le lecteur rend 1, et le monde chargé ne porte pas
    `populations_soutenables` (l'absence déclarée, la règle d'avant), si bien
    que la règle suit le monde et non la durée du patch.
    """
    monkeypatch.setattr(_constantes, "reserve_ville_affamee_jours", _reserve_d_avant)
    monkeypatch.setattr(_monde.World, "charger",
                        _charger_sans_releve_des_champs(_monde.World.__dict__["charger"]))


def amorcer_comme_avant_la_soudure(monkeypatch):
    """Pour la durée d'un test (ou d'un `MonkeyPatch.context()`) : le monde chargé l'est comme avant, sans famine ni réserve."""
    couper_la_famine(monkeypatch)
    garder_le_commerce_d_avant(monkeypatch)
    monkeypatch.setattr(_monde, "amorcer_lieux", _enveloppe(_monde.amorcer_lieux))
    monkeypatch.setattr(_monde, "_porter_la_soudure_dans_chaque_lieu", lambda cellule: None)


def poser():
    """Dans un processus lancé par une épreuve (`python -c`), pour toute sa durée."""
    _monde.amorcer_lieux = _enveloppe(_monde.amorcer_lieux)
    _monde._porter_la_soudure_dans_chaque_lieu = lambda cellule: None
    _evenements.poser_les_famines = _ne_pose_aucune_famine
    _constantes.reserve_ville_affamee_jours = _reserve_d_avant
    _monde.World.charger = _charger_sans_releve_des_champs(_monde.World.__dict__["charger"])


# Le préambule d'un `python -c` d'épreuve qui joue le monde d'avant la soudure.
PREAMBULE = "from sim.tests.amorcage_d_avant import poser; poser()\n"
