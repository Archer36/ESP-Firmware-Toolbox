#!/usr/bin/env python3
"""Download and convert official ESP32-S3 ROM linker labels for Ghidra.

The generated file uses the ``name address l`` format consumed by the
external ImportSymbolsScript referenced by this toolbox's original README.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_IDF_REF = "v5.5.4"
DEFAULT_OUTPUT = "Ghidra-Files/ESP32S3_ROM_LABELS.txt"
LINKER_SCRIPT_PATH = "components/esp_rom/esp32s3/ld/esp32s3.rom.ld"
RAW_URL_TEMPLATE = "https://raw.githubusercontent.com/espressif/esp-idf/{ref}/{path}"

# Covers both `name = 0x...;` and `PROVIDE( name = 0x... );` entries.
SYMBOL_ASSIGNMENT = re.compile(
    r"^\s*(?:PROVIDE\s*\(\s*)?"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*"
    r"(?P<address>0x[0-9A-Fa-f]+)\s*\)?\s*;"
)


def parse_rom_symbols(linker_script: str) -> list[tuple[str, int]]:
    """Return named linker assignments in source order, omitting duplicates."""
    symbols: list[tuple[str, int]] = []
    seen_names: set[str] = set()

    for line in linker_script.splitlines():
        match = SYMBOL_ASSIGNMENT.match(line)
        if not match:
            continue

        name = match.group("name")
        if name in seen_names:
            continue
        seen_names.add(name)
        symbols.append((name, int(match.group("address"), 16)))

    return symbols


def download_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "ESP-Firmware-Toolbox-ROM-label-downloader"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def write_symbol_map(output: Path, symbols: list[tuple[str, int]]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(f"{name} 0x{address:08x} l\n" for name, address in symbols),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download ESP32-S3 ROM labels from Espressif's ESP-IDF and convert them for Ghidra."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(DEFAULT_OUTPUT),
        help=f"destination label file (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--idf-ref",
        default=DEFAULT_IDF_REF,
        help=f"ESP-IDF tag, branch, or commit to download (default: {DEFAULT_IDF_REF})",
    )
    parser.add_argument(
        "--url",
        help="override the source linker-script URL (useful for a local mirror)",
    )
    args = parser.parse_args()

    source_url = args.url or RAW_URL_TEMPLATE.format(ref=args.idf_ref, path=LINKER_SCRIPT_PATH)
    try:
        linker_script = download_text(source_url)
    except (HTTPError, URLError, TimeoutError) as error:
        print(f"Unable to download {source_url}: {error}", file=sys.stderr)
        return 1

    symbols = parse_rom_symbols(linker_script)
    if not symbols:
        print(f"No ROM labels found in {source_url}; refusing to write {args.output}", file=sys.stderr)
        return 1

    write_symbol_map(args.output, symbols)
    print(f"Wrote {len(symbols)} ESP32-S3 ROM labels to {args.output}")
    print(f"Source: {source_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
