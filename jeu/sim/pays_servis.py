"""Le pays de chaque terre : une puissance de 1400, une terre de départ, ou une terre sans État.

Une vue pure, recalculée : elle lit le maître du bourg de chaque cellule, le registre des
maisons, la puissance de chaque cellule et celle des lieux d'une cellule partagée
(`sim/frontieres.py`), et ne pose rien sur le monde. Le pays d'un lieu suit la règle de celui d'une
terre, sur le maître du lieu et la puissance du lieu. La maison qui règne
sur un pays vient en second : la maison de Luxembourg règne sur trois pays (Saint-Empire,
Bohême, Hongrie), qui restent trois pays. Le tick ne lit pas cette vue.

Les identifiants de pays : `puissance-<id>` pour une puissance de la table, l'identifiant
de la maison pour une terre de départ (`seigneurie-<n>`), `sans-etat-<id>` pour une terre sans
État de la table des frontières : ses seigneurs plausibles restent maîtres de leurs lieux, mais aucun
n'est servi comme un pays.
"""
from dataclasses import dataclass, field

from sim.maisons import TableDesMaisons, charger_maisons
from sim.maisons_servies import _nom_de_maison
from sim.model import _NoBadSpatialField
from sim.puissances import TableDesPuissances, charger_table, puissances_depuis_monde
from sim.seigneuries import charger_seigneuries, numero_de_seigneurie

_SORTE_DEPART = "seigneurie"
_PREFIXE_TERRE = "sans-etat-"


class PaysIntrouvable(ValueError):
    """Une maison dont le siège n'a ni puissance ni terre sans État, et qui ne règne sur aucune puissance."""


@dataclass(frozen=True)
class SourcesDesPays(_NoBadSpatialField):
    """Ce que les pays lisent des tables de 1400 et de la carte, jamais des maîtres : lu une fois
    par monde servi, repassé à chaque prise."""
    table: TableDesPuissances
    maisons: TableDesMaisons
    seigneuries: tuple
    vue: dict
    # (cell_id, rang) → puissance des lieux d'une cellule partagée ; ailleurs, celle de la cellule.
    lieux: dict = field(default_factory=dict)
    # (cell_id, rang) → terre sans État de chaque lieu sans pays ; `None` : à lire sur le monde.
    terres: dict | None = None
    # id → nom de chaque terre sans État ; `None` : à lire dans la table des frontières.
    noms_des_terres: dict | None = None


def sources_des_pays(monde, table=None, vue=None) -> SourcesDesPays:
    """Lit les tables ; la table des puissances et la vue déjà lues se repassent. Les places des
    cellules partagées se lisent une fois, pour la puissance et la terre sans État de leurs lieux."""
    from sim.frontieres import frontieres_du_monde, puissances_des_lieux, terres_des_lieux, villes_des_lieux
    table = charger_table() if table is None else table
    frontieres = frontieres_du_monde(monde, table)
    vue = puissances_depuis_monde(monde, table=table, frontieres=frontieres) if vue is None else vue
    villes = villes_des_lieux(monde, table, frontieres)
    return SourcesDesPays(table, charger_maisons(), charger_seigneuries(table=table), vue,
                          puissances_des_lieux(monde, table, frontieres, villes),
                          terres_des_lieux(monde, table, frontieres, villes),
                          {t.id: t.nom for t in frontieres.terres_sans_etat.values()})


def puissance_du_lieu(cell_id, rang, vue, lieux) -> int | None:
    """La puissance d'un lieu : celle de son lieu dans une cellule partagée, sinon celle de sa cellule."""
    lieux = {} if lieux is None else lieux
    return lieux[cell_id, rang] if (cell_id, rang) in lieux else vue.get(cell_id)


def identifiant_de_puissance(puissance_id) -> str:
    """Le pays servi d'une puissance de la table."""
    return f"puissance-{puissance_id}"


def identifiant_de_terre(terre_id) -> str:
    """Le pays servi d'une terre sans État."""
    return f"{_PREFIXE_TERRE}{terre_id}"


def _terres_du_monde(monde, terres):
    """Les terres sans État des lieux, données ou lues sur le monde."""
    if terres is not None:
        return terres
    from sim.frontieres import terres_des_lieux
    return terres_des_lieux(monde)


def tete_de_puissance(puissance_id, maisons) -> str:
    """La maison du registre qui règne sur la puissance : sa grande maison, ou son institution."""
    maison = maisons.par_puissance[puissance_id]
    return f"grande-{maison}" if maison is not None else f"institution-{puissance_id}"


def _dirigees(maisons) -> dict:
    """Maison du registre → puissances sur lesquelles elle règne, triées."""
    dirigees = {}
    for puissance_id in sorted(maisons.par_puissance):
        dirigees.setdefault(tete_de_puissance(puissance_id, maisons), []).append(puissance_id)
    return dirigees


def pays_d_origine(maison, vue, maisons, lieux=None, terres=None) -> str:
    """Le pays d'une maison hors de toute terre : une terre de départ est son propre pays ; une
    autre maison prend la puissance du lieu de son siège, sinon la puissance sur laquelle elle
    règne (un siège hors carte), sinon la terre sans État du lieu de son siège. Une maison qui n'a
    rien de cela est refusée en la nommant : aucun seigneur n'est servi comme son propre pays."""
    if maison.sorte == _SORTE_DEPART:
        return maison.id
    puissance = (None if maison.cell_id is None
                 else puissance_du_lieu(maison.cell_id, maison.rang, vue, lieux))
    if puissance is not None:
        return identifiant_de_puissance(puissance)
    dirigees = _dirigees(maisons).get(maison.id)
    if dirigees:
        return identifiant_de_puissance(dirigees[0])
    terre = None if terres is None else terres.get((maison.cell_id, maison.rang))
    if terre is None:
        raise PaysIntrouvable(f"{maison.id} : siège ({maison.cell_id}, {maison.rang}) sans puissance "
                              f"ni terre sans État")
    return identifiant_de_terre(terre)


def _chaine(par_id, maison) -> list:
    """Le maître, puis ses suzerains jusqu'à la racine, sans repasser par une maison vue."""
    chaine = [maison]
    while maison in par_id and par_id[maison].suzerain is not None and par_id[maison].suzerain not in chaine:
        maison = par_id[maison].suzerain
        chaine.append(maison)
    return chaine


def pays_des_terres(monde, vue, maisons, lieux=None, terres=None) -> dict:
    """cell_id → pays de la terre, ou `None` pour une terre sans maître de bourg.

    La première terre de départ sur la chaîne du maître donne le pays ; sinon la puissance de
    la cellule, si la racine de la chaîne règne sur elle ; sinon le pays d'origine de la racine :
    une place prise par un autre pays passe au pays du preneur. `terres` (`frontieres.terres_des_lieux`)
    se repasse quand il est déjà lu."""
    par_id = {m.id: m for m in monde.maisons}
    terres = _terres_du_monde(monde, terres)
    origines = {}
    pays = {}
    for cid, cellule in sorted(monde.cells.items()):
        maitre = next((l.maitre for l in cellule.lieux if l.rang == 0), None)
        pays[cid] = None if maitre is None else _pays_depuis(
            maitre, puissance_du_lieu(cid, 0, vue, lieux), par_id, vue, maisons, origines, lieux, terres)
    return pays


def pays_des_lieux(monde, vue, maisons, lieux=None, terres=None) -> dict:
    """(cell_id, rang) → pays de chaque lieu, ou `None` pour un lieu sans maître : la règle d'une
    terre, sur le maître du lieu et la puissance du lieu."""
    par_id = {m.id: m for m in monde.maisons}
    terres = _terres_du_monde(monde, terres)
    origines = {}
    pays = {}
    for cid, cellule in sorted(monde.cells.items()):
        for lieu in sorted(cellule.lieux, key=lambda l: l.rang):
            pays[cid, lieu.rang] = None if lieu.maitre is None else _pays_depuis(
                lieu.maitre, puissance_du_lieu(cid, lieu.rang, vue, lieux), par_id, vue, maisons, origines,
                lieux, terres)
    return pays


def pays_des_maisons(monde, vue, maisons, identifiants, lieux=None, terres=None) -> dict:
    """identifiant → pays de la maison : la même règle que pour une terre, sur la chaîne de la
    maison et la puissance du lieu de son siège (aucune hors carte). Pour la maison qui tient le
    lieu de son siège, c'est le pays de ce lieu."""
    par_id = {m.id: m for m in monde.maisons}
    terres = _terres_du_monde(monde, terres)
    origines = {}
    pays = {}
    for identifiant in sorted(set(identifiants)):
        maison = par_id.get(identifiant)
        puissance = (None if maison is None or maison.cell_id is None
                     else puissance_du_lieu(maison.cell_id, maison.rang, vue, lieux))
        pays[identifiant] = _pays_depuis(identifiant, puissance, par_id, vue, maisons, origines, lieux, terres)
    return pays


def regne(identifiant, pays, maisons) -> list:
    """Les pays dont la maison est la maison régnante, dans l'ordre des puissances : celles
    qu'elle dirige, puis son propre pays quand elle l'est elle-même (une terre de départ). Un
    seigneur d'une terre sans État ne règne sur aucun pays."""
    regnes = [identifiant_de_puissance(p) for p in _dirigees(maisons).get(identifiant, ())]
    return regnes + [identifiant] if pays == identifiant else regnes


def _pays_depuis(maison, puissance, par_id, vue, maisons, origines, lieux=None, terres=None) -> str:
    """Le pays d'après la chaîne qui part de `maison` ; `origines` garde le pays d'origine de chaque racine lue."""
    chaine = _chaine(par_id, maison)
    racine = chaine[-1]
    if racine in par_id and racine not in origines:
        origines[racine] = pays_d_origine(par_id[racine], vue, maisons, lieux, terres)
    return _pays_selon(chaine, puissance, par_id, maisons, origines)


def _pays_selon(chaine, puissance, par_id, maisons, origines) -> str:
    """La règle du pays d'une terre, sur la chaîne de son maître et la puissance de sa cellule."""
    depart = next((m for m in chaine if m in par_id and par_id[m].sorte == _SORTE_DEPART), None)
    if depart is not None:
        return depart
    racine = chaine[-1]
    if puissance is not None and tete_de_puissance(puissance, maisons) == racine:
        return identifiant_de_puissance(puissance)
    return origines.get(racine, racine)


def fiches_des_pays(identifiants, monde, table, maisons, seigneuries, matiere, noms_des_terres=None) -> list:
    """`{id, nom, maison: {id, nom}, suzerain, ensemble}` de chaque pays donné et de chaque suzerain
    cité, triés par identifiant. Le nom d'une puissance vient de la table, celui d'une terre de
    départ de sa seigneurie, celui d'une terre sans État de la table des frontières
    (`noms_des_terres`, lu dans la table quand il n'est pas donné) ; un nom absent vaut `None`.
    Le suzerain d'une terre de départ est la puissance dont elle relève ; celui d'une puissance, le
    suzerain que la table déclare. Une terre sans État n'a ni maison (`maison` vaut `None`) ni
    suzerain. `ensemble` est celui que la table déclare pour une puissance (« Saint-Empire »),
    `None` pour une autre puissance, une terre de départ ou une terre sans État."""
    par_id = {m.id: m for m in monde.maisons}
    if noms_des_terres is None and any(i.startswith(_PREFIXE_TERRE) for i in identifiants):
        from sim.frontieres import charger_frontieres
        noms_des_terres = {t.id: t.nom for t in charger_frontieres(table=table).terres_sans_etat.values()}
    puissances = {p.id: p for p in table.puissances}
    par_numero = {s.id: s for s in seigneuries}
    prefixe = identifiant_de_puissance("")

    def nom_de_maison(identifiant):
        maison = par_id.get(identifiant)
        return None if maison is None else _nom_de_maison(matiere, maison)

    fiches, a_faire = {}, sorted(set(identifiants))
    while a_faire:
        identifiant = a_faire.pop()
        if identifiant in fiches:
            continue
        suzerain = ensemble = None
        if identifiant.startswith(prefixe):
            puissance = puissances[int(identifiant.removeprefix(prefixe))]
            tete = tete_de_puissance(puissance.id, maisons)
            nom, maison = puissance.nom, {"id": tete, "nom": nom_de_maison(tete)}
            ensemble = puissance.ensemble
            if puissance.suzerain is not None:
                suzerain = identifiant_de_puissance(puissance.suzerain)
                a_faire.append(suzerain)
        elif identifiant.startswith(_PREFIXE_TERRE):
            nom, maison = noms_des_terres.get(identifiant.removeprefix(_PREFIXE_TERRE)), None
        elif identifiant in par_id and par_id[identifiant].sorte == _SORTE_DEPART:
            seigneurie = par_numero[numero_de_seigneurie(identifiant)]
            nom, suzerain = seigneurie.nom, identifiant_de_puissance(seigneurie.suzerain)
            maison = {"id": identifiant, "nom": nom_de_maison(identifiant)}
            a_faire.append(suzerain)
        else:
            nom = nom_de_maison(identifiant)
            maison = {"id": identifiant, "nom": nom}
        fiches[identifiant] = {"id": identifiant, "nom": nom, "maison": maison, "suzerain": suzerain,
                               "ensemble": ensemble}
    return [fiches[i] for i in sorted(fiches)]
