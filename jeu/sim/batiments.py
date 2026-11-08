"""Les bâtiments de province : poser, payer, bâtir, puis poser leurs modificateurs.

Un bâtiment de province (`data/batiments.toml`) se pose dans une cellule — la
province — dont la maison tient le bourg, par l'intention
`batir_dans_une_province`, du joueur depuis la carte ou de l'IA, par le même
chemin (décision 38). `World.batiments_de_province` garde ses chantiers et ses
bâtiments ; la cible reste `cell_id`, la seule clé spatiale.

Chaque jour, après les chantiers du plan, un bâtiment en chantier prend au
plus `bras_par_jour` paysans de sa cellule, qui deviennent ouvriers pour la
journée (ils manquent aux champs du bourg), et paie leur journée au grenier de
la maison : le grain quitte le grenier et entre au panier du bourg, où ces
gens le mangent (économie physique, décision 35). Sans grain pour payer ni
bras, le chantier attend. Achevé, il pose ses modificateurs sur sa cellule :
le moulin récolte vraiment 10 % de grain en plus.
"""
from dataclasses import dataclass, replace
import math
from pathlib import Path
import tomllib

import sim.constants as _constantes
from sim import modificateurs as _modificateurs
from sim.chantiers import salaire_journee_kg
from sim.model import (contenus_des_paniers, ecrire_habitants_par_metier, ecrire_ouvriers_du_jour,
                       ecrire_stock_marchandise, lire_habitants_par_metier, lire_ouvriers_du_jour)

_CHEMIN = Path(__file__).parents[1] / "data" / "batiments.toml"
_CHAMPS = {"nom", "dit", "journees", "bras_par_jour", "pieces", "modificateurs", "un_par_cellule"}
SOURCE = "batiment"


class BatimentInvalide(ValueError):
    """Une donnée ou un geste de bâtiment que le monde refuse, avec sa raison."""


@dataclass(frozen=True)
class TypeDeBatiment:
    identifiant: str
    nom: str
    dit: str
    journees: int
    bras_par_jour: int
    pieces: int
    modificateurs: tuple
    un_par_cellule: bool


@dataclass(frozen=True)
class BatimentDeProvince:
    identifiant: int
    nature: str
    cell_id: int
    maison: str
    travail_requis: int
    travail_fourni: int
    en_chantier: bool
    debut: int
    fin: int | None = None

    @property
    def source(self) -> str:
        return f"{SOURCE}:{self.nature}-{self.identifiant}"

    def en_document(self) -> dict:
        return {"identifiant": self.identifiant, "nature": self.nature, "cell_id": self.cell_id,
                "maison": self.maison, "travail_requis": self.travail_requis,
                "travail_fourni": self.travail_fourni, "en_chantier": self.en_chantier,
                "debut": self.debut, "fin": self.fin}


def _entier(valeur, ou, minimum):
    if isinstance(valeur, bool) or not isinstance(valeur, int) or valeur < minimum:
        raise BatimentInvalide(f"{ou} : entier au moins égal à {minimum} attendu")
    return valeur


def lire_types(document, modificateurs=None) -> dict:
    """Valide un document déjà lu ; chaque modificateur nommé existe et se pose sur une cellule."""
    donnees = _modificateurs.charger_donnees() if modificateurs is None else modificateurs
    types = {}
    for identifiant, brute in sorted((document.get("batiments") or {}).items()):
        if not isinstance(brute, dict) or set(brute) - _CHAMPS:
            raise BatimentInvalide(f"batiments.{identifiant} : champs inconnus {sorted(set(brute) - _CHAMPS)}")
        nom = brute.get("nom")
        if not isinstance(nom, str) or not nom.strip():
            raise BatimentInvalide(f"batiments.{identifiant}.nom : texte non vide attendu")
        pieces = _entier(brute.get("pieces"), f"batiments.{identifiant}.pieces", 0)
        if pieces:
            raise BatimentInvalide(f"batiments.{identifiant}.pieces : le moteur ne porte pas encore de pièces "
                                   "(jalon 8) ; un coût en pièces ne se paierait nulle part")
        noms = brute.get("modificateurs") or []
        for nom_mod in noms:
            definition = donnees.definitions.get(nom_mod)
            if definition is None:
                raise BatimentInvalide(f"batiments.{identifiant}.modificateurs : {nom_mod!r} inconnu des données")
            if definition.portee != "cellule":
                raise BatimentInvalide(f"batiments.{identifiant}.modificateurs : {nom_mod!r} ne se pose pas "
                                       "sur une cellule")
        un_par_cellule = brute.get("un_par_cellule", False)
        if not isinstance(un_par_cellule, bool):
            raise BatimentInvalide(f"batiments.{identifiant}.un_par_cellule : vrai ou faux attendu")
        types[identifiant] = TypeDeBatiment(
            identifiant, nom, str(brute.get("dit", "")),
            _entier(brute.get("journees"), f"batiments.{identifiant}.journees", 1),
            _entier(brute.get("bras_par_jour"), f"batiments.{identifiant}.bras_par_jour", 1),
            pieces, tuple(noms), un_par_cellule)
    return types


def charger_types(chemin=None) -> dict:
    with open(chemin if chemin is not None else _CHEMIN, "rb") as fichier:
        return lire_types(tomllib.load(fichier))


def journees(monde, type_, cell_id) -> int:
    """Les journées que demande ce bâtiment dans cette cellule, durée modifiée comprise."""
    return _modificateurs.ajuster_journees(monde, cell_id, type_.journees)


def cout_kg(monde, type_, cell_id) -> float:
    """Le grain qu'il coûte : ses journées, payées au salaire du bourg (coût modifié compris)."""
    return journees(monde, type_, cell_id) * salaire_journee_kg(monde, cell_id)


def _grenier(monde, maison):
    return (monde.greniers.get(maison) or {}).get(_constantes.MARCHANDISE_NOURRITURE, 0.0)


def verifier(monde, maison, cell_id, nature, types, engages=()) -> str | None:
    """La raison du refus, ou None. `engages` : les (cellule, nature) déjà déposés par cette maison."""
    type_ = types.get(nature)
    if type_ is None:
        return f"bâtiment inconnu : {nature!r} ({', '.join(sorted(types))})"
    if not isinstance(maison, str) or not any(m.id == maison for m in monde.maisons):
        return f"maison inconnue ou mal formée : {maison!r}"
    cellule = monde.cells.get(cell_id) if not isinstance(cell_id, bool) else None
    if cellule is None:
        return f"cellule inconnue : {cell_id!r}"
    bourg = next((l for l in cellule.lieux if l.rang == 0), None)
    if bourg is None or bourg.maitre != maison:
        return f"pas sur vos terres : le bourg de la cellule {cell_id} est à {getattr(bourg, 'maitre', None)!r}"
    if type_.un_par_cellule and (
            any(b.cell_id == cell_id and b.nature == nature for b in getattr(monde, "batiments_de_province", ()))
            or (cell_id, nature) in engages):
        return f"un seul {type_.nom.lower()} par province : la cellule {cell_id} en a déjà un"
    cout = cout_kg(monde, type_, cell_id)
    deja = sum(cout_kg(monde, types[n], c) for c, n in engages if n in types)
    disponible = _grenier(monde, maison) - deja
    if disponible < cout:
        return f"grenier insuffisant : {cout:g} kg de grain demandés, {disponible:g} kg disponibles"
    metiers = lire_habitants_par_metier(cellule)
    paysans = cellule.population if metiers == -1 else metiers.get(_constantes.METIER_PAYSANS, 0)
    if paysans < type_.bras_par_jour:
        return f"pas assez de bras : {type_.bras_par_jour} paysans par jour demandés, {paysans} dans la cellule"
    return None


def poser(monde, maison, cell_id, nature, types=None) -> BatimentDeProvince:
    """Ouvre le chantier (l'intention s'applique) : ses journées comptées avec la durée modifiée."""
    types = charger_types() if types is None else types
    type_ = types[nature]
    identifiant = max((b.identifiant for b in monde.batiments_de_province), default=-1) + 1
    batiment = BatimentDeProvince(identifiant, nature, cell_id, maison, journees(monde, type_, cell_id), 0, True,
                                  monde.ticks_ecoules)
    monde.batiments_de_province = [*monde.batiments_de_province, batiment]
    return batiment


def avancer(monde, types=None):
    """Un jour de chantier pour chaque bâtiment, par identifiant ; achevé, il pose ses modificateurs."""
    chantiers = [b for b in getattr(monde, "batiments_de_province", ()) if b.en_chantier]
    if not chantiers:
        return
    types = charger_types() if types is None else types
    donnees = _modificateurs.charger_donnees()
    nourriture = _constantes.MARCHANDISE_NOURRITURE
    paysans_nom, ouvriers_nom = _constantes.METIER_PAYSANS, _constantes.METIER_OUVRIERS
    nouveaux = {b.identifiant: b for b in monde.batiments_de_province}
    for batiment in sorted(chantiers, key=lambda b: b.identifiant):
        cellule = monde.cells[batiment.cell_id]
        bourg = next((l for l in cellule.lieux if l.rang == 0), None)
        metiers = lire_habitants_par_metier(cellule)
        panier = monde.greniers.get(batiment.maison)
        # La maison a été vérifiée maîtresse du bourg au dépôt ; le tick ne relit
        # jamais les maîtres (MODELE.md, « Les personnes »).
        if bourg is None or metiers == -1 or panier is None:
            continue  # rien n'est mesuré, ou plus de grenier : le chantier attend
        salaire = salaire_journee_kg(monde, batiment.cell_id)
        payables = math.floor(panier.get(nourriture, 0.0) / salaire)
        restant = batiment.travail_requis - batiment.travail_fourni
        personnes = min(types[batiment.nature].bras_par_jour, restant, payables, metiers.get(paysans_nom, 0))
        if personnes <= 0:
            continue
        metiers = dict(metiers)
        metiers[paysans_nom] -= personnes
        if not metiers[paysans_nom]:
            del metiers[paysans_nom]
        metiers[ouvriers_nom] = metiers.get(ouvriers_nom, 0) + personnes
        ecrire_habitants_par_metier(cellule, metiers)
        ecrire_ouvriers_du_jour(bourg, lire_ouvriers_du_jour(bourg) + personnes)
        montant = personnes * salaire
        panier[nourriture] = panier.get(nourriture, 0.0) - montant
        for entite in (bourg, cellule):
            ecrire_stock_marchandise(entite, nourriture, contenus_des_paniers((entite,), nourriture)[0] + montant)
        fourni = batiment.travail_fourni + personnes
        acheve = fourni >= batiment.travail_requis
        nouveaux[batiment.identifiant] = replace(batiment, travail_fourni=fourni, en_chantier=not acheve,
                                                 fin=monde.ticks_ecoules if acheve else None)
        if acheve:
            for identifiant in types[batiment.nature].modificateurs:
                _modificateurs.poser(monde, identifiant, nouveaux[batiment.identifiant].source,
                                     {"cellule": batiment.cell_id}, donnees)
    monde.batiments_de_province = [nouveaux[i] for i in sorted(nouveaux)]


def journees_restantes(monde, maison) -> dict:
    """cell_id → journées encore à payer par cette maison (l'IA les compte dans sa réserve)."""
    restantes = {}
    for b in getattr(monde, "batiments_de_province", ()):
        if b.en_chantier and b.maison == maison:
            restantes[b.cell_id] = restantes.get(b.cell_id, 0) + b.travail_requis - b.travail_fourni
    return restantes


def document_des_batiments(monde, cellules=None, types=None) -> list:
    """Les bâtiments (et chantiers) des cellules données, ou de toutes, pour le service et la photographie."""
    types = charger_types() if types is None else types
    return [b.en_document() | {"nom": types[b.nature].nom if b.nature in types else b.nature}
            for b in getattr(monde, "batiments_de_province", ())
            if cellules is None or b.cell_id in cellules]
