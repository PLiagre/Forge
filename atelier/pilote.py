"""Le pilote : un tour de la chaîne.

Un tour relit GitHub, fait avancer chaque lot en cours d'un pas, et prend
le lot suivant du jalon courant quand une machine est libre. Il invoque au
plus UN agent par tour : un tour reste court à lire, et un quota ne se vide
pas en une minute. Tout ce qui se décide se décide dans `lots.py`, en
fonction pure ; ici, on fait les gestes.

    un lot = une issue → le chef écrit le brief dans la branche du lot et
    ouvre la PR → le codeur code → la CI joue les tests → le relecteur rend
    ACCEPTE ou CORRIGER → ACCEPTE : fusion automatique ; CORRIGER : le
    codeur corrige, deux fois au plus, puis le lot est « bloque », avec sa
    raison.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re

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

    def _invoquer(self, role: str, prompt: str, chemin: Path, *, exclure=frozenset()) -> agents_mod.Resultat:
        return agents_mod.invoquer(self.projet.poste(role), prompt, chemin, self.projet.delai(role),
                                   exclure=exclure, executeur=self.executeur_agents)

    # --------------------------------------------------------------- tour
    def tour(self) -> list[str]:
        self.lignes = []
        self.depot.fetch()
        jalons = lots.jalons(self.gh.jalons())
        courant = lots.jalon_courant(jalons)
        ouvertes = [Lot.de(i) for i in self.gh.issues("open")]
        self._normaliser(ouvertes, jalons)
        ouvertes = [Lot.de(i) for i in self.gh.issues("open")]
        self._livrer_les_fermes()

        occupe = {"vps": False, "pc": False}
        agent_parti = False
        for lot in sorted(ouvertes, key=lambda l: l.numero):
            if lot.etat != "en-cours":
                continue
            occupe[lot.machine] = True
            if agent_parti:
                continue
            try:
                agent_parti = self._avancer(lot, jalons) or agent_parti
            except (GitHubErreur, DepotErreur) as e:
                self.noter(lot.numero, "erreur", str(e))

        if not agent_parti:
            agent_parti = self._master_rouge()
        if not agent_parti and courant is not None:
            libres = {m: not o for m, o in occupe.items()}
            candidats = [l for l in ouvertes if "lot" in l.etiquettes]
            suivant = lots.a_prendre(candidats, courant.numero, libres, frozenset(l.numero for l in ouvertes))
            if suivant is not None:
                try:
                    self._chef(suivant, courant.titre)
                except (GitHubErreur, DepotErreur) as e:
                    self.noter(suivant.numero, "erreur", str(e))
        self._ranger_jalons()
        if not self.lignes:
            self.lignes.append("RIEN")
        return self.lignes

    # ------------------------------------------------------- normaliser
    def _normaliser(self, ouvertes: list[Lot], jalons: list[lots.Jalon]) -> None:
        """Une issue du formulaire porte son jalon et sa machine dans le texte :
        le pilote les pose en milestone et en étiquette, une fois."""
        par_numero = {j.numero: j for j in jalons}
        for lot in ouvertes:
            if not any(e in lot.etiquettes for e in lots.ETATS) and "lot" in lot.etiquettes:
                self.gh.etiqueter(lot.numero, ["idee"])
            m = re.search(r"### Jalon\s+J(\d+)", lot.corps)
            if lot.jalon is None and m and int(m.group(1)) in par_numero:
                self.gh.jalon_de(lot.numero, par_numero[int(m.group(1))].titre)
            if re.search(r"### Machine\s+pc\b", lot.corps, re.I) and lots.ETIQUETTE_PC not in lot.etiquettes:
                self.gh.etiqueter(lot.numero, [lots.ETIQUETTE_PC])

    # ---------------------------------------------------------- avancer
    def _avancer(self, lot: Lot, jalons: list[lots.Jalon]) -> bool:
        branche = lot.branche(self.projet.prefixe_branche)
        resume = self.gh.pr_de_branche(branche)
        if resume is None:
            titre_jalon = lot.jalon_titre or next((j.titre for j in jalons if j.numero == lot.jalon), "")
            return self._chef(lot, titre_jalon)
        pr = self.gh.pr(resume["number"])
        liste = lots.marques(pr.get("comments") or [])
        etat_ci, _ = etat_des_controles(pr)
        role = "codeur_3d" if lot.machine == "pc" else "codeur"
        action = lots.action_suivante(pr, etat_ci, liste, corrections_max=self.projet.corrections_max,
                                      role_codeur=role, heures_depuis_envoi_pc=self._heures_envoi(liste, role))
        numero_pr = pr["number"]
        if action.nom == "livrer":
            self._livrer(lot.numero, numero_pr)
            return False
        if action.nom == "bloquer":
            self._bloquer(lot.numero, action.raison, numero_pr)
            return False
        if action.nom.startswith("attendre"):
            self.noter(lot.numero, action.nom, f"PR #{numero_pr}")
            return False
        if action.nom == "fusionner":
            self.gh.fusion_auto(numero_pr)
            self.noter(lot.numero, "fusion automatique demandée", f"PR #{numero_pr}")
            return False
        if action.nom == "conflit":
            return self._conflit(lot, pr, branche)
        if action.nom in ("coder", "corriger_ci", "corriger_relecture", "relancer_pc"):
            if lot.machine == "pc":
                self._envoyer_pc(lot, pr, branche, action)
                return False
            return self._coder(lot, pr, branche, action, liste, role="codeur", chantier=lot.numero)
        if action.nom == "relire":
            return self._relire(lot, pr, branche, liste)
        if action.nom == "chef":
            return self._chef(lot, lot.jalon_titre or "")
        self.noter(lot.numero, "action inconnue", action.nom)
        return False

    def _heures_envoi(self, liste: list[dict], role: str) -> float | None:
        envois = [m for m in liste if m.get("role") == role and m.get("etat") == "envoye" and m.get("quand")]
        if not envois:
            return None
        depuis = datetime.fromisoformat(envois[-1]["quand"])
        return (self.maintenant() - depuis).total_seconds() / 3600

    # --------------------------------------------------------------- chef
    def _chef(self, lot: Lot, titre_jalon: str) -> bool:
        issue = self.gh.issue(lot.numero)
        echecs = [m for m in lots.marques(issue.get("comments") or []) if m.get("role") == "chef" and m.get("etat") == "echec"]
        if len(echecs) >= 2:
            self._bloquer(lot.numero, f"le chef a échoué {len(echecs)} fois")
            return False
        branche = lot.branche(self.projet.prefixe_branche)
        chemin_brief = lot.brief(self.projet.dossier_briefs)
        chemin = self.depot.preparer(lot.numero, branche)
        commentaires = "\n\n".join(
            f"{(c.get('author') or {}).get('login', '?')} : {c.get('body', '')}"
            for c in issue.get("comments") or [] if "<!-- atelier" not in (c.get("body") or ""))
        prompt = prompts.chef(self.projet, numero=lot.numero, titre=lot.titre, corps=lot.corps,
                              commentaires=commentaires, jalon=lot.jalon or 0, jalon_titre=titre_jalon,
                              machine=lot.machine, chemin_brief=chemin_brief)
        res = self._invoquer("chef", prompt, chemin)
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
            raison = f"le chef a rendu le code {res.code}"
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
            etiquettes = ["lot", "pret"] + ([lots.ETIQUETTE_PC] if lot.machine == "pc" else [])
            n = self.gh.creer_issue(titre.strip(), f"{quoi.strip()}\n\nDécoupé du lot #{lot.numero} par le chef.",
                                    etiquettes, titre_jalon or None)
            crees.append(n)
        liste = ", ".join(f"#{n}" for n in crees)
        self.gh.fermer_issue(lot.numero, f"🤖 **chef** ({res.agent}) : trop gros pour un lot, découpé en {liste}.",
                             abandon=True)
        self.noter(lot.numero, "découpé", liste, str(res.agent))
        return True

    # ------------------------------------------------------------- coder
    def _coder(self, lot: Lot, pr: dict, branche: str, action: lots.Action, liste: list[dict], *,
               role: str, chantier: str | int, poste: str | None = None, prompt: str | None = None) -> bool:
        """Un passage du codeur (ou du mécanicien) sur la branche d'une PR.

        `role` est le nom écrit dans la marque ; `poste` celui de la ligne de
        `[agents]` qui répond (le même, sauf pour le mécanicien de master)."""
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
        res = self._invoquer(poste or role, prompt, chemin)
        passage = action.essai + 1
        if res.attente:
            self.noter(lot.numero, "attente", f"{role} : " + " · ".join(res.essais))
            return True
        if not res.reussi:
            self.gh.commenter_pr(numero_pr, f"🤖 **{role}** ({res.agent}) a échoué (code {res.code}).\n\n"
                                            f"```\n{_extrait(res.texte, 40)}\n```\n\n"
                                            f"{marque(role=role, etat='echec', essai=passage, agent=str(res.agent))}")
            self.noter(lot.numero, f"{role} en échec", f"code {res.code}", str(res.agent))
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
        images = captures.photographier_lot(self.depot, self.gh.depot, chemin, lot.numero, sha,
                                            f"{self.maintenant():%Y-%m-%d}")
        photos = "".join(f"\n\n📷 ![capture du lot #{lot.numero}]({url})" for url in images)
        self.gh.commenter_pr(numero_pr, f"🤖 **{role}** ({res.agent}) — {quoi}, révision `{sha[:7]}`.\n\n"
                                        f"{_extrait(res.texte)}{retires}{photos}\n\n"
                                        f"{marque(role=role, etat='fait', essai=passage, agent=str(res.agent), sha=sha)}")
        self.noter(lot.numero, f"{role} : {quoi}", f"PR #{numero_pr}", str(res.agent))
        return True

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
        echecs = [m for m in liste if m.get("role") == "relecteur" and m.get("etat") == "echec" and m.get("sha") == tete]
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
        res = self._invoquer("relecteur", prompt, chemin, exclure=lots.auteurs(liste))
        if res.personne:
            self._bloquer(lot.numero, "aucun relecteur possible : chaque outil du poste a écrit ce lot", numero_pr)
            return False
        if res.attente:
            self.noter(lot.numero, "attente", "relecteur : " + " · ".join(res.essais))
            return True
        verdicts = _VERDICT.findall(res.texte) if res.reussi else []
        if not verdicts:
            raison = f"code {res.code}" if not res.reussi else "verdict illisible"
            self.gh.commenter_pr(numero_pr, f"🤖 **relecteur** ({res.agent}) : relecture sans verdict ({raison}).\n\n"
                                            f"{marque(role='relecteur', etat='echec', sha=tete, agent=str(res.agent))}")
            self.noter(lot.numero, "relecteur en échec", raison, str(res.agent))
            return True
        verdict = verdicts[-1]
        texte = _VERDICT.sub("", res.texte).strip()
        self.gh.commenter_pr(numero_pr, f"## Relecture — {verdict}\n\nRévision `{tete[:7]}` · relu par {res.agent}\n\n"
                                        f"{texte}\n\n{marque(role='relecteur', verdict=verdict, sha=tete, agent=str(res.agent))}")
        if verdict == "ACCEPTE":
            self.gh.fusion_auto(numero_pr)
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
        res = self._invoquer("mecanicien", prompt, chemin)
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
        self.gh.commenter_pr(numero_pr, f"🤖 **pilote** : travail envoyé au PC ({action.nom}).\n\n"
                                        f"{marque(role='codeur_3d', etat='envoye', essai=action.essai + 1, quand=quand)}")
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

    def _livrer_les_fermes(self) -> None:
        """Une PR fusionnée ferme son issue (« Closes #N ») avant que le
        pilote ne la voie : l'issue fermée encore « en-cours » est livrée."""
        for issue in self.gh.issues("closed"):
            lot = Lot.de(issue)
            if lot.etat == "en-cours":
                resume = self.gh.pr_de_branche(lot.branche(self.projet.prefixe_branche))
                if resume and (resume.get("mergedAt") or resume.get("state") == "MERGED"):
                    self._livrer(lot.numero, resume["number"])

    def _bloquer(self, numero: int, raison: str, numero_pr: int | None = None) -> None:
        self.gh.etiqueter(numero, ["bloque"], ["en-cours", "pret", "idee"])
        self.gh.commenter_issue(numero, f"🤖 **pilote** : lot bloqué — {raison}.\n\n"
                                        "Pour le reprendre : retirer « bloque » et remettre « pret », "
                                        "ou corriger en mode direct.\n\n"
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
        res = self._invoquer("mecanicien", prompt, chemin)
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
            self.gh.fusion_auto(pr["number"])
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
