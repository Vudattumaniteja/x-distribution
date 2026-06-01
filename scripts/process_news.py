"""Deprecated prototype entrypoint.

The historical implementation embedded fabricated example stories and wrote
them into protected queue state. Keep this file as an explicit compatibility
guard so old commands fail safely instead of silently replacing live data.
"""

from __future__ import annotations


def main() -> int:
    print(
        "process_news.py is deprecated and intentionally disabled: its historical "
        "prototype data is not a live source. Use scripts/x_distribution.py collect "
        "followed by scripts/x_distribution.py normalize."
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
