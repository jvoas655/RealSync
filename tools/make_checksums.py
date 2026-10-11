"""Hash tracked release files; excludes the checksum file itself."""
import hashlib
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
names = (
    subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"])
    .decode()
    .split("\0")
)
lines = []
for name in sorted(filter(None, names)):
    if name == "SHA256SUMS":
        continue
    lines.append(f"{hashlib.sha256((root/name).read_bytes()).hexdigest()}  {name}")
(root / "SHA256SUMS").write_text("\n".join(lines) + "\n")
print(f"Checksums for {len(lines)} tracked files")
