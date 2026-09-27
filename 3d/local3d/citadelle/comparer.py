"""Vérifie la conservation des identités par rapport à l'état photographié avant retouche."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).parent/'sorties'
BEFORE=OUT/'diagnostic/avant'

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))

def compare():
    original=read(BEFORE/'catalogue.json')['assets']
    current=read(OUT/'bibliotheque/catalogue.json')['assets']
    ids={a['id'] for a in original};newids={a['id'] for a in current}
    if not ids or not ids<=newids:raise ValueError('Identifiants du kit perdus')
    sources=read(BEFORE/'sources-empreintes.json')
    if isinstance(sources,dict):sources=[sources]
    if not sources:raise ValueError('Échantillon de sources vide')
    for source in sources:
        if hashlib.sha256(Path(source['Path']).read_bytes()).hexdigest().upper()!=source['Hash']:
            raise ValueError('La source manuelle a été modifiée : '+source['Path'])
    prefabs=read(BEFORE/'prefabs-identites.json')
    if not prefabs:raise ValueError('Échantillon de prefabs vide')
    for prefab in prefabs:
        path=ROOT/'unity/Assets/ForgeLocal3D/Citadelle/Prefabs'/prefab['name']
        if path.read_text(encoding='utf-8').replace('\r\n','\n')!=prefab['contenu'].replace('\r\n','\n'):
            raise ValueError('Identité de prefab modifiée : '+prefab['name'])
    variants=[]
    for variant in read(Path(__file__).parent/'recette.json')['dispositions']:
        name=variant['id'];folder=OUT/'villages'/name
        before=read(BEFORE/name/(name+'.json'));after=read(folder/(name+'.json'))
        instances={i['id']:i for i in after['instances']}
        if not before['instances']:raise ValueError('Implantation initiale vide')
        migration=[]
        for item in before['instances']:
            current=instances.get(item['id'])
            if current is None:raise ValueError('Instance initiale perdue : '+item['id'])
            if current==item:continue
            changes={k for k in item if current[k]!=item[k]}
            reason=None
            if item['asset'].startswith('sapin_') and changes<={'position'}:
                reason='Raccord au relief sculpté et dégagement des accès'
            if item['asset'].startswith('maison_') and changes<={'position','rotation','scale'}:
                if not set(current)-set(item)<={'color','urban_group'} or not all(.45<s<1.4 for s in current['scale']):
                    raise ValueError('Transformation de maison hors enveloppe : '+item['id'])
                reason='Maison indépendante intégrée à un îlot mitoyen : largeur, hauteur, retrait et orientation'
            if item['asset']=='torche' and changes=={'position'}:
                reason='Torche rattachée à la façade déplacée'
            if item['asset'].startswith('falaise_') and abs(item['position'][0])<11 and item['position'][1]<-30 and changes=={'scale'}:
                if current['scale'][:2]==item['scale'][:2] and abs(current['scale'][2]-item['scale'][2]*.91)<1e-6:
                    reason='Dégagement du passage sous la porte'
            if reason is None:raise ValueError('Migration non prévue : '+item['id']+' '+str(changes))
            migration.append({'id':item['id'],'raison':reason,'avant':item,'apres':current})
        cameras={c['name']:c for c in after['cameras']}
        for camera in read(BEFORE/name/'inspection.json')['cameras']:
            c=cameras[camera['nom']]
            if c['position']!=camera['position'] or c['lens']!=camera['focale']:
                raise ValueError('Cadrage historique déplacé : '+camera['nom'])
        historical=[c['nom'] for c in read(BEFORE/name/'inspection.json')['cameras']]
        supplement=BEFORE/name/'cameras-complementaires.json'
        if supplement.exists():
            for c in read(supplement):
                if cameras[c['name']]!=c:raise ValueError('Caméra complémentaire déplacée : '+c['name'])
                historical.append(c['name'])
        for c in cameras:
            paths=[folder/'renders'/('blender_'+c.lower()+'.png')]
            if c in historical:paths.append(BEFORE/name/('blender_'+c.lower()+'.png'))
            for path in paths:
                if not path.is_file() or path.stat().st_size==0:raise ValueError('Comparaison manquante : '+str(path))
        (OUT/'diagnostic'/('migration_'+name+'.json')).write_text(json.dumps(migration,ensure_ascii=False,indent=2),encoding='utf-8')
        variants.append({'id':name,'instances_conservees':len(before['instances']),
                         'instances_ajoutees':len(instances)-len(before['instances']),
                         'triangles_avant':before['triangles_lod0'],'triangles_apres':after['triangles_lod0'],
                         'transformations_migrees':len(migration),'cadrages_compares':len(historical),'autres_angles':len(cameras)-len(historical)})
    result={'status':'valide','identifiants_conserves':len(ids),'modules_ajoutes':sorted(newids-ids),
            'sources_intactes':len(sources),'prefabs_identites_conservees':len(prefabs),'dispositions':variants}
    (OUT/'diagnostic/conservation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':compare()
