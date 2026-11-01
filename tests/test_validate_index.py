import gzip
import hashlib
import json
import unittest
from pathlib import Path

from scripts.validate_index import safe_pack_path, validate_pack_bytes, validate_record

SOURCE_IDS = {"arxiv"}
TOPIC_IDS = {"nlp"}


def record():
    return {
        "work_key": "arxiv:0001.00001",
        "identifiers": {"arxiv_id": "0001.00001"},
        "title": "A test paper",
        "authors": ["Example Author"],
        "authors_complete": True,
        "publication_year": 2020,
        "topics": ["nlp"],
        "paper_url": "https://arxiv.org/abs/0001.00001",
        "source_records": [{
            "source_id": "arxiv",
            "source_record_id": "0001.00001",
            "url": "https://arxiv.org/abs/0001.00001",
            "retrieved_at": "2026-01-01",
        }],
        "evidence_available": ["metadata"],
    }


def pack_entry(raw, **changes):
    entry = {
        "id": "nlp-2020",
        "topic_id": "nlp",
        "year_from": 2020,
        "year_to": 2020,
        "source_set": ["arxiv"],
        "record_schema_version": 1,
        "generated_at": "2026-01-01T00:00:00Z",
        "record_count": 1,
        "size_bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "path": "nlp-2020.jsonl.gz",
        "url": "https://example.org/nlp-2020.jsonl.gz",
    }
    entry.update(changes)
    return entry


class ValidateIndexTests(unittest.TestCase):
    def test_accepts_metadata_only_record(self):
        validate_record(record(), SOURCE_IDS, TOPIC_IDS)

    def test_accepts_abstract_with_explicit_cc0_provenance(self):
        item = record()
        item["abstract"] = {
            "text": "Short abstract.",
            "source_id": "arxiv",
            "license_id": "CC0-1.0",
            "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
            "source_url": "https://info.arxiv.org/help/api/tou.html",
        }
        item["evidence_available"].append("abstract")
        validate_record(item, SOURCE_IDS, TOPIC_IDS)

    def test_rejects_abstract_without_redistribution_license(self):
        item = record()
        item["abstract"] = {
            "text": "Short abstract.",
            "source_id": "arxiv",
            "license_id": "publisher-specific-oa",
            "license_url": "https://example.org/license",
            "source_url": "https://arxiv.org/abs/0001.00001",
        }
        item["evidence_available"].append("abstract")
        with self.assertRaisesRegex(ValueError, "does not allow redistribution"):
            validate_record(item, SOURCE_IDS, TOPIC_IDS)

    def test_rejects_inconsistent_abstract_evidence(self):
        item = record()
        item["evidence_available"].append("abstract")
        with self.assertRaisesRegex(ValueError, "must agree"):
            validate_record(item, SOURCE_IDS, TOPIC_IDS)

    def test_rejects_https_urls_with_embedded_credentials(self):
        item = record()
        item["paper_url"] = "https://user:secret@arxiv.org/abs/0001.00001"
        with self.assertRaisesRegex(ValueError, "paper_url must use HTTPS"):
            validate_record(item, SOURCE_IDS, TOPIC_IDS)

    def test_rejects_unknown_nested_identifier_fields(self):
        item = record()
        item["identifiers"]["pdf_url"] = "https://example.org/paper.pdf"
        with self.assertRaisesRegex(ValueError, "unexpected identifier"):
            validate_record(item, SOURCE_IDS, TOPIC_IDS)

    def test_rejects_unknown_topic(self):
        item = record()
        item["topics"] = ["unknown-topic"]
        with self.assertRaisesRegex(ValueError, "unknown topic"):
            validate_record(item, SOURCE_IDS, TOPIC_IDS)

    def test_rejects_article_body_or_other_unknown_fields(self):
        item = record()
        item["full_text_body"] = "This field must never be stored."
        with self.assertRaisesRegex(ValueError, "unexpected field"):
            validate_record(item, SOURCE_IDS, TOPIC_IDS)

    def test_accepts_a_hashed_gzip_jsonl_pack(self):
        raw = gzip.compress((json.dumps(record()) + "\n").encode("utf-8"), mtime=0)
        self.assertEqual(1, validate_pack_bytes(raw, pack_entry(raw), SOURCE_IDS, TOPIC_IDS))

    def test_rejects_a_bad_pack_digest(self):
        raw = gzip.compress((json.dumps(record()) + "\n").encode("utf-8"), mtime=0)
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            validate_pack_bytes(raw, pack_entry(raw, sha256="0" * 64), SOURCE_IDS, TOPIC_IDS)

    def test_rejects_a_pack_over_its_configured_cap(self):
        raw = gzip.compress((json.dumps(record()) + "\\n").encode("utf-8"), mtime=0)
        with self.assertRaisesRegex(ValueError, "size cap"):
            validate_pack_bytes(raw, pack_entry(raw), SOURCE_IDS, TOPIC_IDS, max_pack_bytes=len(raw) - 1)

    def test_rejects_pack_path_traversal(self):
        with self.assertRaisesRegex(ValueError, "stay within"):
            safe_pack_path(Path("/virtual/index/packs"), "../outside.jsonl.gz")

    def test_rejects_oversized_jsonl_record_line(self):
        item = record()
        item["title"] = "x" * (2 * 1024 * 1024 + 1)
        raw = gzip.compress((json.dumps(item) + "\\n").encode("utf-8"), mtime=0)
        with self.assertRaisesRegex(ValueError, "2 MiB line limit"):
            validate_pack_bytes(raw, pack_entry(raw), SOURCE_IDS, TOPIC_IDS)

    def test_rejects_duplicate_work_keys(self):
        raw = gzip.compress(((json.dumps(record()) + "\n") * 2).encode("utf-8"), mtime=0)
        entry = pack_entry(raw, record_count=2)
        with self.assertRaisesRegex(ValueError, "duplicate work_key"):
            validate_pack_bytes(raw, entry, SOURCE_IDS, TOPIC_IDS)


if __name__ == "__main__":
    unittest.main()
