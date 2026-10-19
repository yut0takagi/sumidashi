import pathlib
import sys
import textwrap

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "dev"))


@pytest.fixture
def make_repo(tmp_path):
    """{パス: 中身} から小さなリポジトリを作る。中身は textwrap.dedent してから書く。"""

    def make(files: dict[str, str]) -> pathlib.Path:
        for rel, text in files.items():
            p = tmp_path / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(textwrap.dedent(text).lstrip("\n"), encoding="utf-8")
        return tmp_path

    return make
