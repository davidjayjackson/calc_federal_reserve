#!/usr/bin/env bash
# Assemble the FRED Calc add-in into build/CalcFredAddin.oxt.
#
# Steps:
#   1. Compile idl/com/example/fred/XFred.idl into a UNO type library
#      (types/XFred.rdb) using the LibreOffice SDK's unoidl-write.
#   2. Stage the Python component, XCU config, description and manifest.
#   3. Zip the staging tree into build/CalcFredAddin.oxt.
#
# This is a real UNO Add-In (Python), which is the only way to get
# =FRED.VALUE(...) / =FRED.DESCRIPTION(...) into Calc's Function Wizard
# and formula autocomplete.
set -euo pipefail

LIBREOFFICE="${LIBREOFFICE:-/usr/lib64/libreoffice}"
ROOT="$(cd "$(dirname "$0")" && pwd)"

UW="$LIBREOFFICE/sdk/bin/unoidl-write"
TYPES_RDB="$LIBREOFFICE/program/types.rdb"
export LD_LIBRARY_PATH="$LIBREOFFICE/program${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

if [ ! -x "$UW" ]; then
    echo "unoidl-write not found at $UW - is the LibreOffice SDK installed?" >&2
    exit 1
fi

BUILD="$ROOT/build"
STAGE="$BUILD/oxt"
rm -rf "$STAGE"
mkdir -p "$STAGE/types" "$STAGE/python" "$STAGE/config" "$STAGE/META-INF"

echo "Compiling IDL -> types/XFred.rdb"
"$UW" "$TYPES_RDB" "$ROOT/idl" "$STAGE/types/XFred.rdb"

cp "$ROOT/src/fred_impl.py"             "$STAGE/python/fred_impl.py"
cp "$ROOT/registration/CalcAddIns.xcu"  "$STAGE/config/CalcAddIns.xcu"
cp "$ROOT/registration/description.xml" "$STAGE/description.xml"
cp "$ROOT/registration/manifest.xml"    "$STAGE/META-INF/manifest.xml"

OXT="$BUILD/CalcFredAddin.oxt"
rm -f "$OXT"
(cd "$STAGE" && zip -qr "$OXT" .)

echo "Built $OXT"
