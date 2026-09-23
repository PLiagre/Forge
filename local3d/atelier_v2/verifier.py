"""Contrôle les scènes sauvegardées et la conservation géométrique du FBX."""
import argparse
import json
import sys
from pathlib import Path
import bpy
import numpy as np

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from local3d.atelier_v2.plan import CONFIG, make_plan, variant, fingerprint
from local3d.atelier_v2.geometrie import tri_count

def check_positions(expected,actual):
    if not expected:raise ValueError('Échantillon vide')
    for item in expected:
        if item['id'] not in actual:raise ValueError('Instance absente : '+item['id'])
        delta=max(abs(a-b) for a,b in zip(item['position'],actual[item['id']]))
        if delta>.0002:raise ValueError('Position divergente : '+item['id'])

def verify(name):
    out=ROOT/'local3d/v2/villages'/name
    report=json.loads((out/'scene.json').read_text(encoding='utf-8'))
    plan=json.loads((out/'plan.json').read_text(encoding='utf-8'))
    if fingerprint(plan)!=fingerprint(make_plan(variant(name))):raise ValueError('Plan non reproductible')
    bpy.ops.wm.open_mainfile(filepath=str(out/(name+'.blend')))
    actual={o.name:tuple(o.location) for o in bpy.context.scene.objects if 'asset_id' in o}
    # Contre-épreuve en mémoire : un déplacement doit être refusé.
    corrupted=dict(actual);first=report['instances'][0]['id'];v=corrupted[first]
    corrupted[first]=(v[0]+1,v[1],v[2])
    rejected=False
    try:check_positions(report['instances'],corrupted)
    except ValueError:rejected=True
    if not rejected:raise ValueError('Le contrôle accepte une scène déplacée')
    check_positions(report['instances'],actual)
    if len(actual)!=len(report['instances']):raise ValueError('Instances supplémentaires ou perdues')
    live=[o for c in bpy.context.scene.collection.children if not c.name.startswith('05') for o in c.objects if o.type=='MESH']
    count=sum(tri_count(o) for o in live)
    if not 0<count==report['triangles_lod0']<=CONFIG['budget_triangles']:raise ValueError('Budget ou géométrie incohérent')
    images={n.image for o in live for s in o.material_slots if s.material for n in s.material.node_tree.nodes if n.type=='TEX_IMAGE' and n.image}
    if not images or not all(i.packed_file for i in images):raise ValueError('Textures non embarquées')
    if any(not np.isfinite(np.asarray(o.matrix_world)).all() for o in live):raise ValueError('Transformation non finie')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(out/'paysage.fbx'))
    imported=[o for o in bpy.context.scene.objects if o.type=='MESH']
    total=sum(tri_count(o) for o in imported)
    if not imported or total!=report['static_triangles']:raise ValueError('Géométrie perdue à l’export du paysage')
    if any(not s.material for o in imported for s in o.material_slots):raise ValueError('Matériau absent dans le paysage')
    result={'scene':name,'plan_deterministe':True,'contre_epreuve_deplacement':'refusée comme attendu',
        'instances':len(actual),'triangles':count,'textures_embarquees':len(images),'paysage_fbx_triangles':total,'status':'valide'}
    (out/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('VERIFICATION_OK '+json.dumps(result),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--variante',required=True)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);verify(a.variante)
