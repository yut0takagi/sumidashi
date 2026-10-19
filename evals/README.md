# 評価用のケース

static チェックの判定が docs/static-checks.md の規則どおりかを測るためのケース集。1ケースは、数ファイルからなる小さなリポジトリ1つと、そこから出るべき指摘の一覧の組み合わせ。

## 置き場所

```text
evals/
  fixtures/<チェックIDの小文字>/<ケース名>/   … ケースのリポジトリ一式
  expected/<チェックIDの小文字>/<ケース名>.json … 期待する指摘
  fixtures/_applicability/<ケース名>/          … 思想の適用判定のケース
  expected/_applicability/<ケース名>.json
  results/                                     … 評価の結果（latest.json など）
```

ケース名は、期待のラベルと言語で決める。

| ケース名 | ラベル | split |
| --- | --- | --- |
| `v1-ts`・`v2-py` … | violation | dev |
| `b1-ts`・`b1-py` … | borderline | dev |
| `n1-ts`・`n2-py` … | not_violation | dev |
| `h1-ts`・`h1-py` | violation | holdout |

各チェックの `checks.yml` の `fixtures` 欄に、ここにあるケース名を並べる。holdout のケースも violation の欄に入れる。

ケースのルートが解析対象のリポジトリのルートになる。`src/` の下に層のディレクトリを置き、TypeScript の別名を使うケースはルートに `tsconfig.json` を置く。ケースだけ設定を変えたいときは、ケースの中に `.claude/sumidashi.yml` を置く。

## 期待値の形式

```json
{
  "case": "ca-dep-01/v1-ts",
  "check": "CA-DEP-01",
  "label": "violation",
  "split": "dev",
  "description": "何を確かめるケースか",
  "findings": [
    {
      "id": "CA-DEP-01",
      "verdict": "violation",
      "file": "src/domain/order.ts",
      "start_line": 4,
      "end_line": 4
    }
  ]
}
```

- `file` はケースのルートからの相対パス。行は1始まり
- `start_line`・`end_line` は docs/static-checks.md の location の決め方に従う。import 文なら文の最初と最後の行、「名前の行」と書かれたものは識別子のある行だけ
- `verdict` は violation か borderline。省略せずに書く
- not_violation のケースは `findings` を空の配列にする

適用判定のケースは形が違う。

```json
{
  "case": "_applicability/crud-01-ts",
  "kind": "applicability",
  "description": "…",
  "expect": {
    "ddd-tactical": { "applied": false, "max_findings": 0 },
    "clean-architecture": { "mode": "dep-only", "severity_shift": -1 }
  }
}
```

- `applied: false` と `max_findings: 0` は、その思想の指摘が1件も出ないこと
- `mode: "dep-only"` は、CA-DEP 系のチェックだけが走ること
- `severity_shift` は重大度を何段動かすか。層マップが推定できないときは -1、推定できるときは 0

## 突き合わせの規則

docs/architecture.md の「評価」の節と同じ規則で数える。

- 採点するのは、ケースの `check` と同じチェックIDの指摘だけ。同じケースから別のチェックの指摘が出ても数えない
- チェックIDとファイルが同じで、行範囲が重なれば一致とみなす。期待1件に一致させられる指摘は1件まで
- violation のケース: 期待どおりの violation は TP、期待にない violation は FP、出なかった期待は FN
- borderline のケース: 適合率と再現率には数えず、borderline として出せたかを borderline 一致率で数える
- not_violation のケース: 出た violation はすべて FP
- 出荷ゲートは適合率・再現率とも 0.85 以上。holdout のケースがあれば holdout だけで判定する

holdout のケースは、解析器の規則を直すときに中身を見ない。dev のケースで調整し、holdout で確かめる。

## ケースを足すとき

1. `fixtures/<チェックIDの小文字>/<ケース名>/` に2〜6ファイルの小さなリポジトリを作る。業務のコードとして不自然にならないように書き、violation のケースには、似ているが指摘されない箇所（おとり）も混ぜる
2. `expected/<チェックIDの小文字>/<ケース名>.json` を書く。行番号は `grep -n` で確かめる
3. `checks.yml` の該当チェックの `fixtures` 欄にケース名を足す
4. 同じ ID の指摘が他のファイルから出ないか、ケース全体を見直す

テストらしいファイル名（`test_*.py`・`*.spec.ts`・`tests/` 配下など）は解析の対象外になる。除外を確かめるケース以外では使わない。Python のケースでは、パッケージとして解決できるように `__init__.py` を置く。
