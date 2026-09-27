"""Construction, import et vérification du ksar du désert."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from local3d.desert.textures import prepare
from local3d.atelier_alpin import BLENDER,UNITY,key
from local3d.atelier_citadelle import prepare_terrain_sample
CODE=ROOT/'local3d/desert';OUT=CODE/'sorties'
RECIPE=json.loads((CODE/'recette.json').read_text(encoding='utf-8'))
UNITY_ROOT=ROOT/'unity/Assets/ForgeLocal3D/Desert'
ACTIONS={'ForgeLocal3D.DesertBuilder.Build':'desert_build','ForgeLocal3D.DesertPlayCheck.Start':'desert_visite','ForgeLocal3D.DesertTraversalCheck.Start':'desert_parcours','ForgeLocal3D.DesertCityTerrain.Start':'desert_terrain','ForgeLocal3D.DesertCityRoads.Start':'desert_routes'}
LOGS={'desert_build':'unity.log','desert_visite':'play.log','desert_parcours':'parcours.log','desert_terrain':'terrain.log','desert_routes':'routes.log'}


def blender(args,log):
    (OUT/'logs').mkdir(parents=True,exist_ok=True)
    with (OUT/'logs'/log).open('w',encoding='utf-8') as f:
        r=subprocess.run([BLENDER,'-b','--python-exit-code','1','--python',str(CODE/args[0]),'--']+args[1:],stdout=f,stderr=subprocess.STDOUT,cwd=ROOT)
    if r.returncode:raise RuntimeError((OUT/'logs'/log).read_text(encoding='utf-8')[-3000:])


def build(ds,force=False,no_render=False):
    (OUT/'cache').mkdir(parents=True,exist_ok=True)
    files=[CODE/name for name in ('assets.py','textures.py','fabriquer.py','paysage.py','urbanisme.py','cameras.py','recette.json')]
    files+=[ROOT/'local3d/atelier_v2/geometrie.py',ROOT/'local3d/atelier_v2/textures.py',ROOT/'local3d/citadelle/urbanisme.py',ROOT/'local3d/citadelle/paysage.py']
    files+=sorted((CODE/'sources').glob('*.blend'))
    digest=key(files);stamp=OUT/'cache/construction.txt'
    if force or not stamp.exists() or stamp.read_text()!=digest or not (OUT/'bibliotheque/Kit_Desert.blend').exists():
        print('Kit du désert : textures et modules.',flush=True)
        prepare(OUT/'textures');blender(['fabriquer.py','assets'],'kit.log');stamp.write_text(digest)
    for d in ds:
        stamp=OUT/'cache'/(d['id']+'.txt');folder=OUT/'villages'/d['id']
        if not force and stamp.exists() and stamp.read_text()==digest and all((folder/p).exists() for p in (d['id']+'.blend',d['id']+'.json','renders/blender_mosquee.png')):
            print(d['id']+' : bibliothèque et scène réutilisées.',flush=True);continue
        print(d['id']+' : relief, palmeraie, accès et cadrages fixes.',flush=True)
        blender(['fabriquer.py','scene','--nom',d['id'],'--graine',str(d['seed'])]+(['--sans-rendus'] if no_render else []),d['id']+'.log')
        if not no_render:stamp.write_text(digest)


def unity(ds):
    for sub in ('Models','Textures','Data','Landscapes'):(UNITY_ROOT/sub).mkdir(parents=True,exist_ok=True)
    for f in (OUT/'bibliotheque').glob('*.fbx'):shutil.copy2(f,UNITY_ROOT/'Models'/f.name)
    for f in (OUT/'textures').glob('*.png'):shutil.copy2(f,UNITY_ROOT/'Textures'/f.name)
    shutil.copy2(OUT/'bibliotheque/catalogue.json',UNITY_ROOT/'Data/catalogue.json')
    for d in ds:
        folder=OUT/'villages'/d['id']
        shutil.copy2(folder/(d['id']+'.json'),UNITY_ROOT/'Data'/(d['id']+'.json'));shutil.copy2(folder/(d['id']+'.fbx'),UNITY_ROOT/'Landscapes'/(d['id']+'.fbx'))
    (UNITY_ROOT/'Data/selection.json').write_text(json.dumps({'variants':[d['id'] for d in ds]}),encoding='utf-8')
    run_unity('ForgeLocal3D.DesertBuilder.Build',True)


def run_unity(method,quit=False):
    prepare_terrain_sample()
    action=ACTIONS[method];log=OUT/'logs'/LOGS[action];log.parent.mkdir(parents=True,exist_ok=True)
    if (ROOT/'unity/Temp/UnityLockfile').exists():
        return run_open_editor(method)
    args=[UNITY,'-batchmode','-projectPath',str(ROOT/'unity'),'-executeMethod',method,'-logFile',str(log)]
    if quit:args.append('-quit')
    r=subprocess.run(args,cwd=ROOT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    if r.returncode:raise RuntimeError('Unity : voir '+str(log))


def run_open_editor(method):
    # Même boîte aux lettres que la citadelle : l'éditeur ouvert exécute une seule opération à la fois.
    action=ACTIONS[method];folder=ROOT/'unity/Library/ForgeCitadelle';folder.mkdir(parents=True,exist_ok=True)
    request=folder/'request.json';identity=uuid.uuid4().hex
    if request.exists():raise RuntimeError('Une opération attend déjà dans Unity : '+str(request))
    temporary=folder/'request.tmp';temporary.write_text(json.dumps({'id':identity,'action':action}),encoding='utf-8');temporary.replace(request)
    start=time.monotonic();deadline=start+900;last=None
    try:
        while time.monotonic()<deadline:
            if not (ROOT/'unity/Temp/UnityLockfile').exists() and request.exists():
                request.unlink()
                return run_unity(method,action=='desert_build')
            response=folder/'response.json'
            if response.exists():
                try:r=json.loads(response.read_text(encoding='utf-8-sig'))
                except (OSError,ValueError):time.sleep(.5);continue
                if r.get('id')==identity:
                    if r['status']!=last:print(r['message'],flush=True);last=r['status']
                    if r['status']=='termine':return
                    if r['status']=='echec':raise RuntimeError(r['message'])
            if last is None and time.monotonic()-start>90:
                raise RuntimeError('L’éditeur ouvert ne répond pas : revenir dans Unity et lancer Assets → Refresh, ou fermer Unity après enregistrement.')
            time.sleep(1)
        raise RuntimeError('Unity n’a pas terminé : vérifier la compilation et les scènes non enregistrées dans l’éditeur.')
    finally:
        if request.exists() and json.loads(request.read_text(encoding='utf-8'))['id']==identity:request.unlink()


def terrain(ds,force=False):
    """Étape 1 de la ville : Unity Terrain tiré de paysage.field, puis contrôle dans Unity."""
    from local3d.desert import terrain as t
    files=[CODE/name for name in ('paysage.py','urbanisme.py','terrain.py')]+[ROOT/'local3d/citadelle/paysage.py']
    for d in ds:
        folder=t.SORTIES/d['id'];stamp=folder/'empreinte.txt'
        digest=key(files,{'graine':d['seed']})
        if force or not stamp.exists() or stamp.read_text()!=digest or not (folder/'terrain.json').exists():
            print(d['id']+' : échantillonnage de paysage.field (une à deux minutes).',flush=True)
            r=t.exporter(d['id'],d['seed']);stamp.write_text(digest)
            print('  écart propre à la grille : médiane {mediane:.4f} m, 95e centile {p95:.4f} m, max {max:.3f} m'.format(**r['ecart_grille']),flush=True)
        else:print(d['id']+' : grille réutilisée.',flush=True)
        (folder/'unity-terrain.json').unlink(missing_ok=True)
    (t.SORTIES/'selection.json').write_text(json.dumps({'implantations':[d['id'] for d in ds]}),encoding='utf-8')
    failure=None
    try:run_unity('ForgeLocal3D.DesertCityTerrain.Start')
    except RuntimeError as e:failure=e
    for d in ds:
        path=t.SORTIES/d['id']/'unity-terrain.json'
        if not path.exists():raise RuntimeError(d['id']+' : Unity n’a pas écrit de rapport ('+str(failure or 'voir sorties/logs/terrain.log')+')')
        r=json.loads(path.read_text(encoding='utf-8'))
        print('{} : {} — {} points dont {} marchables ; écart au rendu : médiane {:.4f} m, 95e centile {:.4f} m, max {:.3f} m ; sol marchable max {:.3f} m'.format(
            d['id'],r['status'],r['points'],r['points_marchables'],r['ecart_rendu']['mediane'],r['ecart_rendu']['p95'],r['ecart_rendu']['max'],r['ecart_marchable_max']),flush=True)
        for fault in r['defauts']:print('  défaut : '+fault,flush=True)
    if failure:raise failure


def routes(ds):
    """Lot 263 : Python écrit les gestes, Unity les pose et mesure, Python rejoue et juge."""
    from local3d.desert import routes as r, terrain as t
    for d in ds:
        donnees=r.ecrire_gestes(d['id'],d['seed'])
        familles={}
        for g in donnees['routes']:familles[g['famille']]=familles.get(g['famille'],0)+1
        print(d['id']+' : '+str(len(donnees['routes']))+' gestes — '+', '.join('{} {}'.format(n,f) for f,n in familles.items()),flush=True)
        (r.dossier(d['id'])/'unity-routes.json').unlink(missing_ok=True)
    (t.SORTIES/'selection.json').write_text(json.dumps({'implantations':[d['id'] for d in ds]}),encoding='utf-8')
    # La boîte aux lettres de l'éditeur ouvert (CitadelEditorBridge) ne connaît pas encore ce contrôle.
    if (ROOT/'unity/Temp/UnityLockfile').exists():
        raise RuntimeError('Unity est ouvert : enregistrer et fermer l’éditeur, puis relancer (le contrôle des routes tourne en mode batch).')
    failure=None
    try:run_unity('ForgeLocal3D.DesertCityRoads.Start')
    except RuntimeError as e:failure=e
    faults=0
    for d in ds:
        if not (r.dossier(d['id'])/'unity-routes.json').exists():
            raise RuntimeError(d['id']+' : Unity n’a pas écrit de rapport ('+str(failure or 'voir sorties/logs/routes.log')+')')
        j=r.juger(d['id'])
        posees=[x for x in j['routes'] if x['decision']=='acceptee']
        print('{} : {} — {} routes posées sur {}, grille à {:.4f} m de la référence, talus max {:.1%}, {} coupes'.format(
            d['id'],j['status'],len(posees),len(j['routes']),j['grille']['ecart_reference_max'],j['grille']['talus_max'],j['grille']['coupes']),flush=True)
        for x in j['routes']:
            axe=x.get('axe',{})
            print('  {:<30} {:<13} {:<9} {}'.format(x['id'],x['famille'],x['decision'],
                  'écart au profil max {:.4f} m, marche à {:.2f} m du bout'.format(axe['max'],x['marche']['distance_fin']) if axe else ''),flush=True)
        for fault in j['defauts']:print('  défaut : '+fault,flush=True)
        faults+=len(j['defauts'])
    if failure:raise failure
    if faults:raise RuntimeError(str(faults)+' défauts : voir sorties/ville/<implantation>/routes/jugement.json')


def verify(ds):
    for d in ds:blender(['verifier.py','--nom',d['id']],'verification_'+d['id']+'.log')
    reports=[json.loads((OUT/'villages'/d['id']/(d['id']+'.json')).read_text(encoding='utf-8')) for d in ds]
    if len({r['catalogue_sha256'] for r in reports})!=1:raise ValueError('Les scènes ne partagent pas le catalogue')
    for k in ('biome','typologie','annee','culture'):
        if len({r[k] for r in reports})!=1:raise ValueError('Contexte divergent')
    signatures=[hashlib.sha256(json.dumps([i for i in r['instances'] if i['asset'].startswith('maison_')],sort_keys=True).encode()).hexdigest() for r in reports]
    if len(set(signatures))!=len(reports):raise ValueError('Implantations identiques')
    shared=set.intersection(*[{i['asset'] for i in r['instances']} for r in reports])
    if not shared:raise ValueError('Aucun asset réutilisé')
    (OUT/'verification-serie.json').write_text(json.dumps({'status':'valide','dispositions':len(reports),'catalogues':1,'assets_partages':len(shared),'contextes':1},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Scènes rouvertes et contrôlées ; bibliothèque commune.',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['fabriquer','unity','verifier','visite','parcours','edition','terrain','routes']);p.add_argument('--disposition');p.add_argument('--force',action='store_true');p.add_argument('--unity',action='store_true');p.add_argument('--asset');p.add_argument('--sans-rendus',action='store_true');a=p.parse_args()
    ds=[d for d in RECIPE['dispositions'] if not a.disposition or d['id']==a.disposition]
    if not ds:p.error('Disposition inconnue')
    if a.action=='fabriquer':build(ds,a.force,a.sans_rendus);verify(ds)
    if a.action=='verifier':verify(ds)
    if a.action=='unity' or a.unity:unity(ds)
    if a.action=='edition':
        if not a.asset:p.error('edition demande --asset IDENTIFIANT')
        catalogue=json.loads((OUT/'bibliotheque/catalogue.json').read_text(encoding='utf-8'))
        if a.asset not in {x['id'] for x in catalogue['assets']}:p.error('Module inconnu')
        destination=CODE/'sources'/(a.asset+'.blend')
        if not destination.exists():blender(['fabriquer.py','edition','--nom',a.asset],'edition.log')
        print(destination)
    if a.action=='visite':
        run_unity('ForgeLocal3D.DesertPlayCheck.Start')
        r=subprocess.run(['ffmpeg','-y','-framerate','24','-i',str(OUT/'visite/frames/image_%04d.png'),'-c:v','libx264','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/'visite/desert.mp4')],capture_output=True)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-2000:])
    if a.action=='parcours':run_unity('ForgeLocal3D.DesertTraversalCheck.Start')
    if a.action=='terrain':terrain(ds,a.force)
    if a.action=='routes':routes(ds)
