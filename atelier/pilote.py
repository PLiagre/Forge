"""Le pilote : un tour de la chaîne.

Un tour relit GitHub, fait avancer d'un pas les lots en cours, et prend le
lot suivant du jalon courant quand une machine a de la place ; une machine
qui n'y a plus rien à prendre prend dans le jalon suivant (la fenêtre de
deux jalons). Il invoque au plus UN agent : un tour reste court à lire.
Plusieurs tours tournent en même temps — le cron en lance un toutes les deux
minutes —, et des verrous (`verrous.py`) font qu'un lot n'avance que dans un
tour à la fois, que relire et choisir se font un tour après l'autre, et
qu'une machine ne prend pas plus de lots que sa capacité (`[machines]`).
Tout ce qui se décide se décide dans `lots.py`, en fonction pure ; ici, on
fait les gestes.

    un lot = une issue → le chef écrit le brief dans la branche du lot et
    ouvre la PR → le codeur code → la CI joue les tests → le relecteur rend
    ACCEPTE ou CORRIGER → ACCEPTE : fusion automatique ; CORRIGER : le
    codeur corrige, deux fois au plus, puis le lot est « bloque », avec sa
    raison.
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
from . import captures, lfs, lots, prompts, traces
from .depot import Depot, DepotErreur
from .github import GitHub, GitHubErreur, etat_des_controles
from .lots import Lot, marque
from .projet import MACHINES, Projet
from .verrous import AucunVerrou

_DECISION = re.compile(r"^\s*DECISION:\s*(BRIEF|REFUS|QUESTION|DECOUPE|MODE-DIRECT|REPRENDRE)\b[ \t]*(?:::[ \t]*(.*))?$", re.M)
# Le dépanneur écrit en Markdown : le 1er octobre 2026, sa décision sur #235
# est restée illisible. Sa ligne se lit en gras, citée ou en code, et sa
# consigne peut suivre sur les lignes d'après.
_DECISION_DEPANNEUR = re.compile(r"^[ \t>*_`]*DECISION\s*:[ \t*_`]*(REPRENDRE|QUESTION|MODE-DIRECT)\b[ \t*_`]*"
                                 r"(?:::[ \t]*(.*))?$", re.M)
_VERDICT = re.compile(r"^\s*\**VERDICT:\s*(ACCEPTE|CORRIGER)\**\s*$", re.M)
_SOUS_LOT = re.compile(r"^\s*-\s*(.+?)\s*::\s*(.+?)\s*$", re.M)
_TAILLE = re.compile(r"Taille prévue\s*:\s*~?\s*(\d+)", re.I)
SECTIONS_BRIEF = ("## But", "## Règle du monde", "## Périmètre", "## Conditions de succès", "## Hors périmètre")
SIGNATURE = "\n\n🤖 Généré par la chaîne de Forge ([Claude Code](https://claude.com/claude-code), Codex, Cursor)"


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

    cap: str
    jalons: list
    courant: "lots.Jalon | None"
    apres: "lots.Jalon | None"
    ouvertes: list[Lot]
    fermes: list[Lot]
    decoupe_du_courant: bool


def _verrou_du_lot(numero: int | str) -> str:
    return f"lot-{numero}"


def _commentaires_pour_le_chef(commentaires: list[dict]) -> str:
    """Ce que le chef lit sous l'issue : les commentaires des humains, et les
    questions qu'il a posées lui-même (sans elles, une réponse « A » ne veut
    rien dire). Le reste de ce qu'écrit le pilote ne le concerne pas."""
    lus = []
    for c in commentaires:
        corps = c.get("body") or ""
        faites = lots.marques([c])
        if not faites:
            lus.append(f"{(c.get('author') or {}).get('login', '?')} : {corps}")
        elif any(m.get("etat") == "bloque" and m.get("question") for m in faites):
            lus.append("ta question au propriétaire : " + lots._MARQUE.sub("", corps).strip())
        elif any(m.get("role") == "depanneur" for m in faites):
            lus.append("le dépanneur : " + lots._MARQUE.sub("", corps).strip())
    return "\n\n".join(lus)


def _extrait(texte: str, lignes: int = 60) -> str:
    morceaux = texte.strip().splitlines()
    if len(morceaux) <= lignes:
        return "\n".join(morceaux)
    return "\n".join(morceaux[:lignes]) + f"\n… ({len(morceaux) - lignes} lignes de plus)"


class Pilote:
    def __init__(self, projet: Projet, gh: GitHub, depot: Depot, *,
                 executeur_agents: agents_mod.Executeur = agents_mod.executer,
                 maintenant=None, journal: Path | None = None, verrous=None,
                 lfs_telechargeur: lfs.Telechargeur = lfs.telecharger):
        self.projet = projet
        self.gh = gh
        self.depot = depot
        self.executeur_agents = executeur_agents
        # Les verrous partagés avec les autres tours ; sans eux, un seul
        # tour à la fois (les tests, le tour à sec).
        self.verrous = verrous or AucunVerrou()
        self.maintenant = maintenant or (lambda: datetime.now(timezone.utc))
        self.journal = journal or Path.home() / ".atelier" / "journal.jsonl"
        self.lignes: list[str] = []
        self.lfs_telechargeur = lfs_telechargeur

    # ----------------------------------------------------------- journal
    def noter(self, lot: int | str, action: str, detail: str = "", agent: str | None = None) -> None:
        quand = self.maintenant().isoformat(timespec="seconds")
        entree = {"quand": quand, "lot": lot, "action": action, "detail": detail, "agent": agent}
        try:
            self.journal.parent.mkdir(parents=True, exist_ok=True)
            with self.journal.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entree, ensure_ascii=False) + "\n")
        except OSError:
            pass
        self.lignes.append(f"#{lot} {action}" + (f" [{agent}]" if agent else "") + (f" — {detail}" if detail else ""))

    def _invoquer(self, role: str, prompt: str, chemin: Path, *, lot: int | str,
                  exclure=frozenset()) -> agents_mod.Resultat:
        res = agents_mod.invoquer(self.projet.poste(role), prompt, chemin, self.projet.delai(role),
                                  exclure=exclure, executeur=self.executeur_agents,
                                  place=lambda outil: self.verrous.place(f"outil-{outil}",
                                                                         self.projet.plafond(outil)))
        # Un secours a répondu : pourquoi les précédents ne l'ont pas fait
        # entre au journal, sinon un quota ou une session perdue ne se voit
        # nulle part (le chef de #184, le 28 septembre 2026).
        refus = [e for e in res.essais[:-1] if "écarté" not in e]
        if res.agent is not None and refus:
            self.noter(lot, "secours", f"{role} : " + " · ".join(refus), str(res.agent))
        return res

    # --------------------------------------------------------------- tour
    def tour(self) -> list[str]:
        """Un tour : relire et ranger (un tour après l'autre), faire avancer
        d'un pas les lots en cours qu'aucun autre tour ne tient, puis, si
        aucun agent n'est parti, prendre le lot suivant quand une machine a
        de la place."""
        self.lignes = []
        with self.verrous.tenir("decider"):
            vue = self._ranger_le_monde()
        agent_parti = False
        for lot in sorted(vue.ouvertes, key=lambda l: l.numero):
            if lot.etat != "en-cours" or agent_parti:
                continue
            if not self.verrous.prendre(_verrou_du_lot(lot.numero)):
                continue  # un autre tour le fait avancer
            try:
                # Relu sous son verrou : depuis la relecture du tour, un autre
                # tour a pu le livrer, le bloquer ou le rendre.
                lot = Lot.de(self.gh.issue(lot.numero))
                if lot.etat != "en-cours":
                    continue
                agent_parti = self._avancer(lot, vue.jalons, vue.courant)
            except (GitHubErreur, DepotErreur) as e:
                self.noter(lot.numero, "erreur", str(e))
            finally:
                self._lacher_lot(lot.numero)

        if not agent_parti:
            agent_parti = self._master_rouge()
        if not agent_parti:
            agent_parti = self._depanner_un_lot(vue)
        if not agent_parti and vue.courant is not None:
            self._prendre_le_suivant(vue)
        with self.verrous.tenir("decider"):
            self._ranger_jalons()
        if not self.lignes:
            self.lignes.append("RIEN")
        return self.lignes

    def _ranger_le_monde(self) -> "_Vue":
        """Ce que le tour sait du monde, rangé : les jalons suivent CAP.md, les
        issues du formulaire sont rangées, les lots qui attendent une
        dépendance rendent leur machine, les lots remis « pret » reprennent,
        les lots fusionnés sont livrés, et le jalon courant sans plan se
        découpe. Se fait sous le verrou « decider » : un tour à la fois."""
        self.depot.fetch()
        cap = self._cap()
        bruts = self._accorder_jalons(cap)
        jalons = lots.jalons(bruts)
        courant = lots.jalon_courant(jalons)
        apres = lots.jalon_suivant(jalons, courant)
        reserve = any(m.get("title") == lots.RESERVE for m in bruts)
        ouvertes = [Lot.de(i) for i in self.gh.issues("open")]
        self._normaliser(ouvertes, jalons, reserve)
        ouvertes = [Lot.de(i) for i in self.gh.issues("open")]
        fermees = self.gh.issues("closed")
        bloq = lots.bloquantes(ouvertes, [Lot.de(i) for i in fermees])
        if self._lever_sur_reponse(ouvertes):
            ouvertes = [Lot.de(i) for i in self.gh.issues("open")]
        if self._attendre_dependances(ouvertes, bloq) | self._reprendre(ouvertes, bloq):
            ouvertes = [Lot.de(i) for i in self.gh.issues("open")]
        self._livrer_les_fermes(fermees)
        fermes = [Lot.de(i) for i in fermees]
        decoupe_du_courant = lots.a_decouper(courant, cap, ouvertes, fermes)
        if decoupe_du_courant:
            self._faire_decouper(courant, ouvertes)
        return _Vue(cap=cap, jalons=jalons, courant=courant, apres=apres, ouvertes=ouvertes,
                    fermes=fermes, decoupe_du_courant=decoupe_du_courant)

    def _prendre_le_suivant(self, vue: "_Vue") -> None:
        """Le lot suivant, quand sa machine a de la place : ses lots en cours,
        et ceux qu'un autre tour est en train de prendre (son chef travaille),
        restent sous sa capacité. Le choix se fait sur une relecture fraîche,
        sous le verrou « decider » ; le chef travaille ensuite, sous le seul
        verrou du lot."""
        courant, apres = vue.courant, vue.apres
        with self.verrous.tenir("decider"):
            ouvertes = [Lot.de(i) for i in self.gh.issues("open")]
            bloq = lots.bloquantes(ouvertes, vue.fermes)
            # L'état est frais (un autre tour a pu prendre un lot depuis), mais
            # un lot né pendant ce tour (une découpe) part au tour suivant.
            connus = {l.numero for l in vue.ouvertes}
            tous = [l for l in ouvertes if "lot" in l.etiquettes]
            en_prise = {l.numero for l in tous
                        if l.etat in ("pret", "idee") and self.verrous.pris_ailleurs(_verrou_du_lot(l.numero))}
            tenus = Counter(l.machine for l in tous if l.etat == "en-cours" or l.numero in en_prise)
            libres = {m: tenus[m] < self.projet.capacite(m) for m in MACHINES}
            if not any(libres.values()):
                return
            libres_de_prendre = [l for l in tous if l.numero in connus and l.numero not in en_prise]
            suivant = lots.a_prendre(libres_de_prendre, courant.numero, libres, bloq)
            # La fenêtre de deux jalons : une machine libre qui n'a plus rien
            # à prendre dans le jalon courant prend dans le suivant, et le
            # découpe s'il n'a encore rien. Le 29 septembre 2026, J1 n'avait
            # plus que des lots « pc » : le VPS attendait sans rien faire que
            # le PC finisse, alors que J2 ne demande que `sim/`.
            apres_a_decouper = False
            if suivant is None and apres is not None and not vue.decoupe_du_courant:
                apres_a_decouper = lots.a_decouper(apres, vue.cap, ouvertes, vue.fermes)
                if apres_a_decouper:
                    self._faire_decouper(apres, ouvertes, courant)
                suivant = lots.a_prendre(libres_de_prendre, apres.numero, libres, bloq)
            if suivant is None and libres["pc"] and apres is not None and not vue.decoupe_du_courant \
                    and not apres_a_decouper:
                suivant = self._plus_loin_pour_le_pc(vue, ouvertes, libres_de_prendre, bloq)
            if suivant is None or not self.verrous.prendre(_verrou_du_lot(suivant.numero)):
                return
        try:
            self._chef(suivant, suivant.jalon_titre or courant.titre, courant)
        except (GitHubErreur, DepotErreur) as e:
            self.noter(suivant.numero, "erreur", str(e))
        finally:
            self._lacher_lot(suivant.numero)

    def _plus_loin_pour_le_pc(self, vue: "_Vue", ouvertes: list[Lot], libres_de_prendre: list[Lot],
                              bloq: frozenset[int]) -> Lot | None:
        """La fenêtre du PC a trois jalons. La 3D n'arrive qu'au jalon 4 : le
        30 septembre 2026, J2 et J3 ne demandaient que `sim/`, et le PC
        attendait des semaines. Un PC qui n'a plus rien dans les deux premiers
        prend un lot « pc » du troisième ; un troisième sans plan se découpe en
        avance pour lui, et sa découpe part même si le VPS est plein : ce
        n'est que le chef, et c'est le PC qu'elle nourrit. Les lots du VPS de
        ce jalon attendent qu'il entre dans la fenêtre."""
        loin = lots.jalon_du_pc(vue.jalons, vue.courant)
        if loin is None:
            return None
        suivant = lots.a_prendre(libres_de_prendre, loin.numero, {"pc": True}, bloq)
        if suivant is not None:
            return suivant
        if lots.a_decouper(loin, vue.cap, ouvertes, vue.fermes):
            self._faire_decouper(loin, ouvertes, vue.courant, pour_le_pc=True)
            return None
        return next((l for l in sorted(libres_de_prendre, key=lambda l: l.numero)
                     if l.jalon == loin.numero and l.etat == "pret" and not l.dependances & bloq
                     and lots.jalon_a_decouper_par(l) == loin.numero), None)

    def _lacher_lot(self, numero: int) -> None:
        """Rend le lot aux autres tours, sous le verrou « decider » : un tour
        qui choisit le lot suivant voit soit le verrou encore tenu, soit
        l'étiquette que ce tour vient de poser, jamais un entre-deux."""
        with self.verrous.tenir("decider"):
            self.verrous.lacher(_verrou_du_lot(numero))

    def _pris_ailleurs(self, numero: int) -> bool:
        return self.verrous.pris_ailleurs(_verrou_du_lot(numero))

    # ------------------------------------------------------------ jalons
    def _cap(self) -> str:
        """CAP.md tel que la copie principale le porte : la source des jalons."""
        try:
            return (self.projet.racine / "CAP.md").read_text(encoding="utf-8")
        except OSError:
            return ""

    def _accorder_jalons(self, cap: str) -> list[dict]:
        """Les milestones disent ce que dit CAP.md : un jalon nouveau se crée,
        un jalon renommé se renomme, la réserve existe si CAP.md la déclare.
        Rien ne se ferme ni ne s'efface ici. Rend les milestones d'après."""
        bruts = self.gh.jalons()
        gestes = lots.accord_des_jalons(cap, bruts)
        for geste in gestes:
            titre = geste[-1]
            cle = f"J{lots.numero_de_jalon(titre)}" if lots.numero_de_jalon(titre) else titre
            try:
                if geste[0] == "creer":
                    self.gh.creer_jalon(titre)
                    self.noter(cle, "jalon créé", f"« {titre} », d'après CAP.md")
                else:
                    self.gh.renommer_jalon(geste[1], titre)
                    self.noter(cle, "jalon renommé", f"« {geste[2]} » devient « {titre} »")
            except GitHubErreur as e:
                self.noter(cle, "erreur", str(e))
        return self.gh.jalons() if gestes else bruts

    def _faire_decouper(self, jalon: lots.Jalon, ouvertes: list[Lot], courant: lots.Jalon | None = None,
                        pour_le_pc: bool = False) -> None:
        """Un jalon qui commence sans plan se fait découper : le pilote ouvre
        le lot de sa découpe, que le chef prend comme un autre. Le jalon
        suivant se découpe en avance quand une machine n'a plus rien dans le
        `courant` ; le troisième, `pour_le_pc`, quand le PC n'a plus rien dans
        les deux premiers."""
        avant = sorted(l.numero for l in ouvertes
                       if l.jalon == jalon.numero and "lot" in l.etiquettes and l.etat == "idee")
        en_avance = courant is not None and jalon.numero > courant.numero
        try:
            n = self.gh.creer_issue(f"Découper le jalon {jalon.titre}",
                                    lots.corps_de_la_decoupe(jalon, avant, courant if en_avance else None,
                                                             pour_le_pc=pour_le_pc),
                                    ["lot", "pret"], jalon.titre)
            self.noter(n, "jalon à découper", jalon.titre + (" (en avance, pour le PC)" if pour_le_pc else
                                                             " (en avance)" if en_avance else ""))
        except GitHubErreur as e:
            self.noter(f"J{jalon.numero}", "erreur", str(e))

    # ------------------------------------------------------- normaliser
    def _normaliser(self, ouvertes: list[Lot], jalons: list[lots.Jalon], reserve: bool = False) -> None:
        """Une issue du formulaire porte son jalon et sa machine dans le texte :
        le pilote les pose en milestone et en étiquette, une fois. Une issue
        déjà rangée dans un milestone, réserve comprise, n'est pas déplacée.
        L'étiquette `reserve` range un lot dans la réserve, puis s'efface."""
        par_numero = {j.numero: j for j in jalons}
        for lot in ouvertes:
            if not any(e in lot.etiquettes for e in lots.ETATS) and "lot" in lot.etiquettes:
                self.gh.etiqueter(lot.numero, ["idee"])
            m = re.search(r"### Jalon\s+J(\d+)", lot.corps)
            if lot.jalon_titre is None and m and int(m.group(1)) in par_numero:
                self.gh.jalon_de(lot.numero, par_numero[int(m.group(1))].titre)
            elif lot.jalon_titre is None and reserve and re.search(r"### Jalon\s+R[ée]serve", lot.corps, re.I):
                self.gh.jalon_de(lot.numero, lots.RESERVE)
            if re.search(r"### Machine\s+pc\b", lot.corps, re.I) and lots.ETIQUETTE_PC not in lot.etiquettes:
                self.gh.etiqueter(lot.numero, [lots.ETIQUETTE_PC])
            if reserve and lots.ETIQUETTE_RESERVE in lot.etiquettes:
                if lot.jalon_titre != lots.RESERVE:
                    self.gh.jalon_de(lot.numero, lots.RESERVE)
                    self.noter(lot.numero, "rangé dans la réserve", lot.jalon_titre or "sans jalon")
                self.gh.etiqueter(lot.numero, retirer=[lots.ETIQUETTE_RESERVE])

    # ---------------------------------------------------------- reprendre
    def _attendre_dependances(self, ouvertes: list[Lot], bloq: frozenset[int]) -> set[int]:
        """Un lot en cours dont une dépendance est encore ouverte n'avance
        pas et ne tient pas sa machine : il redevient « pret », et la reprise
        le relance quand elles sont livrées, compteurs remis à zéro. Mesuré le
        28 septembre 2026 : #184 (le panneau), pris avant #185 et #186 (le
        client qu'il lit), gardait le PC et brûlait ses essais."""
        rendus = set()
        for lot in ouvertes:
            attend = sorted(lot.dependances & bloq)
            if lot.etat != "en-cours" or not attend or self._pris_ailleurs(lot.numero):
                continue
            liste = ", ".join(f"#{n}" for n in attend)
            self.gh.etiqueter(lot.numero, ["pret"], ["en-cours"])
            self.gh.commenter_issue(lot.numero, f"🤖 **pilote** : lot remis « pret » — il dépend de {liste}, pas encore "
                                                "livré. Il sera repris où il en est quand ce sera fait, essais remis "
                                                f"à zéro ; d'ici là, il rend sa machine.\n\n"
                                                f"{marque(role='pilote', etat='attend', raison=f'dépend de {liste}')}")
            self.noter(lot.numero, "remis pret", f"dépend de {liste}")
            rendus.add(lot.numero)
        return rendus

    def _lever_sur_reponse(self, ouvertes: list[Lot]) -> set[int]:
        """Un lot bloqué sur lequel le propriétaire a écrit depuis son blocage
        repart : sa réponse (une lettre, une décision, « c'est corrigé »)
        suffit, sans toucher aux étiquettes. Il redevient « pret » : le chef le
        reprend et lit la réponse, ou sa PR reprend où elle en est
        (`_reprendre`), essais remis à zéro."""
        leves = set()
        for lot in ouvertes:
            if lot.etat != "bloque" or "lot" not in lot.etiquettes or self._pris_ailleurs(lot.numero):
                continue
            if not lots.reponse_apres_blocage(self.gh.issue(lot.numero).get("comments") or []):
                continue
            self.gh.commenter_issue(lot.numero, "🤖 **pilote** : réponse reçue — lot remis « pret ». Au tour suivant, "
                                                "il reprend où il en est, essais remis à zéro ; le chef lit ta "
                                                "réponse s'il reprend le lot.\n\n"
                                                f"{marque(role='pilote', etat='reponse')}")
            self.gh.etiqueter(lot.numero, ["pret"], ["bloque"])
            self.noter(lot.numero, "réponse reçue", "remis pret")
            leves.add(lot.numero)
        return leves

    def _reprendre(self, ouvertes: list[Lot], bloq: frozenset[int] = frozenset()) -> set[int]:
        """Un lot remis « pret » alors que sa PR est ouverte reprend où il en
        est, dès que ses dépendances sont livrées. Relancer le chef coûterait
        un quota, et buterait sur la branche et la PR qui existent déjà. La
        marque « reprise » sur la PR remet les compteurs à zéro
        (`lots.depuis_reprise`) ; elle s'écrit avant l'étiquette : sans elle,
        un lot « en-cours » recompterait ses échecs et serait rebloqué."""
        prets = [l for l in ouvertes if l.etat == "pret" and "lot" in l.etiquettes and not l.dependances & bloq
                 and not self._pris_ailleurs(l.numero)]
        if not prets:
            return set()
        par_branche = {p["headRefName"]: p for p in self.gh.prs_ouvertes()}
        repris = set()
        for lot in prets:
            pr = par_branche.get(lot.branche(self.projet.prefixe_branche))
            if pr is None:
                continue
            quand = self.maintenant().isoformat(timespec="seconds")
            self.gh.commenter_pr(pr["number"], "🤖 **pilote** : lot repris (remis « pret »). "
                                               "Les essais du codeur, du chef et du relecteur repartent de zéro ; "
                                               "le travail déjà poussé reste.\n\n"
                                               f"{marque(role='pilote', etat='reprise', quand=quand)}")
            self.gh.etiqueter(lot.numero, ["en-cours"], [e for e in ("pret", "idee", "bloque") if e in lot.etiquettes])
            self.noter(lot.numero, "repris", f"PR #{pr['number']}")
            repris.add(lot.numero)
        return repris

    # ---------------------------------------------------------- avancer
    def _avancer(self, lot: Lot, jalons: list[lots.Jalon], courant: lots.Jalon | None = None) -> bool:
        branche = lot.branche(self.projet.prefixe_branche)
        resume = self.gh.pr_de_branche(branche)
        if resume is None:
            titre_jalon = lot.jalon_titre or next((j.titre for j in jalons if j.numero == lot.jalon), "")
            return self._chef(lot, titre_jalon, courant)
        pr = self.gh.pr(resume["number"])
        liste = lots.marques(pr.get("comments") or [])
        etat_ci, _ = etat_des_controles(pr)
        role = "codeur_3d" if lot.machine == "pc" else "codeur"
        action = lots.action_suivante(pr, etat_ci, liste, corrections_max=self.projet.corrections_max,
                                      role_codeur=role,
                                      heures_depuis_envoi_pc=self._heures_depuis(liste, role, "envoye"),
                                      heures_depuis_attente_pc=self._heures_depuis(liste, role, "attente"))
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
        if action.nom == "conflit":
            return self._conflit(lot, pr, branche)
        if action.nom == "relancer_pc":
            # Le PC n'a pas répondu : on lui renvoie ce qu'on lui avait demandé.
            derniere = next((m.get("action") for m in reversed(liste)
                             if m.get("role") == role and m.get("etat") == "envoye"), None)
            action = lots.Action(derniere or "coder", action.raison, action.essai)
        if action.nom in ("coder", "corriger_ci", "corriger_relecture"):
            if lot.machine == "pc":
                self._envoyer_pc(lot, pr, branche, action)
                return False
            # Le dernier passage avant blocage se fait par le renfort. Les
            # lots du PC n'en ont pas : Codex n'y écrit pas, Claude y code déjà.
            renfort = lots.passage_de_renfort(action.essai, self.projet.corrections_max)
            return self._coder(lot, pr, branche, action, liste, role="codeur", chantier=lot.numero,
                               poste="renfort" if renfort else None)
        if action.nom == "relire":
            return self._relire(lot, pr, branche, liste)
        if action.nom == "chef":
            return self._chef(lot, lot.jalon_titre or "", courant)
        self.noter(lot.numero, "action inconnue", action.nom)
        return False

    def _heures_depuis(self, liste: list[dict], role: str, etat: str) -> float | None:
        """Les heures écoulées depuis la dernière marque `etat` de ce rôle."""
        vues = [m for m in liste if m.get("role") == role and m.get("etat") == etat and m.get("quand")]
        if not vues:
            return None
        depuis = datetime.fromisoformat(vues[-1]["quand"])
        return (self.maintenant() - depuis).total_seconds() / 3600

    # --------------------------------------------------------------- chef
    def _chef(self, lot: Lot, titre_jalon: str, courant: lots.Jalon | None = None) -> bool:
        issue = self.gh.issue(lot.numero)
        echecs = lots.echecs_du_chef(lots.marques(issue.get("comments") or []))
        if echecs >= 2:
            self._bloquer(lot.numero, f"le chef a échoué {echecs} fois")
            return False
        branche = lot.branche(self.projet.prefixe_branche)
        chemin_brief = lot.brief(self.projet.dossier_briefs)
        chemin = self.depot.preparer(lot.numero, branche)
        commentaires = _commentaires_pour_le_chef(issue.get("comments") or [])
        # Un lot du jalon suivant, pris par la fenêtre, le sait : il ne
        # s'appuie sur rien que le jalon courant doit encore livrer.
        en_avance = courant is not None and lot.jalon is not None and lot.jalon > courant.numero
        prompt = prompts.chef(self.projet, numero=lot.numero, titre=lot.titre, corps=lot.corps,
                              commentaires=commentaires, jalon=lot.jalon or 0, jalon_titre=titre_jalon,
                              machine=lot.machine, chemin_brief=chemin_brief,
                              jalon_courant=courant.titre if en_avance else "")
        res = self._invoquer("chef", prompt, chemin, lot=lot.numero)
        if res.attente:
            self.noter(lot.numero, "attente", "chef : " + " · ".join(res.essais))
            return True
        decisions = _DECISION.findall(res.texte)
        decision, motif = decisions[-1] if decisions else ("", "")
        if res.reussi and decision == "REFUS":
            self._bloquer(lot.numero, f"refusé par le chef : {motif or 'hors du jalon courant'}")
            return True
        if res.reussi and decision == "QUESTION":
            question = lots.question_du_chef(res.texte, motif or "")
            self._bloquer(lot.numero, f"question au propriétaire : {question.texte}", question=question)
            return True
        if res.reussi and decision == "DECOUPE":
            return self._decouper(lot, res, titre_jalon)
        raison = ""
        brief = Path(chemin) / chemin_brief
        if not res.reussi:
            raison = f"le chef a rendu le code {res.code} ({' · '.join(res.essais)})"
        elif decision != "BRIEF" or not brief.is_file():
            raison = "le chef n'a pas écrit de brief (« DECISION: BRIEF » absente ou fichier manquant)"
        else:
            texte = brief.read_text(encoding="utf-8", errors="replace")
            manquantes = [s for s in SECTIONS_BRIEF if s not in texte]
            taille = _TAILLE.search(texte)
            if manquantes:
                raison = f"brief incomplet : {', '.join(manquantes)}"
            elif not taille:
                raison = "brief sans « Taille prévue »"
            elif int(taille.group(1)) >= self.projet.lignes_max:
                raison = f"brief trop gros : {taille.group(1)} lignes prévues (maximum {self.projet.lignes_max})"
        if raison:
            self.gh.commenter_issue(lot.numero, f"🤖 **chef** ({res.agent or '—'}) : {raison}.\n\n"
                                    f"{marque(role='chef', etat='echec', raison=raison)}")
            self.noter(lot.numero, "chef en échec", raison, str(res.agent or ""))
            return True
        autres = [f for f in self.depot.changements(chemin) if f != chemin_brief]
        if autres:
            self.depot.annuler(chemin, autres)
        sha = self.depot.enregistrer(chemin, f"Brief du lot #{lot.numero} : {lot.titre}\n\nÉcrit par {res.agent}.")
        self.depot.pousser(chemin, branche)
        corps = (f"Closes #{lot.numero}\n\nJalon : {titre_jalon} · Machine : {lot.machine}\n"
                 f"Brief : [`{chemin_brief}`](../blob/{branche}/{chemin_brief})\n\n"
                 "Le chef écrit le brief, le codeur code, la CI joue les tests, le relecteur rend son verdict ; "
                 "ACCEPTE fusionne tout seul." + SIGNATURE)
        numero_pr = self.gh.creer_pr(branche, self.projet.branche_base, f"Lot #{lot.numero} — {lot.titre}",
                                     corps, brouillon=True)
        self.gh.etiqueter(lot.numero, ["en-cours"], [e for e in ("pret", "idee", "bloque") if e in lot.etiquettes])
        self.gh.commenter_pr(numero_pr, f"🤖 **chef** ({res.agent}) : brief écrit, révision `{sha[:7]}`.\n\n"
                                        f"{marque(role='chef', etat='fait', agent=str(res.agent), sha=sha)}")
        self.noter(lot.numero, "brief écrit", f"PR #{numero_pr}", str(res.agent))
        return True

    def _decouper(self, lot: Lot, res: agents_mod.Resultat, titre_jalon: str) -> bool:
        apres = res.texte[res.texte.rfind("DECISION: DECOUPE"):]
        sous = [lots.sous_lot(titre, quoi, lot.machine) for titre, quoi in _SOUS_LOT.findall(apres)]
        raison = "" if sous else "découpe illisible"
        rangs: list[tuple[int, ...]] = []
        if sous:
            try:
                rangs = lots.dependances_des_sous_lots(
                    sous, preuve_en_dernier=lots.jalon_a_decouper_par(lot) is not None)
            except ValueError as e:
                raison = f"découpe illisible : {e}"
        if raison:
            self.gh.commenter_issue(lot.numero, f"🤖 **chef** : {raison}, aucun sous-lot créé.\n\n"
                                    f"{marque(role='chef', etat='echec', raison=raison)}")
            self.noter(lot.numero, "chef en échec", raison, str(res.agent))
            return True
        crees: list[int] = []
        for s, attend in zip(sous, rangs):
            etiquettes = ["lot", "pret"] + ([lots.ETIQUETTE_PC] if s.machine == "pc" else [])
            # Un sous-lot attend ceux que le chef a nommés (le précédent, sans
            # rien dire) : un morceau bloqué retient ceux qui s'appuient sur
            # lui, et les autres avancent en même temps.
            suite = ("\n\nDépend de : " + ", ".join(f"#{crees[k - 1]}" for k in attend)) if attend else ""
            n = self.gh.creer_issue(s.titre, f"{s.quoi}\n\nDécoupé du lot #{lot.numero} par le chef.{suite}",
                                    etiquettes, titre_jalon or None)
            crees.append(n)
        liste = ", ".join(f"#{n}" for n in crees)
        pourquoi = "jalon découpé" if lots.jalon_a_decouper_par(lot) else "trop gros pour un lot, découpé"
        self.gh.fermer_issue(lot.numero, f"🤖 **chef** ({res.agent}) : {pourquoi} en {liste}.",
                             abandon=True)
        self.noter(lot.numero, "découpé", liste, str(res.agent))
        return True

    # ------------------------------------------------------------- coder
    def _coder(self, lot: Lot, pr: dict, branche: str, action: lots.Action, liste: list[dict], *,
               role: str, chantier: str | int, poste: str | None = None, prompt: str | None = None,
               photographe: Photographe | None = None, marquer_attente: bool = False) -> bool:
        """Un passage du codeur (ou du mécanicien) sur la branche d'une PR.

        `role` est le nom écrit dans la marque ; `poste` celui de la ligne de
        `[agents]` qui répond (le même, sauf pour le mécanicien de master).
        `photographe` regarde la révision poussée (la carte du monde par
        défaut ; Unity sur le PC) ; ce qu'il voit entre dans le compte rendu.
        `marquer_attente` : sur le PC, une attente s'écrit sur la PR, sinon
        le pilote du VPS ne la voit pas et attend un jour."""
        numero_pr = pr["number"]
        chemin = self.depot.preparer(chantier, branche)
        if prompt is None:
            correction = ""
            if action.nom == "corriger_ci":
                correction = prompts.correction_ci(self._erreur_ci(numero_pr))
            elif action.nom == "corriger_relecture":
                correction = prompts.correction_relecture(self._derniere_revue(pr))
            prompt = prompts.codeur(self.projet, numero=lot.numero, titre=lot.titre,
                                    chemin_brief=lot.brief(self.projet.dossier_briefs), correction=correction,
                                    consigne=self._consigne(lot))
        res = self._invoquer(poste or role, prompt, chemin, lot=lot.numero)
        passage = action.essai + 1
        essais = " · ".join(res.essais)
        if res.attente:
            self.noter(lot.numero, "attente", f"{role} : {essais}")
            if marquer_attente:
                self.marquer_attente(numero_pr, role, f"aucun agent n'a pu répondre : {essais}")
            return True
        if not res.reussi:
            self.gh.commenter_pr(numero_pr, f"🤖 **{role}** ({res.agent}) a échoué (code {res.code}).\n\n"
                                            f"Essais : {essais}\n\n"
                                            f"```\n{_extrait(res.texte, 40)}\n```\n\n"
                                            f"{marque(role=role, etat='echec', essai=passage, agent=str(res.agent))}")
            self.noter(lot.numero, f"{role} en échec", f"code {res.code} — {essais}", str(res.agent))
            return True
        interdits = [f for f in self.depot.changements(chemin) if self.projet.interdit(f)]
        if interdits:
            self.depot.annuler(chemin, interdits)
        if not self.depot.changements(chemin):
            self.gh.commenter_pr(numero_pr, f"🤖 **{role}** ({res.agent}) n'a rien changé.\n\n"
                                            f"{_extrait(res.texte, 30)}\n\n"
                                            f"{marque(role=role, etat='echec', essai=passage, agent=str(res.agent))}")
            self.noter(lot.numero, f"{role} sans changement", "", str(res.agent))
            return True
        quoi = "code" if action.essai == 0 else f"correction {action.essai}"
        if poste == "renfort":
            quoi += ", en renfort (dernier passage avant blocage)"
        sha = self.depot.enregistrer(chemin, f"Lot #{lot.numero} — {quoi}\n\nÉcrit par {res.agent}.")
        self.depot.pousser(chemin, branche)
        if pr.get("isDraft"):
            self.gh.pr_prete(numero_pr)
        retires = ("\n\n⚠️ Changements retirés, hors de portée d'un lot : "
                   + ", ".join(f"`{f}`" for f in interdits)) if interdits else ""
        vu = (photographe or self._photographier)(chemin, lot, sha)
        photos = "".join(f"\n\n📷 ![capture du lot #{lot.numero}]({url})" for url in vu.urls)
        note = f"\n\n{vu.note}" if vu.note else ""
        # Un agent cite ses fichiers par leur chemin sur la machine du lot :
        # dans la PR, ce sont des liens vers la branche.
        texte = res.texte.replace(f"{chemin}/", f"https://github.com/{self.gh.depot}/blob/{branche}/")
        self.gh.commenter_pr(numero_pr, f"🤖 **{role}** ({res.agent}) — {quoi}, révision `{sha[:7]}`.\n\n"
                                        f"{_extrait(texte)}{retires}{note}{photos}\n\n"
                                        + marque(role=role, etat="fait", essai=passage, agent=str(res.agent), sha=sha,
                                                 **vu.marque))
        self.noter(lot.numero, f"{role} : {quoi}", f"PR #{numero_pr}", str(res.agent))
        return True

    def _photographier(self, chemin: Path, lot: Lot, sha: str) -> Photos:
        return Photos(urls=captures.photographier_lot(self.depot, self.gh.depot, chemin, lot.numero, sha,
                                                      f"{self.maintenant():%Y-%m-%d}"))

    def marquer_attente(self, numero_pr: int, role: str, raison: str) -> None:
        """Le PC n'a pas pu travailler : la marque répond à l'envoi sans
        compter comme un passage du codeur, et le pilote renvoie dans l'heure."""
        quand = self.maintenant().isoformat(timespec="seconds")
        self.gh.commenter_pr(numero_pr, f"🤖 **{role}** (PC) : le lot attend — {raison}\n\n"
                                        "Aucun essai n'est compté ; le pilote renvoie le travail dans une heure.\n\n"
                                        f"{marque(role=role, etat='attente', quand=quand)}")

    def _erreur_ci(self, numero_pr: int) -> str:
        try:
            table = self.gh.gh("pr", "checks", str(numero_pr), "-R", self.gh.depot)
        except GitHubErreur as e:
            table = str(e)  # `gh pr checks` rend 1 quand un contrôle échoue
        morceaux = []
        for rouge in traces.rouges(table):
            morceaux.append(f"## {rouge.nom}\n{traces.lire(rouge) if rouge.travail else rouge.description}")
        return "\n\n".join(morceaux) or table

    def _derniere_revue(self, pr: dict) -> str:
        for c in reversed(pr.get("comments") or []):
            corps = c.get("body") or ""
            if any(m.get("role") == "relecteur" and m.get("verdict") == "CORRIGER" for m in lots.marques([c])):
                return lots._MARQUE.sub("", corps)
        return ""

    # ------------------------------------------------------------- relire
    def _relire(self, lot: Lot, pr: dict, branche: str, liste: list[dict]) -> bool:
        numero_pr, tete = pr["number"], pr["headRefOid"]
        echecs = [m for m in lots.depuis_reprise(liste)
                  if m.get("role") == "relecteur" and m.get("etat") == "echec" and m.get("sha") == tete]
        if len(echecs) >= 2:
            self._bloquer(lot.numero, "le relecteur a échoué deux fois sur la même révision", numero_pr)
            return False
        chemin = self.depot.preparer(lot.numero, branche)
        # Le relecteur n'a pas `gh` : ce que le codeur a dit sur la PR lui est
        # donné ici, comme une affirmation à vérifier.
        rapports = "\n\n".join(
            lots._MARQUE.sub("", c.get("body") or "").strip()
            for c in pr.get("comments") or []
            if any(m.get("role") in lots.ROLES_CODEURS and m.get("etat") == "fait" for m in lots.marques([c])))
        lisibles, illisibles = self._lfs_du_lot(chemin)
        prompt = prompts.relecteur(self.projet, numero=lot.numero, titre=lot.titre,
                                   chemin_brief=lot.brief(self.projet.dossier_briefs),
                                   url=pr.get("url", ""), sha=tete, rapports=rapports,
                                   lfs_lisibles=tuple(lisibles), lfs_illisibles=tuple(illisibles),
                                   consigne=self._consigne(lot))
        res = self._invoquer("relecteur", prompt, chemin, lot=lot.numero, exclure=lots.auteurs(liste))
        if res.personne:
            self._bloquer(lot.numero, "aucun relecteur possible : chaque famille de modèle du poste a écrit ce lot "
                                      f"({' · '.join(res.essais)})", numero_pr)
            return False
        if res.attente:
            self.noter(lot.numero, "attente", "relecteur : " + " · ".join(res.essais))
            return True
        verdicts = _VERDICT.findall(res.texte) if res.reussi else []
        if not verdicts:
            raison = f"code {res.code} ; {' · '.join(res.essais)}" if not res.reussi else "verdict illisible"
            self.gh.commenter_pr(numero_pr, f"🤖 **relecteur** ({res.agent}) : relecture sans verdict ({raison}).\n\n"
                                            f"{marque(role='relecteur', etat='echec', sha=tete, agent=str(res.agent))}")
            self.noter(lot.numero, "relecteur en échec", raison, str(res.agent))
            return True
        verdict = verdicts[-1]
        texte = _VERDICT.sub("", res.texte).strip()
        self.gh.commenter_pr(numero_pr, f"## Relecture — {verdict}\n\nRévision `{tete[:7]}` · relu par {res.agent}\n\n"
                                        f"{texte}\n\n{marque(role='relecteur', verdict=verdict, sha=tete, agent=str(res.agent))}")
        if verdict == "ACCEPTE":
            self.gh.fusion_auto(numero_pr, tete)
        self.noter(lot.numero, f"relecture {verdict}", f"PR #{numero_pr}", str(res.agent))
        return True

    def _lfs_du_lot(self, chemin: Path) -> tuple[list[str], list[str]]:
        """Les fichiers LFS du lot, rendus lisibles dans `.atelier/lfs/` du
        chantier (`lfs.py`). Un échec se dit au relecteur ; il ne bloque rien."""
        try:
            fichiers = self.depot.fichiers_du_lot(chemin)
        except DepotErreur as e:
            self.noter("lfs", "erreur", str(e))
            return [], []
        return lfs.rendre_lisibles(chemin, fichiers, self.gh.depot, telechargeur=self.lfs_telechargeur)

    def _consigne(self, lot: Lot) -> str:
        """La consigne du dépanneur qui vaut encore pour ce lot ; rien pour la
        réparation de master, qui n'a pas d'issue."""
        if "lot" not in lot.etiquettes:
            return ""
        try:
            return lots.consigne_du_depanneur(self.gh.issue(lot.numero).get("comments") or [])
        except GitHubErreur:
            return ""

    # ---------------------------------------------------------- dépanner
    def _depanner_un_lot(self, vue: "_Vue") -> bool:
        """Un lot que le pilote vient de bloquer, regardé par le dépanneur
        avant le propriétaire : un seul par tour, comme tout agent."""
        for lot in sorted(vue.ouvertes, key=lambda l: l.numero):
            if lot.etat != "bloque" or "lot" not in lot.etiquettes:
                continue
            if not self.verrous.prendre(_verrou_du_lot(lot.numero)):
                continue
            try:
                issue = self.gh.issue(lot.numero)
                lot = Lot.de(issue)
                commentaires = issue.get("comments") or []
                if lot.etat != "bloque" or not lots.depannage_a_faire(commentaires, self.projet.depannages_max):
                    continue
                return self._depanner(lot, commentaires)
            except (GitHubErreur, DepotErreur) as e:
                self.noter(lot.numero, "erreur", str(e))
            finally:
                self._lacher_lot(lot.numero)
        return False

    def _depanner(self, lot: Lot, commentaires: list[dict]) -> bool:
        """Le dépanneur lit le lot bloqué et décide : le relancer avec une
        consigne, poser la question au propriétaire, ou dire que la chaîne est
        en cause. Sans décision lisible, le lot attend le propriétaire."""
        liste = lots.marques(commentaires)
        raison = next((m.get("raison") or "" for m in reversed(liste) if m.get("etat") == "bloque"), "")
        relances = sum(1 for m in liste if m.get("role") == "depanneur" and m.get("etat") == lots.ETAT_DEPANNE)
        branche = lot.branche(self.projet.prefixe_branche)
        resume = self.gh.pr_de_branche(branche)
        pr = self.gh.pr(resume["number"]) if resume and resume.get("state") == "OPEN" else None
        erreur_ci = self._erreur_ci(pr["number"]) if pr is not None and etat_des_controles(pr)[0] == "rouge" else ""
        chemin = self.depot.preparer(lot.numero, branche)
        dit_issue = "\n\n".join(f"{(c.get('author') or {}).get('login', '?')} : "
                                 f"{_extrait(lots._MARQUE.sub('', c.get('body') or ''), 25)}"
                                 for c in commentaires[-8:])
        dit_pr = "\n\n".join(_extrait(lots._MARQUE.sub("", c.get("body") or ""), 40)
                              for c in (pr.get("comments") or [])[-10:]) if pr else ""
        prompt = prompts.depanneur(self.projet, numero=lot.numero, titre=lot.titre, corps=lot.corps, raison=raison,
                                   chemin_brief=lot.brief(self.projet.dossier_briefs), issue=dit_issue, pr=dit_pr,
                                   erreur_ci=erreur_ci, relances=relances)
        res = self._invoquer("depanneur", prompt, chemin, lot=lot.numero)
        if res.attente:
            self.noter(lot.numero, "attente", "dépanneur : " + " · ".join(res.essais))
            return True
        trouvees = list(_DECISION_DEPANNEUR.finditer(res.texte)) if res.reussi else []
        decision, motif, diagnostic = "", "", _extrait(res.texte, 40)
        if trouvees:
            m = trouvees[-1]
            decision = m.group(1)
            # La consigne suit « :: », ou les lignes d'après quand il passe à la ligne.
            motif = (m.group(2) or "").strip().strip("*_` ") or res.texte[m.end():].strip()[:3000]
            diagnostic = _extrait(res.texte[:m.start()], 40)
        numero_pr = pr["number"] if pr else None
        if decision == "REPRENDRE" and motif.strip():
            # La consigne vit dans la marque : « --> » la fermerait.
            consigne = motif.strip().replace("-->", "→")
            self.gh.commenter_issue(lot.numero, f"🤖 **dépanneur** ({res.agent}) : lot relancé "
                                                f"({relances + 1}/{self.projet.depannages_max}).\n\n{diagnostic}\n\n"
                                                f"**Consigne** : {consigne}\n\n"
                                                + marque(role="depanneur", etat=lots.ETAT_DEPANNE, consigne=consigne,
                                                         agent=str(res.agent)))
            self.gh.etiqueter(lot.numero, ["pret"], ["bloque"])
            self.noter(lot.numero, "dépanné", "remis pret", str(res.agent))
        elif decision == "QUESTION":
            question = lots.question_du_chef(res.texte, motif or "")
            self._bloquer(lot.numero, f"question au propriétaire : {question.texte}", numero_pr,
                          question=question, par=lots.PAR_DEPANNEUR, diagnostic=diagnostic)
        elif decision == "MODE-DIRECT" and motif.strip():
            self._bloquer(lot.numero, f"la chaîne est en cause, mode direct : {motif.strip()}", numero_pr,
                          par=lots.PAR_DEPANNEUR, diagnostic=diagnostic)
        else:
            pourquoi = f"code {res.code}" if not res.reussi else "décision illisible"
            self.gh.commenter_issue(lot.numero, f"🤖 **dépanneur** ({res.agent or '—'}) : pas de décision "
                                                f"({pourquoi}) ; le lot attend le propriétaire.\n\n"
                                                f"<details><summary>Ce qu'il a écrit</summary>\n\n{diagnostic}\n\n"
                                                "</details>\n\n" + marque(role="depanneur", etat="echec", raison=pourquoi))
            self.noter(lot.numero, "dépanneur en échec", pourquoi, str(res.agent or ""))
        return True

    # ------------------------------------------------------------ conflit
    def _conflit(self, lot: Lot, pr: dict, branche: str) -> bool:
        numero_pr = pr["number"]
        chemin = self.depot.preparer(lot.numero, branche)
        conflits = self.depot.fusionner_base(chemin)
        if not conflits:
            self.depot.pousser(chemin, branche)
            self.noter(lot.numero, "base fusionnée", "sans conflit")
            return False
        prompt = prompts.mecanicien_conflit(self.projet, numero=lot.numero, branche=branche, fichiers=conflits)
        res = self._invoquer("mecanicien", prompt, chemin, lot=lot.numero)
        if res.attente:
            self.depot.git_code("merge", "--abort", cwd=chemin)
            self.noter(lot.numero, "attente", "mécanicien : " + " · ".join(res.essais))
            return True
        restants = self.depot.marqueurs_restants(chemin, conflits)
        if not res.reussi or restants:
            self.depot.git_code("merge", "--abort", cwd=chemin)
            self._bloquer(lot.numero, "conflit non résolu : " + ", ".join(restants or conflits), numero_pr)
            return True
        sha = self.depot.conclure_fusion(chemin)
        self.depot.pousser(chemin, branche)
        self.gh.commenter_pr(numero_pr, f"🤖 **mécanicien** ({res.agent}) : conflit avec `{self.projet.branche_base}` "
                                        f"résolu ({', '.join(conflits)}), révision `{sha[:7]}`.\n\n"
                                        f"{marque(role='mecanicien', etat='fait', sha=sha, agent=str(res.agent))}")
        self.noter(lot.numero, "conflit résolu", ", ".join(conflits), str(res.agent))
        return True

    # ----------------------------------------------------------------- PC
    def _envoyer_pc(self, lot: Lot, pr: dict, branche: str, action: lots.Action) -> None:
        numero_pr = pr["number"]
        self.gh.lancer_workflow("lot-pc.yml", self.projet.branche_base, {
            "issue": str(lot.numero), "branche": branche, "pr": str(numero_pr),
            "essai": str(action.essai), "action": action.nom})
        quand = self.maintenant().isoformat(timespec="seconds")
        self.gh.commenter_pr(numero_pr, f"🤖 **pilote** : travail envoyé au PC ({action.nom}). Il part quand le PC "
                                        "est allumé ; sans réponse en 24 h, il est renvoyé.\n\n"
                                        + marque(role="codeur_3d", etat="envoye", essai=action.essai + 1,
                                                 action=action.nom, quand=quand))
        self.noter(lot.numero, "envoyé au PC", action.nom)

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

    def _livrer_les_fermes(self, fermees: list[dict] | None = None) -> None:
        """Une PR fusionnée ferme son issue (« Closes #N ») avant que le
        pilote ne la voie : l'issue fermée encore « en-cours » est livrée."""
        for issue in self.gh.issues("closed") if fermees is None else fermees:
            lot = Lot.de(issue)
            if lot.etat == "en-cours" and not self._pris_ailleurs(lot.numero):
                resume = self.gh.pr_de_branche(lot.branche(self.projet.prefixe_branche))
                if resume and (resume.get("mergedAt") or resume.get("state") == "MERGED"):
                    self._livrer(lot.numero, resume["number"])

    def _bloquer(self, numero: int, raison: str, numero_pr: int | None = None, *,
                 question: lots.Question | None = None, par: str | None = None, diagnostic: str = "") -> None:
        """Bloque le lot, avec sa raison. `par` le dépanneur : ce blocage est
        sa décision, il ne le regarde pas une seconde fois, et son
        `diagnostic` l'accompagne."""
        self.gh.etiqueter(numero, ["bloque"], ["en-cours", "pret", "idee"])
        reprendre = ("sa PR reste ouverte : le pilote la reprend où elle en est, sans relancer le chef, "
                     "et ses essais repartent de zéro" if numero_pr else
                     "le chef reprend le lot, avec ses essais remis à zéro")
        if question is None:
            texte = (f"🤖 **pilote** : lot bloqué — {raison}.\n\n"
                     "Pour le reprendre : corriger la cause (en mode direct si elle est dans la chaîne), puis "
                     "écrire un commentaire ici, ce qui a été fait ou ta décision. Au tour suivant, le pilote "
                     f"remet le lot en route : {reprendre}. Retirer « bloque » et remettre « pret » marche aussi.")
            champs = {}
        else:
            qui = "le dépanneur" if par == lots.PAR_DEPANNEUR else "le chef"
            options = "".join(f"\n- **{l}** — {r}" + (f" ({c})" if c else "") for l, r, c in question.options)
            reco = ""
            if question.recommandation:
                lettre, pourquoi = question.recommandation
                reco = f"\n\n{qui.capitalize()} recommande **{lettre}**" + (f" : {pourquoi}" if pourquoi else "") + "."
            texte = (f"🤖 **pilote** : lot bloqué — {qui} attend ta décision.\n\n**{question.texte}**\n"
                     f"{options}{reco}\n\n"
                     "**Pour répondre** : écris un commentaire ici (une lettre suffit, ou ta propre réponse). "
                     "Au tour suivant, le pilote remet le lot en route, et le chef lit ta réponse.")
            champs = question.marque()
        if par:
            champs["par"] = par
        if diagnostic:
            texte += f"\n\n<details><summary>Le diagnostic du dépanneur</summary>\n\n{diagnostic}\n\n</details>"
        self.gh.commenter_issue(numero, f"{texte}\n\n{marque(role='pilote', etat='bloque', raison=raison, **champs)}")
        self.noter(numero, "bloqué", raison)

    # ------------------------------------------------------------ jalons
    def _ranger_jalons(self) -> None:
        for jalon in lots.jalons(self.gh.jalons()):
            if jalon.ouvert and jalon.ouvertes == 0 and jalon.fermees > 0:
                self.gh.fermer_jalon(jalon.id)
                self.noter(f"J{jalon.numero}", "jalon atteint", jalon.titre)

    # ----------------------------------------------------- master rouge
    def _master_rouge(self) -> bool:
        """Master rouge : un mécanicien à la fois, quel que soit le tour."""
        if not self.verrous.prendre("meca"):
            return False
        try:
            return self._reparer_master()
        finally:
            self.verrous.lacher("meca")

    def _reparer_master(self) -> bool:
        ouvertes = [p for p in self.gh.prs_ouvertes() if p["headRefName"].startswith("meca/")]
        if ouvertes:
            return self._avancer_meca(ouvertes[0])
        run = self.gh.dernier_run("tests.yml", self.projet.branche_base)
        if not run or run.get("status") != "completed" or run.get("conclusion") != "failure":
            return False
        branche = f"meca/{self.maintenant():%Y%m%d-%H%M}-master-rouge"
        chemin = self.depot.preparer("meca", branche)
        erreur = ""
        try:
            erreur = traces.lire_run(self.gh.depot, run["databaseId"])
        except Exception:  # noqa: BLE001 — un journal illisible ne retient pas la réparation
            erreur = ""
        prompt = prompts.mecanicien_master(self.projet, url=run.get("url", ""), erreur=erreur)
        res = self._invoquer("mecanicien", prompt, chemin, lot="master")
        if res.attente:
            self.noter("master", "attente", "mécanicien : " + " · ".join(res.essais))
            return True
        decisions = _DECISION.findall(res.texte)
        if decisions and decisions[-1][0] == "MODE-DIRECT":
            self.noter("master", "rouge, mode direct requis", decisions[-1][1], str(res.agent))
            return True
        interdits = [f for f in self.depot.changements(chemin) if self.projet.interdit(f)]
        if interdits:
            self.depot.annuler(chemin, interdits)
        if not res.reussi or not self.depot.changements(chemin):
            self.noter("master", "mécanicien sans réparation", f"code {res.code}", str(res.agent or ""))
            return True
        sha = self.depot.enregistrer(chemin, f"Mécanicien : master rouge (run {run['databaseId']})\n\nÉcrit par {res.agent}.")
        self.depot.pousser(chemin, branche)
        numero_pr = self.gh.creer_pr(branche, self.projet.branche_base, "Mécanicien : master est rouge",
                                     f"La CI de `{self.projet.branche_base}` est rouge : {run.get('url', '')}.\n\n"
                                     f"{_extrait(res.texte, 40)}" + SIGNATURE, brouillon=False)
        self.gh.commenter_pr(numero_pr, f"🤖 **mécanicien** ({res.agent}) : réparation proposée.\n\n"
                                        f"{marque(role='mecanicien_master', etat='fait', essai=1, agent=str(res.agent), sha=sha)}")
        self.noter("master", "réparation proposée", f"PR #{numero_pr}", str(res.agent))
        return True

    def _avancer_meca(self, resume: dict) -> bool:
        pr = self.gh.pr(resume["number"])
        liste = lots.marques(pr.get("comments") or [])
        etat_ci, _ = etat_des_controles(pr)
        action = lots.action_suivante(pr, etat_ci, liste, corrections_max=self.projet.corrections_max,
                                      role_codeur="mecanicien_master")
        faux = Lot(numero=pr["number"], titre=pr.get("title", "master rouge"), corps="", etiquettes=(),
                   jalon=None, jalon_titre=None)
        if action.nom == "relire":
            return self._relire(faux, pr, pr["headRefName"], liste)
        if action.nom == "fusionner":
            self.gh.fusion_auto(pr["number"], pr.get("headRefOid"))
            self.noter("master", "fusion automatique demandée", f"PR #{pr['number']}")
            return False
        if action.nom in ("corriger_ci", "corriger_relecture"):
            erreur = (self._erreur_ci(pr["number"]) if action.nom == "corriger_ci"
                      else prompts.correction_relecture(self._derniere_revue(pr)))
            prompt = prompts.mecanicien_master(self.projet, url=pr.get("url", ""), erreur=erreur)
            return self._coder(faux, pr, pr["headRefName"], action, liste, role="mecanicien_master",
                               poste="mecanicien", chantier="meca", prompt=prompt)
        if action.nom == "bloquer":
            self.gh.commenter_pr(pr["number"], f"🤖 **pilote** : réparation bloquée — {action.raison}. "
                                               "Mode direct requis.")
            self.gh.fermer_pr(pr["number"], "Fermée par le pilote : la réparation automatique n'a pas abouti.")
            self.noter("master", "réparation abandonnée", action.raison)
            return False
        self.noter("master", action.nom, f"PR #{pr['number']}")
        return False
