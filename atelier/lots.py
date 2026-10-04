"""L'état d'un lot, dérivé de GitHub, et l'action qui vient ensuite.

Un lot est une issue. Son état est une étiquette (idee, pret, en-cours,
bloque, livre), son jalon est un milestone (« J1 — Le pont »), sa machine est
l'étiquette `pc` quand il demande Unity ou Blender. Son travail est une
branche et une PR. Ce que la chaîne y a fait est écrit par le pilote, dans
les commentaires de la PR, sous une marque invisible :

    <!-- atelier {"role": "relecteur", "sha": "…", "verdict": "ACCEPTE"} -->

Rien n'est gardé ailleurs. Le pilote peut s'arrêter au milieu d'un tour : le
tour suivant relit GitHub et reprend où les faits disent qu'on en est.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
import unicodedata

from .projet import FAMILLE_DE_L_OUTIL, famille_du_modele

ETATS =("idee", "pret", "en-cours", "bloque", "livre")
ETIQUETTE_PC = "pc"
# Le milestone des lots qui ne servent aucun jalon. Son titre ne commence pas
# par « J » : le pilote ne le prend jamais pour le jalon courant.
RESERVE = "Réserve"
# L'étiquette qui y range un lot, d'un geste, même depuis le téléphone.
ETIQUETTE_RESERVE = "reserve"
_MARQUE = re.compile(r"<!-- atelier (\{.*?\}) -->", re.S)
_DEPEND = re.compile(r"^[ \t]*(?:#+[ \t]*)?D[ée]pend de[ \t]*:?[ \t]*(.*)$", re.I | re.M)
# La phrase que le pilote écrit dans chaque sous-lot d'une découpe.
_DECOUPE = re.compile(r"D[ée]coup[ée] du lot #(\d+)", re.I)
_JALON = re.compile(r"^J(\d+)\b")
# Dans CAP.md, un jalon est une section « ## Jalon 2 — Le monde de 1400 », et
# la réserve une section « ## La réserve ». Rien d'autre ne se devine.
_JALON_DU_CAP = re.compile(r"^##[ \t]+Jalon[ \t]+(\d+)[ \t]+[—–-][ \t]+(.+?)[ \t]*$", re.M)
_RESERVE_DU_CAP = re.compile(r"^##[ \t]+La r[ée]serve[ \t]*$", re.M | re.I)
ROLES_CODEURS = ("codeur", "codeur_3d", "mecanicien_master")


def slug(titre: str, longueur: int = 48) -> str:
    plat = unicodedata.normalize("NFKD", titre).encode("ascii", "ignore").decode()
    mots = re.sub(r"[^a-z0-9]+", "-", plat.lower()).strip("-")
    return mots[:longueur].rstrip("-") or "lot"


def numero_de_jalon(titre: str | None) -> int | None:
    m = _JALON.match(titre or "")
    return int(m.group(1)) if m else None


def marque(**champs) -> str:
    return f"<!-- atelier {json.dumps(champs, ensure_ascii=False, sort_keys=True)} -->"


def marques(commentaires: list[dict]) -> list[dict]:
    """Les marques du pilote, dans l'ordre des commentaires."""
    trouvees = []
    for c in commentaires or []:
        for brut in _MARQUE.findall(c.get("body") or ""):
            try:
                trouvees.append(json.loads(brut))
            except json.JSONDecodeError:
                continue
    return trouvees


@dataclass(frozen=True)
class Jalon:
    numero: int
    titre: str
    id: int
    ouvert: bool
    ouvertes: int
    fermees: int

    @property
    def pourcentage(self) -> int:
        total = self.ouvertes + self.fermees
        return round(100 * self.fermees / total) if total else 0


def jalons(bruts: list[dict]) -> list[Jalon]:
    trouves = []
    for m in bruts:
        n = numero_de_jalon(m.get("title"))
        if n is None:
            continue
        trouves.append(Jalon(numero=n, titre=m["title"], id=m["number"], ouvert=m.get("state") == "open",
                             ouvertes=m.get("open_issues", 0), fermees=m.get("closed_issues", 0)))
    return sorted(trouves, key=lambda j: j.numero)


def jalon_courant(liste: list[Jalon]) -> Jalon | None:
    """Le premier jalon ouvert, dans l'ordre de CAP.md."""
    return next((j for j in liste if j.ouvert), None)


def jalon_suivant(liste: list[Jalon], courant: Jalon | None) -> Jalon | None:
    """Le jalon ouvert qui suit le courant : le second de la fenêtre. Une
    machine qui n'a plus rien à prendre dans le courant y prend son travail."""
    if courant is None:
        return None
    return next((j for j in liste if j.ouvert and j.numero > courant.numero), None)


def troisieme_jalon(liste: list[Jalon], courant: Jalon | None) -> Jalon | None:
    """Le troisième jalon ouvert, le bout de la fenêtre. Une machine qui n'a
    plus rien dans les deux premiers y prend (Pilote._plus_loin)."""
    return jalon_suivant(liste, jalon_suivant(liste, courant))


def jalons_du_cap(cap: str) -> dict[int, str]:
    """Les jalons que CAP.md déclare : numéro → titre du milestone
    (« J2 — Le monde de 1400 »), tirés de ses sections « ## Jalon n — Titre ».
    Un CAP.md sans section de jalon n'en déclare aucun."""
    trouves: dict[int, str] = {}
    for m in _JALON_DU_CAP.finditer(cap or ""):
        trouves.setdefault(int(m.group(1)), f"J{m.group(1)} — {m.group(2)}")
    return dict(sorted(trouves.items()))


def accord_des_jalons(cap: str, bruts: list[dict]) -> list[tuple]:
    """Ce qu'il faut faire pour que les milestones disent ce que dit CAP.md :
    `("creer", titre)` ou `("renommer", numero, ancien, titre)`.

    Jamais de suppression ni de fermeture : un jalon atteint reste fermé, et
    un milestone que CAP.md ne nomme plus reste tel quel, avec ses issues.
    Deux milestones du même numéro : c'est l'ouvert qui porte le titre."""
    gestes: list[tuple] = []
    for n, titre in jalons_du_cap(cap).items():
        memes = [m for m in bruts if numero_de_jalon(m.get("title")) == n]
        if not memes:
            gestes.append(("creer", titre))
            continue
        garde = next((m for m in memes if m.get("state") == "open"), None) or max(memes, key=lambda m: m["number"])
        if garde.get("title") != titre:
            gestes.append(("renommer", garde["number"], garde.get("title"), titre))
    if _RESERVE_DU_CAP.search(cap or "") and not any(m.get("title") == RESERVE for m in bruts):
        gestes.append(("creer", RESERVE))
    return gestes


@dataclass(frozen=True)
class Lot:
    numero: int
    titre: str
    corps: str
    etiquettes: tuple[str, ...]
    jalon: int | None
    jalon_titre: str | None

    @classmethod
    def de(cls, issue: dict) -> "Lot":
        etiquettes = tuple(e["name"] for e in issue.get("labels") or [])
        titre_jalon = (issue.get("milestone") or {}).get("title")
        return cls(numero=issue["number"], titre=issue["title"], corps=issue.get("body") or "",
                   etiquettes=etiquettes, jalon=numero_de_jalon(titre_jalon), jalon_titre=titre_jalon)

    @property
    def etat(self) -> str:
        return next((e for e in ETATS if e in self.etiquettes), "idee")

    @property
    def machine(self) -> str:
        return "pc" if ETIQUETTE_PC in self.etiquettes else "vps"

    @property
    def slug(self) -> str:
        return slug(self.titre)

    def branche(self, prefixe: str) -> str:
        return f"{prefixe}{self.numero}-{self.slug}"

    def brief(self, dossier: str) -> str:
        return f"{dossier}/{self.numero}-{self.slug}.md"

    @property
    def dependances(self) -> frozenset[int]:
        """Les issues que ce lot attend : « Dépend de : #12, #13 » dans son texte,
        ou le champ « Dépend de » du formulaire (la valeur sur les lignes qui
        suivent, jusqu'au titre suivant)."""
        trouvees: set[int] = set()
        for m in _DEPEND.finditer(self.corps):
            lignes = self.corps[m.start():].splitlines()
            bloc = [lignes[0]]
            # « Dépend de : #12 » tient sur sa ligne ; le champ du formulaire
            # porte sa valeur au paragraphe suivant, jusqu'au titre suivant.
            if not re.search(r"#\d+", lignes[0]):
                for ligne in lignes[1:]:
                    if ligne.startswith("##") or (not ligne.strip() and any(b.strip() for b in bloc[1:])):
                        break
                    bloc.append(ligne)
            trouvees |= {int(n) for n in re.findall(r"#(\d+)", " ".join(bloc))}
        return frozenset(trouvees)

    @property
    def decoupe_de(self) -> int | None:
        """Le lot dont celui-ci est un morceau, quand le chef l'a découpé."""
        m = _DECOUPE.search(self.corps)
        return int(m.group(1)) if m else None


def bloquantes(ouvertes: list[Lot], fermees: list[Lot] = ()) -> frozenset[int]:
    """Les issues qu'un lot qui en dépend attend encore : chaque issue
    ouverte, et un lot découpé tant qu'un de ses descendants est ouvert. Sans
    cela, « Dépend de : #119 » se libérait dès la découpe de #119, avant ses
    morceaux (mesuré le 28 septembre 2026 sur #120). Les découpes s'emboîtent
    (#119 → #183 → #185) : les lots fermés disent de qui ils descendent."""
    parents = {l.numero: l.decoupe_de for l in (*ouvertes, *fermees) if l.decoupe_de is not None}
    resultat = {l.numero for l in ouvertes}
    for lot in ouvertes:
        n, vus = lot.decoupe_de, set()
        while n is not None and n not in vus:
            vus.add(n)
            resultat.add(n)
            n = parents.get(n)
    return frozenset(resultat)


def a_prendre(lots: list[Lot], jalon: int | None, machine_libre: dict[str, bool],
              ouvertes: frozenset[int] = frozenset()) -> Lot | None:
    """Le lot suivant du jalon `jalon` : `pret` d'abord, puis `idee`, dans
    l'ordre des numéros d'issue. Une machine occupée ne prend rien ; un lot
    dont une dépendance est encore ouverte attend ; un lot marqué `reserve`
    sort de son jalon, il ne se prend pas."""
    if jalon is None:
        return None
    for etat in ("pret", "idee"):
        for lot in sorted(lots, key=lambda l: l.numero):
            if (lot.jalon == jalon and lot.etat == etat and machine_libre.get(lot.machine, False)
                    and not (lot.dependances & ouvertes) and ETIQUETTE_RESERVE not in lot.etiquettes):
                return lot
    return None


# La marque que porte le lot ouvert par le pilote pour faire découper un jalon.
ETAT_DECOUPE_JALON = "decoupe-jalon"

# Les options qu'une ligne de découpe porte à sa fin, dans n'importe quel
# ordre : « :: pc » ou « :: vps » (sa machine), « :: après 1, 3 » ou
# « :: après rien » (les sous-lots de la même liste qu'il attend).
_OPTION_MACHINE = re.compile(r"\s*::\s*(pc|vps)\s*$", re.I)
_OPTION_APRES = re.compile(r"\s*::\s*apr[èe]s\s*:?\s*(rien|[\d\s,#et]+?)\s*$", re.I)


@dataclass(frozen=True)
class SousLot:
    """Une ligne de découpe du chef. `apres` : None quand elle ne dit rien
    (le sous-lot part tout de suite), () pour « après rien », sinon les
    rangs, dans la liste, des sous-lots qu'il attend."""

    titre: str
    quoi: str
    machine: str
    apres: tuple[int, ...] | None = None


def sous_lot(titre: str, quoi: str, machine_par_defaut: str) -> SousLot:
    """Lit « <titre> :: <ce qu'il fait> [:: pc|vps] [:: après …] ». Sans
    machine, le sous-lot garde celle du lot découpé."""
    machine, apres = None, None
    while True:
        m = _OPTION_MACHINE.search(quoi)
        if m and machine is None:
            machine, quoi = m.group(1).lower(), quoi[:m.start()]
            continue
        m = _OPTION_APRES.search(quoi)
        if m and apres is None:
            valeur = m.group(1).strip().lower()
            apres = () if valeur == "rien" else tuple(int(n) for n in re.findall(r"\d+", valeur))
            quoi = quoi[:m.start()]
            continue
        break
    return SousLot(titre.strip(), quoi.strip(), machine or machine_par_defaut, apres)


def dependances_des_sous_lots(sous: list[SousLot], *, preuve_en_dernier: bool = False) -> list[tuple[int, ...]]:
    """Pour chaque sous-lot (rang 1…n), les rangs des sous-lots qu'il attend.

    Sans « après », ou « après rien », il part tout de suite ; « après 1, 3 »,
    quand 1 et 3 sont livrés. Jusqu'au 1er octobre 2026, une ligne muette
    attendait la précédente : J2 et J4 sont devenus des files de sept lots,
    et le VPS, qui en tient deux, n'en faisait avancer qu'un.
    Des sous-lots qui ne s'attendent pas avancent en même temps. Le dernier
    d'une découpe de jalon porte la preuve du jalon : il attend tous les
    autres, quoi que dise sa ligne. Un rang qui ne précède pas le sous-lot se
    refuse (ValueError) : les issues naissent dans l'ordre de la liste, et une
    dépendance vers l'avant ne se devine pas."""
    rangs: list[tuple[int, ...]] = []
    for i, s in enumerate(sous, start=1):
        if preuve_en_dernier and i == len(sous):
            rangs.append(tuple(range(1, i)))
            continue
        if s.apres is None:
            rangs.append(())
            continue
        fautifs = [k for k in s.apres if not 1 <= k < i]
        if fautifs:
            raise ValueError(f"le sous-lot {i} (« {s.titre} ») attend {', '.join(map(str, fautifs))}, "
                             "qui ne le précède pas dans la liste")
        rangs.append(tuple(sorted(set(s.apres))))
    return rangs


def jalon_a_decouper_par(lot: Lot) -> int | None:
    """Le jalon que ce lot fait découper, quand le pilote l'a ouvert pour ça."""
    for m in marques([{"body": lot.corps}]):
        if m.get("role") == "pilote" and m.get("etat") == ETAT_DECOUPE_JALON:
            return m.get("jalon")
    return None


def a_decouper(jalon: Jalon | None, cap: str, ouvertes: list[Lot], fermees: list[Lot] = ()) -> bool:
    """Un jalon de la fenêtre (le courant, ou le suivant quand une machine
    n'a plus rien dans le courant) se fait découper, une seule fois, quand
    CAP.md le décrit et qu'il n'a encore aucun lot prêt, en cours ou livré :
    un jalon que personne n'a planifié ne laisse pas la chaîne sans travail,
    et un jalon lancé à la main ne se redécoupe pas."""
    if jalon is None or jalon.numero not in jalons_du_cap(cap):
        return False
    siens = [l for l in (*ouvertes, *fermees) if l.jalon == jalon.numero]
    if any(jalon_a_decouper_par(l) == jalon.numero for l in siens):
        return False
    ouverts = {l.numero for l in ouvertes}
    # Un lot fermé encore « en-cours » vient d'être fusionné : le pilote le
    # livre dans ce même tour, il compte déjà comme livré.
    return not any(l.etat in ("livre", "en-cours") or (l.numero in ouverts and l.etat == "pret")
                   for l in siens if "lot" in l.etiquettes)


def corps_de_la_decoupe(jalon: Jalon, avant: list[int], courant: Jalon | None = None) -> str:
    """Le texte du lot qui fait découper un jalon. Les lots déjà ouverts dans
    le jalon passent d'abord : la découpe vient après eux et les complète.
    Un jalon découpé en avance (il suit le `courant`) le dit : ses lots
    partent pendant que le courant se termine."""
    en_avance = courant is not None and jalon.numero > courant.numero
    if en_avance:
        tete = (f"Le jalon {jalon.titre} n'a encore aucun lot prêt, et une machine n'a plus rien à prendre "
                f"avant lui depuis le jalon courant, {courant.titre} : il se découpe en avance. Ses lots partent "
                "pendant que les jalons d'avant se terminent ; ils ne s'appuient sur rien que ceux-ci doivent "
                "encore livrer. Place d'abord ceux qui ne s'appuient que sur ce qui est déjà sur master.")
    else:
        tete = f"Le jalon courant, {jalon.titre}, n'a encore aucun lot prêt : personne ne l'a découpé."
    lignes = [
        tete,
        "",
        "Ce lot ne se code pas. Le chef le découpe (« DECISION: DECOUPE ») d'après la section "
        f"« Jalon {jalon.numero} » de `CAP.md` et d'après `docs/VISION.md` : les lots qu'il faut, dans "
        "l'ordre où ils se font, chacun à la taille d'un lot. Le dernier porte la preuve du jalon et sa "
        "capture au journal : il attend tous les autres. Un lot qui demande Unity ou Blender finit sa ligne "
        "par « :: pc ». Les lots qui ne s'attendent pas avancent en même temps : chaque ligne dit ceux "
        "qu'elle attend vraiment (« :: après 1, 3 », ou « :: après rien »).",
    ]
    if avant:
        lignes += ["", "Les lots déjà ouverts dans ce jalon passent d'abord ; la découpe les complète, "
                   "elle ne les refait pas.", "", "Dépend de : " + ", ".join(f"#{n}" for n in avant)]
    lignes += ["", marque(role="pilote", etat=ETAT_DECOUPE_JALON, jalon=jalon.numero)]
    return "\n".join(lignes)


@dataclass(frozen=True)
class Action:
    nom: str
    raison: str = ""
    essai: int = 0


# Ce que le PC répond à un envoi. `attente` : aucun de ses agents n'a pu
# répondre (quota, session, installation) ; ce n'est pas un passage du codeur.
# `reponse` : le codeur a répondu à une revue sans changer de fichier.
REPONSES_PC = ("fait", "echec", "attente", "reponse")
# Après une attente du PC, on renvoie au bout d'une heure ; sans réponse du
# tout (PC éteint : GitHub garde le travail en file un jour), au bout de 24 h.
HEURES_ATTENTE_PC = 1
HEURES_SILENCE_PC = 24


def depuis_reprise(liste: list[dict]) -> list[dict]:
    """Les marques depuis la dernière reprise : un lot bloqué que le
    propriétaire remet « pret » recompte ses essais de zéro."""
    for i in range(len(liste) - 1, -1, -1):
        if liste[i].get("etat") == "reprise":
            return liste[i + 1:]
    return list(liste)


def echecs_du_chef(liste: list[dict]) -> int:
    """Les échecs du chef sur une issue, depuis son dernier blocage ou sa
    dernière reprise : remettre « pret » un lot bloqué redonne ses essais."""
    debut = 0
    for i, m in enumerate(liste):
        if m.get("etat") in ("bloque", "reprise"):
            debut = i + 1
    return sum(1 for m in liste[debut:] if m.get("role") == "chef" and m.get("etat") == "echec")


def action_suivante(pr: dict | None, etat_ci: str, liste: list[dict], *,
                    corrections_max: int, role_codeur: str = "codeur",
                    heures_depuis_envoi_pc: float | None = None,
                    heures_depuis_attente_pc: float | None = None) -> Action:
    """Ce que le pilote fait ensuite pour un lot en cours. Fonction pure.

    Un lot a droit à 1 + `corrections_max` passages du codeur : le premier,
    puis une correction par CI rouge ou relecture « CORRIGER ». Au-delà, il
    est bloqué, avec sa raison. Les compteurs partent de la dernière reprise ;
    l'état du travail (code écrit, verdicts), de tout l'historique.
    """
    if pr is None:
        return Action("chef")
    if pr.get("state") == "MERGED" or pr.get("mergedAt"):
        return Action("livrer")
    if pr.get("state") == "CLOSED":
        return Action("bloquer", "la PR a été fermée sans fusion")
    tete = pr.get("headRefOid") or ""
    codeurs = [m for m in depuis_reprise(liste) if m.get("role") == role_codeur]
    essais = sum(1 for m in codeurs if m.get("etat") in ("fait", "echec", "reponse"))
    max_essais = 1 + corrections_max

    # Un envoi au PC attend sa réponse ; sans réponse en un jour, on renvoie.
    envois = sum(1 for m in codeurs if m.get("etat") == "envoye")
    reponses = sum(1 for m in codeurs if m.get("etat") in REPONSES_PC)
    if envois > reponses:
        if heures_depuis_envoi_pc is not None and heures_depuis_envoi_pc > HEURES_SILENCE_PC:
            return Action("relancer_pc", "le PC n'a pas répondu en 24 h", essai=essais)
        return Action("attendre_pc", "le travail est parti sur le PC")
    if (codeurs and codeurs[-1].get("etat") == "attente" and heures_depuis_attente_pc is not None
            and heures_depuis_attente_pc < HEURES_ATTENTE_PC):
        return Action("attendre_pc", "aucun agent du PC n'a pu répondre : renvoi au bout d'une heure")

    if pr.get("mergeable") == "CONFLICTING":
        return Action("conflit", "la branche est en conflit avec la base")

    reussis = [m for m in liste if m.get("role") == role_codeur and m.get("etat") == "fait"]
    if not reussis:
        if essais >= max_essais:
            return Action("bloquer", f"le codeur a échoué {essais} fois")
        return Action("coder", essai=essais)

    if etat_ci == "attente":
        return Action("attendre_ci")
    if etat_ci == "rouge":
        if essais >= max_essais:
            return Action("bloquer", f"CI rouge après {essais - 1} correction(s)")
        return Action("corriger_ci", "CI rouge", essai=essais)

    verdicts = [m for m in liste if m.get("role") == "relecteur" and m.get("sha") == tete]
    # Une relecture sans verdict (délai, verdict illisible) n'est pas un
    # « CORRIGER » : elle se rejoue, et `_relire` bloque à deux échecs. Le
    # 30 septembre 2026, elle renvoyait au codeur une revue vide (#126).
    if not verdicts or not verdicts[-1].get("verdict"):
        return Action("relire")
    dernier = verdicts[-1].get("verdict")
    # Le codeur a répondu à cette revue sans changer de fichier (le constat ne
    # demandait qu'une réponse écrite) : le relecteur relit avec sa réponse.
    # Le 1er octobre 2026, #270 s'est bloqué sur un « n'a rien changé ».
    i_verdict = max(i for i, m in enumerate(liste) if m.get("role") == "relecteur" and m.get("sha") == tete)
    i_reponse = max((i for i, m in enumerate(liste) if m.get("role") == role_codeur and m.get("etat") == "reponse"),
                    default=-1)
    if dernier == "CORRIGER" and i_reponse > i_verdict:
        return Action("relire")
    if dernier == "ACCEPTE":
        if pr.get("autoMergeRequest"):
            return Action("attendre_fusion")
        return Action("fusionner")
    if essais >= max_essais:
        return Action("bloquer", f"relecture « CORRIGER » après {essais - 1} correction(s)")
    return Action("corriger_relecture", "relecture « CORRIGER »", essai=essais)


# La question que le chef pose au propriétaire, quand un lot demande une
# décision que lui seul peut prendre (un test ou une règle du monde à
# changer) : « DECISION: QUESTION :: <la question> », une ligne par réponse
# possible, « - A :: <la réponse> :: <ce qu'elle coûte> », et
# « RECOMMANDATION :: A :: <pourquoi> ». Le 29 septembre 2026, #209 a attendu
# une décision que le journal ne posait pas : « lire sa raison ».
_OPTION = re.compile(r"^\s*-\s*([A-Z])\s*::\s*(.+?)(?:\s*::\s*(.+?))?\s*$", re.M)
_RECOMMANDATION = re.compile(r"^\s*RECOMMANDATION\s*::\s*([A-Z])\s*(?:::\s*(.+?))?\s*$", re.M)
# « NATURE :: jeu » ou « NATURE :: technique ». Le propriétaire tranche ce qui
# oriente le jeu ; une question technique (un test, un format, une règle de
# code) suit la recommandation sans l'attendre : le 3 octobre 2026, il
# répondait toujours la recommandée, et J2, J3, J4 attendaient ses lettres.
# Sans nature lisible, la question est « jeu » : dans le doute, on demande.
_NATURE = re.compile(r"^\s*NATURE\s*::\s*(jeu|technique)\b", re.M | re.I)
NATURE_JEU, NATURE_TECHNIQUE = "jeu", "technique"
# La marque du pilote qui a suivi seul la recommandation d'une question
# technique ; au-delà de DECISIONS_SEULES_MAX par lot, la question suivante
# va au propriétaire : un lot qui pose question sur question tourne en rond.
ETAT_DECISION = "decision"
DECISIONS_SEULES_MAX = 2


@dataclass(frozen=True)
class Question:
    texte: str
    options: tuple[tuple[str, str, str], ...] = ()  # (lettre, réponse, ce qu'elle coûte)
    recommandation: tuple[str, str] | None = None    # (lettre, pourquoi)
    nature: str = NATURE_JEU

    def marque(self) -> dict:
        return {"question": self.texte, "options": [list(o) for o in self.options],
                "recommandation": list(self.recommandation) if self.recommandation else None,
                "nature": self.nature}

    @classmethod
    def de_marque(cls, m: dict) -> "Question | None":
        if not m.get("question"):
            return None
        reco = m.get("recommandation")
        return cls(texte=m["question"], options=tuple(tuple(o) for o in m.get("options") or []),
                   recommandation=tuple(reco) if reco else None, nature=m.get("nature") or NATURE_JEU)

    def se_decide_seule(self) -> bool:
        """Une question technique dont la recommandation nomme une réponse."""
        return self.nature == NATURE_TECHNIQUE and self.recommandation is not None

    def reponse_recommandee(self) -> str:
        lettre = self.recommandation[0] if self.recommandation else ""
        return next((r for l, r, _ in self.options if l == lettre), "")

    def en_une_ligne(self) -> str:
        """Pour le journal : la question, ses réponses, et le choix du chef."""
        ligne = self.texte.rstrip(" ?") + " ?"
        if self.options:
            ligne += " " + " ; ".join(f"{l} : {r}" for l, r, _ in self.options) + "."
        if self.recommandation:
            lettre, pourquoi = self.recommandation
            ligne += f" Le chef recommande {lettre}" + (f" ({pourquoi})" if pourquoi else "") + "."
        return ligne


def question_du_chef(texte: str, question: str) -> Question:
    """La question du chef, lue dans sa réponse : ses options et sa
    recommandation, s'il en a écrit. Une recommandation qui ne nomme aucune
    des options est ignorée."""
    options = tuple((l, r.strip(), (c or "").strip()) for l, r, c in _OPTION.findall(texte))
    reco = None
    trouvees = _RECOMMANDATION.findall(texte)
    if trouvees:
        lettre, pourquoi = trouvees[-1]
        if not options or lettre in {o[0] for o in options}:
            reco = (lettre, (pourquoi or "").strip())
    natures = _NATURE.findall(texte)
    return Question(texte=question.strip() or "le chef n'a pas écrit sa question", options=options,
                    recommandation=reco, nature=natures[-1].lower() if natures else NATURE_JEU)


def decisions_seules(commentaires: list[dict]) -> int:
    """Les questions techniques que le pilote a déjà tranchées seul sur ce lot."""
    return sum(1 for m in marques(commentaires) if m.get("role") == "pilote" and m.get("etat") == ETAT_DECISION)


def reponse_apres_blocage(commentaires: list[dict]) -> bool:
    """Un humain a-t-il écrit sur l'issue depuis son dernier blocage ? Ce
    commentaire vaut réponse : le pilote remet le lot en route. Un lot
    bloqué à la main, sans marque du pilote, n'est pas concerné ; les
    commentaires du pilote (marqués) et des robots ne comptent pas."""
    dernier = None
    for i, c in enumerate(commentaires or []):
        if any(m.get("etat") == "bloque" for m in marques([c])):
            dernier = i
    if dernier is None:
        return False
    return any(_ecrit_par_un_humain(c) for c in commentaires[dernier + 1:])


# Le dépanneur (`pilote._depanner`) regarde un lot que le pilote vient de
# bloquer, avant le propriétaire. Il le relance avec une consigne (marque
# « depanne »), pose une question au propriétaire, ou dit que la chaîne est en
# cause ; il ne relance pas un même lot plus de `depannages_max` fois. Le
# 1er octobre 2026, cinq lots attendaient le propriétaire au matin : trois
# pour un quota, une relecture vide ou une image illisible, que la chaîne
# pouvait lever seule.
ETAT_DEPANNE = "depanne"
PAR_DEPANNEUR = "depanneur"


def depannage_a_faire(commentaires: list[dict], depannages_max: int) -> bool:
    """Le dépanneur doit-il regarder ce lot ? Oui si son dernier blocage
    vient du pilote, n'est ni une question au propriétaire ni un blocage posé
    par le dépanneur lui-même, que le dépanneur n'a rien dit depuis, et qu'il
    n'a pas déjà relancé le lot `depannages_max` fois."""
    liste = marques(commentaires)
    dernier = max((i for i, m in enumerate(liste) if m.get("etat") == "bloque"), default=None)
    if dernier is None:
        return False
    blocage = liste[dernier]
    if blocage.get("question") or blocage.get("par") == PAR_DEPANNEUR:
        return False
    if any(m.get("role") == "depanneur" for m in liste[dernier + 1:]):
        return False
    relances = sum(1 for m in liste if m.get("role") == "depanneur" and m.get("etat") == ETAT_DEPANNE)
    return relances < depannages_max


def consigne_du_depanneur(commentaires: list[dict]) -> str:
    """La consigne du dépanneur qui vaut encore : celle de sa dernière
    relance, tant que le lot n'a pas été rebloqué depuis."""
    consigne = ""
    for m in marques(commentaires):
        if m.get("etat") == "bloque":
            consigne = ""
        elif m.get("role") == "depanneur" and m.get("etat") == ETAT_DEPANNE:
            consigne = m.get("consigne") or ""
    return consigne


def _ecrit_par_un_humain(c: dict) -> bool:
    """Ni le pilote (ses commentaires sont marqués), ni un robot."""
    corps = (c.get("body") or "").strip()
    auteur = ((c.get("author") or {}).get("login") or "").lower()
    return bool(corps) and "<!-- atelier" not in corps and not auteur.endswith("[bot]") and auteur != "github-actions"


def decisions_du_lot(commentaires: list[dict]) -> list[str]:
    """Ce qui a été décidé sur ce lot : chaque question posée au propriétaire,
    avec la réponse qu'il a écrite ensuite, et chaque question technique que
    le pilote a tranchée seul. Rien ne les efface, ni un blocage ni une
    reprise : le 3 octobre 2026, #235 avait l'accord du propriétaire pour
    toucher la chronique, mais le codeur ne lisait que le brief, qui
    l'excluait, et le lot s'est bloqué trois fois sur la même CI rouge."""
    decisions: list[str] = []
    question: Question | None = None
    for c in commentaires or []:
        faites = marques([c])
        for m in faites:
            if m.get("role") != "pilote":
                continue
            if m.get("etat") == "bloque" and m.get("question"):
                question = Question.de_marque(m)
            elif m.get("etat") == ETAT_DECISION and (q := Question.de_marque(m)) and q.recommandation:
                lettre = q.recommandation[0]
                reponse = q.reponse_recommandee()
                decisions.append(f"Question technique : {q.texte} Décision : {lettre}"
                                 + (f" — {reponse}" if reponse else "")
                                 + " (prise par le pilote, selon la recommandation).")
        if faites or question is None or not _ecrit_par_un_humain(c):
            continue
        texte = (c.get("body") or "").strip()
        choisie = next((f"{l} — {r}" for l, r, _ in question.options if texte.rstrip(" .").upper() == l), None)
        decisions.append(f"Question : {question.texte} Réponse du propriétaire : {choisie or texte}")
    return decisions


def passage_de_renfort(essai: int, corrections_max: int) -> bool:
    """Le passage du codeur numéro `essai` (0 : le premier) est-il le dernier
    avant blocage ? Avec deux corrections, c'est la deuxième : le renfort la
    fait, un modèle plus fort que le codeur, qui a sous les yeux ce que les
    passages d'avant n'ont pas réussi. Sans correction permise, pas de
    renfort : le premier passage reste au codeur."""
    return corrections_max >= 1 and essai >= corrections_max


def famille_de(agent: str) -> str:
    """La famille de modèle d'un agent écrit `outil/modèle` dans une marque."""
    outil, _, modele = agent.partition("/")
    return FAMILLE_DE_L_OUTIL.get(outil) or (famille_du_modele(modele) if modele else outil)


def auteurs(liste: list[dict]) -> frozenset[str]:
    """Les familles de modèles qui ont écrit du code sur ce lot : aucun de
    leurs modèles ne le relit, quel que soit l'outil qui le porte."""
    return frozenset(famille_de(m["agent"]) for m in liste
                     if m.get("role") in ROLES_CODEURS and m.get("etat") == "fait" and m.get("agent"))
