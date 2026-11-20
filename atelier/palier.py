"""Le samedi et le vendredi : le palier se décide et se montre.

Chaque palier a son issue, étiquetée `palier` et épinglée : « Palier 2 — La
paix et les alliés ». C'est là que tout se dit.

- **Le vendredi soir**, le CTO y pose la note de démo : quoi essayer, ce qui
  marche, ce qui manque, ce qu'il a décidé seul, ce que la semaine a coûté.
  Le PC fige un build du palier.
- **Le samedi**, le propriétaire joue et écrit sur l'issue ce qu'il veut. Le
  CTO en tire le palier suivant et le propose sur la même issue. Le
  propriétaire répond « oui », et les lots sont ouverts ; ou il corrige, et
  le CTO repropose.

- **En semaine**, un palier dont tous les lots sont fermés avant sa démo
  laisse la chaîne sans travail : le CTO propose sa suite sur la même issue,
  des lots de plus dans le même palier, que le « oui » du propriétaire ouvre.

Rien n'est gardé ailleurs : la proposition vit dans la marque de son
commentaire, et le « oui » est un commentaire.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import re
import time

from . import agents as agents_mod
from . import consignes, journal, lots
from .lots import Lot, marque
from .projet import CTO

PROPOSITION, DEMO = "proposition", "demo"
# La suite d'un palier, une fois ses lots ouverts : sa proposition est close.
SUITE_OUVERTE = "suite-ouverte"
# Ce qui vaut accord : un mot, seul ou en tête d'un commentaire court.
_OUI = re.compile(r"^\W*(oui|ok|go|d'accord|valid[ée]e?s?|c'est bon|lance|vas-y)\b", re.I)
ACCORD_MAX = 80
# Combien de fois le CTO est rappelé seul, le samedi, quand il ne rend rien.
ESSAIS_DU_SAMEDI = 2
# Le vendredi, la note attend le build figé : au plus tant de secondes, en le
# regardant à ce pas. Le tour du vendredi (`crons/tour.sh`) laisse ce temps,
# plus le délai du CTO.
ATTENTE_DU_BUILD, PAS_DU_BUILD = 3000, 60
dormir = time.sleep


def issue_du_palier(gh, ouvertes: list[Lot]) -> Lot | None:
    """L'issue du palier en cours : la plus récente qui porte l'étiquette `palier`."""
    siennes = [l for l in ouvertes if lots.ETIQUETTE_PALIER in l.etiquettes]
    return max(siennes, key=lambda l: l.numero) if siennes else None


def est_un_accord(texte: str) -> bool:
    texte = (texte or "").strip()
    return len(texte) <= ACCORD_MAX and bool(_OUI.match(texte))


def _lots_du_palier(numero: int | None, ouvertes: list[Lot], fermes: list[Lot]) -> list[tuple[Lot, bool]]:
    return [(l, ouvert) for liste, ouvert in ((ouvertes, True), (fermes, False)) for l in liste
            if l.est_un_lot and numero is not None and l.palier == numero]


def etat_du_palier(pilote, numero: int | None, ouvertes: list[Lot], fermes: list[Lot]) -> tuple[str, list[str]]:
    """Où en est chaque lot du palier, et ce que le CTO y a décidé seul."""
    lignes, a_revoir = [], []
    for lot, ouvert in sorted(_lots_du_palier(numero, ouvertes, fermes), key=lambda x: x[0].numero):
        commentaires = pilote.gh.issue(lot.numero).get("comments") or []
        a_revoir += journal.a_revoir_samedi(lot.numero, lot.titre, commentaires)
        if not ouvert:
            etat = "livré" if lot.etat == "livre" else "fermé sans être livré"
        elif lot.etat == "bloque":
            trouve = lots.dernier_blocage(commentaires)
            etat = "arrêté : " + ((trouve[1].get("raison") if trouve else "") or "sans raison écrite")
        elif lot.etat == "en-cours":
            resume = pilote.gh.pr_de_branche(lot.branche(pilote.projet.prefixe_branche))
            pr = pilote.gh.pr(resume["number"]) if resume else None
            etat = "en cours, " + (journal.ou_en_est(lots.marques(pr.get("comments") or [])) if pr
                                   else "son plan s'écrit")
        else:
            etat = "pas commencé"
        lignes += [f"- #{lot.numero} « {lot.titre} » ({lot.piste(pilote.projet.pistes) or '—'}) : {etat}",
                   f"  Ce que je joue de plus : {journal.section(lot.corps, 'Ce que je joue de plus') or '(non dit)'}",
                   f"  Ce que je vois samedi : {journal.section(lot.corps, 'Ce que je vois samedi') or '(non dit)'}"]
    return "\n".join(lignes), a_revoir


def proposition_en_clair(sortie: dict, numero: int, *, suite: bool = False) -> str:
    """La proposition du CTO, lisible sur un téléphone : le palier `numero`,
    ou sa suite."""
    entete = f"## Palier {numero}, la suite" if suite else f"## Palier {numero}"
    lignes = [f"{entete} — {sortie.get('titre', '')}", "", (sortie.get("but") or "").strip(), ""]
    for rang, f in enumerate(sortie.get("fiches") or [], start=1):
        qui = "le développeur seul" if f.get("meneur") == "developpeur" else "le chef de lot"
        attend = ", ".join(str(k) for k in f.get("apres") or [])
        lignes += [f"### {rang}. {f.get('titre', '')}",
                   f"*{f.get('piste', '')} · {f.get('machine', 'vps')} · mené par {qui}"
                   + (f" · après {attend}" if attend else "") + "*", "",
                   f"**Ce que je joue de plus** : {f.get('joueur', '')}", "",
                   f"**Ce que je vois samedi** : {f.get('samedi', '')}", "",
                   f"**La règle du monde** : {f.get('regle', '')}", "",
                   "**Les preuves** :"] + [f"- {p}" for p in f.get("preuves") or []] + [""]
    if (sortie.get("note") or "").strip():
        lignes += ["### Ce que j'ai fait de ta note", sortie["note"].strip(), ""]
    return "\n".join(lignes)


def _fil(commentaires: list[dict], proprietaire: str) -> tuple[dict | None, int, list[int]]:
    """Où en est l'issue du palier : la proposition du CTO qui attend une
    réponse (None s'il n'y en a pas), le rang de la note de démo (-1 sans
    démo), et les rangs de ce que le propriétaire a écrit depuis. Une suite
    déjà ouverte, ou proposée avant la démo, n'attend plus rien."""
    rang_proposition, proposition, rang_demo, rang_ouverte = -1, None, -1, -1
    for i, c in enumerate(commentaires):
        for m in lots.marques([c]):
            if m.get("role") == CTO and m.get("etat") == PROPOSITION:
                rang_proposition, proposition = i, m
            elif m.get("etat") == DEMO:
                rang_demo = i
                if proposition is not None and proposition.get("suite"):
                    rang_proposition, proposition = -1, None
            elif m.get("etat") == SUITE_OUVERTE:
                rang_ouverte, rang_proposition, proposition = i, -1, None
    depart = max(rang_demo, rang_proposition, rang_ouverte)
    siens = [i for i, c in enumerate(commentaires) if i > depart and lots.ecrit_par_le_proprietaire(c, proprietaire)]
    return proposition, rang_demo, siens


def _rates(commentaires: list[dict], depuis: int, **champs) -> int:
    """Combien de fois le CTO n'a rien rendu depuis le rang `depuis`."""
    return sum(1 for c in commentaires[depuis + 1:] for m in lots.marques([c])
               if m.get("role") == CTO and m.get("etat") in (lots.ECHEC, lots.COUPE)
               and all(m.get(k) == v for k, v in champs.items()))


def samedi(pilote, palier, ouvertes: list[Lot], fermes: list[Lot]) -> bool:
    """Le palier suivant, tiré de ce que le propriétaire a écrit sur l'issue
    du palier ; ou, s'il répond à une suite proposée, cette suite ouverte ou
    refaite. Vrai quand le CTO a été appelé."""
    issue = issue_du_palier(pilote.gh, ouvertes)
    if issue is None:
        return False
    commentaires = pilote.gh.issue(issue.numero).get("comments") or []
    proprietaire = pilote.projet.proprietaire
    proposition, rang_demo, siens = _fil(commentaires, proprietaire)
    if not siens:
        return False
    ecrits = [(commentaires[i].get("body") or "").strip() for i in siens]
    # Un CTO qui n'a rien rendu deux fois depuis la dernière parole du
    # propriétaire n'est pas rappelé : il le sera quand le propriétaire récrira.
    rates = _rates(commentaires, siens[-1])
    if rates >= ESSAIS_DU_SAMEDI:
        return False
    numero = lots.numero_de_palier(issue.titre) or (palier.numero if palier else 0)
    en_suite = proposition is not None and bool(proposition.get("suite"))
    if proposition is not None and est_un_accord(ecrits[-1]):
        if en_suite:
            ouvrir_la_suite(pilote, issue, palier, proposition)
        else:
            ouvrir_le_palier(pilote, issue, palier, numero + 1, proposition.get("sortie") or {})
        return False
    # Tout ce que le propriétaire a écrit depuis la démo fait sa note.
    note = "\n\n".join((c.get("body") or "").strip() for c in commentaires[rang_demo + 1:]
                        if lots.ecrit_par_le_proprietaire(c, proprietaire) and not est_un_accord(c.get("body") or ""))
    etat, a_revoir = etat_du_palier(pilote, numero, ouvertes, fermes)
    avant = (proposition_en_clair(proposition.get("sortie") or {}, numero if en_suite else numero + 1, suite=en_suite)
             if proposition else "")
    commun = dict(numero=numero, etat_du_palier=etat, a_revoir="\n".join(f"- {l}" for l in a_revoir),
                  proposition=avant, remarques="\n\n".join(ecrits) if proposition else "")
    consigne = (consignes.suite_du_palier(pilote.projet, **commun) if en_suite
                else consignes.palier(pilote.projet, note_du_proprietaire=note, **commun))
    return _proposer(pilote, issue, numero, consigne, encore=rates + 1 < ESSAIS_DU_SAMEDI,
                     suite=proposition.get("lots") if en_suite else None)


def suite(pilote, palier, ouvertes: list[Lot], fermes: list[Lot]) -> bool:
    """Le palier n'a plus aucun lot ouvert et sa démo n'est pas posée : le
    CTO propose sa suite, une fois par vidage, sans attendre que le
    propriétaire écrive. Vrai quand le CTO a été appelé."""
    issue = issue_du_palier(pilote.gh, ouvertes)
    if issue is None:
        return False
    numero = lots.numero_de_palier(issue.titre) or (palier.numero if palier else 0)
    siens = _lots_du_palier(numero, ouvertes, fermes)
    if not siens or any(ouvert for _, ouvert in siens):
        return False
    commentaires = pilote.gh.issue(issue.numero).get("comments") or []
    proposition, rang_demo, ecrits = _fil(commentaires, pilote.projet.proprietaire)
    # Une démo posée, une proposition qui attend, ou une parole du
    # propriétaire sans réponse : c'est le samedi qui a la main.
    if rang_demo >= 0 or proposition is not None or ecrits:
        return False
    # Le nombre de lots du palier date la suite : elle se propose une fois
    # pour ce vidage, et de nouveau si ses propres lots se ferment à leur tour.
    compte = len(siens)
    pour_ce_vidage = [m for m in lots.marques(commentaires) if m.get("suite") and m.get("lots") == compte]
    if any(m.get("etat") in (PROPOSITION, SUITE_OUVERTE) for m in pour_ce_vidage):
        return False
    rates = _rates(commentaires, -1, suite=True, lots=compte)
    if rates >= ESSAIS_DU_SAMEDI:
        return False
    etat, a_revoir = etat_du_palier(pilote, numero, ouvertes, fermes)
    consigne = consignes.suite_du_palier(pilote.projet, numero=numero, etat_du_palier=etat,
                                         a_revoir="\n".join(f"- {l}" for l in a_revoir))
    return _proposer(pilote, issue, numero, consigne, encore=rates + 1 < ESSAIS_DU_SAMEDI, suite=compte)


def _proposer(pilote, issue: Lot, numero: int, consigne: str, *, encore: bool, suite: int | None) -> bool:
    """Le CTO est appelé, et ce qu'il rend est posé sur l'issue du palier :
    le palier `numero + 1`, ou, quand `suite` donne le nombre de lots du
    palier `numero`, sa suite. Vrai quand il a été appelé."""
    quoi = "la suite du palier" if suite is not None else "le palier suivant"
    de_suite = {"suite": True, "lots": suite} if suite is not None else {}
    appel = agents_mod.Appel(role=CTO, lecture_seule=True, consigne=consigne,
                             schema=consignes.schema_palier(pilote.projet), jours_max=pilote.projet.jours_max)
    res = pilote._invoquer(CTO, appel, pilote.projet.racine, lot=issue.numero)
    if res.attente:
        pilote.noter(issue.numero, "attente", f"CTO : {res.raison}")
        return True
    sortie = res.sortie if res.reussi else None
    fiches = [f for f in (sortie or {}).get("fiches") or [] if isinstance(f, dict) and f.get("titre")]
    if sortie and not fiches and suite is not None:
        # Rien ne mérite un lot avant la démo : c'est une réponse, pas un échec.
        pourquoi = (sortie.get("note") or "").strip() or "sans raison écrite"
        pilote.gh.commenter_issue(issue.numero, f"🤖 **CTO** ({res.agent}) n'ajoute aucun lot au palier {numero} avant "
                                                f"sa démo.\n\n{pourquoi}\n\n"
                                  + marque(**pilote._champs(CTO, res, etat=SUITE_OUVERTE, **de_suite)))
        pilote.noter(issue.numero, "suite sans lot", f"palier {numero}", str(res.agent))
        return True
    if not sortie or not fiches:
        raison = "coupé par son délai" if res.coupe else f"code {res.code}" if not res.reussi else "sans fiche"
        pilote.gh.commenter_issue(issue.numero, f"🤖 **CTO** ({res.agent or '—'}) n'a pas rendu {quoi} "
                                                f"({raison}). "
                                  + ("Le pilote le rappelle au tour suivant." if encore else
                                     "Il ne sera pas rappelé seul : écris de nouveau ici pour le relancer.") + "\n\n"
                                  + marque(**pilote._champs(CTO, res, etat=lots.COUPE if res.coupe else lots.ECHEC,
                                                            **de_suite)))
        pilote.noter(issue.numero, "CTO en échec", f"{quoi} : {raison}", str(res.agent or ""))
        return True
    sortie["fiches"] = fiches
    if suite is not None:
        pilote.gh.commenter_issue(
            issue.numero, f"🤖 **CTO** ({res.agent}) propose la suite du palier : tous ses lots sont fermés, et la "
                          f"chaîne n'a plus rien à faire avant la démo.\n\n"
                          f"{proposition_en_clair(sortie, numero, suite=True)}\n\n"
                          "**Réponds « oui »** pour ouvrir ces lots dans le palier en cours, ou dis ce qu'il faut "
                          "changer.\n\n" + marque(**pilote._champs(CTO, res, etat=PROPOSITION, sortie=sortie, **de_suite)))
        pilote.noter(issue.numero, "suite proposée", f"palier {numero}, {len(fiches)} lot(s)", str(res.agent))
        return True
    manquantes = [p for p in pilote.projet.pistes if p not in {f.get("piste") for f in fiches}]
    alerte = (f"\n\n⚠️ Aucun lot sur : {', '.join(manquantes)}. Un palier avance sur les trois pistes."
              if manquantes else "")
    pilote.gh.commenter_issue(issue.numero, f"🤖 **CTO** ({res.agent}) propose le palier suivant.\n\n"
                                            f"{proposition_en_clair(sortie, numero + 1)}{alerte}\n\n"
                                            "**Réponds « oui »** pour ouvrir ces lots et lancer la semaine, ou dis ce "
                                            "qu'il faut changer.\n\n"
                              + marque(**pilote._champs(CTO, res, etat=PROPOSITION, sortie=sortie)))
    pilote.noter(issue.numero, "palier proposé", f"palier {numero + 1}, {len(fiches)} lot(s)", str(res.agent))
    return True


def ouvrir_la_suite(pilote, issue: Lot, palier, proposition: dict) -> None:
    """Le propriétaire a dit oui à la suite : ses lots s'ouvrent dans le
    jalon du palier en cours, qui reste ouvert jusqu'à sa démo."""
    jalon = palier.titre if palier is not None else issue.titre
    crees = pilote.ouvrir_les_fiches((proposition.get("sortie") or {}).get("fiches") or [], jalon)
    pilote.gh.commenter_issue(issue.numero, "🤖 **pilote** : la suite du palier est ouverte : "
                                            + ", ".join(f"#{n}" for n in crees) + ".\n\n"
                              + marque(role="pilote", etat=SUITE_OUVERTE, suite=True, lots=proposition.get("lots")))
    pilote.noter(issue.numero, "suite ouverte", f"{jalon} : " + ", ".join(f"#{n}" for n in crees))


def ouvrir_le_palier(pilote, issue: Lot, palier, numero: int, sortie: dict) -> None:
    """Le propriétaire a dit oui : le jalon du palier, son issue et ses lots
    sont ouverts ; le palier d'avant se ferme, et la chaîne part."""
    titre = f"Palier {numero} — {(sortie.get('titre') or '').strip() or 'sans titre'}"
    pilote.gh.creer_jalon(titre)
    crees = pilote.ouvrir_les_fiches(sortie.get("fiches") or [], titre)
    corps = (f"{(sortie.get('but') or '').strip()}\n\nSes lots : " + ", ".join(f"#{n}" for n in crees)
             + "\n\nLe vendredi soir, la note de démo arrive ici. Le samedi, écris ici ce que tu veux réorienter, "
               "puis « oui » à la proposition du CTO.\n")
    nouvelle = pilote.gh.creer_issue(titre, corps, [lots.ETIQUETTE_PALIER], titre)
    try:
        pilote.gh.desepingler(issue.numero)
        pilote.gh.epingler(nouvelle)
    except Exception:  # noqa: BLE001 — une épingle manquée ne retient pas le palier
        pass
    atteint = "atteint" if sortie.get("palier_atteint") else "clos sans être dit atteint"
    pilote.gh.fermer_issue(issue.numero, f"Palier {atteint}. Le suivant : #{nouvelle}.")
    if palier is not None:
        pilote.gh.fermer_jalon(palier.id)
    pilote.noter(nouvelle, "palier ouvert", f"{titre} : " + ", ".join(f"#{n}" for n in crees))


def attendre_le_build(pilote, depuis: datetime) -> tuple[str, str]:
    """Le build figé lancé à l'instant `depuis` : on le regarde jusqu'à ce
    qu'il finisse, `ATTENTE_DU_BUILD` secondes au plus. Rend son état
    (`construit`, `rate` ou `inacheve`) et l'adresse de son run."""
    # Deux minutes de marge : l'horloge du VPS n'est pas celle de GitHub.
    borne = f"{depuis - timedelta(minutes=2):%Y-%m-%dT%H:%M:%SZ}"
    run = None
    for regard in range(ATTENTE_DU_BUILD // PAS_DU_BUILD + 1):
        if regard:
            dormir(PAS_DU_BUILD)
        try:
            run = pilote.gh.run_lance("build-nuit.yml", borne)
        except Exception:  # noqa: BLE001 — GitHub qui ne répond pas une fois ne coupe pas l'attente
            continue
        if run is not None and run.get("status") == "completed":
            return ("construit" if run.get("conclusion") == "success" else "rate"), run.get("url") or ""
    return "inacheve", (run or {}).get("url") or ""


def vendredi(pilote, *, publication: bool = True) -> str:
    """La démo du vendredi soir : le PC fige un build du palier, le pilote
    attend qu'il soit construit, et le CTO écrit la note d'une page sur
    l'issue du palier en sachant s'il l'est. Sans CTO, le pilote pose les
    faits tels quels : une démo ne se tait jamais."""
    ouvertes = [Lot.de(i) for i in pilote.gh.issues("open")]
    fermes = [Lot.de(i) for i in pilote.gh.issues("closed")]
    issue = issue_du_palier(pilote.gh, ouvertes)
    if issue is None:
        return "RIEN — aucune issue de palier ouverte"
    numero = lots.numero_de_palier(issue.titre) or 0
    jour = f"{pilote.maintenant():%Y-%m-%d}"
    commentaires = pilote.gh.issue(issue.numero).get("comments") or []
    if any(m.get("etat") == DEMO and m.get("jour") == jour for m in lots.marques(commentaires)):
        return f"RIEN — la note de démo du {jour} est déjà posée"
    etat, a_revoir = etat_du_palier(pilote, numero, ouvertes, fermes)
    siens = _lots_du_palier(numero, ouvertes, fermes)
    hors_lot = journal.issues_hors_lot(pilote.gh)
    couts = journal.table_des_couts(
        journal.mesures_des_lots(pilote.gh, pilote.projet, sorted({*(l.numero for l, _ in siens), *hors_lot})),
        {l.numero: l.titre for l, _ in siens} | hors_lot)
    build = f"palier-{numero}"
    # Ce que la note doit savoir du build, et ce qu'elle en dit en tête : rien
    # quand il est construit.
    if not pilote.gh.pc_actif():
        construit, en_tete = "le PC est en pause : il n'a pas été construit", " (le PC est en pause : il n'a pas été construit)"
    elif not publication:
        construit, en_tete = "non lancé : essai sans publication", ""
    else:
        lance = pilote.maintenant()
        pilote.gh.lancer_workflow("build-nuit.yml", pilote.projet.branche_base, {"nom": build})
        etat_du_build, adresse = attendre_le_build(pilote, lance)
        pilote.noter(issue.numero, "build figé", f"{build} : {etat_du_build}")
        ou = f" ({adresse})" if adresse else ""
        construit, en_tete = {
            "construit": (f"construit ce soir{ou}", ""),
            "rate": (f"⚠️ sa construction a échoué{ou} : le dossier porte un build plus ancien, ou rien",
                     f" (⚠️ sa construction a échoué{' : ' + adresse if adresse else ''})"),
            "inacheve": (f"⚠️ pas encore construit après {ATTENTE_DU_BUILD // 60} minutes d'attente{ou}",
                         " (⚠️ pas encore construit quand cette note a été écrite)"),
        }[etat_du_build]
    faits = (f"LE BUILD FIGÉ : D:\\Forge\\builds\\{build} (lancer {build}\\Jouer.cmd) — {construit}\n\n"
             f"LES LOTS DU PALIER :\n"
             f"{etat or '(aucun)'}\n\nÀ REVOIR SAMEDI :\n" + ("\n".join(f"- {l}" for l in a_revoir) or "(rien)")
             + f"\n\nCE QUE LA SEMAINE A COÛTÉ :\n{couts}")
    titre = issue.titre.split("—", 1)[-1].strip()
    appel = agents_mod.Appel(role=CTO, lecture_seule=True, jours_max=pilote.projet.jours_max,
                             consigne=consignes.note_de_demo(pilote.projet, numero=numero, titre=titre, faits=faits))
    res = pilote._invoquer(CTO, appel, pilote.projet.racine, lot=issue.numero)
    if res.reussi and "## Quoi essayer" in res.texte:
        note, signature = res.texte.strip(), f"Écrit par le CTO ({res.agent})."
    else:
        note = f"Le CTO n'a pas rendu sa note ({res.raison or f'code {res.code}'}). Les faits :\n\n```\n{faits}\n```"
        signature = "Écrit par le pilote, à partir des faits."
    corps = (f"# La démo du palier {numero} — {titre}\n\nLe build figé : `D:\\Forge\\builds\\{build}\\Jouer.cmd`"
             f"{en_tete}\n\n{note}\n\n<sub>{signature}</sub>")
    if publication:
        pilote.gh.commenter_issue(issue.numero, f"{corps}\n\n"
                                  + marque(**pilote._champs(CTO, res, etat=DEMO, jour=jour)))
    pilote.noter(issue.numero, "note de démo", f"palier {numero}", str(res.agent or "pilote"))
    return corps
