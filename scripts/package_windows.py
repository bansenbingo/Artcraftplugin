#!/usr/bin/env python3
"""Build the Windows edition without touching the original macOS archive."""
import hashlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT / "windows"
    dest = ROOT / "dist/artcraft-windows-plugin.zip"
    dest.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            rel = path.relative_to(source)
            if not path.is_file() or "__pycache__" in rel.parts or path.suffix == ".pyc":
                continue
            if rel.parts[0] == "test-results" and path.name != "windows-validation.json":
                continue
            info = zipfile.ZipInfo(rel.as_posix(), date_time=(2026, 10, 11, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    dest.with_suffix(dest.suffix + ".sha256").write_text(f"{digest}  {dest.name}\n", encoding="ascii")
    print(f"{dest.name} SHA256 {digest}")


if __name__ == "__main__":
    main()
