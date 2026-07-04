"""Installs macros/FredMacros.bas into LibreOffice's "My Macros" (the
application-level Basic library storage), so it's available from
Tools > Macros > Run Macro without any manual copy-pasting.

Run against an already-running LibreOffice instance (drives it over UNO,
same connection approach as test_addin.py):

    soffice --accept="socket,host=localhost,port=2002;urp;" &
    /usr/lib64/libreoffice/program/python tools/install_macro.py

Safe to re-run - replaces the "FredMacros" library if it already exists.
"""
import os
import sys
import time
import uno

LIBRARY_NAME = "FredMacros"
MODULE_NAME = "Module1"


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
    libs = smgr.createInstanceWithContext(
        "com.sun.star.script.ApplicationScriptLibraryContainer", ctx)

    bas_path = os.path.join(os.path.dirname(__file__), "..", "macros", "FredMacros.bas")
    with open(bas_path, "r") as f:
        source = f.read()

    if libs.hasByName(LIBRARY_NAME):
        libs.removeLibrary(LIBRARY_NAME)
    lib = libs.createLibrary(LIBRARY_NAME)
    lib.insertByName(MODULE_NAME, source)
    libs.storeLibraries()

    print("Installed %s.%s into My Macros." % (LIBRARY_NAME, MODULE_NAME))
    print('Run via Tools > Macros > Run Macro... > My Macros > %s > %s > FredDumpSeries'
          % (LIBRARY_NAME, MODULE_NAME))


if __name__ == "__main__":
    main()
