# Racing.com Ingestion V2

Racing.com Ingestion V2 is the governed standard-time ingestion chain for EDGEiQ performance intelligence.

Current status: `RACINGCOM_INGESTION_V2_E2E_PASS`.
Migration decision: `DO_NOT_MIGRATE_YET`.

The V2 chain is evidence-first. It starts at meeting discovery, admits only race identities with observed evidence, acquires only explicit/proven CSV sources, parses those CSV files in isolation, and produces a versioned warehouse with provenance.

Production files are not overwritten by this chain.
