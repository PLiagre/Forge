"""Le testeur : il joue le build figé d'une étape comme un joueur, avant le propriétaire.

Le relecteur juge un diff et des captures prises à des endroits choisis
d'avance ; personne ne jouait. Une démo réussie par script prouve que le
chemin existe, pas qu'un joueur le trouve. Le testeur ne connaît que la
promesse de l'étape, la vision du jeu et les ordres de grandeur de 1400 ; il
joue par la seule fenêtre du jeu (`jouer_le_build.ps1`), compte ses essais,
et rend un récit prouvé par ses photos.

Son verdict pèse, donc il ne se croit pas sur parole : `verdict_qui_pese` le
recalcule d'après ce qu'il rapporte (un objectif bloqué, un défaut bloquant,
une réussite sans photo) et ne garde que le plus dur.

Il joue sur le PC, dans la session Windows ouverte du propriétaire : c'est le
seul endroit où le jeu a un écran. Le pilote du VPS l'envoie par
`testeur-pc.yml` ; le runner, qui tourne en service et n'a pas de bureau,
démarre la tâche planifiée « ForgeTesteur », qui lance `python -m atelier
testeur` dans la session ouverte. Le passage répond toujours sur l'issue de
l'étape : son rapport, ou une attente. Il ne lance rien tant que le
propriétaire est au clavier, et s'arrête dès qu'il reprend la main.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Callable

from . import agents as agents_mod
from . import captures, consignes, journal as journal_mod, lots
from .depot import Depot
from .github import GitHub
from .lots import Lot, marque
from .projet import TESTEUR, Projet
from .verrous import AucunVerrou

ICI = Path(__file__).resolve().parent
OUTIL = ICI / "jouer_le_build.ps1"
GARDE = ICI / "garde_testeur.py"
REPERES = ICI / "reperes-1400.md"

# La marque d'un passage qui a rendu un verdict.
JOUE = "joue"
TENUE, AVEC_PEINE, NON_TENUE = "TENUE", "TENUE_AVEC_PEINE", "NON_TENUE"
# Du plus doux au plus dur : un verdict ne se recalcule que vers le plus dur.
VERDICTS = (TENUE, AVEC_PEINE, NON_TENUE)
# Ce qui n'est pas un verdict : il a dû rendre l'écran au propriétaire, ou
# son récit ne prouve rien.
INTERROMPU, SANS_PREUVE = "INTERROMPU", "SANS_PREUVE"
EN_CLAIR = {TENUE: "PROMESSE TENUE", AVEC_PEINE: "TENUE AVEC PEINE", NON_TENUE: "NON TENUE",
            INTERROMPU: "INTERROMPU", SANS_PREUVE: "SANS PREUVE"}
# Au-delà, un objectif trouvé n'était pas trouvable : il compte comme bloqué.
ESSAIS_MAX = 5
# Ce qu'un passage joue au plus ; l'outil refuse le geste suivant.
GESTES_MAX = 60
# Le propriétaire est tenu pour absent après tant de secondes sans clavier ni souris.
INACTIVITE = 600
# Le passage attend que le bureau se libère, tant de secondes au plus, en le
# regardant à ce pas ; au-delà il répond par une attente, et le pilote renvoie.
ATTENTE_DU_BUREAU, PAS_DU_BUREAU = 2700, 30
# Les photos publiées avec le rapport, au plus : celles qu'il cite.
PHOTOS_MAX = 24
_RESULTATS = {"premier_coup": "du premier coup", "apres_essais": "trouvé après {n} essais",
              "bloque": "**bloqué** après {n} essais", "non_joue": "**pas joué**"}


# ------------------------------------------------------------- le verdict
def verdict_qui_pese(sortie: dict, photos: set[str]) -> tuple[str, list[str]]:
    """Le verdict que la chaîne retient, et pourquoi il diffère de celui du
    testeur. `photos` : les noms des photos qui existent vraiment.

    Un récit sans objectif, ou une réussite qu'aucune photo ne montre, ne
    prouve rien : `SANS_PREUVE`. Sinon le plus dur de ce qu'il dit et de ce
    que ses objectifs et ses défauts imposent : un objectif bloqué, pas joué
    ou trouvé après plus de `ESSAIS_MAX` essais, ou un défaut bloquant, et
    l'étape n'est pas tenue ; un objectif trouvé après plusieurs essais ou un
    défaut gênant, et elle l'est avec peine."""
    dit = sortie.get("verdict")
    if dit == INTERROMPU:
        return INTERROMPU, []
    objectifs = [o for o in sortie.get("objectifs") or [] if isinstance(o, dict)]
    if dit not in VERDICTS or not objectifs:
        return SANS_PREUVE, ["le récit ne porte aucun objectif" if dit in VERDICTS else f"verdict inconnu : {dit!r}"]
    reussis = [o for o in objectifs if o.get("resultat") in ("premier_coup", "apres_essais")]
    sans_photo = [o.get("objectif", "?") for o in reussis
                  if not any(str(p).strip() in photos for p in o.get("photos") or [])]
    if sans_photo:
        return SANS_PREUVE, [f"aucune photo ne montre « {o} »" for o in sans_photo]
    impose, relevees = TENUE, []

    def durcir(verdict: str, raison: str) -> None:
        nonlocal impose
        if VERDICTS.index(verdict) > VERDICTS.index(impose):
            impose = verdict
        relevees.append((verdict, raison))

    for o in objectifs:
        nom, resultat, essais = o.get("objectif", "?"), o.get("resultat"), int(o.get("essais") or 0)
        if resultat == "bloque":
            durcir(NON_TENUE, f"« {nom} » est bloqué")
        elif resultat == "non_joue":
            durcir(NON_TENUE, f"« {nom} » n'a pas été joué")
        elif resultat == "apres_essais" and essais > ESSAIS_MAX:
            durcir(NON_TENUE, f"« {nom} » n'a été trouvé qu'après {essais} essais : au-delà de {ESSAIS_MAX}, "
                              "ce n'était pas trouvable")
        elif resultat == "apres_essais" or essais > 1:
            durcir(AVEC_PEINE, f"« {nom} » n'a pas été trouvé du premier coup")
    for d in sortie.get("defauts") or []:
        if isinstance(d, dict) and d.get("gravite") == "bloquant":
            durcir(NON_TENUE, f"défaut bloquant : {d.get('quoi', '?')}")
        elif isinstance(d, dict) and d.get("gravite") == "genant":
            durcir(AVEC_PEINE, f"défaut gênant : {d.get('quoi', '?')}")
    if VERDICTS.index(impose) > VERDICTS.index(dit):
        # Seules les raisons qui portent le verdict retenu : les autres sont déjà dans le récit.
        return impose, [raison for verdict, raison in relevees if verdict == impose]
    return dit, []


def photos_citees(sortie: dict) -> list[str]:
    """Les photos que le récit cite, chacune une fois, dans l'ordre où il les cite."""
    citees: list[str] = []
    for o in sortie.get("objectifs") or []:
        citees += [str(p) for p in (o.get("photos") or [])] if isinstance(o, dict) else []
    for cle in ("non_explique", "defauts"):
        citees += [str(x.get("photo") or "") for x in sortie.get(cle) or [] if isinstance(x, dict)]
    return list(dict.fromkeys(p.strip() for p in citees if p.strip()))


# ----------------------------------------------------------- la promesse
def but_de_l_etape(corps: str) -> str:
    """Ce que l'issue de l'étape promet : son texte, avant la liste de ses lots."""
    return (corps or "").split("Ses lots :", 1)[0].strip()


def promesse(titre: str, corps: str, livres: list[Lot], corrige: tuple[str, str] | None = None) -> str:
    """Ce que le testeur sait de l'étape : son but, et ce que chaque lot
    livré dit que le joueur joue de plus. Ni la règle du monde ni « ce que je
    vois à la démo » : la première parle de fichiers, la seconde dit où
    cliquer. `corrige` : le titre et le but de l'étape que celle-ci corrige,
    et qui reste à tenir."""
    lignes = [f"L'ÉTAPE : « {titre} »", but_de_l_etape(corps) or "(son issue ne dit pas son but)", ""]
    if corrige:
        lignes += [f"ELLE CORRIGE L'ÉTAPE « {corrige[0]} », QUI RESTE À TENIR :", corrige[1] or "(but non dit)", ""]
    lignes.append("CE QUE SES LOTS DISENT QUE LE JOUEUR JOUE DE PLUS :")
    for lot in sorted(livres, key=lambda l: l.numero):
        lignes.append(f"- « {lot.titre} » : "
                      + (journal_mod.section(lot.corps, "Ce que je joue de plus") or "(non dit)"))
    if not livres:
        lignes.append("- (aucun lot livré)")
    return "\n".join(lignes)


# ------------------------------------------------------------ le rapport
def rapport_en_clair(sortie: dict, verdict: str, raisons: list[str], adresses: dict[str, str]) -> str:
    """Le rapport du testeur, lisible sur un téléphone ; chaque photo citée
    renvoie à son image (`adresses` : nom → adresse publiée, ou chemin local)."""
    def photo(nom: str) -> str:
        nom = str(nom or "").strip()
        return f"[{nom}]({adresses[nom]})" if nom in adresses else nom

    dit = sortie.get("verdict")
    lignes = [f"**Verdict : {EN_CLAIR.get(verdict, verdict)}**"
              + (f" (il disait « {EN_CLAIR.get(dit, dit)} » ; durci par la chaîne : {' ; '.join(raisons)})"
                 if raisons and verdict != dit else ""), "", (sortie.get("resume") or "").strip(), "",
              "## Le parcours"]
    for rang, o in enumerate(sortie.get("objectifs") or [], start=1):
        resultat = _RESULTATS.get(o.get("resultat"), str(o.get("resultat"))).format(n=o.get("essais") or 0)
        montre = ", ".join(photo(p) for p in o.get("photos") or [])
        lignes += [f"{rang}. **{o.get('objectif', '')}** — {resultat}" + (f" ({montre})" if montre else ""),
                   f"   {(o.get('recit') or '').strip()}"]
    lignes += ["", "## Ce que l'écran n'explique pas"]
    lignes += [f"- {x.get('quoi', '')}" + (f" ({photo(x.get('photo'))})" if x.get("photo") else "")
               for x in sortie.get("non_explique") or []] or ["- rien"]
    lignes += ["", "## Ce qui paraît faux ou brouillon"]
    lignes += [f"- *{d.get('gravite', '?')} · {d.get('nature', '?')}* — {d.get('quoi', '')}"
               + (f" ({photo(d.get('photo'))})" if d.get("photo") else "")
               for d in sortie.get("defauts") or []] or ["- rien"]
    lignes += ["", "## À corriger d'abord"]
    lignes += [f"{rang}. {quoi}" for rang, quoi in enumerate((sortie.get("a_corriger_d_abord") or [])[:3], start=1)] \
        or ["rien"]
    publiees = [(nom, adresse) for nom, adresse in adresses.items() if adresse.startswith("http")]
    if publiees:
        lignes += ["", f"<details><summary>Ses {len(publiees)} photos</summary>", ""]
        lignes += [f"**{nom}**\n\n![{nom}]({adresse})\n" for nom, adresse in publiees]
        lignes.append("</details>")
    return "\n".join(lignes)


# -------------------------------------------------------------- le bureau
@dataclass
class Bureau:
    """L'écran du PC, vu par l'outil de jeu : est-il libre, et le jeu fermé."""

    build: Path
    sortie: Path
    outil: Path = OUTIL
    inactivite: int = INACTIVITE
    gestes_max: int = GESTES_MAX

    def environnement(self) -> dict[str, str]:
        """Ce que l'outil lit : celui qui joue ne choisit ni le build, ni le dossier."""
        return {"FORGE_TESTEUR_BUILD": str(self.build), "FORGE_TESTEUR_SORTIE": str(self.sortie),
                "FORGE_TESTEUR_INACTIVITE": str(self.inactivite), "FORGE_TESTEUR_GESTES_MAX": str(self.gestes_max)}

    def _outil(self, action: str, delai: int = 120) -> tuple[int, str]:
        try:
            fini = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(self.outil),
                                   "-Action", action], env=os.environ | self.environnement(), capture_output=True,
                                  text=True, encoding="utf-8", errors="replace", timeout=delai)
        except (OSError, subprocess.TimeoutExpired) as e:
            return 1, f"l'outil de jeu ne démarre pas : {e}"
        return fini.returncode, (fini.stdout or fini.stderr or "").strip()

    def sonde(self) -> tuple[bool, str]:
        """(le bureau est libre, ce que l'outil en dit)."""
        code, dit = self._outil("sonde")
        dernier = dit.splitlines()[-1] if dit else f"l'outil de jeu n'a rien dit (code {code})"
        return code == 0 and dernier.startswith("LIBRE"), dernier

    def fermer(self) -> None:
        self._outil("fermer")

    def gestes_joues(self) -> int:
        try:
            return int((self.sortie / "gestes.txt").read_text(encoding="utf-8", errors="replace").strip() or 0)
        except (OSError, ValueError):
            return 0


def attendre_le_bureau(bureau, attente: int, dormir: Callable[[float], None]) -> tuple[bool, str]:
    """Le bureau, regardé jusqu'à ce qu'il soit libre, `attente` secondes au
    plus : le passage part à la première pause du propriétaire."""
    libre, dit = bureau.sonde()
    for _ in range(attente // PAS_DU_BUREAU):
        if libre:
            break
        dormir(PAS_DU_BUREAU)
        libre, dit = bureau.sonde()
    return libre, dit


# ------------------------------------------------------------- le passage
def issue_de_l_etape(gh: GitHub, palier: int | None = None) -> Lot | None:
    """L'issue de l'étape que le testeur joue : celle du palier en cours, ou
    celle du palier `palier`, même fermée."""
    trouvees: list[Lot] = []
    for etat in ("open", "closed") if palier is not None else ("open",):
        trouvees += [l for l in (Lot.de(i) for i in gh.issues(etat)) if lots.ETIQUETTE_PALIER in l.etiquettes
                     and (palier is None or lots.numero_de_palier(l.titre) == palier)]
    return max(trouvees, key=lambda l: l.numero) if trouvees else None


def marques_du_testeur(commentaires: list[dict]) -> list[dict]:
    return [m for m in lots.marques(commentaires) if m.get("role") == TESTEUR]


def etape_corrigee(gh: GitHub, corps: str) -> tuple[str, str] | None:
    """Le titre et le but de l'étape que celle-ci corrige, d'après la marque
    que le pilote a laissée dans son issue en l'ouvrant sur un « non tenue »."""
    numero = next((m.get("corrige") for m in lots.marques([{"body": corps}]) if m.get("corrige")), None)
    if not isinstance(numero, int):
        return None
    try:
        issue = gh.issue(numero)
    except Exception:  # noqa: BLE001 — une étape d'avant illisible ne retient pas le passage
        return None
    return (issue.get("title") or "").split("—", 1)[-1].strip(), but_de_l_etape(issue.get("body") or "")


def texte_d_attente(raison: str, build: str, quand: str, **champs) -> str:
    """Ce que le testeur répond quand il n'a pas pu jouer : sa raison, et la
    marque qui fait renvoyer le passage. `champs` : ce que la marque porte de
    plus (la mesure d'un appel interrompu)."""
    return (f"🤖 **testeur** (PC) : il attend pour jouer — {raison}.\n\nLe build figé est prêt : "
            f"`D:\\Forge\\builds\\{build}\\Jouer.cmd`. Tu peux le jouer sans l'attendre. Le testeur ne joue que "
            "quand tu as quitté le clavier depuis dix minutes ; le pilote le renvoie dans un quart d'heure.\n\n"
            + marque(**({"role": TESTEUR} | champs | {"etat": lots.ATTENTE, "quand": quand, "raison": raison})))


def jouer(projet: Projet, gh: GitHub, depot: Depot, *, journal: Path, builds: Path, palier: int | None = None,
          build: str | None = None, force: bool = False, publication: bool = True, verrous=None,
          executeur_agents: agents_mod.Executeur = agents_mod.executer, bureau_de=Bureau, publier=captures.publier,
          maintenant=None, dormir: Callable[[float], None] = time.sleep, dossier: Path | None = None,
          attente: int = ATTENTE_DU_BUREAU) -> list[str]:
    """Un passage du testeur sur le PC ; il répond toujours sur l'issue de
    l'étape, par son rapport ou par une attente.

    Sans `force`, il ne joue que si le pilote l'a envoyé (sa dernière marque
    est un envoi) : un passage resté en file et parti deux fois ne rejoue
    pas. `palier` et `build` : jouer une autre étape ou un autre build que
    ceux du palier en cours, à la main. Sans `publication`, rien ne part sur
    GitHub : le rapport est rendu ici, ses photos restent dans son dossier."""
    from .pilote import Pilote
    verrous = verrous or AucunVerrou()
    pilote = Pilote(projet, gh, depot, journal=journal, executeur_agents=executeur_agents, machine="pc",
                    verrous=verrous, maintenant=maintenant)
    issue = issue_de_l_etape(gh, palier)
    if issue is None:
        return ["RIEN — aucune issue de palier" + (f" {palier}" if palier is not None else " ouverte")]
    numero = lots.numero_de_palier(issue.titre) or 0
    titre = issue.titre.split("—", 1)[-1].strip()
    siennes = marques_du_testeur(gh.issue(issue.numero).get("comments") or [])
    if not force and (not siennes or siennes[-1].get("etat") != lots.ENVOYE):
        return [f"RIEN — l'étape n'attend pas le testeur ({siennes[-1].get('etat') if siennes else 'aucun envoi'})"]
    nom = build or f"palier-{numero}"
    quand = pilote.maintenant()

    def repondre(texte: str) -> None:
        if publication:
            gh.commenter_issue(issue.numero, texte)

    def attendre(raison: str) -> list[str]:
        repondre(texte_d_attente(raison, nom, quand.isoformat(timespec="seconds")))
        pilote.noter(issue.numero, "attente", f"testeur : {raison}")
        return pilote.lignes

    if not verrous.prendre("testeur"):
        return attendre("un autre passage du testeur joue encore")
    try:
        if not (builds / nom / "Forge.exe").is_file():
            return attendre(f"le build figé `{nom}` n'est pas sur le PC")
        passage = (dossier or Path.home() / ".atelier" / "testeur") / f"palier-{numero}-{quand:%Y%m%dT%H%M%S}"
        bureau = bureau_de(build=builds / nom, sortie=passage)
        libre, dit = attendre_le_bureau(bureau, attente, dormir)
        if not libre:
            return attendre(dit)
        passage.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(projet.racine / "docs" / "VISION.md", passage / "vision.md")
        shutil.copyfile(REPERES, passage / "reperes-1400.md")
        fermes = [Lot.de(i) for i in gh.issues("closed")]
        livres = [l for l in fermes if l.est_un_lot and l.palier == numero and l.etat == "livre"]
        consigne = consignes.testeur(
            numero=numero, titre=titre, promesse=promesse(titre, issue.corps, livres, etape_corrigee(gh, issue.corps)),
            outil=str(bureau.outil), dossier=str(passage), minutes=projet.delai(TESTEUR) // 60,
            gestes_max=bureau.gestes_max, essais_max=ESSAIS_MAX)
        appel = agents_mod.Appel(role=TESTEUR, lecture_seule=True, consigne=consigne, schema=consignes.SCHEMA_TESTEUR,
                                 outils=("Read", "PowerShell"), garde=(str(GARDE), str(bureau.outil), str(passage)),
                                 environnement=tuple(bureau.environnement().items()))
        try:
            res = pilote._invoquer(TESTEUR, appel, passage, lot=issue.numero)
        finally:
            # Le jeu ne reste jamais ouvert derrière lui, même coupé par son délai.
            bureau.fermer()
        if res.attente:
            return attendre(res.raison)
        gestes = bureau.gestes_joues()
        sortie = res.sortie if res.reussi and isinstance(res.sortie, dict) else None
        presentes = {f.stem for f in passage.glob("*.png")}
        verdict, raisons = verdict_qui_pese(sortie, presentes) if sortie else (SANS_PREUVE, [])
        if verdict == INTERROMPU:
            raison = (f"il a dû s'arrêter après {gestes} gestes : "
                      + ((sortie.get("interruption") or "").strip() or "le propriétaire a repris son écran"))
            # Ce qu'il avait trouvé ne fait pas un verdict, mais ne se perd pas : le prochain passage rejoue tout.
            trouve = (f"\n\n<details><summary>Ce qu'il avait trouvé avant de s'arrêter ({gestes} gestes ; ce n'est pas "
                      f"un verdict)</summary>\n\n{rapport_en_clair(sortie, INTERROMPU, [], {})}\n\n</details>"
                      if gestes else "")
            attente_dite = texte_d_attente(raison, nom, quand.isoformat(timespec="seconds"),
                                           **pilote._champs(TESTEUR, res, gestes=gestes))
            repondre(attente_dite.replace("\n\n<!-- atelier", f"{trouve}\n\n<!-- atelier", 1))
            pilote.noter(issue.numero, "testeur interrompu", raison, str(res.agent))
            return pilote.lignes if publication else [*pilote.lignes, trouve, "", f"Ses photos : {passage}"]
        if verdict == SANS_PREUVE:
            raison = ("coupé par son délai" if res.coupe else f"code {res.code}" if not res.reussi
                      else "; ".join(raisons) or "il n'a rendu aucun récit")
            repondre(f"🤖 **testeur** ({res.agent or '—'}) a joué `{nom}` ({gestes} gestes) sans rendre un récit "
                     f"prouvé : {raison}. Ce passage ne compte pas comme un verdict ; le pilote le renvoie.\n\n"
                     + marque(**pilote._champs(TESTEUR, res, etat=lots.COUPE if res.coupe else lots.ECHEC,
                                               quand=quand.isoformat(timespec="seconds"), raison=raison, gestes=gestes)))
            pilote.noter(issue.numero, "testeur en échec", raison, str(res.agent or ""))
            return pilote.lignes
        citees = [p for p in photos_citees(sortie) if p in presentes][:PHOTOS_MAX]
        adresses = {p: str(passage / f"{p}.png") for p in citees}
        if publication:
            # La copie légère de chaque photo, sous un nom qui dit son étape et son passage.
            copies = {p: passage / "publication" / f"testeur-palier-{numero}-{quand:%H%M}-{p}.jpg" for p in citees
                      if (passage / "publication" / f"{p}.jpg").is_file()}
            for p, copie in copies.items():
                shutil.copyfile(passage / "publication" / f"{p}.jpg", copie)
            try:
                publiees = publier(depot, gh.depot, list(copies.values()), f"{quand:%Y-%m-%d}")
            except Exception:  # noqa: BLE001 — des images manquées ne retiennent pas le verdict
                publiees = []
            adresses |= dict(zip(copies, publiees))
        corps = (f"# Le testeur a joué le palier {numero} — {titre}\n\nLe build figé : `D:\\Forge\\builds\\{nom}`, "
                 f"joué par l'écran seul, sans le code ni le service : {gestes} gestes, {len(presentes)} photos.\n\n"
                 + rapport_en_clair(sortie, verdict, raisons, adresses)
                 + f"\n\n<sub>Joué par le testeur ({res.agent}).</sub>")
        repondre(f"{corps}\n\n" + marque(**pilote._champs(
            TESTEUR, res, etat=JOUE, verdict=verdict, dit=sortie.get("verdict"), build=nom, gestes=gestes,
            quand=quand.isoformat(timespec="seconds"), a_corriger=(sortie.get("a_corriger_d_abord") or [])[:3])))
        pilote.noter(issue.numero, "testeur", f"palier {numero} : {EN_CLAIR[verdict]}, {gestes} gestes", str(res.agent))
        return pilote.lignes if publication else [*pilote.lignes, "", corps, "", f"Ses photos : {passage}"]
    finally:
        verrous.lacher("testeur")


def repondre_au_silence(gh: GitHub, *, raison: str) -> str:
    """Un passage qui n'a pas pu partir (la session du propriétaire est
    fermée, la tâche planifiée manque) ou qui est tombé sans répondre ne
    laisse aucune marque, et le pilote attendrait des heures : `testeur-pc.yml`
    répond à sa place par une attente. Seul un envoi resté sans réponse en
    reçoit une."""
    issue = issue_de_l_etape(gh)
    if issue is None:
        return "RIEN — aucune issue de palier ouverte"
    siennes = marques_du_testeur(gh.issue(issue.numero).get("comments") or [])
    if not siennes or siennes[-1].get("etat") != lots.ENVOYE:
        return f"RIEN — l'étape n'attend pas le testeur ({siennes[-1].get('etat') if siennes else 'aucun envoi'})"
    quand = datetime.now(timezone.utc).isoformat(timespec="seconds")
    gh.commenter_issue(issue.numero, texte_d_attente(raison, siennes[-1].get("build") or "", quand))
    return f"attente marquée sur l'issue #{issue.numero}"
