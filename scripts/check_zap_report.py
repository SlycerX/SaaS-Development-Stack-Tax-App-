"""Fail the pen-test job when ZAP reports a high or critical alert."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "zap-report.json")
    if not path.exists():
        print(f"ZAP report not found: {path}", file=sys.stderr)
        raise SystemExit(1)
    report = json.loads(path.read_text(encoding="utf-8"))
    alerts = report.get("site") or report.get("alerts") or []
    if isinstance(alerts, dict):
        alerts = alerts.get("alerts", [])
    blocking = []
    for site in alerts if isinstance(alerts, list) else []:
        site_alerts = site.get("alerts", [site]) if isinstance(site, dict) else []
        for alert in site_alerts:
            risk = str(alert.get("riskcode", alert.get("risk", "")))
            if risk in {"3", "4", "High", "Critical"}:
                blocking.append(alert.get("name") or alert.get("alert") or "unnamed")
    if blocking:
        print("High or critical ZAP findings:", file=sys.stderr)
        for name in blocking:
            print(f"- {name}", file=sys.stderr)
        raise SystemExit(1)
    print("ZAP report has no high or critical findings")


if __name__ == "__main__":
    main()
