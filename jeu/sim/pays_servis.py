"""Le pays de chaque terre : une puissance de 1400, une terre de départ, ou un seigneur libre.

Une vue pure, recalculée : elle lit le maître du bourg de chaque cellule, le registre des
maisons et la puissance de chaque cellule, et ne pose rien sur le monde. La maison qui règne
sur un pays vient en second : la maison de Luxembourg règne sur trois pays (Saint-Empire,
Bohême, Hongrie), qui restent trois pays. Le tick ne lit pas cette vue.

Les identifiants de pays : `puissance-<id>` pour une puissance de la table, l'identifiant
de la maison pour une terre de départ (`seigneurie-<n>`) ou un seigneur libre.
"""
from dataclasses import dataclass

from sim.maisons import TableDesMaisons, charger_maisons
from sim.maisons_servies import _nom_de_maison
from sim.model import _NoBadSpatialField
from sim.puissances import TableDesPuissances, charger_table, puissances_depuis_monde
from sim.seigneuries import charger_seigneuries, numero_de_seigneurie

_SORTE_DEPART = "seigneurie"


@dataclass(frozen=True)
class SourcesDesPays(_NoBadSpatialField):
    """Ce que les pays lisent des tables de 1400 et de la carte, jamais des maîtres : lu une fois
    par monde servi, repassé à chaque prise."""
    table: TableDesPuissances
    maisons: TableDesMaisons
    seigneuries: tuple
    vue: dict


def sources_des_pays(monde, table=None, vue=None) -> SourcesDesPays:
    """Lit les tables ; la table des puissances et la vue déjà lues se repassent."""
    table = charger_table() if table is None else table
    vue = puissances_depuis_monde(monde, table=table) if vue is None else vue
    return SourcesDesPays(table, charger_maisons(), charger_seigneuries(table=table), vue)


def identifiant_de_puissance(puissance_id) -> str:
    """Le pays servi d'une puissance de la table."""
    return f"puissance-{puissance_id}"


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


def pays_d_origine(maison, vue, maisons) -> str:
    """Le pays d'une maison hors de toute terre : une terre de départ est son propre pays ; une
    autre maison prend la puissance de la cellule de son siège, sinon la puissance sur laquelle
    elle règne (un siège hors carte), sinon elle est son propre pays."""
    if maison.sorte == _SORTE_DEPART:
        return maison.id
    if maison.cell_id is not None and vue.get(maison.cell_id) is not None:
        return identifiant_de_puissance(vue[maison.cell_id])
    dirigees = _dirigees(maisons).get(maison.id)
    if dirigees:
        return identifiant_de_puissance(dirigees[0])
    return maison.id


def _chaine(par_id, maison) -> list:
    """Le maître, puis ses suzerains jusqu'à la racine, sans repasser par une maison vue."""
    chaine = [maison]
    while maison in par_id and par_id[maison].suzerain is not None and par_id[maison].suzerain not in chaine:
        maison = par_id[maison].suzerain
        chaine.append(maison)
    return chaine


def pays_des_terres(monde, vue, maisons) -> dict:
    """cell_id → pays de la terre, ou `None` pour une terre sans maître de bourg.

    La première terre de départ sur la chaîne du maître donne le pays ; sinon la puissance de
    la cellule, si la racine de la chaîne règne sur elle ; sinon le pays d'origine de la racine :
    une place prise par un autre pays passe au pays du preneur."""
    par_id = {m.id: m for m in monde.maisons}
    origines = {}
    pays = {}
    for cid, cellule in sorted(monde.cells.items()):
        maitre = next((l.maitre for l in cellule.lieux if l.rang == 0), None)
        if maitre is None:
            pays[cid] = None
            continue
        chaine = _chaine(par_id, maitre)
        racine = chaine[-1]
        if racine in par_id and racine not in origines:
            origines[racine] = pays_d_origine(par_id[racine], vue, maisons)
        pays[cid] = _pays_selon(chaine, vue.get(cid), par_id, maisons, origines)
    return pays


def _pays_selon(chaine, puissance, par_id, maisons, origines) -> str:
    """La règle du pays d'une terre, sur la chaîne de son maître et la puissance de sa cellule."""
    depart = next((m for m in chaine if m in par_id and par_id[m].sorte == _SORTE_DEPART), None)
    if depart is not None:
        return depart
    racine = chaine[-1]
    if puissance is not None and tete_de_puissance(puissance, maisons) == racine:
        return identifiant_de_puissance(puissance)
    return origines.get(racine, racine)


def fiches_des_pays(identifiants, monde, table, maisons, seigneuries, matiere) -> list:
    """`{id, nom, maison: {id, nom}, suzerain}` de chaque pays donné et de chaque suzerain
    cité, triés par identifiant. Le nom d'une puissance vient de la table, celui d'une terre de
    départ de sa seigneurie ; un nom absent vaut `None`. Seule une terre de départ a un
    suzerain : la puissance dont elle relève."""
    par_id = {m.id: m for m in monde.maisons}
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
        suzerain = None
        if identifiant.startswith(prefixe):
            puissance = puissances[int(identifiant.removeprefix(prefixe))]
            tete = tete_de_puissance(puissance.id, maisons)
            nom, maison = puissance.nom, {"id": tete, "nom": nom_de_maison(tete)}
        elif identifiant in par_id and par_id[identifiant].sorte == _SORTE_DEPART:
            seigneurie = par_numero[numero_de_seigneurie(identifiant)]
            nom, suzerain = seigneurie.nom, identifiant_de_puissance(seigneurie.suzerain)
            maison = {"id": identifiant, "nom": nom_de_maison(identifiant)}
            a_faire.append(suzerain)
        else:
            nom = nom_de_maison(identifiant)
            maison = {"id": identifiant, "nom": nom}
        fiches[identifiant] = {"id": identifiant, "nom": nom, "maison": maison, "suzerain": suzerain}
    return [fiches[i] for i in sorted(fiches)]
