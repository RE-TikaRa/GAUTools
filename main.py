# pyright: reportMissingImports=false
from pathlib import Path
import sys

src_path = Path(__file__).resolve().parent / "src"
src_path_str = str(src_path)
if src_path_str not in sys.path:
    sys.path.insert(0, src_path_str)

import src.cli


if __name__ == "__main__":
    src.cli.main()
