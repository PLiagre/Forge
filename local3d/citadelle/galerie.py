"""Galerie locale des véritables rendus et de la capture Unity."""
import json
from pathlib import Path
import html
import re
import time
OUT=Path(__file__).parent/'sorties'
recipe=json.loads((Path(__file__).parent/'recette.json').read_text(encoding='utf-8'))
catalogue=json.loads((OUT/'bibliotheque/catalogue.json').read_text(encoding='utf-8'))
cards=[]
plans=[]
for d in recipe['dispositions']:
    r=json.loads((OUT/'villages'/d['id']/(d['id']+'.json')).read_text(encoding='utf-8'))
    cards.append(f'<article><img loading="lazy" src="villages/{r["id"]}/renders/blender_citadelle.png" alt="{html.escape(r["label"])}"><div><h3>{html.escape(r["label"])}</h3><p>{r["building_count"]} maisons · {r["tree_count"]} sapins · graine {r["seed"]}</p><a href="villages/{r["id"]}/{r["id"]}.blend">Ouvrir le fichier Blender</a></div></article>')
    def xy(p):return ((p[0]+200)*3, (55-p[1])*3)
    elements=['<rect width="780" height="650" fill="#17232a"/>']
    elements.append('<ellipse cx="600" cy="165" rx="158" ry="132" fill="#39454b" stroke="#81929b"/>')
    for i in r['instances']:
        if i['asset'].startswith('maison_'):
            x,y=xy(i['position']);kind=int(i['asset'][-1]);w=6*i['scale'][0]*3;depth=6*i['scale'][1]*3
            elements.append(f'<rect x="{x-w/2:.1f}" y="{y-depth/2:.1f}" width="{w:.1f}" height="{depth:.1f}" transform="rotate({-i["rotation"]:.1f} {x:.1f} {y:.1f})" fill="#889294" stroke="#28343a" stroke-width="1"><title>{i["id"]}</title></rect>')
    for route in r.get('routes',[]):
        points=' '.join(f'{xy(p["position"])[0]:.1f},{xy(p["position"])[1]:.1f}' for p in route['points'])
        color='#c7ab80' if route['id']=='lisiere_bois' or route['id'].startswith('acces') else '#d5d4c7'
        elements.append(f'<polyline points="{points}" stroke="{color}" stroke-width="{route["width"]*3}" fill="none" stroke-linejoin="round"><title>{route["id"].replace("_"," ")}</title></polyline>')
    for plot in r.get('plots',[]):
        x,y=xy(plot['position']);w,h=plot['size'];elements.append(f'<rect x="{x-w*1.5}" y="{y-h*1.5}" width="{w*3}" height="{h*3}" fill="#405c4d" stroke="#b8c79b"/><text x="{x}" y="{y+5}" text-anchor="middle" fill="#eef0cf" font-size="14">{plot["id"][-1]}</text>')
    if 'forest' in r:
        x,y=xy(r['forest']);elements.append(f'<circle cx="{x}" cy="{y}" r="20" fill="#406d58"/><text x="{x+30}" y="{y+5}" fill="#d9e5d5" font-size="16">Forêt</text>')
    elements.append('<text x="550" y="170" fill="#e0dfd7" font-size="18">Citadelle</text><path d="M600 600h150" stroke="#e0dfd7" stroke-width="3"/><text x="655" y="627" fill="#b9c2c5" font-size="15">50 m</text>')
    plans.append('<svg role="img" aria-label="Plan des accès, du village et des terrains" viewBox="0 0 780 650" xmlns="http://www.w3.org/2000/svg">'+''.join(elements)+'</svg>')
    (OUT/'parcours').mkdir(exist_ok=True)
    (OUT/'parcours'/('plan_'+r['id']+'.svg')).write_text(plans[-1],encoding='utf-8')
assets=''.join(f'<li><span>{html.escape(a["id"])}</span><small>{a["triangles"][0]:,} triangles</small></li>' for a in catalogue['assets'])
text='''<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Forge · Citadelle alpine</title>
<style>*{box-sizing:border-box}body{margin:0;background:#10151c;color:#e9e6df;font:16px/1.6 system-ui}main{max-width:1440px;margin:auto;padding:45px 38px}a{color:#e6b877}header{display:flex;justify-content:space-between;align-items:center;gap:30px;border-bottom:1px solid #35404b;padding-bottom:24px}h1{font:52px/1.05 Georgia,serif;margin:12px 0}h2{font:35px Georgia,serif;margin-top:60px}h3{font:27px Georgia,serif;margin:0}p{color:#aeb9c3}.eyebrow{letter-spacing:.22em;font-size:12px;color:#d7b37d}.badge{border:1px solid #5c5142;padding:12px 20px;border-radius:30px;color:#d7b37d}img,video{width:100%;display:block;background:#0a1018;border-radius:6px}.hero{margin-top:28px}.caption{font-size:13px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:26px}article{border:1px solid #303b46;border-radius:7px;overflow:hidden}article div{padding:24px}button{background:#1a2632;color:#ded8cc;border:1px solid #52606c;padding:10px 20px;margin:0 8px 16px 0;border-radius:4px;cursor:pointer}button.active{background:#c8a572;color:#14191e}ul{list-style:none;padding:0;display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:#303b46}li{padding:12px;background:#141c25;display:flex;justify-content:space-between;gap:12px;font-size:12px}small{color:#91a0ab;white-space:nowrap}footer{border-top:1px solid #303b46;margin-top:60px;padding-top:18px;color:#92a0ac;font-size:13px}@media(max-width:800px){main{padding:22px}h1{font-size:37px}header{display:block}.badge{display:inline-block}.grid,ul{grid-template-columns:1fr}}</style>
<main><header><div><div class="eyebrow">FORGE / ATELIER 3D</div><h1>La citadelle dans la neige</h1><p>Gothique alpin · Pierre sombre · Feux chauds · Ciel de tempête</p></div><div class="badge">31 modules réutilisables</div></header>
<img class="hero" src="villages/eperon_des_veilleurs/renders/blender_citadelle.png" alt="Vue de la citadelle fabriquée dans Blender"><p class="caption">Rendu de la scène Blender. La cathédrale, les maisons, les remparts et le paysage sont des maillages 3D.</p>
<h2>Entrer dans la citadelle</h2><video controls loop playsinline preload="metadata" poster="visite/neige.png" src="visite/citadelle.mp4"></video><p class="caption">Capture réelle de Unity · 8 secondes · Neige, bannières, feux et fumées animés.</p>
<h2>Une même scène, plusieurs ambiances</h2><div id="moods"><button class="active" data-image="neige">Neige et vent</button><button data-image="eclaircie">Éclaircie froide</button><button data-image="nuit">Nuit</button><button data-image="brume">Brouillard</button></div><img id="weather" src="visite/neige.png" alt="Ambiance de la scène dans Unity">
<h2>Deux implantations, une bibliothèque</h2><p>Même biome, même typologie, même culture et même année. Les maisons et la végétation changent de place à partir de la graine.</p><div class="grid">CARDS</div>
<h2>Au pied des remparts</h2><div class="grid"><img loading="lazy" src="villages/eperon_des_veilleurs/renders/blender_porte.png" alt="Porte et tours"><img loading="lazy" src="villages/eperon_des_veilleurs/renders/blender_cathedrale.png" alt="Détails de la cathédrale"></div>
<h2>Les pièces de l'atelier</h2><p>Modules en mètres, trois niveaux de détail, matériaux partagés, sources Blender et exports FBX. Les retouches manuelles restent prioritaires à la reconstruction.</p><ul>ASSETS</ul><p><a href="../README.md">Lire le workflow de fabrication et de retouche</a></p>
<footer>Étude artistique gothique imaginaire, inspirée de la référence fournie. Les gardes sont des silhouettes statiques. Cette scène n'est pas encore reliée à une photographie du moteur historique.</footer></main>
<script>document.querySelectorAll('[data-image]').forEach(b=>b.onclick=()=>{document.getElementById('weather').src='visite/'+b.dataset.image+'.png';document.querySelectorAll('[data-image]').forEach(x=>x.classList.toggle('active',x===b));});</script></html>'''.replace('CARDS',''.join(cards)).replace('ASSETS',assets)
comparison='''
<section aria-labelledby="titre-comparaison"><h2 id="titre-comparaison">Le même regard, avant et après</h2>
<p>Caméras et focales identiques. Faites glisser le curseur pour examiner la géométrie, les surfaces et la lumière.</p>
<div class="choix"><label>Implantation <select id="lieu"><option value="eperon_des_veilleurs">Éperon des Veilleurs</option><option value="col_des_cendres">Col des Cendres</option></select></label>
<label>Caméra <select id="camera"><option value="citadelle">Vue générale</option><option value="porte">Porte</option><option value="cathedrale">Cathédrale</option><option value="passage">Sur le pont · hauteur humaine</option><option value="parvis">Parvis · hauteur humaine</option></select></label></div>
<div class="comparateur"><img id="apres" src="villages/eperon_des_veilleurs/renders/blender_citadelle.png" alt="Scène après amélioration"><img id="avant" src="diagnostic/avant/eperon_des_veilleurs/blender_citadelle.png" alt="Même caméra avant amélioration"><span class="etiquette gauche">AVANT</span><span class="etiquette droite">APRÈS</span><i id="limite"></i></div>
<label class="curseur">Répartition avant / après <input id="partage" type="range" min="0" max="100" value="50" aria-label="Part de l'image avant retouche"></label>
<p class="caption"><a href="../DIAGNOSTIC.md">Lire le diagnostic et les modifications</a> · Les vues rapprochées font partie de la reconstruction.</p></section>
<style>.choix{display:flex;gap:24px;margin:22px 0;flex-wrap:wrap}.choix label{font-size:13px;color:#b5c2cc}select{display:block;margin-top:8px;background:#19232d;color:#f1ece4;border:1px solid #51616e;border-radius:4px;padding:12px;min-width:245px}.comparateur{position:relative;aspect-ratio:16/9;overflow:hidden;border:1px solid #51616e;border-radius:6px}.comparateur img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}.comparateur #avant{clip-path:inset(0 50% 0 0)}.etiquette{position:absolute;top:18px;background:#10151cbb;color:#fff;padding:5px 12px;letter-spacing:.15em;font-size:11px}.gauche{left:18px}.droite{right:18px}#limite{position:absolute;left:50%;top:0;height:100%;border-left:2px solid #dab984}.curseur{display:flex;align-items:center;gap:20px;font-size:13px;margin:18px 0}.curseur input{flex:1;accent-color:#dab984}</style>
<script>(()=>{const partage=document.getElementById('partage'),avant=document.getElementById('avant'),apres=document.getElementById('apres');partage.oninput=()=>{avant.style.clipPath='inset(0 '+(100-partage.value)+'% 0 0)';document.getElementById('limite').style.left=partage.value+'%';};const actualiser=()=>{const lieu=document.getElementById('lieu').value,cam=document.getElementById('camera').value;avant.src='diagnostic/avant/'+lieu+'/blender_'+cam+'.png';apres.src='villages/'+lieu+'/renders/blender_'+cam+'.png';};document.getElementById('lieu').onchange=actualiser;document.getElementById('camera').onchange=actualiser;})();</script>
'''
text=text.replace('31 modules réutilisables',str(len(catalogue['assets']))+' modules réutilisables')
comparison=comparison.replace('diagnostic/avant/','diagnostic/habitat-modulaire/avant/').replace('blender_','unity_')
comparison=comparison.replace('examiner la géométrie, les surfaces et la lumière','comparer les nouvelles habitations modulaires, leurs colombages, galeries et couvertures')
comparison=comparison.replace('<option value="parvis">Parvis · hauteur humaine</option>', '<option value="parvis">Parvis · hauteur humaine</option><option value="vallee">Vallée et accès</option><option value="contrechamp">Arrière de la citadelle</option><option value="village">Rue du village</option><option value="foret">Lisière forestière</option>')
comparison=comparison.replace('<option value="foret">Lisière forestière</option>','<option value="foret">Lisière forestière</option><option value="ilots">Maisons mitoyennes</option>')
text=text.replace('<h2>Entrer dans la citadelle</h2>',comparison+'<h2>Entrer dans la citadelle</h2>')
exploration='''<section id="habitat"><h2>Descendre au village, rejoindre la forêt</h2>
<p>Le pont rejoint une descente en lacets, les rues du village et le sentier forestier. Quatre clairières de 13 × 12 m réservent des emplacements pour construire.</p>
<div class="choix"><label>Implantation <select id="angle-lieu"><option value="eperon_des_veilleurs">Éperon des Veilleurs</option><option value="col_des_cendres">Col des Cendres</option></select></label><label>Autre angle <select id="angle"><option value="vallee">Le village et la descente</option><option value="contrechamp">Derrière la citadelle</option><option value="village">Dans la rue</option><option value="foret">À la lisière</option></select></label></div>
<img id="exploration" src="villages/eperon_des_veilleurs/renders/blender_vallee.png" alt="Vue des accès dans la vallée">
<div class="grid" style="margin-top:26px"><article>PLAN<div><h3>Un réseau continu</h3><p>Les lignes représentent les profils exportés dans Unity. Les zones numérotées sont les clairières disponibles.</p></div></article><article><img src="parcours/Forge_Citadelle_eperon_des_veilleurs_foret_apres_abattage.png" alt="Essai d'abattage dans la scène Unity"><div><h3>Marcher et approcher les troncs</h3><p>Dans Unity : <b>Tab</b> pour marcher, <b>ZQSD / flèches</b> pour avancer, clic droit pour regarder et <b>E</b> près d'un sapin pour l'abattre.</p><p>L'abattage est un essai local, réinitialisé au chargement. Les clairières restent libres ; le système de construction n'est pas implémenté.</p><a href="parcours/verification.json">Lire la vérification des parcours</a></div></article></div>
</section><script>(()=>{const update=()=>{const lieu=document.getElementById('angle-lieu').value;document.getElementById('exploration').src='villages/'+lieu+'/renders/blender_'+document.getElementById('angle').value+'.png';document.getElementById('plan-implantation').src='parcours/plan_'+lieu+'.svg';};document.getElementById('angle').onchange=update;document.getElementById('angle-lieu').onchange=update;})();</script>'''.replace('PLAN','<img id="plan-implantation" src="parcours/plan_eperon_des_veilleurs.svg" alt="Plan des maisons indépendantes, des ruelles et des terrains">')
text=text.replace('<h2>Entrer dans la citadelle</h2>',exploration+'<h2>Entrer dans la citadelle</h2>')
text=text.replace('<option value="vallee">Le village et la descente</option>','<option value="ilots">Maisons et ruelles</option><option value="vallee">Le village et la descente</option>')
text=text.replace('id="exploration" src="villages/eperon_des_veilleurs/renders/blender_vallee.png"','id="exploration" src="villages/eperon_des_veilleurs/renders/blender_ilots.png"')
text=text.replace('<h2>Descendre au village, rejoindre la forêt</h2>','<h2>Des maisons mitoyennes, des ruelles irrégulières</h2><p>Façades décalées, hauteurs variables, petits appentis et toitures imbriquées. Chaque maison conserve son objet et son prefab.</p>')
text=text.replace('La citadelle dans la neige','La citadelle et ses ruelles')
# Les ajouts du pack existent dans Unity ; leurs captures ne décrivent pas Blender.
terrain_cards=[]
for d in recipe['dispositions']:
    folder=OUT/'villages'/d['id']
    report=folder/'terrain-sample-verification.json'
    if not report.exists():continue
    sample=json.loads(report.read_text(encoding='utf-8'))
    if sample.get('vegetation',-1)<0:continue
    terrain_cards.append(f'<article><img loading="lazy" src="villages/{d["id"]}/renders/unity_vallee.png" alt="Terrain adapté ”” {html.escape(d["label"])}"><div><h3>{html.escape(d["label"])}</h3><p>{sample.get("arbres_remplaces", 0)} conifères du pack · {sample["vegetation"]} touffes et buissons · {sample.get("rochers_parois", 0)} blocs dans les parois</p><a href="villages/{d["id"]}/renders/unity_foret.png">Entrer dans la forêt</a> · <a href="villages/{d["id"]}/renders/unity_roche.png">Voir la roche</a></div></article>')
if terrain_cards:
    section='<h2>Le terrain, la roche et la lande</h2><p>Terrain Sample Project de Unity, adapté au rendu URP et à l’hiver de la citadelle. Roche, terre et gravier se mêlent à la neige. Cinq bois denses remplacent les arbres dispersés ; les aiguilles portent une neige permanente. Les chemins et les clairières restent libres.</p><div class="grid">'+''.join(terrain_cards)+'</div>'
    text=text.replace('<h2>Des maisons mitoyennes, des ruelles irrégulières</h2>',section+'<h2>Des maisons mitoyennes, des ruelles irrégulières</h2>')
# Toutes les vues proposées par défaut montrent les assets réellement présents dans Unity.
text=text.replace('/renders/blender_', '/renders/unity_')
text=text.replace('Vue de la citadelle fabriquée dans Blender','Citadelle dans Unity ”” conifères et parois rocheuses')
text=text.replace('Rendu de la scène Blender. La cathédrale, les maisons, les remparts et le paysage sont des maillages 3D.',
                  'Capture actuelle de Unity. Les maisons du village et de la citadelle sont assemblées avec le même kit que le chantier jouable : pierre, colombages crème ou brique, ardoise et tuile.')
text=text.replace('La citadelle et ses ruelles','La citadelle, la forêt et la roche')
forge_cards=[]
for d in recipe['dispositions']:
    path=OUT/'villages'/d['id']/'renders/unity_forge.png'
    if path.exists():
        forge_cards.append(f'<article><img loading="lazy" src="villages/{d["id"]}/renders/unity_forge.png" alt="Forge Blacksmith"><div><h3>Blacksmith · {html.escape(d["label"])}</h3><p>Forge du pack 3DForge, matériaux adaptés et assise en pierre.</p></div></article>')
if forge_cards:
    text=text.replace('<h2>Deux implantations, une bibliothèque</h2>','<h2>La forge du hameau</h2><div class="grid">'+''.join(forge_cards)+'</div><p>PB Frontier Settlement : intégration des bâtiments suspendue, car les maillages de murs et de toits manquent dans le pack importé.</p><h2>Deux implantations, une bibliothèque</h2>')
performance=OUT/'performance/performance.json'
if performance.exists() and all(performance.stat().st_mtime > (OUT/'villages'/d['id']/'unity-verification.json').stat().st_mtime for d in recipe['dispositions']):
    perf=json.loads(performance.read_text(encoding='utf-8'))
    if perf.get('images_non_vides'):
        worst=max(m['p95_ms'] for m in perf['mesures'])
        state='Objectif 60 i/s tenu sur les vues mesurées' if perf['objectif_60'] else 'Objectif 60 i/s non atteint sur toutes les vues'
        text=text.replace('<h2>Deux implantations, une bibliothèque</h2>',f'<h2>Performance mesurée</h2><p>{state}. {html.escape(perf["gpu"])} · {perf["largeur"]} × {perf["hauteur"]}, rendu interne à {perf["echelle_rendu"]:.0%}. Pire 95e centile : {worst:.2f} ms. La visite reste plafonnée à 60 i/s.</p><p><a href="performance/performance.json">Rapport complet et protocole</a></p><h2>Deux implantations, une bibliothèque</h2>')
# Le catalogue et ses compteurs viennent des pièces réellement exportées.
habitat=json.loads((OUT/'bibliotheque/habitat.json').read_text(encoding='utf-8'))
habitat_cards=[]
for d in recipe['dispositions']:
    for image_name,label in [('habitat','Colombages dans la citadelle'),('ilots','Maisons du village')]:
        habitat_cards.append(f'<article><img loading="lazy" src="villages/{d["id"]}/renders/unity_{image_name}.png" alt="{label}"><div><h3>{label}</h3><p>{html.escape(d["label"])}</p></div></article>')
section=f'<h2>Construire dans le style de la référence</h2><p>{len(habitat["modules"])} modules, {len(habitat["maisons"])} maisons préassemblées. Soubassements en pierre, étages à colombages, toits pointus, coursives et escaliers extérieurs. Les façades utilisent la pierre, le bois, la brique et les enduits de Blacksmith.</p><div class="grid">'+''.join(habitat_cards)+'</div>'
section+='<h3>Un chantier jouable</h3><p>Lancer <a href="../../../Jouer_Citadelle.cmd">Jouer_Citadelle.cmd</a>, puis appuyer sur <strong>B</strong>. Choisir une des quatre clairières, une maison complète ou une pièce. Clic gauche pour poser, R pour tourner, boutons de hauteur pour empiler, Suppr pour retirer, Ctrl+Z pour annuler. La sauvegarde est automatique et distincte pour chaque scène. F8 montre les colombages de la citadelle.</p>'
construction=OUT/'construction/verification.json'
if construction.exists() and all(construction.stat().st_mtime>(OUT/'villages'/d['id']/'unity-verification.json').stat().st_mtime for d in recipe['dispositions']):
    section+='<div class="grid"><img loading="lazy" src="construction/chantier_0.png" alt="Chantier jouable et deux maisons assemblées"><img loading="lazy" src="construction/chantier_1.png" alt="Chantier dans la deuxième disposition"></div><p><a href="construction/verification.json">Contrôle du placement, des appuis, de la sauvegarde et des escaliers</a></p>'
text=text.replace('<h2>Entrer dans la citadelle</h2>',section+'<h2>Entrer dans la citadelle</h2>')
# Une preuve ancienne reste consultable, mais ne certifie pas une reconstruction
# plus récente. Le message disparaît lorsque les commandes de contrôle sont rejouées.
scene_date=max(max((OUT/'villages'/d['id']/(d['id']+'.blend')).stat().st_mtime, (OUT/'villages'/d['id']/'unity-verification.json').stat().st_mtime) for d in recipe['dispositions'])
def outdated(path):return not path.exists() or path.stat().st_mtime<scene_date
if outdated(OUT/'visite/verification-play.json'):
    text=text.replace('<h2>Entrer dans la citadelle</h2>','<h2>Entrer dans la citadelle</h2><p class="caption">Cette vidéo et les ambiances Unity ci-dessous précèdent la dernière retouche. Leur nouvelle capture reste à exécuter dans Unity.</p>')
if outdated(OUT/'parcours/verification.json'):
    text=text.replace('<h3>Marcher et approcher les troncs</h3>','<h3>Marcher et approcher les troncs</h3><p class="caption">Le parcours a été contrôlé avant la dernière retouche des accotements. Sa vérification complète doit être rejouée.</p>')
# Les noms des captures restent stables pour le workflow, mais le navigateur
# doit relire leurs nouveaux pixels à chaque génération de la galerie.
revision=str(time.time_ns())
text=re.sub(r'((?:src|poster)="[^"\n]+\.(?:png|svg|mp4))"',lambda m:m[1]+'?v='+revision+'"',text)
for suffix in ('png','svg'):
    text=text.replace("'."+suffix+"'","'."+suffix+'?v='+revision+"'")
(OUT/'index.html').write_text(text,encoding='utf-8')
print(OUT/'index.html')
