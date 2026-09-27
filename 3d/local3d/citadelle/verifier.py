"""Rouvre le fichier livré et vérifie les placements et l'animation réelle."""
import argparse
import math
import json
import sys
from statistics import median
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from local3d.atelier_v2.geometrie import tri_count
OUT=ROOT/'local3d/citadelle/sorties'

def verify(name):
    folder=OUT/'villages'/name;report=json.loads((folder/(name+'.json')).read_text(encoding='utf-8'))
    bpy.ops.wm.open_mainfile(filepath=str(folder/(name+'.blend')));bpy.context.scene.frame_set(1)
    def placements():
        for i in report['instances']:
            o=bpy.data.objects.get(i['id'])
            if not o or (o.location-Vector(i['position'])).length>.001:raise ValueError('Placement absent ou divergent : '+i['id'])
    if not report['instances']:raise ValueError('Scène vide')
    placements();o=bpy.data.objects[report['instances'][0]['id']];o.location.x+=1;red=False
    try:placements()
    except ValueError:red=True
    o.location.x-=1
    if not red:raise ValueError('Le contrôle ne détecte pas un déplacement incorrect')
    def cameras():
        if not report.get('cameras'):raise ValueError('Cadrages absents')
        for camera in report['cameras']:
            o=bpy.data.objects.get(camera['name'])
            if not o or o.type!='CAMERA':raise ValueError('Caméra absente')
            target=(Vector(camera['target'])-o.location).normalized()
            direction=o.rotation_euler.to_quaternion()@Vector((0,0,-1))
            if (o.location-Vector(camera['position'])).length>.001 or abs(o.data.lens-camera['lens'])>.001 or target.dot(direction)<.999999:
                raise ValueError('Cadrage divergent : '+camera['name'])
    cameras();camera=bpy.data.objects[report['cameras'][0]['name']];lens=camera.data.lens;camera.data.lens+=2;camera_red=False
    try:cameras()
    except ValueError:camera_red=True
    camera.data.lens=lens
    if not camera_red:raise ValueError('Une mauvaise focale passe le contrôle')
    # Le haut des marches doit rejoindre le sol des portails à une marche près.
    stairs=bpy.data.objects[next(i['id'] for i in report['instances'] if i['asset']=='escalier')]
    portal=bpy.data.objects[next(i['id'] for i in report['instances'] if i['asset']=='cathedrale_facade')]
    def raccord():
        heights=sorted({round((stairs.matrix_world@p.center).z,4) for p in stairs.data.polygons
                        if p.normal.z>.99 and stairs.data.materials[p.material_index].name=='pierre_taille'})
        if len(heights)<2:raise ValueError('Marches absentes')
        rise=median([b-a for a,b in zip(heights,heights[1:])])
        gap=portal.location.z-heights[-1]
        if rise<=0 or abs(gap)>rise:raise ValueError('Escalier non raccordé aux portails')
        return gap
    gap=raccord();scale=stairs.scale.z;stairs.scale.z*=1.8;bpy.context.view_layer.update();stairs_red=False
    try:raccord()
    except ValueError:stairs_red=True
    stairs.scale.z=scale;bpy.context.view_layer.update()
    if not stairs_red:raise ValueError('Un escalier trop haut passe le contrôle')
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and any(c.name[:2] in ('01','02','03','04') for c in o.users_collection)]
    triangles=sum(tri_count(o) for o in meshes)
    if triangles!=report['triangles_lod0'] or not 0<triangles<3000000:raise ValueError('Géométrie ou budget divergent')
    images=[i for i in bpy.data.images if i.source=='FILE' and i.users>0]
    if not images or any(not i.packed_file for i in images):raise ValueError('Texture externe non embarquée')
    banners=[bpy.data.objects[n] for n in report['banners']]
    a=[o.data.shape_keys.key_blocks['Rafale'].value for o in banners];bpy.context.scene.frame_set(18);b=[o.data.shape_keys.key_blocks['Rafale'].value for o in banners]
    if not a or max(abs(x-y) for x,y in zip(a,b))<.1:raise ValueError('Bannières immobiles')
    # La herse laisse un passage réel sous ses barreaux, indispensable à la lecture de la porte.
    gate=bpy.data.objects[next(i['id'] for i in report['instances'] if i['asset']=='porte_ogive')]
    hit,*_=gate.ray_cast(Vector((0,-10,2)),Vector((0,1,0)))
    if hit:raise ValueError('La porte est obstruée à hauteur humaine')
    roads=bpy.data.objects.get('Chemins_praticables')
    def road_surface():
        if not roads or not report.get('routes') or not report.get('plots'):raise ValueError('Accès ou terrains absents')
        count=0;max_grade=0;inverse=roads.matrix_world.inverted()
        for route in report['routes']:
            if route['id']=='citadelle_pont':continue
            pts=[Vector(p['position']) for p in route['points']]
            if len(pts)<2:raise ValueError('Profil de chemin vide')
            for k,p in enumerate(pts):
                # Le rayon entre de 2 cm dans le ruban aux extrémités ouvertes.
                probe=p+(pts[1]-p).normalized()*.02 if k==0 else p+(pts[-2]-p).normalized()*.02 if k==len(pts)-1 else p
                hit,location,*_=roads.ray_cast(inverse@(probe+Vector((0,0,.5))),Vector((0,0,-1)),distance=1)
                if not hit or abs((roads.matrix_world@location).z-p.z)>.3:
                    raise ValueError('Chemin sans surface sous les pieds : '+route['id']+' '+str(p))
                count+=1
            for a,b in zip(pts,pts[1:]):
                grade=abs(b.z-a.z)/max(.001,math.hypot(b.x-a.x,b.y-a.y));max_grade=max(max_grade,grade)
        if count==0 or max_grade>math.tan(math.radians(32)):raise ValueError('Parcours vide ou trop raide')
        return count,max_grade
    road_points,grade=road_surface();roads.location.z-=2;bpy.context.view_layer.update();roads_red=False
    try:road_surface()
    except ValueError:roads_red=True
    roads.location.z+=2;bpy.context.view_layer.update()
    if not roads_red:raise ValueError('Le contrôle accepte un chemin suspendu')
    result={'status':'valide','instances':len(report['instances']),'triangles':triangles,'textures_embarquees':len(images),'bannieres_animees':len(banners),'porte_traversante':True,'contre_epreuve_placement':red}
    result.update(cameras_verifiees=len(report['cameras']),contre_epreuve_focale=camera_red,
                  raccord_escalier_m=gap,contre_epreuve_escalier=stairs_red,
                  points_chemins_sur_maillage=road_points,pente_max_degres=math.degrees(math.atan(grade)),
                  contre_epreuve_chemin=roads_red,terrains_constructibles=len(report['plots']))
    (folder/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(result)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--nom',required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);verify(a.nom)
