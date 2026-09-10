#!/usr/bin/env bash
# Le résultat vient uniquement de l'enveloppe GitHub, jamais du formulaire.
set -euo pipefail
python3 -m outils autoriser-lot --evenement "$GITHUB_EVENT_PATH" >> "$GITHUB_OUTPUT"
