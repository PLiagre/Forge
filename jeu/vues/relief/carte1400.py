"""La carte de 1400 lit la photographie : densités, puissances et terre choisie."""

from collections import defaultdict

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from vues.relief.raster import _bbox, _vers_pixel, index_des_cellules
from vues.relief.statistique import (
    _sans_accent, carte_de_statistique, plan_avec_legende, resume,
)

# Orange chaud : les frontières et les absences de puissance se détachent du bleu.
COULEUR_FRONTIERE = (244, 155, 52, 255)
# Rouge vif réservé au bord intérieur de la terre choisie.
COULEUR_CHOIX = (255, 40, 40, 255)
# Le fond sombre des cartouches garde leurs noms lisibles sur toute densité.
COULEUR_FOND = (13, 13, 13, 255)
# Le blanc porte les villes et le texte, distincts des deux couleurs de bord.
COULEUR_TEXTE = (245, 245, 245, 255)
# Le cercle noir distingue les villes sur les cellules claires.
COULEUR_CERCLE = (0, 0, 0, 255)
# Trois pixels de rayon rendent les points visibles sur la capture du journal.
RAYON_VILLE = 3
# Deux pixels vers l'intérieur soulignent le choix sans déborder de sa cellule.
EPAISSEUR_CHOIX = 2
# Deux pixels séparent le texte du bord de son cartouche.
MARGE_ETIQUETTE = 2
# Six pixels dégagent la fiche des bords de l'image.
MARGE_FICHE = 6
# Quinze pixels par ligne séparent les lignes de la police bitmap par défaut.
HAUTEUR_LIGNE = 15


class Carte1400Erreur(RuntimeError):
    """Photographie incomplète : la vue refuse d'inventer."""


def _verifier(document):
    for cle in ("terre_choisie", "villes_hors_carte"):
        if cle not in document:
            raise Carte1400Erreur(
                f"{cle} absent : photographie antérieure au lot #212 : rephotographier"
            )
    for cellule in document.get("cells", []):
        for cle in ("puissance", "villes"):
            if cle not in cellule:
                raise Carte1400Erreur(
                    f"{cle} absent pour cell_id={cellule.get('cell_id')} : "
                    "photographie antérieure au lot #212 : rephotographier"
                )
    choix = document["terre_choisie"]
    if choix is not None and not any(c["cell_id"] == choix["cell_id"] for c in document.get("cells", [])):
        raise Carte1400Erreur(f"terre_choisie : cell_id={choix['cell_id']} absent des cellules")


def lignes_de_fiche(document) -> list[str]:
    """Affiche les nombres de la fiche photographiée, sans recompter la terre."""
    _verifier(document)
    terre = document["terre_choisie"]
    if terre is None:
        lignes = ["Terre choisie : aucune — python3 -m forge --depart ID"]
    else:
        suzerain, maison = terre["suzerain"], terre["maison_du_suzerain"]
        voisins = sorted({v["puissance"]["nom"] if v["puissance"] else "sans puissance"
                          for v in terre["voisins"]})
        lignes = [
            f"Terre choisie : {terre['nom']} ; maison : {terre['maison']} ; religion : {terre['religion']}",
            f"Siège : {terre['siege']['nom']} ; cellule : {terre['cell_id']}",
            f"Habitants : {terre['habitants']} ; production : {terre['production_kg_par_tick']:.0f} kg par jour",
            f"Suzerain : {suzerain['nom'] if suzerain else 'aucun'} ; maison : {maison['nom'] if maison else 'aucune'}",
            f"Cellules du suzerain : {terre['cellules_du_suzerain']} ; habitants : {terre['habitants_du_suzerain']}",
            f"Voisins : {len(terre['voisins'])} ; puissances distinctes : {', '.join(voisins) or 'aucune'}",
        ]
    lignes.append(f"Villes hors carte : {', '.join(document['villes_hors_carte']) or 'aucune'}")
    sans = sum(c["puissance"] is None for c in document["cells"])
    lignes.append(
        f"orange : frontières ; pointillé : aucune puissance documentée ({sans} cellules) ; "
        "villes au centre de leur cellule"
    )
    return lignes


def _texte(texte):
    # La police bitmap ancienne ne porte pas non plus le tiret cadratin.
    return _sans_accent(texte).replace("—", "-")


def _lignes_ajustees(lignes, dessin, police, largeur):
    """Replie la fiche à la largeur réelle du texte, même sur un petit raster."""
    resultat = []
    disponible = max(1, largeur - 2 * MARGE_FICHE)
    for ligne in lignes:
        courant = ""
        for mot in _texte(ligne).split():
            candidat = f"{courant} {mot}".strip()
            if dessin.textbbox((0, 0), candidat, font=police)[2] <= disponible:
                courant = candidat
                continue
            if courant:
                resultat.append(courant)
            courant = ""
            for lettre in mot:
                if courant and dessin.textbbox((0, 0), courant + lettre, font=police)[2] > disponible:
                    resultat.append(courant)
                    courant = ""
                courant += lettre
        resultat.append(courant)
    return resultat


def carte_de_1400(document, *, lecture, largeur):
    """Une seule géométrie ; les compteurs décrivent les données et le dessin."""
    _verifier(document)
    carte = carte_de_statistique(document, lecture=lecture, largeur=largeur)
    image = plan_avec_legende(carte)
    index, _, cellules = index_des_cellules(document, largeur=largeur)
    hauteur, _ = index.shape
    decalage = len(image) - hauteur
    cles = np.array([-1] + [c["puissance"]["id"] if c["puissance"] else -1 for c in cellules])
    puissances_pixels = cles[index]
    frontiere = np.zeros(index.shape, dtype=bool)
    for a, b in ((np.s_[:, :-1], np.s_[:, 1:]), (np.s_[:-1, :], np.s_[1:, :])):
        frontiere[a] |= ((index[a] > 0) & (index[b] > 0)
                         & (puissances_pixels[a] != puissances_pixels[b]))
    fond = image[decalage:]
    fond[frontiere] = COULEUR_FRONTIERE
    lignes, colonnes = np.indices(index.shape)
    pointille = (index > 0) & (puissances_pixels == -1) & (lignes % 2 == 0) & (colonnes % 2 == 0)
    fond[pointille] = COULEUR_FRONTIERE

    choix = document["terre_choisie"]
    if choix is not None:
        rang = next(i for i, c in enumerate(cellules, 1) if c["cell_id"] == choix["cell_id"])
        masque = index == rang
        bord = np.zeros(index.shape, dtype=bool)
        marge = EPAISSEUR_CHOIX
        etendu = np.pad(masque, marge)
        for pas in range(1, marge + 1):
            for dy, dx in ((pas, 0), (-pas, 0), (0, pas), (0, -pas)):
                bord |= masque & ~etendu[marge + dy:marge + dy + hauteur, marge + dx:marge + dx + largeur]
        fond[bord] = COULEUR_CHOIX


    vignette = Image.fromarray(image, mode="RGBA")
    dessin, police = ImageDraw.Draw(vignette), ImageFont.load_default()
    bounds = _bbox(cellules)
    boites, omises = [], 0

    def position(cellule):
        centre = cellule["centroid"]
        x, y = _vers_pixel(centre["x_m"], centre["y_m"], bounds, largeur, hauteur)
        return x, y + decalage

    villes = [c for c in cellules if c["villes"]]
    points = [position(c) for c in villes]
    # Tous les cercles occupent leur place, même si leur nom sera omis.
    boites_points = [(x - RAYON_VILLE, y - RAYON_VILLE,
                      x + RAYON_VILLE, y + RAYON_VILLE) for x, y in points]

    def etiqueter(texte, x, y, centrer=False):
        nonlocal omises
        texte = _texte(texte)
        gauche, haut, droite, bas = dessin.textbbox((0, 0), texte, font=police)
        w, h = droite - gauche + 2 * MARGE_ETIQUETTE, bas - haut + 2 * MARGE_ETIQUETTE
        x = x - w // 2 if centrer else x + RAYON_VILLE + MARGE_ETIQUETTE
        y -= h // 2
        if w > largeur or h > hauteur:
            omises += 1
            return
        x = max(0, min(x, largeur - w))
        y = max(decalage, min(y, decalage + hauteur - h))
        boite = (x, y, x + w - 1, y + h - 1)
        if any(x <= droite and x + w - 1 >= gauche and y <= bas and y + h - 1 >= haut
               for gauche, haut, droite, bas in boites + boites_points):
            omises += 1
            return
        boites.append(boite)
        dessin.rectangle(boite, fill=COULEUR_FOND)
        dessin.text((x + MARGE_ETIQUETTE - gauche, y + MARGE_ETIQUETTE - haut),
                    texte, font=police, fill=COULEUR_TEXTE)

    # Population urbaine permise au point 5 du brief : classement et choix du nom.
    villes.sort(key=lambda c: (-max(v['population'] for v in c["villes"]), c["cell_id"]))
    for cellule in villes:
        ville = max(cellule["villes"], key=lambda v: v['population'])
        autres = len(cellule["villes"]) - 1
        nom = ville["nom"] + (f" +{autres}" if autres else "")
        x, y = position(cellule)
        etiqueter(nom, x, y)

    groupes = defaultdict(list)
    for cellule in cellules:
        if cellule["puissance"]:
            groupes[cellule["puissance"]["id"]].append(cellule)
    for identifiant in sorted(groupes, key=lambda i: (-len(groupes[i]), i)):
        groupe = groupes[identifiant]
        mx = sum(c["centroid"]["x_m"] for c in groupe) / len(groupe)
        my = sum(c["centroid"]["y_m"] for c in groupe) / len(groupe)
        centre = min(groupe, key=lambda c: (c["centroid"]["x_m"] - mx) ** 2 + (c["centroid"]["y_m"] - my) ** 2)
        etiqueter(centre["puissance"]["nom"], *position(centre), centrer=True)
    # Les points passent après les cartouches : chaque cellule urbaine reste visible.
    for x, y in points:
        dessin.ellipse((x - RAYON_VILLE, y - RAYON_VILLE, x + RAYON_VILLE, y + RAYON_VILLE),
                       fill=COULEUR_TEXTE, outline=COULEUR_CERCLE)
    image = np.array(vignette)

    fiche = _lignes_ajustees(lignes_de_fiche(document), dessin, police, largeur)
    bande = Image.new("RGBA", (largeur, 2 * MARGE_FICHE + HAUTEUR_LIGNE * len(fiche)), COULEUR_FOND)
    crayon = ImageDraw.Draw(bande)
    for i, ligne in enumerate(fiche):
        crayon.text((MARGE_FICHE, MARGE_FICHE + i * HAUTEUR_LIGNE), ligne, font=police, fill=COULEUR_TEXTE)
    compte = resume(carte)
    compte.update(
        puissances=len(groupes), cellules_sans_puissance=sum(c["puissance"] is None for c in cellules),
        pixels_de_frontiere=int(frontiere.sum()), villes_dessinees=sum(len(c["villes"]) for c in cellules),
        cellules_avec_villes=len(villes), villes_hors_carte=document["villes_hors_carte"],
        etiquettes_omises=omises, terre_choisie=choix["id"] if choix else None,
    )
    return np.concatenate([image, np.array(bande)], axis=0), compte
