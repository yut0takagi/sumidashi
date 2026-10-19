# 開発に参加する

sumidashi に Issue や PR を出すときの手順。開発用のコマンドと CI の中身は [実装の設計](docs/architecture.md) の「開発」に、評価のケースの書き方は [evals/README.md](evals/README.md) にある。

参加する人は [行動規範](CODE_OF_CONDUCT.md) に従う。脆弱性は Issue に書かず、[SECURITY.md](SECURITY.md) の手順で非公開で報告する。

## Issue を出す

いちばん助かるのは、誤検知と見逃しの報告だ。Issue のテンプレート「判定の誤り」に、次の3つを書いてもらえれば再現できる。

- チェックID
- 指摘が出た（または出なかった）コードの最小の例
- 期待した結果と、実際の結果（`bin/sumidashi review --format json` の該当する指摘）

このリポジトリは公開している。業務のコードは貼らず、同じ形を保った別のコードに書き換えてから載せる。

解析器が落ちる、コマンドが動かないといった不具合は「動作の不具合」のテンプレートを使う。

## 開発の準備

[uv](https://docs.astral.sh/uv/) を入れておけば、ほかの依存は初回の実行で自動で入る。

```bash
R="uv run --no-project --with-requirements tools/requirements.txt"
$R --with pytest --with jsonschema --with rdflib --with pyshacl python -m pytest tests
```

PR を出す前に、CI と同じ4つ（生成物の確認・SHACL 検証・出荷ゲート・pytest）を手元で通す。コマンドは docs/architecture.md の「開発」にある。

## static チェックを直す・足す

判定規則を先に決め、実装と評価のケースをそれに合わせる。

1. [docs/static-checks.md](docs/static-checks.md) に判定規則を書く。何を違反・グレー・非違反とするかと、指摘の行をどこにするかを決める
2. `skills/<思想>/checks.yml` のチェックの `detection.implementation` に名前を書き、`tools/sumidashi/checks/` に同じ名前で `@register` した関数を置く
3. evals/README.md に従って violation・borderline・not_violation のケースを足し、checks.yml の `fixtures` 欄に並べる。3種類がそろったら `status` を `ready` にする
4. 評価を `--write` 付きで実行して `evals/results/latest.json` を書き直し、`build_knowledge.py` で `generated/` と `docs/check-catalog.md` を作り直す
5. 規則を決めるときに迷った点は、[docs/decisions.md](docs/decisions.md) の「判定規則の細部」に書く

holdout のケース（`h1-*`）は、規則を調整している間は中身を見ない。dev のケースで直し、holdout で確かめる。

## PR を出す

- main は保護している。CI（Python 3.10 と 3.13）が通った PR だけがマージできる
- 1つの PR では1つの変更を扱う。チェックの追加と、別のチェックの修正は分ける
- 判定が変わる変更では、`evals/results/latest.json` の差分も PR に含める。評価の数字が下がるなら、理由を PR の説明に書く

## ライセンス

PR で送られた変更は、このリポジトリと同じ [Apache License 2.0](LICENSE) で配布する。
