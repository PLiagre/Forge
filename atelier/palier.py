"""L'étape se montre et se décide, sur son issue, sans attendre un jour de la semaine.

Chaque étape de `CAP.md` se mène comme un palier : elle a son issue,
étiquetée `palier` et épinglée (« Palier 2 — On s'y retrouve »), et son
jalon, qui porte ses lots. C'est sur l'issue que tout se dit.

- **Dès que l'étape n'a plus de lot ouvert**, le PC en fige un build, et le
  testeur le joue par l'écran seul, comme un joueur qui le découvre
  (`testeur.py`). Son rapport est posé sur l'issue, avec son verdict.
- **Le verdict rendu**, le CTO y pose la note de démo : quoi essayer, ce qui
  marche, ce qui manque, ce qu'il a décidé seul, ce que l'étape a coûté. Un
  testeur qui n'a pas pu jouer ne retient pas la note : elle le dit.
- **Aussitôt la note posée**, le CTO propose la suite : l'étape suivante de
  `CAP.md` si le testeur dit l'étape tenue, ce qui la corrige s'il la dit non
  tenue.
- **La suite s'ouvre** sur le verdict du testeur quand `atelier.toml` le
  règle ainsi (`[testeur] ouvre`), sinon sur le « oui » du propriétaire. Le
  propriétaire joue quand il veut : dès qu'il écrit sur l'issue, c'est sa
  parole qui décide, et le CTO repropose en en tenant compte.

Rien n'est gardé ailleurs : la proposition vit dans la marque de son
commentaire, le verdict dans celle du rapport, et le « oui » est un
commentaire.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
import re
import time

from . import agents as agents_mod
from . import consignes, journal, lots
from . import testeur as testeur_mod
from .lots import Lot, marque
from .projet import CTO, TESTEUR

PROPOSITION, DEMO = "proposition", "demo"
# Les marques du pilote sur l'issue d'une étape : dans son texte, comment
# elle a été ouverte ; en commentaire, l'appel au propriétaire.
OUVERT, APPEL = "ouvert", "appel"
WORKFLOW_DU_TESTEUR = "testeur-pc.yml"
# Le testeur a répondu qu'il attend le bureau du PC, ou n'a rien prouvé : il
# est renvoyé au bout de tant d'heures. Le passage attend lui-même le bureau
# trois quarts d'heure avant de répondre.
HEURES_ATTENTE_TESTEUR = 0.25
# Un envoi resté sans aucune réponse (le PC est éteint) est renvoyé.
HEURES_SILENCE_TESTEUR = 3
# Depuis son premier envoi : au-delà, la note de démo part sans son verdict.
HEURES_SANS_TESTEUR = 6
# Passages sans récit prouvé (coupé, sans photo) après lesquels on s'en passe.
ECHECS_DU_TESTEUR = 2
# Ce qui vaut accord : un mot, seul ou en tête d'un commentaire court.
_OUI = re.compile(r"^\W*(oui|ok|go|d'accord|valid[ée]e?s?|c'est bon|lance|vas-y)\b", re.I)
ACCORD_MAX = 80
# Combien de fois le CTO est rappelé seul quand il ne rend aucune proposition.
ESSAIS_DE_PROPOSITION = 2
# La note de démo attend le build figé : au plus tant de secondes, en le
# regardant à ce pas. Le tour de la démo (`crons/tour.sh`) laisse ce temps,
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
                   f"  Ce que je vois à la démo : {journal.section(lot.corps, 'Ce que je vois à la démo') or '(non dit)'}"]
    return "\n".join(lignes), a_revoir


def proposition_en_clair(sortie: dict, numero: int) -> str:
    """La proposition du CTO, lisible sur un téléphone : le palier `numero`."""
    lignes = [f"## Palier {numero} — {sortie.get('titre', '')}", "", (sortie.get("but") or "").strip(), ""]
    for rang, f in enumerate(sortie.get("fiches") or [], start=1):
        qui = "le développeur seul" if f.get("meneur") == "developpeur" else "le chef de lot"
        attend = ", ".join(str(k) for k in f.get("apres") or [])
        lignes += [f"### {rang}. {f.get('titre', '')}",
                   f"*{f.get('piste', '')} · {f.get('machine', 'vps')} · mené par {qui}"
                   + (f" · après {attend}" if attend else "") + "*", "",
                   f"**Ce que je joue de plus** : {f.get('joueur', '')}", "",
                   f"**Ce que je vois à la démo** : {f.get('samedi', '')}", "",
                   f"**La règle du monde** : {f.get('regle', '')}", "",
                   "**Les preuves** :"] + [f"- {p}" for p in f.get("preuves") or []] + [""]
    if (sortie.get("note") or "").strip():
        lignes += ["### Ce que j'ai fait de ta note", sortie["note"].strip(), ""]
    return "\n".join(lignes)


@dataclass
class Fil:
    """Où en est l'issue de l'étape. Les rangs sont ceux des commentaires ; -1 : absent."""

    # La dernière proposition du CTO, celle qui attend une réponse.
    proposition: dict | None = None
    rang_proposition: int = -1
    rang_demo: int = -1
    # Le dernier verdict du testeur, et son rapport tel qu'il est posé.
    verdict: dict | None = None
    rang_verdict: int = -1
    rapport: str = ""
    # Là où l'étape a commencé à se juger : le premier envoi du testeur, sinon
    # la note de démo. Le build figé est prêt dès ce moment.
    debut: int = -1
    # Ce que le propriétaire a écrit depuis ce début et la dernière proposition.
    siens: list[int] = field(default_factory=list)
    # A-t-il écrit quoi que ce soit depuis ce début ? Sa parole décide alors.
    a_parle: bool = False


def _fil(commentaires: list[dict], proprietaire: str) -> Fil:
    fil, rang_jeu = Fil(), -1
    for i, c in enumerate(commentaires):
        for m in lots.marques([c]):
            if m.get("role") == CTO and m.get("etat") == PROPOSITION:
                fil.rang_proposition, fil.proposition = i, m
            elif m.get("etat") == DEMO:
                fil.rang_demo = i
            elif m.get("role") == TESTEUR:
                rang_jeu = i if rang_jeu < 0 else rang_jeu
                if m.get("etat") == testeur_mod.JOUE and m.get("verdict") in testeur_mod.VERDICTS:
                    fil.verdict, fil.rang_verdict = m, i
                    # Son rapport, sans la planche de ses photos : celui qui le lit n'ouvre pas les images.
                    fil.rapport = lots.sans_marque(c.get("body") or "").split("<details><summary>Ses ", 1)[0].strip()
    fil.debut = min((r for r in (rang_jeu, fil.rang_demo) if r >= 0), default=-1)
    ecrits = [i for i, c in enumerate(commentaires) if lots.ecrit_par_le_proprietaire(c, proprietaire)]
    fil.siens = [i for i in ecrits if i > max(fil.debut, fil.rang_proposition)]
    fil.a_parle = fil.debut >= 0 and any(i > fil.debut for i in ecrits)
    return fil


def _verdict(fil: Fil) -> str:
    return (fil.verdict or {}).get("verdict") or ""


def refus_de_suite(corps: str) -> int:
    """Combien d'étapes de suite le testeur a dites non tenues avant celle-ci,
    d'après la marque que le pilote a laissée dans son texte en l'ouvrant."""
    ouvertures = [m for m in lots.marques([{"body": corps}]) if m.get("etat") == OUVERT]
    return int(ouvertures[-1].get("refus") or 0) if ouvertures else 0


def _rates(commentaires: list[dict], depuis: int) -> int:
    """Combien de fois le CTO n'a rien rendu depuis le rang `depuis`."""
    return sum(1 for c in commentaires[depuis + 1:] for m in lots.marques([c])
               if m.get("role") == CTO and m.get("etat") in (lots.ECHEC, lots.COUPE))


def reponse(pilote, palier, ouvertes: list[Lot], fermes: list[Lot]) -> bool:
    """Le propriétaire a écrit sur l'issue de l'étape : son « oui » ouvre la
    proposition qui attend ; toute autre parole fait proposer, ou reproposer,
    l'étape suivante au CTO. Vrai quand le CTO a été appelé."""
    issue = issue_du_palier(pilote.gh, ouvertes)
    if issue is None:
        return False
    commentaires = pilote.gh.issue(issue.numero).get("comments") or []
    proprietaire = pilote.projet.proprietaire
    fil = _fil(commentaires, proprietaire)
    proposition, siens = fil.proposition, fil.siens
    if not siens:
        return False
    ecrits = [(commentaires[i].get("body") or "").strip() for i in siens]
    # Un CTO qui n'a rien rendu deux fois depuis la dernière parole du
    # propriétaire n'est pas rappelé : il le sera quand le propriétaire récrira.
    rates = _rates(commentaires, siens[-1])
    if rates >= ESSAIS_DE_PROPOSITION:
        return False
    numero = lots.numero_de_palier(issue.titre) or (palier.numero if palier else 0)
    if proposition is not None and est_un_accord(ecrits[-1]):
        ouvrir_le_palier(pilote, issue, palier, numero + 1, proposition.get("sortie") or {}, verdict=_verdict(fil))
        return False
    # Tout ce que le propriétaire a écrit depuis que l'étape se juge fait sa note.
    note = "\n\n".join((c.get("body") or "").strip() for c in commentaires[fil.debut + 1:]
                        if lots.ecrit_par_le_proprietaire(c, proprietaire) and not est_un_accord(c.get("body") or ""))
    etat, a_revoir = etat_du_palier(pilote, numero, ouvertes, fermes)
    avant = proposition_en_clair(proposition.get("sortie") or {}, numero + 1) if proposition else ""
    consigne = consignes.palier(pilote.projet, numero=numero, note_du_proprietaire=note, etat_du_palier=etat,
                                a_revoir="\n".join(f"- {l}" for l in a_revoir), proposition=avant,
                                remarques="\n\n".join(ecrits) if proposition else "",
                                rapport_du_testeur=fil.rapport, verdict_du_testeur=_verdict(fil))
    return _proposer(pilote, issue, numero, consigne, encore=rates + 1 < ESSAIS_DE_PROPOSITION)


def accord_du_testeur(pilote, palier, ouvertes: list[Lot], fermes: list[Lot]) -> bool:
    """Le verdict du testeur ouvre la suite que le CTO a proposée en le
    connaissant, quand `[testeur] ouvre` le règle ainsi et que le propriétaire
    n'a rien écrit depuis que l'étape se juge : l'étape suivante si elle est
    tenue, le tour de correction sinon. Après `refus_max` « non tenue » de
    suite, la correction ne s'ouvre plus seule : le propriétaire est appelé,
    une fois. N'appelle aucun agent."""
    if not pilote.projet.testeur_ouvre:
        return False
    issue = issue_du_palier(pilote.gh, ouvertes)
    if issue is None:
        return False
    commentaires = pilote.gh.issue(issue.numero).get("comments") or []
    fil = _fil(commentaires, pilote.projet.proprietaire)
    if (fil.verdict is None or fil.proposition is None or fil.a_parle
            or not fil.rang_verdict < fil.rang_demo < fil.rang_proposition):
        return False
    verdict = _verdict(fil)
    refus = refus_de_suite(issue.corps) + 1 if verdict == testeur_mod.NON_TENUE else 0
    if refus >= pilote.projet.testeur_refus_max:
        if not any(m.get("etat") == APPEL for m in lots.marques(commentaires[fil.rang_proposition:])):
            pilote.gh.commenter_issue(
                issue.numero, f"@{pilote.projet.proprietaire} : le testeur a jugé {refus} étapes de suite « non tenue ». "
                              "La chaîne n'ouvre pas seule un tour de correction de plus : la correction proposée "
                              "ci-dessus attend ta réponse. **Réponds « oui »** pour l'ouvrir, ou dis ce qu'il faut "
                              "changer.\n\n" + marque(role="pilote", etat=APPEL, refus=refus))
            pilote.noter(issue.numero, "au propriétaire", f"{refus} « non tenue » de suite : la correction attend son oui")
        return False
    numero = lots.numero_de_palier(issue.titre) or (palier.numero if palier else 0)
    ouvrir_le_palier(pilote, issue, palier, numero + 1, fil.proposition.get("sortie") or {}, verdict=verdict,
                     par=TESTEUR, refus=refus)
    return False


def d_avance(pilote, palier, ouvertes: list[Lot], fermes: list[Lot]) -> bool:
    """La démo de l'étape est posée, aucune proposition n'attend et le
    propriétaire n'a encore rien écrit : le CTO propose la suite, d'avance.
    C'est l'étape suivante de `CAP.md`, avec les défauts que le testeur
    demande de corriger d'abord ; ou, s'il a jugé l'étape non tenue, ce qui la
    corrige. Vrai quand le CTO a été appelé."""
    issue = issue_du_palier(pilote.gh, ouvertes)
    if issue is None:
        return False
    commentaires = pilote.gh.issue(issue.numero).get("comments") or []
    fil = _fil(commentaires, pilote.projet.proprietaire)
    if fil.rang_demo < 0 or fil.proposition is not None or fil.siens:
        return False
    rates = _rates(commentaires, fil.rang_demo)
    if rates >= ESSAIS_DE_PROPOSITION:
        return False
    numero = lots.numero_de_palier(issue.titre) or (palier.numero if palier else 0)
    etat, a_revoir = etat_du_palier(pilote, numero, ouvertes, fermes)
    consigne = consignes.palier(pilote.projet, numero=numero, note_du_proprietaire="", etat_du_palier=etat,
                                a_revoir="\n".join(f"- {l}" for l in a_revoir), d_avance=True,
                                rapport_du_testeur=fil.rapport, verdict_du_testeur=_verdict(fil))
    return _proposer(pilote, issue, numero, consigne, encore=rates + 1 < ESSAIS_DE_PROPOSITION, d_avance=True,
                     verdict=_verdict(fil))


def _proposer(pilote, issue: Lot, numero: int, consigne: str, *, encore: bool, d_avance: bool = False,
              verdict: str = "") -> bool:
    """Le CTO est appelé, et ce qu'il rend est posé sur l'issue de l'étape :
    le palier `numero + 1`. `verdict` : celui du testeur, quand la suite se
    propose d'avance en le connaissant ; « non tenue » en fait une correction,
    jamais dite atteinte. Vrai quand le CTO a été appelé."""
    appel = agents_mod.Appel(role=CTO, lecture_seule=True, consigne=consigne,
                             schema=consignes.schema_palier(pilote.projet), jours_max=pilote.projet.jours_max)
    res = pilote._invoquer(CTO, appel, pilote.projet.racine, lot=issue.numero)
    if res.attente:
        pilote.noter(issue.numero, "attente", f"CTO : {res.raison}")
        return True
    sortie = res.sortie if res.reussi else None
    fiches = [f for f in (sortie or {}).get("fiches") or [] if isinstance(f, dict) and f.get("titre")]
    if not sortie or not fiches:
        raison = "coupé par son délai" if res.coupe else f"code {res.code}" if not res.reussi else "sans fiche"
        pilote.gh.commenter_issue(issue.numero, f"🤖 **CTO** ({res.agent or '—'}) n'a pas rendu le palier suivant "
                                                f"({raison}). "
                                  + ("Le pilote le rappelle au tour suivant." if encore else
                                     "Il ne sera pas rappelé seul : écris de nouveau ici pour le relancer.") + "\n\n"
                                  + marque(**pilote._champs(CTO, res, etat=lots.COUPE if res.coupe else lots.ECHEC)))
        pilote.noter(issue.numero, "CTO en échec", f"le palier suivant : {raison}", str(res.agent or ""))
        return True
    sortie["fiches"] = fiches
    corrige = d_avance and verdict == testeur_mod.NON_TENUE
    if corrige:
        sortie["palier_atteint"] = False
    au_oui = "« oui »** pour ouvrir ces lots, ou dis ce qu'il faut changer."
    apres_avoir_joue = "Joue le build figé de la note ci-dessus, puis **réponds " + au_oui
    seule = ("Ces lots s'ouvrent sans t'attendre. Joue le build figé quand tu veux : ce que tu écris ici passe "
             "devant, et ton « non » fait reproposer la suite.")
    ouvre = pilote.projet.testeur_ouvre
    if corrige:
        entete, appel_au_oui = ("propose la correction : le testeur a jugé l'étape non tenue.",
                                seule if ouvre else apres_avoir_joue)
    elif d_avance and verdict:
        entete, appel_au_oui = (f"propose l'étape suivante : le testeur a joué celle-ci "
                                f"(« {testeur_mod.EN_CLAIR[verdict].lower()} »), pas encore toi.",
                                seule if ouvre else apres_avoir_joue)
    elif d_avance:
        entete, appel_au_oui = "propose l'étape suivante, d'avance : tu n'as pas encore joué celle-ci.", apres_avoir_joue
    else:
        entete, appel_au_oui = "propose le palier suivant.", "**Réponds " + au_oui
    pilote.gh.commenter_issue(issue.numero, f"🤖 **CTO** ({res.agent}) {entete}\n\n"
                                            f"{proposition_en_clair(sortie, numero + 1)}\n\n{appel_au_oui}\n\n"
                              + marque(**pilote._champs(CTO, res, etat=PROPOSITION, sortie=sortie,
                                                        **({"corrige": True} if corrige else {}))))
    pilote.noter(issue.numero, "palier proposé", f"palier {numero + 1}, {len(fiches)} lot(s)", str(res.agent))
    return True


def ouvrir_le_palier(pilote, issue: Lot, palier, numero: int, sortie: dict, *, verdict: str = "",
                     par: str = "proprietaire", refus: int = 0) -> None:
    """Le jalon du palier, son issue et ses lots sont ouverts ; le palier
    d'avant se ferme, et la chaîne part. `par` : qui l'ouvre, le « oui » du
    propriétaire ou le verdict du testeur. Le texte de la nouvelle issue garde
    ce verdict, ce qu'elle corrige et le compte des « non tenue » de suite :
    le testeur y relira l'étape qui reste à tenir."""
    titre = f"Palier {numero} — {(sortie.get('titre') or '').strip() or 'sans titre'}"
    pilote.gh.creer_jalon(titre)
    crees = pilote.ouvrir_les_fiches(sortie.get("fiches") or [], titre)
    non_tenu = verdict == testeur_mod.NON_TENUE
    suite = ("Dès que ces lots sont livrés, le build est figé et le testeur le joue ; son rapport et la note de démo "
             "arrivent ici, puis la suite. " + (
                 "Si le testeur dit l'étape tenue, la suivante s'ouvre sans t'attendre. Joue quand tu veux : ce que "
                 "tu écris ici passe devant." if pilote.projet.testeur_ouvre else
                 "Joue quand tu veux : réponds « oui » pour l'ouvrir, ou écris ce qu'il faut changer."))
    corps = f"{(sortie.get('but') or '').strip()}\n\nSes lots : " + ", ".join(f"#{n}" for n in crees) + f"\n\n{suite}\n"
    if non_tenu:
        corps += (f"\nCe palier corrige le palier {numero - 1} (#{issue.numero}), que le testeur a jugé non tenu"
                  + (" : il s'est ouvert sur son verdict, sans t'attendre." if par == TESTEUR else ".") + "\n")
    elif par == TESTEUR:
        corps += (f"\nOuvert sur le verdict du testeur (« {testeur_mod.EN_CLAIR[verdict].lower()} », #{issue.numero}), "
                  "sans t'attendre : ton « non », écrit ici à tout moment, fait passer la correction devant.\n")
    if verdict:
        corps += "\n" + marque(role="pilote", etat=OUVERT, par=par, verdict=verdict, refus=refus,
                               **({"corrige": issue.numero} if non_tenu else {})) + "\n"
    nouvelle = pilote.gh.creer_issue(titre, corps, [lots.ETIQUETTE_PALIER], titre)
    try:
        pilote.gh.desepingler(issue.numero)
        pilote.gh.epingler(nouvelle)
    except Exception:  # noqa: BLE001 — une épingle manquée ne retient pas le palier
        pass
    atteint = ("non tenu d'après le testeur : le suivant le corrige" if non_tenu else
               f"{testeur_mod.EN_CLAIR[verdict].lower()} d'après le testeur" if par == TESTEUR else
               "atteint" if sortie.get("palier_atteint") else "clos sans être dit atteint")
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


def _heures(marque_: dict, maintenant: datetime) -> float | None:
    try:
        return (maintenant - datetime.fromisoformat(marque_.get("quand") or "")).total_seconds() / 3600
    except (TypeError, ValueError):
        return None


def suite_du_testeur(siennes: list[dict], maintenant: datetime) -> tuple[str, str]:
    """Ce que le pilote fait d'un testeur déjà envoyé, d'après ses marques sur
    l'issue de l'étape : `attendre` (il joue, ou vient de dire qu'il attend le
    bureau), `renvoyer` (son attente a un quart d'heure, son envoi est resté
    sans réponse, son récit ne prouvait rien), ou `noter` : il a rendu son
    verdict, ou il n'a pas pu jouer et la note de démo part sans lui. Avec la
    décision, sa raison."""
    derniere = siennes[-1]
    if derniere.get("etat") == testeur_mod.JOUE:
        return "noter", ""
    raison = (derniere.get("raison") or "").strip()
    echecs = sum(1 for m in siennes if m.get("etat") in (lots.ECHEC, lots.COUPE))
    if echecs >= ECHECS_DU_TESTEUR:
        return "noter", f"{echecs} passages sans récit prouvé" + (f" : {raison}" if raison else "")
    age = _heures(derniere, maintenant)
    if derniere.get("etat") == lots.ENVOYE and (age is None or age < HEURES_SILENCE_TESTEUR):
        return "attendre", "joue le build figé, ou attend que le PC le prenne"
    envois = [h for h in (_heures(m, maintenant) for m in siennes if m.get("etat") == lots.ENVOYE) if h is not None]
    if envois and max(envois) >= HEURES_SANS_TESTEUR:
        return "noter", f"il n'a pas pu jouer en {HEURES_SANS_TESTEUR} heures" + (f" : {raison}" if raison else "")
    if derniere.get("etat") == lots.ENVOYE:
        return "renvoyer", "son envoi est resté sans réponse"
    if age is not None and age < HEURES_ATTENTE_TESTEUR:
        return "attendre", "attend pour jouer" + (f" ({raison})" if raison else "")
    return "renvoyer", raison or "son passage n'a rien rendu"


def envoyer_le_testeur(pilote, issue: Lot, numero: int, pourquoi: str = "") -> str:
    """Le testeur part jouer le build figé sur le PC ; la marque de l'envoi
    attend sa réponse sur l'issue de l'étape."""
    build = f"palier-{numero}"
    if not pilote.gh.pc_actif():
        return "RIEN — le PC est en pause : le testeur part à la reprise"
    pilote.gh.lancer_workflow(WORKFLOW_DU_TESTEUR, pilote.projet.branche_base, {})
    quand = pilote.maintenant().isoformat(timespec="seconds")
    encore = f" de nouveau ({pourquoi})" if pourquoi else ""
    pilote.gh.commenter_issue(
        issue.numero, f"🤖 **pilote** : le build figé `{build}` est construit, et le testeur est envoyé{encore} au PC "
                      "pour le jouer par l'écran, avant la note de démo. Il attend que l'écran soit libre : dix "
                      f"minutes sans clavier ni souris. Tu peux jouer sans l'attendre : `D:\\Forge\\builds\\{build}"
                      "\\Jouer.cmd`.\n\n" + marque(role=TESTEUR, etat=lots.ENVOYE, quand=quand, build=build))
    pilote.noter(issue.numero, "testeur envoyé au PC", build + (f" ({pourquoi})" if pourquoi else ""))
    return f"le testeur est envoyé au PC pour jouer {build}"


def figer_le_build(pilote, issue: Lot, numero: int, publication: bool) -> tuple[str, str, str]:
    """Le PC fige un build de l'étape, et le pilote attend qu'il soit
    construit. Rend son état (`construit`, `rate`, `inacheve`, `pause` ou
    `sans`), ce que la note doit en savoir, et ce qu'elle en dit en tête :
    rien quand il est construit."""
    build = f"palier-{numero}"
    if not pilote.gh.pc_actif():
        return "pause", "le PC est en pause : il n'a pas été construit", " (le PC est en pause : il n'a pas été construit)"
    if not publication:
        return "sans", "non lancé : essai sans publication", ""
    lance = pilote.maintenant()
    pilote.gh.lancer_workflow("build-nuit.yml", pilote.projet.branche_base, {"nom": build})
    etat_du_build, adresse = attendre_le_build(pilote, lance)
    pilote.noter(issue.numero, "build figé", f"{build} : {etat_du_build}")
    ou = f" ({adresse})" if adresse else ""
    construit, en_tete = {
        "construit": (f"construit à l'instant{ou}", ""),
        "rate": (f"⚠️ sa construction a échoué{ou} : le dossier porte un build plus ancien, ou rien",
                 f" (⚠️ sa construction a échoué{' : ' + adresse if adresse else ''})"),
        "inacheve": (f"⚠️ pas encore construit après {ATTENTE_DU_BUILD // 60} minutes d'attente{ou}",
                     " (⚠️ pas encore construit quand cette note a été écrite)"),
    }[etat_du_build]
    return etat_du_build, construit, en_tete


def demo_si_videe(pilote, *, publication: bool = True) -> str:
    """Dès que l'étape n'a plus aucun lot ouvert, une fois par étape, à toute
    heure : son build est figé, le testeur est envoyé le jouer, et la note de
    démo part quand il a rendu son verdict, ou qu'il n'a pas pu jouer. Chaque
    regard fait le pas que les marques de l'issue disent venu."""
    ouvertes = [Lot.de(i) for i in pilote.gh.issues("open")]
    fermes = [Lot.de(i) for i in pilote.gh.issues("closed")]
    issue = issue_du_palier(pilote.gh, ouvertes)
    if issue is None:
        return "RIEN — aucune issue de palier ouverte"
    numero = lots.numero_de_palier(issue.titre) or 0
    siens = _lots_du_palier(numero, ouvertes, fermes)
    if not siens:
        return "RIEN — l'étape n'a encore aucun lot"
    reste = sorted(l.numero for l, ouvert in siens if ouvert)
    if reste:
        return "RIEN — l'étape a encore des lots ouverts : " + ", ".join(f"#{n}" for n in reste)
    commentaires = pilote.gh.issue(issue.numero).get("comments") or []
    if any(m.get("etat") == DEMO for m in lots.marques(commentaires)):
        return "RIEN — la note de démo de l'étape est déjà posée"
    siennes = testeur_mod.marques_du_testeur(commentaires)
    if not siennes:
        etat_du_build, construit, en_tete = figer_le_build(pilote, issue, numero, publication)
        if etat_du_build == "construit":
            return envoyer_le_testeur(pilote, issue, numero)
        # Sans build, il n'y a rien à jouer : la note part, et dit pourquoi.
        return _noter(pilote, issue, numero, ouvertes, fermes, construit, en_tete, publication)
    quoi, raison = suite_du_testeur(siennes, pilote.maintenant())
    if quoi == "attendre":
        return f"RIEN — le testeur {raison}"
    if quoi == "renvoyer":
        if not publication:
            return "RIEN — essai sans publication : le testeur n'est pas renvoyé"
        return envoyer_le_testeur(pilote, issue, numero, raison)
    return _noter(pilote, issue, numero, ouvertes, fermes,
                  "construit, puis joué par le testeur" if not raison else "construit", "", publication,
                  sans_testeur=raison)


def demo(pilote, *, publication: bool = True) -> str:
    """La démo de l'étape, tout de suite et sans attendre le testeur : le PC
    en fige un build, le pilote attend qu'il soit construit, et le CTO écrit
    la note d'une page sur l'issue de l'étape en sachant s'il l'est. Sans
    CTO, le pilote pose les faits tels quels : une démo ne se tait jamais."""
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
    _, construit, en_tete = figer_le_build(pilote, issue, numero, publication)
    return _noter(pilote, issue, numero, ouvertes, fermes, construit, en_tete, publication)


def _noter(pilote, issue: Lot, numero: int, ouvertes: list[Lot], fermes: list[Lot], construit: str, en_tete: str,
           publication: bool, *, sans_testeur: str = "") -> str:
    """La note de démo du CTO sur l'issue de l'étape. `construit` et `en_tete`
    disent où en est le build figé ; `sans_testeur`, pourquoi le testeur n'a
    pas pu le jouer. S'il l'a joué, la note porte son verdict en tête, et le
    CTO écrit en ayant lu son rapport."""
    jour = f"{pilote.maintenant():%Y-%m-%d}"
    fil = _fil(pilote.gh.issue(issue.numero).get("comments") or [], pilote.projet.proprietaire)
    etat, a_revoir = etat_du_palier(pilote, numero, ouvertes, fermes)
    siens = _lots_du_palier(numero, ouvertes, fermes)
    hors_lot = journal.issues_hors_lot(pilote.gh)
    couts = journal.table_des_couts(
        journal.mesures_des_lots(pilote.gh, pilote.projet, sorted({*(l.numero for l, _ in siens), *hors_lot})),
        {l.numero: l.titre for l, _ in siens} | hors_lot)
    build = f"palier-{numero}"
    faits = (f"LE BUILD FIGÉ : D:\\Forge\\builds\\{build} (lancer {build}\\Jouer.cmd) — {construit}\n\n"
             f"LES LOTS DU PALIER :\n"
             f"{etat or '(aucun)'}\n\nÀ REVOIR À LA DÉMO :\n" + ("\n".join(f"- {l}" for l in a_revoir) or "(rien)")
             + f"\n\nCE QUE L'ÉTAPE A COÛTÉ :\n{couts}")
    verdict = _verdict(fil) if not sans_testeur else ""
    if verdict:
        faits += ("\n\nCE QUE LE TESTEUR A TROUVÉ (il a joué ce build par l'écran seul, avant le propriétaire, sans "
                  f"connaître le code) :\n{fil.rapport}")
        en_tete += f"\n\nLe testeur l'a joué avant toi : **{testeur_mod.EN_CLAIR[verdict]}**. Son rapport est juste au-dessus."
    elif sans_testeur:
        faits += f"\n\nCE QUE LE TESTEUR A TROUVÉ :\n(il n'a pas pu jouer ce build : {sans_testeur})"
        en_tete += f"\n\nLe testeur n'a pas pu le jouer ({sans_testeur}) : personne n'a joué ce build avant toi."
    titre = issue.titre.split("—", 1)[-1].strip()
    appel = agents_mod.Appel(role=CTO, lecture_seule=True, jours_max=pilote.projet.jours_max,
                             consigne=consignes.note_de_demo(pilote.projet, numero=numero, titre=titre, faits=faits,
                                                             joue_par_le_testeur=bool(verdict)))
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
