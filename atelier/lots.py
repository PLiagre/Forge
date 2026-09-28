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

ETATS = ("idee", "pret", "en-cours", "bloque", "livre")
ETIQUETTE_PC = "pc"
_MARQUE = re.compile(r"<!-- atelier (\{.*?\}) -->", re.S)
_DEPEND = re.compile(r"^[ \t]*(?:#+[ \t]*)?D[ée]pend de[ \t]*:?[ \t]*(.*)$", re.I | re.M)
_JALON = re.compile(r"^J(\d+)\b")
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


def a_prendre(lots: list[Lot], jalon: int | None, machine_libre: dict[str, bool],
              ouvertes: frozenset[int] = frozenset()) -> Lot | None:
    """Le lot suivant du jalon courant : `pret` d'abord, puis `idee`, dans
    l'ordre des numéros d'issue. Une machine occupée ne prend rien ; un lot
    dont une dépendance est encore ouverte attend."""
    if jalon is None:
        return None
    for etat in ("pret", "idee"):
        for lot in sorted(lots, key=lambda l: l.numero):
            if (lot.jalon == jalon and lot.etat == etat and machine_libre.get(lot.machine, False)
                    and not (lot.dependances & ouvertes)):
                return lot
    return None


@dataclass(frozen=True)
class Action:
    nom: str
    raison: str = ""
    essai: int = 0


# Ce que le PC répond à un envoi. `attente` : aucun de ses agents n'a pu
# répondre (quota, session, installation) ; ce n'est pas un passage du codeur.
REPONSES_PC = ("fait", "echec", "attente")
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
    essais = sum(1 for m in codeurs if m.get("etat") in ("fait", "echec"))
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
    if not verdicts:
        return Action("relire")
    dernier = verdicts[-1].get("verdict")
    if dernier == "ACCEPTE":
        if pr.get("autoMergeRequest"):
            return Action("attendre_fusion")
        return Action("fusionner")
    if essais >= max_essais:
        return Action("bloquer", f"relecture « CORRIGER » après {essais - 1} correction(s)")
    return Action("corriger_relecture", "relecture « CORRIGER »", essai=essais)


def auteurs(liste: list[dict]) -> frozenset[str]:
    """Les outils qui ont écrit du code sur ce lot : ils ne le relisent pas."""
    return frozenset((m.get("agent") or "").split("/")[0] for m in liste
                     if m.get("role") in ROLES_CODEURS and m.get("etat") == "fait" and m.get("agent"))
