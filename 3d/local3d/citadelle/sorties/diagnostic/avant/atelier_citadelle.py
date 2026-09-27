"""Construction, import et vérification du kit gothique alpin."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
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

def build(ds,force=False):
    (OUT/'cache').mkdir(parents=True,exist_ok=True)
    files=[CODE/name for name in ('assets.py','textures.py','fabriquer.py','recette.json')]+[ROOT/'local3d/atelier_v2/geometrie.py']+list((CODE/'sources').glob('*.blend'))
    digest=key(files);stamp=OUT/'cache/construction.txt'
    if force or not stamp.exists() or stamp.read_text()!=digest or not (OUT/'bibliotheque/Kit_Citadelle.blend').exists():
        prepare(OUT/'textures');blender(['fabriquer.py','assets'],'kit.log');stamp.write_text(digest)
    for d in ds:
        stamp=OUT/'cache'/(d['id']+'.txt');folder=OUT/'villages'/d['id']
        if not force and stamp.exists() and stamp.read_text()==digest and all((folder/p).exists() for p in (d['id']+'.blend',d['id']+'.json','renders/blender_cathedrale.png')):
            print(d['id']+' : bibliothèque et scène réutilisées.',flush=True);continue
        print(d['id']+' : construction et trois rendus.',flush=True)
        blender(['fabriquer.py','scene','--nom',d['id'],'--graine',str(d['seed'])],d['id']+'.log');stamp.write_text(digest)

def unity(ds):
    dest=ROOT/'unity/Assets/ForgeLocal3D/Citadelle'
    for sub in ('Models','Textures','Data','Landscapes'):(dest/sub).mkdir(parents=True,exist_ok=True)
    for f in (OUT/'bibliotheque').glob('*.fbx'):shutil.copy2(f,dest/'Models'/f.name)
    for f in (OUT/'textures').glob('*.png'):shutil.copy2(f,dest/'Textures'/f.name)
    shutil.copy2(OUT/'bibliotheque/catalogue.json',dest/'Data/catalogue.json')
    for d in ds:
        folder=OUT/'villages'/d['id']
        shutil.copy2(folder/(d['id']+'.json'),dest/'Data'/(d['id']+'.json'));shutil.copy2(folder/(d['id']+'.fbx'),dest/'Landscapes'/(d['id']+'.fbx'))
    (dest/'Data/selection.json').write_text(json.dumps({'variants':[d['id'] for d in ds]}),encoding='utf-8')
    run_unity('ForgeLocal3D.CitadelBuilder.Build','unity.log',True)

def run_unity(method,log,quit=False):
    args=[UNITY,'-batchmode','-projectPath',str(ROOT/'unity'),'-executeMethod',method,'-logFile',str(OUT/'logs'/log)]
    if quit:args.append('-quit')
    r=subprocess.run(args,cwd=ROOT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    if r.returncode:raise RuntimeError('Unity : voir '+str(OUT/'logs'/log))

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
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['fabriquer','unity','verifier','visite','edition']);p.add_argument('--disposition');p.add_argument('--force',action='store_true');p.add_argument('--unity',action='store_true');p.add_argument('--asset');a=p.parse_args()
    ds=[d for d in RECIPE['dispositions'] if not a.disposition or d['id']==a.disposition]
    if not ds:p.error('Disposition inconnue')
    if a.action=='fabriquer':build(ds,a.force);verify(ds)
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
