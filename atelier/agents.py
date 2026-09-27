"""Appeler un agent : la ligne de commande exacte, et le secours.

Un agent est un outil (claude, codex, cursor) et un modèle. Ce module
construit l'argv de chacun — le shell n'en compose aucune — et l'exécute
dans le dossier du lot, sans clé d'API dans l'environnement : une clé fait
basculer la facture de l'abonnement vers l'unité.

Un agent n'a jamais la main sur GitHub : il édite des fichiers, ou il rend
un texte. Commit, poussée, PR, commentaire, étiquette et fusion
appartiennent au pilote. C'est ce qui rend un avis impossible à falsifier
par celui qui le donne, et ce qui évite les refus de shell propres à chaque
outil (`cd … &&` chez Cursor, mesuré le 23 septembre 2026).

Quota épuisé ou session expirée : on passe au secours. Si aucun agent du
poste ne répond pour ces raisons, le lot **attend** — ce n'est pas un
échec, et le tour suivant réessaie.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Callable

from .projet import Agent, Poste

# Les clés qu'on retire avant de lancer un agent.
CLES_API = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "CURSOR_API_KEY")

# Le jeton longue durée de Claude Code (`claude setup-token`), rangé par le
# propriétaire dans un fichier en mode 600. Il est lu ici et passé à l'enfant
# par l'environnement : il n'apparaît ni dans l'argv, ni dans un journal.
FICHIER_JETON_CLAUDE = Path(os.environ.get(
    "ATELIER_JETON_CLAUDE", str(Path.home() / ".atelier" / "claude.token")))

# Ce qu'un rôle qui écrit n'a jamais le droit de faire : le pilote s'en charge.
GESTES_DU_PILOTE = (
    "Bash(git push:*)", "Bash(git commit:*)", "Bash(git reset:*)",
    "Bash(git checkout:*)", "Bash(git switch:*)", "Bash(git rebase:*)",
    "Bash(git merge:*)", "Bash(gh:*)",
)

# Les signes d'un quota épuisé ou d'une session expirée, lus dans la fin de
# la sortie d'un agent qui a rendu un code non nul.
_QUOTA = re.compile(
    r"rate.?limit|usage limit|quota|too many requests|\b429\b|limit reached|"
    r"you'?ve hit your|out of credits|insufficient_quota|credit balance|"
    r"plan limit|overloaded", re.I)
_AUTH = re.compile(
    r"unauthori[sz]ed|\b401\b|not logged in|log ?in required|please (log|sign) ?in|"
    r"invalid (api )?key|token (has )?expired|session expired|oauth|setup-token|"
    r"authentication (failed|required|error)", re.I)


def cause_de_refus(code: int, texte: str) -> str | None:
    """`quota`, `auth` ou None. Seule la fin de la sortie compte : c'est là
    que les outils écrivent leur erreur, et le travail d'un agent peut citer
    ces mots sans que ce soit un refus."""
    if code == 0:
        return None
    fin = "\n".join(texte.strip().splitlines()[-25:])
    if _AUTH.search(fin):
        return "auth"
    if _QUOTA.search(fin):
        return "quota"
    return None


def environnement(outil: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in CLES_API}
    if outil == "claude" and FICHIER_JETON_CLAUDE.is_file():
        jeton = FICHIER_JETON_CLAUDE.read_text(encoding="utf-8").strip()
        if jeton:
            env["CLAUDE_CODE_OAUTH_TOKEN"] = jeton
    return env


def argv(agent: Agent, prompt: str, *, lecture_seule: bool,
         sortie: Path | None = None, windows: bool | None = None) -> list[str]:
    """L'argv exact. Construit ici, exécuté par `invoquer`, jamais recomposé."""
    windows = sys.platform.startswith("win") if windows is None else windows
    if agent.outil == "claude":
        commande = [agent.binaire, "-p", prompt, "--model", agent.modele,
                    "--output-format", "text"]
        if lecture_seule:
            commande += [
                "--permission-mode", "default",
                "--allowedTools",
                "Read,Glob,Grep,Bash(git diff:*),Bash(git log:*),Bash(git show:*),"
                "Bash(ls:*),Bash(cat:*),Bash(grep:*),Bash(head:*),Bash(wc:*)",
                "--disallowedTools", "Edit,Write,NotebookEdit," + ",".join(GESTES_DU_PILOTE),
            ]
        else:
            permis = "Read,Glob,Grep,Edit,Write,Bash" + (",PowerShell" if windows else "")
            commande += [
                "--permission-mode", "acceptEdits",
                "--allowedTools", permis,
                "--disallowedTools", ",".join(GESTES_DU_PILOTE),
            ]
        return commande
    if agent.outil == "codex":
        commande = [agent.binaire, "exec", "--model", agent.modele,
                    "--sandbox", "read-only" if lecture_seule else "workspace-write",
                    "--skip-git-repo-check", "--color", "never"]
        if sortie is not None:
            commande += ["--output-last-message", str(sortie)]
        return commande + [prompt]
    if agent.outil == "cursor":
        commande = [agent.binaire, "-p", prompt, "--model", agent.modele,
                    "--output-format", "text", "--trust"]
        commande += ["--mode", "ask"] if lecture_seule else ["--force"]
        return commande
    raise ValueError(f"outil inconnu : {agent.outil}")


@dataclass
class Resultat:
    """Ce qu'un appel a rendu. `attente` : personne n'a pu répondre (quota,
    session), le lot attend ; ce n'est pas un échec."""

    agent: Agent | None
    code: int
    texte: str
    attente: bool = False
    essais: list[str] = field(default_factory=list)
    # Aucun agent du poste n'avait le droit de répondre (tous écartés) :
    # ce n'est pas une attente, c'est une décision à prendre.
    personne: bool = False

    @property
    def reussi(self) -> bool:
        return self.agent is not None and self.code == 0 and not self.attente


Executeur = Callable[[list[str], Path, dict[str, str], int], tuple[int, str, str]]


def executer(commande: list[str], cwd: Path, env: dict[str, str], delai: int) -> tuple[int, str, str]:
    try:
        fini = subprocess.run(commande, cwd=cwd, env=env, capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              timeout=delai, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired as e:
        sortie = e.stdout.decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        return 124, sortie, f"délai dépassé après {delai} s"
    except FileNotFoundError:
        return 127, "", f"binaire introuvable : {commande[0]}"
    return fini.returncode, fini.stdout, fini.stderr


def invoquer(poste: Poste, prompt: str, cwd: Path, delai: int, *,
             exclure: frozenset[str] = frozenset(),
             executeur: Executeur = executer) -> Resultat:
    """Essaie l'agent du poste, puis ses secours, dans l'ordre.

    `exclure` retire des outils : le modèle qui a écrit un lot ne le relit
    jamais. On ne passe au secours que pour un quota ou une session ; un
    agent qui échoue pour une autre raison a répondu, et c'est son échec.
    """
    essais: list[str] = []
    for agent in poste.agents:
        if agent.outil in exclure:
            essais.append(f"{agent} : écarté (il a écrit ce lot)")
            continue
        # La réponse finale de Codex s'écrit hors du dossier du lot : un
        # fichier laissé dans le worktree finirait dans le commit.
        sortie = Path(tempfile.mkdtemp(prefix="atelier-")) / "reponse.txt" if agent.outil == "codex" else None
        code, out, err = executeur(
            argv(agent, prompt, lecture_seule=poste.lecture_seule, sortie=sortie),
            Path(cwd), environnement(agent.outil), delai)
        texte = out
        if sortie is not None and sortie.exists():
            texte = sortie.read_text(encoding="utf-8", errors="replace")
            sortie.unlink()
        cause = cause_de_refus(code, f"{out}\n{err}")
        if cause:
            essais.append(f"{agent} : {'quota épuisé' if cause == 'quota' else 'session expirée ou absente'}")
            continue
        essais.append(f"{agent} : code {code}")
        return Resultat(agent=agent, code=code, texte=texte if code == 0 else f"{texte}\n{err}".strip(),
                        essais=essais)
    tous_ecartes = all(e.endswith("(il a écrit ce lot)") for e in essais)
    return Resultat(agent=None, code=-1, texte="", attente=not tous_ecartes,
                    personne=tous_ecartes, essais=essais)
