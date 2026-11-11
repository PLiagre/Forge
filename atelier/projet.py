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


# Les outils que l'atelier sait appeler, et le binaire de chacun. Claude Code
# seul : l'abonnement Claude (Opus, Sonnet) est le seul qui reste au
# propriétaire. Codex est retiré le 30 octobre 2026, Cursor (grok, composer)
# le 5 novembre (choix du propriétaire).
OUTILS = {"claude": "claude"}

# Les modèles que la chaîne appelle : ceux de Claude, et rien d'autre (choix
# du propriétaire, 5 novembre 2026). Le chargement refuse le reste.
_CLAUDE = re.compile(r"^(?:claude-)?(opus|sonnet|haiku|fable)\b", re.I)


def famille_du_modele(modele: str) -> str:
    """La famille d'un modèle : chaque modèle Claude (opus, sonnet…) est la
    sienne. Le secours du dépanneur écarte la famille de l'agent qui vient
    de lire sans rien décider (pilote._depanner) : si Opus et Sonnet étaient
    une seule famille, Sonnet ne lirait jamais après Opus. Un autre nom est
    sa propre famille : son premier mot."""
    m = _CLAUDE.match(modele.strip())
    if m:
        return m.group(1).lower()
    return re.split(r"[-_.\s]", modele.strip().lower(), maxsplit=1)[0]


# L'effort (la profondeur de raisonnement) que chaque harnais sait recevoir :
# Claude Code par `--effort` (`claude --help`, 2.1.284). Un effort hors de
# cette liste se refuse : Claude Code l'ignorerait à chaque appel.
EFFORTS = {
    "claude": ("low", "medium", "high", "xhigh", "max"),
}
# Le nom lisible de chaque harnais, pour la table des rôles.
HARNAIS = {"claude": "Claude Code"}

# Les rôles de la chaîne. Chacun doit avoir sa ligne dans [agents].
# Le dépanneur regarde un lot bloqué avant le propriétaire (pilote._depanner).
# Le renfort (un autre modèle pour le dernier passage avant blocage) est retiré
# le 7 novembre 2026 : avec un seul abonnement, c'était le codeur encore une fois.
ROLES = ("chef", "codeur", "codeur_3d", "relecteur", "mecanicien", "depanneur", "chroniqueur",
         "boussole")
# Les rôles qu'un dépôt peut nommer, ou non. Le relecteur du moteur relit les
# lots qui touchent [projet].chemins_du_moteur ; sans lui, le relecteur relit tout.
# La direction regarde une question posée au propriétaire avant lui
# (pilote._diriger) ; sans elle, toute question de jeu lui va, comme avant le
# 10 novembre 2026.
ROLES_FACULTATIFS = ("relecteur_moteur", "direction")

# Les rôles qui n'écrivent rien : leur outil est appelé en lecture seule.
ROLES_LECTURE_SEULE = ("relecteur", "relecteur_moteur", "depanneur", "chroniqueur", "boussole", "direction")

# Les machines d'un lot : le VPS (Python) et le PC (Unity, Blender).
MACHINES = ("vps", "pc")


@dataclass(frozen=True)
class Agent:
    """Un harnais (l'outil qui porte le modèle), un modèle, et l'effort qu'on
    lui donne : `claude/claude-sonnet-5-5@high`. Sans effort, le harnais garde
    le sien ; le dépôt en donne un à chaque agent (tests)."""

    outil: str
    modele: str
    effort: str | None = None

    def __str__(self) -> str:
        return f"{self.outil}/{self.modele}" + (f"@{self.effort}" if self.effort else "")

    @property
    def effort_lisible(self) -> str:
        return self.effort or "non donné (celui du harnais)"

    @property
    def binaire(self) -> str:
        return OUTILS[self.outil]

    @property
    def famille(self) -> str:
        return famille_du_modele(self.modele)


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
    depannages_max: int
    dossier_briefs: str
    prefixe_branche: str
    postes: dict[str, Poste] = field(default_factory=dict)
    chemins_du_moteur: tuple[str, ...] = ()
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

    def relecteur_pour(self, fichiers) -> str:
        """Le rôle qui relit un lot : le relecteur du moteur s'il touche un de
        ses chemins et que le dépôt le nomme, sinon le relecteur."""
        if "relecteur_moteur" in self.postes and any(
                f.replace("\\", "/").startswith(chemin) for f in fichiers for chemin in self.chemins_du_moteur):
            return "relecteur_moteur"
        return "relecteur"

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
    if effort and effort not in EFFORTS[outil]:
        raise ProjetIncomplet(f"{morceau} : {HARNAIS[outil]} ne connaît pas l'effort {effort!r} "
                              f"(connus : {', '.join(EFFORTS[outil])})")
    return Agent(outil=outil, modele=modele, effort=effort or None)


def lire_poste(role: str, ligne: str) -> Poste:
    """`harnais/modèle@effort | secours | …` : l'ordre est celui des essais.
    Un modèle qui n'est pas de Claude se refuse : plus de GPT depuis le
    30 octobre 2026, plus de grok ni de composer depuis le 5 novembre (choix
    du propriétaire)."""
    if not isinstance(ligne, str) or not ligne.strip():
        raise ProjetIncomplet(f"[agents].{role} est vide")
    agents = tuple(lire_agent(morceau) for morceau in ligne.split("|"))
    for agent in agents:
        if not _CLAUDE.match(agent.modele.strip()):
            raise ProjetIncomplet(f"[agents].{role} : {agent} — seuls les modèles Claude tournent (opus, sonnet…) : "
                                  "l'abonnement Claude est le seul qui reste (choix du propriétaire, 5 novembre 2026)")
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
                    "lignes_max", "corrections_max", "depannages_max", "dossier_briefs", "prefixe_branche")
    manquants = [cle for cle in obligatoires if cle not in bloc]
    if manquants:
        raise ProjetIncomplet(f"[projet] ne dit pas : {', '.join(manquants)}")
    agents = doc.get("agents") or {}
    manquants = [role for role in ROLES if role not in agents]
    if manquants:
        raise ProjetIncomplet(f"[agents] ne nomme pas : {', '.join(manquants)}")
    postes = {role: lire_poste(role, agents[role]) for role in (*ROLES, *ROLES_FACULTATIFS) if role in agents}
    inconnus = sorted(set(agents) - set(ROLES) - set(ROLES_FACULTATIFS))
    if inconnus:
        raise ProjetIncomplet(f"[agents] nomme des rôles inconnus : {', '.join(inconnus)}")
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
        depannages_max=int(bloc["depannages_max"]),
        dossier_briefs=str(bloc["dossier_briefs"]).rstrip("/"),
        prefixe_branche=str(bloc["prefixe_branche"]),
        postes=postes,
        chemins_du_moteur=tuple(str(x) for x in bloc.get("chemins_du_moteur", ())),
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
    for role in (*ROLES, *(r for r in ROLES_FACULTATIFS if r in projet.postes)):
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
