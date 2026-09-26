"""Palette froide, pierre stratifiée et ardoises, produites localement."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter
from local3d.atelier_v2.textures import srgb, noise

PALETTE = {
    'basalte': ((.13,.145,.15),'stone'),
    'pierre_taille': ((.28,.275,.25),'cutstone'),
    'calcaire': ((.40,.375,.31),'cutstone'),
    'roche_noire': ((.125,.15,.17),'rock'),
    'roche_claire': ((.245,.28,.30),'rock'),
    'enduit': ((.31,.275,.22),'plaster'),
    'bois_noir': ((.075,.053,.035),'wood'),
    'bois_vieux': ((.20,.127,.071),'wood'),
    'ardoise': ((.075,.12,.155),'tiles'),
    'neige_givre': ((.78,.84,.86),'snow'),
    'neige_ombre': ((.60,.69,.74),'snow'),
    'aiguilles_sombres': ((.022,.068,.059),'leaf'),
    'fer_noir': ((.022,.028,.032),'plaster'),
    'cuivre': ((.31,.18,.07),'plaster'),
    'tissu_bordeaux': ((.14,.018,.027),'plaster'),
    'lumiere': ((1,.39,.055),'plaster'),
    'vitrail_ambre': ((.75,.255,.036),'glass'),
    'vitrail_bleu': ((.075,.21,.26),'glass'),
    'sol_pave': ((.18,.195,.20),'stone'),
}


def save_material(folder, name, color, kind, seed, roughness):
    """Textures métriques : joints creusés, usure et rugosité réellement exportée."""
    rng = np.random.default_rng(seed)
    n = 1024
    yy, xx = np.mgrid[:n, :n] / n
    grain = noise(rng, n)
    micro = rng.random((n, n))
    col = np.ones((n, n, 3)) * color
    height = grain * .018
    rough = roughness + (grain - .5) * .22
    col *= (.72 + grain[..., None] * .55)
    if kind in ('stone', 'tiles'):
        rows = 4 if kind == 'stone' else 10
        cols = 2 if kind == 'stone' else 7
        row = np.floor(yy * rows)
        u = (xx * cols + row % 2 * .5) % 1
        v = (yy * rows) % 1
        cell = np.sin(row * 17.4 + np.floor(xx * cols + row % 2 * .5) * 41.7)
        edge = np.minimum(np.minimum(u, 1-u), np.minimum(v, 1-v))
        erosion = .015 + .023 * grain
        bevel = np.clip((edge - erosion) / .07, 0, 1)
        col *= ((.53 + bevel * .47) * (.96 + cell * .10))[..., None]
        col *= (1 - .18 * np.clip((grain-.57)*5, 0, 1))[..., None]
        height += bevel * .035 + cell * .005
        rough += (1-bevel)*.12
    elif kind == 'wood':
        warp = np.sin(yy*18) * .7 + grain*5
        streak = np.sin(xx*240 + warp) * np.sin(xx*47+warp)
        seam = (xx*8) % 1 < .016
        col *= np.where(seam, .30, .82 + .18*streak)[..., None]
        height += streak*.012 - seam*.055
    elif kind == 'rock':
        strata = np.sin(yy*115 + xx*26 + grain*14)
        fracture = np.clip((abs(np.sin(xx*34+yy*19+grain*4))-.92)*12, 0, 1)
        col *= (.8 + grain*.32 + strata*.10 - fracture*.23)[..., None]
        height += strata*.035 - fracture*.025
    elif kind == 'glass':
        u = (xx+yy*.5)*12
        v = (xx-yy*.5)*12
        lead = (np.abs(np.sin(u*np.pi)) < .09) | (np.abs(np.sin(v*np.pi)) < .09)
        choice = (np.floor(u) + 3*np.floor(v)).astype(int) % 13
        colors = np.array([(.31,.115,.025),(.43,.17,.035),(.29,.095,.018),(.46,.20,.05),
                           (.32,.12,.023),(.39,.15,.03),(.055,.105,.12),(.34,.125,.028),
                           (.45,.195,.06),(.26,.078,.018),(.35,.14,.03),(.13,.047,.022),(.41,.17,.04)])
        if name=='vitrail_bleu':colors=colors[:,[2,1,0]]*.65
        col = colors[choice] * (.72 + grain[..., None]*.6)
        col[lead] = (.009,.013,.016)
        height += lead*.04
        rough[:] = .32
    elif kind == 'snow':
        # Le grain très fin laisse de larges masses calmes à distance.
        col *= (.94 + grain[..., None]*.12)
        height = grain*.008 + micro*.001
        rough = .62 + grain*.16
    elif kind == 'plaster':
        height += (micro-.5)*.004
    dy, dx = np.gradient(height)
    normal = np.stack((-dx*n*.65, -dy*n*.65, np.ones_like(dx)), axis=-1)
    normal /= np.linalg.norm(normal, axis=-1)[..., None]
    folder.mkdir(parents=True, exist_ok=True)
    Image.fromarray((srgb(col)*255).astype(np.uint8)).save(folder/(name+'_BaseColor.png'))
    Image.fromarray(np.clip((normal*.5+.5)*255,0,255).astype(np.uint8)).save(folder/(name+'_Normal.png'))
    pack = np.zeros((n,n,4), dtype=np.uint8)
    pack[:,:,:3] = 210 if name == 'fer_noir' else 165 if name == 'cuivre' else 0
    pack[:,:,3] = (np.clip(1-rough,0,1)*255).astype(np.uint8)
    Image.fromarray(pack).save(folder/(name+'_MetallicGloss.png'))

def prepare(folder):
    for i,(name,(color,kind)) in enumerate(PALETTE.items()):
        save_material(Path(folder),name,color,kind,1100+i,.83 if name!='fer_noir' else .48)

if __name__=='__main__':
    prepare(Path(__file__).parent/'sorties/textures')
