"""One-off script that builds examples/FRED_Demo.ods.

Not part of the add-in itself - a dev tool to (re)generate the demo
workbook. Drives a headless LibreOffice instance over UNO (same connection
approach as test_addin.py); the FRED Calc Add-In must already be installed.

Reads FRED_API_KEY from *this script's own* environment (not soffice's) and
types it into the sheet's key cell (B3) - which every demo formula passes
as its api_key argument - just long enough to compute real values, then
blanks that cell before saving. This keeps the key out of the committed
file while still shipping cached, real numbers; it also means the demo
works regardless of whether FRED_API_KEY happens to be visible to whatever
process ends up running soffice.

    soffice --headless --invisible --norestore --accept="socket,host=localhost,port=2002;urp;" &
    FRED_API_KEY=your_key_here /usr/lib64/libreoffice/program/python tools/build_demo.py
"""
import os
import sys
import time
import uno
from com.sun.star.awt import FontWeight
from com.sun.star.beans import PropertyValue


SERIES = [
    ("GDP", "Gross Domestic Product"),
    ("UNRATE", "Unemployment Rate"),
    ("CPIAUCSL", "Consumer Price Index (All Urban Consumers)"),
    ("FEDFUNDS", "Federal Funds Effective Rate"),
    ("DGS10", "10-Year Treasury Constant Maturity Rate"),
    ("PAYEMS", "Total Nonfarm Payroll Employment"),
]


def connect(port=2002, tries=40):
    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local)
    url = "uno:socket,host=localhost,port=%d;urp;StarOffice.ComponentContext" % port
    last = None
    for _ in range(tries):
        try:
            return resolver.resolve(url)
        except Exception as e:
            last = e
            time.sleep(0.5)
    raise SystemExit("could not connect to LibreOffice: %s" % last)


def set_bold(cell):
    cell.CharWeight = FontWeight.BOLD


def main():
    ctx = connect()
    smgr = ctx.ServiceManager
    desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)

    doc = desktop.loadComponentFromURL("private:factory/scalc", "_blank", 0, ())
    sheet = doc.Sheets.getByIndex(0)
    sheet.Name = "FRED Demo"

    title = sheet.getCellByPosition(0, 0)
    title.setString("FRED Calc Add-In — Demo")
    title.CharHeight = 16
    set_bold(title)

    subtitle = sheet.getCellByPosition(0, 1)
    subtitle.setString(
        "Live economic data via FRED.VALUE() / FRED.DESCRIPTION() "
        "(paste your key below, or set FRED_API_KEY for LibreOffice)"
    )

    key_label = sheet.getCellByPosition(0, 2)
    key_label.setString("Your FRED API key (optional; overrides FRED_API_KEY):")
    key_cell = sheet.getCellByPosition(1, 2)
    key_cell.CellBackColor = 0xFFF2CC
    key_cell_ref = "$B$3"

    headers = ["Series ID", "Title (FRED.DESCRIPTION)", "Units", "Frequency",
               "Latest Value (FRED.VALUE)", "Last Updated"]
    header_row = 4
    for col, text in enumerate(headers):
        cell = sheet.getCellByPosition(col, header_row)
        cell.setString(text)
        set_bold(cell)
        cell.CellBackColor = 0xDCE6F1

    for i, (series_id, _label) in enumerate(SERIES):
        row = header_row + 1 + i
        id_cell = sheet.getCellByPosition(0, row)
        id_cell.setString(series_id)

        sheet.getCellByPosition(1, row).setFormula(
            '=FRED.DESCRIPTION($A%d;"title";%s)' % (row + 1, key_cell_ref))
        sheet.getCellByPosition(2, row).setFormula(
            '=FRED.DESCRIPTION($A%d;"units";%s)' % (row + 1, key_cell_ref))
        sheet.getCellByPosition(3, row).setFormula(
            '=FRED.DESCRIPTION($A%d;"frequency";%s)' % (row + 1, key_cell_ref))
        sheet.getCellByPosition(4, row).setFormula(
            '=FRED.VALUE($A%d;;%s)' % (row + 1, key_cell_ref))
        sheet.getCellByPosition(5, row).setFormula(
            '=FRED.DESCRIPTION($A%d;"last_updated";%s)' % (row + 1, key_cell_ref))

    # A second example further down: pulling a historical (as-of-date) value.
    asof_row = header_row + 1 + len(SERIES) + 2
    note = sheet.getCellByPosition(0, asof_row)
    note.setString("As-of-date lookup: FRED.VALUE(series_id; date)")
    set_bold(note)

    label_row = asof_row + 1
    sheet.getCellByPosition(0, label_row).setString("GDP")
    sheet.getCellByPosition(1, label_row).setString("as of")
    date_cell = sheet.getCellByPosition(2, label_row)
    date_cell.setFormula('=DATE(2020;1;1)')
    locale = uno.createUnoStruct("com.sun.star.lang.Locale")
    formats = doc.getNumberFormats()
    date_format = formats.queryKey("YYYY-MM-DD", locale, False)
    if date_format == -1:
        date_format = formats.addNew("YYYY-MM-DD", locale)
    date_cell.NumberFormat = date_format

    value_cell = sheet.getCellByPosition(3, label_row)
    value_cell.setFormula(
        '=FRED.VALUE($A%d;$C%d;%s)' % (label_row + 1, label_row + 1, key_cell_ref))

    # A third example: pulling a whole range as an array formula. FRED.SERIES
    # returns a matrix, so it must be entered via setArrayFormula (the UI
    # equivalent is: select the range, type the formula, Ctrl+Shift+Enter -
    # this LibreOffice build doesn't auto-spill a single-cell array result).
    series_note_row = label_row + 3
    note2 = sheet.getCellByPosition(0, series_note_row)
    note2.setString(
        "Array formula: FRED.SERIES(series_id; start_date; [end_date]; [api_key]) "
        "- select the range first, then Ctrl+Shift+Enter"
    )
    set_bold(note2)

    series_sub_row = series_note_row + 1
    sheet.getCellByPosition(0, series_sub_row).setString(
        "GDP, quarterly, from 2023-01-01 (date column left as raw serials - "
        "see note below on why)")

    series_header_row = series_note_row + 2
    date_header = sheet.getCellByPosition(0, series_header_row)
    date_header.setString("Date")
    set_bold(date_header)
    value_header = sheet.getCellByPosition(1, series_header_row)
    value_header.setString("Value")
    set_bold(value_header)

    series_data_start = series_header_row + 1
    series_data_rows = 8
    series_range = sheet.getCellRangeByName(
        "A%d:B%d" % (series_data_start + 1, series_data_start + series_data_rows))
    series_range.setArrayFormula(
        '=FRED.SERIES("GDP";"2023-01-01";;%s)' % key_cell_ref)
    # Deliberately not formatting column A as a date here: all cells in a
    # single array-formula block share one number format in Calc, so
    # formatting just the date column also reformats the value column as
    # dates (discovered the hard way - see CLAUDE.md). Paste Special >
    # Values Only first if you want the date column formatted independently.

    # Column widths for readability.
    widths = [2500, 9000, 3500, 2500, 4000, 3000]
    for col, w in enumerate(widths):
        sheet.Columns.getByIndex(col).Width = w

    # Compute real values using a key supplied only for this build step (via
    # FRED_API_KEY in this process's environment), then blank the key cell
    # before saving so no secret ends up in the committed file. The formulas'
    # cached results stay in the saved file; recalculating after reopening
    # needs either FRED_API_KEY set for LibreOffice, or a key pasted into
    # the (now empty) key cell.
    build_key = os.environ.get("FRED_API_KEY")
    if not build_key:
        raise SystemExit("set FRED_API_KEY in this process's environment to build the demo")
    key_cell.setString(build_key)
    doc.calculateAll()
    key_cell.setString("")

    out_url = "file://" + os.path.abspath("examples/FRED_Demo.ods")
    save_props = (PropertyValue(Name="FilterName", Value="calc8"),)
    doc.storeToURL(out_url, save_props)
    doc.close(False)
    desktop.terminate()

    print("Wrote", out_url)


if __name__ == "__main__":
    main()
