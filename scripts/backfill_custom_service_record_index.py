from __future__ import annotations

import argparse

from monitoring.services.custom_service_index import backfill_record_index
from monitoring.storage.mariadb_manager import MariaDBFileManager


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill custom service record search index.")
    parser.add_argument("--batch-size", type=int, default=100, help="Maximum records to index per batch.")
    args = parser.parse_args()

    manager = MariaDBFileManager()
    indexed_count = backfill_record_index(manager=manager, batch_size=args.batch_size)
    print(f"Indexed {indexed_count} custom service record(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
