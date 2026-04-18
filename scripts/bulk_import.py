#!/usr/bin/env python3
"""
Run: python scripts/bulk_import.py --docs-list docs/historical_doc_urls.txt
Each line in the file should be a Google Doc URL.
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src/backend"))

from google.cloud import firestore
from importer import import_document


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs-list", required=True)
    parser.add_argument("--field", default="General")
    args = parser.parse_args()

    db = firestore.Client()

    with open(args.docs_list) as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    print(f"Importing {len(urls)} documents...")
    for i, url in enumerate(urls, 1):
        try:
            result = import_document(url, db, field=args.field)
            print(f"[{i}/{len(urls)}] ✓ {result['doc_id']} ({result['lor_type']})")
        except Exception as e:
            print(f"[{i}/{len(urls)}] ✗ FAILED: {url} — {e}")

    print("Done.")


if __name__ == "__main__":
    main()
