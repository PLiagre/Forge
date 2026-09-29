"""Le pilote : un tour de la chaîne.

Un tour relit GitHub, fait avancer chaque lot en cours d'un pas, et prend
le lot suivant du jalon courant quand une machine est libre ; une machine qui
n'y a plus rien à prendre prend dans le jalon suivant (la fenêtre de deux
jalons). Il invoque au plus UN agent par tour : un tour reste court à lire,
et un quota ne se vide pas en une minute. Tout ce qui se décide se décide dans `lots.py`, en
fonction pure ; ici, on fait les gestes.

    un lot = une issue → le chef écrit le brief dans la branche du lot et
    ouvre la PR → le codeur code → la CI joue les tests → le relecteur rend
    ACCEPTE ou CORRIGER → ACCEPTE : fusion automatique ; CORRIGER : le
    codeur corrige, deux fois au plus, puis le lot est « bloque », avec sa
    raison.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Callable

from . import agents as agents_mod
from . import captures, lots, prompts, traces
from .depot import Depot, DepotErreur
from .github import GitHub, GitHubErreur, etat_des_controles
from .lots import Lot, marque
from .projet import Projet

_DECISION = re.compile(r"^\s*DECISION:\s*(BRIEF|REFUS|DECOUPE|MODE-DIRECT)\b[ \t]*(?:::[ \t]*(.*))?$", re.M)
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


_MACHINE_DU_SOUS_LOT = re.compile(r"\s*::\s*(pc|vps)\s*$", re.I)


def _machine_du_sous_lot(quoi: str, defaut: str) -> tuple[str, str]:
    """« … :: pc » en fin de ligne : ce sous-lot demande Unity ou Blender ;
    « :: vps », Python seul. Sans rien, il garde la machine du lot découpé."""
    m = _MACHINE_DU_SOUS_LOT.search(quoi)
    return (quoi[:m.start()].strip(), m.group(1).lower()) if m else (quoi.strip(), defaut)


def _extrait(texte: str, lignes: int = 60) -> str:
    morceaux = texte.strip().splitlines()
    if len(morceaux) <= lignes:
        return "\n".join(morceaux)
    return "\n".join(morceaux[:lignes]) + f"\n… ({len(morceaux) - lignes} lignes de plus)"


class Pilote:
    def __init__(self, projet: Projet, gh: GitHub, depot: Depot, *,
                 executeur_agents: agents_mod.Executeur = agents_mod.executer,
                 maintenant=None, journal: Path | None = None):
        self.projet = projet
        self.gh = gh
        self.depot = depot
        self.executeur_agents = executeur_agents
        self.maintenant = maintenant or (lambda: datetime.now(timezone.utc))
        self.journal = journal or Path.home() / ".atelier" / "journal.jsonl"
        self.lignes: list[str] = []

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
                                  exclure=exclure, executeur=self.executeur_agents)
        # Un secours a répondu : pourquoi les précédents ne l'ont pas fait
        # entre au journal, sinon un quota ou une session perdue ne se voit
        # nulle part (le chef de #184, le 28 septembre 2026).
        refus = [e for e in res.essais[:-1] if "écarté" not in e]
        if res.agent is not None and refus:
            self.noter(lot, "secours", f"{role} : " + " · ".join(refus), str(res.agent))
        return res

    # --------------------------------------------------------------- tour
    def tour(self) -> list[str]:
        self.lignes = []
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
        if self._attendre_dependances(ouvertes, bloq) | self._reprendre(ouvertes, bloq):
            ouvertes = [Lot.de(i) for i in self.gh.issues("open")]
        self._livrer_les_fermes(fermees)
        fermes = [Lot.de(i) for i in fermees]
        decoupe_du_courant = lots.a_decouper(courant, cap, ouvertes, fermes)
        if decoupe_du_courant:
            self._faire_decouper(courant, ouvertes)

        occupe = {"vps": False, "pc": False}
        agent_parti = False
        for lot in sorted(ouvertes, key=lambda l: l.numero):
            if lot.etat != "en-cours":
                continue
            occupe[lot.machine] = True
            if agent_parti:
                continue
            try:
                agent_parti = self._avancer(lot, jalons, courant) or agent_parti
            except (GitHubErreur, DepotErreur) as e:
                self.noter(lot.numero, "erreur", str(e))

        if not agent_parti:
            agent_parti = self._master_rouge()
        if not agent_parti and courant is not None:
            libres = {m: not o for m, o in occupe.items()}
            candidats = [l for l in ouvertes if "lot" in l.etiquettes]
            suivant = lots.a_prendre(candidats, courant.numero, libres, bloq)
            # La fenêtre de deux jalons : une machine libre qui n'a plus rien
            # à prendre dans le jalon courant prend dans le suivant, et le
            # découpe s'il n'a encore rien. Le 29 septembre 2026, J1 n'avait
            # plus que des lots « pc » : le VPS attendait sans rien faire que
            # le PC finisse, alors que J2 ne demande que `sim/`.
            if suivant is None and apres is not None and any(libres.values()) and not decoupe_du_courant:
                if lots.a_decouper(apres, cap, ouvertes, fermes):
                    self._faire_decouper(apres, ouvertes, courant)
                suivant = lots.a_prendre(candidats, apres.numero, libres, bloq)
            if suivant is not None:
                try:
                    self._chef(suivant, suivant.jalon_titre or courant.titre, courant)
                except (GitHubErreur, DepotErreur) as e:
                    self.noter(suivant.numero, "erreur", str(e))
        self._ranger_jalons()
        if not self.lignes:
            self.lignes.append("RIEN")
        return self.lignes

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

    def _faire_decouper(self, jalon: lots.Jalon, ouvertes: list[Lot], courant: lots.Jalon | None = None) -> None:
        """Un jalon qui commence sans plan se fait découper : le pilote ouvre
        le lot de sa découpe, que le chef prend comme un autre. Le jalon
        suivant se découpe en avance quand une machine n'a plus rien dans le
        `courant`."""
        avant = sorted(l.numero for l in ouvertes
                       if l.jalon == jalon.numero and "lot" in l.etiquettes and l.etat == "idee")
        en_avance = courant is not None and jalon.numero > courant.numero
        try:
            n = self.gh.creer_issue(f"Découper le jalon {jalon.titre}",
                                    lots.corps_de_la_decoupe(jalon, avant, courant if en_avance else None),
                                    ["lot", "pret"], jalon.titre)
            self.noter(n, "jalon à découper", jalon.titre + (" (en avance)" if en_avance else ""))
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
            if lot.etat != "en-cours" or not attend:
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

    def _reprendre(self, ouvertes: list[Lot], bloq: frozenset[int] = frozenset()) -> set[int]:
        """Un lot remis « pret » alors que sa PR est ouverte reprend où il en
        est, dès que ses dépendances sont livrées. Relancer le chef coûterait
        un quota, et buterait sur la branche et la PR qui existent déjà. La
        marque « reprise » sur la PR remet les compteurs à zéro
        (`lots.depuis_reprise`) ; elle s'écrit avant l'étiquette : sans elle,
        un lot « en-cours » recompterait ses échecs et serait rebloqué."""
        prets = [l for l in ouvertes if l.etat == "pret" and "lot" in l.etiquettes and not l.dependances & bloq]
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
            return self._coder(lot, pr, branche, action, liste, role="codeur", chantier=lot.numero)
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
        commentaires = "\n\n".join(
            f"{(c.get('author') or {}).get('login', '?')} : {c.get('body', '')}"
            for c in issue.get("comments") or [] if "<!-- atelier" not in (c.get("body") or ""))
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
        sous = _SOUS_LOT.findall(apres)
        if not sous:
            self.gh.commenter_issue(lot.numero, "🤖 **chef** : découpe demandée, mais aucun sous-lot lisible.\n\n"
                                    f"{marque(role='chef', etat='echec', raison='découpe illisible')}")
            self.noter(lot.numero, "chef en échec", "découpe illisible", str(res.agent))
            return True
        crees = []
        for titre, quoi in sous:
            quoi, machine = _machine_du_sous_lot(quoi, lot.machine)
            etiquettes = ["lot", "pret"] + ([lots.ETIQUETTE_PC] if machine == "pc" else [])
            # Les sous-lots se suivent dans l'ordre du chef : un morceau
            # bloqué retient les suivants, qui s'appuient sur lui.
            suite = f"\n\nDépend de : #{crees[-1]}" if crees else ""
            n = self.gh.creer_issue(titre.strip(), f"{quoi}\n\nDécoupé du lot #{lot.numero} par le chef.{suite}",
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
                                    chemin_brief=lot.brief(self.projet.dossier_briefs), correction=correction)
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
        prompt = prompts.relecteur(self.projet, numero=lot.numero, titre=lot.titre,
                                   chemin_brief=lot.brief(self.projet.dossier_briefs),
                                   url=pr.get("url", ""), sha=tete, rapports=rapports)
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
            if lot.etat == "en-cours":
                resume = self.gh.pr_de_branche(lot.branche(self.projet.prefixe_branche))
                if resume and (resume.get("mergedAt") or resume.get("state") == "MERGED"):
                    self._livrer(lot.numero, resume["number"])

    def _bloquer(self, numero: int, raison: str, numero_pr: int | None = None) -> None:
        self.gh.etiqueter(numero, ["bloque"], ["en-cours", "pret", "idee"])
        reprendre = ("sa PR reste ouverte : le pilote la reprend où elle en est, sans relancer le chef, "
                     "et ses essais repartent de zéro" if numero_pr else
                     "le chef reprend le lot, avec ses essais remis à zéro")
        self.gh.commenter_issue(numero, f"🤖 **pilote** : lot bloqué — {raison}.\n\n"
                                        "Pour le reprendre, corriger la cause (en mode direct si elle est dans la "
                                        f"chaîne), puis retirer « bloque » et remettre « pret » : {reprendre}.\n\n"
                                        f"{marque(role='pilote', etat='bloque', raison=raison)}")
        self.noter(numero, "bloqué", raison)

    # ------------------------------------------------------------ jalons
    def _ranger_jalons(self) -> None:
        for jalon in lots.jalons(self.gh.jalons()):
            if jalon.ouvert and jalon.ouvertes == 0 and jalon.fermees > 0:
                self.gh.fermer_jalon(jalon.id)
                self.noter(f"J{jalon.numero}", "jalon atteint", jalon.titre)

    # ----------------------------------------------------- master rouge
    def _master_rouge(self) -> bool:
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
