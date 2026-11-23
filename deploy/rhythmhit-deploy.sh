#!/usr/bin/env bash
# Publish the Rhythm Hit static site on VPS3 from a pushed GitHub commit.
#
#   rhythmhit-deploy <full-40-char-commit>
#
# Fetches the public repository, builds projects/unified/dist as an
# unprivileged user, installs it as an immutable release and atomically
# switches /srv/rhythmhit/current. The accounts API (rhythmhit-api.service)
# is switched the same way under /opt/rhythmhit/api and restarted. If the
# HTTPS check fails, the previous site and API are restored. Set SKIP_HTTP_CHECK=1 only for the first release
# before DNS and the certificate exist.
set -euo pipefail

REMOTE=https://github.com/Scottshrimp/1354labGP7.git
REPO=/opt/rhythmhit/repo
SITE=/srv/rhythmhit
API=/opt/rhythmhit/api
HOST=rhythmhit.scottshrimp.com
KEEP=5

commit=${1:-}
if [[ ! $commit =~ ^[0-9a-f]{40}$ ]]; then
	echo "usage: rhythmhit-deploy <full 40-character commit>" >&2
	exit 2
fi

exec 9>/run/lock/rhythmhit-deploy.lock
flock -n 9 || { echo "another deployment is running" >&2; exit 1; }

if [[ ! -d $REPO/.git ]]; then
	mkdir -p "$(dirname "$REPO")"
	git clone --quiet "$REMOTE" "$REPO"
fi
git -C "$REPO" fetch --quiet --prune origin '+refs/heads/*:refs/remotes/origin/*'
git -C "$REPO" cat-file -e "$commit^{commit}" 2>/dev/null || {
	echo "commit $commit is not on GitHub; push it first" >&2
	exit 1
}

release=$SITE/releases/$commit
mkdir -p "$SITE/releases"
if [[ ! -d $release ]]; then
	work=$(mktemp -d /tmp/rhythmhit-build.XXXXXX)
	trap 'rm -rf "$work"' EXIT
	git -C "$REPO" archive "$commit" | tar -x -C "$work"
	chown -R nobody:nogroup "$work"
	runuser -u nobody -- env HOME="$work" PYTHONDONTWRITEBYTECODE=1 \
		python3 "$work/projects/unified/tools/build_web.py"
	dist=$work/projects/unified/dist
	for required in index.html style.css console.js main.py tutorial/index.html \
		browser/app.mjs browser/rh1.mjs browser/match.mjs \
		browser/songs.json browser/starter-beat.wav account.mjs leaderboard/index.html; do
		[[ -s $dist/$required ]] || { echo "build is missing $required" >&2; exit 1; }
	done
	# Song audio is uploaded separately; refuse a build whose songs would be silent.
	missing=$(python3 - "$dist/browser/songs.json" "$SITE" <<-'PY'
		import json, os, sys
		songs, site = json.load(open(sys.argv[1])), sys.argv[2]
		for song in songs:
		    if song["audio"].startswith("/media/") and not os.path.isfile(site + song["audio"]):
		        print(song["audio"])
		PY
	)
	if [[ -n $missing ]]; then
		echo "upload these files to $SITE/media first:" >&2
		echo "$missing" >&2
		exit 1
	fi
	staging=$SITE/releases/.staging-$commit
	rm -rf "$staging"
	cp -R "$dist" "$staging"
	chown -R root:root "$staging"
	chmod -R u=rwX,go=rX "$staging"
	mv -T "$staging" "$release"
fi

# Releases before web-v3 have no API; rolling back to them leaves the
# running API untouched (the old pages simply don't call it).
api_release=
if git -C "$REPO" cat-file -e "$commit:projects/unified/server/rhythmhit_api.py" 2>/dev/null; then
	api_release=$API/releases/$commit
fi
if [[ -n $api_release && ! -d $api_release ]]; then
	mkdir -p "$API/releases"
	staging=$API/releases/.staging-$commit
	rm -rf "$staging"
	mkdir -p "$staging"
	git -C "$REPO" show "$commit:projects/unified/server/rhythmhit_api.py" > "$staging/rhythmhit_api.py"
	python3 -c 'import ast, sys; ast.parse(open(sys.argv[1]).read())' "$staging/rhythmhit_api.py"
	chmod -R u=rwX,go=rX "$staging"
	mv -T "$staging" "$api_release"
fi
previous_api=$(readlink "$API/current" 2>/dev/null || true)
switch_api() {
	ln -sfn "$1" "$API/current.next"
	mv -Tf "$API/current.next" "$API/current"
	# A failed restart shows up in the health check below, which rolls back.
	systemctl restart rhythmhit-api || true
}

previous=$(readlink "$SITE/current" 2>/dev/null || true)
ln -sfn "$release" "$SITE/current.next"
mv -Tf "$SITE/current.next" "$SITE/current"
[[ -z $api_release ]] || switch_api "$api_release"

check() {
	local path
	for path in / /tutorial/ /main.py /browser/app.mjs; do
		curl -fsS -o /dev/null --max-time 10 --resolve "$HOST:443:127.0.0.1" "https://$HOST$path" || return 1
	done
	# The API needs a moment to bind after its restart.
	for _ in 1 2 3 4 5 6 7 8 9 10; do
		curl -fsS -o /dev/null --max-time 5 --resolve "$HOST:443:127.0.0.1" "https://$HOST/api/health" && return 0
		sleep 1
	done
	return 1
}
if [[ ${SKIP_HTTP_CHECK:-} != 1 ]] && ! check; then
	echo "HTTPS check failed" >&2
	if [[ -n $previous ]]; then
		ln -sfn "$previous" "$SITE/current.next"
		mv -Tf "$SITE/current.next" "$SITE/current"
		echo "restored $previous" >&2
	fi
	if [[ -n $api_release && -n $previous_api ]]; then
		switch_api "$previous_api"
		echo "restored API $previous_api" >&2
	fi
	exit 1
fi
echo "$commit" > "$SITE/deployed-commit"

# Keep the newest releases plus whatever current points to.
active=$(readlink "$SITE/current")
ls -1dt "$SITE"/releases/*/ 2>/dev/null | tail -n +$((KEEP + 1)) | while read -r old; do
	[[ ${old%/} == "$active" ]] || rm -rf "${old%/}"
done
ls -1dt "$API"/releases/*/ 2>/dev/null | tail -n +$((KEEP + 1)) | while read -r old; do
	[[ ${old%/} == "$(readlink "$API/current")" ]] || rm -rf "${old%/}"
done
echo "rhythmhit live at $commit"
