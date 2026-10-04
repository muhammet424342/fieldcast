#!/usr/bin/env bash
# Install the Foundry dependencies the contract tests import.
#
# Why this file exists: contracts/lib/ is deliberately not in git, so a fresh clone
# has no OpenZeppelin and no forge-std, and `forge test` dies with
#   "Source lib/openzeppelin-contracts/contracts/utils/Pausable.sol not found".
# This script re-creates exactly the versions the imports need. It is idempotent:
# running it again on a set-up tree does nothing.
#
# OpenZeppelin 5.x is required, not arbitrary:
#   - the tests assert on Pausable.EnforcedPause and Ownable.OwnableUnauthorizedAccount,
#     which only exist as custom errors in 5.x (4.x uses require strings);
#   - the vault calls Ownable(initialOwner), and 4.x Ownable has no constructor argument;
#   - 4.x keeps Pausable at security/Pausable.sol, so the utils/Pausable.sol import path
#     does not even exist there.
#
# Usage: bash kur.sh && forge test
# Needs Foundry (forge) reachable; $HOME/.foundry/bin is added to PATH for you.

set -eu

export PATH="$HOME/.foundry/bin:$PATH"

# Work from the contracts directory whatever the caller used, so the paths below
# match the remappings in foundry.toml. $0 works for `bash kur.sh`, `./kur.sh` and
# an absolute path; nothing else in this script is bash-specific.
cd "$(dirname "$0")"

OZ="OpenZeppelin/openzeppelin-contracts@v5.7.0"
FORGE_STD="foundry-rs/forge-std@v1.9.7"

# The directory name (the "alias" in forge install) must equal the folder the
# remappings in foundry.toml point at: lib/<alias>/...
OZ_DIR="lib/openzeppelin-contracts"
FORGE_STD_DIR="lib/forge-std"
STAMP="lib/.kur-installed"

if ! command -v forge >/dev/null 2>&1; then
  echo "kur.sh: forge is not on PATH." >&2
  echo "kur.sh: install Foundry, or put its bin directory on PATH (looked in \$HOME/.foundry/bin)." >&2
  exit 1
fi

installed=$(cat "$STAMP" 2>/dev/null || true)
want="$OZ $FORGE_STD"

if [ "$installed" = "$want" ] \
   && [ -f "$OZ_DIR/contracts/utils/Pausable.sol" ] \
   && [ -f "$FORGE_STD_DIR/src/Test.sol" ]; then
  echo "kur.sh: already set up ($OZ, $FORGE_STD) - nothing to do."
else
  # A half-finished or stale tree is removed first: forge install refuses to
  # clone into a directory that already exists.
  rm -rf "$OZ_DIR" "$FORGE_STD_DIR" "$STAMP"
  echo "kur.sh: installing $OZ"
  forge install "openzeppelin-contracts=$OZ" --no-git --shallow
  echo "kur.sh: installing $FORGE_STD"
  forge install "forge-std=$FORGE_STD" --no-git --shallow
  printf '%s\n' "$want" > "$STAMP"
fi

# The remappings live in foundry.toml (there is no remappings.txt), so check that
# every path the imports resolve to is really on disk. A wrong remapping then
# fails here, loudly, instead of half-way through `forge test`.
missing=0
for f in \
  "$OZ_DIR/contracts/token/ERC20/IERC20.sol" \
  "$OZ_DIR/contracts/token/ERC20/ERC20.sol" \
  "$OZ_DIR/contracts/token/ERC20/utils/SafeERC20.sol" \
  "$OZ_DIR/contracts/access/Ownable.sol" \
  "$OZ_DIR/contracts/access/Ownable2Step.sol" \
  "$OZ_DIR/contracts/utils/Pausable.sol" \
  "$OZ_DIR/contracts/utils/ReentrancyGuard.sol" \
  "$FORGE_STD_DIR/src/Test.sol"
do
  if [ ! -f "$f" ]; then
    echo "kur.sh: remapping target missing: $f" >&2
    missing=1
  fi
done
[ "$missing" -eq 0 ] || exit 1

# Compile once, so a wrong version or a wrong remapping fails here instead of at
# `forge test`. --no-lint only silences informational lint notes, and it does not
# exist on every forge build, so ask before using it.
build_help=$(forge build --help 2>/dev/null || true)
case "$build_help" in
  *--no-lint*) forge build --no-lint ;;
  *) forge build ;;
esac

echo "kur.sh: ok - now run: forge test"