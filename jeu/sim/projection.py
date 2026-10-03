"""Lambert azimutale équivalente ellipsoïdale EPSG:3035, en Python pur."""

import math

DEMI_GRAND_AXE_GRS80_M = 6_378_137.0
APLATISSEMENT_GRS80 = 1 / 298.257222101
LATITUDE_ORIGINE_DEGRES = 52.0
LONGITUDE_ORIGINE_DEGRES = 10.0
FAUSSE_ABSCISSE_M = 4_321_000.0
FAUSSE_ORDONNEE_M = 3_210_000.0
DEUX = 2.0


def _q_authalique(latitude, excentricite):
    """Intégrale ellipsoïdale de Snyder ; sa limite sphérique est 2 sin φ."""
    sinus = math.sin(latitude)
    if excentricite == 0:
        return DEUX * sinus
    produit = excentricite * sinus
    return (1 - excentricite * excentricite) * (
        sinus / (1 - produit * produit)
        - math.log((1 - produit) / (1 + produit)) / (DEUX * excentricite)
    )


def projeter_epsg3035(
    latitude, longitude, *, latitude_origine=LATITUDE_ORIGINE_DEGRES,
    longitude_origine=LONGITUDE_ORIGINE_DEGRES, aplatissement=APLATISSEMENT_GRS80,
):
    """Convertit (latitude, longitude) EPSG:4326 en (x, y) mètres EPSG:3035.

    Les paramètres facultatifs servent aux contre-épreuves de l'origine et
    de l'ellipsoïde ; les ancres utilisent exclusivement les valeurs EPSG.
    """
    phi, phi0 = math.radians(latitude), math.radians(latitude_origine)
    delta_lambda = math.radians(longitude - longitude_origine)
    excentricite = math.sqrt(aplatissement * (DEUX - aplatissement))
    qp = _q_authalique(math.pi / DEUX, excentricite)
    beta = math.asin(_q_authalique(phi, excentricite) / qp)
    beta0 = math.asin(_q_authalique(phi0, excentricite) / qp)
    rayon = DEMI_GRAND_AXE_GRS80_M * math.sqrt(qp / DEUX)
    m0 = math.cos(phi0) / math.sqrt(1 - (excentricite * math.sin(phi0)) ** DEUX)
    d = DEMI_GRAND_AXE_GRS80_M * m0 / (rayon * math.cos(beta0))
    b = rayon * math.sqrt(DEUX / (
        1 + math.sin(beta0) * math.sin(beta)
        + math.cos(beta0) * math.cos(beta) * math.cos(delta_lambda)
    ))
    return (
        FAUSSE_ABSCISSE_M + b * d * math.cos(beta) * math.sin(delta_lambda),
        FAUSSE_ORDONNEE_M + b / d * (
            math.cos(beta0) * math.sin(beta)
            - math.sin(beta0) * math.cos(beta) * math.cos(delta_lambda)
        ),
    )
