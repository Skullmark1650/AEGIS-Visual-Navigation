$ErrorActionPreference = 'Stop'
Write-Host 'AEGIS API key setup'
Write-Host 'Create a key at https://platform.openai.com/api-keys first.'
Write-Host 'Paste it below. Input is hidden; do not paste it into chat.'
$aegisSecureKey = Read-Host 'OpenAI API key' -AsSecureString
$aegisPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($aegisSecureKey)
try {
    $aegisApiValue = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($aegisPointer).Trim()
    if (-not $aegisApiValue.StartsWith('sk-') -or $aegisApiValue.Length -lt 20) {
        throw 'The value does not look like an OpenAI API key. Nothing was saved.'
    }
    [Environment]::SetEnvironmentVariable('OPENAI_API_KEY', $aegisApiValue, 'User')
    Write-Host 'AEGIS API key saved as a Windows user environment variable.'
    Write-Host 'The key was not written to the project or displayed.'
    Write-Host 'Return to the chat and say: The key is saved.'
} finally {
    $aegisApiValue = $null
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($aegisPointer)
    $aegisSecureKey.Dispose()
}
Read-Host 'Press Enter to close'
