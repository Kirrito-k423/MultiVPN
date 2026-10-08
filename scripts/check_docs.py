"""Check local Markdown links and catch local-only material before publishing."""

from pathlib import Path
import re
import subprocess


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    files = [root / "README.md", root / "CONTRIBUTING.md", *root.glob("docs/**/*.md")]
    for path in files:
        text = path.read_text(encoding="utf-8")
        if text.count("```") % 2:
            raise SystemExit(f"Unbalanced code fences: {path.relative_to(root)}")
        if "/Users/" in text or re.search(r"[A-Za-z]:\\Users\\", text):
            raise SystemExit(f"Personal absolute path in public document: {path.relative_to(root)}")
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if target.startswith(("https://", "http://", "#")):
                continue
            destination = (path.parent / target.split("#", 1)[0]).resolve()
            if not destination.is_relative_to(root) or not destination.exists():
                raise SystemExit(f"Invalid local link: {path.relative_to(root)} -> {target}")

    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
    forbidden_suffixes = {
        ".pem", ".key", ".p12", ".pfx", ".pcap", ".pcapng", ".ipsw",
        ".vhd", ".vhdx", ".qcow2", ".vmdk", ".img", ".iso", ".pkg",
        ".dmg", ".msi", ".exe", ".run",
    }
    for name in filter(None, tracked):
        p = Path(name)
        if p.suffix.lower() in forbidden_suffixes or p.parts[0] in {
            "local", "private", "profiles", "logs", "artifacts",
        } or p.name == ".env" or p.name.startswith(".env."):
            raise SystemExit(f"Local-only material is tracked: {name}")
    print(f"Checked {len(files)} Markdown files and {len(list(filter(None, tracked)))} tracked paths.")
    print("This scope check is not a complete secret scanner or a VPN compatibility test.")


if __name__ == "__main__":
    main()
