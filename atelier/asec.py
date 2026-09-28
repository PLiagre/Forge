"""Le tour à sec : il lit le vrai GitHub, et n'écrit rien.

Chaque geste qui écrirait (commentaire, étiquette, PR, fusion, commit,
poussée) est imprimé au lieu d'être fait, et aucun agent n'est invoqué :
c'est la façon de vérifier une décision du pilote sans dépenser un quota ni
toucher au dépôt. Les étiquettes et commentaires qu'il aurait posés, il les
relit dans le même tour : une reprise est suivie de ce qu'elle déclenche,
pas d'un faux blocage.
"""

from __future__ import annotations

from pathlib import Path

from .depot import Depot
from .github import GitHub, executer


def _dire(quoi: str) -> None:
    print(f"(à sec) {quoi}")


class GitHubASec(GitHub):
    def __init__(self, depot: str, executeur=executer):
        super().__init__(depot, executeur)
        self._etiquettes: dict[int, tuple[list[str], list[str]]] = {}
        self._commentaires_pr: dict[int, list[str]] = {}

    def _etiquete(self, issue: dict) -> dict:
        ajout, retrait = self._etiquettes.get(issue.get("number"), ([], []))
        if not ajout and not retrait:
            return issue
        noms = [e["name"] for e in issue.get("labels") or [] if e["name"] not in retrait]
        return dict(issue, labels=[{"name": n} for n in noms + [a for a in ajout if a not in noms]])

    def issues(self, etat="open"):
        return [self._etiquete(i) for i in super().issues(etat)]

    def issue(self, numero):
        return self._etiquete(super().issue(numero))

    def pr(self, numero):
        pr = super().pr(numero)
        faux = self._commentaires_pr.get(numero)
        return dict(pr, comments=list(pr.get("comments") or []) + [{"body": t} for t in faux]) if faux else pr

    def creer_issue(self, titre, corps, etiquettes=(), jalon=None):
        _dire(f"créer l'issue « {titre} » {list(etiquettes)} {jalon or ''}")
        return 0

    def commenter_issue(self, numero, texte):
        _dire(f"commenter l'issue #{numero} : {texte.splitlines()[0][:100]}")

    def etiqueter(self, numero, ajouter=(), retirer=()):
        _dire(f"étiqueter #{numero} : +{list(ajouter)} -{list(retirer)}")
        ajout, retrait = self._etiquettes.get(numero, ([], []))
        ajout = [a for a in ajout if a not in retirer] + [a for a in ajouter if a not in ajout]
        retrait = [r for r in retrait if r not in ajouter] + [r for r in retirer if r not in retrait]
        self._etiquettes[numero] = (ajout, retrait)

    def jalon_de(self, numero, titre_jalon):
        _dire(f"ranger #{numero} dans {titre_jalon}")

    def fermer_issue(self, numero, commentaire=None, *, abandon=False):
        _dire(f"fermer #{numero}")

    def fermer_jalon(self, numero):
        _dire(f"fermer le jalon {numero}")

    def creer_pr(self, branche, base, titre, corps, *, brouillon=True):
        _dire(f"ouvrir la PR « {titre} » ({branche} → {base})")
        return 0

    def pr_prete(self, numero):
        _dire(f"PR #{numero} prête")

    def commenter_pr(self, numero, texte):
        _dire(f"commenter la PR #{numero} : {texte.splitlines()[0][:100]}")
        self._commentaires_pr.setdefault(numero, []).append(texte)

    def fusion_auto(self, numero, tete=None):
        _dire(f"fusion automatique de la PR #{numero}" + (f" (révision {tete[:7]})" if tete else ""))

    def fermer_pr(self, numero, commentaire):
        _dire(f"fermer la PR #{numero}")

    def lancer_workflow(self, workflow, reference, champs):
        _dire(f"lancer {workflow} sur {reference} : {champs}")


class DepotASec(Depot):
    def fetch(self):
        _dire("git fetch")

    def preparer(self, nom, branche):
        _dire(f"préparer le worktree {nom} sur {branche}")
        return Path(self.racine)

    def retirer(self, nom):
        _dire(f"retirer le worktree {nom}")

    def changements(self, chemin):
        return []

    def annuler(self, chemin, fichiers):
        _dire(f"annuler {fichiers}")

    def enregistrer(self, chemin, message):
        _dire(f"commit : {message.splitlines()[0]}")
        return "0" * 40

    def pousser(self, chemin, branche):
        _dire(f"pousser {branche}")

    def fusionner_base(self, chemin):
        _dire("fusionner la base")
        return []


def executeur_a_sec(argv, cwd, env, delai):
    _dire(f"invoquer {argv[0]} (modèle {argv[argv.index('--model') + 1] if '--model' in argv else '?'})")
    return 0, "à sec : aucun agent invoqué", ""
