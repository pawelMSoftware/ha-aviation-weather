"""Generate the European FIR database from traffic.data.eurofirs.

This script is the ONLY place in the project that imports from the
`traffic` library.  The library depends on geopandas and shapely, which
are heavyweight dependencies that have no place in a Home Assistant
integration.  Running this script is a one-time (or occasional)
developer action; the generated CSV is committed to the repository and
read at runtime without any dependency on `traffic`.

Usage:
    python -m scripts.generate_firs

Output:
    scripts/data/firs.csv

The CSV is intentionally minimal — only the fields needed by the
integration at runtime are included.  Geometry (polygon coordinates)
is deliberately omitted: the integration uses FIR data only for naming
devices and filtering SIGMET API responses by `firId`, not for
point-in-polygon calculations.
"""

from __future__ import annotations

import csv
import warnings

from scripts.config import FIR_FILE

# Suppress noisy deprecation warnings from traffic's heavy dependencies
# (geopandas, shapely, pandas) — they're irrelevant to what we're doing here.
warnings.filterwarnings("ignore")


def _load_eurofirs() -> list[dict[str, str]]:
    """Load European FIR data from traffic.data.eurofirs.

    Returns a list of dicts with keys: icao, name, type.
    Rows are sorted by ICAO designator for deterministic output.

    Raises:
        ImportError: if the `traffic` library is not installed.
            Install it with: pip install traffic
    """
    try:
        from traffic.data import eurofirs  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "The `traffic` library is required to generate the FIR database.\n"
            "Install it with: pip install traffic\n"
            "Note: traffic is a generator-only dependency — it must never be "
            "added to the integration's runtime dependencies.",
        ) from exc

    data = eurofirs.data

    rows: list[dict[str, str]] = []
    for _, row in data.iterrows():
        designator = str(row.get("designator", "")).strip()
        name = str(row.get("name", "")).strip()
        fir_type = str(row.get("type", "")).strip()

        if not designator:
            continue

        rows.append(
            {
                "icao": designator,
                "name": name,
                "type": fir_type,
            },
        )

    return sorted(rows, key=lambda r: r["icao"])


def generate() -> None:
    """Generate scripts/data/firs.csv from traffic.data.eurofirs."""
    print("Loading European FIR data from traffic.data.eurofirs...")  # noqa: T201

    rows = _load_eurofirs()

    FIR_FILE.parent.mkdir(parents=True, exist_ok=True)

    with FIR_FILE.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["icao", "name", "type"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated {FIR_FILE} — {len(rows)} FIRs.")  # noqa: T201

    _print_summary(rows)


def _print_summary(rows: list[dict[str, str]]) -> None:
    """Print a brief summary of generated FIRs."""
    types: dict[str, int] = {}
    for row in rows:
        fir_type = row["type"] or "unknown"
        types[fir_type] = types.get(fir_type, 0) + 1

    print()  # noqa: T201
    print("Summary")  # noqa: T201
    print("-------")  # noqa: T201
    for fir_type, count in sorted(types.items()):
        print(f"  {fir_type}: {count}")  # noqa: T201
    print(f"  Total:   {len(rows)}")  # noqa: T201
    print()  # noqa: T201
    print("Sample (first 5 rows):")  # noqa: T201
    for row in rows[:5]:
        print(f"  {row['icao']:<6}  {row['name']:<30}  {row['type']}")  # noqa: T201


def main() -> None:
    """Entry point for python -m scripts.generate_firs."""
    generate()


if __name__ == "__main__":
    main()
