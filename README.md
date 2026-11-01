# ML Literature Index

A small, agent-first index for finding machine-learning papers and reaching their original records. Clone it, let your agent read AGENTS.md, and load only the metadata pack needed for the current topic and year.

## Use

1. Clone this repository.
2. Have the agent read AGENTS.md and SPEC.md.
3. Select a topic/year pack in index/manifest.json.
4. Download only that pack, verify its SHA-256, and inspect its JSONL records.
5. Follow the DOI or provider record to verify the paper. Use the abstract or full text at the source only as its terms allow.
6. Cite the DOI, arXiv ID, or provider record and label whether the evidence came from metadata, an abstract, or full text read at the source.

Validate a clone with:

    python3 scripts/validate_index.py --manifest index/manifest.json --packs-dir index/packs
    python3 -m unittest discover -s tests -v

## What it contains

- Agent instructions and source access/rights notes.
- A stable topic taxonomy with aliases.
- A versioned record schema and manifest.
- Three tiny gzip JSONL bootstrap packs spanning 1959, 2017, and 2025.
- A Python standard-library validator.

The packs contain bibliographic metadata and arXiv abstracts whose descriptive metadata terms permit redistribution. They contain no PDF files or article full text. The sample only proves the data format and citation path; it does not indicate coverage.

## Network and provider use

A clone works offline for its local packs and validation. Finding newer or unindexed papers needs network access through the consuming agent.

OpenAlex supports basic queries without a key; a provider key raises quotas and is needed for cursor paging beyond the first page. arXiv provides a metadata API and permits descriptive metadata reuse under CC0. Its legacy API limit is one request every three seconds, with one connection at a time. Do not place credentials in this repository.

See catalog/sources.json for official provider docs and terms. See SPEC.md for scope, refresh plans, data contract, and coverage limits.

## Project status

Alpha bootstrap. The records are a hand-checked sample, not a comprehensive corpus and not an automated monthly update pipeline. Wider coverage and repeatable pack refresh are planned follow-up work.

## Boundary

This repository is an index, not a paper archive or a chatbot. It has no model runtime, backend, web app, or MCP server. Read papers at their original sources and honor their individual licenses.
