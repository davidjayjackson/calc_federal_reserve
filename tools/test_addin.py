"""End-to-end test for the FRED Calc Add-In (build/CalcFredAddin.oxt).

Run with LibreOffice's bundled Python (it ships the `uno` module) against a
headless instance listening on a UNO socket:

    soffice --headless --invisible --norestore --accept="socket,host=localhost,port=2002;urp;" &
    /usr/lib64/libreoffice/program/python tools/test_addin.py

Prints RESULT: PASS / FAIL and exits non-zero on failure. Requires the
extension to already be installed (see build_addin.sh + `unopkg add`).

Always checks that FRED.VALUE / FRED.DESCRIPTION / FRED.SERIES are
registered as real Add-Ins (proves Function Wizard/autocomplete wiring). If
FRED_API_KEY is set in the environment this process was launched from, it
also drives live formulas against the real FRED API; otherwise that part is
skipped since there is no key to call out with.
"""
import os
import sys
import time
import uno


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


def main():
    ctx = connect()
    smgr = ctx.ServiceManager
    desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)

    # 1. FRED.VALUE / FRED.DESCRIPTION / FRED.SERIES are registered as real Add-Ins.
    fdescs = smgr.createInstanceWithContext("com.sun.star.sheet.FunctionDescriptions", ctx)
    registered_names = {
        {p.Name: p.Value for p in fdescs.getByIndex(i)}.get("Name")
        for i in range(fdescs.Count)
    }
    value_registered = "FRED.VALUE" in registered_names
    description_registered = "FRED.DESCRIPTION" in registered_names
    series_registered = "FRED.SERIES" in registered_names

    print("FRED.VALUE registered:", value_registered)
    print("FRED.DESCRIPTION registered:", description_registered)
    print("FRED.SERIES registered:", series_registered)

    ok = value_registered and description_registered and series_registered

    if os.environ.get("FRED_API_KEY"):
        doc = desktop.loadComponentFromURL("private:factory/scalc", "_blank", 0, ())
        try:
            sheet = doc.Sheets.getByIndex(0)
            value_cell = sheet.getCellByPosition(0, 0)
            value_cell.setFormula('=FRED.VALUE("GDP")')
            desc_cell = sheet.getCellByPosition(0, 1)
            desc_cell.setFormula('=FRED.DESCRIPTION("GDP")')

            series_range = sheet.getCellRangeByName("A3:B6")
            series_range.setArrayFormula('=FRED.SERIES("GDP";"2023-01-01";"2023-12-31")')

            doc.calculateAll()

            value_ok = value_cell.getError() == 0 and value_cell.getValue() > 0
            desc_ok = desc_cell.getError() == 0 and len(desc_cell.getString()) > 0
            series_ok = (
                sheet.getCellByPosition(0, 2).getError() == 0
                and sheet.getCellByPosition(1, 2).getValue() > 0
            )

            print("FRED.VALUE(\"GDP\") ->", value_cell.getValue(), "PASS" if value_ok else "FAIL")
            print("FRED.DESCRIPTION(\"GDP\") ->", desc_cell.getString(), "PASS" if desc_ok else "FAIL")
            print("FRED.SERIES(\"GDP\";...) first row ->",
                  sheet.getCellByPosition(0, 2).getValue(), sheet.getCellByPosition(1, 2).getValue(),
                  "PASS" if series_ok else "FAIL")
            ok = ok and value_ok and desc_ok and series_ok
        finally:
            doc.close(False)
    else:
        print("FRED_API_KEY not set - skipping live API call test")

    desktop.terminate()

    print("RESULT:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
