#!/usr/bin/env bash
# Un 404 connu n'est pas un déploiement raté. Les autres erreurs restent visibles.
set -euo pipefail
: "${DEPOT:?DEPOT manquant}"
: "${GITHUB_OUTPUT:?GITHUB_OUTPUT manquant}"
: "${GITHUB_STEP_SUMMARY:?GITHUB_STEP_SUMMARY manquant}"
code=0
gh api "repos/$DEPOT/pages" > pages.json 2> pages-erreur.log || code=$?
if [ "$code" != 0 ]; then
  if [[ $(cat pages-erreur.log) == *'HTTP 404'* ]]; then
    echo "publier=false" >> "$GITHUB_OUTPUT"
    echo "Tableau généré et conservé dans l’artefact. Pages est absent (HTTP 404) : aucune page publiée. Réglage : Settings → Pages → Source → GitHub Actions." >> "$GITHUB_STEP_SUMMARY"
    exit 0
  fi
  cat pages-erreur.log >&2
  exit "$code"
fi
python3 - <<'PY'
import json, os
from pathlib import Path
site = json.loads(Path('pages.json').read_text())
pret = site.get('build_type') == 'workflow'
with open(os.environ['GITHUB_OUTPUT'], 'a') as sortie:
    sortie.write('publier=' + str(pret).lower() + '\n')
if not pret:
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as resume:
        resume.write('Tableau généré et conservé dans l’artefact. Publication non configurée pour Actions : Settings → Pages → Source → GitHub Actions.\n')
PY
