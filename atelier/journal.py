"""Le journal du matin, et ce que la chaîne coûte.

Les faits se relèvent en Python, sur GitHub : ce que chaque lot livré donne
au joueur (sa fiche), où en est chaque lot en cours, ce qui est arrêté et
pourquoi, ce que le CTO a décidé seul (« à revoir samedi »), ce que le
propriétaire doit faire lui-même, et ce que les appels ont coûté. Le lecteur
en fait un récit court, en mots de joueur ; il ne juge rien. S'il se tait ou
sort du gabarit, le pilote écrit le journal seul, à partir des mêmes faits :
un journal ne se tait jamais.

Le coût se relève dans les marques des commentaires, sur GitHub : chaque
appel d'agent y laisse sa mesure, sur le VPS comme sur le PC, coupé ou non.

Chaque journal est sa propre issue, épinglée ; celle de la veille se ferme.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re

from . import agents as agents_mod
from . import consignes, lots
from .github import VARIABLE_PC, GitHub
from .lots import Lot
from .projet import CTO, LECTEUR, ROLES, Projet

ETIQUETTE_JOURNAL = "journal"
_ENTETES = ("> **Avancé** :", "> **Arrêté** :", "> **Pour toi** :", "### Ce qui a changé dans le jeu")
_SECTION = re.compile(r"^##+ (.+?)\n(.*?)(?=^##+ |\Z)", re.S | re.M)


def _date(texte: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat((texte or "").replace("Z", "+00:00"))
    except ValueError:
        return None


def section(corps: str, titre: str) -> str:
    """Une section de la fiche d'un lot (« Ce que je joue de plus »…)."""
    return next((texte.strip() for nom, texte in _SECTION.findall(corps or "") if nom.strip() == titre), "")


# ------------------------------------------------------------------ coûts
@dataclass(frozen=True)
class Mesure:
    """Ce qu'un appel a coûté, tel que sa marque le dit."""

    lot: int
    role: str
    quand: datetime | None
    mesure: dict

    @property
    def cout(self) -> float:
        valeur = self.mesure.get("cout")
        return float(valeur) if isinstance(valeur, (int, float)) else 0.0

    @property
    def duree(self) -> int:
        return int(self.mesure.get("duree") or 0)


def mesures_des_commentaires(numero: int, commentaires: list[dict]) -> list[Mesure]:
    """Les mesures que portent les marques de ces commentaires."""
    lues = []
    for c in commentaires or []:
        quand = _date(c.get("createdAt"))
        for m in lots.marques([c]):
            if isinstance(m.get("mesure"), dict) and m.get("role") in ROLES:
                lues.append(Mesure(lot=numero, role=m["role"], quand=quand, mesure=m["mesure"]))
    return lues


def mesures_des_lots(gh: GitHub, projet: Projet, numeros: list[int]) -> list[Mesure]:
    """Toutes les mesures de ces issues : celles de leur texte (la fiche
    d'une réparation, un journal du matin), de leurs commentaires et de leur PR."""
    lues: list[Mesure] = []
    for numero in numeros:
        issue = gh.issue(numero)
        lues += mesures_des_commentaires(numero, [{"body": issue.get("body"), "createdAt": issue.get("createdAt")}])
        lues += mesures_des_commentaires(numero, issue.get("comments") or [])
        resume = gh.pr_de_branche(Lot.de(issue).branche(projet.prefixe_branche))
        if resume is not None:
            lues += mesures_des_commentaires(numero, gh.pr(resume["number"]).get("comments") or [])
    return lues


def issues_hors_lot(gh: GitHub) -> dict[int, str]:
    """Les issues où la chaîne laisse un coût sans que ce soit un lot :
    celle du palier en cours (les propositions et la note de démo du CTO), et
    les journaux du matin parus depuis qu'elle est ouverte (le lecteur)."""
    ouvertes = gh.issues("open")
    du_palier = [i for i in ouvertes if lots.ETIQUETTE_PALIER in {e["name"] for e in i.get("labels") or []}]
    trouvees = {i["number"]: "le palier (CTO)" for i in du_palier}
    debuts = [d for d in (_date(i.get("createdAt")) for i in du_palier) if d is not None]
    if not du_palier:
        return trouvees
    for issue in [*ouvertes, *gh.issues("closed")]:
        if ETIQUETTE_JOURNAL not in {e["name"] for e in issue.get("labels") or []}:
            continue
        paru = _date(issue.get("createdAt"))
        if not debuts or paru is None or paru >= min(debuts):
            trouvees[issue["number"]] = "le journal du matin"
    return trouvees


def _minutes(secondes: int) -> str:
    return f"{secondes // 60} min" if secondes >= 60 else f"{secondes} s"


def table_des_couts(mesures: list[Mesure], titres: dict[int, str] | None = None) -> str:
    """Ce que la chaîne a coûté, par rôle puis par lot. Le coût est celui du
    prix de l'API, notionnel sous un abonnement ; un appel coupé n'a pas dit
    le sien, il est compté à part. La dernière ligne dit où en sont les
    limites de l'abonnement d'après le dernier appel."""
    if not mesures:
        return "Aucun appel mesuré."
    titres = titres or {}

    def ligne(nom: str, siennes: list[Mesure]) -> str:
        coupes = sum(1 for m in siennes if m.mesure.get("coupe"))
        return (f"| {nom} | {len(siennes)} | {_minutes(sum(m.duree for m in siennes))} | "
                f"{sum(m.cout for m in siennes):.2f} $ | {coupes or '—'} |")

    lignes = ["| rôle | appels | durée | coût (prix de l'API) | coupés |", "|---|---|---|---|---|"]
    lignes += [ligne(role, [m for m in mesures if m.role == role]) for role in ROLES
               if any(m.role == role for m in mesures)]
    lignes.append(ligne("**tous**", mesures))
    lignes += ["", "| lot | appels | durée | coût (prix de l'API) | coupés |", "|---|---|---|---|---|"]
    for numero in sorted({m.lot for m in mesures}):
        nom = f"#{numero}" + (f" {titres[numero]}" if titres.get(numero) else "")
        lignes.append(ligne(nom, [m for m in mesures if m.lot == numero]))
    datees = sorted((m for m in mesures if m.quand and isinstance(m.mesure.get("limites"), dict)),
                    key=lambda m: m.quand)
    if datees:
        semaines = [m.mesure["limites"].get("semaine") for m in datees
                    if isinstance(m.mesure["limites"].get("semaine"), (int, float))]
        derniere = datees[-1].mesure["limites"]

        def part(valeur) -> str:
            return f"{valeur:.0%}" if isinstance(valeur, (int, float)) else "non dite"

        lignes += ["", f"Abonnement, au dernier appel : limite de cinq heures à {part(derniere.get('cinq_heures'))}, "
                       f"limite hebdomadaire à {part(derniere.get('semaine'))}"
                       + (f" (elle était à {part(semaines[0])} au premier appel compté)" if semaines else "") + "."]
    return "\n".join(lignes)


# ------------------------------------------------------------------ faits
@dataclass
class Releve:
    """Les faits du matin, et ce que le pilote en garde pour écrire seul."""

    texte: str = ""
    livres: list[dict] = field(default_factory=list)
    en_cours: list[str] = field(default_factory=list)
    arretes: list[str] = field(default_factory=list)
    a_revoir: list[str] = field(default_factory=list)
    pour_toi: list[str] = field(default_factory=list)
    couts: str = ""


def a_revoir_samedi(numero: int, titre: str, commentaires: list[dict]) -> list[str]:
    """Les choix que le CTO a pris seul sur ce lot, à revoir samedi."""
    return [f"#{numero} {titre} : {m['a_revoir']}" for m in lots.marques(commentaires)
            if m.get("role") == CTO and m.get("etat") == lots.DECISION and (m.get("a_revoir") or "").strip()]


def ou_en_est(liste: list[dict], etat_ci: str = "") -> str:
    """Où en est un lot en cours, en une ligne, d'après les marques de sa PR."""
    plan = lots.plan_du_lot(liste)
    if plan is None:
        return "son plan s'écrit"
    total, faites = int(plan.get("etapes") or 0), len(lots.etapes_faites(liste))
    if faites < total:
        return f"étape {faites + 1} sur {total}"
    verdicts = [m.get("verdict") for m in liste if m.get("verdict")]
    if verdicts and verdicts[-1] == "ACCEPTE":
        return "accepté, il attend sa fusion"
    if verdicts and verdicts[-1] == "CORRIGER":
        return "en correction après la relecture"
    return {"rouge": "en correction, la CI est rouge", "attente": "ses tests tournent"}.get(etat_ci, "en relecture")


def fusionnees_depuis(gh: GitHub, depuis: datetime) -> list[dict]:
    """Les PR fusionnées depuis `depuis`, de la plus ancienne à la plus récente."""
    prs = gh.json("pr", "list", "-R", gh.depot, "--state", "merged", "--limit", "60", "--json",
                  "number,title,headRefName,mergedAt,url") or []
    return sorted((p for p in prs if (_date(p.get("mergedAt")) or depuis) > depuis), key=lambda p: p["mergedAt"])


def releve(gh: GitHub, projet: Projet, maintenant: datetime, *, heures: int = 24) -> Releve:
    """Ce qui s'est passé depuis `heures` heures, relevé sur GitHub."""
    from .github import etat_des_controles
    r = Releve()
    depuis = maintenant - timedelta(hours=heures)
    ouvertes = [Lot.de(i) for i in gh.issues("open")]
    des_lots = [l for l in ouvertes if l.est_un_lot]
    palier = lots.palier_courant(lots.paliers(gh.jalons()))
    lignes = [f"LE PALIER EN COURS : {palier.titre if palier else '(aucun)'}", ""]
    livrees = [p for p in fusionnees_depuis(gh, depuis)
               if (p.get("headRefName") or "").startswith(projet.prefixe_branche)]
    lignes.append(f"LOTS LIVRÉS DEPUIS {depuis:%Y-%m-%d %H:%M} UTC ({len(livrees)}) :")
    comptes: list[int] = []
    titres: dict[int, str] = {}
    for p in livrees:
        numero = int(p["headRefName"][len(projet.prefixe_branche):].split("-", 1)[0])
        issue = gh.issue(numero)
        lot = Lot.de(issue)
        comptes.append(numero)
        titres[numero] = lot.titre
        r.livres.append({"numero": numero, "titre": lot.titre, "url": p.get("url", ""),
                         "joueur": section(lot.corps, "Ce que je joue de plus"),
                         "samedi": section(lot.corps, "Ce que je vois samedi")})
        lignes += [f"- #{numero} « {lot.titre} » — {p.get('url', '')} (piste : {lot.piste(projet.pistes) or '—'})",
                   f"  Ce que je joue de plus : {r.livres[-1]['joueur'] or '(non dit)'}",
                   f"  Ce que je vois samedi : {r.livres[-1]['samedi'] or '(non dit)'}"]
        r.a_revoir += a_revoir_samedi(numero, lot.titre, issue.get("comments") or [])
    lignes += ["", "LOTS EN COURS :"]
    for lot in des_lots:
        if lot.etat != "en-cours":
            continue
        comptes.append(lot.numero)
        titres[lot.numero] = lot.titre
        resume = gh.pr_de_branche(lot.branche(projet.prefixe_branche))
        pr = gh.pr(resume["number"]) if resume else None
        etat = ou_en_est(lots.marques(pr.get("comments") or []), etat_des_controles(pr)[0]) if pr else "son plan s'écrit"
        r.en_cours.append(f"#{lot.numero} « {lot.titre} » ({lot.piste(projet.pistes) or '—'}) : {etat}")
        r.a_revoir += a_revoir_samedi(lot.numero, lot.titre, gh.issue(lot.numero).get("comments") or [])
    lignes += [f"- {l}" for l in r.en_cours] or ["- (aucun)"]
    lignes += ["", "LOTS ARRÊTÉS :"]
    for lot in des_lots:
        if lot.etat != "bloque":
            continue
        comptes.append(lot.numero)
        titres[lot.numero] = lot.titre
        commentaires = gh.issue(lot.numero).get("comments") or []
        trouve = lots.dernier_blocage(commentaires)
        raison = (trouve[1].get("raison") if trouve else "") or "sans raison écrite"
        decisions = [m for m in lots.marques(commentaires) if m.get("role") == CTO and m.get("etat") == lots.DECISION]
        suite = {"reporter": "reporté à samedi par le CTO", "proprietaire": "il attend le propriétaire"}.get(
            decisions[-1].get("decision") if decisions else "", "le CTO le regarde")
        r.arretes.append(f"#{lot.numero} « {lot.titre} » : {raison} — {suite}")
        if decisions and decisions[-1].get("decision") == "proprietaire":
            r.pour_toi.append(f"#{lot.numero} « {lot.titre} » : le CTO te laisse la décision "
                              f"({decisions[-1].get('pourquoi') or raison})")
        r.a_revoir += a_revoir_samedi(lot.numero, lot.titre, commentaires)
    lignes += [f"- {l}" for l in r.arretes] or ["- (aucun)"]
    if not gh.pc_actif():
        r.pour_toi.append(f"le PC est en pause ({VARIABLE_PC} = non) : les lots de la ville et de l'interface attendent")
    lignes += ["", "À REVOIR SAMEDI (les choix que le CTO a pris seul) :"] + ([f"- {l}" for l in r.a_revoir] or ["- (rien)"])
    lignes += ["", "POUR LE PROPRIÉTAIRE :"] + ([f"- {l}" for l in r.pour_toi] or ["- (rien)"])
    hors_lot = issues_hors_lot(gh)
    mesures = [m for m in mesures_des_lots(gh, projet, sorted({*comptes, *hors_lot}))
               if m.quand is None or m.quand > depuis]
    r.couts = table_des_couts(mesures, titres | hors_lot)
    r.texte = "\n".join(lignes)
    return r


# ---------------------------------------------------------------- écrire
def publier(gh: GitHub, titre: str, corps: str) -> int:
    """Une issue par journal, épinglée ; celles d'avant se désépinglent et se
    ferment : l'issue ouverte est toujours la dernière."""
    anciennes = [i["number"] for i in gh.issues("open")
                 if ETIQUETTE_JOURNAL in {e["name"] for e in i.get("labels") or []}]
    numero = gh.creer_issue(titre, corps, [ETIQUETTE_JOURNAL])
    for n in anciennes:
        try:
            gh.desepingler(n)
        except Exception:  # noqa: BLE001 — une issue jamais épinglée ne retient pas le journal
            pass
        gh.fermer_issue(n, f"Le suivant : #{numero}.")
    try:
        gh.epingler(numero)
    except Exception:  # noqa: BLE001 — trois issues déjà épinglées ne retiennent pas le journal
        pass
    return numero


def infidele(texte: str, faits_du_matin: str) -> str | None:
    """Pourquoi le texte du lecteur est écarté : il sort du gabarit, ou cite
    un numéro que les faits ne donnent pas. None s'il est fidèle."""
    manquantes = [e for e in _ENTETES if e not in texte]
    if manquantes:
        return f"il sort du gabarit ({', '.join(manquantes)} absent)"
    inconnus = sorted({n for n in re.findall(r"#(\d+)", texte)} - set(re.findall(r"#(\d+)", faits_du_matin))
                      - set(re.findall(r"/pull/(\d+)", faits_du_matin)))
    if inconnus:
        return "il cite " + ", ".join(f"#{n}" for n in inconnus) + ", que les faits ne donnent pas"
    return None


def redaction_du_pilote(r: Releve) -> str:
    """Le journal, écrit sans agent, dans le même gabarit."""
    avance = "; ".join(l["titre"] for l in r.livres[:3]) or "rien de livré depuis hier"
    lignes = [f"> **Avancé** : {avance}.", f"> **Arrêté** : {'; '.join(r.arretes) or 'rien'}.",
              f"> **Pour toi** : {'; '.join(r.pour_toi) or 'rien'}.", "", "### Ce qui a changé dans le jeu"]
    for l in r.livres:
        lignes += ["", f"**[{l['titre']}]({l['url']})**", l["joueur"] or "", l["samedi"] or ""]
    if not r.livres:
        lignes.append("Aucun lot livré depuis hier.")
    lignes += ["", "### En route"] + ([f"- {l}" for l in r.en_cours] or ["- rien"])
    lignes += ["", "### À revoir samedi"] + ([f"- {l}" for l in r.a_revoir] or ["- rien"])
    return "\n".join(lignes)


def ecrire(gh: GitHub, projet: Projet, *, maintenant: datetime | None = None, publication: bool = True,
           executeur=agents_mod.executer, dossier: Path | None = None) -> str:
    """Le journal du matin : les faits, le récit du lecteur (ou du pilote), les coûts."""
    maintenant = maintenant or datetime.now(timezone.utc)
    r = releve(gh, projet, maintenant)
    appel = agents_mod.Appel(role=LECTEUR, lecture_seule=True, sans_outil=True, consigne=consignes.journal(faits=r.texte))
    res = agents_mod.invoquer(projet.agent(LECTEUR), appel, dossier or projet.racine, projet.delai(LECTEUR),
                              executeur=executeur, trace=agents_mod.nom_de_trace("journal", LECTEUR, maintenant))
    if not (res.reussi and res.texte.strip()):
        pourquoi = f"Le lecteur n'a pas répondu ({res.raison or f'code {res.code}'})"
    else:
        pourquoi = infidele(res.texte, r.texte)
        pourquoi = pourquoi and f"Le texte du lecteur ({res.agent}) est écarté : {pourquoi}"
    if pourquoi:
        redaction, signature = redaction_du_pilote(r), f"{pourquoi}. Écrit par le pilote, à partir des faits."
    else:
        redaction, signature = res.texte.strip(), f"Écrit par {res.agent}."
    mesure = (f" Ce journal a coûté {res.mesure['cout']:.2f} $ au prix de l'API."
              if isinstance(res.mesure.get("cout"), (int, float)) else "")
    corps = (f"{redaction}\n\n<details><summary>Ce que les appels ont coûté depuis hier</summary>\n\n{r.couts}\n\n"
             f"</details>\n\n<sub>{signature}{mesure}</sub>")
    if res.mesure:
        # La mesure du lecteur vit dans le texte du journal : elle se relève comme les autres.
        corps += "\n\n" + lots.marque(role=LECTEUR, etat="journal", agent=str(projet.agent(LECTEUR)),
                                       mesure=res.mesure)
    if publication:
        publier(gh, f"Journal du {maintenant:%d/%m/%Y}", corps)
    return corps


def couts_du_palier(gh: GitHub, projet: Projet) -> str:
    """Ce que le palier en cours a coûté depuis son premier appel, par rôle et par lot."""
    palier = lots.palier_courant(lots.paliers(gh.jalons()))
    siens = [Lot.de(i) for etat in ("open", "closed") for i in gh.issues(etat)]
    siens = [l for l in siens if l.est_un_lot and palier is not None and l.palier == palier.numero]
    hors_lot = issues_hors_lot(gh)
    mesures = mesures_des_lots(gh, projet, sorted({*(l.numero for l in siens), *hors_lot}))
    return table_des_couts(mesures, {l.numero: l.titre for l in siens} | hors_lot)

