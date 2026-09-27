"""Galerie locale des rendus réels et planches de comparaison."""
import html,json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'sorties'
recipe=json.loads((ROOT/'recette.json').read_text(encoding='utf-8'))
cards=[]
for d in recipe['dispositions']:
    name=d['id'];r=json.loads((OUT/'villages'/name/'scene.json').read_text(encoding='utf-8'))
    cards.append(f'<article><a href="villages/{name}/renders/territoire.png"><img src="villages/{name}/renders/territoire.png"></a><div><small>DISPOSITION {d["seed"]}</small><h2>{html.escape(d["label"])}</h2><p>{r["building_count"]} bâtiments · {r["tree_count"]} arbres</p><a href="villages/{name}/{name}.blend">Ouvrir la source Blender</a> · <a href="villages/{name}/renders/moulin.png">Voir de près</a></div></article>')
states=[('clair','Éclaircies'),('soir','Soir'),('couvert','Couvert'),('brume','Brume'),('pluie','Pluie'),('neige','Neige')]
buttons=''.join(f'<button onclick="document.getElementById(\'meteo\').src=\'visite/{name}.png\'">{label}</button>' for name,label in states)
page='''<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Forge — le village alpin</title><style>body{margin:0;background:#18221f;color:#eee5d0;font:16px/1.6 system-ui}header,section{max-width:1440px;margin:auto;padding:40px}small{color:#b2baa2;letter-spacing:.16em}h1{font:normal 66px Georgia;margin:8px 0}h2{font:normal 32px Georgia;margin:8px 0}p{color:#bcc5b6}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}article{background:#263029;border:1px solid #475347}article div{padding:22px}img,video{width:100%;display:block}a{color:#dcc490}button{background:#354539;color:#eee5d0;border:1px solid #7a876b;padding:12px 25px;cursor:pointer;margin:8px 8px 15px 0}video{max-width:1100px;margin:auto}@media(max-width:850px){.grid{grid-template-columns:1fr}h1{font-size:44px}}</style><header><small>FORGE / ATELIER ALPIN</small><h1>Un lieu vivant. Plusieurs villages.</h1><p>Une bibliothèque réutilisable. Un biome, une culture, une époque. Trois façons de s'installer dans la vallée.</p></header><section><video controls loop muted poster="villages/combe_du_moulin/renders/moulin.png"><source src="visite/visite_alpine.mp4" type="video/mp4"></video><p>Visite enregistrée dans Unity : moulin, courant, vent, fumée, pluie et neige.</p></section><section><small>LA MÊME DISPOSITION, UNE AUTRE ATMOSPHÈRE</small><h2>L'heure et le temps qu'il fait</h2>'''+buttons+'''<img id="meteo" src="visite/clair.png"></section><section><small>MÊME KIT · ALPIN · VILLAGE DE VALLÉE · 1400 · CULTURE ALPINE CENTRALE</small><h2>Trois dispositions</h2><div class="grid">'''+''.join(cards)+'''</div></section><section><a href="../README.md">Guide de fabrication et de réutilisation</a><p>Les scènes Blender et Unity sont éditables. Les effets météo sont visuels ; le moteur historique n'est pas modifié.</p></section></html>'''
(OUT/'index.html').write_text(page,encoding='utf-8')
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',30)
board=Image.new('RGB',(1920,1410),(24,34,31));draw=ImageDraw.Draw(board)
draw.text((24,18),'FORGE / ALPIN — même village, lumière et météo variables',font=font,fill='#eee5d0')
for i,(name,label) in enumerate([states[k] for k in (0,1,4,5)]):
    x=(i%2)*960;y=75+(i//2)*665
    with Image.open(OUT/'visite'/(name+'.png')) as im:board.paste(im.resize((940,617),Image.Resampling.LANCZOS),(x+10,y))
    draw.text((x+22,y+617),label,font=font,fill='#eee5d0')
board.save(OUT/'meteo.png')
board=Image.new('RGB',(1920,570),(24,34,31));draw=ImageDraw.Draw(board)
draw.text((24,18),'Un même kit alpin. Trois implantations.',font=font,fill='#eee5d0')
for i,d in enumerate(recipe['dispositions']):
    with Image.open(OUT/'villages'/d['id']/'renders/territoire.png') as im:board.paste(im.resize((630,414),Image.Resampling.LANCZOS),(i*640+5,80))
    draw.text((i*640+18,510),d['label']+' · '+str(d['seed']),font=font,fill='#eee5d0')
board.save(OUT/'dispositions.png')
