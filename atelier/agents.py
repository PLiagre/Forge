"""Appeler un agent : la ligne de commande exacte, la session, la mesure.

Un agent est Claude Code, lancé sans écran avec un modèle. Ce module
construit son argv — le shell n'en compose aucune —, lui donne sa consigne
par l'entrée standard, et l'exécute dans le dossier du lot, sans clé d'API
dans l'environnement : une clé ferait basculer la facture de l'abonnement
vers l'unité.

Un agent n'a jamais la main sur GitHub : il édite des fichiers, ou il rend
un texte. Commit, poussée, PR, commentaire, étiquette et fusion
appartiennent au pilote : un avis ne peut pas être falsifié par celui qui le
donne.

Trois choses tiennent ici :

- **la session** : un appel ouvre une session nommée ou la reprend. Une
  session reprise se souvient de ce qu'elle a lu et fait ; une session
  introuvable repart avec la consigne entière ;
- **la trace** : la sortie de l'agent s'écrit dans un fichier au fil de
  l'eau. Un appel coupé par son délai garde ce qu'il a déjà dit et ce qu'il
  a déjà coûté ;
- **l'attente** : quota épuisé, session de l'abonnement expirée, outil qui
  ne démarre pas ou qui a déjà tous ses agents en route — le lot attend, ce
  n'est pas un échec, et le tour suivant réessaie.
"""

from __future__ import annotations

from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from typing import Callable

from .projet import Agent

WINDOWS = sys.platform.startswith("win")

# Les clés qu'on retire avant de lancer un agent : aucune facture à l'unité,
# seul l'abonnement (Claude ou Google Antigravity) tourne.
CLES_API = (
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "CURSOR_API_KEY",
    "GEMINI_API_KEY", "GOOGLE_API_KEY", "NANOBANANA_API_KEY",
)

# Le jeton longue durée de Claude Code (`claude setup-token`), rangé par le
# propriétaire dans un fichier en mode 600. Il est lu ici et passé à l'enfant
# par l'environnement : il n'apparaît ni dans l'argv, ni dans un journal.
FICHIER_JETON_CLAUDE = Path(os.environ.get(
    "ATELIER_JETON_CLAUDE", str(Path.home() / ".atelier" / "claude.token")))

# Ce qu'un agent n'a jamais le droit de faire : le pilote s'en charge.
GESTES_DU_PILOTE = (
    "Bash(git push:*)", "Bash(git commit:*)", "Bash(git reset:*)",
    "Bash(git checkout:*)", "Bash(git switch:*)", "Bash(git rebase:*)",
    "Bash(git merge:*)", "Bash(gh:*)",
)
# Ce qu'un rôle en lecture seule peut lancer : lire, et rejouer un test.
LECTURE = ("Read,Glob,Grep,Bash(git diff:*),Bash(git log:*),Bash(git show:*),Bash(ls:*),Bash(cat:*),"
           "Bash(grep:*),Bash(head:*),Bash(wc:*),Bash(python3 -m pytest:*),Bash(py -m pytest:*)")
# Ce qu'un rôle qui nomme ses outils (`Appel.outils`) n'a jamais : écrire,
# chercher dans des fichiers, ouvrir le réseau, appeler un autre agent.
HORS_DU_JEU = "Edit,Write,NotebookEdit,Agent,Bash,Glob,Grep,WebFetch,WebSearch"

# La garde des commandes, appelée par Claude Code avant chaque commande de
# shell d'un agent ou de son sous-agent (`garde_commandes.py`).
GARDE = Path(__file__).resolve().parent / "garde_commandes.py"

# Les signes d'un quota épuisé ou d'une session expirée, lus dans la fin de
# ce qu'a rendu un agent qui a échoué.
_QUOTA = re.compile(
    r"rate.?limit|usage limit|quota|too many requests|\b429\b|limit reached|"
    r"you'?ve hit your|out of credits|out of usage|insufficient_quota|credit balance|"
    r"plan limit|overloaded|resource_exhausted|quota_exhausted|individual quota", re.I)
_AUTH = re.compile(
    r"unauthori[sz]ed|\b401\b|not logged in|log ?in required|please (log|sign) ?in|"
    r"invalid (api )?key|token (has )?expired|session expired|oauth|setup-token|"
    r"authentication (failed|required|error)", re.I)
# Le harnais refuse l'appel tel que la chaîne le construit : une option qu'il
# ne connaît pas, une valeur de réglage qu'il refuse. C'est le réglage ou la
# version du harnais qui est en cause, pas l'agent.
_APPEL = re.compile(r"error: unknown option '|error: unexpected argument '|unknown variant `|error loading config|"
                    r"invalid model selection", re.I)
# Ce que dit le harnais quand la session demandée n'est pas celle qu'on croit.
_SESSION_INCONNUE = re.compile(r"No conversation found with session ID|conversation[^\n]*not found|unknown conversation",
                               re.I)
_SESSION_PRISE = re.compile(r"Session ID \S+ is already in use", re.I)

# Les codes d'un outil qui n'a pas démarré : introuvable (127) ou refusé par
# le système (126). C'est une panne de la machine, pas un échec de l'agent.
CODES_INSTALLATION = (126, 127)
CODE_COUPE = 124
LIBELLES = {"quota": "quota épuisé", "auth": "session de l'abonnement expirée ou absente",
            "installation": "ne démarre pas", "appel": "refuse l'appel (option, effort ou réglage)"}
_SECRET = re.compile(r"\b(sk-[A-Za-z0-9_-]{8,}|[A-Za-z0-9_-]{40,})")


def cause_de_refus(code: int, texte: str) -> str | None:
    """`quota`, `auth`, `installation`, `appel` ou None. Seule la fin de la
    sortie compte : c'est là que l'outil écrit son erreur, et le travail d'un
    agent peut citer ces mots sans que ce soit un refus."""
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


# Le .js qu'un shim npm (`<outil>.cmd`) fait lancer par node.
_SHIM_NPM = re.compile(r'"%dp0%\\([^"%]+\.js)"')


def lancement(commande: list[str], env: dict[str, str], *, windows: bool | None = None,
              chercher: Callable[[str], str | None] | None = None) -> tuple[list[str], dict[str, str]]:
    """L'argv et l'environnement qu'on donne à CreateProcess, sans cmd.exe.

    Sous Windows, CreateProcess n'ajoute que `.exe` : les shims npm
    (`<outil>.cmd`) sont introuvables. Et les appeler quand même ferait
    passer les arguments par cmd.exe, qui interprète `& | % ^` : une
    injection. On refait donc ici ce que fait le shim — lancer node.exe sur
    son .js —, résolu à chaque appel.
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
    raise Introuvable(f"{chemin} n'a pas de lancement sûr : un script passerait les arguments par cmd.exe")


def environnement(outil: str = "claude") -> dict[str, str]:
    """L'environnement d'un agent : sans clé d'API, avec le jeton de
    l'abonnement, et sans tâche de fond — un sous-agent ou une commande lancés
    « en arrière-plan » laisseraient la session rendre la main avant d'avoir
    leur résultat."""
    env = {k: v for k, v in os.environ.items() if k not in CLES_API}
    if outil == "claude" and FICHIER_JETON_CLAUDE.is_file():
        jeton = FICHIER_JETON_CLAUDE.read_text(encoding="utf-8").strip()
        if jeton:
            env["CLAUDE_CODE_OAUTH_TOKEN"] = jeton
    env["CLAUDE_CODE_DISABLE_BACKGROUND_TASKS"] = "1"
    return env


@dataclass(frozen=True)
class Appel:
    """Ce qu'on demande à un agent.

    `consigne` tient seule : c'est ce que reçoit une session neuve. `suite`
    est ce que reçoit une session reprise, qui se souvient du reste ; sans
    elle, la session reprise reçoit la consigne entière. `schema` : la forme
    de ce que l'agent doit rendre, que le harnais vérifie. `sous_agents` : ceux
    que la session peut appeler (le développeur, pour le chef).

    Le testeur ne lit pas le dépôt et n'y écrit pas : `outils` nomme ses
    seuls outils, `garde` le script qui juge chacun de leurs appels avec ses
    arguments (à la place de la garde des commandes), et `environnement` ce
    que son outil de jeu lit (le build, le dossier de ses photos)."""

    role: str
    consigne: str
    lecture_seule: bool
    suite: str = ""
    session: str | None = None
    reprendre: bool = False
    schema: dict | None = None
    sous_agents: dict | None = None
    sans_outil: bool = False
    jours_max: int = 400
    outils: tuple[str, ...] = ()
    garde: tuple[str, ...] = ()
    environnement: tuple[tuple[str, str], ...] = ()


def reglages(appel: Appel) -> dict:
    """Les réglages passés à Claude Code pour cet appel : la garde, jouée
    avant chaque commande de shell ; pour un rôle qui a sa propre garde,
    avant chaque appel d'outil."""
    if appel.garde:
        from .garde_testeur import JUGES
        commande = " ".join(f'"{morceau}"' for morceau in (sys.executable, *appel.garde))
        return {"hooks": {"PreToolUse": [{"matcher": "|".join(JUGES),
                                          "hooks": [{"type": "command", "command": commande}]}]}}
    commande = f'"{sys.executable}" "{GARDE}" {appel.jours_max}'
    return {"hooks": {"PreToolUse": [{"matcher": "Bash|PowerShell",
                                      "hooks": [{"type": "command", "command": commande}]}]}}


def entree(agent: Agent, consigne: str) -> str:
    """Ce qui part sur l'entrée standard du harnais. Antigravity CLI attend un
    événement JSON par ligne sous `--input-format stream-json` ; Claude Code
    lit la consigne en texte brut."""
    if agent.outil == "antigravity":
        return json.dumps({"event": "user", "message": {"content": consigne}}, ensure_ascii=False) + "\n"
    return consigne


def argv(agent: Agent, appel: Appel, *, reprise: bool, windows: bool | None = None) -> list[str]:
    """L'argv exact. Construit ici, exécuté par `invoquer`, jamais recomposé.
    La consigne n'y est pas : elle passe par l'entrée standard."""
    if agent.outil == "antigravity":
        # En flux des deux côtés : la consigne arrive sur stdin (jamais dans
        # l'argv), et chaque étape/outil s'écrit dans la trace au fil de l'eau.
        commande = [agent.binaire, "--input-format", "stream-json", "--output-format", "stream-json",
                    "--model", agent.modele]
        if agent.effort:
            commande += ["--effort", agent.effort]
        if appel.session and reprise:
            commande += ["--conversation", appel.session]
        if appel.schema:
            commande += ["--json-schema", json.dumps(appel.schema, ensure_ascii=False)]
        if appel.lecture_seule or appel.sans_outil:
            commande += ["--sandbox"]
        else:
            commande += ["--dangerously-skip-permissions"]
        return commande
    windows = WINDOWS if windows is None else windows
    # En flux : chaque message de l'agent s'écrit dès qu'il existe, avec ce
    # qu'il a coûté. Un appel coupé garde donc sa trace et sa mesure.
    commande = [agent.binaire, "-p", "--model", agent.modele, "--output-format", "stream-json", "--verbose"]
    if agent.effort:
        commande += ["--effort", agent.effort]
    if appel.session:
        commande += ["--resume" if reprise else "--session-id", appel.session]
    if appel.schema:
        commande += ["--json-schema", json.dumps(appel.schema, ensure_ascii=False)]
    if appel.sous_agents:
        commande += ["--agents", json.dumps(appel.sous_agents, ensure_ascii=False)]
    if appel.sans_outil:
        return commande + ["--tools", ""]
    commande += ["--settings", json.dumps(reglages(appel), ensure_ascii=False)]
    if appel.outils:
        return commande + ["--permission-mode", "default", "--allowedTools", ",".join(appel.outils),
                           "--disallowedTools", HORS_DU_JEU + "," + ",".join(GESTES_DU_PILOTE)]
    if appel.lecture_seule:
        return commande + ["--permission-mode", "default", "--allowedTools", LECTURE,
                           "--disallowedTools", "Edit,Write,NotebookEdit,Agent," + ",".join(GESTES_DU_PILOTE)]
    permis = "Read,Glob,Grep,Edit,Write,Bash" + (",PowerShell" if windows else "") \
        + (",Agent" if appel.sous_agents else "")
    return commande + ["--permission-mode", "acceptEdits", "--allowedTools", permis,
                       "--disallowedTools", ",".join(GESTES_DU_PILOTE)]


def _evenements(sortie: str) -> list[dict]:
    lus = []
    for ligne in sortie.splitlines():
        ligne = ligne.strip()
        if not ligne.startswith("{"):
            continue
        try:
            lu = json.loads(ligne)
        except ValueError:
            continue
        if isinstance(lu, dict):
            lus.append(lu)
    return lus


def _jetons(usage: dict) -> dict:
    """Les jetons d'un usage de l'API, sous nos noms."""
    return {"entree": usage.get("input_tokens") or usage.get("inputTokens") or 0,
            "sortie": usage.get("output_tokens") or usage.get("outputTokens") or 0,
            "cache_lu": (usage.get("cache_read_input_tokens") or usage.get("cacheReadInputTokens")
                         or usage.get("cache_read_tokens") or 0),
            "cache_ecrit": usage.get("cache_creation_input_tokens") or usage.get("cacheCreationInputTokens") or 0}


@dataclass
class Lecture:
    """Ce qu'on lit dans la sortie en flux d'un appel."""

    texte: str = ""
    sortie: dict | None = None
    mesure: dict = field(default_factory=dict)
    session: str | None = None
    fini: bool = False


def _lire_flux_antigravity(evenements: list[dict]) -> Lecture:
    """Le flux NDJSON d'Antigravity CLI (`init`, `step_update`, `result`)."""
    lecture = Lecture()
    modele_init = None
    images = 0
    for e in evenements:
        if e.get("conversation_id") and not lecture.session:
            lecture.session = e["conversation_id"]
        if e.get("event") == "init" and isinstance(e.get("init"), dict):
            modele_init = e["init"].get("model") or modele_init
        if e.get("event") == "step_update" and isinstance(e.get("step_update"), dict):
            su = e["step_update"]
            if su.get("conversation_id") and not lecture.session:
                lecture.session = su["conversation_id"]
            if su.get("step_type") == "tool" and su.get("state") == "DONE" and su.get("tool_name") == "generate_image":
                images += 1
    mesure: dict = {}
    if images:
        mesure["images"] = images
    resultat = next((e["result"] for e in reversed(evenements)
                     if e.get("event") == "result" and isinstance(e.get("result"), dict)), None)
    if resultat is not None:
        lecture.fini = True
        if resultat.get("conversation_id"):
            lecture.session = resultat["conversation_id"]
        statut = str(resultat.get("status") or "").upper()
        erreur = bool(statut and statut != "SUCCESS") or bool(resultat.get("error"))
        reponse = resultat.get("response") if isinstance(resultat.get("response"), str) else ""
        err_msg = resultat.get("error") if isinstance(resultat.get("error"), str) else ""
        lecture.texte = f"{reponse}\n{err_msg}".strip() if err_msg else reponse
        if isinstance(resultat.get("structured_output"), dict):
            lecture.sortie = resultat["structured_output"]
        duree = resultat.get("duration_seconds")
        usage = resultat.get("usage") if isinstance(resultat.get("usage"), dict) else None
        modeles = {modele_init or "antigravity": _jetons(usage)} if usage else None
        mesure |= {"tours": resultat.get("num_turns"),
                   "duree": round(duree) if isinstance(duree, (int, float)) else None,
                   "modeles": modeles, "erreur": erreur}
    else:
        textes: list[str] = []
        totaux = {"entree": 0, "sortie": 0, "cache_lu": 0, "cache_ecrit": 0}
        a_usage = False
        for e in evenements:
            if e.get("event") != "step_update" or not isinstance(e.get("step_update"), dict):
                continue
            su = e["step_update"]
            if su.get("step_type") == "agent_response" and isinstance(su.get("text_delta"), str):
                textes.append(su["text_delta"])
            if su.get("state") == "DONE" and isinstance(su.get("usage"), dict):
                a_usage = True
                for cle, valeur in _jetons(su["usage"]).items():
                    totaux[cle] += valeur
        lecture.texte = "".join(textes).strip()
        mesure |= {"modeles": {modele_init or "antigravity": totaux} if a_usage else None, "coupe": True}
    lecture.mesure = {k: v for k, v in mesure.items() if v is not None and v is not False}
    return lecture


def lire_flux(sortie: str) -> Lecture:
    """Le texte de l'agent, sa sortie structurée et la mesure de l'appel.

    Lit aussi bien le flux de Claude Code (`type`: system/assistant/result)
    que celui d'Antigravity CLI (`event`: init/step_update/result)."""
    evenements = _evenements(sortie)
    if any("event" in e and "type" not in e for e in evenements):
        return _lire_flux_antigravity(evenements)
    lecture = Lecture()
    lecture.session = next((e.get("session_id") for e in evenements if e.get("session_id")), None)
    limites = [e["rate_limit_info"]["unifiedWindows"] for e in evenements
               if e.get("type") == "rate_limit_event" and isinstance(e.get("rate_limit_info"), dict)
               and isinstance(e["rate_limit_info"].get("unifiedWindows"), dict)]
    mesure: dict = {}
    if limites:
        dites = {nom: fenetre.get("utilization") for nom, fenetre in limites[-1].items() if isinstance(fenetre, dict)}
        mesure["limites"] = {"cinq_heures": dites.get("five_hour"), "semaine": dites.get("seven_day")}
    resultat = next((e for e in reversed(evenements) if e.get("type") == "result"), None)
    if resultat is not None:
        lecture.fini = True
        lecture.texte = resultat.get("result") if isinstance(resultat.get("result"), str) else ""
        if isinstance(resultat.get("structured_output"), dict):
            lecture.sortie = resultat["structured_output"]
        modeles = {nom: _jetons(u) | {"cout": u.get("costUSD")} for nom, u in (resultat.get("modelUsage") or {}).items()
                   if isinstance(u, dict)}
        duree = resultat.get("duration_ms")
        mesure |= {"cout": resultat.get("total_cost_usd"), "tours": resultat.get("num_turns"),
                   "duree": round(duree / 1000) if isinstance(duree, (int, float)) else None,
                   "modeles": modeles or None, "erreur": bool(resultat.get("is_error"))}
    else:
        # Chaque message de l'agent porte son usage ; un même message revient
        # pour chacun de ses blocs, avec le même usage : on le compte une fois.
        par_message: dict[str, tuple[str, dict]] = {}
        textes: list[str] = []
        for e in evenements:
            message = e.get("message") if e.get("type") == "assistant" else None
            if not isinstance(message, dict):
                continue
            if isinstance(message.get("usage"), dict):
                par_message[message.get("id") or str(len(par_message))] = (message.get("model") or "?", message["usage"])
            if not e.get("parent_tool_use_id"):
                textes += [b.get("text", "") for b in message.get("content") or []
                           if isinstance(b, dict) and b.get("type") == "text"]
        modeles: dict[str, dict] = {}
        for modele, usage in par_message.values():
            somme = modeles.setdefault(modele, {"entree": 0, "sortie": 0, "cache_lu": 0, "cache_ecrit": 0})
            for cle, valeur in _jetons(usage).items():
                somme[cle] += valeur
        lecture.texte = "\n".join(t for t in textes[-3:] if t.strip())
        mesure |= {"modeles": modeles or None, "coupe": True}
    lecture.mesure = {k: v for k, v in mesure.items() if v is not None and v is not False}
    return lecture


@dataclass
class Resultat:
    """Ce qu'un appel a rendu. `attente` : personne n'a pu répondre (quota,
    session de l'abonnement, outil qui ne démarre pas, outil plein) ; ce n'est
    pas un échec. `coupe` : le délai a coupé l'appel ; sa session reprend.
    `neuve` : la session a été ouverte par cet appel (la première fois, ou
    parce que celle qu'on voulait reprendre a disparu)."""

    agent: Agent | None
    code: int
    texte: str = ""
    sortie: dict | None = None
    attente: bool = False
    raison: str = ""
    mesure: dict = field(default_factory=dict)
    session: str | None = None
    neuve: bool = False
    trace: str = ""

    @property
    def coupe(self) -> bool:
        return self.code == CODE_COUPE

    @property
    def reussi(self) -> bool:
        return self.agent is not None and self.code == 0 and not self.attente


# (argv, dossier, environnement, délai, consigne, fichier de trace) → (code, sortie, erreur)
Executeur = Callable[[list[str], Path, dict[str, str], int, str, Path | None], tuple[int, str, str]]
# Une place pour un agent de cet outil : vraie, tenue le temps de l'appel ;
# fausse quand l'outil a déjà tous ses agents en route (Verrous.place).
Place = Callable[[str], AbstractContextManager[bool]]


def dossier_des_traces() -> Path:
    return Path(os.environ.get("ATELIER_APPELS") or Path.home() / ".atelier" / "appels")


def _tuer(processus: subprocess.Popen) -> None:
    """Arrête l'agent et tout ce qu'il a lancé : un test resté en route après
    son agent tiendrait un processeur pour rien."""
    try:
        if WINDOWS:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(processus.pid)], capture_output=True, timeout=30)
        else:
            os.killpg(processus.pid, signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        processus.kill()


def executer(commande: list[str], cwd: Path, env: dict[str, str], delai: int, consigne: str,
             trace: Path | None) -> tuple[int, str, str]:
    """Lance l'agent, lui donne sa consigne, et écrit sa sortie dans `trace`
    au fil de l'eau. Coupé par son délai, l'appel rend 124 et ce qu'il avait
    déjà écrit."""
    try:
        commande, env = lancement(commande, env)
    except Introuvable as e:
        return 127, "", str(e)
    jetable = trace is None
    if jetable:
        descripteur, nom = tempfile.mkstemp(prefix="appel-", suffix=".jsonl")
        os.close(descripteur)
        trace = Path(nom)
    trace.parent.mkdir(parents=True, exist_ok=True)
    erreurs = trace.with_suffix(".err")
    try:
        with trace.open("wb") as sortie, erreurs.open("wb") as err:
            try:
                processus = subprocess.Popen(commande, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=sortie,
                                             stderr=err, start_new_session=not WINDOWS)
            except FileNotFoundError:
                return 127, "", f"binaire introuvable : {commande[0]}"
            except OSError as e:
                return 126, "", f"ne démarre pas : {commande[0]} ({e})"
            try:
                processus.stdin.write(consigne.encode("utf-8"))
                processus.stdin.close()
            except OSError:
                pass
            try:
                code = processus.wait(timeout=delai)
                dit = ""
            except subprocess.TimeoutExpired:
                _tuer(processus)
                processus.wait()
                code, dit = CODE_COUPE, f"délai dépassé après {delai} s"
        lu = trace.read_text(encoding="utf-8", errors="replace")
        return code, lu, dit or erreurs.read_text(encoding="utf-8", errors="replace")
    finally:
        if erreurs.exists() and (jetable or erreurs.stat().st_size == 0):
            erreurs.unlink()
        if jetable and trace.exists():
            trace.unlink()


def invoquer(agent: Agent, appel: Appel, cwd: Path, delai: int, *,
             executeur: Executeur = executer, place: Place | None = None,
             trace: Path | None = None) -> Resultat:
    """Appelle l'agent. Il reprend la session si on le demande, en ouvre une
    sinon ; si la session à reprendre a disparu, ou si celle à ouvrir existe
    déjà, il fait l'autre geste, et le dit (`neuve`)."""
    with (place(agent.outil) if place else nullcontext(True)) as libre:
        if not libre:
            return Resultat(agent=None, code=-1, attente=True,
                            raison=f"{agent} : occupé ({agent.outil} a déjà tous ses agents en route)")
        reprise = bool(appel.session and appel.reprendre)
        env = environnement(agent.outil) | dict(appel.environnement)
        for essai in (1, 2):
            consigne = appel.suite if reprise and appel.suite else appel.consigne
            code, brut, err = executeur(argv(agent, appel, reprise=reprise), Path(cwd), env, delai,
                                        entree(agent, consigne), trace)
            if essai == 1 and appel.session and code not in (0, CODE_COUPE):
                if reprise and _SESSION_INCONNUE.search(f"{brut}\n{err}"):
                    reprise = False
                    continue
                if not reprise and _SESSION_PRISE.search(f"{brut}\n{err}"):
                    reprise = True
                    continue
            break
    lecture = lire_flux(brut)
    if code != CODE_COUPE:
        # Seul le délai coupe un appel : un appel refusé ou en panne n'a pas
        # non plus de message « result », et ce n'est pas une coupure.
        lecture.mesure.pop("coupe", None)
    if lecture.mesure.get("erreur") and code == 0:
        # Une erreur que le harnais dit dans son flux sans la rendre par son code.
        code = 1
    cause = cause_de_refus(code, f"{lecture.texte}\n{err}") if code != CODE_COUPE else None
    if cause:
        pourquoi = derniere_ligne(f"{lecture.texte}\n{err}")
        return Resultat(agent=None, code=code, attente=True, mesure=lecture.mesure,
                        raison=f"{agent} : {LIBELLES[cause]}" + (f" (« {pourquoi} »)" if pourquoi else ""))
    texte = lecture.texte if code == 0 else f"{lecture.texte}\n{err}".strip()
    session_rendue = (lecture.session or appel.session) if agent.outil == "antigravity" else (appel.session or lecture.session)
    return Resultat(agent=agent, code=code, texte=texte, sortie=lecture.sortie if code == 0 else None,
                    raison=err.strip() if code == CODE_COUPE else "", mesure=lecture.mesure,
                    session=session_rendue, neuve=bool(session_rendue) and not reprise,
                    trace=str(trace) if trace else "")


def nom_de_trace(lot: int | str, role: str, quand: datetime | None = None) -> Path:
    """Le fichier où s'écrit la sortie d'un appel : `<lot>-<rôle>-<instant>.jsonl`."""
    quand = quand or datetime.now(timezone.utc)
    return dossier_des_traces() / f"{lot}-{role}-{quand:%Y%m%dT%H%M%S}.jsonl"


# Le fichier qu'un agent qui écrit doit créer pour passer la sonde.
FICHIER_SONDE = "sonde-atelier.txt"


def sonder(agent: Agent, role: str, lecture_seule: bool, *, delai: int = 300,
           executeur: Executeur = executer) -> tuple[bool, str]:
    """Un agent répond-il, avec son modèle, sans écran ? Et s'il écrit,
    écrit-il vraiment ? Un agent en lecture seule répond « OK » ; un agent qui
    écrit crée un fichier dans un dossier jetable, et la sonde le relit.
    Rend (réussi, la ligne qui le dit)."""
    with tempfile.TemporaryDirectory(prefix="sonde-", ignore_cleanup_errors=True) as dossier:
        if lecture_seule:
            consigne = "Réponds exactement par le mot : OK"
        else:
            consigne = (f"Crée dans le dossier courant le fichier `{FICHIER_SONDE}`, qui contient exactement le mot "
                        "OK. Puis réponds exactement par le mot : OK")
        res = invoquer(agent, Appel(role=role, consigne=consigne, lecture_seule=lecture_seule), Path(dossier), delai,
                       executeur=executeur)
        fichier = Path(dossier) / FICHIER_SONDE
        ecrit = fichier.is_file() and "OK" in fichier.read_text(encoding="utf-8", errors="replace")
    detail = res.texte.strip().splitlines()[-1][:80] if res.texte.strip() else res.raison
    if lecture_seule:
        return res.reussi and "OK" in res.texte, detail
    if res.reussi and not ecrit:
        return False, f"a répondu sans rien écrire : {detail}"
    return res.reussi and ecrit and "OK" in res.texte, detail
