"""Lecture d'un style architectural et derivation du plan d'un batiment.

Ce module ne depend ni de Blender ni d'Unity : il transforme un style
(`AssetFactory/Styles/<id>.json`) et le programme d'une famille du catalogue en
un plan geometrique deterministe. Les generateurs Blender consomment ce plan ;
les tests le verifient sans Blender.

Le catalogue decrit le programme (fonction, systeme de mur, marqueurs, graine,
emprise de base). Le style decrit le regard. Aucune valeur de regard n'est
ecrite ici : tout nombre vient du fichier de style.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field, replace
from pathlib import Path


# Vocabulaire : le style declare *quelles* formes existent et avec quel poids,
# le code sait *comment* chacune se construit. Une forme inconnue est une
# erreur, jamais un silence.
LEVEL_STOREYS = {"one": 1.0, "one_and_half": 1.5, "two": 2.0, "three": 3.0}
FOOTPRINT_FORMS = ("rectangle", "l_shape", "rectangle_lean_to")
ROOF_FORMS = ("gable", "hipped", "gable_dormer")
RIDGE_AXES = ("long", "short")
EAVE_STRIP_MODES = ("alpha_clip",)

# Vocabulaire du schema de construction. Le style dit *quels* schemas existent
# et ce que chacun fixe ; le code sait *comment* chaque terme se construit.
SCHEME_BASES = ("plinth", "stone_storey", "battered_stone")
STOREY_BASES = ("stone_storey", "battered_stone")
SCHEME_JETTIES = ("none", "first_floor", "each_floor")
ROOF_COMPOSITIONS = ("simple", "dormer", "cross_gable", "cross_gable_dormer")
EDGE_TRIMS = ("none", "barge_boards", "barge_finials", "purlin_ends")
# Ce que le batiment presente a la rue -- et donc a la camera de revue.
# C'est la difference de nature la plus forte entre deux maisons
# medievales : un pignon presente un triangle, un gouttereau une bande
# horizontale. Elle etait tiree au hasard par roof.ridge_axis.
STREET_FACES = ("gable", "eave")
APPENDAGES = ("porch", "lean_to", "stair", "gallery", "chimney_stack",
              "roof_lantern", "hanging_sign")
# Les quatre faces d'un niveau. Une facade aveugle n'existe pas : trois faces
# sur quatre ne portaient aucune ouverture, ce qui se voyait immediatement.
FACES = ("front", "back", "left", "right")


class StyleError(RuntimeError):
    """Style incoherent avec le vocabulaire des generateurs."""


def load_style(project_root: Path, style_id: str) -> dict:
    path = Path(project_root) / "AssetFactory" / "Styles" / f"{style_id}.json"
    if not path.is_file():
        raise StyleError(f"Style absent : {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _forms(style: dict, *path: str) -> list[dict]:
    node: object = style
    for key in path:
        if not isinstance(node, dict) or key not in node:
            raise StyleError("Cle de style absente : " + ".".join(path))
        node = node[key]
    if not isinstance(node, list) or not node:
        raise StyleError("Liste ponderee vide : " + ".".join(path))
    return node


def _known(identifiers: list[str], vocabulary: tuple[str, ...], label: str) -> None:
    unknown = [item for item in identifiers if item not in vocabulary]
    if unknown:
        raise StyleError(f"{label} hors vocabulaire : {', '.join(sorted(unknown))}")


def weighted_pick(rng: random.Random, forms: list[dict]) -> str:
    total = sum(float(form["weight"]) for form in forms)
    target = rng.random() * total
    cursor = 0.0
    for form in forms:
        cursor += float(form["weight"])
        if target < cursor:
            return str(form["id"])
    return str(forms[-1]["id"])


def stratified_picks(rng: random.Random, forms: list[dict], count: int) -> list[str]:
    """Tirer `count` formes en epuisant le pool avant de le reconstituer.

    Deux variantes d'une meme famille ne peuvent donc pas recevoir la meme
    emprise tant que le style en propose assez : la distinction de silhouette
    vient de la grammaire, pas d'un jitter sous-metrique.
    """
    picks: list[str] = []
    pool: list[dict] = []
    for _ in range(count):
        if not pool:
            pool = [dict(form) for form in forms]
        chosen = weighted_pick(rng, pool)
        pool = [form for form in pool if form["id"] != chosen]
        picks.append(chosen)
    return picks


def storey_height(style: dict, wall_height_m: float) -> float:
    """Deriver la hauteur d'un niveau de la moyenne ponderee du style.

    Le catalogue ne donne qu'une hauteur de mur ; le style dit combien de
    niveaux sont possibles et a quelle frequence. La hauteur d'etage est donc
    la hauteur du catalogue divisee par le nombre moyen de niveaux.
    """
    forms = _forms(style, "levels", "forms")
    _known([str(form["id"]) for form in forms], tuple(LEVEL_STOREYS), "levels.forms")
    weight = sum(float(form["weight"]) for form in forms)
    mean = sum(LEVEL_STOREYS[str(form["id"])] * float(form["weight"]) for form in forms) / weight
    return wall_height_m / mean


@dataclass(frozen=True)
class Storey:
    """Un niveau de la coque, avec son emprise propre.

    L'encorbellement fait deborder un niveau sur celui du dessous : chaque
    niveau porte donc son rectangle, et non un decalage par rapport a une
    emprise unique. C'est aussi ce qui permet a un rez-de-chaussee en pierre
    d'etre un vrai niveau et non un soubassement epaissi.
    """

    kind: str            # "stone" ou "wall"
    band: str            # bande de trim de ce niveau
    bottom: float
    height: float
    x0: float
    x1: float
    y0: float
    y1: float
    # Une jupe de base fruitee est une assise de modelisation, pas un niveau
    # habitable. Sans cette distinction les ouvertures la traitaient comme un
    # etage : voir `_openings`.
    role: str = "storey"

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def depth(self) -> float:
        return self.y1 - self.y0

    @property
    def centre(self) -> tuple[float, float]:
        return ((self.x0 + self.x1) * 0.5, (self.y0 + self.y1) * 0.5)

    @property
    def top(self) -> float:
        return self.bottom + self.height


@dataclass(frozen=True)
class RoofFrame:
    """L'enveloppe de toiture, derivee du niveau qu'elle couvre.

    Un batiment est un chemin de charge : le niveau du haut porte la sabliere,
    la sabliere porte les chevrons, les chevrons portent la couverture, et le
    pignon remplit exactement le triangle entre la sabliere et les chevrons.

    Tout ce qui est au-dessus du mur lit cette enveloppe et rien d'autre.
    Recalculer chacun depuis l'emprise nominale du catalogue les faisait diverger
    des que le niveau du haut ne coincidait plus avec elle : sur la maison de
    ville, encorbellee, la charpente etait posee sur une emprise 2,05 m plus
    etroite que le mur qu'elle devait couvrir, et decalee de 0,51 m.
    """

    span_axis: str       # axe le long duquel la pente descend
    x0: float
    x1: float
    y0: float
    y1: float
    eave_z: float        # dessus de la sabliere : depart des chevrons
    rise: float
    overhang: float
    pitch_deg: float
    plate: float
    ridge_beam: float
    rafter: float
    rafter_spacing: float
    rafter_depth: float

    @property
    def centre(self) -> tuple[float, float]:
        return ((self.x0 + self.x1) * 0.5, (self.y0 + self.y1) * 0.5)

    @property
    def span(self) -> float:
        """Portee : la dimension que la pente traverse."""
        return (self.x1 - self.x0) if self.span_axis == "x" else (self.y1 - self.y0)

    @property
    def run(self) -> float:
        """Longueur : la dimension que le faitage suit."""
        return (self.y1 - self.y0) if self.span_axis == "x" else (self.x1 - self.x0)

    @property
    def half_span(self) -> float:
        return self.span * 0.5

    @property
    def half_run(self) -> float:
        return self.run * 0.5

    @property
    def ridge_axis(self) -> str:
        """Axe que suit le faitage : c'est celui du plan de pignon.

        Le pignon ferme le toit a l'extremite du faitage : son plan est donc a
        coordonnee constante sur l'axe du faitage, jamais sur celui de la pente.
        Les deux etaient confondus, si bien que les deux triangles de charpente
        traversaient le toit a angle droit au lieu de le fermer.
        """
        return "y" if self.span_axis == "x" else "x"

    @property
    def ridge_z(self) -> float:
        return self.eave_z + self.rise

    @property
    def covering_lift(self) -> float:
        """Decalage vertical de la couverture posee sur les chevrons.

        Un plan incline deplace de `d` selon sa normale monte de `d / cos(pente)`
        a la verticale. C'est ce qui fait reposer la couverture sur la charpente
        au lieu de la confondre avec elle.
        """
        return self.rafter_depth / math.cos(math.radians(self.pitch_deg))

    def local(self, across: float, along: float, z: float) -> tuple[float, float, float]:
        """Repere du toit vers le monde : `across` traverse la portee."""
        cx, cy = self.centre
        if self.span_axis == "x":
            return (cx + across, cy + along, z)
        return (cx + along, cy + across, z)

    @property
    def reach(self) -> float:
        """Distance du faite a l'egout, mesuree a plat sur l'axe de portee."""
        return self.half_span + self.overhang

    def slope_z(self, across: float) -> float:
        """Hauteur du dessus des chevrons a cette abscisse de portee."""
        return self.eave_z + self.rise * max(0.0, 1.0 - abs(across) / self.reach)

    def slope_meets(self, z: float) -> float:
        """Abscisse de portee ou le rampant atteint la hauteur `z`.

        C'est la que meurt le faitage d'une toiture secondaire : une lucarne ou
        une croupe s'arrete ou son arete rencontre la pente principale, elle ne
        la traverse pas. Sans ce calcul, chaque toiture secondaire avait une
        profondeur arbitraire et coupait le versant.
        """
        if self.rise <= 0.0:
            return 0.0
        ratio = (z - self.eave_z) / self.rise
        return self.reach * max(0.0, min(1.0, 1.0 - ratio))

    def eave_side(self, facing: int) -> float:
        """Coordonnee de la ligne d'egout du cote demande.

        Les egouts sont sur l'axe de portee ; les pignons sur l'axe de faitage.
        Poser une lucarne sur un pignon la fait traverser le toit : elle se pose
        sur une pente.
        """
        if self.span_axis == "x":
            return self.x1 if facing > 0 else self.x0
        return self.y1 if facing > 0 else self.y0


@dataclass(frozen=True)
class Annex:
    """Un corps accole : un batiment complet, pas un volume rapporte.

    Il a sa propre pile de niveaux, sa propre enveloppe de toiture, sa propre
    face de rue et ses propres baies. La reference 1 n'est pas un corps augmente
    d'annexes, c'est plusieurs maisons mitoyennes de hauteurs differentes -- et
    un volume rapporte, mesure a l'appui, se noie dans la masse principale.
    """

    storeys: tuple[Storey, ...]
    frames: tuple[RoofFrame, ...]
    openings: tuple[Opening, ...]
    width: float
    depth: float
    span_axis: str
    rise: float
    half_span: float
    upper_band: str
    lower_band: str


@dataclass(frozen=True)
class Opening:
    """Une baie, sur la face d'un niveau.

    `along` est la coordonnee le long de la face, `plane` la coordonnee constante
    du plan de facade. Une ouverture qui ne connaissait que `center_x` ne pouvait
    vivre que sur un seul mur : c'est pourquoi trois facades sur quatre etaient
    aveugles.
    """

    kind: str
    face: str
    along: float
    sill_z: float
    width: float
    height: float
    shutters: bool
    plane: float = 0.0
    storey: int = 0

    @property
    def axis(self) -> str:
        """Axe perpendiculaire a la face : celui que le plan tient constant."""
        return "y" if self.face in ("front", "back") else "x"

    @property
    def outward(self) -> float:
        """Sens vers l'exterieur du mur."""
        return -1.0 if self.face in ("front", "left") else 1.0

    def position(self, depth: float, z: float) -> tuple[float, float, float]:
        """Point a `depth` metres vers l'exterieur du plan de facade."""
        offset = self.plane + self.outward * depth
        return (self.along, offset, z) if self.axis == "y" else (offset, self.along, z)

    def size(self, across: float, thickness: float) -> tuple[float, float, float]:
        """Dimensions d'une piece large de `across` et epaisse de `thickness`."""
        return ((across, thickness, 0.0) if self.axis == "y"
                else (thickness, across, 0.0))


@dataclass(frozen=True)
class Plan:
    asset_id: str
    seed: int
    function: str
    wall_system: str
    roof_system: str
    identity_markers: tuple[str, ...]
    palette_id: str
    palette: dict
    footprint_form: str
    level_form: str
    levels: float
    width: float
    depth: float
    storey_m: float
    wall_height: float
    wall_thickness: float
    corner_post: float
    wall_bevel: float
    foundation_height: float
    foundation_projection: float
    foundation_bevel: float
    roof_form: str
    ridge_axis: str
    pitch_deg: float
    overhang: float
    roof_thickness: float
    rise: float
    span_axis: str
    half_span: float
    eave_mode: str
    eave_depth: float
    eave_teeth_per_m: float
    reveal_depth: float
    openings: tuple[Opening, ...]
    scheme_id: str = ""
    scheme_rank: str = ""
    base_kind: str = "plinth"
    jetty: str = "none"
    jetty_overhang: float = 0.0
    roof_composition: str = "simple"
    roof_frame: RoofFrame | None = None
    roof_frame_high: RoofFrame | None = None
    annexes: tuple[Annex, ...] = ()
    body_role: str = "main"
    cross_gable: dict = field(default_factory=dict)
    dormers: tuple[dict, ...] = ()
    jetty_bracket: float = 0.0
    edge_trim: str = "none"
    edge_trim_spec: dict = field(default_factory=dict)
    appendages: dict = field(default_factory=dict)
    storeys: tuple[Storey, ...] = ()
    finish_id: str = ""
    upper_band: str = ""
    lower_band: str = ""
    wing: dict = field(default_factory=dict)
    lean_to: dict = field(default_factory=dict)
    window_mullion: float = 0.0
    window_frame_inset: float = 0.0
    budget_class: str = "standard"
    budget_lod: tuple[int, int, int] = (0, 0, 0)
    trim: dict = field(default_factory=dict)
    lod: dict = field(default_factory=dict)
    silhouette_gate: dict = field(default_factory=dict)
    review: dict = field(default_factory=dict)

    base_storey_height: float = 0.0

    @property
    def wall_top(self) -> float:
        return self.foundation_height + self.base_storey_height + self.wall_height

    @property
    def ridge_z(self) -> float:
        return self.wall_top + self.rise

    @property
    def top_storey(self) -> Storey:
        return self.storeys[-1]


def band_for(plan: Plan, role: str) -> str:
    """Bande de trim d'un role de surface, telle que le style la declare.

    La finition, quand elle est tiree, l'emporte sur la valeur par defaut du
    systeme de mur : c'est elle qui porte la variation de matiere d'une variante
    a l'autre, sans jamais toucher a la masse.
    """
    trim = plan.trim
    if role == "roof":
        mapping = trim["roof_system_map"]
        if plan.roof_system not in mapping:
            raise StyleError(f"Toiture sans bande : {plan.roof_system}")
        return str(mapping[plan.roof_system])
    if role == "body" and plan.upper_band:
        return plan.upper_band
    if role == "base" and plan.lower_band:
        return plan.lower_band
    mapping = trim["wall_system_map"]
    if plan.wall_system not in mapping:
        raise StyleError(f"Mur sans bande : {plan.wall_system}")
    entry = mapping[plan.wall_system]
    if role not in entry:
        raise StyleError(f"Role de mur absent : {plan.wall_system}.{role}")
    return str(entry[role])


def wall_base_height(plan: Plan) -> float:
    entry = plan.trim["wall_system_map"][plan.wall_system]
    return float(entry.get("base_height_m", 0.0))


def face_of(storey: Storey, face: str) -> tuple[str, float, float, float]:
    """(axe constant, plan, debut, fin) de la face d'un niveau."""
    if face == "front":
        return "y", storey.y0, storey.x0, storey.x1
    if face == "back":
        return "y", storey.y1, storey.x0, storey.x1
    if face == "left":
        return "x", storey.x0, storey.y0, storey.y1
    if face == "right":
        return "x", storey.x1, storey.y0, storey.y1
    raise StyleError("Face hors vocabulaire : " + str(face))


def _openings(style: dict, rng: random.Random, storeys: tuple[Storey, ...],
              wide_door: bool, with_windows: bool,
              forced_shutters: bool = False) -> tuple[Opening, ...]:
    """Diviser chaque face en travees, et poser une baie par travee.

    Une facade se lit par son rythme. Percer quelques trous sur un seul mur
    laissait trois faces sur quatre aveugles et une densite de 2,6 a 3,5 fenetres
    pour 100 m2, la ou les references en alignent trois a quatre par niveau et
    par face.

    Le rez en pierre recoit moins de baies que les etages : c'est ce que fait un
    soubassement porteur, et c'est ce que montrent les deux references.
    """
    opening = style["opening"]
    door_style, window_style = opening["door"], opening["window"]
    min_pier = float(opening["min_pier_m"])
    faces = tuple(opening.get("faces", FACES))
    bay_target = rng.uniform(*opening["bay_width_m"])
    stone_share = float(opening.get("stone_storey_bay_share", 1.0))

    door_width = rng.uniform(*door_style["wide_width_m" if wide_door else "width_m"])
    door_height = rng.uniform(*door_style["height_m"])
    minimum_door = float(door_style.get("min_height_m", 0.0))

    # La porte est au sol. Elle allait « dans le niveau le plus bas qui puisse
    # la contenir » : sous une base fruitee -- une jupe de 1,28 m puis un rez de
    # pierre de 1,76 -- aucune des deux assises n'atteignait les 2,0 m exiges et
    # la seule porte de la maison partait a 3,61 m, desservie par un escalier de
    # pierre massif de 5,70 m de long. Une maison a son entree au sol ; les
    # assises d'une base sont des boites de modelisation, pas des etages, et une
    # porte traverse celles qu'elle recoupe.
    door_index = 0
    door_storey = storeys[0]
    door_height = min(door_height,
                      storeys[-1].top - door_storey.bottom - min_pier * 0.25)
    if door_height < minimum_door:
        raise StyleError(
            f"porte_plus_basse_que_le_minimum:{door_height:.2f}<{minimum_door:.2f}")
    _, door_plane, door_lo, door_hi = face_of(door_storey, "front")
    door_along = (door_lo + door_hi) * 0.5
    door_top = door_storey.bottom + door_height
    # Les niveaux que la porte recoupe : ils ne recoivent pas de fenetre dans sa
    # travee, et le percement doit les traverser tous.
    door_span = frozenset(index for index, storey in enumerate(storeys)
                          if storey.bottom < door_top and storey.top > door_storey.bottom)
    openings = [Opening("door", "front", door_along, door_storey.bottom,
                        door_width, door_height, False, door_plane, door_index)]
    if not with_windows:
        return tuple(openings)

    window_width = rng.uniform(*window_style["width_m"])
    window_height = rng.uniform(*window_style["height_m"])
    # L'allege se rapporte a un niveau habitable, pas a l'assise qui porte la
    # porte : depuis que la porte est au sol, celle-ci peut etre une jupe de
    # 1,28 m et le rapport partait a 1,45.
    reference = next((storey for storey in storeys
                      if storey.role == "storey" and storey.height >= minimum_door),
                     storeys[-1])
    sill_ratio = rng.uniform(*window_style["sill_height_m"]) / max(1e-6, reference.height)
    # Le catalogue peut declarer `shutters` comme marqueur d'identite. Un
    # marqueur declare se pose : il ne se tire pas au sort.
    shutters = (forced_shutters
                or rng.random() < float(window_style["shutters_probability"]))

    for index, storey in enumerate(storeys):
        sill = storey.bottom + min(sill_ratio * storey.height,
                                   storey.height - window_height - min_pier * 0.5)
        if sill < storey.bottom or sill + window_height > storey.top:
            continue
        # Un niveau de pierre porte : il s'ouvre moins que les etages a pans de bois.
        share = stone_share if storey.kind == "stone" else 1.0
        for face in faces:
            _, plane, lo, hi = face_of(storey, face)
            extent = hi - lo
            bays = max(1, int(round(extent / bay_target)))
            # Trumeaux egaux, bords compris : n baies laissent n+1 trumeaux. En
            # centrant simplement chaque baie dans sa travee, celui de rive ne
            # valait que la moitie du minimum -- mesure 0,52 m pour 0,55 exiges.
            width = min(window_width, (extent - (bays + 1) * min_pier) / bays)
            if width < window_width * 0.45:
                continue
            pier = (extent - bays * width) / (bays + 1)
            for slot in range(bays):
                if share < 1.0 and (slot % 2) == 1:
                    continue
                along = lo + pier + width * 0.5 + slot * (width + pier)
                # La travee qui porte la porte ne recoit pas de fenetre basse.
                # La porte reclame un trumeau entier de chaque cote, pas la
                # moitie : sinon la baie voisine venait a 0,41 m d'elle.
                if (index in door_span and face == "front"
                        and abs(along - door_along) < (door_width + width) * 0.5 + min_pier):
                    continue
                openings.append(Opening("window", face, along, sill, width,
                                        window_height, shutters, plane, index))
    return tuple(openings)


def _scheme_for(style: dict, family: dict, variants: list[dict], index: int) -> dict:
    """Le schema d'une variante, stratifie sur la famille.

    Trois variantes recoivent trois schemas distincts tant que les rangs que la
    famille declare en offrent assez : c'est la porte C-5, et la variation de
    masse vient donc de la grammaire et non d'un jitter de dimensions.
    """
    forms = _forms(style, "scheme", "forms")
    ranks = family.get("scheme_ranks")
    if not isinstance(ranks, list) or not ranks:
        raise StyleError(f"Famille sans rang de schema : {family.get('id')}")
    reachable = [form for form in forms if form.get("rank") in ranks]
    # Un schema declare son public. Le vocabulaire etait entierement domestique
    # et les sept familles y puisaient sans filtre : la mesure etait sans appel,
    # `building_chapel_frontier_01_a` tirait `town_house` et sortait une
    # chapelle a encorbellement a chaque etage, avec deux lucarnes.
    #
    #   `any`       une masse que tout le monde peut prendre ;
    #   `domestic`  l'encorbellement et la maison de ville, reserves a l'habitat ;
    #   `utility`   la halle, reservee a ce qui n'est pas une maison.
    domestic = style["scheme"].get("domestic_functions")
    if domestic is not None:
        allowed = ("any", "domestic") if family["function"] in domestic else ("any", "utility")
        reachable = [form for form in reachable
                     if str(form.get("audience", "any")) in allowed]
    if len(reachable) < len(variants):
        raise StyleError(
            f"Schemas insuffisants pour {family.get('id')} : "
            f"{len(reachable)} pour {len(variants)} variantes")
    chosen = stratified_picks(random.Random(int(family["seed"])), reachable,
                              len(variants))[index]
    scheme = next(form for form in reachable if str(form["id"]) == chosen)
    _known([str(scheme["base"])], SCHEME_BASES, "scheme.base")
    _known([str(scheme["jetty"])], SCHEME_JETTIES, "scheme.jetty")
    _known([str(scheme["roof_composition"])], ROOF_COMPOSITIONS, "scheme.roof_composition")
    _known([str(scheme["edge_trim"])], EDGE_TRIMS, "scheme.edge_trim")
    _known([str(item) for item in scheme["appendages"]], APPENDAGES, "scheme.appendages")
    return scheme


def _finish_for(style: dict, family: dict, variants: list[dict], index: int) -> dict:
    """La finition d'une variante, stratifiee elle aussi et bornee par le mur."""
    forms = _forms(style, "finish", "forms")
    allowed = ((style["trim"]["wall_system_map"].get(str(family["wall_system"])) or {})
               .get("finishes"))
    pool = [form for form in forms if allowed is None or form["id"] in allowed]
    if not pool:
        raise StyleError(f"Aucune finition pour le mur {family['wall_system']}")
    chosen = stratified_picks(random.Random(int(family["seed"]) + 977), pool,
                              len(variants))[index]
    return next(form for form in pool if str(form["id"]) == chosen)


def _storeys(style: dict, rng: random.Random, scheme: dict, width: float, depth: float,
             storey_m: float, levels: float, bottom: float,
             upper_band: str, lower_band: str) -> tuple[Storey, ...]:
    """Empiler les niveaux, avec leur base et leurs encorbellements."""
    node = style["scheme"]
    base_kind = str(scheme["base"])
    base_spec = node["base"][base_kind]
    full = max(1, int(levels))

    base_height = 0.0
    batter = 0.0
    if base_kind in STOREY_BASES:
        base_height = rng.uniform(*base_spec["height_m"])
        raw_batter = base_spec.get("batter_m", 0.0)
        batter = (rng.uniform(*raw_batter) if isinstance(raw_batter, list)
                  else float(raw_batter))
        wall_storeys = max(1, full - 1)
    else:
        wall_storeys = full

    jetty = node["jetty"]
    faces = list(jetty["faces"][str(scheme["jetty"])])
    overhang = rng.uniform(*jetty["overhang_m"]) if faces else 0.0

    storeys: list[Storey] = []
    z = bottom
    half_w, half_d = width * 0.5, depth * 0.5
    if base_height > 0.0:
        # Le fruit est une jupe au pied du mur, pas un elargissement du niveau
        # entier : elargir tout le rez rattrapait l'encorbellement du niveau
        # au-dessus et le rendait invisible -- mesure : 0,05 m de debord utile
        # au lieu de 0,35.
        if batter > 0.0:
            skirt = base_height * 0.42
            storeys.append(Storey("stone", lower_band, z, skirt,
                                  -half_w - batter, half_w + batter,
                                  -half_d - batter, half_d + batter,
                                  role="skirt"))
            z += skirt
            base_height -= skirt
        storeys.append(Storey("stone", lower_band, z, base_height,
                              -half_w, half_w, -half_d, half_d))
        z += base_height

    # « first_floor » designe le niveau au-dessus du rez : quand la base est un
    # vrai niveau de pierre, c'est deja le premier niveau de mur.
    first = 0 if base_height > 0.0 else 1
    x0, x1, y0, y1 = -half_w, half_w, -half_d, half_d
    for index in range(wall_storeys):
        jetties = faces and index >= first and (
            str(scheme["jetty"]) == "each_floor" or index == first)
        if jetties:
            if "front" in faces:
                y0 -= overhang
            if "left" in faces:
                x0 -= overhang
            if "right" in faces:
                x1 += overhang
        storeys.append(Storey("wall", upper_band, z, storey_m, x0, x1, y0, y1))
        z += storey_m
    return tuple(storeys)


def _appendages(style: dict, rng: random.Random, scheme: dict,
                storeys: tuple[Storey, ...], wall_top: float,
                ridge_z: float) -> dict:
    """Tirer les parametres de chaque volume rapporte declare par le schema."""
    node = style["scheme"]["appendage"]
    top, ground = storeys[-1], storeys[0]
    # Un volume rapporte tire du cote oppose a la camera de revue disparait
    # derriere la masse : il coute des triangles et ne se lit jamais. Le style
    # declare la face que la revue voit ; la position le long de cette face
    # reste tiree par la graine.
    facing = int(style.get("review", {}).get("camera_facing_side_x", 1))
    drawn: dict = {}
    for name in scheme["appendages"]:
        spec = node[name]
        side = facing
        rng.random()  # la graine reste consommee a l'identique
        if name == "porch":
            depth_spec = scheme.get("porch_depth_m") or spec["depth_m"]
            drawn[name] = {
                "depth": rng.uniform(*depth_spec),
                "width": ground.width * rng.uniform(*spec["width_ratio"]),
                "post": float(spec["post_m"]),
                "pitch_deg": rng.uniform(*spec["pitch_deg"]),
            }
        elif name == "lean_to":
            drawn[name] = {
                "depth": ground.depth * rng.uniform(*spec["depth_ratio"]),
                "height": (wall_top - ground.bottom) * rng.uniform(*spec["height_ratio"]),
                "pitch_deg": rng.uniform(*spec["pitch_deg"]),
                "side": side,
            }
        elif name == "stair":
            # `rise` est la hauteur que le perron franchit reellement : du
            # terrain au seuil. Elle valait la hauteur du rez, que la geometrie
            # n'utilisait pas -- seul le cadrage de revue la lisait, et il
            # dimensionnait donc un escalier qui n'etait pas construit.
            drawn[name] = {
                "width": rng.uniform(*spec["width_m"]),
                "tread": float(spec["tread_m"]),
                "rail": float(spec["rail_m"]),
                "max_rise_m": float(spec["max_rise_m"]),
                "side": side,
                "rise": ground.bottom,
            }
        elif name == "gallery":
            depth_spec = scheme.get("gallery_depth_m") or spec["depth_m"]
            drawn[name] = {
                "depth": rng.uniform(*depth_spec),
                "rail": float(spec["rail_m"]),
                "post": float(spec["post_m"]),
                "level": max(1, len(storeys) - 1),
            }
        elif name == "chimney_stack":
            above_spec = scheme.get("chimney_above_ridge_m") or spec["above_ridge_m"]
            drawn[name] = {
                "width": rng.uniform(*spec["width_m"]),
                "depth": rng.uniform(*spec["depth_m"]),
                "top": ridge_z + rng.uniform(*above_spec),
                "taper": float(spec["taper"]),
                "side": side,
            }
        elif name == "roof_lantern":
            height_spec = scheme.get("lantern_height_m") or spec["height_m"]
            width_spec = scheme.get("lantern_width_ratio") or spec["width_ratio"]
            drawn[name] = {
                "width": top.width * rng.uniform(*width_spec),
                "height": rng.uniform(*height_spec),
            }
        elif name == "hanging_sign":
            drawn[name] = {
                "bracket": rng.uniform(*spec["bracket_m"]),
                "board": rng.uniform(*spec["board_m"]),
                "side": side,
            }
    return drawn


def _roof_composition(style: dict, rng: random.Random, scheme: dict, top: Storey,
                      span_axis: str, rise: float, half_span: float) -> tuple[dict, tuple[dict, ...]]:
    """Croupe transversale et lucarnes, telles que la composition les declare.

    Une croupe transversale casse le faitage unique : c'est l'element qui fait
    le plus monter l'articulation de silhouette a 96 px, pour un cout de deux
    versants.
    """
    node = style["scheme"]
    composition = node["roof_composition"][str(scheme["roof_composition"])]
    cross: dict = {}
    if composition.get("cross_gable"):
        spec = node["cross_gable"]
        cross = {
            "width": top.width * rng.uniform(*spec["width_ratio"]) if span_axis == "y"
            else top.depth * rng.uniform(*spec["width_ratio"]),
            "run": (top.depth if span_axis == "y" else top.width) * rng.uniform(*spec["run_ratio"]),
            "ridge_drop": rise * rng.uniform(*spec["ridge_drop_ratio"]),
            "offset": rng.uniform(-0.18, 0.18),
        }
    dormers: list[dict] = []
    spec = node["dormer"]
    count = int(composition.get("dormers", 0))
    for index in range(count):
        width = (top.width if span_axis == "y" else top.depth) * rng.uniform(*spec["width_ratio"])
        dormers.append({
            "width": width,
            "height": rise * rng.uniform(*spec["height_ratio"]),
            "seat": rng.uniform(*spec["seat_ratio"]),
            "offset": (index - (count - 1) * 0.5) * width * 1.9,
        })
    del half_span
    return cross, tuple(dormers)


def _annex(style: dict, rng: random.Random, scheme: dict, main: tuple[Storey, ...],
           storey_m: float, upper_band: str, lower_band: str,
           roof_style: dict, wall_style: dict, wide_door: bool,
           with_windows: bool) -> Annex | None:
    """Batir le corps accole : une maison entiere, mitoyenne de la principale."""
    entry = scheme.get("annex")
    if not entry:
        return None
    node = style["scheme"]["annex"]
    ground = main[0]
    width = ground.width * rng.uniform(*node["width_ratio"])
    depth = ground.depth * rng.uniform(*node["depth_ratio"])
    gap = float(node.get("gap_m", 0.0))

    level_form = str(entry["levels"])
    _known([level_form], tuple(LEVEL_STOREYS), "annex.levels")
    street_face = str(entry.get("street_face", "gable"))
    _known([street_face], STREET_FACES, "annex.street_face")

    sub = {
        "levels": level_form,
        "base": str(entry.get("base", "plinth")),
        "jetty": str(entry.get("jetty", "none")),
    }
    _known([sub["base"]], SCHEME_BASES, "annex.base")
    _known([sub["jetty"]], SCHEME_JETTIES, "annex.jetty")

    storeys = _storeys(style, rng, sub, width, depth, storey_m,
                       LEVEL_STOREYS[level_form], ground.bottom,
                       upper_band, lower_band)
    # Mitoyen : colle au flanc du corps principal. Deux blocs au meme nu de
    # facade se lisent comme un seul rectangle a 64 px ; un decalage vers la
    # rue, c'est le L des references -- deux pignons de hauteurs differentes,
    # le plus bas en avant. Le nombre vient du schema, pas d'un tirage : un
    # rng de plus aurait decale toute la suite et change les toitures.
    projection_spec = entry.get("street_projection_m", node.get("street_projection_m", 0.0))
    if isinstance(projection_spec, (list, tuple)):
        projection = (float(projection_spec[0]) + float(projection_spec[1])) * 0.5
    else:
        projection = float(projection_spec)
    shift_x = ground.x1 + gap + width * 0.5
    shift_y = ground.y0 + depth * 0.5 - projection
    storeys = tuple(
        replace(item, x0=item.x0 + shift_x, x1=item.x1 + shift_x,
                y0=item.y0 + shift_y, y1=item.y1 + shift_y)
        for item in storeys)

    top = storeys[-1]
    span_axis = "x" if street_face == "gable" else "y"
    half_span = (top.width if span_axis == "x" else top.depth) * 0.5
    pitch = rng.uniform(*(scheme.get("pitch_deg") or roof_style["pitch_deg"]))
    overhang = rng.uniform(*roof_style["overhang_m"])
    rise = math.tan(math.radians(pitch)) * (half_span + overhang)
    frame_style = roof_style["frame"]
    frame = RoofFrame(
        span_axis=span_axis, x0=top.x0, x1=top.x1, y0=top.y0, y1=top.y1,
        eave_z=top.top, rise=rise, overhang=overhang, pitch_deg=pitch,
        plate=float(frame_style["plate_m"]),
        ridge_beam=float(frame_style["ridge_m"]),
        rafter=float(frame_style["rafter_m"]),
        rafter_spacing=float(frame_style["rafter_spacing_m"]),
        rafter_depth=float(frame_style["rafter_depth_m"]),
    )
    # Une annexe s'ouvre moins qu'un corps principal : ses travees sont plus
    # larges, donc ses baies moins nombreuses.
    scaled = json.loads(json.dumps(style))
    span = scaled["opening"]["bay_width_m"]
    scale = float(node.get("bay_scale", 1.0))
    scaled["opening"]["bay_width_m"] = [span[0] * scale, span[1] * scale]
    openings = _openings(scaled, rng, storeys, wide_door, with_windows)
    return Annex(storeys=storeys, frames=(frame,), openings=openings,
                 width=width, depth=depth, span_axis=span_axis,
                 rise=rise, half_span=half_span,
                 upper_band=upper_band, lower_band=lower_band)


def plan_building(style: dict, family: dict, variants: list[dict], variant_id: str) -> Plan:
    """Deriver le plan complet d'une variante, sans aucun aleatoire non graine."""
    identifiers = [variant["id"] for variant in variants]
    if variant_id not in identifiers:
        raise StyleError(f"Variante inconnue : {variant_id}")
    index = identifiers.index(variant_id)
    variant = variants[index]
    seed = int(family["seed"]) + int(variant["seed_offset"])

    footprint_forms = _forms(style, "footprint", "forms")
    _known([str(form["id"]) for form in footprint_forms], FOOTPRINT_FORMS, "footprint.forms")
    level_forms = _forms(style, "levels", "forms")
    roof_forms = _forms(style, "roof", "forms")
    _known([str(form["id"]) for form in roof_forms], ROOF_FORMS, "roof.forms")
    ridge_forms = _forms(style, "roof", "ridge_axis")
    _known([str(form["id"]) for form in ridge_forms], RIDGE_AXES, "roof.ridge_axis")

    # L'emprise, la forme et la pente du toit et le nombre de niveaux
    # appartiennent tous au schema : ils decrivent une meme masse et les tirer
    # separement produisait des combinaisons incoherentes -- une croupe a 50
    # degres sur une maison de ville a trois niveaux, par exemple.
    scheme = _scheme_for(style, family, variants, index)
    finish = _finish_for(style, family, variants, index)
    footprint_form = str(scheme.get("footprint") or stratified_picks(
        random.Random(int(family["seed"])), footprint_forms, len(variants))[index])
    _known([footprint_form], FOOTPRINT_FORMS, "scheme.footprint")

    rng = random.Random(seed)
    level_form = str(scheme["levels"])
    _known([level_form], tuple(LEVEL_STOREYS), "scheme.levels")
    del level_forms
    footprint = style["footprint"]
    wall_style, roof_style, foundation_style = style["wall"], style["roof"], style["foundation"]
    base_width, base_depth, base_wall = (float(value) for value in family["dimensions"][:3])
    minimum = float(footprint["min_side_m"])
    jitter = footprint["dimension_jitter"]
    # Un schema peut etirer l'emprise du catalogue. Une halle est un long
    # vaisseau : sans cet etirement elle sortait aux memes proportions qu'une
    # chaumiere et les deux silhouettes se confondaient -- mesure IoU 0,822
    # entre `cottage_stack` et `open_hall` sur l'entrepot, pour un seuil de 0,80.
    stretch = scheme.get("plan_stretch") or [1.0, 1.0]
    width = max(minimum, base_width * float(stretch[0]) * (1.0 + rng.uniform(*jitter)))
    depth = max(minimum, base_depth * float(stretch[1]) * (1.0 + rng.uniform(*jitter)))

    storey_m = storey_height(style, base_wall)
    levels = LEVEL_STOREYS[level_form]
    foundation_height = rng.uniform(*foundation_style["height_m"])

    upper_band = str(finish["upper"])
    lower_band = str(finish["lower"])
    storeys = _storeys(style, rng, scheme, width, depth, storey_m, levels,
                       foundation_height, upper_band, lower_band)
    wall_storeys = [storey for storey in storeys if storey.kind == "wall"]
    base_storey_height = sum(storey.height for storey in storeys if storey.kind == "stone")
    wall_height = (sum(storey.height for storey in wall_storeys)
                   + rng.uniform(*wall_style["height_jitter"]))

    # La forme et la pente du toit appartiennent au schema : un tirage global
    # posait une croupe a 50 degres sur une maison de ville a trois niveaux, et
    # la toiture avalait la masse.
    roof_form = str(scheme.get("roof_form") or weighted_pick(rng, roof_forms))
    _known([roof_form], ROOF_FORMS, "scheme.roof_form")
    ridge_axis = weighted_pick(rng, ridge_forms)
    pitch_deg = rng.uniform(*(scheme.get("pitch_deg") or roof_style["pitch_deg"]))
    overhang = rng.uniform(*roof_style["overhang_m"])
    # Le toit couvre le niveau du haut, pas l'emprise nominale : sous
    # encorbellement le dernier niveau deborde, et un toit cale sur l'emprise
    # laisserait la facade a nu.
    top = storeys[-1]
    # La face de rue appartient au schema. Le faitage court perpendiculairement a
    # l'axe de portee : portee sur x, le faitage suit y et la facade avant est un
    # pignon ; portee sur y, la facade avant est un gouttereau.
    street_face = str(scheme.get("street_face") or "gable")
    _known([street_face], STREET_FACES, "scheme.street_face")
    span_axis = "x" if street_face == "gable" else "y"
    half_span = (top.width if span_axis == "x" else top.depth) * 0.5
    rise = math.tan(math.radians(pitch_deg)) * (half_span + overhang)

    wing: dict = {}
    lean_to: dict = {}
    facing = int(style.get("review", {}).get("camera_facing_side_x", 1))
    if footprint_form == "l_shape":
        shape = footprint["l_shape"]
        # L'aile va vers la camera de revue. Posee au fond, elle disparaissait
        # derriere le corps principal : mesure a l'appui, la maison de ville
        # restait a 5,6 d'articulation avec une aile qu'on ne voyait pas.
        wing = {
            "width": width * rng.uniform(*shape["wing_width_ratio"]),
            "depth": depth * rng.uniform(*shape["wing_depth_ratio"]),
            "ridge_ratio": rng.uniform(*shape["wing_ridge_ratio"]),
            "projection": depth * rng.uniform(*shape["wing_projection_ratio"]),
            "side": facing,
        }
        rng.random()
    elif footprint_form == "rectangle_lean_to":
        shape = footprint["lean_to"]
        lean_to = {
            "depth": depth * rng.uniform(*shape["depth_ratio"]),
            "height": wall_height * rng.uniform(*shape["height_ratio"]),
            "pitch_deg": rng.uniform(*shape["pitch_deg"]),
            "side": facing,
        }
        rng.random()

    markers = tuple(family.get("identity_markers", ()))
    wide_door = bool({"double_door", "cross_braced_doors"} & set(markers))
    with_windows = "lancet_windows" not in markers
    openings = _openings(style, rng, storeys, wide_door, with_windows,
                         forced_shutters="shutters" in markers)
    annex = _annex(style, rng, scheme, storeys, storey_m, upper_band, lower_band,
                   roof_style, wall_style, wide_door, with_windows)
    frame_style = roof_style["frame"]
    roof_frame = RoofFrame(
        span_axis=span_axis,
        x0=top.x0, x1=top.x1, y0=top.y0, y1=top.y1,
        eave_z=foundation_height + base_storey_height + wall_height,
        rise=rise, overhang=overhang, pitch_deg=pitch_deg,
        plate=float(frame_style["plate_m"]),
        ridge_beam=float(frame_style["ridge_m"]),
        rafter=float(frame_style["rafter_m"]),
        rafter_spacing=float(frame_style["rafter_spacing_m"]),
        rafter_depth=float(frame_style["rafter_depth_m"]),
    )
    # Decrochement de faitage : la volee haute couvre une part du long-pan et
    # monte d'un cran. Deux pignons contre le ciel au lieu d'un seul faitage
    # continu -- un second corps adjacent, lui, se noie en projection.
    roof_frame_high = None
    if scheme.get("ridge_break"):
        node = style["scheme"]["ridge_break"]
        share = rng.uniform(*node["run_ratio"])
        step = rng.uniform(*node["step_m"])
        run = roof_frame.run
        cut = run * share
        if span_axis == "x":
            split = top.y0 + cut
            roof_frame_high = replace(roof_frame, y1=split, eave_z=roof_frame.eave_z + step)
            roof_frame = replace(roof_frame, y0=split)
        else:
            split = top.x0 + cut
            roof_frame_high = replace(roof_frame, x1=split, eave_z=roof_frame.eave_z + step)
            roof_frame = replace(roof_frame, x0=split)

    cross_gable, dormers = _roof_composition(style, rng, scheme, storeys[-1],
                                             span_axis, rise, half_span)
    appendages = _appendages(style, rng, scheme, storeys,
                             foundation_height + base_storey_height + wall_height,
                             foundation_height + base_storey_height + wall_height + rise)

    palettes = {palette["id"]: palette for palette in style["palettes"]}
    palette_id = str(variant["palette_id"])
    if palette_id not in palettes:
        raise StyleError(f"Palette absente du style : {palette_id}")

    budget = style["budget"]
    function = str(family["function"])
    if function not in budget["function_class"]:
        raise StyleError(f"Fonction sans classe de budget : {function}")
    budget_class = str(budget["function_class"][function])
    lod_budget = tuple(int(value) for value in budget["classes"][budget_class]["lod"])

    eave = roof_style["eave_strip"]
    if eave["mode"] not in EAVE_STRIP_MODES:
        raise StyleError(f"Mode de bande d'egout inconnu : {eave['mode']}")

    return Plan(
        asset_id=f"{family['id']}_{variant_id}",
        seed=seed,
        function=function,
        wall_system=str(family["wall_system"]),
        roof_system=str(family["roof_system"]),
        identity_markers=markers,
        palette_id=palette_id,
        palette=palettes[palette_id],
        footprint_form=footprint_form,
        level_form=level_form,
        levels=levels,
        width=width,
        depth=depth,
        storey_m=storey_m,
        wall_height=wall_height,
        wall_thickness=float(wall_style["thickness_m"]),
        corner_post=float(wall_style["corner_post_m"]),
        wall_bevel=float(wall_style["bevel_m"]),
        foundation_height=foundation_height,
        foundation_projection=float(foundation_style["projection_m"]),
        foundation_bevel=float(foundation_style["bevel_m"]),
        roof_form=roof_form,
        ridge_axis=ridge_axis,
        pitch_deg=pitch_deg,
        overhang=overhang,
        roof_thickness=float(roof_style["thickness_m"]),
        rise=rise,
        span_axis=span_axis,
        half_span=half_span,
        eave_mode=str(eave["mode"]),
        eave_depth=float(eave["depth_m"]),
        eave_teeth_per_m=float(eave["teeth_per_m"]),
        reveal_depth=rng.uniform(*style["opening"]["reveal_depth_m"]),
        openings=openings,
        scheme_id=str(scheme["id"]),
        scheme_rank=str(scheme["rank"]),
        base_kind=str(scheme["base"]),
        jetty=str(scheme["jetty"]),
        # Le debord se mesure contre l'emprise nominale, pas contre le niveau du
        # dessous : sinon une jupe de fruit le fait disparaitre du rapport.
        jetty_overhang=max([0.0] + [abs(storey.y0) - depth * 0.5
                                    for storey in storeys if storey.kind == "wall"]),
        roof_composition=str(scheme["roof_composition"]),
        roof_frame=roof_frame,
        roof_frame_high=roof_frame_high,
        annexes=tuple(item for item in (annex,) if item is not None),
        cross_gable=cross_gable,
        dormers=dormers,
        jetty_bracket=float(style["scheme"]["jetty"]["bracket_m"]),
        edge_trim=str(scheme["edge_trim"]),
        edge_trim_spec=dict(style["scheme"]["edge_trim"][str(scheme["edge_trim"])]),
        appendages=appendages,
        storeys=storeys,
        finish_id=str(finish["id"]),
        upper_band=upper_band,
        lower_band=lower_band,
        base_storey_height=base_storey_height,
        wing=wing,
        lean_to=lean_to,
        window_mullion=float(style["opening"]["window"].get("mullion_m", 0.0)),
        window_frame_inset=float(style["opening"]["window"].get("frame_inset_m", 0.0)),
        budget_class=budget_class,
        budget_lod=lod_budget,
        trim=style["trim"],
        lod=style["lod"],
        silhouette_gate=style["silhouette_gate"],
        review=style["review"],
    )
