Option Explicit

Dim inputPath, outputPath, extension, app, document
If WScript.Arguments.Count <> 3 Then
  WScript.Echo "Argumen konversi tidak lengkap."
  WScript.Quit 2
End If

inputPath = WScript.Arguments(0)
outputPath = WScript.Arguments(1)
extension = LCase(WScript.Arguments(2))

On Error Resume Next

If extension = ".docx" Then
  Set app = CreateObject("Word.Application")
  If Err.Number = 0 Then
    app.Visible = False
    app.DisplayAlerts = 0
    Set document = app.Documents.Open(inputPath, False, True, False)
    If Err.Number = 0 Then document.SaveAs2 outputPath, 17
    If Not document Is Nothing Then document.Close False
    app.Quit False
  End If
ElseIf extension = ".pptx" Then
  Set app = CreateObject("PowerPoint.Application")
  If Err.Number = 0 Then
    Set document = app.Presentations.Open(inputPath, True, True, False)
    If Err.Number = 0 Then document.SaveAs outputPath, 32
    If Not document Is Nothing Then document.Close
    app.Quit
  End If
ElseIf extension = ".xlsx" Then
  Set app = CreateObject("Excel.Application")
  If Err.Number = 0 Then
    app.Visible = False
    app.DisplayAlerts = False
    Set document = app.Workbooks.Open(inputPath, 0, True)
    If Err.Number = 0 Then document.ExportAsFixedFormat 0, outputPath
    If Not document Is Nothing Then document.Close False
    app.Quit
  End If
Else
  WScript.Echo "Format Office tidak didukung."
  WScript.Quit 2
End If

If Err.Number <> 0 Then
  WScript.Echo "Konversi gagal: " & Err.Description
  WScript.Quit 1
End If

WScript.Quit 0
