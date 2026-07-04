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
