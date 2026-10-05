"""Plan du bourg en mètres locaux, lu par les intentions et les chantiers."""

from dataclasses import asdict, dataclass, field
import math

import sim.constants as _constantes


class PlanInvalide(ValueError):
    """Une donnée du plan manque ou contredit son contrat."""


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


@dataclass(frozen=True)
class Rue:
    """Ligne de rue et largeur, sans effet sur les flux du monde."""

    identifiant: int
    points: list[tuple[float, float]]
    largeur_m: float
    en_chantier: bool = False
    foyers: int = 0
    travail_requis: int = 0
    travail_fourni: int = 0

    def __post_init__(self):
        if not isinstance(self.en_chantier, bool):
            raise PlanInvalide("rue.en_chantier : booléen attendu")
        _identifiant(self.identifiant, "rue.identifiant")
        for champ in ("foyers", "travail_requis", "travail_fourni"):
            _identifiant(getattr(self, champ), f"rue.{champ}")
        if self.travail_fourni > self.travail_requis:
            raise PlanInvalide("rue.travail_fourni : dépasse le travail requis")
        if self.en_chantier != (self.travail_fourni < self.travail_requis):
            raise PlanInvalide("rue.en_chantier : contredit le travail restant")
        if self.en_chantier and self.foyers == 0:
            raise PlanInvalide("rue.foyers : chantier sans foyer")
        _points(self.points, _constantes.POINTS_MIN_RUE, "rue.points")
        _nombre_fini(self.largeur_m, "rue.largeur_m")
        if self.largeur_m <= 0:
            raise PlanInvalide("rue.largeur_m : largeur strictement positive attendue")


@dataclass(frozen=True)
class Parcelle:
    """Contour local d'une parcelle."""

    identifiant: int
    contour: list[tuple[float, float]]

    def __post_init__(self):
        _identifiant(self.identifiant, "parcelle.identifiant")
        _points(self.contour, _constantes.POINTS_MIN_CONTOUR, "parcelle.contour")


@dataclass(frozen=True)
class Batiment:
    """Emprise et nature d'un bâtiment, rattaché à une parcelle du plan."""

    identifiant: int
    parcelle: int
    nature: str
    emprise: list[tuple[float, float]]

    def __post_init__(self):
        _identifiant(self.identifiant, "bâtiment.identifiant")
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
                for champ in ("points", "contour", "emprise"):
                    if champ in entree:
                        entree[champ] = [list(point) for point in entree[champ]]
                document[nom].append(entree)
        return document
