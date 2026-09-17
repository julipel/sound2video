param([string]$Frames = 'work\ocr-frames', [string]$Output = 'work\ocr-frames.jsonl')
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime]
$null = [Windows.Storage.Streams.IRandomAccessStream, Windows.Storage.Streams, ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrResult, Windows.Foundation, ContentType=WindowsRuntime]
$null = [Windows.Globalization.Language, Windows.Globalization, ContentType=WindowsRuntime]
$asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
function Await-Result($Operation, [Type]$ResultType) {
    $task = $asTask.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    $task.Wait()
    return $task.Result
}
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new('ru'))
$writer = [System.IO.StreamWriter]::new((Join-Path (Get-Location) $Output), $false, [System.Text.UTF8Encoding]::new($false))
try {
    $files = Get-ChildItem -LiteralPath $Frames -Filter '*.png' | Sort-Object Name
    $i = 0
    foreach ($file in $files) {
        $storage = Await-Result ([Windows.Storage.StorageFile]::GetFileFromPathAsync($file.FullName)) ([Windows.Storage.StorageFile])
        $stream = Await-Result ($storage.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
        $decoder = Await-Result ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $bitmap = Await-Result ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
        $result = Await-Result ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
        $lines = @($result.Lines | ForEach-Object { @{text=$_.Text; top=($_.Words | ForEach-Object { $_.BoundingRect.Y } | Measure-Object -Minimum).Minimum; bottom=($_.Words | ForEach-Object { $_.BoundingRect.Y + $_.BoundingRect.Height } | Measure-Object -Maximum).Maximum} })
        $writer.WriteLine((@{frame=$file.BaseName; lines=$lines} | ConvertTo-Json -Compress))
        $writer.Flush()
        $bitmap.Dispose()
        $stream.Dispose()
        $i++
        if ($i % 100 -eq 0) { Write-Output "OCR $i / $($files.Count)" }
    }
} finally { $writer.Dispose() }
