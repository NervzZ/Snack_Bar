#!/usr/bin/env bash
# Checks what a release needs and prints the version of the addon. Run from the top of the repo.
set -euo pipefail

toc=addon/Snack_Bar/Snack_Bar.toc

fail() {
	echo "::error::$1" >&2
	exit 1
}

field() {
	tr -d '\r' < "$toc" | sed -n "s/^## $1:[[:space:]]*//p"
}

version=$(field Version)
[[ $version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail "The version in Snack_Bar.toc must look like 1.2.3, not '$version'."
tr -d '\r' < CHANGELOG.md | grep -xF "## $version" > /dev/null || fail "CHANGELOG.md has no section for $version."

# The packager skips CurseForge without an error when the id is not a plain number.
if grep -q '^## X-Curse-Project-ID' "$toc"; then
	id=$(field X-Curse-Project-ID)
	[[ $id =~ ^[1-9][0-9]*$ ]] || fail "X-Curse-Project-ID in Snack_Bar.toc must be a number, not '$id'."
fi

echo "$version"
