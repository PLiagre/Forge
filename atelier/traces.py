"""Ce qui fait rougir un contrôle, lu par le relecteur sans la main qui écrit.

Le relecteur doit nommer l'erreur d'un contrôle rouge : son prompt le lui
demande (`backends.prompt_du_role`). Il ne pouvait pas la lire. `gh api`
lui reste refusé, parce que la même commande sait aussi écrire. Et
`gh run view --log` rend zéro ligne avec le code 0 sur le gh 2.45 du VPS,
mesuré le 16 septembre 2026 sur le run 35060735773 : un outil qui se tait
ressemble à un journal vide. Le relecteur de la PR 15 a donc demandé la
trace au propriétaire, et la carte est tombée sans cause lisible.

Ce module fait une seule lecture : le journal d'un travail, à une adresse
qu'il construit lui-même depuis la table de `gh pr checks`. L'agent donne
un numéro de PR, rien d'autre : ni méthode, ni chemin, ni champ.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import subprocess

# L'adresse d'un travail, telle que `gh pr checks` l'imprime. Le dépôt se
# lit dans l'adresse : il ne dépend ni du dossier courant, ni d'un remote.
_TRAVAIL = re.compile(r"^https://github\.com/([^/\s]+/[^/\s]+)/actions/runs/\d+/job/(\d+)")
# L'horodatage que GitHub met en tête de chaque ligne de journal.
_HORODATAGE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z ")
# La ligne par laquelle GitHub dit qu'une étape a échoué. Ce qui la
# précède est la cause ; ce qui la suit est le rangement du runner.
_ERREUR = "##[error]"
# Un appel qui ne répond pas ne fait pas attendre le tour pour toujours.
DELAI = 60


@dataclass(frozen=True)
class Rouge:
    """Un contrôle en échec, et où lire son journal s'il en a un."""

    nom: str
    depot: str
    travail: str
    description: str


def rouges(table: str) -> list[Rouge]:
    """Les contrôles en échec d'une table de `gh pr checks`, dans son ordre.

    Un état posé par un travail (`relecture`) n'a pas d'adresse de travail :
    il garde sa description, qui dit déjà pourquoi il est rouge.
    """
    trouves = []
    for ligne in table.splitlines():
        champs = ligne.split("\t")
        if len(champs) < 2 or champs[1] != "fail":
            continue
        adresse = champs[3] if len(champs) > 3 else ""
        description = champs[4] if len(champs) > 4 else ""
        travail = _TRAVAIL.match(adresse)
        trouves.append(Rouge(
            nom=champs[0],
            depot=travail.group(1) if travail else "",
            travail=travail.group(2) if travail else "",
            description=description or adresse,
        ))
    return trouves


def extrait(journal: str, lignes: int) -> list[str]:
    """Les `lignes` dernières lignes avant la première erreur, sans horodatage.

    Sans ligne d'erreur, la fin du journal : on ne devine pas où est la cause.
    """
    propres = [_HORODATAGE.sub("", ligne) for ligne in journal.splitlines()]
    fin = next((i + 1 for i, ligne in enumerate(propres) if _ERREUR in ligne), len(propres))
    return propres[max(0, fin - lignes):fin]


def _gh(*args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["gh", *args], text=True, capture_output=True, check=False, timeout=DELAI,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(["gh", *args], 124, "", f"sans réponse après {DELAI} s")
    except OSError as exc:
        return subprocess.CompletedProcess(["gh", *args], 127, "", str(exc))


def rapport(numero: int, lignes: int, depot: str | None = None) -> tuple[int, str]:
    """Ce qui fait rougir chaque contrôle de la PR, et le code à rendre.

    Code 1 dès qu'une lecture échoue : un journal illisible se dit, il ne
    passe pas pour un journal vide.
    """
    table = _gh("pr", "checks", str(numero), *(["-R", depot] if depot else []))
    # `gh pr checks` rend 1 quand un contrôle échoue : c'est la table vide
    # qui dit qu'il n'a rien lu, pas son code.
    if not table.stdout.strip():
        raison = table.stderr.strip() or f"code {table.returncode}"
        return 1, f"FAIL  aucun contrôle lu sur la PR {numero} : {raison}"
    trouves = rouges(table.stdout)
    if not trouves:
        return 0, f"aucun contrôle en échec sur la PR {numero}"
    code = 0
    blocs = []
    for rouge in trouves:
        if not rouge.travail:
            blocs.append(f"== {rouge.nom} : pas de journal de travail — {rouge.description}")
            continue
        lu, corps = _lire(rouge, lignes)
        if not lu:
            code = 1
            blocs.append(f"== {rouge.nom} (travail {rouge.travail}) : {corps}")
            continue
        blocs.append(f"== {rouge.nom} (travail {rouge.travail})\n{corps}")
    return code, "\n\n".join(blocs)


def _lire(rouge: Rouge, lignes: int) -> tuple[bool, str]:
    journal = _gh("api", f"repos/{rouge.depot}/actions/jobs/{rouge.travail}/logs")
    if journal.returncode != 0:
        return False, f"journal illisible — {journal.stderr.strip() or f'code {journal.returncode}'}"
    return True, "\n".join(extrait(journal.stdout, lignes))


def lire(rouge: Rouge, lignes: int = 80) -> str:
    """L'extrait du journal d'un contrôle rouge, pour la correction du
    codeur. Un journal illisible se dit ; il ne passe pas pour un vide."""
    return _lire(rouge, lignes)[1]


def lire_run(depot: str, run: int, lignes: int = 80) -> str:
    """Ce qui fait rougir un run (la CI de master) : l'extrait du journal de
    chacun de ses travaux en échec. Un journal illisible se dit."""
    travaux = _gh("run", "view", str(run), "-R", depot, "--json", "jobs")
    if travaux.returncode != 0:
        return f"run {run} illisible : {travaux.stderr.strip()}"
    import json
    blocs = []
    for job in json.loads(travaux.stdout or "{}").get("jobs", []):
        if job.get("conclusion") != "failure":
            continue
        journal = _gh("api", f"repos/{depot}/actions/jobs/{job.get('databaseId')}/logs")
        corps = "\n".join(extrait(journal.stdout, lignes)) if journal.returncode == 0 else "journal illisible"
        blocs.append(f"== {job.get('name')}\n{corps}")
    return "\n\n".join(blocs) or f"aucun travail en échec lisible dans le run {run}"
