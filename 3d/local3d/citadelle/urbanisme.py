"""Maisons indépendantes, regroupées en îlots mitoyens irréguliers.

Chaque empreinte reste associée à un seul identifiant de maison. Les retraits,
largeurs et hauteurs changent avec la graine, sans fabriquer un bâtiment collectif.
"""
import math
import random


def rangee(count,center,angle,length,rng,group):
    widths=[rng.uniform(.77,1.23) for _ in range(count)]
    widths=[w*(length+.10*(count-1))/sum(widths) for w in widths]
    angle+=rng.uniform(-7,7);a=math.radians(angle);along=(math.cos(a),math.sin(a));front=(math.sin(a),-math.cos(a))
    cursor=-length/2;houses=[];centers=[];directions=[]
    phase=rng.uniform(0,math.tau)
    for i,width in enumerate(widths):
        theta=math.radians(angle+13*math.sin(i*1.2+phase)+rng.uniform(-5,5));direction=(math.cos(theta),math.sin(theta))
        if i==0:point=(0,0)
        else:
            previous=centers[-1];before=directions[-1]
            point=(previous[0]+before[0]*(widths[i-1]/2-.12)+direction[0]*(width/2-.12),
                   previous[1]+before[1]*(widths[i-1]/2-.12)+direction[1]*(width/2-.12))
        centers.append(point);directions.append(direction)
    midpoint=((centers[0][0]+centers[-1][0])/2,(centers[0][1]+centers[-1][1])/2)
    for index,width in enumerate(widths):
        depth=rng.uniform(5.5,8.1);recess=rng.uniform(-.75,.75)
        x=center[0]+centers[index][0]-midpoint[0]+front[0]*recess
        y=center[1]+centers[index][1]-midpoint[1]+front[1]*recess
        rotation=math.degrees(math.atan2(directions[index][1],directions[index][0]));theta=math.radians(rotation)
        f=(math.sin(theta),-math.cos(theta));margin=1.0
        houses.append({'position':[x,y,center[2]],'rotation':rotation,'width':width,'depth':depth,
                       'height_scale':rng.uniform(.78,1.17),'group':group,
                       'pad_position':[x-f[0]*1.5,y-f[1]*1.5,center[2]],
                       'size':[abs(math.cos(theta))*width+abs(math.sin(theta))*(depth+3)+margin,
                               abs(math.sin(theta))*width+abs(math.cos(theta))*(depth+3)+margin],
                       'door':[x+f[0]*(depth/2+1),y+f[1]*(depth/2+1),center[2]],
                       'lane':[x+f[0]*(depth/2+3.5),y+f[1]*(depth/2+3.5),center[2]],
                       'color':rng.choice([(1,.88,.73),(.72,.79,.83),(.87,.94,.83),(.91,.79,.65),(.78,.76,.72),(1,.97,.86)])})
        cursor+=width-.10
    return houses


def hameau(seed):
    rng=random.Random(seed+7169);houses=[]
    blocks=[(5,(-81,-68,17.3),-88,25),(3,(-113,-69,16.1),85,17.5),
            (4,(-116,-16,11.7),64,23),(3,(-140,-53,13.8),101,17)]
    for i,(count,center,angle,length) in enumerate(blocks):
        center=(center[0]+rng.uniform(-.8,.8),center[1]+rng.uniform(-2,2),center[2])
        houses.extend(rangee(count,center,angle,length,rng,'hameau_'+str(i)))
    return houses


def cite(seed,count):
    rng=random.Random(seed+9381);houses=[]
    blocks=[(5,(-23,-25,42.15),0,27),(4,(23,-25,42.15),0,24),
            (6,(-32,7,42.15),90,35),(count-19,(33,8,42.15),-90,32),
            (2,(-19,-11,42.15),90,11),(2,(20,-11,42.15),-90,11)]
    for i,(n,center,angle,length) in enumerate(blocks):
        houses.extend(rangee(n,center,angle,length,rng,'cite_'+str(i)))
    return houses


def echelle(house,kind):
    return (house['width']/6,house['depth']/6,house['height_scale'])
