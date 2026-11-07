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

Chaque usage le dit dans son test. Le monde du jeu, lui, n'a plus que la
soudure : cette aide ne vit que sous `sim/tests/`.
"""
import sim.constants as _constantes
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


def amorcer_comme_avant_la_soudure(monkeypatch):
    """Pour la durée d'un test (ou d'un `MonkeyPatch.context()`) : le monde chargé l'est comme avant."""
    monkeypatch.setattr(_monde, "amorcer_lieux", _enveloppe(_monde.amorcer_lieux))
    monkeypatch.setattr(_monde, "_porter_la_soudure_dans_chaque_lieu", lambda cellule: None)


def poser():
    """Dans un processus lancé par une épreuve (`python -c`), pour toute sa durée."""
    _monde.amorcer_lieux = _enveloppe(_monde.amorcer_lieux)
    _monde._porter_la_soudure_dans_chaque_lieu = lambda cellule: None


# Le préambule d'un `python -c` d'épreuve qui joue le monde d'avant la soudure.
PREAMBULE = "from sim.tests.amorcage_d_avant import poser; poser()\n"
