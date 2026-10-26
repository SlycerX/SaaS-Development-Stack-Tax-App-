Waivers live in this directory as YAML files. CI rejects a waiver on or after its `expires_on` date.

```yaml
id: WVR-2026-001
finding_id: SNYK-OR-ZAP-ID
severity: high
expires_on: 2026-12-31
reason: Why the finding stays open until this date.
approved_by: operator
```

An agent does not add or edit a waiver. That is a deviation, and you approve it first.
