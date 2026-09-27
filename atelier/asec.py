"""Le tour à sec : il lit le vrai GitHub, et n'écrit rien.

Chaque geste qui écrirait (commentaire, étiquette, PR, fusion, commit,
poussée) est imprimé au lieu d'être fait, et aucun agent n'est invoqué :
c'est la façon de vérifier une décision du pilote sans dépenser un quota ni
toucher au dépôt.
"""

from __future__ import annotations

from pathlib import Path

from .depot import Depot
from .github import GitHub


def _dire(quoi: str) -> None:
    print(f"(à sec) {quoi}")


class GitHubASec(GitHub):
    def creer_issue(self, titre, corps, etiquettes=(), jalon=None):
        _dire(f"créer l'issue « {titre} » {list(etiquettes)} {jalon or ''}")
        return 0

    def commenter_issue(self, numero, texte):
        _dire(f"commenter l'issue #{numero} : {texte.splitlines()[0][:100]}")

    def etiqueter(self, numero, ajouter=(), retirer=()):
        _dire(f"étiqueter #{numero} : +{list(ajouter)} -{list(retirer)}")

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

    def fusion_auto(self, numero):
        _dire(f"fusion automatique de la PR #{numero}")

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
