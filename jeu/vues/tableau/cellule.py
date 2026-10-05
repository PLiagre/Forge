"""Dessin des lieux photographiés : les nombres viennent du document seul."""

from __future__ import annotations

import json
import math
from html import escape

COLONNES = 1
LARGEUR_CARTE = 300
MARGE = 12
INTERLIGNE = 22
HAUTEUR_ENTETE = 52
TAILLE_TEXTE = 14


class LieuxIllisibles(ValueError):
    """La photographie ne porte pas des lieux lisibles."""


def cellule_du_document(document: dict, cell_id: int) -> dict:
    for cell in document["cells"]:
        if int(cell["cell_id"]) == cell_id:
            return cell
    raise KeyError(f"cellule {cell_id} absente de la photographie")


def lire_lieux(cellule: dict) -> list | None:
    if "lieux" not in cellule or cellule["lieux"] == []:
        return None
    lieux = cellule["lieux"]

    def refuser(raison: str) -> None:
        raise LieuxIllisibles(f"cellule {cellule['cell_id']} : {raison}")

    def nombre(valeur) -> bool:
        return type(valeur) in (int, float) and (
            type(valeur) is int or math.isfinite(valeur)
        )

    if not isinstance(lieux, list):
        refuser("lieux n'est pas une liste")
    for rang, lieu in enumerate(lieux):
        if not isinstance(lieu, dict):
            refuser("lieu n'est pas un objet")
        if type(lieu.get("rang")) is not int or lieu["rang"] != rang:
            refuser("rangs hors de l'ordre 0 … n − 1")
        population = lieu.get("population")
        if type(population) is not int or population < 0:
            refuser(f"population illisible au rang {rang}")
        surface = lieu.get("surface_km2")
        if not nombre(surface) or surface <= 0:
            refuser(f"surface illisible au rang {rang}")
        stocks = lieu.get("stocks")
        if not isinstance(stocks, dict):
            refuser(f"stocks n'est pas un objet au rang {rang}")
        for nom, kg in stocks.items():
            if not isinstance(nom, str) or not nombre(kg) or kg < 0:
                refuser(f"stock illisible au rang {rang}")
    return lieux


def formater(valeur: int | float) -> str:
    if type(valeur) is int:
        return f"{valeur:,d}".replace(",", " ")
    return f"{valeur:,.2f}".rstrip("0").rstrip(".").replace(",", " ").replace(".", ",")


def render_cellule_svg(document: dict, cell_id: int) -> str:
    lieux = lire_lieux(cellule_du_document(document, cell_id))
    largeur = COLONNES * (LARGEUR_CARTE + MARGE) + MARGE
    cartes = []
    y = HAUTEUR_ENTETE
    if lieux:
        for debut in range(0, len(lieux), COLONNES):
            ligne = lieux[debut:debut + COLONNES]
            hauteur = MARGE * 2 + INTERLIGNE * (3 + max(len(l["stocks"]) for l in ligne))
            for colonne, lieu in enumerate(ligne):
                cartes.append((lieu, MARGE + colonne * (LARGEUR_CARTE + MARGE), y, hauteur))
            y += hauteur + MARGE
    else:
        y += INTERLIGNE + MARGE
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{largeur}" height="{y}" '
           f'viewBox="0 0 {largeur} {y}">',
           '<rect width="100%" height="100%" fill="#0e141b"/>',
           f'<g fill="#e7eef4" font-family="monospace" font-size="{TAILLE_TEXTE}">']

    def texte(x, y, contenu, attributs=""):
        ajuste = ''
        if len(contenu) * TAILLE_TEXTE * 0.6 > LARGEUR_CARTE - 2 * MARGE:
            ajuste = f' textLength="{LARGEUR_CARTE - 2 * MARGE}" lengthAdjust="spacingAndGlyphs"'
        return f'<text x="{x}" y="{y}"{ajuste}{attributs}>{escape(contenu)}</text>'

    def exact(valeur):
        return escape(json.dumps(valeur), quote=True)

    svg.append(texte(MARGE, 28, f"cellule {cell_id} — tick {document['tick']} graine {document['seed']}"))
    if lieux is None:
        svg.append(texte(MARGE, HAUTEUR_ENTETE, "lieux absents de la photographie"))
    for lieu, x, y, hauteur in cartes:
        rang = lieu["rang"]
        svg.append(f'<g id="lieu-{rang}" data-rang="{exact(rang)}" '
                   f'data-population="{exact(lieu["population"])}" '
                   f'data-surface-km2="{exact(lieu["surface_km2"])}">')
        fond, bord = ("#233b50", "#f0c14b") if rang == 0 else ("#151d27", "#2a3a4a")
        svg.append(f'<rect x="{x}" y="{y}" width="{LARGEUR_CARTE}" height="{hauteur}" '
                   f'rx="6" fill="{fond}" stroke="{bord}"/>')
        svg.append(texte(x + MARGE, y + INTERLIGNE, f"rang {rang}"))
        if rang == 0:
            svg.append(texte(x + LARGEUR_CARTE - 80, y + INTERLIGNE, "bourg"))
        svg.append(texte(x + MARGE, y + 2 * INTERLIGNE, f"{formater(lieu['surface_km2'])} km²"))
        svg.append(texte(x + MARGE, y + 3 * INTERLIGNE, f"{formater(lieu['population'])} habitants"))
        for numero, nom in enumerate(sorted(lieu["stocks"]), start=4):
            kg = lieu["stocks"][nom]
            svg.append(texte(x + MARGE, y + numero * INTERLIGNE,
                             f"{nom} : {formater(kg)} kg",
                             f' data-marchandise="{escape(nom, quote=True)}" data-kg="{exact(kg)}"'))
        svg.append('</g>')
    svg.append('</g></svg>')
    return '\n'.join(svg) + '\n'
