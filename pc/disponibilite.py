"""La disponibilité du PC pour la chaîne, en une fenêtre.

    py pc\\disponibilite.py        (ou pc\\Disponibilite.cmd)

Ce qu'elle montre : la charge du processeur, ce qui tourne de lourd (Python,
Unity, Blender), le service du runner `pc-forge` et le travail qu'il fait.

Ce qu'elle fait :
- l'interrupteur de la chaîne : la variable d'Actions `PC_ACTIF` du dépôt,
  que le pilote du VPS et les workflows du PC lisent (docs/WORKFLOW.md). Sur
  « non », aucun lot `pc` ne part, ni le build de nuit, ni Unity sur une
  poussée. La même variable se bascule dans GitHub (Settings → Secrets and
  variables → Actions → Variables), du téléphone aussi ;
- le mode discret : Python, Unity et Blender passent en priorité basse, que
  la charge vienne de la chaîne ou de tests lancés à la main : le PC reste
  fluide, le travail va seulement moins vite quand on s'en sert ;
- le service du runner : l'arrêter coupe aussi ce que le pilote avait déjà
  envoyé (il attend alors en file chez GitHub, ou se renvoie au bout d'une
  heure) ; Windows demande l'élévation.

Bibliothèque standard seule, plus `gh` pour la variable. Les fonctions du haut
du fichier ne touchent à rien : les tests les jouent sans Windows.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
VARIABLE = "PC_ACTIF"
DEPOT_PAR_DEFAUT = "PLiagre/Forge"
RUNNER = re.compile(r"actions\.runner\.[\w.\-]+")
ETATS = ("RUNNING", "STOPPED", "START_PENDING", "STOP_PENDING", "PAUSED", "PAUSE_PENDING", "CONTINUE_PENDING")
ETATS_FR = {"RUNNING": "démarré", "STOPPED": "arrêté", "START_PENDING": "démarre", "STOP_PENDING": "s'arrête",
            "PAUSED": "en pause", "PAUSE_PENDING": "se met en pause", "CONTINUE_PENDING": "reprend"}

# Ce que le mode discret rabaisse, par famille. Le travail du runner est
# seulement compté : le baisser n'avancerait à rien.
LOURDS = {"python.exe": "Python", "pythonw.exe": "Python",
          "unity.exe": "Unity", "unityshadercompiler.exe": "Unity",
          "blender.exe": "Blender"}
TRAVAIL_DU_RUNNER = "runner.worker.exe"

# Les classes de priorité de Windows (processthreadsapi.h).
IDLE, BELOW_NORMAL, NORMAL, ABOVE_NORMAL, HIGH = 0x40, 0x4000, 0x20, 0x8000, 0x80


# ----------------------------------------------------------------------
# Ce qui se lit, sans toucher à rien
# ----------------------------------------------------------------------
def lire_tasklist(texte: str) -> list[tuple[str, int]]:
    """`tasklist /FO CSV /NH` : (image, pid). Sans en-tête, donc sans dépendre
    de la langue de Windows."""
    gens = []
    for ligne in csv.reader(io.StringIO(texte)):
        if len(ligne) >= 2 and ligne[1].strip().isdigit():
            gens.append((ligne[0].strip(), int(ligne[1])))
    return gens


def regrouper(processus: list[tuple[str, int]]) -> tuple[dict[str, list[int]], bool]:
    """Les pid lourds par famille, et si le runner a un travail en cours."""
    familles: dict[str, list[int]] = {}
    en_travail = False
    for image, pid in processus:
        nom = image.lower()
        if nom in LOURDS:
            familles.setdefault(LOURDS[nom], []).append(pid)
        elif nom == TRAVAIL_DU_RUNNER:
            en_travail = True
    return familles, en_travail


def charge(avant: tuple[int, int, int], apres: tuple[int, int, int]) -> float:
    """La charge (0-100) entre deux relevés (inactif, noyau, utilisateur) ;
    le temps noyau compte déjà l'inactif."""
    total = (apres[1] + apres[2]) - (avant[1] + avant[2])
    inactif = apres[0] - avant[0]
    if total <= 0:
        return 0.0
    return max(0.0, min(100.0, 100.0 * (total - inactif) / total))


def a_baisser(classe: int) -> bool:
    """Une priorité normale ou plus haute se rabaisse ; une déjà basse reste."""
    return classe in (NORMAL, ABOVE_NORMAL, HIGH)


def nom_du_service(sortie_sc: str) -> str | None:
    """Le service du runner dans la liste de `sc query state= all`. Cherché
    par son nom, qui ne se traduit pas : les libellés de `sc` le sont."""
    trouve = RUNNER.search(sortie_sc)
    return trouve.group(0) if trouve else None


def etat_du_service(sortie_sc: str) -> str | None:
    """RUNNING, STOPPED… : les noms d'états ne se traduisent pas non plus."""
    for etat in ETATS:
        if re.search(rf"\b{etat}\b", sortie_sc):
            return etat
    return None


def depot_du_projet(racine: Path = RACINE) -> str:
    try:
        import tomllib

        return tomllib.loads((racine / "atelier.toml").read_text(encoding="utf-8"))["projet"]["depot"]
    except (OSError, KeyError, ValueError, ImportError):
        return DEPOT_PAR_DEFAUT


def valeur_de_la_variable(code: int, sortie: str, erreur: str) -> str | None:
    """« oui » ou « non », ou `None` quand elle est illisible. Une variable
    absente (404) laisse le PC travailler : c'est « oui », comme pour le pilote."""
    if code == 0:
        return "non" if sortie.strip().lower() == "non" else "oui"
    if "404" in erreur or "Not Found" in erreur:
        return "oui"
    return None


# ----------------------------------------------------------------------
# Ce qui touche à Windows et à GitHub
# ----------------------------------------------------------------------
def _lancer(argv: list[str], delai: int = 30) -> tuple[int, str, str]:
    drapeau = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW : pas de console qui clignote
    try:
        fini = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=delai, creationflags=drapeau)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, "", f"{argv[0]} : {e}"
    return fini.returncode, fini.stdout, fini.stderr


def temps_du_systeme() -> tuple[int, int, int]:
    import ctypes
    from ctypes import wintypes

    class FileTime(ctypes.Structure):
        _fields_ = [("bas", wintypes.DWORD), ("haut", wintypes.DWORD)]

    inactif, noyau, utilisateur = FileTime(), FileTime(), FileTime()
    ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(inactif), ctypes.byref(noyau), ctypes.byref(utilisateur))
    return tuple((t.haut << 32) | t.bas for t in (inactif, noyau, utilisateur))  # type: ignore[return-value]


def rabaisser(pid: int) -> bool:
    """Passe le processus en priorité basse s'il ne l'est pas déjà. Vrai s'il a
    changé ; faux si rien à faire ou refusé (un processus d'un autre compte)."""
    import ctypes

    noyau = ctypes.windll.kernel32
    droits = 0x0200 | 0x1000  # SET_INFORMATION | QUERY_LIMITED_INFORMATION
    poignee = noyau.OpenProcess(droits, False, pid)
    if not poignee:
        return False
    try:
        if not a_baisser(noyau.GetPriorityClass(poignee)):
            return False
        return bool(noyau.SetPriorityClass(poignee, BELOW_NORMAL))
    finally:
        noyau.CloseHandle(poignee)


def releve(discret: bool) -> dict:
    """Un instantané : ce qui tourne, le service du runner, et — en mode
    discret — ce qu'on vient de rabaisser."""
    _, liste, _ = _lancer(["tasklist", "/FO", "CSV", "/NH"], 15)
    familles, en_travail = regrouper(lire_tasklist(liste))
    rabaisses = 0
    if discret:
        moi = os.getpid()
        rabaisses = sum(rabaisser(pid) for pids in familles.values() for pid in pids if pid != moi)
    nom = nom_du_service(_lancer(["sc", "query", "state=", "all"], 15)[1])
    etat = etat_du_service(_lancer(["sc", "query", nom], 15)[1]) if nom else None
    return {"familles": {k: len(v) for k, v in familles.items()}, "travail": en_travail,
            "service": nom, "etat": etat, "rabaisses": rabaisses}


def variable_de_la_chaine(depot: str) -> str | None:
    code, sortie, erreur = _lancer(["gh", "api", f"repos/{depot}/actions/variables/{VARIABLE}", "--jq", ".value"])
    return valeur_de_la_variable(code, sortie, erreur)


def poser_la_variable(depot: str, valeur: str) -> str | None:
    """Rien si c'est fait, sinon pourquoi."""
    code, _, erreur = _lancer(["gh", "variable", "set", VARIABLE, "--body", valeur, "-R", depot])
    return None if code == 0 else (erreur.strip() or "gh a échoué")[:300]


def commande_du_service(verbe: str, nom: str) -> str | None:
    """`sc stop` ou `sc start`, élevé : Windows pose sa question. Rien si c'est
    parti, sinon pourquoi."""
    import ctypes

    code = ctypes.windll.shell32.ShellExecuteW(None, "runas", "sc.exe", f"{verbe} {nom}", None, 0)
    return None if code > 32 else "l'élévation a été refusée ou a échoué"


# ----------------------------------------------------------------------
# La fenêtre
# ----------------------------------------------------------------------
def fenetre() -> int:
    import queue
    import threading
    import tkinter as tk
    import webbrowser
    from tkinter import messagebox, ttk

    depot = depot_du_projet()
    racine = tk.Tk()
    racine.title("Forge — disponibilité du PC")
    racine.resizable(False, False)
    cadre = ttk.Frame(racine, padding=14)
    cadre.grid()

    recus: "queue.Queue[tuple[str, object]]" = queue.Queue()
    etat = {"service": None, "service_etat": None, "travail": False, "variable": None,
            "mesure": False, "variable_en_cours": False}
    discret = tk.BooleanVar(value=False)

    def ligne(rang: int, titre: str) -> ttk.Label:
        ttk.Label(cadre, text=titre, font=("Segoe UI", 9, "bold")).grid(row=rang, column=0, sticky="nw", pady=(8, 0))
        valeur = ttk.Label(cadre, text="…", wraplength=330, justify="left")
        valeur.grid(row=rang, column=1, sticky="w", padx=(12, 0), pady=(8, 0))
        return valeur

    pourcent = ttk.Progressbar(cadre, length=200, maximum=100)
    ttk.Label(cadre, text="Processeur", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="nw")
    pourcent.grid(row=0, column=1, sticky="w", padx=(12, 0))
    texte_charge = ttk.Label(cadre, text="…")
    texte_charge.grid(row=0, column=2, sticky="w", padx=(8, 0))
    v_lourds = ligne(1, "Ce qui tourne")
    v_runner = ligne(2, "Runner pc-forge")
    v_chaine = ligne(3, "La chaîne")
    v_message = ttk.Label(cadre, text="", foreground="#a33", wraplength=480, justify="left")

    boutons = ttk.Frame(cadre)
    boutons.grid(row=4, column=0, columnspan=3, sticky="w", pady=(12, 0))
    b_chaine = ttk.Button(boutons, text="…")
    b_chaine.grid(row=0, column=0, padx=(0, 8))
    b_service = ttk.Button(boutons, text="…")
    b_service.grid(row=0, column=1, padx=(0, 8))
    ttk.Checkbutton(cadre, text="Mode discret : Python, Unity et Blender en priorité basse "
                                "(le jeu lancé par Jouer.cmd s'en ressent)",
                    variable=discret).grid(row=5, column=0, columnspan=3, sticky="w", pady=(10, 0))
    liens = ttk.Frame(cadre)
    liens.grid(row=6, column=0, columnspan=3, sticky="w", pady=(10, 0))
    ttk.Button(liens, text="Runners sur GitHub",
               command=lambda: webbrowser.open(f"https://github.com/{depot}/settings/actions/runners")
               ).grid(row=0, column=0, padx=(0, 8))
    ttk.Button(liens, text="Variables sur GitHub",
               command=lambda: webbrowser.open(f"https://github.com/{depot}/settings/variables/actions")
               ).grid(row=0, column=1)
    v_message.grid(row=7, column=0, columnspan=3, sticky="w", pady=(8, 0))

    def dire(texte: str) -> None:
        v_message.config(text=texte)

    # --- ce que la fenêtre demande, en fil à part pour ne jamais figer
    def en_fil(nom: str, travail) -> None:
        def court() -> None:
            try:
                recus.put((nom, travail()))
            except Exception as e:  # une mesure ratée ne fige jamais la fenêtre
                recus.put(("erreur", (nom, str(e))))

        threading.Thread(target=court, daemon=True).start()

    def mesurer() -> None:
        if etat["mesure"]:
            return
        etat["mesure"] = True
        en_fil("releve", lambda: releve(discret.get()))

    def lire_variable() -> None:
        if etat["variable_en_cours"]:
            return
        etat["variable_en_cours"] = True
        en_fil("variable", lambda: variable_de_la_chaine(depot))

    def basculer_la_chaine() -> None:
        voulu = "oui" if etat["variable"] == "non" else "non"
        b_chaine.state(["disabled"])
        dire(f"{VARIABLE} → {voulu}…")
        en_fil("pose", lambda: (voulu, poser_la_variable(depot, voulu)))

    def basculer_le_service() -> None:
        nom, courant = etat["service"], etat["service_etat"]
        if not nom:
            return
        verbe = "stop" if courant == "RUNNING" else "start"
        if verbe == "stop" and etat["travail"] and not messagebox.askyesno(
                "Arrêter le runner", "Un travail est en cours sur le PC : l'arrêter l'interrompt.\n\n"
                                     "Arrêter quand même ?"):
            return
        dire(commande_du_service(verbe, nom) or "")

    b_chaine.config(command=basculer_la_chaine)
    b_service.config(command=basculer_le_service)

    # --- ce qui revient
    def afficher_variable() -> None:
        v, b = etat["variable"], b_chaine
        b.state(["!disabled"])
        if v == "non":
            v_chaine.config(text="en pause : aucun lot pc, ni build de nuit, ni Unity sur poussée")
            b.config(text="Reprendre la chaîne sur ce PC")
        elif v == "oui":
            v_chaine.config(text=f"le PC travaille pour la chaîne ({VARIABLE} = oui)")
            b.config(text="Mettre la chaîne en pause")
        else:
            v_chaine.config(text="état illisible (gh absent, ou pas connecté à GitHub ?)")
            b.config(text="Mettre la chaîne en pause")

    def afficher_releve(r: dict) -> None:
        etat.update(service=r["service"], service_etat=r["etat"], travail=r["travail"], mesure=False)
        lourds = r["familles"]
        v_lourds.config(text=" · ".join(f"{nom} : {n}" for nom, n in sorted(lourds.items())) or "rien de lourd")
        if r["service"] is None:
            v_runner.config(text="service introuvable sur ce PC")
            b_service.config(text="Runner introuvable")
            b_service.state(["disabled"])
        else:
            travail = "un travail est en cours" if r["travail"] else "aucun travail en cours"
            v_runner.config(text=f"{ETATS_FR.get(r['etat'], '?')} · {travail}")
            b_service.state(["!disabled"])
            b_service.config(text="Arrêter le service du runner" if r["etat"] == "RUNNING"
                             else "Démarrer le service du runner")

    avant = [temps_du_systeme()]

    def pouls() -> None:
        maintenant = temps_du_systeme()
        valeur = charge(avant[0], maintenant)
        avant[0] = maintenant
        pourcent["value"] = valeur
        texte_charge.config(text=f"{valeur:.0f} %")
        mesurer()
        racine.after(2000, pouls)

    def courrier() -> None:
        try:
            while True:
                nom, contenu = recus.get_nowait()
                if nom == "releve":
                    afficher_releve(contenu)  # type: ignore[arg-type]
                elif nom == "variable":
                    etat["variable_en_cours"] = False
                    etat["variable"] = contenu
                    afficher_variable()
                elif nom == "erreur":
                    quoi, pourquoi = contenu  # type: ignore[misc]
                    etat["mesure"] = etat["variable_en_cours"] = False
                    b_chaine.state(["!disabled"])
                    dire(f"{quoi} : {pourquoi}")
                elif nom == "pose":
                    voulu, erreur = contenu  # type: ignore[misc]
                    if erreur:
                        dire(f"la variable n'a pas changé : {erreur}")
                        b_chaine.state(["!disabled"])
                    else:
                        dire("")
                        etat["variable"] = voulu
                        afficher_variable()
        except queue.Empty:
            pass
        racine.after(300, courrier)

    def relire_la_variable() -> None:
        lire_variable()
        racine.after(30000, relire_la_variable)

    pouls()
    courrier()
    relire_la_variable()
    racine.mainloop()
    return 0


def main() -> int:
    if sys.platform != "win32":
        print("cette fenêtre pilote le PC Windows du runner : rien à faire ici")
        return 1
    return fenetre()


if __name__ == "__main__":
    sys.exit(main())
