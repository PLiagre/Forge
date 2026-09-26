"""Fabriquer le même village alpin avec plusieurs graines, puis le visiter."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from local3d.alpin.paysage import RECIPE,make_plan,field
from local3d.alpin.textures import palette,terrain
from local3d.atelier_v2.plan import fingerprint
CODE=ROOT/'local3d/alpin';OUT=CODE/'sorties'
BLENDER=r'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'
UNITY=r'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'

def run_blender(arguments,log):
    log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('w',encoding='utf-8') as stream:
        result=subprocess.run([BLENDER,'-b','--python-exit-code','1','--python',str(CODE/arguments[0]),'--']+arguments[1:],stdout=stream,stderr=subprocess.STDOUT,cwd=ROOT)
    if result.returncode:raise RuntimeError(log.read_text(encoding='utf-8')[-3500:])

def key(paths,extra=None):
    h=hashlib.sha256()
    for p in sorted(paths):h.update(p.name.encode());h.update(p.read_bytes())
    h.update(json.dumps(extra,sort_keys=True).encode());return h.hexdigest()

def build(dispositions,force):
    (OUT/'textures').mkdir(parents=True,exist_ok=True);(OUT/'cache').mkdir(exist_ok=True)
    files=[CODE/'assets.py',CODE/'textures.py',CODE/'fabriquer.py',ROOT/'local3d/atelier_v2/assets.py',ROOT/'local3d/atelier_v2/geometrie.py']
    stamp=OUT/'cache/kit.txt'
    library_source=(CODE/'fabriquer.py').read_text(encoding='utf-8').split('def scene(',1)[0]
    digest=key([p for p in files if p.name!='fabriquer.py']+list((CODE/'sources').glob('*.blend')),library_source)
    if force or not stamp.exists() or stamp.read_text()!=digest or not (OUT/'bibliotheque/Kit_Alpin.blend').exists():
        print('Kit alpin : modèles et matières.',flush=True);palette(OUT/'textures');run_blender(['fabriquer.py','assets'],OUT/'logs/kit.log');stamp.write_text(digest)
    else:print('Kit alpin inchangé : réutilisé.',flush=True)
    for d in dispositions:
        name=d['id'];plan=make_plan(d['seed']);height=field(plan);stamp=OUT/'cache'/(name+'.txt')
        digest=key(files+[CODE/'paysage.py',OUT/'bibliotheque/catalogue.json',OUT/'cache/kit.txt'],{'plan':plan,'recipe':RECIPE})
        folder=OUT/'villages'/name
        outputs=[folder/(name+'.blend'),folder/'scene.json',folder/'paysage.fbx',folder/'renders/moulin.png']
        if not force and stamp.exists() and stamp.read_text()==digest and all(p.exists() for p in outputs):print(name+' : scène inchangée.',flush=True);continue
        print(name+' : implantation, paysage et rendus.',flush=True)
        terrain(plan,height,OUT/'textures'/('terrain_'+name+'_BaseColor.png'))
        run_blender(['fabriquer.py','scene','--nom',name,'--seed',str(d['seed'])],OUT/'logs'/(name+'.log'));stamp.write_text(digest)

def unity(dispositions):
    dest=ROOT/'unity/Assets/ForgeLocal3D/Alpin'
    for sub in ('Models','Textures','Data','Landscapes'):(dest/sub).mkdir(parents=True,exist_ok=True)
    cat=json.loads((OUT/'bibliotheque/catalogue.json').read_text(encoding='utf-8'));textures={m['texture'] for m in cat['materials']}
    for a in cat['assets']:shutil.copy2(OUT/'bibliotheque'/(a['id']+'.fbx'),dest/'Models'/(a['id']+'.fbx'))
    shutil.copy2(OUT/'bibliotheque/catalogue.json',dest/'Data/catalogue.json')
    for d in dispositions:
        name=d['id'];src=OUT/'villages'/name
        shutil.copy2(src/'scene.json',dest/'Data'/(name+'.json'));shutil.copy2(src/'paysage.fbx',dest/'Landscapes'/(name+'.fbx'))
        textures.update(m['texture'] for m in json.loads((src/'scene.json').read_text(encoding='utf-8'))['materials'])
    for name in textures:
        for p in (OUT/'textures').glob(name+'_*.png'):shutil.copy2(p,dest/'Textures'/p.name)
    (dest/'Data/selection.json').write_text(json.dumps({'variants':[d['id'] for d in dispositions]}),encoding='utf-8')
    kwargs={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
    result=subprocess.run([UNITY,'-batchmode','-quit','-projectPath',str(ROOT/'unity'),'-executeMethod','ForgeLocal3D.AlpineBuilder.Build','-logFile',str(OUT/'logs/unity.log')],cwd=ROOT,**kwargs)
    if result.returncode:raise RuntimeError('Unity a refusé la scène. Voir '+str(OUT/'logs/unity.log'))

def verify(dispositions):
    for d in dispositions:run_blender(['verifier.py','--nom',d['id']],OUT/'logs'/('verification_'+d['id']+'.log'))
    reports=[json.loads((OUT/'villages'/d['id']/'scene.json').read_text(encoding='utf-8')) for d in dispositions]
    if len(reports)>1:
        if len({r['catalogue_sha256'] for r in reports})!=1:raise ValueError('Bibliothèques différentes entre les dispositions')
        # Comparer les placements visibles, en excluant la graine et les métadonnées.
        # Une graine différente inscrite sur une scène identique ne suffit pas.
        layouts=[fingerprint([{'asset':i['asset'],'position':i['position'],'rotation':i['rotation']} for i in r['instances'] if i['category']=='01']) for r in reports]
        if len(set(layouts))!=len(reports):raise ValueError('Deux implantations visibles sont identiques')
        reliefs=[hashlib.sha256((OUT/'villages'/r['id']/'hauteurs.npy').read_bytes()).hexdigest() for r in reports]
        if len(set(reliefs))!=len(reports):raise ValueError('Deux reliefs sont identiques')
        for field in ('biome','typologie','annee','culture'):
            if any(r[field]!=RECIPE[field] for r in reports):raise ValueError('Contexte différent : '+field)
        shared=set.intersection(*[{i['asset'] for i in r['instances']} for r in reports])
        if not shared:raise ValueError('Aucun asset partagé entre les dispositions')
        (OUT/'verification-serie.json').write_text(json.dumps({'status':'valide','dispositions':[r['id'] for r in reports],
            'contexte_commun':{k:RECIPE[k] for k in ('biome','typologie','annee','culture')},'assets_utilises_en_commun':len(shared),
            'implantations_distinctes':len(set(layouts)),'reliefs_distincts':len(set(reliefs)),'catalogues':1},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Vérifié : scènes distinctes, bibliothèque commune.',flush=True)

def play():
    kwargs={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
    result=subprocess.run([UNITY,'-batchmode','-projectPath',str(ROOT/'unity'),'-executeMethod','ForgeLocal3D.AlpinePlayCheck.Start','-logFile',str(OUT/'logs/play.log')],cwd=ROOT,**kwargs)
    if result.returncode:raise RuntimeError('Visite refusée : '+str(OUT/'logs/play.log'))
    result=subprocess.run(['ffmpeg','-y','-framerate','24','-i',str(OUT/'visite/frames/image_%04d.png'),'-c:v','libx264','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/'visite/visite_alpine.mp4')],capture_output=True)
    if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-2000:])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['fabriquer','unity','verifier','visite','edition']);p.add_argument('--disposition',default='toutes',choices=['toutes']+[d['id'] for d in RECIPE['dispositions']]);p.add_argument('--graine',type=int);p.add_argument('--unity',action='store_true');p.add_argument('--force',action='store_true');p.add_argument('--asset')
    a=p.parse_args();ds=RECIPE['dispositions'] if a.disposition=='toutes' else [d for d in RECIPE['dispositions'] if d['id']==a.disposition]
    if a.graine is not None:ds=[{'id':'alpin_'+str(a.graine),'label':'Village alpin '+str(a.graine),'seed':a.graine}]
    if a.action=='fabriquer':build(ds,a.force);verify(ds)
    if a.action=='verifier':verify(ds)
    if a.action=='unity' or a.unity:unity(ds)
    if a.action=='visite':play()
    if a.action=='edition':
        if not a.asset:p.error('edition demande --asset IDENTIFIANT')
        catalogue=json.loads((OUT/'bibliotheque/catalogue.json').read_text(encoding='utf-8'))
        if a.asset not in {x['id'] for x in catalogue['assets']}:p.error('Asset inconnu')
        destination=CODE/'sources'/(a.asset+'.blend')
        if not destination.exists():run_blender(['fabriquer.py','edition','--nom',a.asset],OUT/'logs/edition.log')
        print(destination)
