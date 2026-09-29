"""Contrôle les originaux et construit une galerie locale, sans modifier les PNG."""

import hashlib
import html
import json
from collections import Counter
from pathlib import Path

from PIL import Image

RACINE = Path(__file__).resolve().parent
catalogue = json.loads((RACINE / 'catalogue.json').read_text(encoding='utf-8'))
erreurs = []
empreintes = {}
if len(catalogue) < 100:
    erreurs.append('La demande exige au moins cent images individuelles.')
identifiants = [image['id'] for image in catalogue]
if len(set(identifiants)) != len(identifiants):
    erreurs.append('Identifiants répétés dans le catalogue.')
for entree in catalogue:
    fichier = RACINE / entree['file']
    if not fichier.is_file():
        entree['status'] = 'absente'
        erreurs.append('Image absente : ' + entree['file'])
        continue
    try:
        with Image.open(fichier) as image:
            image.verify()
        with Image.open(fichier) as image:
            image.load()
            largeur, hauteur = image.size
            alpha = image.getchannel('A').getextrema() if 'A' in image.getbands() else None
            entree['alpha_min'] = alpha[0] if alpha else None
            entree['alpha_max'] = alpha[1] if alpha else None
            entree['largeur'] = largeur
            entree['hauteur'] = hauteur
            entree['mode'] = image.mode
            entree['fond_transparent'] = bool(alpha and alpha[0] == 0 and alpha[1] == 255)
            if min(largeur, hauteur) < 900 or max(largeur, hauteur) < 1500:
                erreurs.append('Définition insuffisante : ' + entree['file'])
            if entree['transparent'] and not entree['fond_transparent']:
                erreurs.append('Transparence stricte non validée (alpha attendu 0–255, mesuré ' + str(alpha) + ') : ' + entree['file'])
        empreinte = hashlib.sha256(fichier.read_bytes()).hexdigest()
        if empreinte in empreintes:
            erreurs.append('Doublon exact : ' + entree['file'] + ' / ' + empreintes[empreinte])
        empreintes[empreinte] = entree['file']
        entree['sha256'] = empreinte
        entree['octets'] = fichier.stat().st_size
        entree['status'] = 'generee'
    except Exception as exc:
        entree['status'] = 'illisible'
        erreurs.append(entree['file'] + ' : ' + str(exc))
presentes = [entree for entree in catalogue if entree['status'] == 'generee']
prevus = {entree['file'] for entree in catalogue}
supplementaires = sorted(str(p.relative_to(RACINE)).replace('\\', '/') for p in RACINE.glob('*/*.png') if str(p.relative_to(RACINE)).replace('\\', '/') not in prevus)
if supplementaires:
    erreurs.append('Images hors catalogue : ' + ', '.join(supplementaires))
controle = {
    'attendues': len(catalogue), 'presentes': len(presentes),
    'uniques': len(empreintes), 'par_categorie': dict(Counter(e['category'] for e in presentes)),
    'fonds_transparents': sum(e.get('fond_transparent', False) for e in presentes),
    'octets': sum(e.get('octets', 0) for e in presentes),
    'erreurs': erreurs,
    'portee': 'Intégrité, définition, présence, unicité et transparence ; la qualité artistique se regarde séparément.'
}
(RACINE / 'controle.json').write_text(json.dumps(controle, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(RACINE / 'catalogue.json').write_text(json.dumps(catalogue, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
cartes = []
categories = {}
for entree in presentes:
    categories[entree['category']] = entree['categorie_fr']
    titre, region, chemin = (html.escape(str(entree[cle]), quote=True) for cle in ['title', 'region', 'file'])
    recherche = html.escape(' '.join([entree['title'], entree['region'], entree['categorie_fr'], str(entree['year'])]), quote=True)
    cartes.append(f'''<article data-categorie="{entree['category']}" data-annee="{entree['year']}" data-recherche="{recherche}">
<a class="image" href="{chemin}" aria-label="Agrandir : {titre}"><img src="{chemin}" alt="{titre}" loading="lazy" width="{entree['largeur']}" height="{entree['hauteur']}"></a>
<div class="legende"><p class="date">VERS {entree['year']} · {region}</p><h2>{titre}</h2><p>{html.escape(entree['categorie_fr'])}</p>
<p class="liens"><a href="{chemin}" download>Télécharger le PNG</a><span>{entree['largeur']} × {entree['hauteur']}</span></p>
<details><summary>Consigne de création</summary><p class="consigne">{html.escape(entree['prompt'])}</p></details></div></article>''')
options = ''.join(f'<option value="{cle}">{html.escape(valeur)}</option>' for cle, valeur in categories.items())
page = '''<!doctype html>
<html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Forge — Atlas artistique</title>
<style>
:root{color-scheme:dark;font-family:Georgia,serif;background:#151a1b;color:#e8e2d7}*{box-sizing:border-box}body{margin:0}a{color:#d4b980}a:hover{color:white}header{padding:70px max(5vw,24px) 45px;background:linear-gradient(90deg,rgba(12,19,19,.96),rgba(12,19,19,.3)),url('01_scenes/seigneurie_1400.png') center/cover}header p{max-width:620px;font:17px/1.7 system-ui}h1{font-weight:normal;font-size:clamp(42px,6vw,80px);margin:10px 0}.surtitle{letter-spacing:.22em;color:#d4b980;font:12px system-ui}.outils{padding:22px max(5vw,24px);background:#1e2628;border-bottom:1px solid #3a4241;display:flex;gap:16px;flex-wrap:wrap;align-items:end;position:sticky;top:0;z-index:2}label{display:flex;gap:7px;flex-direction:column;font:12px system-ui;color:#c5cbc5}input,select,button{font:15px system-ui;background:#111819;border:1px solid #58605b;border-radius:4px;padding:10px;color:#eee;max-width:100%}input{width:270px}button{cursor:pointer}main{padding:30px max(5vw,24px)}#compteur{font:14px system-ui;color:#bdc6c2;margin:0 0 25px}.grille{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,330px),1fr));gap:25px}article{background:#202729;border:1px solid #384140;border-radius:6px;overflow:hidden}article[hidden]{display:none}.image{display:block;height:270px;background:repeating-conic-gradient(#242c2d 0% 25%,#2c3536 0% 50%) 50%/24px 24px}.image img{width:100%;height:100%;object-fit:contain}.legende{padding:20px}h2{font-size:23px;font-weight:normal;margin:8px 0 12px}.legende p{font:14px/1.5 system-ui}.legende .date{font-size:10px;letter-spacing:.07em;color:#d1b77f}.liens{display:flex;gap:15px;justify-content:space-between;font-size:12px!important}.liens span{color:#aeb7b2}details{font:13px system-ui;border-top:1px solid #3b4543;padding-top:14px}summary{cursor:pointer;color:#c6c9bd}.consigne{white-space:pre-wrap;color:#bac3be;font-size:12px!important}footer{padding:40px 5vw;color:#afb7b1;font:13px/1.7 system-ui;border-top:1px solid #3b4543}dialog{padding:15px;background:#151a1b;color:#eee;border:1px solid #58605b;max-width:95vw;max-height:95vh}dialog::backdrop{background:rgba(0,0,0,.88)}dialog img{display:block;max-width:88vw;max-height:78vh;object-fit:contain;margin:14px auto}dialog form{text-align:right}dialog p{font:14px system-ui}#vide{font:18px system-ui}
</style>
<header><span class="surtitle">FORGE / DIRECTION ARTISTIQUE</span><h1>Un monde qui se transforme.</h1><p>Du domaine de 1400 à l’État industriel de 1900. Paysages, habitants, architectures et symboles d’une Europe et d’une Méditerranée vivantes.</p><p>__TOTAL__ illustrations originales · __CATEGORIES__ catégories · <a href="README.md">La direction artistique</a></p></header>
<div class="outils"><label>Rechercher<input id="recherche" type="search" placeholder="Oasis, forge, portrait…"></label><label>Catégorie<select id="categorie"><option value="">Toutes les catégories</option>__OPTIONS__</select></label><label>Période<select id="periode"><option value="">1400–1900</option><option value="1400">1400–1499</option><option value="1500">1500–1599</option><option value="1600">1600–1699</option><option value="1700">1700–1799</option><option value="1800">1800–1900</option></select></label><button id="effacer" type="button">Tout afficher</button></div>
<main><p id="compteur" aria-live="polite"></p><div class="grille">__CARTES__</div><p id="vide" hidden>Aucune image pour ces critères.</p></main>
<dialog id="agrandissement" aria-label="Image agrandie"><form method="dialog"><button>Fermer</button></form><img alt=""><p></p><a download>Télécharger l’original PNG</a></dialog>
<footer>Concepts artistiques plausibles de niveau 2. Les dates situent les propositions ; les personnages et emblèmes sont fictifs. Génération par l’outil intégré image_gen.<br><a href="catalogue.json">Catalogue et consignes</a> · <a href="controle.json">Contrôle des fichiers</a></footer>
<script>
const cartes=[...document.querySelectorAll('article')], recherche=document.querySelector('#recherche'), categorie=document.querySelector('#categorie'), periode=document.querySelector('#periode');
const normaliser=s=>s.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase();
function filtrer(){let n=0;const mots=normaliser(recherche.value).trim().split(/\\s+/).filter(Boolean);for(const carte of cartes){const a=Number(carte.dataset.annee),p=Number(periode.value);const visible=(!categorie.value||carte.dataset.categorie===categorie.value)&&(!p||(a>=p&&a<(p===1800?1901:p+100)))&&mots.every(m=>normaliser(carte.dataset.recherche).includes(m));carte.hidden=!visible;if(visible)n++;}document.querySelector('#compteur').textContent=n+' image'+(n>1?'s':'')+' affichée'+(n>1?'s':'')+' sur '+cartes.length;document.querySelector('#vide').hidden=n>0;}
for(const champ of [recherche,categorie,periode])champ.addEventListener('input',filtrer);
document.querySelector('#effacer').onclick=()=>{recherche.value='';categorie.value='';periode.value='';filtrer();};
const dialogue=document.querySelector('dialog');for(const lien of document.querySelectorAll('a.image'))lien.addEventListener('click',e=>{if(e.ctrlKey||e.metaKey||e.shiftKey)return;e.preventDefault();const image=dialogue.querySelector('img');image.src=lien.href;image.alt=lien.querySelector('img').alt;dialogue.querySelector('p').textContent=image.alt;dialogue.querySelector('a').href=lien.href;dialogue.showModal();});
filtrer();
</script></html>
'''
for cle, valeur in {'__TOTAL__': str(len(presentes)), '__CATEGORIES__': str(len(categories)), '__OPTIONS__': options, '__CARTES__': '\n'.join(cartes)}.items():
    page = page.replace(cle, valeur)
(RACINE / 'index.html').write_text(page, encoding='utf-8')
print(json.dumps(controle, ensure_ascii=False, indent=2))
raise SystemExit(1 if erreurs else 0)
