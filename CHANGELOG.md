# Changelog

## 1.0.0

- Initial release: `FRED.VALUE(series_id; [date])` and
  `FRED.DESCRIPTION(series_id; [field])` Calc Add-In functions backed by the
  FRED (Federal Reserve Bank of St. Louis) API.
- Added `examples/FRED_Demo.ods` demo workbook and the `tools/build_demo.py`
  script that generates it.
- Added an optional trailing `api_key` argument to both functions, so a key
  can be passed directly in the formula as an alternative to the
  `FRED_API_KEY` environment variable.
- Added `FRED.SERIES(series_id; start_date; [end_date]; [api_key])`,
  returning a whole range of observations as a (date, value) matrix for use
  as an array formula.
- Added `macros/FredMacros.bas` (installed via `tools/install_macro.py`), a
  Basic macro that dumps a series into the sheet as static values instead
  of a live formula - no ongoing dependency on the add-in, network, or key
  once written.
- Updated `examples/FRED_Demo.ods` with a `FRED.SERIES` array-formula
  example (quarterly GDP history).
