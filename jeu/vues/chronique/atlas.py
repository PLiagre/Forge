"""La planche : une chronique dessinee, en une page qui se suffit.

Ce module **lit** une chronique et rend du HTML. Il ne rejoue aucun tick,
n'agrege rien que la chronique ne porte deja, et ne choisit aucune
couleur : les couleurs vivent dans `chronique/da.json`, parce qu'une
direction artistique ecrite dans du code est une direction artistique que
le prochain moteur de rendu devra reecrire.

La geometrie n'est ecrite **qu'une fois**, dans les `<defs>` du SVG ;
tout le reste — la terre, le trait de cote, les hachures de relief, le
lavis de la donnee, les limites de province — la reference par `<use>`.
C'est la meme economie que celle de la chronique elle-meme, et c'est la
meme que fera Unity : un maillage charge une fois, un flux d'etats.

La page ne charge aucune bibliotheque. Elle demande trois fontes a
Google Fonts, et se rabat proprement sur les fontes du systeme si elles
n'arrivent pas ; `--sans-reseau` retire meme cette demande.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Sequence

from sim.constants import MARCHANDISE_NOURRITURE

DA_PATH = Path(__file__).with_name("da.json")

# Largeur de la planche, en unites SVG. Le viewBox s'y ajuste ; la page,
# elle, est fluide.
LARGEUR_PLANCHE = 1000.0

# Les quatre lectures que la planche sait dessiner. L'ordre est celui des
# onglets : ce qu'il y a (population), ce qui nourrit (subsistances), ce
# qui manque (disette, dette).
LECTURES = ("population", "nourriture", "faim", "dette")


class AtlasError(RuntimeError):
    """Refus de rendu : donnee absente, jamais devinee."""


def lire_da(chemin: Path | None = None) -> dict:
    """Charge la direction artistique. Aucune valeur par defaut en dur."""
    source = Path(chemin) if chemin else DA_PATH
    return json.loads(source.read_text(encoding="utf-8"))


def _anneaux(geometrie: dict) -> list[list[Sequence[float]]]:
    if geometrie["type"] == "Polygon":
        return list(geometrie["coordinates"])
    return [anneau for polygone in geometrie["coordinates"] for anneau in polygone]


def _cadre(cellules: Sequence[dict]) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for cellule in cellules:
        for anneau in _anneaux(cellule["geometry"]):
            for x, y in anneau:
                xs.append(float(x))
                ys.append(float(y))
    if not xs:
        raise AtlasError("aucune geometrie a dessiner")
    return min(xs), min(ys), max(xs), max(ys)


def _projeteur(cadre: tuple[float, float, float, float], largeur: float):
    """Metres EPSG:3035 vers unites de planche. Y descend, comme en SVG.

    Le facteur d'echelle est rendu avec la fonction : Unity a besoin du
    meme, et un facteur recalcule ailleurs est un second modele.
    """
    minx, miny, maxx, maxy = cadre
    etendue_x = max(maxx - minx, 1.0)
    etendue_y = max(maxy - miny, 1.0)
    echelle = largeur / etendue_x
    hauteur = etendue_y * echelle

    def projeter(x: float, y: float) -> tuple[float, float]:
        return (float(x) - minx) * echelle, (maxy - float(y)) * echelle

    return projeter, hauteur, echelle


def _chemin(cellule: dict, projeter) -> str:
    morceaux: list[str] = []
    for anneau in _anneaux(cellule["geometry"]):
        for rang, (x, y) in enumerate(anneau):
            px, py = projeter(x, y)
            morceaux.append(f"{'M' if rang == 0 else 'L'}{px:.1f},{py:.1f}")
        morceaux.append("Z")
    return "".join(morceaux)


def _valeur_nourriture(stocks: Any) -> float | None:
    """Le stock de nourriture d'une cellule, ou `None` s'il est absent.

    Un panier sans nourriture n'est pas un panier a zero (regle 8) : la
    planche le dessine « absent », elle ne le dessine pas vide.
    """
    if not isinstance(stocks, dict) or MARCHANDISE_NOURRITURE not in stocks:
        return None
    return float(stocks[MARCHANDISE_NOURRITURE])


def _sentinelle(valeur: Any) -> float | None:
    """Rend `None` pour la sentinelle « non calcule » (-1), la valeur sinon."""
    if valeur is None:
        return None
    nombre = float(valeur)
    return None if nombre < 0 else nombre


def lectures_par_image(chronique: dict) -> list[dict]:
    """Les quatre colonnes lisibles, et les totaux, image par image.

    Les totaux sont **derives** des colonnes de la chronique, jamais
    recopies d'un resume de `sim/` : deux chemins vers le meme nombre
    finissent par ne plus dire la meme chose.
    """
    images = []
    for image in chronique["images"]:
        colonnes = image["colonnes"]
        population = [int(v) for v in colonnes["population"]]
        nourriture = [_valeur_nourriture(s) for s in colonnes["stocks"]]
        faim = [_sentinelle(v) for v in colonnes["hunger_ticks"]]
        dette = [_sentinelle(v) for v in colonnes["food_deficit_kg"]]
        images.append(
            {
                "tick": image["tick"],
                "jour": image["jour"],
                "population": population,
                "nourriture": [None if v is None else round(v) for v in nourriture],
                "faim": [None if v is None else int(v) for v in faim],
                "dette": [None if v is None else round(v) for v in dette],
                "totaux": {
                    "population": sum(population),
                    "nourriture": round(sum(v for v in nourriture if v is not None)),
                    "disette": sum(1 for v in faim if v is not None and v > 0),
                    "dette": round(sum(v for v in dette if v is not None and v > 0)),
                },
            }
        )
    return images


def echelles(images: Sequence[dict]) -> dict[str, float | None]:
    """Le maximum de chaque lecture sur toute la chronique, ou `None`.

    Derive, et derive sur l'ensemble : une echelle recalculee image par
    image ferait paraitre identiques une cellule pleine et une cellule
    vide, et l'animation ne montrerait plus rien bouger.

    Une lecture sans aucune valeur positive rend `None`, et la planche le
    dit : sur une chronique de deux ticks, personne n'a encore de dette,
    et une dette nulle partout n'est pas une dette qu'on peut mettre a
    l'echelle. Rendre 0 la peindrait « au plus bas » comme si on l'avait
    mesuree — c'est exactement l'invention silencieuse que la regle 10
    interdit. Refuser la planche entiere serait l'autre exces : un
    controle trop grossier coute aussi cher qu'un controle laxiste
    (regle 6). Alors on refuse **cette lecture-la**, nommement.

    Si aucune lecture n'a de valeur, il n'y a rien a dessiner du tout, et
    la planche se refuse.
    """
    resultat: dict[str, float | None] = {}
    for lecture in LECTURES:
        valeurs = [
            float(v)
            for image in images
            for v in image[lecture]
            if v is not None and float(v) > 0
        ]
        resultat[lecture] = max(valeurs) if valeurs else None
    if all(valeur is None for valeur in resultat.values()):
        raise AtlasError(
            "aucune des lectures n'a de valeur positive sur toute la "
            "chronique : il n'y a rien a dessiner"
        )
    return resultat


def _defs_cellules(cellules: Sequence[dict], projeter) -> str:
    return "".join(
        f'<path id="c{cellule["cell_id"]}" d="{_chemin(cellule, projeter)}"/>'
        for cellule in cellules
    )


def _hachures(da: dict) -> str:
    """Les motifs de relief : chevrons, points, tirets. Graves, pas peints."""
    trait = da["papier"]["trait_pale"]
    motifs = [
        '<pattern id="h-points" width="9" height="9" patternUnits="userSpaceOnUse">'
        f'<circle cx="2" cy="2" r="0.75" fill="{trait}" opacity="0.55"/>'
        f'<circle cx="6.5" cy="6" r="0.75" fill="{trait}" opacity="0.55"/></pattern>',
        '<pattern id="h-chevrons" width="14" height="11" patternUnits="userSpaceOnUse">'
        f'<path d="M1,8 L4.5,2.5 L8,8" fill="none" stroke="{trait}" '
        'stroke-width="1.1" opacity="0.6"/>'
        f'<path d="M8,10.5 L11,6 L14,10.5" fill="none" stroke="{trait}" '
        'stroke-width="0.9" opacity="0.4"/></pattern>',
        '<pattern id="h-chevrons_serres" width="9" height="7" patternUnits="userSpaceOnUse">'
        f'<path d="M0.5,5.5 L3,1.5 L5.5,5.5" fill="none" stroke="{trait}" '
        'stroke-width="1.15" opacity="0.8"/>'
        f'<path d="M5,7 L7,4 L9,7" fill="none" stroke="{trait}" '
        'stroke-width="1" opacity="0.6"/></pattern>',
        '<pattern id="h-tirets" width="12" height="8" patternUnits="userSpaceOnUse">'
        f'<path d="M1,2.5 H6 M6.5,6 H11.5" stroke="{trait}" stroke-width="1" '
        'opacity="0.55" fill="none"/></pattern>',
    ]
    return "".join(motifs)


def _groupe_reliefs(cellules: Sequence[dict], da: dict) -> str:
    """Un groupe par classe de relief. Une classe inconnue est refusee."""
    par_classe: dict[str, list[int]] = {}
    for cellule in cellules:
        classe = cellule.get("relief")
        if classe not in da["reliefs"]:
            raise AtlasError(
                f"relief '{classe}' absent de la direction artistique "
                f"(cellule {cellule['cell_id']})"
            )
        par_classe.setdefault(classe, []).append(int(cellule["cell_id"]))
    fragments = []
    for classe, identifiants in sorted(par_classe.items()):
        reglage = da["reliefs"][classe]
        if reglage["hachure"] == "aucune":
            continue
        uses = "".join(f'<use href="#c{i}"/>' for i in identifiants)
        fragments.append(
            f'<g fill="url(#h-{reglage["hachure"]})" stroke="none">{uses}</g>'
        )
    return "".join(fragments)


def _provinces(cellules: Sequence[dict]) -> str:
    """Les limites de province, par masque : seul le contour de l'union sort.

    Les cellules ne partagent pas leurs sommets — on ne peut donc pas
    fabriquer le contour d'une province en annulant les aretes internes.
    Le masque le fait autrement : on cache l'interieur de la province, et
    il ne reste du trait que sa moitie exterieure. Le resultat est le
    contour de l'union, sans jamais toucher a la geometrie.
    """
    par_province: dict[int, list[int]] = {}
    noms: dict[int, str] = {}
    for cellule in cellules:
        province = cellule["province"]
        identifiant = int(province["id"])
        par_province.setdefault(identifiant, []).append(int(cellule["cell_id"]))
        noms[identifiant] = province["name"]
    masques = []
    traits = []
    for identifiant, cellules_de_la_province in sorted(par_province.items()):
        uses = "".join(f'<use href="#c{i}"/>' for i in cellules_de_la_province)
        masques.append(
            f'<mask id="m-p{identifiant}" maskUnits="userSpaceOnUse" '
            'x="-50" y="-50" width="200%" height="200%">'
            '<rect x="-50" y="-50" width="10000" height="10000" fill="#fff"/>'
            f'<g fill="#000" stroke="none">{uses}</g></mask>'
        )
        traits.append(
            f'<g mask="url(#m-p{identifiant})" fill="none">{uses}</g>'
        )
    return "".join(masques), "".join(traits)


def _foyers(cellules: Sequence[dict], projeter) -> str:
    cercles = []
    for cellule in cellules:
        centroide = cellule["centroid"]
        px, py = projeter(centroide["x_m"], centroide["y_m"])
        cercles.append(
            f'<circle id="f{cellule["cell_id"]}" cx="{px:.1f}" cy="{py:.1f}" r="0"/>'
        )
    return "".join(cercles)


def _an_de_tick(numero_tick: int) -> int:
    """Le rang de l'annee depuis le premier tick, derive de la base de temps.

    Le monde ne porte **pas** d'annee civile : il porte un jour dans
    l'annee. La planche compte donc des ans depuis le debut de la partie,
    et le dit ; elle n'ecrit pas « 1400 », qui n'est nulle part dans
    l'etat du monde (regle 10 : ce qui manque se declare, il ne se
    devine pas).
    """
    from sim.constants import CALENDAR_DAYS_PER_YEAR, TICK_DURATION_DAYS

    return (numero_tick * TICK_DURATION_DAYS) // CALENDAR_DAYS_PER_YEAR + 1


_ROMAINS = (
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
    (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
)


def _romain(nombre: int) -> str:
    reste = int(nombre)
    sortie = []
    for valeur, signe in _ROMAINS:
        while reste >= valeur:
            sortie.append(signe)
            reste -= valeur
    return "".join(sortie) or "0"


def _courbe(images: Sequence[dict], da: dict, largeur: float, hauteur: float) -> str:
    """Le rail chronologique : la population en aire, la disette en trait.

    Le rail n'est pas une decoration sous la carte — c'est la reglette
    elle-meme : on parcourt l'histoire en glissant le long de la courbe
    de la population. La forme de la courbe dit ou il faut regarder.
    """
    populations = [image["totaux"]["population"] for image in images]
    disettes = [image["totaux"]["disette"] for image in images]
    haut_population = max(populations) or 1
    haut_disette = max(disettes) or 1
    dernier = max(len(images) - 1, 1)

    def x_de(rang: int) -> float:
        return rang / dernier * largeur

    aire = [f"M0,{hauteur:.1f}"]
    for rang, valeur in enumerate(populations):
        y = hauteur - valeur / haut_population * hauteur
        aire.append(f"L{x_de(rang):.1f},{y:.1f}")
    aire.append(f"L{largeur:.1f},{hauteur:.1f}Z")

    trait = []
    for rang, valeur in enumerate(disettes):
        y = hauteur - valeur / haut_disette * hauteur
        trait.append(f"{'M' if rang == 0 else 'L'}{x_de(rang):.1f},{y:.1f}")

    encre = da["papier"]["trait"]
    madder = da["couches"]["faim"]["lavis"][4]
    return (
        f'<path class="aire" d="{"".join(aire)}" fill="{encre}" opacity="0.13"/>'
        f'<path d="{"".join(aire)}" fill="none" stroke="{encre}" stroke-width="1.6"/>'
        f'<path d="{" ".join(trait)}" fill="none" stroke="{madder}" '
        'stroke-width="1.6" stroke-dasharray="4 3"/>'
        f'<line id="tete" x1="0" y1="0" x2="0" y2="{hauteur:.1f}" '
        f'stroke="{encre}" stroke-width="1.4"/>'
        f'<circle id="tete-point" cx="0" cy="0" r="4" fill="{encre}"/>'
    ), haut_population, haut_disette


def _legende_lavis(da: dict) -> str:
    blocs = []
    for lecture in LECTURES:
        reglage = da["couches"][lecture]
        cases = "".join(
            f'<span class="case" style="background:{teinte}"></span>'
            for teinte in reglage["lavis"]
        )
        blocs.append(
            f'<div class="rampe{" active" if lecture == LECTURES[0] else ""}" '
            f'data-lecture="{lecture}">'
            f'<div class="cases">{cases}</div>'
            f'<div class="bornes"><span class="bas" data-lecture="{lecture}">0</span>'
            f'<span class="haut" data-lecture="{lecture}"></span></div></div>'
        )
    return "".join(blocs)


def _legende_reliefs(da: dict) -> str:
    lignes = []
    for classe, reglage in da["reliefs"].items():
        motif = (
            f'background:{reglage["teinte"]}'
            if reglage["hachure"] == "aucune"
            else f'background:{reglage["teinte"]}'
        )
        lignes.append(
            f'<li><svg class="vignette" viewBox="0 0 26 16" aria-hidden="true">'
            f'<rect width="26" height="16" fill="{reglage["teinte"]}"/>'
            + (
                ""
                if reglage["hachure"] == "aucune"
                else f'<rect width="26" height="16" fill="url(#h-{reglage["hachure"]})"/>'
            )
            + f'</svg><span>{classe.replace("_", " ")}</span></li>'
        )
    return "".join(lignes)


_FONTES = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    "family=Bodoni+Moda:opsz,wght@6..96,400;6..96,600&"
    "family=IBM+Plex+Sans+Condensed:wght@400;500;600&"
    "family=Spectral:ital,wght@0,300;0,400;1,300&display=swap\">"
)

_CSS = """
:root {
  --fond: %(fond)s;
  --planche: %(planche)s;
  --mer: %(mer)s;
  --trait: %(trait)s;
  --trait-pale: %(trait_pale)s;
  --filet: %(filet)s;
  --absent: %(absent)s;
  --madder: %(madder)s;
  --titre: "Bodoni Moda", "Didot", "Bodoni MT", Georgia, serif;
  --texte: "Spectral", "Iowan Old Style", Georgia, serif;
  --note: "IBM Plex Sans Condensed", "Avenir Next Condensed", "Roboto Condensed",
          system-ui, sans-serif;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--fond);
  color: var(--trait);
  font-family: var(--texte);
  font-size: 15px;
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}
.planche {
  max-width: 1400px;
  margin: 0 auto;
  padding: 30px 26px 40px;
  display: flex;
  flex-direction: column;
  gap: 22px;
}
.cartouche {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px 26px;
  border-bottom: 1.5px solid var(--trait);
  padding-bottom: 12px;
}
.cartouche h1 {
  font-family: var(--titre);
  font-weight: 400;
  font-size: clamp(30px, 4.4vw, 52px);
  letter-spacing: 0.005em;
  margin: 0;
  line-height: 1;
  text-wrap: balance;
}
.eyebrow, .sous {
  font-family: var(--note);
  text-transform: uppercase;
  letter-spacing: 0.16em;
  font-size: 11px;
  color: var(--trait-pale);
  margin: 0;
}
.sous { letter-spacing: 0.1em; font-variant-numeric: tabular-nums; }
.corps {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 292px;
  gap: 26px;
  align-items: start;
}
.carte {
  margin: 0;
  background: var(--mer);
  border: 1px solid var(--filet);
  overflow: hidden;
}
.carte svg { display: block; width: 100%%; height: auto; }
.marge { display: flex; flex-direction: column; gap: 20px; }
.date {
  border: 1.5px solid var(--trait);
  padding: 12px 14px 10px;
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}
.date .an {
  font-family: var(--titre);
  font-size: 30px;
  line-height: 1;
}
.date .jour {
  font-family: var(--note);
  text-transform: uppercase;
  letter-spacing: 0.14em;
  font-size: 11px;
  color: var(--trait-pale);
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.onglets { display: grid; grid-template-columns: 1fr 1fr; gap: 0; }
.onglets button {
  font-family: var(--note);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-size: 11px;
  padding: 9px 6px;
  background: transparent;
  color: var(--trait-pale);
  border: 1px solid var(--filet);
  margin: -0.5px 0 0 -0.5px;
  cursor: pointer;
}
.onglets button:hover:not(:disabled) { color: var(--trait); }
.onglets button:disabled { opacity: 0.42; cursor: not-allowed; }
.onglets button[aria-pressed="true"] {
  background: var(--trait);
  color: var(--planche);
  border-color: var(--trait);
}
.onglets button:focus-visible { outline: 2px solid var(--madder); outline-offset: 1px; }
.releves { list-style: none; margin: 0; padding: 0; }
.releves li {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  padding: 7px 0;
  border-bottom: 1px solid var(--filet);
}
.releves li:first-child { border-top: 1px solid var(--filet); }
.releves .quoi {
  font-family: var(--note);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-size: 10.5px;
  color: var(--trait-pale);
}
.releves .combien {
  font-family: var(--titre);
  font-size: 19px;
  font-variant-numeric: tabular-nums;
}
.releves li.alerte .combien { color: var(--madder); }
.bloc-titre {
  font-family: var(--note);
  text-transform: uppercase;
  letter-spacing: 0.16em;
  font-size: 10px;
  color: var(--trait-pale);
  margin: 0 0 7px;
}
.rampe { display: none; }
.rampe.active { display: block; }
.cases { display: flex; height: 13px; }
.case { flex: 1; }
.bornes {
  display: flex;
  justify-content: space-between;
  font-family: var(--note);
  font-size: 10px;
  color: var(--trait-pale);
  padding-top: 3px;
  font-variant-numeric: tabular-nums;
}
.reliefs { list-style: none; margin: 0; padding: 0; columns: 2; column-gap: 12px; }
.reliefs li {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: var(--note);
  font-size: 10.5px;
  color: var(--trait-pale);
  padding: 2px 0;
  break-inside: avoid;
}
.vignette { width: 22px; height: 13px; border: 0.5px solid var(--filet); flex: none; }
.rail { border-top: 1.5px solid var(--trait); padding-top: 14px; }
.rail-tete {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 6px;
}
.rail-tete p { margin: 0; }
.courbe-boite { position: relative; cursor: ew-resize; }
.courbe-boite svg { display: block; width: 100%%; height: 92px; }
.axe {
  display: flex;
  justify-content: space-between;
  font-family: var(--note);
  font-size: 10px;
  color: var(--trait-pale);
  letter-spacing: 0.08em;
  font-variant-numeric: tabular-nums;
  padding-top: 4px;
  border-top: 1px solid var(--filet);
}
.commandes { display: flex; align-items: center; gap: 14px; margin-top: 12px; }
.commandes button {
  font-family: var(--note);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 11px;
  padding: 8px 18px;
  background: var(--trait);
  color: var(--planche);
  border: 1px solid var(--trait);
  cursor: pointer;
  min-width: 104px;
}
.commandes button:focus-visible { outline: 2px solid var(--madder); outline-offset: 2px; }
.commandes input[type="range"] { flex: 1; accent-color: %(trait)s; min-width: 120px; }
.pied {
  font-family: var(--note);
  font-size: 10.5px;
  color: var(--trait-pale);
  line-height: 1.6;
  border-top: 1px solid var(--filet);
  padding-top: 12px;
  max-width: 78ch;
}
.pied code { font-family: ui-monospace, "SFMono-Regular", Menlo, monospace; font-size: 10px; }
@media (max-width: 900px) {
  .corps { grid-template-columns: minmax(0, 1fr); }
  .reliefs { columns: 3; }
}
@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; }
}
"""


_JS = r"""
(function () {
  var C = CHRONIQUE;
  var ids = C.cellules;
  var lavis = document.getElementById("lavis");
  var groupeFoyers = document.getElementById("foyers");
  var taches = ids.map(function (id) { return document.getElementById("d" + id); });
  var disques = ids.map(function (id) { return document.getElementById("f" + id); });
  var lecture = "population";
  var rang = 0;
  var joue = false;
  var dernier = 0;
  var derniereImage = C.images.length - 1;
  var doux = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function teinte(nom, valeur) {
    var haut = C.echelles[nom];
    if (valeur === null || haut === null) { return C.absent; }
    var rampe = C.lavis[nom];
    var t = haut > 0 ? valeur / haut : 0;
    if (C.modes[nom] === "racine") { t = Math.sqrt(t); }
    var i = Math.floor(t * rampe.length);
    if (i >= rampe.length) { i = rampe.length - 1; }
    if (i < 0) { i = 0; }
    return rampe[i];
  }

  function nombre(valeur) { return valeur.toLocaleString("fr-FR"); }

  function compact(valeur) {
    if (valeur >= 1e9) { return (valeur / 1e9).toFixed(2) + " Md"; }
    if (valeur >= 1e6) { return (valeur / 1e6).toFixed(1) + " M"; }
    if (valeur >= 1e3) { return (valeur / 1e3).toFixed(0) + " k"; }
    return nombre(valeur);
  }

  function bornes() {
    var elements = document.querySelectorAll(".haut");
    for (var i = 0; i < elements.length; i++) {
      var nom = elements[i].getAttribute("data-lecture");
      var haut = C.echelles[nom];
      var bas = document.querySelector('.bas[data-lecture="' + nom + '"]');
      if (haut === null) {
        elements[i].textContent = "jamais mesuree sur cette chronique";
        bas.textContent = "";
      } else {
        elements[i].textContent = compact(haut) + " " + C.unites[nom];
      }
    }
    var boutons = document.querySelectorAll(".onglets button");
    for (var j = 0; j < boutons.length; j++) {
      var lu = boutons[j].getAttribute("data-lecture");
      if (C.echelles[lu] === null) {
        boutons[j].disabled = true;
        boutons[j].title = "aucune valeur sur cette chronique";
      }
    }
  }

  function peindre(index) {
    var image = C.images[index];
    var valeurs = image[lecture];
    var populations = image.population;
    groupeFoyers.setAttribute("opacity", lecture === "population" ? "0" : C.foyerOpacite);
    for (var i = 0; i < taches.length; i++) {
      taches[i].setAttribute("fill", teinte(lecture, valeurs[i]));
      var r = C.rayonMax * Math.sqrt(populations[i] / C.popMax);
      disques[i].setAttribute("r", r.toFixed(2));
    }
    document.getElementById("an").textContent = "AN " + image.an;
    document.getElementById("jour").innerHTML =
      "jour " + image.jour + "<br>tick " + image.tick;
    document.getElementById("v-population").textContent = nombre(image.totaux.population);
    document.getElementById("v-nourriture").textContent = compact(image.totaux.nourriture) + " kg";
    document.getElementById("v-disette").textContent =
      nombre(image.totaux.disette) + " / " + C.cellules.length;
    document.getElementById("v-dette").textContent = compact(image.totaux.dette) + " kg";
    document.getElementById("l-disette").classList.toggle("alerte", image.totaux.disette > 0);
    document.getElementById("l-dette").classList.toggle("alerte", image.totaux.dette > 0);
    var x = derniereImage > 0 ? (index / derniereImage) * C.railLargeur : 0;
    var y = C.railHauteur - (image.totaux.population / C.railHautPopulation) * C.railHauteur;
    var tete = document.getElementById("tete");
    tete.setAttribute("x1", x.toFixed(1));
    tete.setAttribute("x2", x.toFixed(1));
    var point = document.getElementById("tete-point");
    point.setAttribute("cx", x.toFixed(1));
    point.setAttribute("cy", y.toFixed(1));
    document.getElementById("reglette").value = index;
  }

  function aller(index) {
    rang = Math.max(0, Math.min(derniereImage, index));
    peindre(rang);
  }

  function boucle(horodatage) {
    if (!joue) { return; }
    if (horodatage - dernier > C.msParImage) {
      dernier = horodatage;
      aller(rang >= derniereImage ? 0 : rang + 1);
    }
    window.requestAnimationFrame(boucle);
  }

  function basculer() {
    joue = !joue;
    document.getElementById("jouer").textContent = joue ? "Arreter" : "Derouler";
    if (joue) { dernier = 0; window.requestAnimationFrame(boucle); }
  }

  var onglets = document.querySelectorAll(".onglets button");

  function choisir(nom) {
    lecture = nom;
    for (var j = 0; j < onglets.length; j++) {
      onglets[j].setAttribute(
        "aria-pressed",
        onglets[j].getAttribute("data-lecture") === lecture ? "true" : "false"
      );
    }
    var rampes = document.querySelectorAll(".rampe");
    for (var k = 0; k < rampes.length; k++) {
      rampes[k].classList.toggle(
        "active", rampes[k].getAttribute("data-lecture") === lecture
      );
    }
    document.getElementById("titre-lecture").textContent = C.titres[lecture];
    peindre(rang);
  }

  for (var i = 0; i < onglets.length; i++) {
    onglets[i].addEventListener("click", function (evenement) {
      choisir(evenement.currentTarget.getAttribute("data-lecture"));
    });
  }

  document.getElementById("jouer").addEventListener("click", basculer);
  document.getElementById("reglette").addEventListener("input", function (evenement) {
    joue = false;
    document.getElementById("jouer").textContent = "Derouler";
    aller(parseInt(evenement.target.value, 10));
  });

  var boite = document.getElementById("courbe-boite");
  function pointer(evenement) {
    var rect = boite.getBoundingClientRect();
    var part = (evenement.clientX - rect.left) / rect.width;
    aller(Math.round(part * derniereImage));
  }
  boite.addEventListener("pointerdown", function (evenement) {
    joue = false;
    document.getElementById("jouer").textContent = "Derouler";
    boite.setPointerCapture(evenement.pointerId);
    pointer(evenement);
  });
  boite.addEventListener("pointermove", function (evenement) {
    if (evenement.buttons) { pointer(evenement); }
  });

  document.addEventListener("keydown", function (evenement) {
    if (evenement.key === "ArrowRight") { joue = false; aller(rang + 1); }
    if (evenement.key === "ArrowLeft") { joue = false; aller(rang - 1); }
    if (evenement.key === " ") { evenement.preventDefault(); basculer(); }
  });

  bornes();
  var demande = new URLSearchParams(window.location.search).get("image");
  var depart = demande === null ? 0 : parseInt(demande, 10);
  if (isNaN(depart)) { depart = 0; }
  var lu = new URLSearchParams(window.location.search).get("lecture");
  aller(depart);
  if (lu !== null && C.lavis[lu] !== undefined) { choisir(lu); }
  if (!doux && demande === null) { basculer(); }
})();
"""


_RAIL_LARGEUR = 1000.0
_RAIL_HAUTEUR = 92.0

# Cadence de deroulement, en millisecondes par image. Une chronique est
# lue, pas subie : sept images par seconde laissent voir une vague de
# disette traverser la carte sans qu'on ait a la rembobiner.
MS_PAR_IMAGE = 140


def rendre(
    chronique: dict,
    da: dict | None = None,
    *,
    sans_reseau: bool = False,
    cadence_ms: int = MS_PAR_IMAGE,
) -> str:
    """Rend la planche complete, en une page HTML autonome."""
    da = da or lire_da()
    decor = chronique["decor"]
    cellules = decor["cellules"]
    images = lectures_par_image(chronique)
    for image in images:
        image["an"] = _romain(_an_de_tick(image["tick"]))
    hauts = echelles(images)

    cadre = _cadre(cellules)
    projeter, hauteur, _echelle_m = _projeteur(cadre, LARGEUR_PLANCHE)
    identifiants = [int(cellule["cell_id"]) for cellule in cellules]
    uses_terre = "".join(f'<use href="#c{i}"/>' for i in identifiants)
    masques_provinces, traits_provinces = _provinces(cellules)
    papier = da["papier"]

    defs = (
        "<defs>"
        + _defs_cellules(cellules, projeter)
        + _hachures(da)
        + f'<g id="terre-traits">{uses_terre}</g>'
        + '<mask id="m-terre" maskUnits="userSpaceOnUse" x="0" y="0" '
        f'width="{LARGEUR_PLANCHE:.0f}" height="{hauteur:.0f}">'
        f'<rect width="{LARGEUR_PLANCHE:.0f}" height="{hauteur:.0f}" fill="#fff"/>'
        f'<g fill="#000" stroke="none">{uses_terre}</g></mask>'
        + masques_provinces
        + "</defs>"
    )

    cote = (
        f'<g mask="url(#m-terre)" fill="none" stroke="{papier["trait"]}" '
        'stroke-linejoin="round" stroke-linecap="round">'
        '<use href="#terre-traits" stroke-width="15" opacity="0.05"/>'
        '<use href="#terre-traits" stroke-width="9" opacity="0.07"/>'
        '<use href="#terre-traits" stroke-width="4.5" opacity="0.10"/>'
        '<use href="#terre-traits" stroke-width="1.8" opacity="0.55"/></g>'
    )
    lavis = "".join(
        f'<use id="d{i}" href="#c{i}"/>' for i in identifiants
    )
    foyers = da["foyers"]
    svg_carte = (
        f'<svg viewBox="0 0 {LARGEUR_PLANCHE:.0f} {hauteur:.0f}" '
        'role="img" aria-label="Carte du monde simule, cellule par cellule">'
        + defs
        + f'<rect width="{LARGEUR_PLANCHE:.0f}" height="{hauteur:.0f}" '
        f'fill="{papier["mer"]}"/>'
        + cote
        + f'<g fill="{papier["planche"]}" stroke="none">'
        '<use href="#terre-traits"/></g>'
        + f"<g>{_groupe_reliefs(cellules, da)}</g>"
        + f'<g id="lavis" stroke="none" opacity="0.85">{lavis}</g>'
        + f'<g fill="none" stroke="{papier["trait"]}" stroke-width="0.3" '
        'opacity="0.3"><use href="#terre-traits"/></g>'
        + f'<g stroke="{papier["trait"]}" stroke-width="2.4" opacity="0.8" '
        'stroke-linejoin="round" '
        f'fill="none">{traits_provinces}</g>'
        + f'<g id="foyers" fill="{foyers["remplissage"]}" '
        f'opacity="{foyers["opacite"]}">{_foyers(cellules, projeter)}</g>'
        + "</svg>"
    )

    courbe, haut_population, _haut_disette = _courbe(
        images, da, _RAIL_LARGEUR, _RAIL_HAUTEUR
    )
    svg_rail = (
        f'<svg viewBox="0 0 {_RAIL_LARGEUR:.0f} {_RAIL_HAUTEUR:.0f}" '
        'preserveAspectRatio="none" role="img" '
        'aria-label="Courbe de la population totale au fil des ticks">'
        + courbe
        + "</svg>"
    )

    charge = {
        "cellules": identifiants,
        "images": images,
        "echelles": hauts,
        "lavis": {nom: da["couches"][nom]["lavis"] for nom in LECTURES},
        "modes": {nom: da["couches"][nom]["echelle"] for nom in LECTURES},
        "titres": {nom: da["couches"][nom]["titre"] for nom in LECTURES},
        "unites": {nom: da["couches"][nom]["unite"] for nom in LECTURES},
        "absent": papier["absent"],
        "popMax": max(
            max(image["population"]) for image in images
        ),
        "rayonMax": foyers["rayon_max_pour_mille_unites"],
        "foyerOpacite": foyers["opacite"],
        "railLargeur": _RAIL_LARGEUR,
        "railHauteur": _RAIL_HAUTEUR,
        "railHautPopulation": haut_population,
        "msParImage": int(cadence_ms),
    }

    onglets = "".join(
        f'<button type="button" data-lecture="{nom}" '
        f'aria-pressed="{"true" if nom == "population" else "false"}">'
        f'{da["couches"][nom]["titre"]}</button>'
        for nom in LECTURES
    )
    css = _CSS % {
        "fond": papier["fond"],
        "planche": papier["planche"],
        "mer": papier["mer"],
        "trait": papier["trait"],
        "trait_pale": papier["trait_pale"],
        "filet": papier["filet"],
        "absent": papier["absent"],
        "madder": da["couches"]["faim"]["lavis"][4],
    }
    provinces = len({int(c["province"]["id"]) for c in cellules})
    premier, dernier = images[0], images[-1]

    page = _PAGE
    page = page.replace("__FONTES__", "" if sans_reseau else _FONTES)
    page = page.replace("__CSS__", css)
    page = page.replace("__CARTE__", svg_carte)
    page = page.replace("__RAIL__", svg_rail)
    page = page.replace("__ONGLETS__", onglets)
    page = page.replace("__RAMPES__", _legende_lavis(da))
    page = page.replace("__RELIEFS__", _legende_reliefs(da))
    page = page.replace("__NB_IMAGES__", str(len(images) - 1))
    page = page.replace("__CELLULES__", str(len(cellules)))
    page = page.replace("__PROVINCES__", str(provinces))
    page = page.replace("__GRAINE__", str(chronique["seed"]))
    page = page.replace("__PAS__", str(chronique["pas"]))
    page = page.replace("__TICK_FIN__", str(dernier["tick"]))
    page = page.replace("__IMAGES__", str(len(images)))
    page = page.replace("__CARTE_VERSION__", str(decor["carte"]["version"]))
    page = page.replace("__SCHEMA__", str(decor["schema_version"]))
    page = page.replace(
        "__DEBUT__", f'an {premier["an"]}, jour {premier["jour"]}'
    )
    page = page.replace("__FIN__", f'an {dernier["an"]}, jour {dernier["jour"]}')
    page = page.replace(
        "__DONNEES__",
        json.dumps(charge, ensure_ascii=False, separators=(",", ":")),
    )
    page = page.replace("__JS__", _JS)
    return page


_PAGE = """<title>Chronique du monde</title>
__FONTES__
<style>__CSS__</style>
<main class="planche">
  <header class="cartouche">
    <div>
      <p class="eyebrow">ForgeHistory &middot; moteur de simulation historique</p>
      <h1>Chronique du monde</h1>
    </div>
    <p class="sous">
      graine __GRAINE__ &middot; __CELLULES__ cellules &middot; __PROVINCES__ provinces
      &middot; __IMAGES__ images &middot; EPSG:3035
    </p>
  </header>

  <div class="corps">
    <figure class="carte">__CARTE__</figure>

    <aside class="marge">
      <div class="date">
        <span class="an" id="an">AN I</span>
        <span class="jour" id="jour">jour 0<br>tick 0</span>
      </div>

      <ul class="releves">
        <li><span class="quoi">Population</span>
            <span class="combien" id="v-population">&mdash;</span></li>
        <li><span class="quoi">Subsistances</span>
            <span class="combien" id="v-nourriture">&mdash;</span></li>
        <li id="l-disette"><span class="quoi">Cellules en disette</span>
            <span class="combien" id="v-disette">&mdash;</span></li>
        <li id="l-dette"><span class="quoi">Dette alimentaire</span>
            <span class="combien" id="v-dette">&mdash;</span></li>
      </ul>

      <div>
        <p class="bloc-titre">Ce que la carte montre</p>
        <nav class="onglets">__ONGLETS__</nav>
      </div>

      <div>
        <p class="bloc-titre" id="titre-lecture">Population</p>
        __RAMPES__
      </div>

      <div>
        <p class="bloc-titre">Relief</p>
        <ul class="reliefs">__RELIEFS__</ul>
      </div>
    </aside>
  </div>

  <section class="rail">
    <div class="rail-tete">
      <p class="bloc-titre">
        Population totale (aire) &middot; cellules en disette (trait rouge)
      </p>
      <p class="bloc-titre">Glisser sur la courbe pour parcourir</p>
    </div>
    <div class="courbe-boite" id="courbe-boite">__RAIL__</div>
    <div class="axe"><span>__DEBUT__</span><span>__FIN__</span></div>
    <div class="commandes">
      <button type="button" id="jouer">Derouler</button>
      <input type="range" id="reglette" min="0" max="__NB_IMAGES__" value="0"
             step="1" aria-label="Instant de la chronique">
    </div>
  </section>

  <p class="pied">
    Chronique deroulee par <code>python3 -m chronique</code> sur __TICK_FIN__ ticks,
    une image tous les __PAS__ ticks, carte <code>__CARTE_VERSION__</code>,
    schema de photographie <code>__SCHEMA__</code>. Cette page ne simule rien :
    elle lit un decor ecrit une fois et une colonne de valeurs par instant.
    Le monde ne porte pas d'annee civile &mdash; il porte un jour dans l'annee ;
    l'an compte donc depuis le premier tick. Les disques disent la population
    d'une cellule, pas un bourg : le bourg est une agregation derivee que la
    photographie ne porte pas encore.
  </p>
</main>
<script>const CHRONIQUE = __DONNEES__;__JS__</script>
"""
