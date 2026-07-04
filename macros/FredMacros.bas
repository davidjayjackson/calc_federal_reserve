' FredMacros - dumps a FRED series into the sheet as static values (no
' formulas, no live dependency on the add-in afterward).
'
' Installed into "My Macros" by tools/install_macro.py. Reuses the same
' com.example.fred.FredImpl UNO service that backs the FRED.SERIES() Calc
' function, called directly rather than through a cell formula.
'
' Run via Tools > Macros > Run Macro... > My Macros > FredMacros > Module1
' > FredDumpSeries, after selecting the top-left cell to write into.

Sub FredDumpSeries
    Dim seriesId As String, startDate As String, endDate As String, apiKey As String
    Dim vEndDate As Variant, vApiKey As Variant
    Dim oDoc As Object, oSel As Object
    Dim nCol As Integer, nRow As Integer
    Dim nRows As Long

    seriesId = InputBox("FRED series ID (e.g. GDP, UNRATE, CPIAUCSL):", "FRED: Dump Series as Static Table")
    If Trim(seriesId) = "" Then Exit Sub

    startDate = InputBox("Start date (YYYY-MM-DD):", "FRED: Dump Series as Static Table")
    If Trim(startDate) = "" Then Exit Sub

    endDate = InputBox("End date (YYYY-MM-DD), leave blank for most recent:", "FRED: Dump Series as Static Table")

    apiKey = Environ("FRED_API_KEY")
    If Trim(apiKey) = "" Then
        apiKey = InputBox("FRED API key (leave blank to use the FRED_API_KEY environment variable):", "FRED: Dump Series as Static Table")
    End If

    If Trim(endDate) = "" Then
        vEndDate = Null
    Else
        vEndDate = endDate
    End If
    If Trim(apiKey) = "" Then
        vApiKey = Null
    Else
        vApiKey = apiKey
    End If

    oDoc = ThisComponent
    oSel = oDoc.CurrentController.Selection
    nCol = oSel.RangeAddress.StartColumn
    nRow = oSel.RangeAddress.StartRow

    On Error GoTo FredFailed
    nRows = FredWriteSeries(seriesId, startDate, vEndDate, vApiKey, nCol, nRow)
    On Error GoTo 0

    MsgBox "Wrote " & nRows & " rows of """ & UCase(seriesId) & """ starting at " _
        & oDoc.CurrentController.ActiveSheet.getCellByPosition(nCol, nRow).AbsoluteName & "."
    Exit Sub

FredFailed:
    MsgBox "Could not fetch """ & seriesId & """:" & Chr(10) & FredCleanError(Error$)
End Sub

' The UNO bridge reports Python exceptions as a verbose block (exception
' type, message, then a full Python traceback); this pulls out just the
' message line for a MsgBox instead of dumping the whole traceback.
Function FredCleanError(sRaw As String) As String
    Dim nStart As Long, nEnd As Long
    Dim sMsg As String

    nStart = InStr(sRaw, "Message:")
    If nStart = 0 Then
        FredCleanError = sRaw
        Exit Function
    End If
    sMsg = Mid(sRaw, nStart + Len("Message:"))

    nEnd = InStr(sMsg, ", traceback follows")
    If nEnd > 0 Then sMsg = Left(sMsg, nEnd - 1)

    FredCleanError = Trim(sMsg)
End Function

' Fetches seriesId's observations between startDate/endDate (Variant, may
' be Null) using apiKey (Variant, may be Null - falls back to
' FRED_API_KEY), and writes them as static values (date, value) starting
' at column nCol / row nRow (0-based) on the active sheet. Returns the
' number of rows written. No dialogs - kept separate from FredDumpSeries
' so it can be driven directly (e.g. from a test, or another macro).
Function FredWriteSeries(seriesId As String, startDate As String, endDate As Variant, apiKey As Variant, nCol As Integer, nRow As Integer) As Long
    Dim oFred As Object, oDoc As Object, oSheet As Object
    Dim oFormats As Object, oLocale As New com.sun.star.lang.Locale
    Dim nDateFormat As Long
    Dim data() As Variant
    Dim i As Integer

    oFred = createUnoService("com.example.fred.FredImpl")
    data = oFred.series(seriesId, startDate, endDate, apiKey)

    oDoc = ThisComponent
    oSheet = oDoc.CurrentController.ActiveSheet

    oFormats = oDoc.getNumberFormats()
    nDateFormat = oFormats.queryKey("YYYY-MM-DD", oLocale, False)
    If nDateFormat = -1 Then
        nDateFormat = oFormats.addNew("YYYY-MM-DD", oLocale)
    End If

    Dim oDateCell As Object, oValueCell As Object
    For i = LBound(data) To UBound(data)
        oDateCell = oSheet.getCellByPosition(nCol, nRow + i)
        oDateCell.setValue(data(i)(0))
        oDateCell.NumberFormat = nDateFormat
        oValueCell = oSheet.getCellByPosition(nCol + 1, nRow + i)
        oValueCell.setValue(data(i)(1))
    Next i

    FredWriteSeries = UBound(data) - LBound(data) + 1
End Function
