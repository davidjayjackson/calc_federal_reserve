# calc_federal_reserve

A LibreOffice Calc Add-In that pulls economic data and series descriptions
from [FRED](https://fred.stlouisfed.org/) (Federal Reserve Bank of St.
Louis) directly into a spreadsheet.

## Functions

```
FRED.VALUE(series_id; [date]; [api_key])
```
Looks up a FRED series observation. If `date` is omitted, returns the most
recent available observation; otherwise returns the most recent observation
on or before `date` (a Calc date value or an `"YYYY-MM-DD"` string). If
`api_key` is omitted, the `FRED_API_KEY` environment variable is used
instead (see Setup below).

```
=FRED.VALUE("UNRATE")                    -> latest unemployment rate
=FRED.VALUE("GDP"; "2023-01-01")         -> GDP as of the observation on/before that date
=FRED.VALUE("CPIAUCSL"; A1)              -> A1 is a date cell
=FRED.VALUE("GDP"; ; $Z$1)               -> no date, explicit key from cell Z1
```

```
FRED.DESCRIPTION(series_id; [field]; [api_key])
```
Looks up a metadata field describing a FRED series. `field` defaults to
`"title"` and may otherwise be one of: `units`, `units_short`, `frequency`,
`frequency_short`, `seasonal_adjustment`, `seasonal_adjustment_short`,
`notes`, `last_updated`, `observation_start`, `observation_end`,
`popularity`. `api_key` behaves the same as in `FRED.VALUE`.

```
=FRED.DESCRIPTION("GDP")          -> "Gross Domestic Product"
=FRED.DESCRIPTION("GDP"; "units") -> "Billions of Dollars"
```

Series IDs are the short codes FRED uses on each series' page, e.g.
[`GDP`](https://fred.stlouisfed.org/series/GDP),
[`UNRATE`](https://fred.stlouisfed.org/series/UNRATE),
[`CPIAUCSL`](https://fred.stlouisfed.org/series/CPIAUCSL).

## Setup

### 1. Get a FRED API key

Free, from <https://fred.stlouisfed.org/docs/api/api_key.html>.

### 2. Make it visible to LibreOffice

There are two ways to supply the key; pick whichever is less friction for you.

**Option A — pass it as the `api_key` argument**, e.g. put it in one cell
(say `Z1`) and reference that cell from every formula:
`=FRED.VALUE("GDP"; ; $Z$1)`. Works immediately, no environment
configuration needed. Trade-off: the key is stored in plain text in that
cell, and travels with the file if you share or commit it.

**Option B — the `FRED_API_KEY` environment variable**, read **at the time
LibreOffice itself starts** — not just a terminal you happened to export it
in. If you launch `soffice` from a desktop icon/app launcher, it will *not*
see a variable you only exported in a terminal. Two reliable ways to set it:

- Export it in a shell and launch LibreOffice **from that same shell**:
  ```sh
  export FRED_API_KEY=your_key_here
  soffice --calc
  ```
- Put it in a login-time environment file (e.g. `~/.profile` or
  `~/.config/environment.d/fred.conf` on systemd-based distros) and fully
  log out and back in — not just restart LibreOffice — so the desktop
  session's environment picks it up. You can check what a running
  `soffice` process actually sees with
  `tr '\0' '\n' < /proc/$(pgrep -f soffice.bin)/environ | grep FRED_API_KEY`.

### 3. Build and install the extension

Requires the LibreOffice **SDK** package installed (for `unoidl-write`; no
C++/Java compiler needed):

```sh
./build_addin.sh                        # -> build/CalcFredAddin.oxt
unopkg add --force build/CalcFredAddin.oxt
```

Restart LibreOffice after installing. `FRED.VALUE` and `FRED.DESCRIPTION`
will then appear in the Function Wizard under the "Add-In" category and in
formula autocomplete.

To remove: `unopkg remove com.example.fred`.

## Demo

`examples/FRED_Demo.ods` shows both functions in use: a table of popular
series (GDP, UNRATE, CPIAUCSL, FEDFUNDS, DGS10, PAYEMS) with their title,
units, frequency, latest value and last-updated timestamp, plus an
as-of-date lookup example. Cell `B3` is a blank slot for your API key that
every formula in the sheet passes as its `api_key` argument.

Note that Calc always recalculates Add-In function cells on open (they're
treated as volatile, unlike ordinary formulas), so this only shows real
values once you've either pasted a key into `B3` or have `FRED_API_KEY` set
for LibreOffice — you'll see `#VALUE!` in every data cell until then.

## Development

- `idl/` — the UNO interface (`XFred`) Calc calls into.
- `src/fred_impl.py` — the implementation, run by LibreOffice's own bundled
  Python interpreter (not the project `.venv`).
- `registration/` — `.xcu` config (Function Wizard names/descriptions),
  `description.xml` (extension metadata), `manifest.xml` (packaging map).
- `build_addin.sh` — assembles the pieces above into `build/CalcFredAddin.oxt`.
- `tools/test_addin.py` — end-to-end test driving a headless LibreOffice
  instance over UNO; see `CLAUDE.md` for how to run it.
- `tools/build_demo.py` — (re)generates `examples/FRED_Demo.ods`; also
  driven over UNO, see the script's docstring.

The `.venv` under the LibreOffice directory (`../.venv`) is for local
analysis/dev tooling, not for the add-in itself — see `CLAUDE.md` for why.

See `CLAUDE.md` for full architecture notes.
