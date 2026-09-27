"""Maisons de terre crue en îlots mitoyens, dans le ksar et au bord de l'oasis.

La composition reprend `citadelle.urbanisme.rangee` : largeurs, retraits et
orientations irréguliers, un identifiant par maison. Seules les teintes
d'enduit changent : ocres, roses et chaux plutôt que les crépis alpins.
"""
import random
from local3d.citadelle.urbanisme import rangee

TEINTES = [(1,.93,.84),(.97,.84,.72),(.92,.78,.66),(1,.97,.91),(.95,.81,.70),(.88,.73,.61),(1,.89,.80)]


def teinter(houses, seed):
    rng = random.Random(seed)
    for house in houses:
        house['color'] = rng.choice(TEINTES)
    return houses


def hameau(seed, z):
    """Le bourg bas : quatre rangées au bord des jardins, altitudes fournies par le relief."""
    rng = random.Random(seed + 7169); houses = []
    blocks = [(5,(-81,-68,z[0]),-88,25),(3,(-113,-69,z[1]),85,17.5),
              (4,(-116,-16,z[2]),64,23),(3,(-140,-53,z[3]),101,17)]
    for i,(count,center,angle,length) in enumerate(blocks):
        center = (center[0]+rng.uniform(-.8,.8), center[1]+rng.uniform(-2,2), center[2])
        houses.extend(rangee(count,center,angle,length,rng,'hameau_'+str(i)))
    return teinter(houses, seed + 71)


def cite(seed, count, z):
    """Le ksar haut : rues serrées autour de la place, sur le plateau de grès."""
    rng = random.Random(seed + 9381); houses = []
    blocks = [(5,(-23,-25,z),0,27),(4,(23,-25,z),0,24),
              (6,(-32,7,z),90,35),(count-19,(33,8,z),-90,32),
              (2,(-19,-11,z),90,11),(2,(20,-11,z),-90,11)]
    for i,(n,center,angle,length) in enumerate(blocks):
        houses.extend(rangee(n,center,angle,length,rng,'ksar_'+str(i)))
    return teinter(houses, seed + 93)


def echelle(house, kind):
    return (house['width']/6, house['depth']/6, house['height_scale'])
