# SaaS delivery stack

A starter for one product. Agents draft the change. GitHub Actions walks every environment. The rules are in [docs/guardrails.md](docs/guardrails.md). The shape of the system is in [docs/architecture.md](docs/architecture.md).

## Local

```powershell
Copy-Item .env.example .env
docker compose up --build
```

API: http://127.0.0.1:8000/health

Web: http://127.0.0.1:3000

Playwright, from `tests/playwright` after the API and web are up:

```powershell
npm install
npx playwright install chromium
$env:API_URL = "http://127.0.0.1:8000"
$env:WEB_URL = "http://127.0.0.1:3000"
npm run test:lite
```

`npm run test:full` runs the whole suite. Use that for a major release.

## Checks

```powershell
pip install -r scripts/requirements.txt
python scripts/ci_check.py change-pack
python scripts/ci_check.py requirements
python scripts/ci_check.py waivers
python scripts/ci_check.py protected-paths
python scripts/ci_check.py workflows
python scripts/ci_check.py release-class
```

## AWS

Terraform is ready to validate. Applying it creates resources and is a separate step. Follow [docs/runbooks/environments.md](docs/runbooks/environments.md) and [.github/RULESETS.md](.github/RULESETS.md).

## Rename

```powershell
.\scripts\new-product.ps1 -Name "acme" -Domain "acme.example"
```
