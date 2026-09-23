"""Construction, import et vérification du kit gothique alpin."""
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
from local3d.citadelle.textures import prepare
from local3d.atelier_alpin import BLENDER,UNITY,key
CODE=ROOT/'local3d/citadelle';OUT=CODE/'sorties'
RECIPE=json.loads((CODE/'recette.json').read_text(encoding='utf-8'))

def blender(args,log):
    (OUT/'logs').mkdir(parents=True,exist_ok=True)
    with (OUT/'logs'/log).open('w',encoding='utf-8') as f:
        r=subprocess.run([BLENDER,'-b','--python-exit-code','1','--python',str(CODE/args[0]),'--']+args[1:],stdout=f,stderr=subprocess.STDOUT,cwd=ROOT)
    if r.returncode:raise RuntimeError((OUT/'logs'/log).read_text(encoding='utf-8')[-3000:])

def build(ds,force=False,no_render=False):
    (OUT/'cache').mkdir(parents=True,exist_ok=True)
    files=[CODE/name for name in ('assets.py','habitat.py','marche.py','textures.py','fabriquer.py','paysage.py','urbanisme.py','cameras.py','recette.json')]+[ROOT/'local3d/atelier_v2/geometrie.py',ROOT/'local3d/atelier_v2/textures.py']+sorted((CODE/'sources').glob('*.blend'))
    digest=key(files);stamp=OUT/'cache/construction.txt'
    if force or not stamp.exists() or stamp.read_text()!=digest or not (OUT/'bibliotheque/Kit_Citadelle.blend').exists():
        prepare(OUT/'textures');blender(['fabriquer.py','assets'],'kit.log');stamp.write_text(digest)
    for d in ds:
        stamp=OUT/'cache'/(d['id']+'.txt');folder=OUT/'villages'/d['id']
        if not force and stamp.exists() and stamp.read_text()==digest and all((folder/p).exists() for p in (d['id']+'.blend',d['id']+'.json','renders/blender_cathedrale.png')):
            print(d['id']+' : bibliothèque et scène réutilisées.',flush=True);continue
        print(d['id']+' : construction du relief, des accès et des cadrages fixes.',flush=True)
        blender(['fabriquer.py','scene','--nom',d['id'],'--graine',str(d['seed'])]+(['--sans-rendus'] if no_render else []),d['id']+'.log')
        if not no_render:stamp.write_text(digest)

def unity(ds):
    dest=ROOT/'unity/Assets/ForgeLocal3D/Citadelle'
    for sub in ('Models','Textures','Data','Landscapes'):(dest/sub).mkdir(parents=True,exist_ok=True)
    for f in (OUT/'bibliotheque').glob('*.fbx'):shutil.copy2(f,dest/'Models'/f.name)
    for f in (OUT/'textures').glob('*.png'):shutil.copy2(f,dest/'Textures'/f.name)
    shutil.copy2(OUT/'bibliotheque/catalogue.json',dest/'Data/catalogue.json')
    shutil.copy2(OUT/'bibliotheque/habitat.json',dest/'Data/habitat.json')
    for d in ds:
        folder=OUT/'villages'/d['id']
        shutil.copy2(folder/(d['id']+'.json'),dest/'Data'/(d['id']+'.json'));shutil.copy2(folder/(d['id']+'.fbx'),dest/'Landscapes'/(d['id']+'.fbx'))
    (dest/'Data/selection.json').write_text(json.dumps({'variants':[d['id'] for d in ds]}),encoding='utf-8')
    run_unity('ForgeLocal3D.CitadelBuilder.Build','unity.log',True)

def prepare_terrain_sample():
    # Les scripts de visite HDRP exigent Visual Scripting. Les maillages et
    # textures sont autonomes ; le tutoriel reste disponible sur activation explicite.
    folders=('Vendor/TerrainDemoScene_HDRP', 'TerrainDemoScene_HDRP')
    if all((ROOT/'unity/Assets'/folder).is_dir() for folder in folders):
        raise RuntimeError('Terrain Sample importé deux fois : conserver une seule copie du pack dans Assets.')
    for folder in folders:
        scripts=ROOT/'unity/Assets'/folder/'Scripts'
        if not scripts.is_dir():continue
        assembly=scripts/'Forge.TerrainSample.Tutoriel.asmdef'
        content=json.dumps({'name':'Forge.TerrainSample.Tutoriel','includePlatforms':['Editor'],
                            'defineConstraints':['FORGE_TERRAIN_SAMPLE_TUTORIEL']},indent=2)+'\n'
        if not assembly.exists() or assembly.read_text(encoding='utf-8')!=content:
            assembly.write_text(content,encoding='utf-8')


def run_unity(method,log,quit=False):
    prepare_terrain_sample()
    if (ROOT/'unity/Temp/UnityLockfile').exists():
        return run_open_editor(method)
    args=[UNITY,'-batchmode','-projectPath',str(ROOT/'unity'),'-executeMethod',method,'-logFile',str(OUT/'logs'/log)]
    if quit:args.append('-quit')
    r=subprocess.run(args,cwd=ROOT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    if r.returncode:raise RuntimeError('Unity : voir '+str(OUT/'logs'/log))


def run_open_editor(method):
    actions={'ForgeLocal3D.CitadelBuilder.Build':'build','ForgeLocal3D.CitadelPlayCheck.Start':'visite','ForgeLocal3D.CitadelTraversalCheck.Start':'parcours','ForgeLocal3D.CitadelQuality.BuildPlayer':'joueur','ForgeLocal3D.CitadelDecor.CaptureBuildings':'batiments'}
    action=actions[method];folder=ROOT/'unity/Library/ForgeCitadelle';folder.mkdir(parents=True,exist_ok=True)
    request=folder/'request.json';identity=uuid.uuid4().hex
    if request.exists():raise RuntimeError('Une opération attend déjà dans Unity : '+str(request))
    temporary=folder/'request.tmp';temporary.write_text(json.dumps({'id':identity,'action':action}),encoding='utf-8');temporary.replace(request)
    start=time.monotonic();deadline=start+600;last=None
    try:
        while time.monotonic()<deadline:
            if not (ROOT/'unity/Temp/UnityLockfile').exists() and request.exists():
                request.unlink()
                return run_unity(method,{'build':'unity.log','visite':'play.log','parcours':'parcours.log','joueur':'joueur.log','batiments':'forge-vues.log'}[action],action in ('build','joueur','batiments'))
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
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['fabriquer','unity','verifier','visite','parcours','edition','joueur','performance','construction']);p.add_argument('--disposition');p.add_argument('--force',action='store_true');p.add_argument('--unity',action='store_true');p.add_argument('--asset');p.add_argument('--sans-rendus',action='store_true');a=p.parse_args()
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
        run_unity('ForgeLocal3D.CitadelPlayCheck.Start','play.log')
        r=subprocess.run(['ffmpeg','-y','-framerate','24','-i',str(OUT/'visite/frames/image_%04d.png'),'-c:v','libx264','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/'visite/citadelle.mp4')],capture_output=True)
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace')[-2000:])
    if a.action=='parcours':run_unity('ForgeLocal3D.CitadelTraversalCheck.Start','parcours.log')

    if a.action in ('joueur','performance','construction'):
        run_unity('ForgeLocal3D.CitadelQuality.BuildPlayer','joueur.log',True)
    if a.action=='performance':
        folder=OUT/'performance';folder.mkdir(parents=True,exist_ok=True)
        started=time.time_ns()
        result=subprocess.run([str(OUT/'joueur/Citadelle.exe'),'-forge-benchmark','-forge-output',str(folder),
                               '-screen-width','1920','-screen-height','1080','-screen-fullscreen','0',
                               '-logFile',str(folder/'joueur.log')],cwd=ROOT)
        if result.returncode:raise RuntimeError('Mesure rejetée : consulter sorties/performance/erreur.txt et joueur.log')
        report=folder/'performance.json'
        if not report.exists() or report.stat().st_mtime_ns<started:
            raise RuntimeError('Le joueur s’est fermé avant la fin de la mesure ; aucun rapport actuel.')
        print(report)

    if a.action=='construction':
        folder=OUT/'construction';folder.mkdir(parents=True,exist_ok=True)
        started=time.time_ns()
        result=subprocess.run([str(OUT/'joueur/Citadelle.exe'),'-forge-construction-check','-forge-output',str(folder),
                               '-screen-width','1920','-screen-height','1080','-screen-fullscreen','0',
                               '-logFile',str(folder/'joueur.log')],cwd=ROOT)
        if result.returncode:raise RuntimeError('Chantier refusé : consulter sorties/construction/erreur.txt et joueur.log')
        report=folder/'verification.json'
        if not report.exists() or report.stat().st_mtime_ns<started:
            raise RuntimeError('Le joueur s’est fermé avant la fin du contrôle de construction.')
        print(report)
