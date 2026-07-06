from __future__ import annotations

from scripts.updaters.airport_updater import AirportUpdater


def main() -> None:
    """Update airport data."""

    AirportUpdater().update()


if __name__ == "__main__":
    main()
