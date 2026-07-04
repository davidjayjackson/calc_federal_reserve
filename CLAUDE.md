# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Two Calc functions, `FRED.VALUE()` and `FRED.DESCRIPTION()`, that pull
economic data and series metadata from FRED (Federal Reserve Bank of St.
Louis, https://fred.stlouisfed.org/) directly into a spreadsheet. Like
`../calc_loess_addin`, this is implemented as a real UNO Add-In
(`com.sun.star.sheet.AddIn`) in Python (`src/fred_impl.py`), not a Basic
macro — that's what gets the functions into the Function Wizard and formula
autocomplete, which are driven by `com.sun.star.sheet.FunctionDescriptions`
and only enumerate real, registered Add-Ins.

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

The test always checks that both functions are registered in
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
`com.sun.star.sheet.AddIn` service. `date` and `field` are typed `any` in
the IDL so they arrive as Python `None` when the formula omits them.

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
actually changes.

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

## API key

`FRED_API_KEY` must be set in the environment LibreOffice itself runs in —
not just a terminal you happened to export it in, since a `soffice`
launched from a desktop icon doesn't inherit that shell's environment. See
README.md's Setup section for the two reliable ways to make that true.

## Versioning

`registration/description.xml`'s `<version>` and `CHANGELOG.md` should be
bumped together on every release.
