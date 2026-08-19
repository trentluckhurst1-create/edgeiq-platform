# Provenance

Every warehouse record must retain:

- source CSV URL
- repository-local source cache path
- source SHA256
- acquisition timestamp
- parser version
- pipeline/admission/discovery versions

Records without provenance fail the E2E gate.
