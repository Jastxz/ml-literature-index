#!/usr/bin/env python3
"""Validate the local ML literature index without network access."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit

MAX_PACK_BYTES = 50 * 1024 * 1024
MAX_RECORD_LINE_BYTES = 2 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 250 * 1024 * 1024
REDISTRIBUTABLE_ABSTRACT_LICENSES = {"CC0-1.0", "CC-BY-4.0"}
ALLOWED_RECORD_KEYS = {
    "work_key",
    "identifiers",
    "title",
    "authors",
    "authors_complete",
    "publication_year",
    "topics",
    "paper_url",
    "source_records",
    "evidence_available",
    "abstract",
    "open_access_full_text",
    "related_identifiers",
    "links",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def is_https_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and parsed.username is None
        and parsed.password is None
        and not any(char.isspace() for char in parsed.netloc)
    )


def validate_record(record: Any, source_ids: set[str], topic_ids: set[str]) -> None:
    require(isinstance(record, dict), "record must be a JSON object")
    extra = set(record) - ALLOWED_RECORD_KEYS
    require(not extra, "unexpected field(s): " + ", ".join(sorted(extra)))

    for field in ("work_key", "title", "paper_url"):
        require(isinstance(record.get(field), str) and record[field].strip(), field + " must be a non-empty string")
    require(is_https_url(record["paper_url"]), "paper_url must use HTTPS")

    identifiers = record.get("identifiers")
    require(isinstance(identifiers, dict) and identifiers, "identifiers must be a non-empty object")
    require(set(identifiers) <= {"doi", "arxiv_id", "openalex_id"}, "unexpected identifier field")
    for value in identifiers.values():
        require(isinstance(value, str) and value.strip(), "identifier values must be non-empty strings")
    doi = identifiers.get("doi")
    arxiv_id = identifiers.get("arxiv_id")
    openalex_id = identifiers.get("openalex_id")
    require(
        (isinstance(doi, str) and doi.strip())
        or (isinstance(arxiv_id, str) and arxiv_id.strip())
        or (isinstance(openalex_id, str) and re.fullmatch(r"W[0-9]+", openalex_id)),
        "record needs a DOI, arXiv ID, or OpenAlex work ID",
    )
    if doi:
        expected_key = "doi:" + doi.lower()
    elif arxiv_id:
        expected_key = "arxiv:" + arxiv_id.lower()
    else:
        expected_key = "openalex:" + openalex_id.lower()
    require(record["work_key"].lower() == expected_key, "work_key must use the preferred available identifier")

    require(isinstance(record.get("authors"), list) and record["authors"], "authors must be a non-empty list")
    require(all(isinstance(name, str) and name.strip() for name in record["authors"]), "author names must be non-empty strings")
    require(isinstance(record.get("authors_complete"), bool), "authors_complete must be boolean")
    year = record.get("publication_year")
    require(isinstance(year, int) and 1600 <= year <= 2100, "publication_year must be between 1600 and 2100")

    topics = record.get("topics")
    require(isinstance(topics, list) and topics, "topics must be a non-empty list")
    require(len(topics) == len(set(topics)), "topics must not contain duplicates")
    require(set(topics) <= topic_ids, "record contains an unknown topic ID")

    evidence = record.get("evidence_available")
    require(isinstance(evidence, list) and "metadata" in evidence, "evidence_available must include metadata")
    require(len(evidence) == len(set(evidence)), "evidence_available must not contain duplicates")
    require(set(evidence) <= {"metadata", "abstract", "full_text_at_source"}, "unknown evidence_available value")

    source_records = record.get("source_records")
    require(isinstance(source_records, list) and source_records, "source_records must be a non-empty list")
    record_source_ids: set[str] = set()
    for source_record in source_records:
        require(isinstance(source_record, dict), "source record must be a JSON object")
        require(set(source_record) <= {"source_id", "source_record_id", "url", "retrieved_at"}, "unexpected source-record field")
        source_id = source_record.get("source_id")
        require(source_id in source_ids, "source record uses an unknown source ID")
        record_source_ids.add(source_id)
        require(isinstance(source_record.get("source_record_id"), str) and source_record["source_record_id"].strip(), "source_record_id must be non-empty")
        require(is_https_url(source_record.get("url")), "source record URL must use HTTPS")
        require(isinstance(source_record.get("retrieved_at"), str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", source_record["retrieved_at"]), "retrieved_at must use YYYY-MM-DD")

    abstract = record.get("abstract")
    require(("abstract" in evidence) == (abstract is not None), "abstract evidence and abstract field must agree")
    if abstract is not None:
        require(isinstance(abstract, dict), "abstract must be an object")
        require(set(abstract) <= {"text", "source_id", "license_id", "license_url", "source_url"}, "unexpected abstract field")
        require(isinstance(abstract.get("text"), str) and abstract["text"].strip(), "abstract text must be non-empty")
        require(abstract.get("source_id") in record_source_ids, "abstract source must be present in source_records")
        require(abstract.get("license_id") in REDISTRIBUTABLE_ABSTRACT_LICENSES, "abstract license does not allow redistribution")
        require(is_https_url(abstract.get("license_url")), "abstract license URL must use HTTPS")
        require(is_https_url(abstract.get("source_url")), "abstract source URL must use HTTPS")
        require("abstract" in evidence, "abstract evidence must be declared")

    full_text = record.get("open_access_full_text")
    require(("full_text_at_source" in evidence) == (full_text is not None), "full-text evidence and link must agree")
    if full_text is not None:
        require(isinstance(full_text, dict), "open_access_full_text must be an object containing a link only")
        require(set(full_text) <= {"url", "license_id", "license_url"}, "unexpected full-text field")
        require(is_https_url(full_text.get("url")), "full text link must use HTTPS")
        require(isinstance(full_text.get("license_id"), str) and full_text["license_id"], "full-text license ID is required")
        require(is_https_url(full_text.get("license_url")), "full-text license URL must use HTTPS")
    related = record.get("related_identifiers", [])
    require(isinstance(related, list), "related_identifiers must be a list")
    for item in related:
        require(isinstance(item, dict), "related identifier must be an object")
        require(set(item) <= {"relation", "doi"}, "unexpected related-identifier field")
        require(isinstance(item.get("relation"), str) and item["relation"].strip(), "related identifier relation must be non-empty")
        require(isinstance(item.get("doi"), str) and item["doi"].strip(), "related identifier DOI must be non-empty")

    links = record.get("links", [])
    require(isinstance(links, list), "links must be a list")
    for item in links:
        require(isinstance(item, dict), "link must be an object")
        require(set(item) <= {"kind", "url", "source_id"}, "unexpected link field")
        require(item.get("kind") in {"code", "benchmark", "dataset"}, "link kind is unsupported")
        require(is_https_url(item.get("url")), "link URL must use HTTPS")
        require(item.get("source_id") in source_ids, "link uses an unknown source ID")


def validate_pack_bytes(
    raw: bytes,
    entry: dict[str, Any],
    source_ids: set[str],
    topic_ids: set[str],
    max_pack_bytes: int = MAX_PACK_BYTES,
) -> int:
    require(isinstance(entry, dict), "pack entry must be an object")
    required = {"id", "topic_id", "year_from", "year_to", "source_set", "record_schema_version", "generated_at", "record_count", "size_bytes", "sha256", "path", "url"}
    require(required <= set(entry), "pack entry is missing required fields")
    require(entry["topic_id"] in topic_ids, "pack uses an unknown topic ID")
    year_from, year_to = entry["year_from"], entry["year_to"]
    require(isinstance(year_from, int) and isinstance(year_to, int) and year_from <= year_to, "pack year range is invalid")
    require(isinstance(entry["source_set"], list) and entry["source_set"], "source_set must be a non-empty list")
    require(len(entry["source_set"]) == len(set(entry["source_set"])), "source_set must not contain duplicates")
    require(set(entry["source_set"]) <= source_ids, "pack uses an unknown source ID")
    require(entry["record_schema_version"] == 1, "unsupported record schema version")
    require(isinstance(entry["generated_at"], str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", entry["generated_at"]), "generated_at must be an ISO UTC timestamp")
    require(isinstance(entry["record_count"], int) and entry["record_count"] >= 0, "record_count must be a non-negative integer")
    require(isinstance(entry["size_bytes"], int) and 0 < entry["size_bytes"] <= max_pack_bytes <= MAX_PACK_BYTES, "pack exceeds the 50 MiB size cap")
    require(len(raw) == entry["size_bytes"], "compressed byte count does not match")
    require(hashlib.sha256(raw).hexdigest() == entry["sha256"], "SHA-256 digest does not match")
    require(is_https_url(entry["url"]), "pack download URL must use HTTPS")

    # ponytail: A bounded, standard-library pass is enough for packs under 50 MiB; split larger exports instead of adding a database or service.
    seen: set[str] = set()
    count = 0
    decompressed_bytes = 0
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(raw), mode="rb") as stream:
            line_number = 0
            while True:
                raw_line = stream.readline(MAX_RECORD_LINE_BYTES + 1)
                if not raw_line:
                    break
                line_number += 1
                decompressed_bytes += len(raw_line)
                require(len(raw_line) <= MAX_RECORD_LINE_BYTES, "JSONL record exceeds the 2 MiB line limit")
                require(decompressed_bytes <= MAX_UNCOMPRESSED_BYTES, "decompressed pack exceeds the 250 MiB limit")
                line = raw_line.decode("utf-8")
                require(bool(line.strip()), "blank JSONL line at " + str(line_number))
                record = json.loads(line)
                validate_record(record, source_ids, topic_ids)
                require(entry["topic_id"] in record["topics"], "record topic does not match pack topic")
                require(year_from <= record["publication_year"] <= year_to, "record year is outside pack range")
                require(set(item["source_id"] for item in record["source_records"]) <= set(entry["source_set"]), "record source is absent from pack source_set")
                key = record["work_key"].lower()
                require(key not in seen, "duplicate work_key: " + key)
                seen.add(key)
                count += 1
    except (OSError, EOFError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("invalid gzip JSONL pack: " + str(error)) from error

    require(count == entry["record_count"], "record_count does not match pack contents")
    return count


def load_ids(path: Path, collection_key: str) -> set[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get(collection_key)
    require(isinstance(items, list), str(path) + " must contain a " + collection_key + " list")
    ids = {item.get("id") for item in items if isinstance(item, dict)}
    require(None not in ids and len(ids) == len(items), str(path) + " contains an item without a unique ID")
    return ids


def safe_pack_path(pack_dir: Path, value: Any) -> Path:
    require(isinstance(value, str) and value.endswith(".jsonl.gz"), "pack path must end in .jsonl.gz")
    relative = PurePosixPath(value)
    require(not relative.is_absolute() and ".." not in relative.parts, "pack path must stay within the packs directory")
    base = pack_dir.resolve()
    candidate = (base / Path(*relative.parts)).resolve()
    require(candidate == base or base in candidate.parents, "pack path escapes the packs directory")
    return candidate


def validate_manifest(manifest_path: Path, packs_dir: Path, sources_path: Path, topics_path: Path) -> tuple[int, int]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(manifest.get("schema_version") == 1 and manifest.get("record_schema_version") == 1, "unsupported manifest or record schema version")
    require(isinstance(manifest.get("coverage"), dict) and manifest["coverage"].get("not_exhaustive") is True, "manifest must state that coverage is not exhaustive")
    max_pack_bytes = manifest.get("max_pack_size_bytes")
    require(isinstance(max_pack_bytes, int) and 0 < max_pack_bytes <= MAX_PACK_BYTES, "max_pack_size_bytes must be at most 50 MiB")
    source_ids = load_ids(sources_path, "providers")
    topic_ids = load_ids(topics_path, "topics")
    packs = manifest.get("packs")
    require(isinstance(packs, list), "manifest must contain a packs list")

    seen_pack_ids: set[str] = set()
    total_records = 0
    for entry in packs:
        require(isinstance(entry, dict), "pack entry must be an object")
        pack_id = entry.get("id")
        require(isinstance(pack_id, str) and pack_id and pack_id not in seen_pack_ids, "pack IDs must be non-empty and unique")
        seen_pack_ids.add(pack_id)
        raw = safe_pack_path(packs_dir, entry.get("path")).read_bytes()
        total_records += validate_pack_bytes(raw, entry, source_ids, topic_ids, max_pack_bytes)
    return len(packs), total_records


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the local ML literature index without network access.")
    parser.add_argument("--manifest", type=Path, default=Path("index/manifest.json"))
    parser.add_argument("--packs-dir", type=Path, default=Path("index/packs"))
    parser.add_argument("--sources", type=Path, default=Path("catalog/sources.json"))
    parser.add_argument("--topics", type=Path, default=Path("catalog/topics.json"))
    args = parser.parse_args()
    try:
        pack_count, record_count = validate_manifest(args.manifest, args.packs_dir, args.sources, args.topics)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 1
    print("Validated " + str(pack_count) + " packs and " + str(record_count) + " records.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
