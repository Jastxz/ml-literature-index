# Implementation plan: ML Literature Index

## Overview

Turn the approved specification into a cloneable index that an agent can use without an MCP server or application runtime.

## Decisions

- Keep provider metadata and article-content rights separate.
- Use OpenAlex and arXiv for the initial source map; link to publisher records through DOI.
- Keep the public contract in JSON Schema and validate it with Python's standard library.
- Track only tiny bootstrap packs in Git. Move expanded packs to optional GitHub Release assets.
- Keep live provider queries in the consuming agent; this repository does not make requests or hold credentials.

## Slices

### Slice 1: contract and sample packs

- [x] Publish provider and topic catalogs.
- [x] Publish a stable record schema and manifest.
- [x] Add historical, transformer-era, and recent reasoning examples with provenance.
- [x] State the no-PDF, no-full-text, no-embedding boundary.

### Slice 2: local validation

- [x] Add an offline validator for schema-critical fields, provider/topic IDs, hashes, counts, duplicates, years, and size.
- [x] Add standard-library self-checks for valid, malformed, duplicate, and forbidden-content cases.
- [x] Document the exact commands for an agent to validate a clone.

### Slice 3: broaden coverage and refresh

- [ ] Define inclusion and deduplication policy for broad source queries.
- [ ] Build a repeatable pack-generation path that respects provider rate limits and credentials.
- [ ] Expand topic/year coverage without making the default clone large.
- [ ] Publish expanded packs as optional Release assets and refresh the manifest monthly.
- [ ] Recheck source terms and validation after every source or data-contract change.

## Verification checkpoints

- [x] The bootstrap packs decompress to valid records, span a historical paper and recent research, and lead to original sources.
- [x] The validator and test suite pass without network access or third-party dependencies.
- [x] The README does not imply complete coverage.
- [ ] The refresh path can create a pack, validate it, and make it discoverable through the manifest.

## Risks

| Risk | Mitigation |
| --- | --- |
| Metadata providers have uneven historical and subject coverage | Show sample status and report coverage by provider/topic/year |
| Abstract rights differ from article rights | Record metadata source/license and never copy article bodies |
| Source API behavior or limits change | Link official docs and recheck before publishing a refresh |
| A normal clone grows as packs accumulate | Keep bootstrap packs tiny and host larger packs as optional Releases |

## Completion boundary

The bootstrap index is an initial usable slice. The remaining release and refresh work is tracked in tasks/todo.md; do not claim full literature coverage.
