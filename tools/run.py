"""bin/sumidashi から呼ばれる。tools/ を import パスに足して CLI を起動する。"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

try:
    from sumidashi.cli import main
except ImportError as exc:  # 依存が入っていない python3 で直接動かした場合
    sys.stderr.write(
        f"sumidashi: 依存パッケージが見つかりません（{exc.name}）。\n"
        "uv を入れるか、pip install -r tools/requirements.txt を実行してください。\n"
    )
    sys.exit(2)

sys.exit(main())
