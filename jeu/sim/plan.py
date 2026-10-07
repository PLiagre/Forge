"""Plan du bourg en mètres locaux, lu par les intentions et les chantiers."""

from dataclasses import asdict, dataclass, field
import math

import sim.constants as _constantes


class PlanInvalide(ValueError):
    """Une donnée du plan manque ou contredit son contrat."""


def aire_du_contour(points):
    """Aire en m² par le lacet, indépendante du sens du contour."""
    produits = sum(a[0] * b[1] - b[0] * a[1]
                   for a, b in zip(points, (*points[1:], points[0])))
    return abs(produits) * _constantes.AIRE_PAR_PRODUIT_CROISE


def _identifiant(valeur, champ):
    if isinstance(valeur, bool) or not isinstance(valeur, int) or valeur < 0:
        raise PlanInvalide(f"{champ} invalide : attendu un entier ≥ 0, reçu {valeur!r}")


def _nombre_fini(valeur, champ):
    if (isinstance(valeur, bool) or not isinstance(valeur, (int, float))
            or (isinstance(valeur, float) and not math.isfinite(valeur))):
        raise PlanInvalide(f"{champ} : nombre fini attendu, reçu {valeur!r}")


def _points(points, minimum, champ):
    if not isinstance(points, (list, tuple)) or len(points) < minimum:
        raise PlanInvalide(f"{champ} : au moins {minimum} points attendus")
    for point in points:
        if not isinstance(point, (list, tuple)) or len(point) != _constantes.COORDONNEES_PAR_POINT:
            raise PlanInvalide(f"{champ} : point (x, y) attendu, reçu {point!r}")
        for coordonnee in point:
            _nombre_fini(coordonnee, champ)


def _chantier(element, nature):
    """Valide l’état, les foyers et le compte des journées d’un chantier."""
    if not isinstance(element.en_chantier, bool):
        raise PlanInvalide(f"{nature}.en_chantier : booléen attendu")
    _identifiant(element.identifiant, f"{nature}.identifiant")
    for champ in ("foyers", "travail_requis", "travail_fourni"):
        _identifiant(getattr(element, champ), f"{nature}.{champ}")
    if element.travail_fourni > element.travail_requis:
        raise PlanInvalide(f"{nature}.travail_fourni : dépasse le travail requis")
    if element.en_chantier != (element.travail_fourni < element.travail_requis):
        raise PlanInvalide(f"{nature}.en_chantier : contredit le travail restant")
    if element.en_chantier and element.foyers == 0:
        raise PlanInvalide(f"{nature}.foyers : chantier sans foyer")


@dataclass(frozen=True)
class Rue:
    """Ligne de rue ; achevée avec porte, elle concentre le commerce terrestre."""

    identifiant: int
    points: list[tuple[float, float]]
    largeur_m: float
    en_chantier: bool = False
    foyers: int = 0
    travail_requis: int = 0
    travail_fourni: int = 0
    porte_cell_id: int | None = None

    def __post_init__(self):
        _chantier(self, "rue")
        if self.porte_cell_id is not None:
            _identifiant(self.porte_cell_id, "rue.porte_cell_id")
        _points(self.points, _constantes.POINTS_MIN_RUE, "rue.points")
        _nombre_fini(self.largeur_m, "rue.largeur_m")
        if self.largeur_m <= 0:
            raise PlanInvalide("rue.largeur_m : largeur strictement positive attendue")


@dataclass(frozen=True)
class Parcelle:
    """Contour local d'une parcelle."""

    identifiant: int
    contour: list[tuple[float, float]]
    en_chantier: bool = False
    foyers: int = 0
    travail_requis: int = 0
    travail_fourni: int = 0

    def __post_init__(self):
        _chantier(self, "parcelle")
        _points(self.contour, _constantes.POINTS_MIN_CONTOUR, "parcelle.contour")


@dataclass(frozen=True)
class Batiment:
    """Emprise et nature d'un bâtiment, rattaché à une parcelle du plan."""

    identifiant: int
    parcelle: int
    nature: str
    emprise: list[tuple[float, float]]
    en_chantier: bool = False
    foyers: int = 0
    travail_requis: int = 0
    travail_fourni: int = 0

    def __post_init__(self):
        _chantier(self, "bâtiment")
        _identifiant(self.parcelle, "bâtiment.parcelle")
        if not isinstance(self.nature, str) or not self.nature.strip():
            raise PlanInvalide("bâtiment.nature : texte non vide attendu")
        _points(self.emprise, _constantes.POINTS_MIN_CONTOUR, "bâtiment.emprise")


@dataclass
class Plan:
    """Trois listes triées ; son unique clé spatiale appartient à World.plans."""

    rues: list[Rue] = field(default_factory=list)
    parcelles: list[Parcelle] = field(default_factory=list)
    batiments: list[Batiment] = field(default_factory=list)

    def __post_init__(self):
        listes = self._listes_validees()
        self.rues = listes["rues"]
        self.parcelles = listes["parcelles"]
        self.batiments = listes["batiments"]

    def _listes_validees(self):
        listes = {}
        for nom, classe in (("rues", Rue), ("parcelles", Parcelle), ("batiments", Batiment)):
            elements = getattr(self, nom)
            if not isinstance(elements, list):
                raise PlanInvalide(f"{nom} : liste attendue")
            identifiants = set()
            for element in elements:
                if not isinstance(element, classe):
                    raise PlanInvalide(f"{nom} : {classe.__name__} attendu")
                element.__post_init__()
                if element.identifiant in identifiants:
                    raise PlanInvalide(f"{nom} : identifiant en double {element.identifiant}")
                identifiants.add(element.identifiant)
            listes[nom] = sorted(elements, key=lambda element: element.identifiant)
        parcelles = {parcelle.identifiant for parcelle in listes["parcelles"]}
        for batiment in listes["batiments"]:
            if batiment.parcelle not in parcelles:
                raise PlanInvalide(
                    f"bâtiment {batiment.identifiant} : parcelle absente {batiment.parcelle}"
                )
        return listes

    def to_dict(self) -> dict:
        """Copie canonique triée ; refuse aussi une liste altérée après construction."""
        document = {}
        for nom, elements in self._listes_validees().items():
            document[nom] = []
            for element in elements:
                entree = asdict(element)
                if nom == "rues" and entree["porte_cell_id"] is None:
                    del entree["porte_cell_id"]
                for champ in ("points", "contour", "emprise"):
                    if champ in entree:
                        entree[champ] = [list(point) for point in entree[champ]]
                document[nom].append(entree)
        return document


def apport_routes_arete_kg(monde, a_id, b_id):
    """Somme stable des largeurs achevées vers l'autre bout, sans cache."""
    plans = getattr(monde, "plans", {})
    largeurs = sum(rue.largeur_m
                   for origine, porte in sorted(((a_id, b_id), (b_id, a_id)))
                   if origine in plans
                   for rue in sorted(plans[origine].rues, key=lambda rue: rue.identifiant)
                   if not rue.en_chantier and rue.porte_cell_id == porte)
    return _constantes.DEBIT_ROUTE_KG_PAR_M_PAR_TICK * largeurs
