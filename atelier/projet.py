"""Branchement du dépôt sur l'atelier : `atelier.toml`. L'atelier ne devine rien.

Le fichier dit trois choses : le projet (dépôt, base, tests, ce qu'un lot ne
touche jamais), les rôles (une ligne par rôle : outil/modèle, puis les
secours) et les délais. Un champ qui manque se refuse, il ne s'invente pas.
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

# Les rôles de la chaîne. Chacun doit avoir sa ligne dans [agents].
ROLES = ("chef", "codeur", "codeur_3d", "relecteur", "mecanicien", "chroniqueur", "boussole")

# Les rôles qui n'écrivent rien : leur outil est appelé en lecture seule.
ROLES_LECTURE_SEULE = ("relecteur", "chroniqueur", "boussole")


@dataclass(frozen=True)
class Agent:
    """Un outil et un modèle : `codex/gpt-5.6-sol`."""

    outil: str
    modele: str

    def __str__(self) -> str:
        return f"{self.outil}/{self.modele}"

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
    """`outil/modèle`, sans espace superflu. Un outil inconnu se refuse."""
    morceau = texte.strip()
    outil, barre, modele = morceau.partition("/")
    if not barre or not outil or not modele:
        raise ProjetIncomplet(f"agent illisible : {texte!r} (attendu : outil/modèle)")
    if outil not in OUTILS:
        connus = ", ".join(sorted(OUTILS))
        raise ProjetIncomplet(f"outil inconnu : {outil!r} (connus : {connus})")
    return Agent(outil=outil, modele=modele)


def lire_poste(role: str, ligne: str) -> Poste:
    """`outil/modèle | secours | …` : l'ordre est celui des essais."""
    if not isinstance(ligne, str) or not ligne.strip():
        raise ProjetIncomplet(f"[agents].{role} est vide")
    agents = tuple(lire_agent(morceau) for morceau in ligne.split("|"))
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
    )


def table_des_roles(projet: Projet) -> str:
    """Ce que `python3 -m atelier agents` imprime : une ligne par rôle."""
    lignes = [f"{'rôle':12} {'agent':40} secours"]
    for role in ROLES:
        poste = projet.postes[role]
        secours = ", ".join(str(a) for a in poste.secours) or "—"
        lecture = " (lecture seule)" if poste.lecture_seule else ""
        lignes.append(f"{role:12} {str(poste.principal) + lecture:40} {secours}")
    return "\n".join(lignes)
