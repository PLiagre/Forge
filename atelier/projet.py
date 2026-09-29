"""Branchement du dépôt sur l'atelier : `atelier.toml`. L'atelier ne devine rien.

Le fichier dit le projet (dépôt, base, tests, ce qu'un lot ne touche
jamais), les rôles (une ligne par rôle : harnais/modèle@effort, puis les
secours), les
délais, et le parallélisme : combien de lots chaque machine tient en même
temps (`[machines]`), combien d'agents de chaque outil tournent ensemble
(`[outils]`). Un champ obligatoire qui manque se refuse, il ne s'invente
pas ; sans `[machines]`, chaque machine tient un lot, et sans `[outils]`,
aucun outil n'a de plafond : la chaîne d'avant le 29 septembre 2026.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import tomllib


class ProjetIncomplet(ValueError):
    """Un champ obligatoire manque ou se lit mal : on refuse, on n'invente pas."""


# Les outils que l'atelier sait appeler, et le binaire de chacun.
OUTILS = {"claude": "claude", "codex": "codex", "cursor": "cursor-agent"}

# La famille d'un modèle : qui l'a entraîné. Le relecteur n'est jamais de la
# famille qui a écrit : du code écrit par cursor/claude-opus ne se relit pas
# par claude/claude-opus, qui partage ses angles morts. Claude Code ne porte
# que des modèles Claude, Codex que des modèles d'OpenAI ; Cursor porte tout,
# sa famille se lit dans le nom du modèle. Un nom inconnu est sa propre
# famille (son premier mot).
FAMILLE_DE_L_OUTIL = {"claude": "claude", "codex": "gpt"}
_FAMILLES = (
    ("claude", re.compile(r"^(claude|opus|sonnet|haiku|fable)\b", re.I)),
    ("gpt", re.compile(r"^(gpt|o\d|codex)\b", re.I)),
    ("grok", re.compile(r"^grok\b", re.I)),
    ("gemini", re.compile(r"^gemini\b", re.I)),
    ("composer", re.compile(r"^composer\b", re.I)),
)


def famille_du_modele(modele: str) -> str:
    for nom, motif in _FAMILLES:
        if motif.match(modele):
            return nom
    return re.split(r"[-_.\s]", modele.strip().lower(), maxsplit=1)[0]

# L'effort (la profondeur de raisonnement) que chaque harnais sait recevoir,
# et comment : Claude Code par `--effort` (`claude --help`, 2.1.284) ; Codex
# par `-c model_reasoning_effort` ; Cursor n'a pas d'option, l'effort est dans
# le nom du modèle (`grok-4.7-high`), et « defaut » dit qu'un modèle Cursor
# n'en propose pas (composer). Un effort hors de cette liste se refuse : le
# harnais le refuserait à chaque appel.
EFFORTS = {
    "claude": ("low", "medium", "high", "xhigh", "max"),
    "codex": ("minimal", "low", "medium", "high", "xhigh"),
    "cursor": ("low", "medium", "high", "xhigh", "defaut"),
}
_EFFORT_DANS_LE_NOM = re.compile(r"-(low|medium|high|xhigh)$")
# Le nom lisible de chaque harnais, pour la table des rôles.
HARNAIS = {"claude": "Claude Code", "codex": "Codex CLI", "cursor": "Cursor (cursor-agent)"}

# Les rôles de la chaîne. Chacun doit avoir sa ligne dans [agents].
ROLES = ("chef", "codeur", "codeur_3d", "relecteur", "mecanicien", "chroniqueur", "boussole")

# Les rôles qui n'écrivent rien : leur outil est appelé en lecture seule.
ROLES_LECTURE_SEULE = ("relecteur", "chroniqueur", "boussole")

# Les machines d'un lot : le VPS (Python) et le PC (Unity, Blender).
MACHINES = ("vps", "pc")


@dataclass(frozen=True)
class Agent:
    """Un harnais (l'outil qui porte le modèle), un modèle, et l'effort qu'on
    lui donne : `codex/gpt-5.6-sol@high`. Sans effort, le harnais garde le
    sien ; le dépôt en donne un à chaque agent (tests)."""

    outil: str
    modele: str
    effort: str | None = None

    def __str__(self) -> str:
        return f"{self.outil}/{self.modele}" + (f"@{self.effort}" if self.effort else "")

    @property
    def effort_lisible(self) -> str:
        if self.effort is None:
            return "non donné (celui du harnais)"
        if self.outil == "cursor":
            return ("aucun (Cursor n'en propose pas pour ce modèle)" if self.effort == "defaut"
                    else f"{self.effort} (dans le nom du modèle)")
        return self.effort

    @property
    def binaire(self) -> str:
        return OUTILS[self.outil]

    @property
    def famille(self) -> str:
        return FAMILLE_DE_L_OUTIL.get(self.outil) or famille_du_modele(self.modele)


@dataclass(frozen=True)
class Poste:
    """Un rôle, son agent, puis ses secours dans l'ordre."""

    role: str
    agents: tuple[Agent, ...]

    @property
    def principal(self) -> Agent:
        return self.agents[0]

    @property
    def secours(self) -> tuple[Agent, ...]:
        return self.agents[1:]

    @property
    def lecture_seule(self) -> bool:
        return self.role in ROLES_LECTURE_SEULE


@dataclass(frozen=True)
class Projet:
    racine: Path
    nom: str
    depot: str
    branche_base: str
    tests: str
    interdits: tuple[str, ...]
    lignes_max: int
    corrections_max: int
    dossier_briefs: str
    prefixe_branche: str
    postes: dict[str, Poste] = field(default_factory=dict)
    delais: dict[str, int] = field(default_factory=dict)
    machines: dict[str, int] = field(default_factory=lambda: {m: 1 for m in MACHINES})
    plafonds: dict[str, int] = field(default_factory=dict)

    def capacite(self, machine: str) -> int:
        """Combien de lots cette machine tient en même temps."""
        return self.machines.get(machine, 1)

    def plafond(self, outil: str) -> int | None:
        """Combien d'agents de cet outil tournent ensemble ; None : sans plafond."""
        return self.plafonds.get(outil)

    def poste(self, role: str) -> Poste:
        if role not in self.postes:
            raise ProjetIncomplet(f"[agents] ne nomme pas le rôle {role!r}")
        return self.postes[role]

    def delai(self, role: str) -> int:
        return self.delais.get(role, 1800)

    def interdit(self, chemin: str) -> bool:
        """Un lot ne touche jamais ce chemin : seul le mode direct y écrit."""
        chemin = chemin.replace("\\", "/")
        return any(
            chemin == regle or (regle.endswith("/") and chemin.startswith(regle))
            for regle in self.interdits
        )


def lire_agent(texte: str) -> Agent:
    """`harnais/modèle@effort` (l'effort est facultatif ici), sans espace
    superflu. Un harnais inconnu, ou un effort qu'il ne sait pas recevoir,
    se refuse."""
    morceau = texte.strip()
    outil, barre, reste = morceau.partition("/")
    modele, arobase, effort = reste.partition("@")
    if not barre or not outil or not modele or (arobase and not effort):
        raise ProjetIncomplet(f"agent illisible : {texte!r} (attendu : harnais/modèle@effort)")
    if outil not in OUTILS:
        connus = ", ".join(sorted(OUTILS))
        raise ProjetIncomplet(f"outil inconnu : {outil!r} (connus : {connus})")
    if effort:
        if effort not in EFFORTS[outil]:
            raise ProjetIncomplet(f"{morceau} : {HARNAIS[outil]} ne connaît pas l'effort {effort!r} "
                                  f"(connus : {', '.join(EFFORTS[outil])})")
        if outil == "cursor":
            dans_le_nom = _EFFORT_DANS_LE_NOM.search(modele)
            voulu = None if effort == "defaut" else effort
            if (dans_le_nom.group(1) if dans_le_nom else None) != voulu:
                raise ProjetIncomplet(
                    f"{morceau} : Cursor n'a pas d'option d'effort, il est dans le nom du modèle "
                    + (f"(« {modele} » n'en porte pas : « @defaut »)" if not dans_le_nom and voulu is None
                       else f"(« {modele} » dit « {dans_le_nom.group(1) if dans_le_nom else 'rien'} »)"))
    return Agent(outil=outil, modele=modele, effort=effort or None)


def lire_poste(role: str, ligne: str) -> Poste:
    """`harnais/modèle@effort | secours | …` : l'ordre est celui des essais.
    Un modèle Claude ne passe que par Claude Code, jamais par un autre
    harnais : c'est le choix du propriétaire (29 septembre 2026)."""
    if not isinstance(ligne, str) or not ligne.strip():
        raise ProjetIncomplet(f"[agents].{role} est vide")
    agents = tuple(lire_agent(morceau) for morceau in ligne.split("|"))
    for agent in agents:
        if agent.outil != "claude" and famille_du_modele(agent.modele) == "claude":
            raise ProjetIncomplet(f"[agents].{role} : {agent} — un modèle Claude ne passe que par Claude Code "
                                  f"(harnais « claude »), jamais par {HARNAIS[agent.outil]}")
    return Poste(role=role, agents=agents)


def charger(racine: Path | str) -> Projet:
    racine = Path(racine)
    chemin = racine / "atelier.toml"
    if not chemin.is_file():
        raise ProjetIncomplet(f"{chemin} introuvable : l'atelier ne devine pas le branchement")
    with chemin.open("rb") as f:
        doc = tomllib.load(f)
    bloc = doc.get("projet") or {}
    obligatoires = ("nom", "depot", "branche_base", "tests", "interdits",
                    "lignes_max", "corrections_max", "dossier_briefs", "prefixe_branche")
    manquants = [cle for cle in obligatoires if cle not in bloc]
    if manquants:
        raise ProjetIncomplet(f"[projet] ne dit pas : {', '.join(manquants)}")
    agents = doc.get("agents") or {}
    manquants = [role for role in ROLES if role not in agents]
    if manquants:
        raise ProjetIncomplet(f"[agents] ne nomme pas : {', '.join(manquants)}")
    postes = {role: lire_poste(role, agents[role]) for role in ROLES}
    delais = {cle: int(valeur) for cle, valeur in (doc.get("delais") or {}).items()}
    machines = {m: 1 for m in MACHINES} | _entiers_positifs("machines", doc.get("machines") or {}, MACHINES)
    plafonds = _entiers_positifs("outils", doc.get("outils") or {}, tuple(OUTILS))
    return Projet(
        racine=racine,
        nom=str(bloc["nom"]),
        depot=str(bloc["depot"]),
        branche_base=str(bloc["branche_base"]),
        tests=str(bloc["tests"]),
        interdits=tuple(str(x) for x in bloc["interdits"]),
        lignes_max=int(bloc["lignes_max"]),
        corrections_max=int(bloc["corrections_max"]),
        dossier_briefs=str(bloc["dossier_briefs"]).rstrip("/"),
        prefixe_branche=str(bloc["prefixe_branche"]),
        postes=postes,
        delais=delais,
        machines=machines,
        plafonds=plafonds,
    )


def _entiers_positifs(section: str, bloc: dict, connus: tuple[str, ...]) -> dict[str, int]:
    """Une section de nombres (`[machines]`, `[outils]`) : chaque clé est
    connue, chaque valeur un entier ≥ 1. Un zéro arrêterait la chaîne sans le
    dire ; une faute de frappe laisserait croire à un réglage qui ne joue pas."""
    lus = {}
    for cle, valeur in bloc.items():
        if cle not in connus:
            raise ProjetIncomplet(f"[{section}] ne connaît pas {cle!r} (connus : {', '.join(connus)})")
        if isinstance(valeur, bool) or not isinstance(valeur, int) or valeur < 1:
            raise ProjetIncomplet(f"[{section}].{cle} doit être un entier ≥ 1, pas {valeur!r}")
        lus[cle] = valeur
    return lus


def table_des_roles(projet: Projet) -> str:
    """Ce que `python3 -m atelier agents` imprime : pour chaque rôle, chaque
    agent dans l'ordre des essais, avec son harnais, son modèle et son effort ;
    puis le parallélisme."""
    lignes = [f"{'rôle':28} {'rang':8} {'harnais':22} {'modèle':22} effort"]
    for role in ROLES:
        poste = projet.postes[role]
        nom = role + (" (lecture seule)" if poste.lecture_seule else "")
        for i, agent in enumerate(poste.agents):
            lignes.append(f"{nom if i == 0 else '':28} {'1' if i == 0 else 'secours':8} "
                          f"{HARNAIS[agent.outil]:22} {agent.modele:22} {agent.effort_lisible}")
    lignes.append("")
    lignes.append("lots en même temps : " + ", ".join(f"{m} {projet.capacite(m)}" for m in MACHINES))
    lignes.append("agents en même temps : " + (", ".join(f"{o} {n}" for o, n in sorted(projet.plafonds.items()))
                                               or "sans plafond"))
    return "\n".join(lignes)
