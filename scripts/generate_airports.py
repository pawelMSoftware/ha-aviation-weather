from __future__ import annotations

from pathlib import Path

from scripts.generators.airport_generator import AirportGenerator


def main() -> None:
    """Generate airport files."""

    AirportGenerator(
        Path(__file__).resolve().parent.parent,
    ).generate()


if __name__ == "__main__":
    main()
