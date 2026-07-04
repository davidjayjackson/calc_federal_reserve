# calc_federal_reserve

A LibreOffice Calc Add-In that pulls economic data and series descriptions
from [FRED](https://fred.stlouisfed.org/) (Federal Reserve Bank of St.
Louis) directly into a spreadsheet.

## Functions

```
FRED.VALUE(series_id; [date])
```
Looks up a FRED series observation. If `date` is omitted, returns the most
recent available observation; otherwise returns the most recent observation
on or before `date` (a Calc date value or an `"YYYY-MM-DD"` string).

```
=FRED.VALUE("UNRATE")            -> latest unemployment rate
=FRED.VALUE("GDP"; "2023-01-01") -> GDP as of the observation on/before that date
=FRED.VALUE("CPIAUCSL"; A1)      -> A1 is a date cell
```

```
FRED.DESCRIPTION(series_id; [field])
```
Looks up a metadata field describing a FRED series. `field` defaults to
`"title"` and may otherwise be one of: `units`, `units_short`, `frequency`,
`frequency_short`, `seasonal_adjustment`, `seasonal_adjustment_short`,
`notes`, `last_updated`, `observation_start`, `observation_end`,
`popularity`.

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

The add-in reads the key from the `FRED_API_KEY` environment variable **at
the time LibreOffice itself starts** — not just a terminal you happened to
export it in. If you launch `soffice` from a desktop icon/app launcher, it
will *not* see a variable you only exported in a terminal. Two reliable
options:

- Export it in a shell and launch LibreOffice **from that same shell**:
  ```sh
  export FRED_API_KEY=your_key_here
  soffice --calc
  ```
- Put it in a login-time environment file (e.g. `~/.profile` or
  `~/.config/environment.d/fred.conf` on systemd-based distros) and log out
  and back in so desktop-launched apps inherit it too.

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

## Development

- `idl/` — the UNO interface (`XFred`) Calc calls into.
- `src/fred_impl.py` — the implementation, run by LibreOffice's own bundled
  Python interpreter (not the project `.venv`).
- `registration/` — `.xcu` config (Function Wizard names/descriptions),
  `description.xml` (extension metadata), `manifest.xml` (packaging map).
- `build_addin.sh` — assembles the pieces above into `build/CalcFredAddin.oxt`.
- `tools/test_addin.py` — end-to-end test driving a headless LibreOffice
  instance over UNO; see `CLAUDE.md` for how to run it.

The `.venv` under the LibreOffice directory (`../.venv`) is for local
analysis/dev tooling, not for the add-in itself — see `CLAUDE.md` for why.

See `CLAUDE.md` for full architecture notes.
