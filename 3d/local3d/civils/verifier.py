# Contrôle de civil.vat (lot #785), bibliothèque standard seule : py verifier.py CHEMIN [--contre-epreuves]
# Tout se dérive des octets livrés : en-tête, clips, longueur, valeurs, taille et marche. Non nul au refus.
import math, pathlib, struct, sys

CLIPS = [('marche', 24, 1.15), ('repos', 24, 4.0)]

def decoder(data):
    """Coins de référence (position, normale, couleur RGBA) et poses (position, normale) par clip."""
    if len(data) < 12 or data[:4] != b'VAT1':
        raise ValueError('signature VAT1 absente')
    c, n = struct.unpack_from('<ii', data, 4)
    if c <= 0 or c % 3 or n <= 0 or len(data) < 12 + 24 * n:
        raise ValueError('en-tête incohérent : %d coins, %d clips' % (c, n))
    clips = [struct.unpack_from('<16sif', data, 12 + 24 * k) for k in range(n)]
    clips = [(nom.rstrip(b'\0').decode('ascii', 'replace'), max(i, 0), d) for nom, i, d in clips]
    o = 12 + 24 * n + 20 * c
    if len(data) != o + 12 * c * sum(i for _, i, _ in clips):
        raise ValueError('longueur %d octets, attendue %d' % (len(data), o + 12 * c * sum(i for _, i, _ in clips)))
    v = struct.unpack_from('<%de' % (10 * c), data, o - 20 * c)
    ref, poses = [v[10 * i:10 * i + 10] for i in range(c)], {}
    for nom, images, _ in clips:
        v = struct.unpack_from('<%de' % (6 * c * images), data, o)
        poses[nom], o = [[v[6 * i:6 * i + 6] for i in range(c * j, c * j + c)] for j in range(images)], o + 12 * c * images
    return c, clips, ref, poses

def centre(pose, groupe):
    return [sum(pose[i][a] for i in groupe) / len(groupe) for a in range(3)]

def controler(data):
    """Lève ValueError au premier défaut ; rend les lignes du compte rendu sinon."""
    c, clips, ref, poses = decoder(data)
    if [k[:2] for k in clips] != [k[:2] for k in CLIPS] or any(abs(a[2] - b[2]) > 1e-5 for a, b in zip(clips, CLIPS)):
        raise ValueError('clips %s, attendus %s' % (clips, CLIPS))
    toutes = [ref] + poses['marche'] + poses['repos']
    for coin in (coin for pose in toutes for coin in pose):
        if not all(math.isfinite(x) for x in coin) or abs(math.hypot(*coin[3:6]) - 1) > 0.02:
            raise ValueError('valeur non finie ou normale non unitaire : %s' % (coin,))
    if any(not 0 <= x <= 1 for coin in ref for x in coin[6:10]):
        raise ValueError('couleur hors de [0, 1]')
    bornes = [(min(p[a] for q in toutes for p in q), max(p[a] for q in toutes for p in q)) for a in range(3)]
    bas, haut = min(p[1] for p in ref), max(p[1] for p in ref) - min(p[1] for p in ref)
    if not 1.5 <= haut <= 2.0 or abs(bas) >= 0.02:
        raise ValueError('hauteur %.3f m, bas %.3f m' % (haut, bas))
    # Groupes tirés de la pose de référence (Unity : X droite, Y haut, Z avant).
    pied = {s: [i for i, p in enumerate(ref) if p[1] < 0.35 and p[0] * s > 0] for s in (1, -1)}
    main = {s: [i for i, p in enumerate(ref) if 0.7 < p[1] < 1.0 and p[0] * s > 0.22] for s in (1, -1)}
    torse = [i for i, p in enumerate(ref) if 1.0 < p[1] < 1.5 and abs(p[0]) < 0.12]
    if not all(list(pied.values()) + list(main.values()) + [torse]):
        raise ValueError('un groupe pied, main ou torse est vide')
    q1, q3 = [poses['marche'][len(poses['marche']) * k // 4] for k in (1, 3)]
    avance = lambda g: (centre(q1, g)[2] - centre(q1, torse)[2]) - (centre(q3, g)[2] - centre(q3, torse)[2])
    ecart, bras = {s: avance(pied[s]) for s in pied}, {s: avance(main[s]) for s in main}
    if min(abs(e) for e in ecart.values()) < 0.08 or ecart[1] * ecart[-1] >= 0:
        raise ValueError('pieds immobiles ou non alternés : D %+.3f G %+.3f m' % (ecart[1], ecart[-1]))
    if min(abs(e) for e in bras.values()) < 0.05:
        raise ValueError('bras immobiles : D %+.3f G %+.3f m' % (bras[1], bras[-1]))
    t0 = centre(ref, torse)
    derive = max(math.hypot(t[0] - t0[0], t[2] - t0[2]) for t in (centre(p, torse) for p in toutes))
    if derive > 0.03:
        raise ValueError('racine déplacée de %.3f m' % derive)
    return ['%d triangles, %d coins ; %s' % (c // 3, c, ', '.join('%s %d images / %.2f s' % k for k in clips)),
            'bornes (toutes poses) : ' + ' '.join('%s [%.3f, %.3f]' % (a, *b) for a, b in zip('xyz', bornes)),
            'hauteur %.3f m, bas %.3f m ; coins des pieds %d/%d, des mains %d/%d, du torse %d' % (
                haut, bas, len(pied[1]), len(pied[-1]), len(main[1]), len(main[-1]), len(torse)),
            'marche, quart moins trois quarts : pieds D %+.3f G %+.3f m, mains D %+.3f G %+.3f m ; racine %.3f m' % (
                ecart[1], ecart[-1], bras[1], bras[-1], derive)]

def copies(data):
    """Copies altérées en mémoire : vide, tronquée, coin NaN, marche figée, translation en bloc."""
    c, clips, ref, _ = decoder(data)
    o, n = 12 + 24 * len(clips), clips[0][1]
    m = o + 20 * c
    glisse = [struct.pack('<%de' % (6 * c), *[x for p in ref for x in (p[0], p[1], p[2] + 0.02 * k) + p[3:6]])
              for k in range(sum(i for _, i, _ in clips))]
    return {'vide': b'', 'tronquée': data[:-7], 'coin NaN': data[:o] + b'\x00\x7e' + data[o + 2:],
            'marche figée': data[:m] + data[m:m + 12 * c] * n + data[m + n * 12 * c:],
            'translation': data[:m] + b''.join(glisse)}

def main(args):
    try:
        data = pathlib.Path(args[0] if args else '').read_bytes()
        print('\n'.join('[civil] ' + ligne for ligne in controler(data)))
    except (OSError, ValueError, struct.error) as e:
        return print('[civil] REFUS :', e) or 1
    refus, altere = 0, copies(data) if '--contre-epreuves' in args else {}
    for nom, copie in altere.items():
        try:
            controler(copie)
            print('[civil] contre-épreuve « %s » ACCEPTÉE à tort' % nom)
        except (ValueError, struct.error) as e:
            refus += copie != data
            print('[civil] contre-épreuve « %s » refusée : %s' % (nom, e))
    print('[civil] contre-épreuves refusées : %d/%d' % (refus, len(altere)) if altere else '[civil] VAT accepté')
    return 0 if refus == len(altere) else 1

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
