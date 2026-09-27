"""Atelier V2 : recettes, cache, génération, vérification et transfert Unity."""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from local3d.atelier_v2.plan import CONFIG, variant, make_plan, field, fingerprint
from local3d.atelier_v2.textures import prepare, terrain_texture

OUT=ROOT/'local3d/v2';CODE=ROOT/'local3d/atelier_v2'
BLENDER=r'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'
UNITY=r'C:\Program Files\Unity\Hub\Editor\6000.0.43f1\Editor\Unity.exe'

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temporary.replace(path)

def digest(paths,extra=None):
    h=hashlib.sha256()
    for p in sorted(paths):h.update(p.name.encode());h.update(p.read_bytes())
    if extra is not None:h.update(json.dumps(extra,sort_keys=True).encode())
    return h.hexdigest()

def cached(stamp,key,outputs):
    return stamp.exists() and json.loads(stamp.read_text())['key']==key and all(p.exists() and p.stat().st_size>0 for p in outputs)

def blender(args,log):
    log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('w',encoding='utf-8') as stream:
        result=subprocess.run([BLENDER,'--background','--python-exit-code','1','--python',str(CODE/args[0]),'--']+args[1:],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
    if result.returncode:
        print(log.read_text(encoding='utf-8')[-4000:]);raise RuntimeError(f'Blender a refusé la génération : {log}')

def library(force=False):
    folder=OUT/'textures';folder.mkdir(parents=True,exist_ok=True)
    # Les paramètres de peuplement ne modifient pas les modèles partagés.
    library_config={'styles':CONFIG['styles'],'foliage':sorted({k for v in CONFIG['variants'] for k in v['foliage']})}
    builder=(CODE/'fabriquer.py').read_text(encoding='utf-8').split('def build_library():',1)[1].split('def prepare_edit(',1)[0]
    key=digest([CODE/'assets.py',CODE/'geometrie.py',CODE/'textures.py']+list((ROOT/'local3d/sources_v2').glob('*.blend')),{'config':library_config,'builder':builder})
    stamp=OUT/'cache/assets.json';catalog=OUT/'bibliotheque/catalogue.json'
    if not force and cached(stamp,key,[catalog,OUT/'bibliotheque/Forge_Assets_V2.blend']):
        print('Bibliothèque inchangée : réutilisation.',flush=True);return
    print('Textures et bibliothèque : fabrication.',flush=True)
    prepare(folder)
    blender(['fabriquer.py','assets'],OUT/'logs/assets.log')
    write(stamp,{'key':key})

def build(names,quality,force):
    library(force)
    for name in names:
        v=variant(name);plan=make_plan(v);height=field(plan);folder=OUT/'villages'/name
        key=digest([CODE/'plan.py',CODE/'fabriquer.py',CODE/'textures.py',OUT/'bibliotheque/catalogue.json',OUT/'cache/assets.json'],{'variant':v,'quality':quality,'extent':CONFIG['extent_m'],'cells':CONFIG['terrain_cells'],'budget':CONFIG['budget_triangles']})
        stamp=OUT/'cache'/(name+'.json')
        outputs=[folder/(name+'.blend'),folder/'paysage.fbx',folder/'scene.json',folder/'renders/village.png',folder/'renders/territoire.png']
        if not force and cached(stamp,key,outputs):
            print(name+' : scène inchangée, réutilisation.',flush=True);continue
        print(name+' : relief, biomes, implantation et rendu.',flush=True)
        terrain_texture(plan,height,OUT/'textures'/('terrain_'+name+'_BaseColor.png'))
        blender(['fabriquer.py','scene','--variante',name,'--qualite',quality],OUT/'logs'/(name+'.log'))
        write(stamp,{'key':key,'quality':quality})
    gallery()

def gallery():
    cards=[]
    for v in CONFIG['variants']:
        p=OUT/'villages'/v['id']/'scene.json'
        if not p.exists():continue
        d=json.loads(p.read_text(encoding='utf-8'));name=v['id']
        cards.append(f'<article><a href="villages/{name}/renders/territoire.png"><img src="villages/{name}/renders/territoire.png"></a><div><small>{html.escape(v["biome"].upper())} / {html.escape(v["style"].upper())}</small><h2>{html.escape(v["label"])}</h2><p>{html.escape(v["subtitle"])}</p><p>{d["building_count"]} bâtiments · {d["tree_count"]} arbres · {d["triangles_lod0"]:,} triangles</p><a href="villages/{name}/{name}.blend">Scène Blender</a> · <a href="villages/{name}/renders/village.png">Détail du village</a></div></article>')
    document='''<!doctype html><html lang="fr"><meta charset="utf-8"><title>Forge — atlas des villages</title><style>body{margin:0;background:#18211d;color:#ede6d6;font:16px/1.6 system-ui}header,main{max-width:1440px;margin:auto;padding:42px}small{letter-spacing:.14em;color:#b8ba93}h1{font:normal 64px Georgia;margin:8px 0}h2{font:normal 32px Georgia;margin:8px 0}main{display:grid;grid-template-columns:1fr 1fr;gap:32px;padding-top:0}article{background:#242e27;border:1px solid #495043}img{width:100%;display:block}article div{padding:24px}a{color:#d7c193}p{color:#bfc2b5}@media(max-width:850px){main{grid-template-columns:1fr}h1{font-size:40px}}</style><header><small>FORGE / ATELIER 3D / V2</small><h1>Quatre façons d’habiter un paysage.</h1><p>Scènes de revue graphique, issues de recettes reproductibles. Architectures, eau et végétation propres à chaque lieu.</p></header><main>'''+''.join(cards)+'</main></html>'
    (OUT/'index.html').write_text(document,encoding='utf-8')
    # Planche de comparaison issue des rendus réels, avec les mesures des scènes.
    from PIL import Image, ImageDraw, ImageFont
    existing=[v for v in CONFIG['variants'] if (OUT/'villages'/v['id']/'renders/territoire.png').exists()]
    if not existing:return
    rows=(len(existing)+1)//2
    sheet=Image.new('RGB',(2080,180+rows*770),(24,33,29));draw=ImageDraw.Draw(sheet)
    def font(size):
        path=Path('C:/Windows/Fonts/segoeui.ttf')
        return ImageFont.truetype(str(path),size) if path.exists() else ImageFont.load_default(size=size)
    draw.text((48,30),'FORGE  /  ATLAS DES VILLAGES V2',font=font(46),fill='#eee5cf')
    draw.text((50,100),'Quatre biomes, quatre architectures — rendus des scènes Blender',font=font(27),fill='#b6bdab')
    for i,v in enumerate(existing):
        xx=40+(i%2)*1020;yy=176+(i//2)*770
        folder=OUT/'villages'/v['id'];scene=json.loads((folder/'scene.json').read_text(encoding='utf-8'))
        with Image.open(folder/'renders/territoire.png') as render:sheet.paste(render.resize((1000,656),Image.Resampling.LANCZOS),(xx,yy))
        draw.text((xx+10,yy+670),v['label'],font=font(33),fill='#eee5cf')
        draw.text((xx+10,yy+715),v['subtitle'],font=font(23),fill='#b6bdab')
    sheet.save(OUT/'atlas.png')

def verify(names):
    for name in names:
        print(name+' : réouverture et mesures.',flush=True)
        blender(['verifier.py','--variante',name],OUT/'logs'/('verification_'+name+'.log'))

def unity(names):
    dest=ROOT/'unity/Assets/ForgeLocal3D/V2'
    for sub in ('Models','Textures','Data','Landscapes'):(dest/sub).mkdir(parents=True,exist_ok=True)
    for p in (OUT/'bibliotheque').glob('*.fbx'):shutil.copy2(p,dest/'Models'/p.name)
    for p in (OUT/'textures').glob('*.png'):shutil.copy2(p,dest/'Textures'/p.name)
    shutil.copy2(OUT/'bibliotheque/catalogue.json',dest/'Data/catalogue.json')
    for name in names:
        src=OUT/'villages'/name
        shutil.copy2(src/'paysage.fbx',dest/'Landscapes'/(name+'.fbx'))
        shutil.copy2(src/'scene.json',dest/'Data'/(name+'.json'))
    write(dest/'Data/selection.json',{'variants':names})
    command=[UNITY,'-batchmode','-quit','-projectPath',str(ROOT/'unity'),'-executeMethod','ForgeLocal3D.VillageV2Builder.Build','-logFile',str(OUT/'logs/unity.log')]
    kwargs={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
    result=subprocess.run(command,cwd=ROOT,**kwargs)
    if result.returncode:raise RuntimeError('Import Unity refusé. Voir local3d/v2/logs/unity.log.')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['catalogue','assets','edition','fabriquer','verifier','unity','galerie'])
    p.add_argument('--asset',help='Identifiant de la bibliothèque, pour préparer une retouche Blender.')
    p.add_argument('--variante',default='toutes',choices=['toutes']+[v['id'] for v in CONFIG['variants']])
    p.add_argument('--qualite',choices=['apercu','final'],default='final')
    p.add_argument('--force',action='store_true')
    p.add_argument('--unity',action='store_true')
    a=p.parse_args();names=[v['id'] for v in CONFIG['variants']] if a.variante=='toutes' else [a.variante]
    if a.action=='catalogue':
        for v in CONFIG['variants']:print(v['id']+' — '+v['subtitle'])
    elif a.action=='assets':library(a.force)
    elif a.action=='edition':
        if not a.asset:p.error('edition demande --asset IDENTIFIANT')
        catalog=json.loads((OUT/'bibliotheque/catalogue.json').read_text(encoding='utf-8'))
        if a.asset not in {entry['id'] for entry in catalog['assets']}:p.error('Asset absent du catalogue : '+a.asset)
        destination=ROOT/'local3d/sources_v2'/(a.asset+'.blend')
        if destination.exists():print('Retouche conservée : '+str(destination))
        else:blender(['fabriquer.py','edition','--asset',a.asset],OUT/'logs/edition.log')
        print(str(destination))
    elif a.action=='fabriquer':
        build(names,a.qualite,a.force);verify(names)
        if a.unity:unity(names)
    elif a.action=='verifier':verify(names)
    elif a.action=='unity':unity(names)
    else:gallery()

if __name__=='__main__':main()
