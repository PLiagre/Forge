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

Quota épuisé, session expirée, outil qui ne démarre pas (installation), ou
outil qui a déjà tous ses agents en route (son plafond, quand plusieurs lots
avancent en même temps) : on passe au secours. Si aucun agent du poste ne
répond pour ces raisons, le lot **attend** — ce n'est pas un échec, et le
tour suivant réessaie.
"""

from __future__ import annotations

from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass, field
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Callable

from .projet import Agent, Poste

WINDOWS = sys.platform.startswith("win")

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


# Un harnais qui refuse l'appel tel que la chaîne le construit : une option
# qu'il ne connaît pas (un Claude Code trop ancien pour `--effort`), une
# valeur de réglage qu'il refuse (Codex). C'est le réglage ou la version du
# harnais qui est en cause, pas l'agent : on passe au secours sans brûler
# d'essai. Les motifs sont ceux des harnais eux-mêmes (commander pour Claude
# Code, clap et serde pour Codex), pas ceux qu'un test lancé par l'agent
# écrirait (argparse dit « unrecognized »). Un effort inconnu, Claude Code
# 2.1.284 ne le refuse pas : il l'ignore et prend le sien — c'est le
# chargement de atelier.toml qui le refuse (projet.EFFORTS). Un modèle que
# ce Codex ne sait pas appeler est aussi un refus d'appel, pas un échec : le
# 29 septembre 2026, Codex 0.151 sur le VPS a refusé gpt-6-sol (« not
# supported when using Codex with a ChatGPT account ») et gpt-6-astra
# (« requires a newer version of Codex ») ; compté comme un échec du codeur,
# ce refus a brûlé les trois essais des lots #220 et #224 sans que le
# secours ne soit essayé.
_APPEL = re.compile(r"error: unknown option '|error: unexpected argument '|unknown variant `|error loading config|"
                    r"model is not supported when using codex|model requires a newer version of codex", re.I)

# Les codes d'un outil qui n'a pas démarré : introuvable (127) ou refusé par
# le système (126). C'est une panne de la machine, pas un échec du codeur :
# trois 127 ont bloqué le lot #118 le 27 septembre 2026.
CODES_INSTALLATION = (126, 127)
LIBELLES = {"quota": "quota épuisé", "auth": "session expirée ou absente", "installation": "ne démarre pas",
            "appel": "refuse l'appel (option, effort ou réglage)"}
_SECRET = re.compile(r"\b(sk-[A-Za-z0-9_-]{8,}|[A-Za-z0-9_-]{40,})")


def cause_de_refus(code: int, texte: str) -> str | None:
    """`quota`, `auth`, `installation`, `appel` ou None. Seule la fin de la
    sortie compte : c'est là que les outils écrivent leur erreur, et le
    travail d'un agent peut citer ces mots sans que ce soit un refus."""
    if code == 0:
        return None
    if code in CODES_INSTALLATION:
        return "installation"
    fin = "\n".join(texte.strip().splitlines()[-25:])
    if _APPEL.search(fin):
        return "appel"
    if _AUTH.search(fin):
        return "auth"
    if _QUOTA.search(fin):
        return "quota"
    return None


def derniere_ligne(texte: str, longueur: int = 160) -> str:
    """La dernière ligne non vide d'une sortie, sans rien qui ressemble à un
    jeton : c'est elle qui dit pourquoi un outil a refusé."""
    lignes = [l.strip() for l in texte.strip().splitlines() if l.strip()]
    return _SECRET.sub("…", lignes[-1])[:longueur] if lignes else ""


class Introuvable(RuntimeError):
    """L'outil n'a pas de lancement sûr sur cette machine."""


# Les versions de cursor-agent, comme les trie son `cursor-agent.ps1` :
# AAAA.M.J-commit, ou AAAA.M.J-HH-MM-SS-commit.
_VERSION_CURSOR = re.compile(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})(?:-(\d{2})-(\d{2})-(\d{2}))?-[a-f0-9]+$")
# Le .js qu'un shim npm (`codex.cmd`) fait lancer par node.
_SHIM_NPM = re.compile(r'"%dp0%\\([^"%]+\.js)"')


def _cursor(dossier: Path) -> tuple[Path, Path] | None:
    """node.exe et index.js de la version la plus récente, comme le fait
    `cursor-agent.ps1` : dans son propre dossier s'il y a un node.exe, sinon
    dans `versions\\<la plus récente>`."""
    if (dossier / "node.exe").is_file() and (dossier / "index.js").is_file():
        return dossier / "node.exe", dossier / "index.js"
    versions = []
    if (dossier / "versions").is_dir():
        for d in (dossier / "versions").iterdir():
            m = _VERSION_CURSOR.match(d.name)
            if d.is_dir() and m:
                versions.append((tuple(int(x or 0) for x in m.groups()), d.name, d))
    for _, _, d in sorted(versions, reverse=True):
        if (d / "node.exe").is_file() and (d / "index.js").is_file():
            return d / "node.exe", d / "index.js"
    return None


def lancement(commande: list[str], env: dict[str, str], *, windows: bool | None = None,
              chercher: Callable[[str], str | None] | None = None) -> tuple[list[str], dict[str, str]]:
    """L'argv et l'environnement qu'on donne à CreateProcess, sans cmd.exe.

    Sous Windows, CreateProcess n'ajoute que `.exe` : `cursor-agent.cmd` et
    `codex.cmd` (npm) sont introuvables. Et les appeler quand même ferait
    passer le prompt par cmd.exe, qui le coupe aux retours à la ligne et
    interprète `& | % ^` : une injection. On refait donc ici ce que font leurs
    scripts — lancer node.exe sur leur .js —, résolu à chaque appel : une
    mise à jour de cursor-agent ajoute une version sans rien casser.
    """
    windows = WINDOWS if windows is None else windows
    if not windows or not commande:
        return commande, env
    # Le PATH de l'enfant, pas celui du pilote : c'est lui qui lancera.
    chercher = chercher or (lambda nom: shutil.which(nom, path=env["PATH"]) if env.get("PATH") else None)
    binaire, reste = commande[0], commande[1:]
    trouve = chercher(binaire)
    chemin = Path(trouve) if trouve else None
    if chemin is not None and chemin.suffix.lower() in (".exe", ".com"):
        return [str(chemin), *reste], env
    local = Path(env.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    if binaire == "cursor-agent":
        # Hors du PATH (le service ne voit pas celui de la session), il est
        # dans son dossier d'installation par défaut.
        dossier = chemin.parent if chemin else local / "cursor-agent"
        paire = _cursor(dossier)
        if paire is None:
            raise Introuvable(f"binaire introuvable : cursor-agent (aucune version lançable dans {dossier})")
        nom = f"{chemin.stem}.cmd" if chemin and chemin.suffix.lower() == ".cmd" else "cursor-agent.cmd"
        env = dict(env, CURSOR_INVOKED_AS=nom)
        env.setdefault("NODE_COMPILE_CACHE", str(local / "cursor-compile-cache"))
        return [str(paire[0]), str(paire[1]), *reste], env
    if chemin is None:
        raise Introuvable(f"binaire introuvable : {binaire}")
    if chemin.suffix.lower() == ".cmd":
        m = _SHIM_NPM.search(chemin.read_text(encoding="utf-8", errors="replace"))
        if m:
            # Le shim écrit son chemin à la Windows : un segment à la fois.
            script = chemin.parent.joinpath(*m.group(1).split("\\"))
            node = chemin.parent / "node.exe"
            node = str(node) if node.is_file() else chercher("node")
            if node and script.is_file():
                return [node, str(script), *reste], env
    raise Introuvable(f"{chemin} n'a pas de lancement sûr : un script passerait le prompt par cmd.exe")


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
        if agent.effort:
            commande += ["--effort", agent.effort]
        if lecture_seule:
            commande += [
                "--permission-mode", "default",
                "--allowedTools",
                # Rejouer un test n'écrit que des caches : le relecteur vérifie
                # une affirmation du codeur au lieu de la croire (lot #115).
                "Read,Glob,Grep,Bash(git diff:*),Bash(git log:*),Bash(git show:*),"
                "Bash(ls:*),Bash(cat:*),Bash(grep:*),Bash(head:*),Bash(wc:*),"
                "Bash(python3 -m pytest:*),Bash(py -m pytest:*)",
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
        if agent.effort:
            commande += ["-c", f'model_reasoning_effort="{agent.effort}"']
        if not lecture_seule:
            # Le bac à sable coupe le réseau, jusqu'aux sockets locales : les
            # tests du tableau et du service (127.0.0.1) y échouaient
            # (PermissionError, mesuré le 27 septembre 2026 sur le lot #115).
            commande += ["-c", "sandbox_workspace_write.network_access=true"]
        if sortie is not None:
            commande += ["--output-last-message", str(sortie)]
        return commande + [prompt]
    if agent.outil == "cursor":
        # Cursor n'a pas d'option d'effort : il est dans le nom du modèle
        # (`grok-4.7-high`), vérifié au chargement (projet.lire_agent).
        commande = [agent.binaire, "-p", prompt, "--model", agent.modele,
                    "--output-format", "text", "--trust"]
        commande += ["--mode", "ask"] if lecture_seule else ["--force"]
        return commande
    raise ValueError(f"outil inconnu : {agent.outil}")


@dataclass
class Resultat:
    """Ce qu'un appel a rendu. `attente` : personne n'a pu répondre (quota,
    session, outil qui ne démarre pas), le lot attend ; ce n'est pas un
    échec. `essais` dit, agent par agent, ce qui s'est passé."""

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
# Une place pour un agent de cet outil : vraie, tenue le temps de l'appel ;
# fausse quand l'outil a déjà tous ses agents en route (Verrous.place).
Place = Callable[[str], AbstractContextManager[bool]]


def executer(commande: list[str], cwd: Path, env: dict[str, str], delai: int) -> tuple[int, str, str]:
    try:
        commande, env = lancement(commande, env)
    except Introuvable as e:
        return 127, "", str(e)
    try:
        fini = subprocess.run(commande, cwd=cwd, env=env, capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              timeout=delai, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired as e:
        sortie = e.stdout.decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        return 124, sortie, f"délai dépassé après {delai} s"
    except FileNotFoundError:
        return 127, "", f"binaire introuvable : {commande[0]}"
    except OSError as e:
        return 126, "", f"ne démarre pas : {commande[0]} ({e})"
    return fini.returncode, fini.stdout, fini.stderr


def _appeler(agent: Agent, poste: Poste, prompt: str, cwd: Path, delai: int,
             executeur: Executeur) -> tuple[int, str, str, str]:
    """Un appel d'un agent : son code, sa sortie, son erreur, et son texte."""
    # La réponse finale de Codex s'écrit hors du dossier du lot : un
    # fichier laissé dans le worktree finirait dans le commit.
    sortie = Path(tempfile.mkdtemp(prefix="atelier-")) / "reponse.txt" if agent.outil == "codex" else None
    try:
        code, out, err = executeur(
            argv(agent, prompt, lecture_seule=poste.lecture_seule, sortie=sortie),
            Path(cwd), environnement(agent.outil), delai)
        texte = out
        if sortie is not None and sortie.exists():
            texte = sortie.read_text(encoding="utf-8", errors="replace")
    finally:
        if sortie is not None:
            shutil.rmtree(sortie.parent, ignore_errors=True)
    return code, out, err, texte


def invoquer(poste: Poste, prompt: str, cwd: Path, delai: int, *,
             exclure: frozenset[str] = frozenset(),
             executeur: Executeur = executer,
             place: Place | None = None) -> Resultat:
    """Essaie l'agent du poste, puis ses secours, dans l'ordre.

    `exclure` retire des familles de modèles (`Agent.famille`) : le modèle
    qui a écrit un lot ne le relit jamais, par quelque outil que ce soit.
    On ne passe au secours que pour un quota, une session, un outil qui ne
    démarre pas, ou un outil à son plafond d'agents simultanés (`place`) ;
    un agent qui échoue pour une autre raison a répondu, et c'est son échec.
    Chaque essai garde la ligne qui dit pourquoi : « écarté » sans raison ne
    se répare pas.
    """
    essais: list[str] = []
    ecartes = 0
    for agent in poste.agents:
        if agent.famille in exclure:
            essais.append(f"{agent} : écarté (sa famille, {agent.famille}, a écrit ce lot)")
            ecartes += 1
            continue
        with (place(agent.outil) if place else nullcontext(True)) as libre:
            if not libre:
                essais.append(f"{agent} : occupé ({agent.outil} a déjà tous ses agents en route)")
                continue
            code, out, err, texte = _appeler(agent, poste, prompt, cwd, delai, executeur)
        cause = cause_de_refus(code, f"{out}\n{err}")
        if cause:
            pourquoi = derniere_ligne(f"{out}\n{err}")
            essais.append(f"{agent} : {LIBELLES[cause]}" + (f" (« {pourquoi} »)" if pourquoi else ""))
            continue
        essais.append(f"{agent} : code {code}")
        return Resultat(agent=agent, code=code, texte=texte if code == 0 else f"{texte}\n{err}".strip(),
                        essais=essais)
    tous_ecartes = ecartes == len(essais)
    return Resultat(agent=None, code=-1, texte="", attente=not tous_ecartes,
                    personne=tous_ecartes, essais=essais)


# Le fichier qu'un agent qui écrit doit créer pour passer la sonde.
FICHIER_SONDE = "sonde-atelier.txt"


def sonder(poste: Poste, racine: Path, *, delai: int = 300,
           executeur: Executeur = executer) -> tuple[bool, str]:
    """Un agent répond-il, avec son modèle, en non interactif ? Et s'il écrit,
    écrit-il vraiment ? Un agent en lecture seule répond « OK » ; un agent qui
    écrit crée un fichier dans un dossier jetable, et la sonde le relit. Le
    29 septembre 2026, codex a répondu « OK » à la sonde du PC, puis n'a rien
    pu écrire sur le lot #120 (son bac à sable Windows ne démarrait pas) : le
    lot a brûlé son dernier essai. Rend (réussi, la ligne qui le dit)."""
    if poste.lecture_seule:
        res = invoquer(poste, "Réponds exactement par le mot : OK", racine, delai, executeur=executeur)
        return res.reussi and "OK" in res.texte, _detail(res)
    with tempfile.TemporaryDirectory(prefix="sonde-") as dossier:
        prompt = (f"Crée dans le dossier courant le fichier `{FICHIER_SONDE}`, qui contient exactement le mot OK. "
                  "Puis réponds exactement par le mot : OK")
        res = invoquer(poste, prompt, Path(dossier), delai, executeur=executeur)
        fichier = Path(dossier) / FICHIER_SONDE
        ecrit = fichier.is_file() and "OK" in fichier.read_text(encoding="utf-8", errors="replace")
    if res.reussi and not ecrit:
        return False, f"a répondu sans rien écrire : {_detail(res)}"
    return res.reussi and ecrit and "OK" in res.texte, _detail(res)


def _detail(res: Resultat) -> str:
    return res.texte.strip().splitlines()[-1][:80] if res.texte.strip() else "; ".join(res.essais)
