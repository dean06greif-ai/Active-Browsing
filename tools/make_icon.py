import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from awaketoggle.icons import save_ico  # noqa: E402

out = Path(sys.argv[1] if len(sys.argv) > 1 else "build/awaketoggle.ico")
out.parent.mkdir(parents=True, exist_ok=True)
save_ico(out)
print(f"Symbol geschrieben: {out}")
