#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Pushes main + tags to the internal GitLab mirror from a machine that can
# reach it. Use this when the GitHub Actions mirror job is not enabled
# (hosted runners cannot resolve the internal host).
set -euo pipefail

REMOTE="${GITLAB_REMOTE:-gitlab}"

if ! git remote get-url "$REMOTE" >/dev/null 2>&1; then
    echo "error: remote '$REMOTE' not configured" >&2
    exit 1
fi

echo "Mirroring main + tags to '$REMOTE'..."
git push "$REMOTE" main:main
git push "$REMOTE" --tags
echo "Done."
