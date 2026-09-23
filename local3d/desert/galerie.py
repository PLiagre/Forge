"""Galerie locale des véritables rendus Blender, des captures Unity et de la visite."""
import json
from pathlib import Path
import html

OUT = Path(__file__).parent / 'sorties'
recipe = json.loads((Path(__file__).parent / 'recette.json').read_text(encoding='utf-8'))
catalogue = json.loads((OUT / 'bibliotheque/catalogue.json').read_text(encoding='utf-8'))
reports = [json.loads((OUT / 'villages' / d['id'] / (d['id'] + '.json')).read_text(encoding='utf-8')) for d in recipe['dispositions']]
first = reports[0]['id']


def exists(path):
    return (OUT / path).exists()


def plan(r):
    """Plan des rues, maisons, jardins et de la guelta, en coordonnées Blender."""
    def xy(p): return ((p[0] + 260) * 2.4, (70 - p[1]) * 2.4)
    items = ['<rect width="780" height="620" fill="#2a1d14"/>',
             '<ellipse cx="624" cy="168" rx="127" ry="106" fill="#6b4a30" stroke="#c89a6a"/>']
    px, py, _ = r['pool']['position']; w, d = r['pool']['size']; x, y = xy((px, py))
    items.append(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{w * 1.2:.1f}" ry="{d * 1.2:.1f}" fill="#2f6f73"><title>guelta</title></ellipse>')
    for i in r['instances']:
        if i['asset'].startswith('palmier_'):
            x, y = xy(i['position']); items.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.6" fill="#4d7a3a"/>')
    for route in r['routes']:
        points = ' '.join(f'{xy(p["position"])[0]:.1f},{xy(p["position"])[1]:.1f}' for p in route['points'])
        color = '#d8b27c' if route['id'].startswith(('lisiere', 'acces')) else '#efe3cf'
        items.append(f'<polyline points="{points}" stroke="{color}" stroke-width="{route["width"] * 2.4}" fill="none" stroke-linejoin="round"><title>{html.escape(route["id"].replace("_", " "))}</title></polyline>')
    for i in r['instances']:
        if i['asset'].startswith('maison_'):
            x, y = xy(i['position']); ww = 6 * i['scale'][0] * 2.4; dd = 6 * i['scale'][1] * 2.4
            items.append(f'<rect x="{x - ww / 2:.1f}" y="{y - dd / 2:.1f}" width="{ww:.1f}" height="{dd:.1f}" transform="rotate({-i["rotation"]:.1f} {x:.1f} {y:.1f})" fill="#c98f5c" stroke="#3a2618"><title>{i["id"]}</title></rect>')
    for p in r['plots']:
        x, y = xy(p['position']); w, h = p['size']
        items.append(f'<rect x="{x - w * 1.2}" y="{y - h * 1.2}" width="{w * 2.4}" height="{h * 2.4}" fill="#3f5a2c" stroke="#b9c98f"/><text x="{x}" y="{y + 5}" text-anchor="middle" fill="#f1ecd0" font-size="13">{p["id"][-1]}</text>')
    items.append('<text x="585" y="172" fill="#fbe9cf" font-size="17">Ksar</text><path d="M600 590h120" stroke="#fbe9cf" stroke-width="3"/><text x="638" y="612" fill="#d9c3a3" font-size="14">50 m</text>')
    return '<svg role="img" aria-label="Plan des rues, du bourg, des jardins et de la guelta" viewBox="0 0 780 620" xmlns="http://www.w3.org/2000/svg">' + ''.join(items) + '</svg>'


cards = []
for r in reports:
    cards.append(f'<article><img loading="lazy" src="villages/{r["id"]}/renders/blender_ksar.png" alt="{html.escape(r["label"])}"><div><h3>{html.escape(r["label"])}</h3>'
                 f'<p>{r["building_count"]} maisons · {r["tree_count"]} palmiers et acacias · graine {r["seed"]}</p>'
                 f'<a href="villages/{r["id"]}/{r["id"]}.blend">Ouvrir le fichier Blender</a></div>{plan(r)}</article>')
views = [(c['name'].lower(), c['name']) for c in reports[0]['cameras']]
options = ''.join(f'<option value="{v}">{html.escape(label)}</option>' for v, label in views)
places = ''.join(f'<option value="{r["id"]}">{html.escape(r["label"])}</option>' for r in reports)
moods = [('soleil', 'Plein soleil'), ('vent_de_sable', 'Vent de sable'), ('crepuscule', 'Crépuscule'), ('nuit', 'Nuit'), ('brume', 'Brume de chaleur')]
mood_buttons = ''.join(f'<button{" class=active" if i == 0 else ""} data-image="{k}">{label}</button>' for i, (k, label) in enumerate(moods) if exists('visite/' + k + '.png'))
visit = ''
if exists('visite/desert.mp4'):
    visit = '<h2>Entrer dans le ksar</h2><video controls loop playsinline preload="metadata" poster="visite/soleil.png" src="visite/desert.mp4"></video><p class="caption">Capture réelle de Unity · 8 secondes · vent de sable, étendards, lanternes et fumées animés.</p>'
if mood_buttons:
    visit += f'<h2>Une même scène, plusieurs heures</h2><div id="moods">{mood_buttons}</div><img id="weather" src="visite/soleil.png" alt="Ambiance de la scène dans Unity">'
assets = ''.join(f'<li><span>{html.escape(a["id"])}</span><small>{a["triangles"][0]:,} triangles</small></li>' for a in catalogue['assets'])
page = f'''<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Forge · Ksar du désert</title>
<style>*{{box-sizing:border-box}}body{{margin:0;background:#1a120c;color:#f3e7d6;font:16px/1.6 system-ui}}main{{max-width:1440px;margin:auto;padding:45px 38px}}a{{color:#e9b46c}}header{{display:flex;justify-content:space-between;align-items:center;gap:30px;border-bottom:1px solid #4a3526;padding-bottom:24px}}h1{{font:52px/1.05 Georgia,serif;margin:12px 0}}h2{{font:35px Georgia,serif;margin-top:60px}}h3{{font:27px Georgia,serif;margin:0}}p{{color:#cdb89d}}.eyebrow{{letter-spacing:.22em;font-size:12px;color:#e9b46c}}.badge{{border:1px solid #6b4f36;padding:12px 20px;border-radius:30px;color:#e9b46c}}img,video{{width:100%;display:block;background:#120c08;border-radius:6px}}svg{{width:100%;display:block}}.hero{{margin-top:28px}}.caption{{font-size:13px}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:26px}}article{{border:1px solid #4a3526;border-radius:7px;overflow:hidden}}article div{{padding:24px}}button{{background:#2a1d14;color:#f0e2cc;border:1px solid #6b4f36;padding:10px 20px;margin:0 8px 16px 0;border-radius:4px;cursor:pointer}}button.active{{background:#e0a860;color:#1a120c}}select{{display:block;margin-top:8px;background:#2a1d14;color:#f3e7d6;border:1px solid #6b4f36;border-radius:4px;padding:12px;min-width:245px}}.choix{{display:flex;gap:24px;margin:22px 0;flex-wrap:wrap}}.choix label{{font-size:13px;color:#d4bfa2}}.pair{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}ul{{list-style:none;padding:0;display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:#4a3526}}li{{padding:12px;background:#221710;display:flex;justify-content:space-between;gap:12px;font-size:12px}}small{{color:#b39b7c;white-space:nowrap}}footer{{border-top:1px solid #4a3526;margin-top:60px;padding-top:18px;color:#b39b7c;font-size:13px}}@media(max-width:800px){{main{{padding:22px}}h1{{font-size:37px}}header{{display:block}}.badge{{display:inline-block}}.grid,ul,.pair{{grid-template-columns:1fr}}}}</style>
<main><header><div><div class="eyebrow">FORGE / ATELIER 3D</div><h1>Le ksar au-dessus de l'oasis</h1><p>Terre crue · Grès stratifié · Palmeraie · Dunes · Lumière de fin de journée</p></div><div class="badge">{len(catalogue["assets"])} modules réutilisables</div></header>
<img class="hero" src="villages/{first}/renders/blender_ksar.png" alt="Vue du ksar fabriquée dans Blender"><p class="caption">Rendu Cycles de la scène Blender. Remparts, mosquée, maisons, palmiers et dunes sont des maillages 3D.</p>
{visit}
<h2>Chaque cadrage, dans Blender et dans Unity</h2><p>Mêmes positions, mêmes cibles et mêmes focales, transmises par le manifeste. Les éclairages restent propres à chaque moteur.</p>
<div class="choix"><label>Implantation <select id="lieu">{places}</select></label><label>Cadrage <select id="camera">{options}</select></label></div>
<div class="pair"><figure><img id="blender" src="villages/{first}/renders/blender_ksar.png" alt="Rendu Blender"><figcaption class="caption">Blender · Cycles</figcaption></figure><figure><img id="unity" src="villages/{first}/renders/unity_ksar.png" alt="Capture Unity"><figcaption class="caption">Unity · URP</figcaption></figure></div>
<h2>Deux implantations, une bibliothèque</h2><p>Même biome, même typologie, même culture et même année. La graine déplace les maisons, la mosquée, la palmeraie et les dunes.</p><div class="grid">{"".join(cards)}</div>
<h2>Les pièces de l'atelier</h2><p>Modules en mètres, trois niveaux de détail, matériaux partagés, sources Blender et exports FBX. Les retouches manuelles de <code>sources/</code> restent prioritaires à la reconstruction.</p><ul>{assets}</ul><p><a href="../README.md">Lire le workflow de fabrication et de retouche</a></p>
<footer>Étude artistique saharienne imaginaire, fidélité 2. Les gardes et les dromadaires sont des silhouettes statiques. Cette scène n'est pas reliée à une photographie du moteur historique.</footer></main>
<script>(()=>{{const lieu=document.getElementById('lieu'),cam=document.getElementById('camera'),b=document.getElementById('blender'),u=document.getElementById('unity');const maj=()=>{{b.src='villages/'+lieu.value+'/renders/blender_'+cam.value+'.png';u.src='villages/'+lieu.value+'/renders/unity_'+cam.value+'.png';}};lieu.onchange=maj;cam.onchange=maj;
document.querySelectorAll('[data-image]').forEach(x=>x.onclick=()=>{{document.getElementById('weather').src='visite/'+x.dataset.image+'.png';document.querySelectorAll('[data-image]').forEach(y=>y.classList.toggle('active',y===x));}});}})();</script></html>'''
(OUT / 'index.html').write_text(page, encoding='utf-8')
print(OUT / 'index.html')
