"""Les pays que le joueur peut prendre : une vue pure du registre et des maîtres de lieux.

Une maison est jouable si elle n'est pas une institution (république, Église,
ordre : elles élisent leur chef) et si au moins un lieu du monde l'a pour
maître actuel. Rien ne s'écrit ici, rien ne se tire au hasard.
"""
import re

from sim.puissances import charger_table
from sim.seigneuries import numero_de_seigneurie

_RAISONS_DES_INSTITUTIONS = {
    "république": "une république élit ses magistrats",
    "Église": "l'Église élit ses prélats",
    "ordre": "un ordre élit son maître",
}


def _lieux_tenus(monde) -> dict:
    """Nombre de lieux dont chaque maison est maître actuel, relu sur les cellules."""
    tenus = {}
    for cellule in monde.cells.values():
        for lieu in cellule.lieux:
            if lieu.maitre is not None:
                tenus[lieu.maitre] = tenus.get(lieu.maitre, 0) + 1
    return tenus


def _raison_d_institution(maison, table):
    """La raison d'une institution (nature relue dans la table des puissances), sinon None."""
    if maison.sorte != "institution":
        return None
    trouve = re.fullmatch(r"institution-(\d+)", maison.id)
    nature = None
    if trouve is not None:
        nature = next((p.nature for p in table.puissances if p.id == int(trouve.group(1))), None)
    explication = _RAISONS_DES_INSTITUTIONS.get(nature)
    if explication is None:
        raise ValueError(f"institution {maison.id} ({maison.nom}) : nature inconnue : {nature!r}")
    return f"maison non jouable : {maison.id} ({maison.nom}), {explication}"


def raison_de_refus(monde, identifiant):
    """`None` si la maison est jouable, sinon la raison de son refus."""
    maison = None
    if isinstance(identifiant, str):
        maison = next((m for m in monde.maisons if m.id == identifiant), None)
    if maison is None:
        return f"maison inconnue ou mal formée : {identifiant!r}"
    raison = _raison_d_institution(maison, charger_table())
    if raison is not None:
        return raison
    if _lieux_tenus(monde).get(identifiant, 0) == 0:
        return f"maison sans lieu : {identifiant}"
    return None


_ORDRE_DES_SORTES = ("seigneurie", "grande maison")  # puis les petits seigneurs (`plausible`)


def _rang(maison):
    """Les six seigneuries de départ par numéro, puis les grandes maisons, puis les petits seigneurs."""
    rang = (_ORDRE_DES_SORTES.index(maison.sorte) if maison.sorte in _ORDRE_DES_SORTES
            else len(_ORDRE_DES_SORTES))
    if maison.sorte == "seigneurie":
        return (rang, numero_de_seigneurie(maison.id), "")
    return (rang, 0, maison.id)


def _siege(maison, noms) -> dict:
    """Le siège : `nom`, celui du registre (la capitale ou le siège sourcés), et `lieu`, le nom servi
    du lieu dans les noms de sa cellule. Un petit seigneur n'a que le nom servi : son registre
    reprend son identifiant. Hors carte, ni lieu ni cellule."""
    if maison.cell_id is None:
        return {"nom": maison.siege, "lieu": None, "cell_id": None}
    lieux = noms.get(maison.cell_id, {}).get("lieux", ())
    lieu = next((l["nom"] for l in lieux if l["rang"] == maison.rang), None)
    return {"nom": lieu if maison.sorte == "plausible" else maison.siege, "lieu": lieu, "cell_id": maison.cell_id}


def _pays_du_suzerain(maison, pays, fiches, pays_des_suzerains):
    """Le pays au nom duquel le suzerain tient la maison : celui de la maison quand le suzerain y
    règne (un seigneur de Hongrie tenu par Luxembourg), sinon la puissance dont relève la terre de
    départ (Wurtemberg relève du Saint-Empire), sinon le pays du suzerain lui-même."""
    fiche = fiches[pays]
    if fiche["maison"] is not None and fiche["maison"]["id"] == maison.suzerain:
        return pays
    if fiche["suzerain"] is not None:
        return fiche["suzerain"]
    return pays_des_suzerains[maison.suzerain]


def _suzerain_du_pays(maison, fiche, fiches):
    """Le suzerain qu'une racine sert par son pays : la tête du pays suzerain que la table déclare,
    quand la maison règne sur son pays. L'hommage n'entre pas dans le registre : la maison reste
    une racine. Une terre sans État n'a ni maison ni suzerain."""
    if (maison.suzerain is not None or fiche["maison"] is None or fiche["maison"]["id"] != maison.id
            or fiche["suzerain"] is None):
        return None
    suzerain = fiches[fiche["suzerain"]]
    return {"id": suzerain["maison"]["id"], "nom": suzerain["maison"]["nom"],
            "pays": {"id": suzerain["id"], "nom": suzerain["nom"]}}


def maisons_jouables(monde, sources=None, noms=None, villes=None) -> list:
    """Les maisons jouables, dans l'ordre où le choix les propose, chacune avec ce que le joueur
    prend : son pays, les pays où elle règne, son siège, son suzerain et la ville de sa capitale.
    Le suzerain d'une racine est celui que la table déclare pour le pays où elle règne, s'il y en a un.

    `sources` (`pays_servis.sources_des_pays`), `noms` (`noms_depuis_monde`) et `villes`
    (`villes_3d.charger_villes_3d`) se repassent quand ils sont déjà lus. Une capitale n'est
    bâtie que si sa maison est déclarée dans la donnée des villes en 3D ; sinon sa raison le dit."""
    from types import SimpleNamespace
    from sim.maisons_servies import _nom_de_maison
    from sim.noms import avec_son_article, noms_depuis_monde
    from sim.pays_servis import fiches_des_pays, pays_des_maisons, regne, sources_des_pays
    from sim.villes_3d import charger_villes_3d, raison_sans_ville
    tenus = _lieux_tenus(monde)
    sources = sources_des_pays(monde) if sources is None else sources
    noms = noms_depuis_monde(monde, table=sources.table, vue=sources.vue) if noms is None else noms
    villes = charger_villes_3d() if villes is None else villes
    matiere = SimpleNamespace(noms=noms)
    par_id = {m.id: m for m in monde.maisons}
    jouables = sorted((m for m in monde.maisons
                       if _raison_d_institution(m, sources.table) is None and tenus.get(m.id, 0) > 0), key=_rang)
    suzerains = [m.suzerain for m in jouables if m.suzerain in par_id]
    pays = pays_des_maisons(monde, sources.vue, sources.maisons, [m.id for m in jouables] + suzerains,
                            sources.lieux, sources.terres)
    regnes = {m.id: regne(m.id, pays[m.id], sources.maisons) for m in jouables}
    fiches = {f["id"]: f for f in fiches_des_pays(
        set(pays.values()) | {p for r in regnes.values() for p in r},
        monde, sources.table, sources.maisons, sources.seigneuries, matiere, sources.noms_des_terres)}

    def court(identifiant):
        return {"id": identifiant, "nom": fiches[identifiant]["nom"]}

    scenes = {v.maison: v.scene for v in villes.capitales}
    baties = ", ".join(sorted(par_id[m].siege for m in scenes if m in par_id))
    resultat = []
    for m in jouables:
        siege = _siege(m, noms)
        suzerain = None if m.suzerain not in par_id else {
            "id": m.suzerain, "nom": _nom_de_maison(matiere, par_id[m.suzerain]),
            "pays": court(_pays_du_suzerain(m, pays[m.id], fiches, pays))}
        if suzerain is None:
            suzerain = _suzerain_du_pays(m, fiches[pays[m.id]], fiches)
        batie = m.id in scenes
        resultat.append({
            "id": m.id, "nom": _nom_de_maison(matiere, m), "sorte": m.sorte, "lieux": tenus[m.id],
            "pays": court(pays[m.id]), "regne": [court(p) for p in regnes[m.id]],
            "siege": siege, "suzerain": suzerain,
            "ville": {"batie": batie, "scene": scenes.get(m.id),
                      "raison": None if batie else raison_sans_ville(villes, avec_son_article(siege["nom"]), baties)},
        })
    return resultat
