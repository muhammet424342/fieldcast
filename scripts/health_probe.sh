#!/usr/bin/env bash
# Fieldcast probu icin ince sarmalayici.
#
# NEDEN VAR: saglik probu Python. Bu makinede sistem python3'te flask/x402
# KURULU DEGIL; proje kendi .venv'ini kullanir. Burada sirayla:
#   1) FIELDCAST_PROBE_PYTHON (acik secim)
#   2) bu kopyanin .venv'i
#   3) calisma kopyasinin .venv'i (git ortak dizini = worktree'siz klon)
#   4) sistem python3
# Probu calistiran yorumlayici bilgisi stdout'a "[probe] ..." ile yazilir;
# probe'un kendi ciktisi degistirilmez.
#
# CIKIS KODU dogrudan gecer: 0 saglikli, 1 CRITIK bulundu, 2 komut hatasi.
# `set -e` YOK: probun 1 donmesi hata degil, "kritik bulundu" demektir.
set -uo pipefail

KOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROBE="$KOK/scripts/health_probe.py"

if [ ! -f "$PROBE" ]; then
  echo "[probe] HATA: $PROBE bulunamadi" >&2
  exit 2
fi

# venv/bin/python sembolik bag olabilir; realpath alinirsa site-packages
# kaybolur. Bu yuzden COZULMEZ, yolu oldugu gibi kullanilir.
sec=""
for aday in \
  "${FIELDCAST_PROBE_PYTHON:-}" \
  "$KOK/.venv/bin/python" \
  ""
do
  [ -n "$aday" ] || continue
  if [ -x "$aday" ]; then sec="$aday"; break; fi
done

if [ -z "$sec" ]; then
  ortak="$(git -C "$KOK" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)"
  if [ -n "$ortak" ]; then
    aday="$(dirname "$ortak")/.venv/bin/python"
    [ -x "$aday" ] && sec="$aday"
  fi
fi

if [ -z "$sec" ]; then
  if command -v python3 >/dev/null 2>&1; then
    sec="$(command -v python3)"
    echo "[probe] proje .venv'i yok; sistem python3 kullaniliyor ($sec)" >&2
  else
    echo "[probe] HATA: python3 bulunamadi" >&2
    exit 2
  fi
else
  echo "[probe] yorumlayici: $sec" >&2
fi

exec "$sec" "$PROBE" "$@"