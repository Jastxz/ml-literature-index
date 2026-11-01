# Tasks: ML Literature Index

## Approved baseline

- [x] Add official source catalog and documented reuse boundaries.
- [x] Add stable topic IDs, aliases, and initial provider-neutral taxonomy.
- [x] Define a versioned paper record schema and topic/year pack manifest.
- [x] Provide downloadable bootstrap packs spanning 1959, 2017, and 2025.
- [x] Validate required identifiers, provenance, topic/year membership, hashes, size caps, duplicate keys, and abstract licenses offline.
- [x] Add self-check tests with in-memory fixtures and no external API calls.
- [x] Document clone-first, agent-first use and coverage limits.

## Follow-up to complete the broader index workflow

- [ ] Decide an inclusion policy for reviews, conference versions, preprints, corrections, and withdrawn works.
- [ ] Add a repeatable pack builder for OpenAlex and arXiv that honors rate limits and uses only caller-provided credentials.
- [ ] Define a normalized cross-provider deduplication and version-linking process.
- [ ] Add broader coverage reports by topic and year; distinguish zero records from unavailable source data.
- [ ] Publish expanded packs as optional GitHub Release assets and refresh the manifest monthly.
- [ ] Revisit source terms before adding providers or redistributing new metadata fields.

## Done criteria for the broader workflow

- An agent can find useful records across the declared topic/year coverage from a fresh clone or one selected pack download.
- New packs can be generated deterministically, checked offline, and published without adding paper bodies or credentials to Git.
- Monthly updates are attributable, versioned, and discoverable in the manifest.
- The README reports actual coverage and still makes no completeness claim.
