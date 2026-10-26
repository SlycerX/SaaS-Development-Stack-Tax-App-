param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Domain,
    [string]$Region = "ap-southeast-2"
)

if ($Name -notmatch '^[a-z][a-z0-9-]{1,20}$') {
    throw "Name must start with a letter and use only lowercase letters, numbers, and hyphens."
}

$root = Split-Path -Parent $PSScriptRoot
$productPath = Join-Path $root "product.yaml"
$envExample = Join-Path $root ".env.example"
$envFile = Join-Path $root ".env"

$product = Get-Content -LiteralPath $productPath
$product = $product -replace '^name:.*', "name: $Name"
$product = $product -replace '^domain:.*', "domain: $Domain"
$product = $product -replace '^region:.*', "region: $Region"
Set-Content -LiteralPath $productPath -Value $product

$envText = @"
PRODUCT_NAME=$Name
NEXT_PUBLIC_PRODUCT_NAME=$Name
DATABASE_URL=postgresql://saas:saas@postgres:5432/saas
API_URL=http://api:8000
WEB_URL=http://127.0.0.1:3000
"@
Set-Content -LiteralPath $envExample -Value $envText.TrimEnd()
Set-Content -LiteralPath $envFile -Value $envText.TrimEnd()

Write-Output "Updated product.yaml, .env.example, and .env for $Name."
