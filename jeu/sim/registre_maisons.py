"""Registre pur des maisons du monde, dérivé des trois tables de 1400."""
from dataclasses import dataclass
import json
from pathlib import Path

from sim.capitales import Capitale, charger_capitales, cellule_de_capitale
from sim.maisons import charger_maisons
from sim.model import _NoBadSpatialField
from sim.puissances import _CHEMIN_TABLE, _texte, PuissanceInvalide, charger_table
from sim.seigneuries import charger_seigneuries, cellule_du_siege, identifiant_de_seigneurie

@dataclass(frozen=True)
class MaisonDuMonde(_NoBadSpatialField):
    id: str
    nom: str
    sorte: str
    suzerain: str | None
    siege: str
    cell_id: int | None
    rang: int | None
    hors_carte: str | None

def valider_registre_maisons(registre):
    """Refuse les références inconnues et les cycles, même sur un registre altéré."""
    par_id = {m.id: m for m in registre}
    for maison in registre:
        courant, vus = maison, set()
        while courant.suzerain is not None:
            if courant.id in vus or courant.suzerain not in par_id:
                raise PuissanceInvalide(f"maison {maison.id} ({maison.nom}), champ suzerain : inconnu ou cycle")
            vus.add(courant.id)
            courant = par_id[courant.suzerain]

def charger_registre_maisons(carte, puissances_path=None, capitales_path=None, seigneuries_path=None):
    """Charge aussi la maison du joueur ; les chemins permettent les contre-épreuves."""
    puissances_path = Path(puissances_path) if puissances_path is not None else _CHEMIN_TABLE
    capitales_path = Path(capitales_path) if capitales_path is not None else _CHEMIN_TABLE.with_name("capitales-1400.json")
    seigneuries_path = Path(seigneuries_path) if seigneuries_path is not None else _CHEMIN_TABLE.with_name("seigneuries-1400.json")
    try:
        table, maisons = charger_table(puissances_path), charger_maisons(puissances_path)
        capitales = charger_capitales(capitales_path, maisons)
        seigneuries = charger_seigneuries(seigneuries_path, table)
        ancres_brutes = {a["id"]: a for a in json.loads(puissances_path.read_text(encoding="utf-8"))["ancres"]}
    except (OSError, json.JSONDecodeError) as erreur:
        raise PuissanceInvalide(f"table source absente ou illisible : {erreur}") from erreur
    for cid in sorted(carte):
        if carte[cid].get("geometry") is None:
            raise PuissanceInvalide(f"cellule {cid}, champ geometry : géométrie absente")
    racines = {p: f"grande-{m}" if m is not None else f"institution-{p}" for p, m in maisons.par_puissance.items()}
    noms = {m.id: m.nom for m in maisons.maisons}
    registre = []
    def ajouter(identifiant, nom, sorte, suzerain, siege, cid, raison=None):
        registre.append(MaisonDuMonde(identifiant, nom, sorte, suzerain, siege, cid, 0 if cid is not None else None, raison))
    for c in capitales:
        ajouter(f"grande-{c.maison}", noms[c.maison], "grande maison", None,
                c.nom, cellule_de_capitale(c, carte), c.hors_carte)
    for p in table.puissances:
        if maisons.par_puissance[p.id] is None:
            ancre = min((a for a in table.ancres if a.puissance == p.id), key=lambda a: a.id)
            brute = ancres_brutes[ancre.id]
            raison = _texte(brute["hors_carte"], "institution", p.id, "hors_carte") if "hors_carte" in brute else None
            c = Capitale(p.id, ancre.nom, ancre.lat, ancre.lon, ancre.source, raison)
            ajouter(racines[p.id], p.nom, "institution", None,
                    c.nom, cellule_de_capitale(c, carte), raison)
    for s in seigneuries:
        ajouter(identifiant_de_seigneurie(s.id), s.maison, "seigneurie", racines[s.suzerain],
                s.siege.nom, cellule_du_siege(s, carte))
    resultat = tuple(sorted(registre, key=lambda m: m.id))
    valider_registre_maisons(resultat)
    return resultat
