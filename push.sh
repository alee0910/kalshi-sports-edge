#!/usr/bin/env bash
# First-push helper.
#
# Usage:
#   1. Create an EMPTY private repo at https://github.com/new
#      (name: kalshi-sports-edge — no README, no .gitignore, no license)
#   2. export GH_USER="your-github-username"
#   3. export GH_PAT="ghp_your_personal_access_token"
#   4. bash push.sh
#
# After the first push, the script sets the remote URL to a PAT-free form so
# the token stops living on disk.

set -euo pipefail

: "${GH_USER:?set GH_USER to your GitHub username}"
: "${GH_PAT:?set GH_PAT to your personal access token (scope: repo)}"

REPO="kalshi-sports-edge"
cd "$(dirname "$0")"

# Clean any stale git state
rm -rf .git

git init
# Rename default branch to main (portable across older git versions that
# lack `init -b`)
git symbolic-ref HEAD refs/heads/main
git config user.email "${GIT_EMAIL:-a.lee53@gmail.com}"
git config user.name  "${GIT_NAME:-Andy}"

git add .
git commit -m "kalshi-sports-edge v1 — MLB/NBA/NFL live, 7 sports stubbed"

# If the commit landed on "master" (really old git), rename to main
if git show-ref --quiet refs/heads/master; then
  git branch -m master main
fi

git remote add origin "https://${GH_USER}:${GH_PAT}@github.com/${GH_USER}/${REPO}.git"
git push -u origin main

# Scrub the PAT from .git/config immediately
git remote set-url origin "https://github.com/${GH_USER}/${REPO}.git"

echo
echo "Push complete."
echo "Next steps:"
echo "  1. Settings → Pages → Source = GitHub Actions"
echo "  2. Settings → Secrets → Actions → New secret: KALSHI_API_KEY"
echo "  3. Dashboard will be live at https://${GH_USER}.github.io/${REPO}/ after the first Pages run."
