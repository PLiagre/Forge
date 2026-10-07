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
ACTIONS={'ForgeLocal3D.DesertBuilder.Build':'desert_build','ForgeLocal3D.DesertPlayCheck.Start':'desert_visite','ForgeLocal3D.DesertTraversalCheck.Start':'desert_parcours','ForgeLocal3D.DesertCityTerrain.Start':'desert_terrain','ForgeLocal3D.DesertCityRoads.Start':'desert_routes','ForgeLocal3D.DesertKit.Start':'desert_kit',
         'ForgeLocal3D.DesertCityRelance.Tracer':'desert_relance_tracer','ForgeLocal3D.DesertCityRelance.Relancer':'desert_relance','ForgeLocal3D.DesertCityRelance.Vierge':'desert_relance_vierge',
         'ForgeLocal3D.DesertCityBatiments.Poser':'desert_batiments_poser','ForgeLocal3D.DesertCityBatiments.Relancer':'desert_batiments_relance','ForgeLocal3D.DesertCityBatiments.Vierge':'desert_batiments_vierge'}
LOGS={'desert_build':'unity.log','desert_visite':'play.log','desert_parcours':'parcours.log','desert_terrain':'terrain.log','desert_routes':'routes.log','desert_kit':'kit.log',
      'desert_relance_tracer':'relance_tracer.log','desert_relance':'relance.log','desert_relance_vierge':'relance_vierge.log',
      'desert_batiments_poser':'batiments_poser.log','desert_batiments_relance':'batiments_relance.log','desert_batiments_vierge':'batiments_vierge.log'}


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


PORT_SERVICE=8000


def lancer_service(sourd=False):
    """Lot 293 : le service du monde sur 127.0.0.1:8000, à vitesse 0 (le contrôle fait passer les ticks).
    Sourd, le monde ignore toute intention (local3d/desert/routes.py). Rend le processus, prêt."""
    import socket
    import threading
    # Sous Windows, le service (SO_REUSEADDR) se lierait au port même déjà pris : on le vérifie avant.
    with socket.socket() as s:
        s.settimeout(1)
        if s.connect_ex(('127.0.0.1',PORT_SERVICE))==0:
            raise RuntimeError('Service du monde : le port '+str(PORT_SERVICE)+' est déjà pris par un autre processus.')
    commande=[sys.executable,str(CODE/'routes.py'),'--service-sourd'] if sourd else [sys.executable,'-m','sim.service']
    p=subprocess.Popen(commande+['--port',str(PORT_SERVICE),'--jours-par-seconde','0'],cwd=ROOT.parent/'jeu',
                       stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=dict(os.environ,PYTHONIOENCODING='utf-8'))
    attendue='service prêt sur 127.0.0.1:'+str(PORT_SERVICE);lignes=[];pret=threading.Event()
    def lire():
        # La sortie est lue jusqu'au bout : un tuyau plein bloquerait le service.
        for brute in p.stdout:
            ligne=brute.decode('utf-8',errors='replace').rstrip();lignes.append(ligne)
            if ligne==attendue:pret.set()
        pret.set()
    threading.Thread(target=lire,daemon=True).start()
    if pret.wait(120) and p.poll() is None and attendue in lignes:
        print('Service du monde{} prêt sur 127.0.0.1:{} (vitesse 0).'.format(' sourd' if sourd else '',PORT_SERVICE),flush=True)
        return p
    arreter_service(p)
    raise RuntimeError('Service du monde absent sur le port {} (déjà pris, ou service tombé). Fin de sa sortie :\n{}'.format(PORT_SERVICE,'\n'.join(lignes[-30:])))


def arreter_service(p):
    if p.poll() is None:
        p.terminate()
        try:p.wait(15)
        except subprocess.TimeoutExpired:p.kill();p.wait()


def routes(ds,sourd=False):
    """Lot 263 : Python écrit les gestes, Unity les pose et mesure, Python rejoue et juge.
    Lot 293 : les clics d'Unity passent par un vrai service du monde, lancé et arrêté ici."""
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
    service=lancer_service(sourd)
    try:run_unity('ForgeLocal3D.DesertCityRoads.Start')
    except RuntimeError as e:failure=e
    finally:arreter_service(service)
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
        c=j.get('camera') or {};b=c.get('balayage') or {};z=c.get('zoom') or {};m=c.get('marche') or {}
        if b and z and m:print('  caméra du joueur : {}/{} poses mesurées, {} sous le terrain, marge min {:.2f} m ; zoom de {:.1f} à {:.0f} m ; œil à {:.2f} m, marche à {:.2f} m du bout'.format(
            b['mesurees'],b['prevues'],b['sous_terrain'],b['marge_min'],z['distance_min'],z['distance_max'],c['oeil'],m.get('distance_fin',-1)),flush=True)
        for fault in j['defauts']:print('  défaut : '+fault,flush=True)
        faults+=len(j['defauts'])
    if failure:raise failure
    if faults:raise RuntimeError(str(faults)+' défauts : voir sorties/ville/<implantation>/routes/jugement.json')


RELANCE=(('tracer','ForgeLocal3D.DesertCityRelance.Tracer'),('relance','ForgeLocal3D.DesertCityRelance.Relancer'),('vierge','ForgeLocal3D.DesertCityRelance.Vierge'))


def relance(ds,service_neuf=True):
    """Lot 361 : Unity relancé redessine la même ville, d'après le seul plan du monde. Sur un service
    neuf, `tracer` trace deux routes et en dépose une trop raide ; `relance`, sur le même service, doit
    retrouver la même ville ; `vierge`, sur un service neuf, le sable vierge. Unity contrôle et juge.
    Sans service neuf (contre-épreuve), `vierge` joue sur le premier service et doit rougir."""
    from local3d.desert import routes as r, terrain as t
    d=ds[0]
    r.ecrire_gestes(d['id'],d['seed'])
    (t.SORTIES/'selection.json').write_text(json.dumps({'implantations':[d['id']]}),encoding='utf-8')
    rapports={s:t.SORTIES/d['id']/'relance'/(s+'.json') for s,_ in RELANCE}
    for p in rapports.values():p.unlink(missing_ok=True)
    if (ROOT/'unity/Temp/UnityLockfile').exists():
        raise RuntimeError('Unity est ouvert : enregistrer et fermer l’éditeur, puis relancer (le contrôle du relancement tourne en mode batch).')
    methodes=dict(RELANCE);echecs=[]
    def jouer(session):
        try:run_unity(methodes[session])
        except RuntimeError as e:echecs.append(session+' : '+str(e))
    service=lancer_service()
    try:
        jouer('tracer');jouer('relance')
        if not service_neuf:jouer('vierge')
    finally:arreter_service(service)
    if service_neuf:
        service=lancer_service()
        try:jouer('vierge')
        finally:arreter_service(service)
    manquants=[];defauts=0
    for s,p in rapports.items():
        if not p.exists():manquants.append(s);print(s+' : pas de rapport ('+str(p)+')',flush=True);continue
        j=json.loads(p.read_text(encoding='utf-8-sig'))
        essais=lambda liste:', '.join('{} {}'.format(e['identifiant'],'acceptée' if e['acceptee'] else 'refusée ('+e['motif']+')') for e in liste) or 'aucun'
        print('{} : tick d’ouverture {} ; ouverture : {} ; traces : {} ; plan : {} ; empreinte {} ; vierge {} ; {} défaut(s)'.format(
            s,j['tick_ouverture'],essais(j['ouverture']),essais(j['traces']),j['plan'],j['empreinte'],j['vierge'],len(j['defauts'])),flush=True)
        print('  parcelles : {} ; plan : {} ; pièces {} ; empreinte des parcelles {}'.format(*(', '.join('{} {}'.format(e['identifiant'],e['etat']) for e in j[c]) or 'aucune' for c in ('parcelles','parcelles_plan')),j['pieces_parcelles'],j['empreinte_parcelles']),flush=True)
        for fault in j['defauts']:print('  défaut : '+fault,flush=True)
        defauts+=len(j['defauts'])
    if manquants:raise RuntimeError('Unity n’a pas écrit de rapport pour : '+', '.join(manquants)+(' ('+' ; '.join(echecs)+')' if echecs else ''))
    if defauts:raise RuntimeError(str(defauts)+' défauts : voir sorties/ville/'+d['id']+'/relance/')
    if echecs:raise RuntimeError(' ; '.join(echecs))


BATIMENTS=(('poser','ForgeLocal3D.DesertCityBatiments.Poser'),('relance','ForgeLocal3D.DesertCityBatiments.Relancer'),('vierge','ForgeLocal3D.DesertCityBatiments.Vierge'))


def batiments(ds,service_neuf=True):
    """Lot 370 : les bâtiments de la capitale vivent dans le monde, pas dans Unity. Sur un service neuf,
    `poser` pose une maison, une scierie et un four et relève la ville rouverte à trois ticks ; `relance`,
    sur le même service, doit reposer les mêmes pièces aux mêmes places ; `vierge`, sur un service neuf,
    n'en poser aucune. Unity contrôle et juge. Sans service neuf (contre-épreuve), `vierge` joue sur le
    premier service et doit rougir."""
    from local3d.desert import routes as r, terrain as t
    d=ds[0]
    r.ecrire_gestes(d['id'],d['seed'])
    (t.SORTIES/'selection.json').write_text(json.dumps({'implantations':[d['id']]}),encoding='utf-8')
    dossier=t.SORTIES/d['id']/'batiments'
    for p in dossier.glob('*.json'):p.unlink()
    rapports={s:dossier/(s+'.json') for s,_ in BATIMENTS}
    if (ROOT/'unity/Temp/UnityLockfile').exists():
        raise RuntimeError('Unity est ouvert : enregistrer et fermer l’éditeur, puis relancer (le contrôle des bâtiments tourne en mode batch).')
    methodes=dict(BATIMENTS);echecs=[]
    def jouer(session):
        try:run_unity(methodes[session])
        except RuntimeError as e:echecs.append(session+' : '+str(e))
    service=lancer_service()
    try:
        jouer('poser');jouer('relance')
        if not service_neuf:jouer('vierge')
    finally:arreter_service(service)
    if service_neuf:
        service=lancer_service()
        try:jouer('vierge')
        finally:arreter_service(service)
    def releve(x):
        pieces=', '.join('{} {} {}/{} {}'.format(b['identifiant'],b['nature'],b['fourni'],b['requis'],b['dessinee']) for b in x['batiments']) or 'aucun bâtiment'
        return 'tick {} : {} ; pièces {} ; empreinte {}'.format(x['tick'],pieces,x['pieces'],x['empreinte'])
    manquants=[];defauts=0
    for s,p in rapports.items():
        if not p.exists():manquants.append(s);print(s+' : pas de rapport ('+str(p)+')',flush=True);continue
        j=json.loads(p.read_text(encoding='utf-8-sig'))
        print('{} : tick d’ouverture {} ; {} défaut(s)'.format(s,j['tick_ouverture'],len(j['defauts'])),flush=True)
        print('  ouverture, '+releve(j['ouverture']),flush=True)
        for x in j['ticks']:print('  '+releve(x),flush=True)
        if s=='poser':print('  séquence de la maison : '+(', '.join(j['sequence_maison']) or 'aucune'),flush=True)
        for fault in j['defauts']:print('  défaut : '+fault,flush=True)
        defauts+=len(j['defauts'])
    if manquants:raise RuntimeError('Unity n’a pas écrit de rapport pour : '+', '.join(manquants)+(' ('+' ; '.join(echecs)+')' if echecs else ''))
    if defauts:raise RuntimeError(str(defauts)+' défauts : voir sorties/ville/'+d['id']+'/batiments/')
    if echecs:raise RuntimeError(' ; '.join(echecs))


def proteges():
    """Ce que la commande `kit` ne doit pas toucher, relevé sur le disque par glob."""
    from local3d.desert import kit
    nouveaux=set(kit.NOUVEAUX)
    # Lot 270 : toute scène du projet, en plus de celles du ksar ; une scène apparue est un défaut.
    chemins=sorted(set((UNITY_ROOT/'Scenes').glob('*.unity'))|set((ROOT/'unity/Assets').glob('**/*.unity')))
    for dossier,motif in (('Prefabs','*.prefab'),('Models','*.fbx'),('Materials','*.mat')):
        chemins+=[p for p in sorted((UNITY_ROOT/dossier).glob(motif)) if p.stem not in nouveaux]
    for motif in ('*/*.json','*/*.fbx'):chemins+=sorted((OUT/'villages').glob(motif))
    return chemins


def empreintes():
    """SHA-256 des fichiers protégés."""
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in proteges()}


PLANCHES=('ateliers','chantiers')
# Le cadrage du banc. `inspecter_kit.py` recule sa caméra d'après la largeur de la famille, ce qui
# coupe les bouts d'une planche large comme celle des six étapes. Le banc ne change pas le script :
# il le lance par ce relais, qui, juste avant chaque rendu, recule la caméra sans la tourner jusqu'à
# ce que toutes les enveloppes entrent dans le cadre, avec une marge.
CADRAGE='''import runpy
from pathlib import Path
import bpy
from mathutils import Vector


@bpy.app.handlers.persistent
def cadrer(scene,*_):
    camera=scene.camera;bpy.context.view_layer.update()
    coins=[o.matrix_world@Vector(b) for o in scene.objects if o.type=='MESH' for b in o.bound_box]
    if not coins:return
    cadre,_=camera.camera_fit_coords(bpy.context.evaluated_depsgraph_get(),[v for c in coins for v in c])
    recul=camera.matrix_world.to_quaternion()@Vector((0,0,1));distance=(Vector(cadre)-sum(coins,Vector())/len(coins)).dot(recul)
    camera.location=Vector(cadre)+recul*distance*.1;camera.data.clip_end=distance*6


bpy.app.handlers.render_pre.append(cadrer)
runpy.run_path(str(Path(__file__).with_name('inspecter_kit.py')),run_name='__main__')
'''


def planche(noms):
    """SC8 : les planches des nouveaux modules, par `inspecter_kit.py` tel qu'il est.

    Il lit sa bibliothèque à côté de lui (`sorties/bibliotheque/Kit_Desert.blend`), où les
    nouveaux modules n'entrent qu'à la prochaine reconstruction complète, et ce fichier-là
    ne se touche pas. Il tourne donc dans un banc d'essai, sorties/cache/planche/ : une copie
    du script, et pour bibliothèque les LOD0 que `fabriquer.py kit` vient d'écrire
    (sorties/cache/kit_nouveaux.blend, chemins de textures absolus). Le banc est refait à
    chaque passage : chaque planche (`PLANCHES`) montre ce que `kit` vient de construire,
    jamais une ancienne, et entière (`CADRAGE`).
    """
    banc=OUT/'cache/planche';images={p:OUT/'diagnostic'/('kit_'+p+'.png') for p in PLANCHES}
    shutil.rmtree(banc,ignore_errors=True)
    for image in images.values():image.unlink(missing_ok=True)
    (banc/'sorties/bibliotheque').mkdir(parents=True)
    shutil.copy2(CODE/'inspecter_kit.py',banc/'inspecter_kit.py')
    (banc/'cadrer.py').write_text(CADRAGE,encoding='utf-8')
    shutil.copy2(OUT/'cache/kit_nouveaux.blend',banc/'sorties/bibliotheque/Kit_Desert.blend')
    blender([(banc/'cadrer.py').relative_to(CODE).as_posix()]+noms,'planche_ateliers.log')
    for p,image in images.items():
        rendu=banc/'sorties/diagnostic'/image.name
        if rendu.exists():image.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(rendu,image)


def ecart_image(path):
    """Variation spatiale des pixels d'une image (`kit.ecart_pixels`) ; -1 si elle manque."""
    if not path.exists():return -1.0
    import numpy as np
    from PIL import Image
    from local3d.desert import kit
    with Image.open(path) as image:return kit.ecart_pixels(np.asarray(image.convert('RGB')))


def pixels_image(path):
    """Lot 270 : les pixels RGB d'une image (hauteur × largeur × 3) ; None si elle manque."""
    if not path.exists():return None
    import numpy as np
    from PIL import Image
    with Image.open(path) as image:return np.array(image.convert('RGB'))


def verification_scenes(ds):
    """SC9 : rejoue `verifier` sur chaque disposition et rend son résultat, sans lever.

    Le vérificateur réécrit ses rapports (sorties/villages/*/verification.json, fins de ligne
    du système comprises, et verification-serie.json). Ils sont lus, puis chaque fichier
    protégé est remis octet pour octet dans l'état d'avant la vérification : ce qu'ont laissé
    Blender et Unity reste en place, et les empreintes après, relevées ensuite, le jugent.
    """
    serie=OUT/'verification-serie.json'
    gardes={p:p.read_bytes() for p in proteges()+[serie] if p.exists()}
    try:
        try:verify(ds);status,message='valide',''
        except (RuntimeError,ValueError,OSError,KeyError) as e:status,message='echec',str(e)[-600:]
        dispositions={}
        for d in ds:
            rapport=OUT/'villages'/d['id']/'verification.json'
            dispositions[d['id']]=json.loads(rapport.read_text(encoding='utf-8')).get('status') if rapport.exists() else None
    finally:
        for p in proteges()+[serie]:
            if p.exists() and p not in gardes:p.unlink()
        for p,octets in gardes.items():
            if not p.exists() or p.read_bytes()!=octets:p.write_bytes(octets)
    return {'status':status,'message':message,'dispositions':dispositions}


def kit_ateliers():
    """Lots 266 et 269 : ajoute les modules de kit.NOUVEAUX au kit, jusqu'aux prefabs d'Unity,
    fait mesurer par Unity les bâtiments finis de kit.REFERENCES, puis juge. Lot 270 : Unity
    photographie aussi les étapes de chantier (kit.rangees_planche), et Python juge la planche."""
    from local3d.desert import kit
    from local3d.desert.routes import ECART_CAPTURE
    # La garde passe avant tout effet : l'éditeur ouvert réimporterait sous nos pieds.
    if (ROOT/'unity/Temp/UnityLockfile').exists():
        raise RuntimeError('Unity est ouvert : enregistrer et fermer l’éditeur, puis relancer (l’ajout au kit tourne en mode batch).')
    dossier=OUT/'kit';dossier.mkdir(parents=True,exist_ok=True)
    avant=empreintes()
    catalogue_avant=json.loads((OUT/'bibliotheque/catalogue.json').read_text(encoding='utf-8'))
    print('Empreintes avant : {} fichiers ; {} anciens modules au catalogue.'.format(len(avant),sum(a['id'] not in kit.NOUVEAUX for a in catalogue_avant['assets'])),flush=True)
    if not any((OUT/'textures').glob('*.png')):
        print('Textures du kit.',flush=True);prepare(OUT/'textures')
    print('Blender : '+', '.join(kit.NOUVEAUX)+'.',flush=True)
    blender(['fabriquer.py','kit'],'kit_ateliers.log')
    planche(['scierie','four','chantier'])
    for sub in ('Models','Data'):(UNITY_ROOT/sub).mkdir(parents=True,exist_ok=True)
    for nom in kit.NOUVEAUX:shutil.copy2(OUT/'bibliotheque'/(nom+'.fbx'),UNITY_ROOT/'Models'/(nom+'.fbx'))
    shutil.copy2(OUT/'bibliotheque/catalogue.json',UNITY_ROOT/'Data/catalogue.json')
    # Les références : bâtiments finis des chantiers, mesurés par Unity sans être refaits.
    # Lot 270 : la planche, une rangée par chantier, qu'Unity photographie.
    (dossier/'selection.json').write_text(json.dumps({'modules':kit.NOUVEAUX,'references':kit.REFERENCES,'planche':kit.rangees_planche()},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (dossier/'unity-kit.json').unlink(missing_ok=True)
    # Une ancienne planche Unity ne compte jamais : seule celle de ce passage est relue.
    planche_unity=CODE/kit.PLANCHE_UNITY;planche_unity.unlink(missing_ok=True)
    print('Unity : prefabs et mesures.',flush=True)
    failure=None
    try:run_unity('ForgeLocal3D.DesertKit.Start',True)
    except RuntimeError as e:failure=e
    rapport=dossier/'unity-kit.json'
    if not rapport.exists():raise RuntimeError('Unity n’a pas écrit de rapport ('+str(failure or 'voir sorties/logs/kit.log')+')')
    print('Vérificateur des scènes : '+', '.join(d['id'] for d in RECIPE['dispositions'])+'.',flush=True)
    verification=verification_scenes(RECIPE['dispositions'])
    # Les empreintes après se relèvent une fois tous les effets de la commande passés, vérificateur compris.
    apres=empreintes()
    entrees={'plafonds':dict(kit.PLAFONDS),'catalogue_avant':catalogue_avant,
             'catalogue_apres':json.loads((OUT/'bibliotheque/catalogue.json').read_text(encoding='utf-8')),
             'unity':json.loads(rapport.read_text(encoding='utf-8-sig')),'empreintes_avant':avant,'empreintes_apres':apres,
             'ecart_image':ecart_image(OUT/'diagnostic/kit_ateliers.png'),'ecart_chantiers':ecart_image(OUT/'diagnostic/kit_chantiers.png'),
             'ecart_minimal':ECART_CAPTURE,'verification':verification,'planche':pixels_image(planche_unity)}
    j=kit.jugement(entrees)
    (dossier/'jugement.json').write_text(json.dumps(j,ensure_ascii=False,indent=1)+'\n',encoding='utf-8')
    print('{} : {} anciens modules intacts attendus, {} empreintes, planches à écart-type {:.1f} (ateliers) et {:.1f} (chantiers)'.format(
        j['status'],j['anciens_modules'],j['empreintes'],j['ecart_image'],j['ecart_chantiers']),flush=True)
    print('  verifier : {} ; {}'.format(verification['status'],', '.join('{} {}'.format(k,v) for k,v in verification['dispositions'].items())),flush=True)
    for m in j['modules']:
        print('  {:<32} LOD {} ; triangles {} (plafonds {}) ; y min {:.4f} m ; matériaux {}'.format(
            m['id'],m['niveaux'],m['triangles'],j['plafonds'].get(m['id']),m['y_min'],', '.join(m['materiaux'])),flush=True)
    # Pour chaque chantier : l'enveloppe et la hauteur de chaque étape, puis du bâtiment fini.
    mesures={m['id']:m for m in j['modules']+j['references']}
    for fini,etapes in j['chantiers'].items():
        print('  chantier '+fini+' :',flush=True)
        for e in etapes:
            m=mesures.get(e) or {}
            print('    {:<32} x {:.2f} à {:.2f} m ; z {:.2f} à {:.2f} m ; hauteur {:.2f} m'.format(
                e,*(m.get(k,-1) for k in ('x_min','x_max','z_min','z_max','y_max'))),flush=True)
    p=entrees['unity'].get('planche') or {}
    print('  planche Unity {} : {} × {} px, fond {}, scène « {} »'.format(
        p.get('chemin'),p.get('largeur'),p.get('hauteur'),p.get('fond'),p.get('scene_chemin')),flush=True)
    for c in j['planche']:
        print('    rangée {} colonne {} {:<32} {} renderers ; écart-type {:.1f}'.format(
            c['rangee'],c['colonne'],c['id'],c['renderers'],c['ecart']),flush=True)
    for nom,c in j['contre_epreuves'].items():
        print('  contre-épreuve {:<28} {} ({})'.format(nom,'rougit' if c['rougit'] else 'SANS EFFET',', '.join(c['obtenues']) or 'aucun défaut'),flush=True)
    for f in j['defauts']:print('  défaut [{}] {}'.format(f['etiquette'],f['message']),flush=True)
    if failure:raise failure
    if j['defauts']:raise RuntimeError(str(len(j['defauts']))+' défauts : voir sorties/kit/jugement.json')


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
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['fabriquer','unity','verifier','visite','parcours','edition','terrain','routes','kit','relance','batiments']);p.add_argument('--disposition');p.add_argument('--force',action='store_true');p.add_argument('--unity',action='store_true');p.add_argument('--asset');p.add_argument('--sans-rendus',action='store_true');p.add_argument('--service-sourd',action='store_true',help='routes : le monde ignore les intentions (contre-épreuve du lot 293)');p.add_argument('--sans-service-neuf',action='store_true',help='relance et batiments : la session vierge joue sur le premier service (contre-épreuves des lots 361 et 370)');a=p.parse_args()
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
    if a.action=='routes':routes(ds,a.service_sourd)
    if a.action=='kit':kit_ateliers()
    if a.action=='relance':relance(ds,not a.sans_service_neuf)
    if a.action=='batiments':batiments(ds,not a.sans_service_neuf)
