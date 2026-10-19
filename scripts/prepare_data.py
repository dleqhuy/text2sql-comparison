"""Freeze ordered Spider dev IDs and export inputs for the original methods."""

import argparse
import hashlib
import shutil
from pathlib import Path
from common import ROOT, read_json, sql_line, write_json


def prepare(source, output, count=20, ids_path=None):
    source, output = Path(source).resolve(), Path(output)
    dev_path, tables_path = source / "dev.json", source / "tables.json"
    dev, tables = read_json(dev_path), read_json(tables_path)
    ids_path = Path(ids_path) if ids_path else output / "subset.json"
    # An existing selection is reused, never silently sampled again.
    ids = (
        read_json(ids_path)
        if ids_path.exists()
        else [f"dev_{i:04d}" for i in range(min(count, len(dev)))]
    )
    if not isinstance(ids, list) or not ids or len(set(ids)) != len(ids):
        raise ValueError("Subset IDs must be a nonempty unique array")
    rows, original = [], []
    schemas = {t["db_id"] for t in tables}
    for eid in ids:
        if not isinstance(eid, str) or not eid.startswith("dev_"):
            raise ValueError(f"Invalid example ID: {eid!r}")
        index = int(eid[4:])
        if index < 0 or index >= len(dev) or eid != f"dev_{index:04d}":
            raise ValueError(f"Out-of-range or noncanonical ID: {eid}")
        item = dev[index]
        db = item["db_id"]
        if db not in schemas:
            raise ValueError(f"Missing schema for {db}")
        database = source / "database" / db / f"{db}.sqlite"
        if not database.is_file():
            raise FileNotFoundError(f"Missing Spider database: {database}")
        rows.append(dict(item, example_id=eid))
        # MAC-SQL uses question_id as its local position for resume and output idx.
        original.append(dict(item, question_id=len(original)))
    if (output / "source.json").exists():
        previous = read_json(output / "source.json")
        for key, path in (("dev_sha256", dev_path), ("tables_sha256", tables_path)):
            if previous[key] != hashlib.sha256(path.read_bytes()).hexdigest():
                raise ValueError(
                    "Dataset changed; use a separate output directory for a new experiment"
                )
        for db, expected in previous.get("databases_sha256", {}).items():
            database = source / "database" / db / f"{db}.sqlite"
            if (
                not database.is_file()
                or hashlib.sha256(database.read_bytes()).hexdigest() != expected
            ):
                raise ValueError(f"Spider database changed: {db}")
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "subset.json", ids)
    write_json(output / "examples.json", rows)
    write_json(output / "dev.json", original)
    shutil.copyfile(tables_path, output / "tables.json")
    (output / "gold.txt").write_text(
        "".join(sql_line(r["query"]) + "\t" + r["db_id"] + "\n" for r in rows),
        encoding="utf-8",
    )
    write_json(
        output / "source.json",
        {
            "source": str(source),
            "split": "dev",
            "count": len(rows),
            "dev_sha256": hashlib.sha256(dev_path.read_bytes()).hexdigest(),
            "tables_sha256": hashlib.sha256(tables_path.read_bytes()).hexdigest(),
            "databases_sha256": {
                db: hashlib.sha256(
                    (source / "database" / db / f"{db}.sqlite").read_bytes()
                ).hexdigest()
                for db in sorted({r["db_id"] for r in rows})
            },
        },
    )
    return len(rows)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--spider-data", type=Path, required=True)
    p.add_argument("--count", type=int, default=20)
    p.add_argument("--ids", type=Path, help="Existing JSON array of dev_0000-style IDs")
    p.add_argument("--output", type=Path, default=ROOT / "data")
    a = p.parse_args()
    if a.count < 1:
        p.error("--count must be positive")
    print(f"Prepared {prepare(a.spider_data, a.output, a.count, a.ids)} examples")
