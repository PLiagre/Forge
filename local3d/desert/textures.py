"""Palette chaude : terre crue, grès stratifié, sable ridé, palmes et tissus.

Les cartes sont calculées ici et partagées par Blender et Unity. Une unité UV
couvre deux mètres, comme dans la citadelle : les motifs gardent leur échelle.
"""
from pathlib import Path
import numpy as np
from PIL import Image
from local3d.atelier_v2.textures import srgb, noise

PALETTE = {
    'pise': ((.50,.29,.17),'pise'),
    'pise_clair': ((.62,.42,.27),'pise'),
    'enduit_pise': ((.68,.48,.33),'plaster'),
    'brique_crue': ((.50,.32,.20),'brick'),
    'chaux': ((.86,.82,.74),'plaster'),
    'pierre_taille': ((.64,.49,.34),'ashlar'),
    'gres_rouge': ((.50,.24,.13),'sandstone'),
    'gres_ocre': ((.66,.42,.22),'sandstone'),
    'gres_clair': ((.75,.59,.41),'sandstone'),
    'gres_sombre': ((.32,.18,.11),'sandstone'),
    'sable_dune': ((.80,.57,.34),'sand'),
    'sable_ombre': ((.68,.45,.27),'sand'),
    'reg_gravier': ((.55,.37,.23),'gravel'),
    'terre_jardin': ((.25,.16,.09),'garden'),
    'palme': ((.12,.21,.09),'palm'),
    'palme_seche': ((.46,.35,.17),'palm'),
    'stipe_palmier': ((.35,.25,.16),'palmbark'),
    'bois_palmier': ((.38,.27,.16),'wood'),
    'bois_sombre': ((.13,.08,.048),'wood'),
    'bois_peint_bleu': ((.07,.19,.31),'wood'),
    'bois_peint_vert': ((.06,.22,.13),'wood'),
    'tuile_verte': ((.09,.36,.19),'tiles'),
    'feuillage_acacia': ((.19,.25,.08),'acacia'),
    'tissu_etendard': ((.05,.24,.13),'fabric'),
    'tissu_poil': ((.10,.075,.06),'fabric'),
    'zellige': ((.12,.36,.34),'zellige'),
    'eau_oasis': ((.035,.105,.10),'water'),
    'fer_noir': ((.022,.028,.032),'plaster'),
    'cuivre': ((.47,.25,.09),'plaster'),
    'lumiere': ((1,.45,.10),'plaster'),
    'baie_sombre': ((.035,.028,.024),'plaster'),
    'tissu_indigo': ((.045,.075,.23),'fabric'),
    'tissu_garance': ((.46,.065,.04),'fabric'),
    'tissu_safran': ((.73,.43,.07),'fabric'),
    'tissu_ecru': ((.73,.65,.51),'fabric'),
    'tapis': ((.42,.08,.05),'rug'),
    'poterie': ((.57,.31,.17),'plaster'),
    'dattes': ((.30,.11,.04),'plaster'),
    'epices_rouge': ((.56,.12,.03),'plaster'),
    'epices_jaune': ((.76,.50,.05),'plaster'),
    'epices_vert': ((.26,.32,.08),'plaster'),
    'cuir_chameau': ((.56,.41,.26),'hide'),
    'sol_dalle': ((.56,.44,.31),'stone'),
    'souk_dalles': ((.52,.40,.28),'roadstone'),
    'chemin_dalle': ((.52,.40,.28),'roadstone'),
    'chemin_sable': ((.58,.41,.26),'roadsoil'),
}


def save_material(folder, name, color, kind, seed, roughness):
    rng = np.random.default_rng(seed)
    n = 1024
    yy, xx = np.mgrid[:n, :n] / n
    grain = noise(rng, n)
    micro = rng.random((n, n))
    col = np.ones((n, n, 3)) * color
    height = grain * .018
    rough = roughness + (grain - .5) * .20
    col *= (.78 + grain[..., None] * .44)
    alpha = None
    if kind == 'pise':
        # Banchées de 65 cm, trous de boulins, ravines verticales laissées par les rares pluies.
        lift = (yy * 3) % 1
        seam = np.clip(1 - abs(lift - .02) / .025, 0, 1)
        gully = np.clip((noise(np.random.default_rng(seed + 7), n)[:, :1].repeat(n, 1).T - .62) * 4, 0, 1)
        gully = np.clip(gully * (.4 + .6 * np.sin(yy * np.pi) ** 2), 0, 1)
        holes = (((xx * 4 + np.floor(yy * 3) * .5) % 1 - .5) ** 2 * 900 + ((lift - .08) * 60) ** 2) < 1
        pebbles = np.clip((micro - .985) * 60, 0, 1)
        col *= (1 - .22 * seam - .16 * gully + .12 * pebbles)[..., None]
        col[holes] *= .28
        height += -seam * .02 - gully * .025 + pebbles * .01 - holes * .05 + (micro - .5) * .004
        rough += gully * .05
    elif kind == 'brick':
        rows, cols = 9, 4
        row = np.floor(yy * rows)
        u = (xx * cols + row % 2 * .5) % 1
        v = (yy * rows) % 1
        cell = np.sin(row * 17.4 + np.floor(xx * cols + row % 2 * .5) * 41.7)
        edge = np.minimum(np.minimum(u, 1 - u) * 2.2, np.minimum(v, 1 - v))
        bevel = np.clip((edge - .03 - .03 * grain) / .07, 0, 1)
        col *= ((.70 + bevel * .30) * (.94 + cell * .08))[..., None]
        height += bevel * .03 + cell * .004
    elif kind in ('stone', 'roadstone', 'ashlar', 'tiles'):
        rows = 12 if kind == 'roadstone' else 5 if kind == 'stone' else 14 if kind == 'tiles' else 4
        cols = 10 if kind == 'roadstone' else 3 if kind == 'stone' else 9 if kind == 'tiles' else 2
        row = np.floor(yy * rows)
        jitter = np.sin(row * 7.1) * .2
        u = (xx * cols + row % 2 * .5 + jitter) % 1
        v = (yy * rows) % 1
        cell = np.sin(row * 17.4 + np.floor(xx * cols + row % 2 * .5 + jitter) * 41.7)
        edge = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v))
        erosion = .02 + .03 * grain
        bevel = np.clip((edge - erosion) / .07, 0, 1)
        col *= ((.60 + bevel * .40) * (.95 + cell * .09))[..., None]
        height += bevel * .03 + cell * .004
        rough += (1 - bevel) * .08
        if kind == 'tiles':
            # Tuiles canal vernissées : un reflet par rang, joints sombres.
            glaze = np.sin(u * np.pi) ** 2
            col = np.array(color)[None, None, :] * (.55 + .6 * glaze + .10 * cell)[..., None] * (.7 + .3 * bevel)[..., None]
            height = glaze * .03 + bevel * .01
            rough = .35 + (1 - glaze) * .3
        if kind == 'ashlar':
            bevel = np.clip((edge - .01) / .02, 0, 1)
            col = np.array(color)[None, None, :] * (.92 + .12 * grain + .06 * cell)[..., None] * (.80 + .20 * bevel)[..., None]
            height = bevel * .01 + grain * .003
    elif kind == 'sandstone':
        # Bancs horizontaux, litages obliques et diaclases : le grès se lit par couches.
        warp = grain * 6 + np.sin(xx * 9) * .4
        bands = np.sin(yy * 38 + warp)
        cross = np.sin((yy * 1.0 + xx * .35) * 140 + grain * 9) * np.clip(np.sin(yy * 19 + warp), 0, 1)
        layer = np.floor(yy * 7 + grain * .6)
        tint = np.sin(layer * 3.7)[..., None] * np.array((.10, .05, .02))
        joints = np.clip((abs(np.sin(xx * 11 + np.floor(yy * 7) * 2.3 + grain * 2)) - .965) * 30, 0, 1)
        col = col * (.86 + bands[..., None] * .10 + cross[..., None] * .035 - joints[..., None] * .35) + tint
        height += bands * .03 + cross * .006 - joints * .05 + micro * .002
    elif kind == 'sand':
        # Rides éoliennes : pente douce au vent, raide sous le vent.
        warp = grain * 4 + np.sin(yy * 5) * .3
        phase = (xx * 26 + yy * 7 + warp) % 1
        ripple = np.where(phase < .78, phase / .78, (1 - phase) / .22)
        col *= (.93 + ripple[..., None] * .10 + (micro[..., None] - .5) * .05)
        height = ripple * .014 + micro * .0015
        rough = .88 + grain * .08
    elif kind == 'gravel':
        pebble = noise(np.random.default_rng(seed + 3), n)
        stones = np.clip((pebble - .58) * 7, 0, 1) * np.clip((micro - .35) * 2, 0, 1)
        dark = np.clip((noise(np.random.default_rng(seed + 5), n) - .5) * 3, -.5, .5)
        col = col * (1 - stones[..., None] * .35) + stones[..., None] * np.array((.24, .16, .11)) * (1 + dark[..., None])
        height += stones * .035
    elif kind == 'garden':
        furrow = np.sin(xx * 28 * np.pi)
        plants = (furrow > .35) & (noise(np.random.default_rng(seed + 9), n) > .42)
        col *= (.85 + furrow[..., None] * .12)
        col[plants] = np.array((.13, .26, .06)) * (.7 + grain[plants, None] * .6)
        height += furrow * .03 + plants * .02
    elif kind == 'wood':
        warp = np.sin(yy * 18) * .7 + grain * 5
        streak = np.sin(xx * 240 + warp) * np.sin(xx * 47 + warp)
        seam = (xx * 8) % 1 < .016
        col *= np.where(seam, .35, .84 + .16 * streak)[..., None]
        height += streak * .012 - seam * .05
    elif kind == 'palmbark':
        # Bases de palmes coupées : losanges imbriqués autour du stipe.
        a = (xx * 6 + yy * 9) % 1
        b = (xx * 6 - yy * 9) % 1
        ridge = np.minimum(np.minimum(a, 1 - a), np.minimum(b, 1 - b))
        scale = np.clip(ridge / .18, 0, 1)
        col *= (.50 + scale[..., None] * .55)
        height += scale * .05
    elif kind == 'palm':
        # Rachis au centre, folioles obliques de part et d'autre ; l'enveloppe s'effile.
        center = .5 + .02 * np.sin(xx * 7)
        d = abs(yy - center)
        envelope = .48 * np.sin(np.pi * np.clip(xx * 1.02, 0, 1)) ** .45
        leaflet = (xx * 46 + d * 3.2 + grain * .15) % 1
        cover = (d < envelope) & ((leaflet < .34) | (d < .02))
        col *= (.72 + grain[..., None] * .45 + (d < .02)[..., None] * .25)
        height = grain * .003
        alpha = cover
    elif kind == 'acacia':
        # Petites folioles regroupées ; les trous laissent passer la lumière.
        blobs = noise(np.random.default_rng(seed + 13), n)
        leaves = (np.sin(xx * 180 + grain * 9) * np.sin(yy * 170 + grain * 7)) > -.25
        alpha = (blobs > .47) & leaves
        col *= (.7 + blobs[..., None] * .6)
        height = blobs * .01
    elif kind == 'fabric':
        stripes = np.floor(yy * 6) % 3
        weave = (np.sin(xx * n * .8) * np.sin(yy * n * .8)) * .5 + .5
        col *= (.82 + .10 * weave[..., None])
        col[stripes == 1] *= .62
        border = ((yy * 6) % 1 < .06)
        col[border] = col[border] * .4 + np.array((.72, .62, .44)) * .6
        height += weave * .004
    elif kind == 'rug':
        u = abs((xx * 4) % 1 - .5); v = abs((yy * 4) % 1 - .5)
        diamond = (u + v) < .32
        inner = (u + v) < .14
        border = (np.minimum(np.minimum(xx, 1 - xx), np.minimum(yy, 1 - yy)) < .07)
        col[diamond] = np.array((.70, .48, .15))
        col[inner] = np.array((.05, .08, .20))
        col[border] = np.array((.08, .06, .05))
        col *= (.85 + grain[..., None] * .3)
    elif kind == 'zellige':
        # Étoiles à huit branches et carreaux émaillés, joints de mortier clair.
        u = (xx * 8) % 1 - .5; v = (yy * 8) % 1 - .5
        star = np.maximum(abs(u) + abs(v) * .41, abs(v) + abs(u) * .41) < .36
        star |= np.maximum(abs(u), abs(v)) < .22
        tile = (np.floor(xx * 8) + np.floor(yy * 8)) % 3
        palette = np.array([(.06, .26, .34), (.12, .38, .28), (.80, .76, .66)])
        col = palette[tile.astype(int)] * (.9 + grain[..., None] * .2)
        col[star] = np.array((.72, .52, .14)) * (.9 + grain[star, None] * .2)
        grout = (abs(abs(u) + abs(v) * .41 - .36) < .012) | (abs(np.maximum(abs(u), abs(v)) - .5) < .02)
        col[grout] = (.62, .58, .50)
        height = grout * -.02 + grain * .002
        rough[:] = .25
    elif kind == 'water':
        wave = np.sin(xx * 40 + grain * 7) * np.sin(yy * 33 + grain * 5)
        col = np.array(color)[None, None, :] * (.9 + wave[..., None] * .1)
        height = wave * .006
        rough[:] = .06
    elif kind == 'hide':
        fur = noise(np.random.default_rng(seed + 11), n)
        col *= (.8 + fur[..., None] * .35)
        height += fur * .01
    elif kind == 'plaster':
        height += (micro - .5) * .004
    if kind in ('roadstone', 'roadsoil') and name != 'souk_dalles':
        # Le sable gagne les accotements par langues irrégulières, sans ruban à bord franc.
        edge = abs(xx - .5) * 2
        threshold = .50 + .26 * grain + .04 * np.sin(yy * 6 * np.pi)
        drift = np.clip((edge - threshold) / .25, 0, 1)
        drift = drift * drift * (3 - 2 * drift)
        tongues = np.clip((grain - .62) * 6, 0, .5) * (1 - drift)
        sand = np.maximum(drift, tongues)
        phase = (xx * 26 + yy * 7 + grain * 4) % 1
        ripple = np.where(phase < .78, phase / .78, (1 - phase) / .22)
        sandcolor = np.array((.78, .56, .34)) * (.93 + ripple[..., None] * .1)
        col = col * (1 - sand[..., None]) + sandcolor * sand[..., None]
        height = height * (1 - sand) + ripple * .012 * sand
        rough = rough * (1 - sand) + .9 * sand
    dy, dx = np.gradient(height)
    normal = np.stack((-dx * n * .65, -dy * n * .65, np.ones_like(dx)), axis=-1)
    normal /= np.linalg.norm(normal, axis=-1)[..., None]
    folder.mkdir(parents=True, exist_ok=True)
    rgba = (srgb(col) * 255).astype(np.uint8)
    if alpha is not None:
        rgba = np.dstack((rgba, alpha.astype(np.uint8) * 255))
    Image.fromarray(rgba).save(folder / (name + '_BaseColor.png'))
    Image.fromarray(np.clip((normal * .5 + .5) * 255, 0, 255).astype(np.uint8)).save(folder / (name + '_Normal.png'))
    pack = np.zeros((n, n, 4), dtype=np.uint8)
    pack[:, :, :3] = 210 if name == 'fer_noir' else 170 if name == 'cuivre' else 0
    pack[:, :, 3] = (np.clip(1 - rough, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(pack).save(folder / (name + '_MetallicGloss.png'))


def prepare(folder):
    for i, (name, (color, kind)) in enumerate(PALETTE.items()):
        save_material(Path(folder), name, color, kind, 2100 + i,
                      .48 if name == 'fer_noir' else .5 if name == 'cuivre' else .86)


if __name__ == '__main__':
    prepare(Path(__file__).parent / 'sorties/textures')
