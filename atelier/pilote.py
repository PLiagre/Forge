"""Le pilote : un tour de la chaîne.

Un tour relit GitHub, fait avancer d'un pas les lots en cours, puis, si
aucun agent n'est parti, regarde master, un lot bloqué, le palier du samedi,
et prend le lot suivant quand une machine a de la place. Il invoque au plus
UN agent : un tour reste court à lire. Plusieurs tours tournent en même temps
— le cron en lance un toutes les deux minutes —, et des verrous (`verrous.py`)
font qu'un lot n'avance que dans un tour à la fois.

Tout ce qui se décide se décide dans `lots.py`, en fonction pure ; ici, on
fait les gestes.

    la fiche (le CTO) → le plan (le meneur ouvre sa session, le pilote ouvre
    la PR) → les étapes (la session est reprise pour chacune) → la CI → la
    relecture (une autre session) → la fusion.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Callable

from . import agents as agents_mod
from . import captures, consignes, lfs, lots, traces
from .depot import Depot, DepotErreur
from .github import (AGREGATS, VARIABLE_PC, GitHub, GitHubErreur, controles_de_la_pr, etat_des_controles,
                     travaux as travaux_du_workflow)
from .lots import Lot, Question, marque
from .projet import CHEF, CTO, LECTEUR, MACHINES, RELECTEUR, ROLES_MENEURS, Projet
from .verrous import AucunVerrou

_RUN = re.compile(r"/actions/runs/(\d+)/")
_TRAVAIL = re.compile(r"/actions/runs/(\d+)/job/(\d+)")
SIGNATURE = "\n\n🤖 Généré par la chaîne de Forge ([Claude Code](https://claude.com/claude-code))"
NOMS = {CTO: "CTO", CHEF: "chef de lot", "developpeur": "développeur", RELECTEUR: "relecteur", LECTEUR: "lecteur"}


@dataclass
class Photos:
    """Ce qu'on a regardé d'une révision poussée : les images publiées, une
    note pour le relecteur, et ce qui entre dans la marque (`unity`)."""

    urls: list[str] = field(default_factory=list)
    note: str = ""
    marque: dict = field(default_factory=dict)


Photographe = Callable[[Path, Lot, str], Photos]


@dataclass
class _Vue:
    """Ce qu'un tour a relu et rangé, sous le verrou « decider »."""

    palier: "lots.Palier | None"
    ouvertes: list[Lot]
    fermes: list[Lot]


def _verrou_du_lot(numero: int | str) -> str:
    return f"lot-{numero}"


def _extrait(texte: str, lignes: int = 60) -> str:
    morceaux = (texte or "").strip().splitlines()
    if len(morceaux) <= lignes:
        return "\n".join(morceaux)
    return "\n".join(morceaux[:lignes]) + f"\n… ({len(morceaux) - lignes} lignes de plus)"


def _dit(mesure: dict) -> str:
    """Une mesure, en une ligne lisible."""
    return ", ".join(x for x in (
        f"{mesure['cout']:.2f} $" if isinstance(mesure.get("cout"), (int, float)) else "",
        f"{mesure['tours']} tours" if mesure.get("tours") else "",
        f"{mesure['duree']} s" if mesure.get("duree") else "",
        "coupé" if mesure.get("coupe") else "") if x)


def corps_de_pr(lot: Lot, projet: Projet, etapes: list[dict], faites: set[int], changes: dict[str, str],
                non_declares: list[str] = ()) -> str:
    """Le texte de la PR d'un lot : son plan, coché à mesure, et ses tests changés."""
    plan = "\n".join(f"- [{'x' if i in faites else ' '}] **{i}. {e.get('titre', '')}** — {e.get('quoi', '')} "
                     f"({'le développeur' if e.get('qui') == 'developpeur' else 'le chef'})"
                     for i, e in enumerate(etapes, start=1)) or "(en cours d'écriture)"
    tests = "\n".join(f"- `{f}` : {pourquoi}" for f, pourquoi in sorted(changes.items()))
    tests += "".join(f"\n- `{f}` : ⚠️ modifié sans raison donnée" for f in non_declares if f not in changes)
    return (f"Closes #{lot.numero}\n\n{lot.palier_titre or 'Hors palier'} · Piste : {lot.piste(projet.pistes) or '—'} "
            f"· Machine : {lot.machine}\n\n## Le plan\n{plan}\n\n## Tests changés\n"
            f"{tests.strip() or 'Aucun test existant ne change.'}" + SIGNATURE)


class Pilote:
    def __init__(self, projet: Projet, gh: GitHub, depot: Depot, *, journal: Path,
                 executeur_agents: agents_mod.Executeur = agents_mod.executer, maintenant=None, verrous=None,
                 lfs_telechargeur: lfs.Telechargeur = lfs.telecharger, machine: str = "vps",
                 garder_les_traces: bool = True, seul: int | None = None):
        self.projet = projet
        self.gh = gh
        self.depot = depot
        self.executeur_agents = executeur_agents
        # Les verrous partagés avec les autres tours ; sans eux, un seul tour
        # à la fois (les tests, le tour à sec, le côté PC).
        self.verrous = verrous or AucunVerrou()
        self.maintenant = maintenant or (lambda: datetime.now(timezone.utc))
        # Le journal local de cette machine : un fait par ligne. Il n'a pas de
        # chemin par défaut : un test ou un tour à sec n'écrit jamais dans le
        # vrai journal sans l'avoir demandé.
        self.journal = Path(journal)
        self.machine = machine
        self.garder_les_traces = garder_les_traces
        # Un seul lot : le tour ne regarde que lui, quel que soit son palier,
        # et ne touche à aucun autre (un essai, une réparation à la main).
        self.seul = seul
        self.lignes: list[str] = []
        self.lfs_telechargeur = lfs_telechargeur
        # Le groupe de capture que le meneur a nommé pour le lot en cours de passage (PC).
        self.capture = ""
        self.invoques = 0  # les agents appelés par ce pilote, tous tours confondus
        self.attentes = 0  # ceux de ces appels où personne n'a pu répondre

    # ----------------------------------------------------------- journal
    def noter(self, lot: int | str, action: str, detail: str = "", agent: str | None = None, *,
              mesure: dict | None = None) -> None:
        quand = self.maintenant().isoformat(timespec="seconds")
        entree = {"quand": quand, "lot": lot, "action": action, "detail": detail, "agent": agent,
                  "machine": self.machine}
        if mesure:
            entree["mesure"] = mesure
        try:
            self.journal.parent.mkdir(parents=True, exist_ok=True)
            with self.journal.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entree, ensure_ascii=False) + "\n")
        except OSError:
            pass
        self.lignes.append(f"#{lot} {action}" + (f" [{agent}]" if agent else "") + (f" — {detail}" if detail else ""))

    def _invoquer(self, role: str, appel: agents_mod.Appel, chemin: Path, *, lot: int | str) -> agents_mod.Resultat:
        """Appelle le rôle. Chaque appel qui a coûté quelque chose l'écrit au
        journal local, coupé ou non ; la marque du commentaire que le pilote
        pose ensuite le porte sur GitHub, d'où se relève le coût d'un lot."""
        self.invoques += 1
        trace = agents_mod.nom_de_trace(lot, role, self.maintenant()) if self.garder_les_traces else None
        res = agents_mod.invoquer(self.projet.agent(role), appel, chemin, self.projet.delai(role),
                                  executeur=self.executeur_agents, trace=trace,
                                  place=lambda outil: self.verrous.place(f"outil-{outil}", self.projet.plafond(outil)))
        if res.attente:
            self.attentes += 1
        if res.mesure:
            self.noter(lot, "appel", f"{role} : {_dit(res.mesure)}", str(res.agent or self.projet.agent(role)),
                       mesure={"role": role, **res.mesure})
        return res

    def _champs(self, role: str, res: agents_mod.Resultat, **champs) -> dict:
        """Ce que porte la marque d'un appel : qui, sur quelle machine, dans
        quelle session, et ce qu'il a coûté."""
        communs = {"role": role, "agent": str(res.agent or self.projet.agent(role)), "machine": self.machine}
        if res.session:
            communs["session"] = res.session
        if res.mesure:
            communs["mesure"] = res.mesure
        return communs | champs

    # --------------------------------------------------------------- tour
    def tour(self) -> list[str]:
        """Un tour : relire et ranger (un tour après l'autre), faire avancer
        d'un pas les lots en cours qu'aucun autre tour ne tient, puis, si aucun
        agent n'est parti : master, un lot bloqué, le palier, le lot suivant."""
        self.lignes = []
        with self.verrous.tenir("decider"):
            vue = self._ranger_le_monde()
        agent_parti = False
        for lot in sorted(vue.ouvertes, key=lambda l: (not l.urgent, l.numero)):
            if not lot.est_un_lot or lot.etat != "en-cours" or agent_parti:
                continue
            if not self.verrous.prendre(_verrou_du_lot(lot.numero)):
                continue  # un autre tour le fait avancer
            try:
                # Relu sous son verrou : depuis la relecture du tour, un autre
                # tour a pu le livrer, le bloquer ou le rendre.
                lot = Lot.de(self.gh.issue(lot.numero))
                if lot.etat != "en-cours":
                    continue
                agent_parti = self._a_fait_partir(lambda: self._avancer(lot))
            except (GitHubErreur, DepotErreur) as e:
                self.noter(lot.numero, "erreur", str(e))
            finally:
                self._lacher_lot(lot.numero)
        pas_du_tour = ((lambda: self._debloquer_un_lot(vue),) if self.seul is not None else
                       (lambda: self._master_rouge(vue), lambda: self._debloquer_un_lot(vue),
                        lambda: self._palier(vue)))
        for pas in pas_du_tour:
            if agent_parti:
                break
            avant = self.invoques
            try:
                agent_parti = self._a_fait_partir(pas)
            except (GitHubErreur, DepotErreur) as e:
                # Une panne ici se dit et n'arrête que ce pas : les lots continuent.
                self.noter("chaîne", "erreur", str(e))
                agent_parti = self.invoques > avant
        if not agent_parti and (vue.palier is not None or self.seul is not None
                                or any(l.urgent for l in vue.ouvertes)):
            self._prendre_le_suivant(vue)
        if not self.lignes:
            self.lignes.append("RIEN")
        return self.lignes

    def _a_fait_partir(self, pas) -> bool:
        """Le pas a-t-il fait partir un agent ? Un pas dont chaque appel n'a
        trouvé personne (quota, session expirée, outil plein) n'a fait
        qu'attendre : il ne retient pas le tour, et les autres lots sont essayés."""
        invoques, attentes = self.invoques, self.attentes
        parti = pas()
        appels = self.invoques - invoques
        return bool(parti) and not (appels and appels == self.attentes - attentes)

    def _palier(self, vue: "_Vue") -> bool:
        from . import palier
        return palier.samedi(self, vue.palier, vue.ouvertes, vue.fermes)

    def _ranger_le_monde(self) -> "_Vue":
        """Ce que le tour sait du monde, rangé : les boucles de dépendances
        sont dites, les lots qui attendent une dépendance rendent leur machine,
        les lots auxquels on a répondu repartent, les lots fusionnés sont
        livrés. Se fait sous le verrou « decider » : un tour à la fois."""
        self.depot.fetch()
        courant = lots.palier_courant(lots.paliers(self.gh.jalons()))
        ouvertes = self._ouvertes()
        fermees = [i for i in self.gh.issues("closed") if self.seul is None or i["number"] == self.seul]
        fermes = [Lot.de(i) for i in fermees]
        toutes = [Lot.de(i) for i in self.gh.issues("open")] if self.seul is not None else ouvertes
        bloq = lots.bloquantes(toutes, fermes)
        change = self._signaler_les_boucles(ouvertes) if self.seul is None else False
        change |= bool(self._lever_sur_reponse(ouvertes))
        if change:
            ouvertes = self._ouvertes()
            bloq = lots.bloquantes(ouvertes if self.seul is None else toutes, fermes)
        if self._attendre_dependances(ouvertes, bloq) | self._reprendre(ouvertes, bloq):
            ouvertes = self._ouvertes()
        self._livrer_les_fermes(fermees)
        return _Vue(palier=courant, ouvertes=ouvertes, fermes=fermes)

    def _ouvertes(self) -> list[Lot]:
        """Les issues ouvertes que ce tour regarde : toutes, ou le seul lot demandé."""
        return [l for l in (Lot.de(i) for i in self.gh.issues("open")) if self.seul is None or l.numero == self.seul]

    def _prendre_le_suivant(self, vue: "_Vue") -> None:
        """Le lot suivant, quand sa machine a de la place : ses lots en cours,
        et ceux qu'un autre tour est en train de prendre, restent sous sa
        capacité. Le choix se fait sur une relecture fraîche, sous le verrou
        « decider » ; le lot avance ensuite, sous son seul verrou."""
        with self.verrous.tenir("decider"):
            ouvertes = [Lot.de(i) for i in self.gh.issues("open")]
            bloq = lots.bloquantes(ouvertes, vue.fermes)
            tous = [l for l in ouvertes if l.est_un_lot and (self.seul is None or l.numero == self.seul)]
            en_prise = {l.numero for l in tous
                        if l.etat == "pret" and self.verrous.pris_ailleurs(_verrou_du_lot(l.numero))}
            tenus = Counter(l.machine for l in tous if l.etat == "en-cours" or l.numero in en_prise)
            libres = {m: tenus[m] < self.projet.capacite(m) for m in MACHINES}
            # Un PC en pause ne prend aucun lot neuf : le VPS continue.
            if libres["pc"] and not self.gh.pc_actif():
                libres["pc"] = False
            if not any(libres.values()):
                return
            # Un lot « pret » qui a déjà sa PR attend une place pour reprendre
            # (`_reprendre`) : il ne repart jamais de zéro.
            avec_pr = {p["headRefName"] for p in self.gh.prs_ouvertes()}
            libres_de_prendre = [l for l in tous if l.numero not in en_prise
                                 and l.branche(self.projet.prefixe_branche) not in avec_pr]
            if self.seul is not None:
                suivant = next((l for l in libres_de_prendre if l.etat == "pret" and libres.get(l.machine)
                                and not l.dependances & bloq), None)
            else:
                suivant = lots.a_prendre(libres_de_prendre, vue.palier.numero if vue.palier else None, libres, bloq)
            if suivant is None or not self.verrous.prendre(_verrou_du_lot(suivant.numero)):
                return
            self.gh.etiqueter(suivant.numero, ["en-cours"], ["pret"])
        try:
            self.noter(suivant.numero, "pris", suivant.titre)
            self._avancer(Lot.de(self.gh.issue(suivant.numero)))
        except (GitHubErreur, DepotErreur) as e:
            self.noter(suivant.numero, "erreur", str(e))
        finally:
            self._lacher_lot(suivant.numero)

    def _lacher_lot(self, numero: int) -> None:
        """Rend le lot aux autres tours, sous le verrou « decider » : un tour
        qui choisit le lot suivant voit soit le verrou encore tenu, soit
        l'étiquette que ce tour vient de poser, jamais un entre-deux."""
        with self.verrous.tenir("decider"):
            self.verrous.lacher(_verrou_du_lot(numero))

    def _pris_ailleurs(self, numero: int) -> bool:
        return self.verrous.pris_ailleurs(_verrou_du_lot(numero))

    # ---------------------------------------------------------- ranger
    def _signaler_les_boucles(self, ouvertes: list[Lot]) -> bool:
        """Des lots qui s'attendent en rond n'avanceraient jamais : la boucle
        est dite sur chacun, une fois, et le plus récent est bloqué pour que le
        CTO retire la dépendance de trop."""
        change = False
        for boucle in lots.boucles([l for l in ouvertes if l.est_un_lot]):
            dernier = max(boucle)
            issue = self.gh.issue(dernier)
            if any(m.get("etat") == lots.BLOQUE and m.get("boucle") == list(boucle)
                   for m in lots.marques(issue.get("comments") or [])):
                continue
            chemin = " → ".join(f"#{n}" for n in (*boucle, boucle[0]))
            for numero in boucle:
                if numero != dernier:
                    self.gh.commenter_issue(numero, f"🤖 **pilote** : ce lot est pris dans une boucle de dépendances "
                                                    f"({chemin}) : aucun de ces lots ne peut partir. Le CTO la "
                                                    f"dénoue sur #{dernier}.\n\n"
                                                    f"{marque(role='pilote', etat=lots.BOUCLE, boucle=list(boucle))}")
            self._bloquer(dernier, f"boucle de dépendances : {chemin}", boucle=list(boucle))
            change = True
        return change

    def _attendre_dependances(self, ouvertes: list[Lot], bloq: frozenset[int]) -> set[int]:
        """Un lot en cours dont une dépendance est encore ouverte n'avance pas
        et ne tient pas sa machine : il redevient « pret », et la reprise le
        relance quand elles sont livrées."""
        rendus = set()
        for lot in ouvertes:
            attend = sorted(lot.dependances & bloq)
            if not lot.est_un_lot or lot.etat != "en-cours" or not attend or self._pris_ailleurs(lot.numero):
                continue
            liste = ", ".join(f"#{n}" for n in attend)
            self.gh.etiqueter(lot.numero, ["pret"], ["en-cours"])
            self.gh.commenter_issue(lot.numero, f"🤖 **pilote** : lot remis « pret » — il dépend de {liste}, pas encore "
                                                "livré. Il reprendra où il en est quand ce sera fait ; d'ici là, il "
                                                f"rend sa machine.\n\n{marque(role='pilote', etat='attend', raison=liste)}")
            self.noter(lot.numero, "remis pret", f"dépend de {liste}")
            rendus.add(lot.numero)
        return rendus

    def _lever_sur_reponse(self, ouvertes: list[Lot]) -> set[int]:
        """Un lot bloqué sur lequel le propriétaire a écrit depuis son blocage
        repart : ce qu'il a écrit suffit, sans toucher aux étiquettes, et suit
        le lot comme une consigne."""
        leves = set()
        for lot in ouvertes:
            if lot.etat != "bloque" or not lot.est_un_lot or self._pris_ailleurs(lot.numero):
                continue
            if not lots.reponse_apres_blocage(self.gh.issue(lot.numero).get("comments") or [],
                                              self.projet.proprietaire):
                continue
            self.gh.commenter_issue(lot.numero, "🤖 **pilote** : réponse reçue — lot remis « pret ». Il reprend où il "
                                                "en est, essais remis à zéro ; ta réponse suit le lot.\n\n"
                                                f"{marque(role='pilote', etat='reponse')}")
            self.gh.etiqueter(lot.numero, ["pret"], ["bloque"])
            self.noter(lot.numero, "réponse reçue", "remis pret")
            leves.add(lot.numero)
        return leves

    def _reprendre(self, ouvertes: list[Lot], bloq: frozenset[int] = frozenset()) -> set[int]:
        """Un lot remis « pret » alors que sa PR est ouverte reprend où il en
        est, dès que ses dépendances sont livrées et que sa machine a une
        place. La marque « reprise » sur la PR remet ses compteurs à zéro ; elle
        s'écrit avant l'étiquette : sans elle, le lot recompterait ses échecs
        et serait rebloqué."""
        prets = [l for l in ouvertes if l.etat == "pret" and l.est_un_lot and not l.dependances & bloq
                 and not self._pris_ailleurs(l.numero)]
        if not prets:
            return set()
        par_branche = {p["headRefName"]: p for p in self.gh.prs_ouvertes()}
        tenus = Counter(l.machine for l in ouvertes if l.est_un_lot and l.etat == "en-cours")
        repris = set()
        for lot in prets:
            pr = par_branche.get(lot.branche(self.projet.prefixe_branche))
            if pr is None or tenus[lot.machine] >= self.projet.capacite(lot.machine):
                continue
            if lot.machine == "pc" and not self.gh.pc_actif():
                continue
            tenus[lot.machine] += 1
            quand = self.maintenant().isoformat(timespec="seconds")
            self.gh.commenter_pr(pr["number"], "🤖 **pilote** : lot repris. Ses essais repartent de zéro ; le travail "
                                               f"déjà poussé reste.\n\n{marque(role='pilote', etat=lots.REPRISE, quand=quand)}")
            self.gh.etiqueter(lot.numero, ["en-cours"], [e for e in ("pret", "bloque") if e in lot.etiquettes])
            self.noter(lot.numero, "repris", f"PR #{pr['number']}")
            repris.add(lot.numero)
        return repris

    # ---------------------------------------------------------- avancer
    def _avancer(self, lot: Lot) -> bool:
        """Un pas du lot. Vrai quand un agent est parti."""
        branche = lot.branche(self.projet.prefixe_branche)
        resume = self.gh.pr_de_branche(branche)
        if resume is None:
            if lot.machine == "pc" and self.machine != "pc":
                return self._passer_au_pc(lot, lots.marques(self.gh.issue(lot.numero).get("comments") or []),
                                          "planifier", None)
            return self._planifier(lot)
        pr = self.gh.pr(resume["number"])
        liste = lots.marques(pr.get("comments") or [])
        etat_ci, _ = etat_des_controles(pr)
        action = lots.action_suivante(pr, etat_ci, liste, corrections_max=self.projet.corrections_max,
                                      coupures_max=self.projet.coupures_max,
                                      heures_depuis_envoi_pc=self._heures_depuis(liste, lots.ENVOYE),
                                      heures_depuis_attente_pc=self._heures_depuis(liste, lots.ATTENTE))
        numero_pr = pr["number"]
        if action.nom == "livrer":
            self._livrer(lot.numero, numero_pr)
            return False
        if action.nom == "bloquer":
            self._bloquer(lot.numero, action.raison, numero_pr if pr.get("state") == "OPEN" else None)
            return False
        if action.nom.startswith("attendre"):
            self.noter(lot.numero, action.nom, f"PR #{numero_pr}" + (f" — {action.raison}" if action.raison else ""))
            return False
        if action.nom == "fusionner":
            self.gh.fusion_auto(numero_pr, pr.get("headRefOid"))
            self.noter(lot.numero, "fusion automatique demandée", f"PR #{numero_pr}")
            return False
        if action.nom == "relancer_pc":
            derniere = next((m.get("action") for m in reversed(liste) if m.get("etat") == lots.ENVOYE), None)
            return self._passer_au_pc(lot, [], derniere or "etape", pr)
        if action.nom in ("resumer_ci", "corriger_ci") and (self._attendre_la_base(lot, pr, branche, liste)
                                                            or self._rejouer_une_panne(lot, pr, liste)
                                                            or self._rejouer_le_chronometre(lot, pr, branche, liste)):
            return False
        if action.nom == "resumer_ci":
            return self._resumer_ci(lot, pr)
        if action.nom in ("etape", "corriger_ci", "corriger_relecture", "conflit"):
            if lot.machine == "pc" and self.machine != "pc":
                return self._passer_au_pc(lot, liste, action.nom, pr)
            return self.passage(lot, pr, action, liste)
        if action.nom == "relire":
            return self._relire(lot, pr, branche, liste)
        if action.nom == "arbitrer":
            return self._arbitrer(lot, pr, branche, liste)
        if action.nom == "planifier":
            return self._planifier(lot)
        self.noter(lot.numero, "action inconnue", action.nom)
        return False

    def _heures_depuis(self, liste: list[dict], etat: str) -> float | None:
        """Les heures écoulées depuis la dernière marque `etat` du meneur."""
        vues = [m for m in lots.du_meneur(liste) if m.get("etat") == etat and m.get("quand")]
        if not vues:
            return None
        return (self.maintenant() - datetime.fromisoformat(vues[-1]["quand"])).total_seconds() / 3600

    def _heures_depuis_pilote(self, liste: list[dict], etat: str) -> float | None:
        vues = [m for m in liste if m.get("role") == "pilote" and m.get("etat") == etat and m.get("quand")]
        if not vues:
            return None
        return (self.maintenant() - datetime.fromisoformat(vues[-1]["quand"])).total_seconds() / 3600

    # ----------------------------------------------------------------- PC
    def _passer_au_pc(self, lot: Lot, liste: list[dict], action: str, pr: dict | None) -> bool:
        """Un pas du meneur d'un lot `pc` : sa session vit sur le PC, c'est
        donc lui qui le fait. Le pilote le lui envoie, et attend sa réponse
        sur l'issue (avant la PR) ou sur la PR."""
        siens = lots.du_meneur(lots.depuis_reprise(liste))
        if pr is None and siens and siens[-1].get("etat") in (lots.ENVOYE, lots.ATTENTE):
            heures = self._heures_depuis(liste, siens[-1]["etat"])
            limite = lots.HEURES_SILENCE_PC if siens[-1]["etat"] == lots.ENVOYE else lots.HEURES_ATTENTE_PC
            if heures is not None and heures < limite:
                self.noter(lot.numero, "attendre_pc", "le plan est parti sur le PC")
                return False
        if not self.gh.pc_actif():
            self.noter(lot.numero, "attente", f"PC en pause ({VARIABLE_PC} = non) : {action} part à la reprise")
            return False
        self.gh.lancer_workflow("lot-pc.yml", self.projet.branche_base, {"issue": str(lot.numero)})
        quand = self.maintenant().isoformat(timespec="seconds")
        texte = (f"🤖 **pilote** : travail envoyé au PC ({action}). Il part quand le PC est allumé ; sans réponse en "
                 f"24 h, il est renvoyé.\n\n{marque(role=lot.meneur, etat=lots.ENVOYE, action=action, quand=quand)}")
        if pr is None:
            self.gh.commenter_issue(lot.numero, texte)
        else:
            self.gh.commenter_pr(pr["number"], texte)
        self.noter(lot.numero, "envoyé au PC", action)
        return False

    def marquer_attente(self, lot: Lot, numero_pr: int | None, raison: str) -> None:
        """Le PC n'a pas pu travailler : la marque répond à l'envoi sans compter
        comme un passage du meneur, et le pilote renvoie dans l'heure."""
        quand = self.maintenant().isoformat(timespec="seconds")
        texte = (f"🤖 **{NOMS[lot.meneur]}** (PC) : le lot attend — {raison}\n\nAucun essai n'est compté ; le pilote "
                 f"renvoie le travail dans une heure.\n\n{marque(role=lot.meneur, etat=lots.ATTENTE, quand=quand)}")
        if numero_pr is None:
            self.gh.commenter_issue(lot.numero, texte)
        else:
            self.gh.commenter_pr(numero_pr, texte)

    # ------------------------------------------------------------ le plan
    def _session(self, lot: Lot, liste: list[dict]) -> tuple[str, bool]:
        """La session du lot, et si elle existe déjà (une marque la porte)."""
        session = lots.session_du_lot(self.projet.depot, lot.numero)
        return session, any(m.get("session") == session and m.get("machine", self.machine) == self.machine
                            for m in liste)

    def _planifier(self, lot: Lot, *, chantier: str | int | None = None, marquer_attente: bool = False) -> bool:
        """Le meneur ouvre sa session, lit la fiche et le code, et rend son
        plan ; le pilote ouvre la PR, le plan dedans. Il lit sans écrire : la
        suite entière et les simulations longues lui sont fermées."""
        issue = self.gh.issue(lot.numero)
        commentaires = issue.get("comments") or []
        liste = lots.marques(commentaires)
        passages = [m for m in lots.du_meneur(lots.depuis_reprise(liste))
                    if m.get("etat") in (lots.COUPE, lots.ECHEC)]
        depuis_blocage = passages[-(len(passages)):]
        fin = [m for m in liste if m.get("etat") in (lots.BLOQUE, lots.COUPE, lots.ECHEC) and
               (m.get("etat") == lots.BLOQUE or m.get("role") in ROLES_MENEURS)]
        suite = []
        for m in reversed(fin):
            if m.get("etat") == lots.BLOQUE:
                break
            suite.append(m.get("etat"))
        if suite.count(lots.COUPE) >= self.projet.coupures_max and depuis_blocage:
            self._bloquer(lot.numero, f"le {NOMS[lot.meneur]} a été coupé par son délai "
                                      f"{self.projet.coupures_max} fois pendant le plan")
            return False
        if suite.count(lots.ECHEC) >= lots.ECHECS_MAX:
            self._bloquer(lot.numero, f"le {NOMS[lot.meneur]} a échoué {lots.ECHECS_MAX} fois à écrire son plan")
            return False
        branche = lot.branche(self.projet.prefixe_branche)
        chemin = self.depot.preparer(lot.numero if chantier is None else chantier, branche)
        session, connue = self._session(lot, liste)
        decisions = tuple(lots.decisions_du_lot(commentaires, self.projet.proprietaire))
        appel = agents_mod.Appel(
            role=lot.meneur, lecture_seule=True, session=session, reprendre=connue,
            consigne=consignes.plan(self.projet, lot, decisions), schema=consignes.SCHEMA_PLAN,
            suite=("Ton passage précédent a été coupé par son délai. Ne relis pas tout : rends ton plan maintenant, "
                   "d'après ce que tu as déjà lu." + consignes._decisions(decisions)),
            jours_max=self.projet.jours_max)
        res = self._invoquer(lot.meneur, appel, chemin, lot=lot.numero)
        nom = NOMS[lot.meneur]
        if res.attente:
            self.noter(lot.numero, "attente", f"{nom} : {res.raison}")
            if marquer_attente:
                self.marquer_attente(lot, None, f"aucun agent n'a pu répondre : {res.raison}")
            return True
        if res.coupe:
            self.gh.commenter_issue(lot.numero, f"🤖 **{nom}** ({res.agent}) : coupé par son délai pendant le plan "
                                                f"({self.projet.delai(lot.meneur)} s). Sa session reprend au tour "
                                                f"suivant.\n\n{marque(**self._champs(lot.meneur, res, etat=lots.COUPE))}")
            self.noter(lot.numero, f"{nom} coupé", "pendant le plan", str(res.agent))
            return True
        sortie = res.sortie or {}
        decision = sortie.get("decision") if res.reussi else ""
        if decision == "question" and (question := Question.de(sortie.get("question"))) is not None:
            self.gh.commenter_issue(lot.numero, f"🤖 **{nom}** ({res.agent}) pose une question avant son plan.\n\n"
                                                f"{marque(**self._champs(lot.meneur, res, etat='question'))}")
            self._bloquer(lot.numero, f"question du {nom} : {question.texte}", question=question)
            return True
        if decision == "refus":
            self.gh.commenter_issue(lot.numero, f"🤖 **{nom}** ({res.agent}) refuse la fiche.\n\n"
                                                f"{marque(**self._champs(lot.meneur, res, etat='refus'))}")
            self._bloquer(lot.numero, f"le {nom} refuse la fiche : {sortie.get('raison') or 'sans raison donnée'}")
            return True
        etapes = [e for e in sortie.get("etapes") or [] if isinstance(e, dict) and e.get("titre")]
        if decision != "plan" or not etapes:
            raison = f"code {res.code}" if not res.reussi else "plan illisible ou sans étape"
            self.gh.commenter_issue(lot.numero, f"🤖 **{nom}** ({res.agent or '—'}) n'a pas rendu de plan ({raison})."
                                                f"\n\n```\n{_extrait(res.texte, 20)}\n```\n\n"
                                                f"{marque(**self._champs(lot.meneur, res, etat=lots.ECHEC))}")
            self.noter(lot.numero, f"{nom} en échec", raison, str(res.agent or ""))
            return True
        # Le plan ne change aucun fichier : ce qui traînerait est retiré.
        restes = self.depot.changements(chemin)
        if restes:
            self.depot.annuler(chemin, restes)
        prevus = {t["fichier"]: t["pourquoi"] for t in sortie.get("tests_a_changer") or []
                  if isinstance(t, dict) and t.get("fichier")}
        sha = self.depot.enregistrer(chemin, f"Lot #{lot.numero} — le plan : {lot.titre}\n\nÉcrit par {res.agent}.",
                                     vide=True)
        self.depot.pousser(chemin, branche)
        numero_pr = self.gh.creer_pr(branche, self.projet.branche_base, f"Lot #{lot.numero} — {lot.titre}",
                                     corps_de_pr(lot, self.projet, etapes, set(), prevus), brouillon=True)
        resume = f"\n\n{sortie['resume'].strip()}" if (sortie.get("resume") or "").strip() else ""
        self.gh.commenter_pr(numero_pr, f"🤖 **{nom}** ({res.agent}) — le plan, en {len(etapes)} étape(s).{resume}\n\n"
                             + marque(**self._champs(lot.meneur, res, etat=lots.PLAN, etapes=len(etapes),
                                                     detail=etapes, tests_prevus=prevus, sha=sha)))
        self.noter(lot.numero, "plan écrit", f"PR #{numero_pr}, {len(etapes)} étape(s)", str(res.agent))
        return True

    # ------------------------------------------------------- les passages
    def passage(self, lot: Lot, pr: dict, action: lots.Action, liste: list[dict], *,
                chantier: str | int | None = None, photographe: Photographe | None = None,
                marquer_attente: bool = False) -> bool:
        """Un passage du meneur dans sa session reprise : une étape du plan,
        une correction (CI rouge, relecture), ou un conflit avec la base.

        `photographe` regarde la révision poussée quand le plan est fini (la
        carte du monde par défaut ; Unity sur le PC) ; ce qu'il voit entre
        dans le compte rendu. `marquer_attente` : sur le PC, une attente
        s'écrit sur la PR, sinon le pilote du VPS ne la voit pas."""
        numero_pr, branche = pr["number"], lot.branche(self.projet.prefixe_branche)
        plan = lots.plan_du_lot(liste) or {}
        etapes = plan.get("detail") or []
        faites = lots.etapes_faites(liste)
        chemin = self.depot.preparer(lot.numero if chantier is None else chantier, branche)
        commentaires = self.gh.issue(lot.numero).get("comments") or []
        decisions = tuple(lots.decisions_du_lot(commentaires, self.projet.proprietaire))
        siens = lots.du_meneur(liste)
        coupee = bool(siens) and siens[-1].get("etat") == lots.COUPE
        conflits: list[str] = []
        if action.nom == "conflit":
            conflits = self.depot.fusionner_base(chemin)
            if not conflits:
                self.depot.pousser(chemin, branche)
                self.noter(lot.numero, "base fusionnée", "sans conflit")
                return False
            tache = consignes.conflit(branche, self.projet.branche_base, conflits)
            neuve = consignes.suite_neuve(self.projet, lot, etapes, tache, decisions)
        else:
            self._mettre_a_jour(chemin, branche, lot.numero)
            if action.nom == "etape":
                neuve, tache = consignes.etape(self.projet, lot, action.essai, etapes, decisions, coupee)
            else:
                if action.nom == "corriger_ci":
                    tache = consignes.correction_ci(self._dernier_resume(pr))
                else:
                    revue, arbitrage = self._derniere_revue(pr)
                    tache = consignes.correction_relecture(revue, arbitrage)
                neuve = consignes.suite_neuve(self.projet, lot, etapes, tache, decisions)
                tache += consignes._decisions(decisions)
        session, connue = self._session(lot, lots.marques(commentaires) + liste)
        appel = agents_mod.Appel(
            role=lot.meneur, lecture_seule=False, session=session, reprendre=connue, consigne=neuve, suite=tache,
            schema=consignes.SCHEMA_PASSAGE, jours_max=self.projet.jours_max,
            sous_agents=consignes.sous_agents(self.projet) if lot.meneur == CHEF else None)
        res = self._invoquer(lot.meneur, appel, chemin, lot=lot.numero)
        nom = NOMS[lot.meneur]
        quoi = {"etape": f"étape {action.essai}", "corriger_ci": f"correction {action.essai} (CI rouge)",
                "corriger_relecture": f"correction {action.essai} (relecture)", "conflit": "conflit avec la base"}[action.nom]
        if res.attente:
            if conflits:
                self.depot.git_code("merge", "--abort", cwd=chemin)
            self.noter(lot.numero, "attente", f"{nom} : {res.raison}")
            if marquer_attente:
                self.marquer_attente(lot, numero_pr, f"aucun agent n'a pu répondre : {res.raison}")
            return True
        interdits = [f for f in self.depot.changements(chemin) if self.projet.interdit(f)]
        if interdits:
            self.depot.annuler(chemin, interdits)
        retires = ("\n\n⚠️ Changements retirés, hors de portée d'un lot : "
                   + ", ".join(f"`{f}`" for f in interdits)) if interdits else ""
        sortie = res.sortie or {}
        etat = sortie.get("etat") if res.reussi else ""
        changes = bool(self.depot.changements(chemin))
        if conflits and (not res.reussi or self.depot.marqueurs_restants(chemin, conflits)):
            self.depot.git_code("merge", "--abort", cwd=chemin)
            changes = False
        if res.coupe:
            # Un passage coupé a souvent écrit du code : il part, marqué
            # inachevé, et la session le reprendra où elle en était.
            sha = self._enregistrer(chemin, branche, lot, f"{quoi}, coupée par le délai", res.agent, conflits) \
                if changes else ""
            self.gh.commenter_pr(numero_pr, f"🤖 **{nom}** ({res.agent}) — {quoi} : coupé par son délai "
                                            f"({self.projet.delai(lot.meneur)} s)"
                                            + (f", révision `{sha[:7]}` poussée" if sha else ", rien à pousser")
                                            + f". Sa session reprend au tour suivant.{retires}\n\n"
                                            + marque(**self._champs(lot.meneur, res, etat=lots.COUPE, **({"sha": sha} if sha else {}))))
            self.noter(lot.numero, f"{nom} coupé", quoi, str(res.agent))
            return True
        if etat not in ("faite", "a_poursuivre", "question", "conteste"):
            raison = f"code {res.code}" if not res.reussi else "compte rendu illisible"
            self.gh.commenter_pr(numero_pr, f"🤖 **{nom}** ({res.agent or '—'}) — {quoi} : échec ({raison}).\n\n"
                                            f"```\n{_extrait(res.texte, 40)}\n```\n\n"
                                            f"{marque(**self._champs(lot.meneur, res, etat=lots.ECHEC))}")
            self.noter(lot.numero, f"{nom} en échec", f"{quoi} — {raison}", str(res.agent or ""))
            return True
        compte_rendu = _extrait((sortie.get("compte_rendu") or "").strip())
        joues = "".join(f"\n- `{t.get('commande', '')}` : {t.get('resultat', '')}" for t in sortie.get("tests_joues") or []
                        if isinstance(t, dict))
        confie = "".join(f"\n- {c}" for c in sortie.get("confie") or [] if isinstance(c, str))
        corps = (compte_rendu + (f"\n\n**Tests joués**{joues}" if joues else "")
                 + (f"\n\n**Confié au développeur**{confie}" if confie else "") + retires)
        declares = {t["fichier"]: t["pourquoi"] for t in sortie.get("tests_changes") or []
                    if isinstance(t, dict) and t.get("fichier")}
        if etat == "conteste" or (action.nom == "corriger_relecture" and etat == "faite" and not changes):
            # Le meneur conteste la relecture, ou ne change rien pour elle : le CTO tranchera.
            contestes = "".join(f"\n- {c.get('constat', '')} — {c.get('pourquoi', '')}" for c in sortie.get("conteste") or []
                                if isinstance(c, dict))
            sha = self._enregistrer(chemin, branche, lot, quoi, res.agent, conflits) if changes else ""
            self.gh.commenter_pr(numero_pr, f"🤖 **{nom}** ({res.agent}) conteste la relecture.\n\n{corps}"
                                            + (f"\n\n**Ce qu'il conteste**{contestes}" if contestes else "") + "\n\n"
                                            + marque(**self._champs(lot.meneur, res, etat=lots.REPONSE,
                                                                    **({"sha": sha} if sha else {}))))
            self.noter(lot.numero, f"{nom} : conteste la relecture", "", str(res.agent))
            return True
        sha = self._enregistrer(chemin, branche, lot, quoi, res.agent, conflits) if changes else self.depot.tete(chemin)
        fini = etat == "faite"
        if action.nom == "etape":
            champs = {"etat": lots.ETAPE, "etape": action.essai, "fini": fini}
            if fini:
                faites = faites | {action.essai}
        elif action.nom == "conflit":
            champs = {"etat": "conflit"}
        else:
            champs = {"etat": lots.CORRECTION, "cause": "ci" if action.nom == "corriger_ci" else "relecture"}
        tout_fait = bool(etapes) and len(faites) >= len(etapes)
        vu = Photos()
        self.capture = str(sortie.get("capture") or next((m["capture"] for m in reversed(liste) if m.get("capture")), ""))
        if self.capture:
            champs["capture"] = self.capture
        if tout_fait and changes and fini:
            vu = (photographe or self._photographier)(chemin, lot, sha)
        photos = "".join(f"\n\n📷 ![capture du lot #{lot.numero}]({url})" for url in vu.urls)
        note = f"\n\n{vu.note}" if vu.note else ""
        etat_dit = {"faite": "faite", "a_poursuivre": "à poursuivre", "question": "arrêtée sur une question"}[etat]
        self.gh.commenter_pr(numero_pr, f"🤖 **{nom}** ({res.agent}) — {quoi} : {etat_dit}"
                                        + (f", révision `{sha[:7]}`" if changes else ", sans changement de fichier")
                                        + f".\n\n{corps}{note}{photos}\n\n"
                                        + marque(**self._champs(lot.meneur, res, sha=sha, tests_changes=declares,
                                                                **champs, **vu.marque)))
        self._ecrire_la_pr(lot, numero_pr, chemin, liste, etapes, faites, declares)
        if tout_fait and pr.get("isDraft"):
            self.gh.pr_prete(numero_pr)
        self.noter(lot.numero, f"{nom} : {quoi} {etat_dit}", f"PR #{numero_pr}", str(res.agent))
        if etat == "question" and (question := Question.de(sortie.get("question"))) is not None:
            self._bloquer(lot.numero, f"question du {nom} : {question.texte}", numero_pr, question=question)
        return True

    def _enregistrer(self, chemin: Path, branche: str, lot: Lot, quoi: str, agent, conflits: list[str]) -> str:
        if conflits:
            sha = self.depot.conclure_fusion(chemin)
        else:
            sha = self.depot.enregistrer(chemin, f"Lot #{lot.numero} — {quoi}\n\nÉcrit par {agent}.")
        self.depot.pousser(chemin, branche)
        return sha

    def _ecrire_la_pr(self, lot: Lot, numero_pr: int, chemin: Path, liste: list[dict], etapes: list[dict],
                      faites: set[int], declares: dict[str, str]) -> None:
        """Le texte de la PR suit le lot : les étapes cochées, et chaque test
        changé avec sa raison. Un test modifié sans raison donnée y est dit."""
        plan = lots.plan_du_lot(liste) or {}
        changes = dict(plan.get("tests_prevus") or {})
        for m in lots.du_meneur(liste):
            changes.update(m.get("tests_changes") or {})
        changes.update(declares)
        try:
            modifies = lots.tests_changes(self.depot.etats_du_lot(chemin))
            self.gh.corps_de_pr(numero_pr, corps_de_pr(lot, self.projet, etapes, faites,
                                                       {f: p for f, p in changes.items()}, modifies))
        except (GitHubErreur, DepotErreur) as e:
            self.noter(lot.numero, "erreur", f"texte de la PR non mis à jour : {e}")

    def _mettre_a_jour(self, chemin: Path, branche: str, numero: int | str) -> None:
        """La branche du lot reçoit la base avant que le meneur travaille : il
        ne peut pas fusionner lui-même. Un conflit attend son propre passage."""
        if not self.depot.en_retard(chemin):
            return
        if self.depot.fusionner_base(chemin):
            self.depot.git_code("merge", "--abort", cwd=chemin)
            self.noter(numero, "base non fusionnée", "conflit : le meneur le résoudra")
            return
        self.depot.pousser(chemin, branche)
        self.noter(numero, "base fusionnée", "avant le passage")

    def _photographier(self, chemin: Path, lot: Lot, sha: str) -> Photos:
        return Photos(urls=captures.photographier_lot(self.depot, self.gh.depot, chemin, lot.numero, sha,
                                                      f"{self.maintenant():%Y-%m-%d}"))

    # -------------------------------------------------------------- la CI
    def _erreur_ci(self, numero_pr: int) -> str:
        try:
            table = self.gh.gh("pr", "checks", str(numero_pr), "-R", self.gh.depot)
        except GitHubErreur as e:
            table = str(e)  # `gh pr checks` rend 1 quand un contrôle échoue
        morceaux = []
        for rouge in traces.rouges(table):
            morceaux.append(f"## {rouge.nom}\n{traces.lire(rouge) if rouge.travail else rouge.description}")
        return "\n\n".join(morceaux) or table

    def _resumer_ci(self, lot: Lot, pr: dict) -> bool:
        """Le lecteur résume le journal d'une CI rouge avant que le meneur
        corrige. S'il ne répond pas ou se trompe de forme, le journal brut
        part au meneur : le lot n'attend pas un résumé."""
        numero_pr, tete = pr["number"], pr.get("headRefOid") or ""
        brut = self._erreur_ci(numero_pr)
        appel = agents_mod.Appel(role=LECTEUR, lecture_seule=True, sans_outil=True,
                                 consigne=consignes.resume_ci(brut), schema=consignes.SCHEMA_RESUME_CI)
        res = self._invoquer(LECTEUR, appel, self.depot.racine, lot=lot.numero)
        sortie = res.sortie if res.reussi else None
        if sortie and (sortie.get("resume") or sortie.get("echecs")):
            echecs = "".join(
                f"\n- **{e.get('travail', '?')}**" + (f" · `{e['test']}`" if e.get("test") else "")
                + (f" · `{e['fichier']}`" + (f":{e['ligne']}" if e.get("ligne") else "") if e.get("fichier") else "")
                + f"\n  ```\n  {str(e.get('erreur', '')).strip()[:1500]}\n  ```"
                for e in sortie.get("echecs") or [] if isinstance(e, dict))
            texte = f"{(sortie.get('resume') or '').strip()}\n{echecs}"
            qui = f"**lecteur** ({res.agent})"
        else:
            texte = f"Le lecteur n'a pas rendu de résumé ; le journal, tel quel :\n\n```\n{_extrait(brut, 80)}\n```"
            qui = "**pilote**"
        self.gh.commenter_pr(numero_pr, f"🤖 {qui} : la CI est rouge sur `{tete[:7]}`.\n\n{texte}\n\n"
                                        + marque(**self._champs(LECTEUR, res, etat="resume", sha=tete)))
        self.noter(lot.numero, "CI résumée", f"PR #{numero_pr}", str(res.agent or "pilote"))
        return not res.attente

    def _dernier_resume(self, pr: dict) -> str:
        tete = pr.get("headRefOid") or ""
        for c in reversed(pr.get("comments") or []):
            if any(m.get("role") == LECTEUR and m.get("sha") == tete for m in lots.marques([c])):
                return lots.sans_marque(c.get("body") or "")
        return ""

    def _derniere_revue(self, pr: dict) -> tuple[str, str]:
        """La dernière revue « CORRIGER », et l'arbitrage du CTO s'il y en a eu un depuis."""
        revue, arbitrage = "", ""
        for c in pr.get("comments") or []:
            faites = lots.marques([c])
            if any(m.get("verdict") == "CORRIGER" for m in faites):
                revue, arbitrage = lots.sans_marque(c.get("body") or ""), ""
            elif any(m.get("role") == CTO and m.get("etat") == "arbitrage" for m in faites):
                arbitrage = lots.sans_marque(c.get("body") or "")
        return revue, arbitrage

    def _attendre_la_base(self, lot: Lot, pr: dict, branche: str, liste: list[dict]) -> bool:
        """Une CI rouge sur les seuls travaux que la base de la PR avait déjà
        rouges : le meneur n'y peut rien. Tant que master les porte, le lot
        attend, sans compter d'essai, et la PR le dit une fois ; dès que
        master les a guéris, la branche le reçoit et la CI repart. Vrai quand
        le meneur n'a pas à passer."""
        numero_pr, tete = pr["number"], pr.get("headRefOid") or ""
        agregat = "tests"
        travaux = travaux_du_workflow(pr, AGREGATS[agregat])
        rouges = {n for n, t in travaux.items() if t["etat"] == "rouge" and n != agregat}
        if not rouges or not tete:
            return False
        base = self.projet.branche_base
        try:
            depart = self.gh.base_de_fusion(base, tete)
            quoi = lots.rouge_de_la_base(rouges, self.gh.travaux_du_commit(depart), self.gh.travaux_du_commit(base))
        except GitHubErreur as e:
            # Une base illisible ne retient pas le lot : le meneur corrige.
            self.noter(lot.numero, "base illisible", str(e))
            return False
        if not quoi:
            return False
        noms = ", ".join(f"`{n}`" for n in sorted(rouges))
        if quoi == "attendre":
            dit = any(m.get("role") == "pilote" and m.get("etat") == lots.ETAT_BASE_ROUGE and m.get("sha") == tete
                      for m in liste)
            if not dit:
                self.gh.commenter_pr(numero_pr, f"🤖 **pilote** : {noms} déjà rouge sur `{base}` (`{depart[:7]}`), "
                                                "d'où part cette PR : le lot n'y est pour rien. Il attend que "
                                                f"`{base}` soit réparé, sans compter d'essai.\n\n"
                                                f"{marque(role='pilote', etat=lots.ETAT_BASE_ROUGE, sha=tete)}")
            self.noter(lot.numero, "attendre_base", f"PR #{numero_pr} — {noms} rouge sur `{base}` aussi")
            return True
        chemin = self.depot.preparer(lot.numero, branche)
        if self.depot.fusionner_base(chemin):
            self.depot.git_code("merge", "--abort", cwd=chemin)
            return False
        self.depot.pousser(chemin, branche)
        self.gh.commenter_pr(numero_pr, f"🤖 **pilote** : {noms} était rouge sur `{base}` (`{depart[:7]}`), d'où "
                                        f"partait cette PR, et `{base}` l'a réparé depuis : la branche le reçoit, "
                                        "la CI repart, sans compter d'essai.")
        self.noter(lot.numero, "base fusionnée", f"PR #{numero_pr} — {noms} réparé sur `{base}`")
        return True

    def _rejouer_une_panne(self, lot: Lot, pr: dict, liste: list[dict]) -> bool:
        """Une CI rouge dont tous les travaux rouges sont tombés en se
        préparant : le meneur n'y peut rien. Le pilote les rejoue, sans
        compter d'essai, `lots.PANNES_MAX` fois au plus ; au-delà il bloque le
        lot en nommant l'étape. Vrai quand le meneur n'a pas à passer."""
        numero_pr, tete = pr["number"], pr.get("headRefOid") or ""
        tous = controles_de_la_pr(pr)
        rouges = {n: t for n, t in tous.items() if t["etat"] == "rouge" and n not in AGREGATS}
        if not rouges:
            return False
        workflows = {t["workflow"] for t in rouges.values()}
        en_cours = any(t["etat"] == "attente" and t["workflow"] in workflows for t in tous.values())
        rejeux = lots.rejeux_de_panne(liste)
        en_vol = lots.rejeu_de_panne_en_vol(
            [t["date"] for t in rouges.values()], en_cours, rejeux,
            heures_depuis_rejeu=self._heures_depuis_pilote(liste, lots.ETAT_REJEU_PANNE))
        if en_vol == "attendre":
            self.noter(lot.numero, "attendre_ci", f"PR #{numero_pr} — panne de la CI rejouée : le pilote attend ce "
                                                  "qu'elle rend")
            return True
        if en_vol == "abandonner":
            return False
        # Chaque travail rouge doit être une panne : un seul contrôle qui a
        # vraiment échoué, et c'est au meneur.
        pannes: dict[str, str] = {}
        runs: list[int] = []
        for nom, t in rouges.items():
            trouve = _TRAVAIL.search(t["adresse"])
            if trouve is None:
                return False
            try:
                etape = lots.panne_d_infrastructure(self.gh.etapes_du_travail(int(trouve.group(2))))
            except GitHubErreur as e:
                # Des étapes illisibles ne prouvent pas une panne : le meneur corrige.
                self.noter(lot.numero, "étapes illisibles", str(e))
                return False
            if not etape:
                return False
            pannes[nom] = etape
            if int(trouve.group(1)) not in runs:
                runs.append(int(trouve.group(1)))
        dites = ", ".join(f"`{n}` (étape « {e} »)" for n, e in sorted(pannes.items()))
        if en_cours:
            self.noter(lot.numero, "attendre_ci", f"PR #{numero_pr} — panne de la CI sur {dites} : rejouée quand "
                                                  "son run sera fini")
            return True
        if len(rejeux) >= lots.PANNES_MAX:
            self._bloquer(lot.numero, f"panne de la CI, rejouée {lots.PANNES_MAX} fois sans succès : {dites} tombe "
                                      "avant d'avoir rien contrôlé ; le lot n'a rien à corriger, c'est le workflow "
                                      "ou le service qu'il appelle", numero_pr)
            return True
        for run in runs:
            self.gh.rejouer_les_echecs(run)
        quand = self.maintenant().isoformat(timespec="seconds")
        fois = f"{len(rejeux) + 1} sur {lots.PANNES_MAX}"
        self.gh.commenter_pr(numero_pr, f"🤖 **pilote** : la CI est rouge sur {dites}, tombé avant d'avoir rien "
                                        f"contrôlé : le lot n'y est pour rien. Le travail est rejoué ({fois}), sans "
                                        "compter d'essai.\n\n"
                                        f"{marque(role='pilote', etat=lots.ETAT_REJEU_PANNE, sha=tete, quand=quand)}")
        self.noter(lot.numero, "panne rejouée", f"PR #{numero_pr} — {dites}, {fois}")
        return True

    def _rejouer_le_chronometre(self, lot: Lot, pr: dict, branche: str, liste: list[dict]) -> bool:
        """Un rouge du seul travail `chronometre` : le pilote le rejoue une
        fois avant d'appeler le meneur, sans compter d'essai. La branche reçoit
        la base si elle a bougé ; sinon le travail rouge se rejoue. Vrai quand
        le meneur n'a pas à passer."""
        numero_pr, tete = pr["number"], pr.get("headRefOid") or ""
        agregat = "tests"  # le contrôle exigé qui attend `chronometre`
        travaux = travaux_du_workflow(pr, AGREGATS[agregat])
        quoi = lots.rejeu_du_chronometre(travaux, agregat, liste,
                                         heures_depuis_rejeu=self._heures_depuis_pilote(liste, lots.ETAT_REJEU))
        if quoi == "attendre":
            self.noter(lot.numero, "attendre_ci", f"PR #{numero_pr} — `{lots.TRAVAIL_CHRONOMETRE}` rouge seul : "
                                                  "rejoué quand son run sera fini")
            return True
        if quoi != "rejouer":
            return False
        chemin = self.depot.preparer(lot.numero, branche)
        en_retard = self.depot.en_retard(chemin)
        conflits = self.depot.fusionner_base(chemin) if en_retard else []
        if en_retard and not conflits:
            self.depot.pousser(chemin, branche)
            geste = f"la branche reçoit `{self.projet.branche_base}`, qui a bougé depuis : la CI repart"
        else:
            if conflits:
                self.depot.git_code("merge", "--abort", cwd=chemin)
            run = _RUN.search(travaux[lots.TRAVAIL_CHRONOMETRE]["adresse"])
            if run is None:
                return False
            self.gh.rejouer_les_echecs(int(run.group(1)))
            geste = f"le travail est rejoué (run {run.group(1)})"
        quand = self.maintenant().isoformat(timespec="seconds")
        self.gh.commenter_pr(numero_pr, f"🤖 **pilote** : seul `{lots.TRAVAIL_CHRONOMETRE}` est rouge, et son budget "
                                        f"est au bord du bruit des runners. Une fois, {geste}, sans compter d'essai. "
                                        "S'il rougit encore, le meneur corrige.\n\n"
                                        f"{marque(role='pilote', etat=lots.ETAT_REJEU, sha=tete, quand=quand)}")
        self.noter(lot.numero, f"{lots.TRAVAIL_CHRONOMETRE} rejoué", f"PR #{numero_pr} — {geste}")
        return True

    # ------------------------------------------------------------- relire
    def _relire(self, lot: Lot, pr: dict, branche: str, liste: list[dict]) -> bool:
        """Une autre session que celle du meneur, en lecture seule, rend un
        verdict structuré : rien ne s'en perd. Le CTO relit à la place du
        relecteur un lot qui touche le cœur du moteur."""
        numero_pr, tete = pr["number"], pr["headRefOid"]
        echecs = [m for m in lots.depuis_reprise(liste)
                  if m.get("role") in (RELECTEUR, CTO) and m.get("etat") == lots.ECHEC and m.get("sha") == tete]
        if len(echecs) >= 2:
            self._bloquer(lot.numero, "la relecture a échoué deux fois sur la même révision", numero_pr)
            return False
        chemin = self.depot.preparer(lot.numero, branche)
        fichiers = self.depot.fichiers_du_lot(chemin)
        role = CTO if self.projet.touche_le_coeur(fichiers) else RELECTEUR
        plan = lots.plan_du_lot(liste) or {}
        plan_ecrit = "\n".join(f"{i}. {e.get('titre', '')} — {e.get('quoi', '')}"
                               for i, e in enumerate(plan.get("detail") or [], start=1))
        declares = dict(plan.get("tests_prevus") or {})
        for m in lots.du_meneur(liste):
            declares.update(m.get("tests_changes") or {})
        modifies = lots.tests_changes(self.depot.etats_du_lot(chemin))
        rapports = "\n\n".join(
            lots.sans_marque(c.get("body") or "") for c in pr.get("comments") or []
            if any(m.get("role") in ROLES_MENEURS and m.get("etat") in (lots.ETAPE, lots.CORRECTION, lots.REPONSE)
                   for m in lots.marques([c])))
        lisibles, illisibles = self._lfs_du_lot(chemin, fichiers)
        decisions = tuple(lots.decisions_du_lot(self.gh.issue(lot.numero).get("comments") or [],
                                                self.projet.proprietaire))
        consigne = consignes.relecteur(
            self.projet, lot, url=pr.get("url", ""), sha=tete, plan_ecrit=plan_ecrit,
            tests_declares="\n".join(f"- `{f}` : {p}" for f, p in sorted(declares.items())),
            tests_non_declares=tuple(f for f in modifies if f not in declares), rapports=rapports,
            lfs_lisibles=tuple(lisibles), lfs_illisibles=tuple(illisibles), decisions=decisions, cto=role == CTO)
        appel = agents_mod.Appel(role=role, lecture_seule=True, consigne=consigne,
                                 schema=consignes.SCHEMA_RELECTURE, jours_max=self.projet.jours_max)
        res = self._invoquer(role, appel, chemin, lot=lot.numero)
        nom = NOMS[role]
        if res.attente:
            self.noter(lot.numero, "attente", f"{nom} : {res.raison}")
            return True
        sortie = res.sortie if res.reussi else None
        if not sortie or sortie.get("verdict") not in ("ACCEPTE", "CORRIGER"):
            raison = ("coupé par son délai" if res.coupe else f"code {res.code}" if not res.reussi
                      else "verdict illisible")
            self.gh.commenter_pr(numero_pr, f"🤖 **{nom}** ({res.agent}) : relecture sans verdict ({raison}).\n\n"
                                            f"{marque(**self._champs(role, res, etat=lots.ECHEC, sha=tete))}")
            self.noter(lot.numero, f"{nom} en échec", raison, str(res.agent))
            return True
        constats = [c for c in sortie.get("constats") or [] if isinstance(c, dict) and c.get("quoi")]
        bloquants = [c for c in constats if c.get("gravite") == "bloquant"]
        verdict = sortie["verdict"]
        # Un « ACCEPTE » qui porte un constat bloquant, une promesse non tenue
        # ou un test changé sans raison se contredit : c'est « CORRIGER ».
        incoherent = verdict == "ACCEPTE" and (bloquants or sortie.get("promesse_joueur_tenue") is False
                                               or sortie.get("tests_changes_justifies") is False)
        if incoherent:
            verdict = "CORRIGER"
        dits = "".join(f"\n- **{c.get('gravite', 'mineur')}** · `{c.get('fichier', '?')}`"
                       + (f":{c['ligne']}" if c.get("ligne") else "") + f" — {c['quoi']}" for c in constats)
        rejoues = "".join(f"\n- `{t.get('commande', '')}` : {t.get('resultat', '')}" for t in sortie.get("tests_rejoues") or []
                          if isinstance(t, dict))
        oui = {True: "oui", False: "non", None: "non dit"}
        texte = (f"## Relecture — {verdict}\n\nRévision `{tete[:7]}` · relu par le {nom} ({res.agent})\n\n"
                 f"{(sortie.get('resume') or '').strip()}\n\n"
                 f"**Constats**{dits or chr(10) + 'Aucun.'}\n\n"
                 f"La promesse au joueur est tenue : {oui[sortie.get('promesse_joueur_tenue')]} · "
                 f"les tests changés sont justifiés : {oui[sortie.get('tests_changes_justifies')]}"
                 + (f"\n\n**Tests rejoués**{rejoues}" if rejoues else "")
                 + ("\n\n⚠️ Le verdict rendu était « ACCEPTE », mais il porte un constat bloquant, une promesse non "
                    "tenue ou un test changé sans raison : le pilote le lit « CORRIGER »." if incoherent else ""))
        self.gh.commenter_pr(numero_pr, f"{texte}\n\n" + marque(**self._champs(role, res, verdict=verdict, sha=tete,
                                                                               constats=len(bloquants))))
        if verdict == "ACCEPTE":
            self.gh.fusion_auto(numero_pr, tete)
        self.noter(lot.numero, f"relecture {verdict}", f"PR #{numero_pr}", str(res.agent))
        return True

    def _arbitrer(self, lot: Lot, pr: dict, branche: str, liste: list[dict]) -> bool:
        """Le meneur conteste la relecture : le CTO tranche. Le meneur a
        raison : le lot est accepté sur cette révision. Le relecteur a raison :
        le meneur corrige, avec la consigne du CTO."""
        numero_pr, tete = pr["number"], pr["headRefOid"]
        chemin = self.depot.preparer(lot.numero, branche)
        revue, _ = self._derniere_revue(pr)
        contestation = next((lots.sans_marque(c.get("body") or "") for c in reversed(pr.get("comments") or [])
                             if any(m.get("etat") == lots.REPONSE for m in lots.marques([c]))), "")
        appel = agents_mod.Appel(role=CTO, lecture_seule=True, schema=consignes.SCHEMA_ARBITRAGE,
                                 consigne=consignes.arbitrage(self.projet, lot, revue=revue, contestation=contestation),
                                 jours_max=self.projet.jours_max)
        res = self._invoquer(CTO, appel, chemin, lot=lot.numero)
        if res.attente:
            self.noter(lot.numero, "attente", f"CTO : {res.raison}")
            return True
        sortie = res.sortie if res.reussi else None
        pour = (sortie or {}).get("decision")
        if pour not in ("meneur", "relecteur"):
            # Sans arbitrage lisible, la relecture tient : le meneur corrige.
            pour, sortie = "relecteur", {"pourquoi": "l'arbitrage n'a rien rendu de lisible : la relecture tient",
                                         "consigne": ""}
        pourquoi = (sortie.get("pourquoi") or "").strip()
        if pour == "meneur":
            self.gh.commenter_pr(numero_pr, f"## Relecture — ACCEPTE\n\nRévision `{tete[:7]}` · tranché par le CTO "
                                            f"({res.agent}) : le meneur a raison.\n\n{pourquoi}\n\n"
                                            + marque(**self._champs(CTO, res, verdict="ACCEPTE", sha=tete,
                                                                    etat="arbitrage", pour="meneur")))
            self.gh.fusion_auto(numero_pr, tete)
        else:
            consigne = (sortie.get("consigne") or "").strip()
            self.gh.commenter_pr(numero_pr, f"🤖 **CTO** ({res.agent}) tranche : le relecteur a raison.\n\n{pourquoi}"
                                            + (f"\n\n**Consigne** : {consigne}" if consigne else "") + "\n\n"
                                            + marque(**self._champs(CTO, res, etat="arbitrage", pour="relecteur")))
        self.noter(lot.numero, "arbitrage du CTO", f"pour le {pour}", str(res.agent))
        return True

    def _lfs_du_lot(self, chemin: Path, fichiers: list[str]) -> tuple[list[str], list[str]]:
        """Les fichiers LFS du lot, rendus lisibles dans `.atelier/lfs/` du
        chantier. Un échec se dit au relecteur ; il ne bloque rien."""
        return lfs.rendre_lisibles(chemin, fichiers, self.gh.depot, telechargeur=self.lfs_telechargeur)

    # ---------------------------------------------------------- débloquer
    def _debloquer_un_lot(self, vue: "_Vue") -> bool:
        """Un lot bloqué, regardé par le CTO : un seul par tour."""
        for lot in sorted(vue.ouvertes, key=lambda l: l.numero):
            if lot.etat != "bloque" or not lot.est_un_lot:
                continue
            if not self.verrous.prendre(_verrou_du_lot(lot.numero)):
                continue
            try:
                issue = self.gh.issue(lot.numero)
                lot = Lot.de(issue)
                commentaires = issue.get("comments") or []
                if lot.etat != "bloque" or not lots.deblocage_a_faire(commentaires):
                    continue
                return self._debloquer(lot, commentaires)
            except (GitHubErreur, DepotErreur) as e:
                self.noter(lot.numero, "erreur", str(e))
            finally:
                self._lacher_lot(lot.numero)
        return False

    def _debloquer(self, lot: Lot, commentaires: list[dict]) -> bool:
        """Le CTO lit le lot arrêté et décide : trancher la question, relancer
        avec une consigne, redécouper, reporter à samedi, ou, pour
        l'irréversible, l'argent et les droits seulement, prévenir le
        propriétaire. Sa décision est écrite en entier — la réponse, ses
        raisons, ses bornes — et suit le lot."""
        _, blocage = lots.dernier_blocage(commentaires)
        question = Question.de(blocage) if blocage.get("question") else None
        relances = lots.relances_du_cto(commentaires)
        branche = lot.branche(self.projet.prefixe_branche)
        resume = self.gh.pr_de_branche(branche)
        pr = self.gh.pr(resume["number"]) if resume and resume.get("state") == "OPEN" else None
        erreur_ci = self._erreur_ci(pr["number"]) if pr is not None and etat_des_controles(pr)[0] == "rouge" else ""
        chemin = self.depot.preparer(lot.numero, branche)
        dit_issue = "\n\n".join(f"{(c.get('author') or {}).get('login', '?')} : "
                                 f"{_extrait(lots.sans_marque(c.get('body') or ''), 25)}" for c in commentaires[-8:])
        dit_pr = "\n\n".join(_extrait(lots.sans_marque(c.get("body") or ""), 40)
                              for c in (pr.get("comments") or [])[-12:]) if pr else ""
        consigne = consignes.deblocage(self.projet, lot, raison=blocage.get("raison") or "", question=question,
                                       issue=dit_issue, pr=dit_pr, erreur_ci=erreur_ci, relances=relances,
                                       boucle=tuple(blocage.get("boucle") or ()))
        appel = agents_mod.Appel(role=CTO, lecture_seule=True, consigne=consigne,
                                 schema=consignes.schema_deblocage(self.projet), jours_max=self.projet.jours_max)
        res = self._invoquer(CTO, appel, chemin, lot=lot.numero)
        if res.attente:
            self.noter(lot.numero, "attente", f"CTO : {res.raison}")
            return True
        sortie = (res.sortie if res.reussi else None) or {}
        decision = sortie.get("decision")
        pourquoi = (sortie.get("pourquoi") or "").strip()
        bornes = (sortie.get("bornes") or "").strip()
        a_revoir = (sortie.get("a_revoir_samedi") or "").strip()
        numero_pr = pr["number"] if pr else None
        suite = ((f"\n\nPourquoi : {pourquoi}" if pourquoi else "") + (f"\n\nBornes : {bornes}" if bornes else "")
                 + (f"\n\n**À revoir samedi** : {a_revoir}" if a_revoir else ""))
        champs = {"etat": lots.DECISION, "pourquoi": pourquoi, "bornes": bornes, "a_revoir": a_revoir}
        retirer = [int(n) for n in sortie.get("dependances_a_retirer") or [] if isinstance(n, int)]

        def repartir() -> None:
            if retirer:
                self.gh.corps_de(lot.numero, lots.sans_dependances(lot.corps, retirer))
            self.gh.etiqueter(lot.numero, ["pret"], ["bloque"])

        lettre = str(sortie.get("reponse") or "").strip().upper()
        if decision == "trancher" and question is not None and question.reponse(lettre):
            reponse = f"{lettre} — {question.reponse(lettre)}"
            self.gh.commenter_issue(lot.numero, f"🤖 **CTO** ({res.agent}) tranche la question, sans attendre le "
                                                f"propriétaire.\n\n**{question.texte}**\n\nRéponse : **{reponse}**{suite}"
                                                "\n\nLe lot continue. Pour une autre décision : écris-la ici.\n\n"
                                    + marque(**self._champs(CTO, res, decision="trancher", question=question.texte,
                                                            reponse=reponse, **champs)))
            repartir()
            self.noter(lot.numero, "question tranchée par le CTO", reponse[:160], str(res.agent))
        elif decision == "relancer" and (sortie.get("consigne") or "").strip() \
                and relances < self.projet.deblocages_max:
            consigne_cto = sortie["consigne"].strip()
            self.gh.commenter_issue(lot.numero, f"🤖 **CTO** ({res.agent}) relance le lot "
                                                f"({relances + 1}/{self.projet.deblocages_max}).\n\n"
                                                f"**Consigne** : {consigne_cto}{suite}\n\n"
                                    + marque(**self._champs(CTO, res, decision="relancer", consigne=consigne_cto,
                                                            **champs)))
            repartir()
            self.noter(lot.numero, "relancé par le CTO", "remis pret", str(res.agent))
        elif decision == "redecouper" and (fiches := [f for f in sortie.get("fiches") or []
                                                      if isinstance(f, dict) and f.get("titre")]):
            crees = self.ouvrir_les_fiches(fiches, lot.palier_titre, decoupe_de=lot.numero)
            liste = ", ".join(f"#{n}" for n in crees)
            self.gh.commenter_issue(lot.numero, f"🤖 **CTO** ({res.agent}) redécoupe le lot en {liste}.{suite}\n\n"
                                    + marque(**self._champs(CTO, res, decision="redecouper", par=CTO, **champs)))
            self.gh.fermer_issue(lot.numero, None, abandon=True)
            if numero_pr is not None:
                self.gh.fermer_pr(numero_pr, f"Fermée par le pilote : le CTO a redécoupé le lot #{lot.numero} en "
                                             f"{liste}. La branche garde le travail d'avant.")
            self.depot.retirer(lot.numero)
            self.noter(lot.numero, "redécoupé par le CTO", liste, str(res.agent))
        elif decision == "proprietaire":
            self.gh.commenter_issue(lot.numero, f"🤖 **CTO** ({res.agent}) : @{self.projet.proprietaire}, ce lot "
                                                "demande ta décision (l'irréversible, l'argent ou les droits)."
                                                f"{suite}\n\nÉcris ta réponse ici : le lot repartira avec elle.\n\n"
                                    + marque(**self._champs(CTO, res, decision="proprietaire", par=CTO, **champs)))
            self.noter(lot.numero, "laissé au propriétaire", pourquoi[:160], str(res.agent))
        elif decision == "reporter" or decision in ("relancer", "trancher", "redecouper"):
            # Une décision que le lot ne peut pas recevoir (une lettre que la
            # question ne propose pas, une relance de trop, une découpe sans
            # fiche) vaut report : rien n'attend le propriétaire en semaine.
            dit = a_revoir or pourquoi or "le lot ne peut pas aboutir cette semaine"
            self.gh.commenter_issue(lot.numero, f"🤖 **CTO** ({res.agent}) reporte le lot à samedi.{suite}\n\n"
                                    + marque(**self._champs(CTO, res, decision="reporter", par=CTO,
                                                            **(champs | {"a_revoir": dit}))))
            self.noter(lot.numero, "reporté à samedi par le CTO", dit[:160], str(res.agent))
        else:
            raison = ("coupé par son délai" if res.coupe else f"code {res.code}" if not res.reussi
                      else "décision illisible")
            self.gh.commenter_issue(lot.numero, f"🤖 **CTO** ({res.agent or '—'}) : pas de décision ({raison}).\n\n"
                                    + marque(**self._champs(CTO, res, etat=lots.ECHEC)))
            self.noter(lot.numero, "CTO en échec", raison, str(res.agent or ""))
        return True

    def ouvrir_les_fiches(self, fiches: list[dict], palier_titre: str | None, *, decoupe_de: int | None = None,
                          urgent: bool = False, en_plus: str = "") -> list[int]:
        """Ouvre une issue par fiche : chacune avec sa piste, sa machine, son
        meneur, et les lots de la même liste qu'elle attend. Une fiche qui en
        attend une autre s'ouvre après elle, où qu'elle soit dans la liste : sa
        dépendance est écrite dès sa naissance, et aucune ne se perd. Rend les
        numéros dans l'ordre de la liste."""
        attendus = {rang: sorted({k for k in fiche.get("apres") or []
                                  if isinstance(k, int) and 1 <= k <= len(fiches) and k != rang})
                    for rang, fiche in enumerate(fiches, start=1)}
        # D'abord les fiches qui n'attendent plus rien ; des fiches qui
        # s'attendent en rond s'ouvrent à la fin, et leur boucle sera dite.
        ordre: list[int] = []
        while len(ordre) < len(fiches):
            libres = [r for r in attendus if r not in ordre and all(k in ordre for k in attendus[r])]
            ordre += libres or [r for r in attendus if r not in ordre]
        numeros: dict[int, int] = {}
        en_retard: dict[int, list[int]] = {}
        for rang in ordre:
            fiche = fiches[rang - 1]
            attend = [numeros[k] for k in attendus[rang] if k in numeros]
            en_retard[rang] = [k for k in attendus[rang] if k not in numeros]
            etiquettes = [lots.ETIQUETTE_LOT, "pret"]
            if fiche.get("piste") in self.projet.pistes:
                etiquettes.append(fiche["piste"])
            if fiche.get("machine") == "pc":
                etiquettes.append(lots.ETIQUETTE_PC)
            if fiche.get("meneur") == "developpeur":
                etiquettes.append(lots.ETIQUETTE_SIMPLE)
            if urgent:
                etiquettes.append(lots.ETIQUETTE_URGENT)
            corps = consignes.corps_de_fiche(fiche, depend_de=attend, decoupe_de=decoupe_de) + en_plus
            numeros[rang] = self.gh.creer_issue(str(fiche["titre"]).strip(), corps, etiquettes, palier_titre)
        for rang, manquants in en_retard.items():
            if manquants:
                issue = self.gh.issue(numeros[rang])
                self.gh.corps_de(numeros[rang], lots.avec_dependances(issue.get("body") or "",
                                                                      [numeros[k] for k in manquants]))
        return [numeros[rang] for rang in range(1, len(fiches) + 1)]

    # ----------------------------------------------------- master rouge
    def _master_rouge(self, vue: "_Vue") -> bool:
        """Master rouge : tous les lots attendent. Le CTO écrit la fiche du lot
        de réparation, que le pilote prend avant tout autre. Une réparation à
        la fois, et une seule par run rouge."""
        if any(l.urgent and l.est_un_lot for l in vue.ouvertes):
            return False
        run = self.gh.dernier_run("tests.yml", self.projet.branche_base)
        if not run or run.get("status") != "completed" or run.get("conclusion") != "failure":
            return False
        identifiant = run.get("databaseId")
        if any(m.get("etat") == "reparation" and m.get("run") == identifiant
               for l in vue.fermes for m in lots.marques([{"body": l.corps}])):
            return False
        if not self.verrous.prendre("reparation"):
            return False
        try:
            try:
                journal = traces.lire_run(self.gh.depot, identifiant)
            except Exception:  # noqa: BLE001 — un journal illisible ne retient pas la réparation
                journal = ""
            chemin = self.depot.preparer("reparation", f"reparation/{self.maintenant():%Y%m%d-%H%M}")
            appel = agents_mod.Appel(role=CTO, lecture_seule=True, schema=consignes.schema_fiche(self.projet),
                                     consigne=consignes.reparation_de_master(self.projet, url=run.get("url", ""),
                                                                             resume=journal),
                                     jours_max=self.projet.jours_max)
            res = self._invoquer(CTO, appel, chemin, lot="master")
            if res.attente:
                self.noter("master", "attente", f"CTO : {res.raison}")
                return True
            fiche = res.sortie if res.reussi else None
            if not fiche or not fiche.get("titre"):
                self.noter("master", "rouge, sans fiche de réparation", f"code {res.code}", str(res.agent or ""))
                return True
            en_plus = (f"\nRéparation de `{self.projet.branche_base}` : {run.get('url', '')}\n\n"
                       + marque(**self._champs(CTO, res, etat="reparation", run=identifiant)))
            numero = self.ouvrir_les_fiches([fiche], vue.palier.titre if vue.palier else None, urgent=True,
                                            en_plus=en_plus)[0]
            self.noter("master", "rouge : lot de réparation ouvert", f"#{numero}", str(res.agent))
            return True
        finally:
            self.verrous.lacher("reparation")

    # --------------------------------------------------- livrer, bloquer
    def _livrer(self, numero: int, numero_pr: int | None = None) -> None:
        self.gh.etiqueter(numero, ["livre"], ["en-cours"])
        try:
            issue = self.gh.issue(numero)
            if issue.get("state") == "OPEN":
                self.gh.fermer_issue(numero, f"Livré par #{numero_pr}." if numero_pr else None)
        except GitHubErreur:
            pass
        self.depot.retirer(numero)
        self.noter(numero, "livré", f"PR #{numero_pr}" if numero_pr else "")

    def _livrer_les_fermes(self, fermees: list[dict]) -> None:
        """Une PR fusionnée ferme son issue (« Closes #N ») avant que le
        pilote ne la voie : l'issue fermée encore « en-cours » est livrée."""
        for issue in fermees:
            lot = Lot.de(issue)
            if lot.etat == "en-cours" and lot.est_un_lot and not self._pris_ailleurs(lot.numero):
                resume = self.gh.pr_de_branche(lot.branche(self.projet.prefixe_branche))
                if resume and (resume.get("mergedAt") or resume.get("state") == "MERGED"):
                    self._livrer(lot.numero, resume["number"])

    def _bloquer(self, numero: int, raison: str, numero_pr: int | None = None, *,
                 question: Question | None = None, boucle: list[int] | None = None) -> None:
        """Arrête le lot, avec sa raison. Le CTO le regarde au tour suivant ;
        une réponse du propriétaire sur l'issue le fait repartir aussi."""
        self.gh.etiqueter(numero, ["bloque"], ["en-cours", "pret"])
        champs: dict = question.marque() if question is not None else {}
        if boucle:
            champs["boucle"] = boucle
        if question is None:
            texte = f"🤖 **pilote** : lot arrêté — {raison}.\n\nLe CTO le regarde au tour suivant."
        else:
            texte = (f"🤖 **pilote** : lot arrêté sur une question du meneur.\n\n{question.en_clair()}\n\n"
                     "Le CTO la tranche au tour suivant.")
        self.gh.commenter_issue(numero, f"{texte}\n\n{marque(role='pilote', etat=lots.BLOQUE, raison=raison, **champs)}")
        self.noter(numero, "bloqué", raison)
