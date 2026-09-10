"""Les trois décisions, en ligne de commande.

    python3 -m outils relecture   --depot O/R --pr N
    python3 -m outils integration --depot O/R --projet .
    python3 -m outils palier      --projet . [--ecrire]
    python3 -m outils tableau     --depot O/R --projet . --sortie site/index.html
    python3 -m outils saisie      --projet . --corps demande.md [--ecrire]
    python3 -m outils controles   --depot O/R --pr N
    python3 -m outils brouillon   --depot O/R --pr N
    python3 -m outils etat        --projet . --lot NNN --etat abandonne [--ecrire]

Chacune imprime **une** ligne sur la sortie standard — celle que le
workflow lit — et son compte rendu sur l'erreur standard. Aucune n'écrit
sur GitHub : `relecture` et `integration` disent ce qui est, le workflow
fait le geste. `palier --ecrire` est la seule qui touche un fichier, et
seulement celui du registre.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import sys

from . import (actions, attention, demandes, github, histoire, integration, mesure,
               palier, registre, relecture, saisie, sante, tableau)


def _relecture(args: argparse.Namespace) -> int:
    gh = github.Github(args.depot, args.jeton)
    pr = gh.get(f"pulls/{args.pr}")
    revision = args.revision or pr["head"]["sha"]
    verdict = relecture.juger(
        revision,
        github.auteurs_du_code(gh, args.pr),
        relecture.revues_depuis_github(github.revues(gh, args.pr)),
    )
    # Bornée ici, une fois : cette ligne est reprise telle quelle dans la
    # description de l'état de commit, et le workflow n'a rien à couper.
    print(github.borner(f"{'PASS' if verdict.passe else 'FAIL'}  PR {args.pr} — {verdict.raison}"))
    return 0 if verdict.passe else 1


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


def _pr_integrable(gh: github.Github, brut: dict, base: str, prefixes) -> integration.PR:
    """Une PR, avec ce qu'il faut pour décider — et pas un appel de plus.

    Un brouillon ou une branche hors périmètre est écarté avant d'aller
    chercher ses contrôles : c'est le cas ordinaire du dépôt, et il ne
    coûte rien.
    """
    minimale = integration.depuis_github(brut)
    if minimale.brouillon or not integration.integree(minimale.branche, prefixes):
        return minimale
    detail = gh.get(f"pulls/{brut['number']}")
    sha = detail["head"]["sha"]
    return integration.depuis_github(
        brut, detail, github.controles(gh, sha), github.retard(gh, base, sha),
        _verdict(gh, brut["number"], sha),
    )


def _integration(args: argparse.Namespace) -> int:
    racine = Path(args.projet)
    reglage = registre.integration(racine)
    base = args.base or registre.branchement(racine)["base"]
    gh = github.Github(args.depot, args.jeton)
    prs = [
        _pr_integrable(gh, brut, base, reglage["branches"])
        for brut in gh.liste("pulls", state="open", base=base)
    ]
    rapport = integration.decider(prs, reglage["controles"], reglage["branches"])
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


def _palier(args: argparse.Namespace) -> int:
    racine = Path(args.projet)
    branchement = registre.branchement(racine)
    feuille = registre.feuille(racine)
    for etape in palier.etapes(feuille.fiches):
        etat = "finie" if etape.finie else f"en cours : {', '.join(etape.en_cours)}"
        couverture = (
            f"couverts : {', '.join(etape.couverts) or palier.VIDE}"
            f" · à couvrir : {', '.join(etape.a_couvrir) or palier.VIDE}"
        )
        print(f"couche {etape.couche}  {etat}  ({couverture})", file=sys.stderr)

    etape = palier.due(feuille.fiches)
    if etape is None:
        print("RIEN")
        print("aucune couche finie n'attend son palier", file=sys.stderr)
        return 0

    reserves = demandes.reservations(github.Github(args.depot), feuille.fiches) if args.depot else ()
    numero = palier.numero_libre(feuille.fiches, reserves)
    souche = palier.slug(etape, numero)
    texte_fiche = palier.fiche(etape, numero, branchement["briefs"])
    print(f"palier {numero} {souche} couche={etape.couche}")
    print(
        f"→ couche {etape.couche} finie ; lots à couvrir : {', '.join(etape.a_couvrir)}",
        file=sys.stderr,
    )
    if not args.ecrire:
        print("sans --ecrire : le registre n'est pas touché.", file=sys.stderr)
        return 0
    chemin = feuille.chemin
    module = registre.atelier()
    chemin.write_text(
        palier.inserer(chemin.read_text(encoding="utf-8"), texte_fiche, module.REPERE_DEBUT),
        encoding="utf-8",
    )
    print(f"fiche {numero} écrite en tête de {chemin}", file=sys.stderr)
    return 0


def _examens(gh, base, reglage):
    """Chaque proposition ouverte, et la décision de l'intégration sur elle.

    La décision, pas une paraphrase : `examiner` est la fonction qui
    fusionne, appelée telle quelle. C'est ce qui garantit que la page et
    la machine ne peuvent pas diverger.
    """
    examens = []
    for brut in gh.liste("pulls", state="open", base=base):
        pr = _pr_integrable(gh, brut, base, reglage["branches"])
        examens.append((pr, integration.examiner(pr, reglage["controles"], reglage["branches"])))
    return examens


def _essayer(refus: list, quoi: str, faire, defaut):
    """Une lecture qui a le droit d'échouer, à condition de le dire.

    Une page amputée en silence laisse croire que sa vue est complète.
    Chaque renoncement s'écrit dans `refus`, et la page les montre.
    """
    try:
        return faire()
    except (github.GithubErreur, ValueError) as exc:
        refus.append(f"{quoi} : {github.borner(str(exc))}")
        return defaut


def _proposition(gh, brut, detaillee: bool) -> histoire.Proposition:
    """Une proposition fermée, lue au niveau de détail qu'on lui accorde.

    Le détail coûte trois appels par proposition — les commits, les
    revues, les contrôles. On ne le paie que pour ce que le journal
    montre, et pour les propositions de lot, dont la date d'approbation
    date une étape de la traversée.
    """
    numero = brut["number"]
    branche = brut["head"]["ref"]
    fusionnee = mesure.instant(brut.get("merged_at"))
    relecteurs: tuple[str, ...] = ()
    approuvee = None
    auteurs: tuple[str, ...] = ()
    controles: tuple[tuple[str, str], ...] = ()
    mot_de_la_fin = ""
    if detaillee or branche.startswith(histoire.CODE):
        # Un seul appel : les revues brutes portent la date que le module
        # de relecture ne garde pas, et les redemander serait payer deux
        # fois la même page pour deux lectures qui peuvent différer.
        brutes = github.revues(gh, numero)
        approbations = [
            (revue, brute)
            for revue, brute in zip(relecture.revues_depuis_github(brutes), brutes)
            if revue.etat == relecture.APPROUVE and revue.auteur
        ]
        relecteurs = tuple(dict.fromkeys(revue.auteur for revue, _ in approbations))
        connues = [
            date for date in (mesure.instant(b.get("submitted_at")) for _, b in approbations)
            if date is not None
        ]
        approuvee = min(connues) if connues else None
    if detaillee:
        auteurs = tuple(github.auteurs_du_code(gh, numero))
        # La conclusion telle que GitHub la rend, pas la lecture sévère de
        # l'intégration : le journal rapporte, il ne juge pas une fusion
        # qui a déjà eu lieu.
        controles = tuple(
            (nom, histoire.conclusion(statut, mot))
            for nom, statut, mot in github.controles(gh, brut["head"]["sha"])
        )
        if fusionnee is None:
            derniers = github.commentaires(gh, numero)
            mot_de_la_fin = github.borner(derniers[-1].get("body", "")) if derniers else ""
    return histoire.Proposition(
        numero=numero,
        titre=brut.get("title", ""),
        branche=branche,
        auteurs=auteurs,
        relecteurs=relecteurs,
        ouverte=mesure.instant(brut.get("created_at")),
        fermee=mesure.instant(brut.get("closed_at")),
        fusionnee=fusionnee,
        approuvee=approuvee,
        controles=controles,
        mot_de_la_fin=mot_de_la_fin,
        lien=brut.get("html_url", ""),
    )


def _reveils(bruts) -> tuple:
    """Les exécutions de l'intégration, ramenées à ce que la page en montre."""
    lus = []
    for brut in bruts:
        moment = mesure.instant(brut.get("run_started_at") or brut.get("created_at"))
        if moment is None:
            continue
        lus.append(sante.Reveil(moment, brut.get("conclusion") or "en cours",
                                brut.get("html_url", "")))
    return tuple(lus)


def _rouges(bruts) -> tuple:
    """La dernière exécution rouge de chaque travail, une par travail."""
    par_travail: dict[str, sante.Rouge] = {}
    for brut in bruts:
        nom = brut.get("name") or brut.get("path", "")
        moment = mesure.instant(brut.get("run_started_at") or brut.get("created_at"))
        if not nom or moment is None:
            continue
        connue = par_travail.get(nom)
        if connue is None or moment > connue.moment:
            par_travail[nom] = sante.Rouge(nom, moment, brut.get("html_url", ""))
    return tuple(sorted(par_travail.values(), key=lambda r: r.moment, reverse=True))


def _etat_de_la_page(gh, feuille, examens, base, reglage, page, maintenant, depot):
    """Tout ce que la page montre en plus du registre, lu une fois."""
    refus: list[str] = []
    fermees_brutes = _essayer(
        refus, "les propositions fermées",
        lambda: github.propositions_fermees(gh, base, page["historique"]), [],
    )
    fermees_brutes.sort(key=lambda b: b.get("closed_at") or "", reverse=True)
    du_journal = {b["number"] for b in fermees_brutes[: page["journal"]]}
    propositions = tuple(
        _proposition(gh, brut, brut["number"] in du_journal) for brut in fermees_brutes
    )
    journal = tuple(p for p in propositions if p.numero in du_journal)

    fusions = [p.fusionnee for p in propositions if p.fusionnee is not None]
    derniere_fusion = max(fusions) if fusions else None
    reveils = _reveils(_essayer(
        refus, "l'historique de l'intégration",
        lambda: github.executions(gh, actions.TRAVAIL_INTEGRATION, page["executions"]), [],
    ))
    protection = _essayer(
        refus, "la protection de la branche de base",
        lambda: github.protection(gh, base), mesure.Lecture.inconnue("lecture impossible"),
    )
    etat_sante = _essayer(refus, "la santé de la chaîne", lambda: sante.Sante(
        tours_sans_fusion=sante.tours_sans_fusion(
            [r.moment for r in reveils], derniere_fusion),
        seuil=page["tours_sans_fusion"],
        derniere_fusion=derniere_fusion,
        dernier_reveil=sante.dernier_reveil(reveils),
        requis=reglage["controles"],
        obligatoires=sante.controles_obligatoires(protection),
        admins_soumis=sante.admins_soumis(protection),
        pages=sante.publication(_essayer(
            refus, "l'état de la publication",
            lambda: github.pages(gh), mesure.Lecture.inconnue("lecture impossible"))),
        rouges=_rouges(_essayer(
            refus, "les exécutions rouges", lambda: github.executions_rouges(gh), [])),
    ), None)

    velocite = _essayer(
        refus, "la vélocité",
        lambda: histoire.velocite(propositions, maintenant, page["semaines"]), (),
    )
    chemins = histoire.parcours(propositions)
    branches = _essayer(refus, "les branches distantes", lambda: github.branches(gh), [])
    ouvertes = {pr.branche for pr, _ in examens}
    return tableau.Etat(
        maintenant=maintenant,
        sante=etat_sante,
        alertes=attention.alertes(
            examens=examens,
            fiches=feuille.fiches,
            controles_base=_essayer(
                refus, f"les contrôles de {base}",
                lambda: github.controles(gh, base), []),
            requis=reglage["controles"],
            prefixes=reglage["branches"],
            base=base,
            brouillon_jours=page["brouillon_jours"],
            maintenant=maintenant,
            depot=depot,
        ),
        journal=journal,
        velocite=velocite,
        traversee=histoire.traversee(chemins),
        ages={f.numero: histoire.age(propositions, f, maintenant) for f in feuille.fiches},
        deductions=histoire.travaux_commences(branches, ouvertes),
        actions=actions.actions(depot),
        refus=tuple(refus),
    )


def _tableau(args: argparse.Namespace) -> int:
    racine = Path(args.projet)
    reglage = registre.integration(racine)
    page = registre.tableau(racine)
    base = args.base or registre.branchement(racine)["base"]
    feuille = registre.feuille(racine)
    gh = github.Github(args.depot, args.jeton)
    maintenant = datetime.now(timezone.utc)

    examens = _examens(gh, base, reglage)
    lignes = [
        tableau.LignePR(pr.numero, pr.branche, decision.action, decision.raison,
                        pr.titre, pr.ouverte, pr.brouillon)
        for pr, decision in examens
    ]
    etat = _etat_de_la_page(gh, feuille, examens, base, reglage, page, maintenant, args.depot)
    rendu = tableau.rendre(
        feuille.fiches, lignes,
        maintenant.strftime("%d/%m/%Y à %Hh%M UTC"),
        args.depot, etat,
    )
    chemin = Path(args.sortie)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(rendu, encoding="utf-8")
    for ligne in etat.refus:
        print(f"non lu — {ligne}", file=sys.stderr)
    print(f"{chemin}  {len(feuille.fiches)} lot(s), {len(lignes)} proposition(s), "
          f"{len(etat.journal)} au journal")
    return 0


def _saisie(args: argparse.Namespace) -> int:
    racine = Path(args.projet)
    branchement = registre.branchement(racine)
    feuille = registre.feuille(racine)
    demande = saisie.lire(Path(args.corps).read_text(encoding="utf-8"))

    for dep in demande.depend_de:
        if feuille.fiche(dep) is None:
            print(f"FAIL  le lot {dep} n'a pas de fiche : on ne dépend pas d'un fantôme",
                  file=sys.stderr)
            return 1

    reserves = demandes.reservations(github.Github(args.depot), feuille.fiches) if args.depot else ()
    numero = palier.numero_libre(feuille.fiches, reserves)
    texte = saisie.fiche(demande, numero, branchement["briefs"])
    print(f"lot {numero} {saisie.souche(demande, numero)}")
    print(f"→ {demande.titre} · couche {demande.couche or saisie.VIDE} · "
          f"dépend de {', '.join(demande.depend_de) or saisie.VIDE}", file=sys.stderr)
    if not args.ecrire:
        print("sans --ecrire : le registre n'est pas touché.", file=sys.stderr)
        return 0
    chemin = feuille.chemin
    module = registre.atelier()
    chemin.write_text(
        palier.inserer(chemin.read_text(encoding="utf-8"), texte, module.REPERE_DEBUT),
        encoding="utf-8",
    )
    print(f"fiche {numero} écrite en tête de {chemin}", file=sys.stderr)
    return 0


def _controles(args: argparse.Namespace) -> int:
    """Faut-il redemander les contrôles de cette proposition, ou sont-ils là ?"""
    reglage = registre.integration(Path(args.projet))
    gh = github.Github(args.depot, args.jeton)
    brut = gh.get(f"pulls/{args.pr}")
    sha = brut["head"]["sha"]
    pr = integration.depuis_github(brut, brut, github.controles(gh, sha))
    geste = actions.redemander_controles(
        brut.get("state") == "open", bool(brut.get("draft")), pr, reglage["controles"]
    )
    print(f"redemander {args.pr} {brut['head']['ref']} {sha}" if geste.a_faire else "RIEN")
    print(geste.raison, file=sys.stderr)
    return 0


def _brouillon(args: argparse.Namespace) -> int:
    """Faut-il sortir cette proposition du brouillon, ou en est-elle sortie ?"""
    gh = github.Github(args.depot, args.jeton)
    brut = gh.get(f"pulls/{args.pr}")
    geste = actions.sortir_du_brouillon(brut.get("state") == "open", bool(brut.get("draft")))
    print(f"sortir {args.pr} {brut['head']['ref']}" if geste.a_faire else "RIEN")
    print(geste.raison, file=sys.stderr)
    return 0


def _etat(args: argparse.Namespace) -> int:
    """Changer l'état d'un lot dans sa fiche — la seule représentation qui compte.

    La transition n'est pas jugée ici : c'est `atelier feuille marquer`
    qui refuse ce que `atelier feuille valider` interdirait, avec le même
    code et le même message. Un second juge finirait par dire autre chose
    que le premier.
    """
    racine = Path(args.projet)
    feuille = registre.feuille(racine)
    fiche = feuille.fiche(args.lot)
    if fiche is None:
        print(f"FAIL  aucune fiche pour le lot {args.lot} au registre", file=sys.stderr)
        return 1
    if fiche.etat == args.etat:
        print("RIEN")
        print(f"le lot {fiche.numero} est déjà « {args.etat} » : déjà fait", file=sys.stderr)
        return 0
    module = registre.atelier()
    texte = feuille.chemin.read_text(encoding="utf-8")
    try:
        nouveau = module.marquer(texte, args.lot, args.etat, chemin=feuille.chemin)
    except ValueError as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    print(f"etat {fiche.numero} {args.etat} etat-{fiche.numero}-{args.etat}")
    print(f"→ lot {fiche.numero} : {fiche.etat} → {args.etat}", file=sys.stderr)
    if not args.ecrire:
        print("sans --ecrire : le registre n'est pas touché.", file=sys.stderr)
        return 0
    feuille.chemin.write_text(nouveau, encoding="utf-8")
    print(f"fiche {fiche.numero} réécrite dans {feuille.chemin}", file=sys.stderr)
    return 0


def _autoriser_lot(args):
    evenement = json.loads(Path(args.evenement).read_text(encoding="utf-8"))
    print("autorise=" + str(demandes.autorisee(evenement)).lower())
    return 0


def _demande(args):
    evenement = json.loads(Path(args.evenement).read_text(encoding="utf-8"))
    # Avant même de charger un jeton ou le registre : aucune écriture,
    # aucun appel distant pour un événement non autorisé.
    if not demandes.autorisee(evenement):
        print("RIEN")
        print("demande non autorisée ou événement déjà couvert", file=sys.stderr)
        return 0
    racine = Path(args.projet)
    feuille = registre.feuille(racine)
    plan = demandes.preparer(github.Github(args.depot), evenement, feuille.fiches,
                            registre.branchement(racine)["briefs"])
    if plan["action"] == "RIEN":
        print("RIEN")
        print(plan["raison"], file=sys.stderr)
        return 0
    if plan["fiche"]:
        feuille.chemin.write_text(palier.inserer(
            feuille.chemin.read_text(encoding="utf-8"), plan["fiche"],
            registre.atelier().REPERE_DEBUT), encoding="utf-8")
    print(" ".join(str(plan[k]).lower() for k in
                   ("action", "numero", "branche", "issue", "pr", "reservee", "reponse")))
    return 0


def construire() -> argparse.ArgumentParser:
    parseur = argparse.ArgumentParser(prog="outils", description=__doc__)
    sous = parseur.add_subparsers(dest="commande", required=True)

    p = sous.add_parser("relecture", help="la PR a-t-elle été relue par un tiers, sur sa révision ?")
    p.add_argument("--depot", required=True, help="proprietaire/nom")
    p.add_argument("--pr", type=int, required=True)
    p.add_argument("--revision", help="la révision jugée ; par défaut la tête de la PR")
    p.add_argument("--jeton")
    p.set_defaults(faire=_relecture)

    p = sous.add_parser("integration", help="quelle PR entre dans master, ou RIEN")
    p.add_argument("--depot", required=True, help="proprietaire/nom")
    p.add_argument("--projet", default=".")
    p.add_argument("--base", help="la branche d'arrivée ; par défaut celle du branchement")
    p.add_argument("--jeton")
    p.add_argument("--sortie", help="fichier de sortie Actions pour la révision jugée")
    p.set_defaults(faire=_integration)

    p = sous.add_parser("palier", help="une couche finie attend-elle son lot de stabilisation ?")
    p.add_argument("--projet", default=".")
    p.add_argument("--ecrire", action="store_true", help="poser la fiche dans le registre")
    p.add_argument("--depot", help="réservations distantes, obligatoire dans le workflow")
    p.set_defaults(faire=_palier)

    p = sous.add_parser("tableau", help="écrire la page « où en est le travail »")
    p.add_argument("--depot", required=True, help="proprietaire/nom")
    p.add_argument("--projet", default=".")
    p.add_argument("--base")
    p.add_argument("--sortie", default="site/index.html")
    p.add_argument("--jeton")
    p.set_defaults(faire=_tableau)

    p = sous.add_parser("saisie", help="une demande de lot devient une fiche au registre")
    p.add_argument("--projet", default=".")
    p.add_argument("--corps", required=True, help="le fichier qui porte la réponse au formulaire")
    p.add_argument("--ecrire", action="store_true", help="poser la fiche dans le registre")
    p.add_argument("--depot", help="réservations distantes")
    p.set_defaults(faire=_saisie)
    p = sous.add_parser("controles", help="les contrôles requis manquent-ils à cette proposition ?")
    p.add_argument("--depot", required=True, help="proprietaire/nom")
    p.add_argument("--projet", default=".")
    p.add_argument("--pr", type=int, required=True)
    p.add_argument("--jeton")
    p.set_defaults(faire=_controles)

    p = sous.add_parser("brouillon", help="cette proposition est-elle encore un brouillon ?")
    p.add_argument("--depot", required=True, help="proprietaire/nom")
    p.add_argument("--pr", type=int, required=True)
    p.add_argument("--jeton")
    p.set_defaults(faire=_brouillon)

    p = sous.add_parser("etat", help="changer l'état d'un lot dans sa fiche")
    p.add_argument("--projet", default=".")
    p.add_argument("--lot", required=True, help="le numéro du lot, 049")
    p.add_argument("--etat", required=True, help="l'état visé : abandonne, idee, …")
    p.add_argument("--ecrire", action="store_true", help="réécrire la fiche du registre")
    p.set_defaults(faire=_etat)

    p = sous.add_parser("autoriser-lot", help="vérifier la confiance avant le travail en écriture")
    p.add_argument("--evenement", required=True)
    p.set_defaults(faire=_autoriser_lot)

    p = sous.add_parser("demande", help="préparer ou reprendre une demande autorisée")
    p.add_argument("--evenement", required=True)
    p.add_argument("--depot", required=True)
    p.add_argument("--projet", default=".")
    p.set_defaults(faire=_demande)
    return parseur


def main(argv=None) -> int:
    args = construire().parse_args(argv)
    try:
        return args.faire(args)
    except (github.GithubErreur, registre.AtelierAbsent, registre.BranchementIncomplet,
            saisie.DemandeIllisible) as exc:
        # Bornée comme le verdict : ce refus-ci peut finir dans la même
        # description d'état, et une description trop longue n'est pas
        # posée du tout.
        print(f"FAIL  {github.borner(str(exc), github.BORNE_DESCRIPTION - 6)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
