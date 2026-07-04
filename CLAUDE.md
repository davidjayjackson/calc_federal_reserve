# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Three Calc functions, `FRED.VALUE()`, `FRED.DESCRIPTION()` and
`FRED.SERIES()`, that pull economic data and series metadata from FRED
(Federal Reserve Bank of St. Louis, https://fred.stlouisfed.org/) directly
into a spreadsheet. Like `../calc_loess_addin`, this is implemented as a
real UNO Add-In (`com.sun.star.sheet.AddIn`) in Python
(`src/fred_impl.py`), not a Basic macro — that's what gets the functions
into the Function Wizard and formula autocomplete, which are driven by
`com.sun.star.sheet.FunctionDescriptions` and only enumerate real,
registered Add-Ins.

## Commands

Build the `.oxt` extension package (requires the LibreOffice **SDK**, for
`unoidl-write`; no C++/Java compiler needed):

```sh
./build_addin.sh                              # -> build/CalcFredAddin.oxt
```

`LIBREOFFICE` env var overrides the install dir (default
`/usr/lib64/libreoffice`; must contain `sdk/bin/unoidl-write` and
`program/types.rdb`).

Install/reinstall (LibreOffice must be restarted after):

```sh
unopkg add --force build/CalcFredAddin.oxt
```

Remove:

```sh
unopkg remove com.example.fred
```

Run the end-to-end test against a headless LibreOffice instance (requires
the extension to already be installed):

```sh
soffice --headless --invisible --norestore --accept="socket,host=localhost,port=2002;urp;" &
/usr/lib64/libreoffice/program/python tools/test_addin.py
```

The test always checks that all three functions are registered in
`FunctionDescriptions`. It only drives a live formula against the real FRED
API if `FRED_API_KEY` is set in the environment the test process runs in
(same env-var requirement as the add-in itself — see README.md).

## Architecture

**IDL interface (`idl/com/example/fred/XFred.idl`) defines the contract
Calc calls into.** `unoidl-write` compiles this into `types/XFred.rdb`
inside the `.oxt`. The directory path `idl/com/example/fred/` must match
the `module com { module example { module fred { ... } } }` declaration —
`unoidl-write`'s source-tree reader derives the UNO module name from the
directory structure, not from the file's own `module {}` block.

**`src/fred_impl.py` implements that interface** as a `unohelper.Base`
subclass registered as both `com.example.fred.FredImpl` and the generic
`com.sun.star.sheet.AddIn` service. `date`, `field` and `apiKey` are typed
`any` in the IDL so they arrive as Python `None` when the formula omits
them.

**No third-party HTTP library is used or needed.** `fred_impl.py` runs
under LibreOffice's *own bundled* CPython interpreter
(`/usr/lib64/libreoffice/program/python`), not the `.venv` at
`../.venv` — that venv has no `requests`/`fredapi` installed and
extensions can't rely on packages from a different Python environment
anyway. Instead the add-in uses only stdlib `urllib.request` + `json`, both
present in the bundled interpreter. The `../.venv` is for local
dev/analysis tooling (pandas, matplotlib, etc. — see sibling projects), not
for the add-in runtime.

**A small in-process cache (`_cache` dict in `fred_impl.py`) memoizes API
responses by URL** for `OBSERVATIONS_CACHE_TTL` (5 min) / `METADATA_CACHE_TTL`
(1 hour) seconds. Calc can re-evaluate the same formula on every keystroke
or recalculation; without this, a sheet with several `FRED.*` formulas
would hammer the FRED API (which is rate-limited) far more than the data
actually changes. This cache is process-local and gets no benefit from
persisting across LibreOffice restarts.

**Calc always recalculates Add-In function cells on file open** — they're
treated as volatile, unlike ordinary formulas whose last computed value is
trusted from the saved file. This showed up while building
`examples/FRED_Demo.ods`: computing real values at build time and then
saving them didn't help, because reopening the file recalculates from
scratch anyway and shows `#VALUE!` if no key is available at that moment.
`tools/build_demo.py` still computes real values during the build (as a
sanity check that the sheet actually works), but don't expect that to
translate into cached values a user sees without their own key.

**`FRED.SERIES` returns `sequence<sequence<any>>`** (a matrix), not a
scalar, so it must be entered as a classic array formula (select the
target range, type the formula, Ctrl+Shift+Enter) — this LibreOffice build
doesn't spill a single-cell array-result formula automatically. Its date
column is converted to a Calc serial number via `CALC_EPOCH` (the reverse
of what `_as_iso_date` does for input dates); the cell itself isn't
reformatted as a date by the add-in, since a UNO Add-In function has no way
to set the number format of the cell it's called from — that's on the
user, via Format ▸ Cells.

**Setting `NumberFormat` on one cell of an array-formula block propagates
to the whole block** — you cannot format just the date column of a
`FRED.SERIES` result while leaving the value column as a plain number.
Found this the hard way building the demo's `FRED.SERIES` section:
formatting column A as a date silently reformatted column B's GDP values
as dates too (`27216.445` displayed as `1974-07-06`, i.e. that many days
after the Calc epoch). Reproduced with plain unrelated numbers (a 3x2
array of `=A1:B3*1`) to confirm it's an array-formula quirk, not something
specific to `FRED.SERIES` - and it isn't simple format-copying either: only
D1 (the cell actually touched) got the exact format code set on it, while
every other cell in the block silently picked up a *different* auto-guessed
date/time format. Read this as "don't touch `NumberFormat` on any cell of
an array-formula range unless you want the whole block visually
reinterpreted," not as "cells in an array share one deliberate format."

The fix used in `tools/build_demo.py`: leave the array's raw date column
unformatted, and add a *separate*, ordinary (non-array) helper column with
`=TEXT($A1;"YYYY-MM-DD")` for a readable date string - `TEXT()` returns a
plain string, so it's a normal per-cell formula unaffected by the array's
shared-format behavior. Converting the array to static values first (Copy,
Paste Special → Values Only) also works, since that removes the array
grouping entirely and each cell can then be formatted independently.

**`registration/CalcAddIns.xcu` is what actually populates the Function
Wizard** — display names, descriptions, category ("Add-In"), and
per-argument help text. The `XAddIn` methods on `FredAddIn`
(`getFunctionDescription`, `getDisplayArgumentName`, etc.) are a fallback
path and largely redundant with the `.xcu` in practice.

**`build_addin.sh` assembles the `.oxt`** from these pieces:
`idl/` → compiled `.rdb` (via `unoidl-write`), `src/fred_impl.py`,
`registration/*.xcu`/`manifest.xml`/`description.xml` — staged into
`build/oxt/` and zipped. `registration/manifest.xml` maps each staged file
to its final path inside the package (`types/`, `python/`, `config/`).

## The "dump as static table" macro

`macros/FredMacros.bas` is a Basic macro (`FredDumpSeries`, plus a helper
`FredWriteSeries` and `FredCleanError`) for one-shot snapshots: it prompts
for series ID/dates/key via `InputBox`, then writes plain static values
(`setValue`, not `setFormula`) starting at whatever cell is selected -
unlike `FRED.SERIES`, the result has no ongoing dependency on the add-in,
network, or key once written, and needs no Ctrl+Shift+Enter.

**`FredWriteSeries` calls `createUnoService("com.example.fred.FredImpl")`
directly** rather than duplicating the HTTP/parsing logic - `FredImpl` is
registered under both `com.example.fred.FredImpl` (a plain instantiable
service) and `com.sun.star.sheet.AddIn`, so Basic can create and call it
like any other UNO service, sidestepping the Calc formula/cell layer
entirely. Confirmed empirically (see below) rather than assumed, since this
isn't the primary documented use of an Add-In service.

**`tools/install_macro.py` installs the library programmatically** via
`smgr.createInstanceWithContext("com.sun.star.script.ApplicationScriptLibraryContainer", ctx)`
(this is the *application-level* / "My Macros" Basic library storage,
despite the service name looking document-scoped) rather than shipping a
hand-crafted `Basic/` folder inside the `.oxt` - packaging a Basic library
into an extension requires exact `script.xlb`/`.xba` XML that's easy to get
subtly wrong and hard to debug; driving the real `XLibraryContainer` API
(`createLibrary`, `insertByName`, `storeLibraries()`) gets the same result
with much less risk. `install_macro.py` always removes and recreates the
library, so it's safe to re-run after editing the `.bas` source - don't
call `replaceByName` on a library that may be in a bad state (a module that
failed to compile on `insertByName` can leave the library object
throwing `WrappedTargetException` on every subsequent call; discovered
while testing invalid-series error handling - the fix was a fresh
`removeLibrary`/`createLibrary` rather than reusing the handle).

**Two Calc API surprises found while building this, worth remembering if
touching it again:**
- There's no `ViewCursor` on a Calc controller (that's a Writer-only
  concept). The correct way to get the "current cell" in Calc is
  `oDoc.CurrentController.Selection` - a single selected cell supports
  `.RangeAddress` (via `XCellRangeAddressable`) just like a multi-cell
  range does, so no need to branch on selection shape.
- A Python exception raised inside a UNO service method, when the method
  is called from Basic, surfaces as a catchable Basic runtime error (`On
  Error GoTo` works) - but `Error$` dumps the *entire* pyuno-formatted
  block (exception type + message + full Python traceback), not just the
  message. `FredCleanError` in the `.bas` file strips it down to the text
  between `Message:` and `, traceback follows`.

Tested via the same headless-instance-over-UNO approach as
`tools/test_addin.py`: install the library, then invoke
`FredWriteSeries`/`FredCleanError` directly by name via
`com.sun.star.script.provider.MasterScriptProviderFactory` with explicit
arguments (bypassing the `InputBox` calls in `FredDumpSeries`, which would
otherwise hang forever waiting for input that never comes in `--headless`
mode - there is no way to drive `InputBox`/`MsgBox` from an automated test).

## API key

Both functions take an optional trailing `api_key` argument
(`_resolve_api_key` in `fred_impl.py`); if omitted, `FRED_API_KEY` is read
from the environment instead. The env var must be set in the environment
LibreOffice itself runs in — not just a terminal you happened to export it
in, since a `soffice` launched from a desktop icon doesn't inherit that
shell's environment. This bit a real user during development: they'd
exported the var in a terminal after LibreOffice was already running, so
the running `soffice.bin` process never saw it — confirmed by reading
`/proc/<pid>/environ` directly, which is the fastest way to debug this
class of issue rather than guessing about shell/login semantics. See
README.md's Setup section for both ways to supply the key.

## Versioning

`registration/description.xml`'s `<version>` and `CHANGELOG.md` should be
bumped together on every release.
