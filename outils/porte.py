"""La porte de master : lectures et décision, sans charger les autres outils."""

from __future__ import annotations

import argparse
import os
from dataclasses import replace
from pathlib import Path
import sys

from . import demandes, github, integration, registre, relecture


def _verdict(gh: github.Github, numero: int, revision: str) -> relecture.Verdict:
    """La relecture de cette révision, calculée ici — pas lue sur la PR.

    Le contrôle `relecture` est posé par un travail qui tourne sur le code
    de la PR ; s'y fier pour fusionner laisserait une PR changer le code
    qui la juge. Même module, même règle, mais appelé depuis `master`.
    """
    return relecture.juger(
        revision,
        github.auteurs_du_code(gh, numero),
        relecture.revues_depuis_github(github.revues(gh, numero)),
    )


def _pr_integrable(gh: github.Github, brut: dict, base: str, prefixes, zone=()) -> integration.PR:
    """Une PR, avec ce qu'il faut pour décider — et pas un appel de plus.

    Un brouillon ou une branche hors périmètre est écarté avant d'aller
    chercher ses contrôles : c'est le cas ordinaire du dépôt, et il ne
    coûte rien.
    """
    minimale = integration.depuis_github(brut)
    if minimale.brouillon or not integration.integree(minimale.branche, prefixes):
        return minimale
    # Un préfixe ne prouve pas une origine. La tête doit vivre dans ce dépôt,
    # et `demandes.interne` le dit pour les demandes de lot comme ici : un
    # seul prédicat, deux appelants. Une origine illisible vaut une fourche,
    # et une fourche ne coûte aucun appel de plus.
    if not demandes.interne(gh, brut):
        return integration.depuis_github(brut, interne=False)
    detail = gh.get(f"pulls/{brut['number']}")
    sha = detail["head"]["sha"]
    try:
        fichiers = github.fichiers_pr(gh, brut["number"], detail.get("changed_files"))
        if zone:
            cible = detail.get("base")
            if not isinstance(cible, dict) or cible.get("ref") != base:
                raise github.GithubErreur("base de la PR changée ou illisible")
            base_sha = cible.get("sha")
            proteges = github.fichiers_proteges(gh, base_sha, sha, zone)
            fichiers = tuple(sorted(set(fichiers) | set(proteges)))
        controles = github.controles(gh, sha)
        retard = github.retard(gh, base, sha)
        verdict = _verdict(gh, brut["number"], sha)
        # La tête peut bouger pendant n'importe laquelle de ces lectures.
        # Le geste vérifiera encore ce SHA juste avant d'écrire sur GitHub.
        apres = gh.get(f"pulls/{brut['number']}")
        if apres.get("head", {}).get("sha") != sha:
            raise github.GithubErreur("fichiers de la PR : révision changée pendant la lecture")
        if zone:
            cible_apres = apres.get("base")
            if (not isinstance(cible_apres, dict) or cible_apres.get("ref") != base
                    or cible_apres.get("sha") != base_sha):
                raise github.GithubErreur("base de la PR changée pendant la lecture")
    except github.GithubErreur as exc:
        return replace(integration.depuis_github(brut, detail, interne=True),
                       motif_fichiers=f"fichiers de la PR illisibles : {exc}")
    return replace(integration.depuis_github(
        brut, detail, controles, retard, verdict, interne=True,
    ), fichiers=fichiers)


def _integration(args: argparse.Namespace) -> int:
    racine = Path(args.projet)
    reglage = registre.integration(racine)
    base = args.base or registre.branchement(racine)["base"]
    gh = github.Github(args.depot, args.jeton)
    prs = [
        _pr_integrable(gh, brut, base, reglage["branches"], reglage["zone"])
        for brut in gh.liste("pulls", state="open", base=base)
    ]
    rapport = integration.decider(prs, reglage["controles"], reglage["branches"], reglage["zone"])
    for ligne in rapport.lignes:
        print(ligne, file=sys.stderr)
    decision = rapport.decision
    if decision.action == integration.RIEN or decision.pr is None:
        print("RIEN")
        print(decision.raison, file=sys.stderr)
        return 0
    fichier_sortie = args.sortie or os.environ.get("SORTIE_DECISION")
    if fichier_sortie:
        selection = next(pr for pr in prs if pr.numero == decision.pr)
        with Path(fichier_sortie).open("a", encoding="utf-8") as sortie:
            sortie.write(f"revision={selection.revision}\n")
    print(f"{decision.action} {decision.pr}")
    print(f"→ {decision.action} PR {decision.pr} : {decision.raison}", file=sys.stderr)
    return 0


def main(argv=None):
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--depot", required=True)
    parseur.add_argument("--projet", default=".")
    parseur.add_argument("--base")
    parseur.add_argument("--jeton")
    parseur.add_argument("--sortie")
    args = parseur.parse_args(argv)
    try:
        return _integration(args)
    except (github.GithubErreur, registre.BranchementIncomplet) as exc:
        print(f"FAIL  {github.borner(str(exc), github.BORNE_DESCRIPTION - 6)}", file=sys.stderr)
        return 1
