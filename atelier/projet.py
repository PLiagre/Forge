"""Le branchement du dépôt sur l'atelier : `atelier.toml`. L'atelier ne devine rien.

Le fichier dit le projet (dépôt, base, ce qu'un lot ne touche jamais, le
cœur du moteur, les pistes), les cinq rôles (une ligne chacun :
harnais/modèle@effort), leurs délais, et le parallélisme : combien de lots
chaque machine tient en même temps (`[machines]`), combien d'agents tournent
ensemble (`[outils]`). Un champ obligatoire qui manque se refuse, il ne
s'invente pas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import tomllib


class ProjetIncomplet(ValueError):
    """Un champ obligatoire manque ou se lit mal : on refuse, on n'invente pas."""


# Le harnais que l'atelier sait appeler, et son binaire.
OUTILS = {"claude": "claude"}
HARNAIS = {"claude": "Claude Code"}
# L'effort que le harnais sait recevoir par `--effort`. Un effort hors de
# cette liste se refuse : le harnais l'ignorerait à chaque appel.
EFFORTS = {"claude": ("low", "medium", "high", "xhigh", "max")}
# Seuls les modèles de l'abonnement tournent : le chargement refuse le reste.
_CLAUDE = re.compile(r"^(?:claude-)?(opus|sonnet|haiku|fable)\b", re.I)

# Les cinq rôles, par niveau de jugement. Chacun a sa ligne dans [agents].
CTO, CHEF, DEVELOPPEUR, RELECTEUR, LECTEUR = "cto", "chef", "developpeur", "relecteur", "lecteur"
ROLES = (CTO, CHEF, DEVELOPPEUR, RELECTEUR, LECTEUR)
# Ceux qui mènent un lot : ils écrivent des fichiers, dans la session du lot.
ROLES_MENEURS = (CHEF, DEVELOPPEUR)
# Les machines d'un lot : le VPS (Python) et le PC (Unity, Blender).
MACHINES = ("vps", "pc")


@dataclass(frozen=True)
class Agent:
    """Un harnais, un modèle et un effort : `claude/claude-sonnet-5-5@high`."""

    outil: str
    modele: str
    effort: str | None = None

    def __str__(self) -> str:
        return f"{self.outil}/{self.modele}" + (f"@{self.effort}" if self.effort else "")

    @property
    def binaire(self) -> str:
        return OUTILS[self.outil]


@dataclass(frozen=True)
class Projet:
    racine: Path
    nom: str
    depot: str
    branche_base: str
    prefixe_branche: str
    proprietaire: str
    interdits: tuple[str, ...]
    coeur: tuple[str, ...]
    pistes: tuple[str, ...]
    corrections_max: int
    coupures_max: int
    deblocages_max: int
    agents: dict[str, Agent] = field(default_factory=dict)
    delais: dict[str, int] = field(default_factory=dict)
    machines: dict[str, int] = field(default_factory=lambda: {m: 1 for m in MACHINES})
    plafonds: dict[str, int] = field(default_factory=dict)
    jours_max: int = 400

    def agent(self, role: str) -> Agent:
        if role not in self.agents:
            raise ProjetIncomplet(f"[agents] ne nomme pas le rôle {role!r}")
        return self.agents[role]

    def delai(self, role: str) -> int:
        return self.delais.get(role, 1800)

    def capacite(self, machine: str) -> int:
        """Combien de lots cette machine tient en même temps."""
        return self.machines.get(machine, 1)

    def plafond(self, outil: str) -> int | None:
        """Combien d'agents de cet outil tournent ensemble ; None : sans plafond."""
        return self.plafonds.get(outil)

    def interdit(self, chemin: str) -> bool:
        """Un lot ne touche jamais ce chemin : seul le mode direct y écrit."""
        return _sous(chemin, self.interdits)

    def touche_le_coeur(self, fichiers) -> bool:
        """Un de ces fichiers est-il du cœur du moteur, que le CTO relit ?"""
        return any(_sous(f, self.coeur) for f in fichiers)


def _sous(chemin: str, regles: tuple[str, ...]) -> bool:
    chemin = chemin.replace("\\", "/")
    return any(chemin == r or (r.endswith("/") and chemin.startswith(r)) for r in regles)


def lire_agent(role: str, texte: object) -> Agent:
    """`harnais/modèle@effort`. Un harnais inconnu, un effort qu'il ne sait pas
    recevoir ou un modèle hors de l'abonnement se refusent."""
    if not isinstance(texte, str) or not texte.strip():
        raise ProjetIncomplet(f"[agents].{role} est vide")
    morceau = texte.strip()
    outil, barre, reste = morceau.partition("/")
    modele, arobase, effort = reste.partition("@")
    if not barre or not outil or not modele or (arobase and not effort) or " " in morceau:
        raise ProjetIncomplet(f"[agents].{role} illisible : {texte!r} (attendu : harnais/modèle@effort)")
    if outil not in OUTILS:
        raise ProjetIncomplet(f"[agents].{role} : outil inconnu {outil!r} (connus : {', '.join(sorted(OUTILS))})")
    if effort and effort not in EFFORTS[outil]:
        raise ProjetIncomplet(f"[agents].{role} : {HARNAIS[outil]} ne connaît pas l'effort {effort!r} "
                              f"(connus : {', '.join(EFFORTS[outil])})")
    if not _CLAUDE.match(modele):
        raise ProjetIncomplet(f"[agents].{role} : {morceau} — seuls les modèles de l'abonnement Claude tournent "
                              "(fable, opus, sonnet, haiku)")
    return Agent(outil=outil, modele=modele, effort=effort or None)


def charger(racine: Path | str) -> Projet:
    racine = Path(racine)
    chemin = racine / "atelier.toml"
    if not chemin.is_file():
        raise ProjetIncomplet(f"{chemin} introuvable : l'atelier ne devine pas le branchement")
    with chemin.open("rb") as f:
        doc = tomllib.load(f)
    bloc = doc.get("projet") or {}
    obligatoires = ("nom", "depot", "branche_base", "prefixe_branche", "proprietaire", "interdits", "pistes",
                    "corrections_max", "coupures_max", "deblocages_max")
    manquants = [cle for cle in obligatoires if cle not in bloc]
    if manquants:
        raise ProjetIncomplet(f"[projet] ne dit pas : {', '.join(manquants)}")
    agents = doc.get("agents") or {}
    manquants = [role for role in ROLES if role not in agents]
    if manquants:
        raise ProjetIncomplet(f"[agents] ne nomme pas : {', '.join(manquants)}")
    inconnus = sorted(set(agents) - set(ROLES))
    if inconnus:
        raise ProjetIncomplet(f"[agents] nomme des rôles inconnus : {', '.join(inconnus)} "
                              f"(les cinq rôles : {', '.join(ROLES)})")
    delais = doc.get("delais") or {}
    inconnus = sorted(set(delais) - set(ROLES))
    if inconnus:
        raise ProjetIncomplet(f"[delais] nomme des rôles inconnus : {', '.join(inconnus)}")
    gardes = _entiers_positifs("gardes", doc.get("gardes") or {}, ("jours_max",))
    return Projet(
        racine=racine,
        nom=str(bloc["nom"]),
        depot=str(bloc["depot"]),
        branche_base=str(bloc["branche_base"]),
        prefixe_branche=str(bloc["prefixe_branche"]),
        proprietaire=str(bloc["proprietaire"]),
        interdits=tuple(str(x) for x in bloc["interdits"]),
        coeur=tuple(str(x) for x in bloc.get("coeur", ())),
        pistes=tuple(str(x) for x in bloc["pistes"]),
        corrections_max=int(bloc["corrections_max"]),
        coupures_max=int(bloc["coupures_max"]),
        deblocages_max=int(bloc["deblocages_max"]),
        agents={role: lire_agent(role, agents[role]) for role in ROLES},
        delais=_entiers_positifs("delais", delais, ROLES),
        machines={m: 1 for m in MACHINES} | _entiers_positifs("machines", doc.get("machines") or {}, MACHINES),
        plafonds=_entiers_positifs("outils", doc.get("outils") or {}, tuple(OUTILS)),
        jours_max=gardes.get("jours_max", 400),
    )


def _entiers_positifs(section: str, bloc: dict, connus: tuple[str, ...]) -> dict[str, int]:
    """Une section de nombres : chaque clé est connue, chaque valeur un entier
    ≥ 1. Un zéro arrêterait la chaîne sans le dire ; une faute de frappe
    laisserait croire à un réglage qui ne joue pas."""
    lus = {}
    for cle, valeur in bloc.items():
        if cle not in connus:
            raise ProjetIncomplet(f"[{section}] ne connaît pas {cle!r} (connus : {', '.join(connus)})")
        if isinstance(valeur, bool) or not isinstance(valeur, int) or valeur < 1:
            raise ProjetIncomplet(f"[{section}].{cle} doit être un entier ≥ 1, pas {valeur!r}")
        lus[cle] = valeur
    return lus


def table_des_roles(projet: Projet) -> str:
    """Ce que `python3 -m atelier agents` imprime : chaque rôle, son modèle,
    son effort, son délai ; puis le parallélisme."""
    lignes = [f"{'rôle':14} {'modèle':22} {'effort':8} délai"]
    for role in ROLES:
        agent = projet.agents[role]
        lignes.append(f"{role:14} {agent.modele:22} {agent.effort or '—':8} {projet.delai(role)} s")
    lignes.append("")
    lignes.append("lots en même temps : " + ", ".join(f"{m} {projet.capacite(m)}" for m in MACHINES))
    lignes.append("agents en même temps : " + (", ".join(f"{o} {n}" for o, n in sorted(projet.plafonds.items()))
                                               or "sans plafond"))
    return "\n".join(lignes)
