# sumidashi

クリーンアーキテクチャと DDD 戦術設計を、1つのチェック項目カタログに束ねた Claude Code プラグイン。新機能の設計相談と、PR・差分のレビューの両方で使う。

- 指摘には必ずチェックID・重大度・ファイルと行・原則と出典が付く。一般論だけの指摘は出さない
- 依存関係や型の構造のように事実で決まるものは静的解析で確定し、解釈が要る判定だけを LLM に任せる
- プロジェクトの規模と複雑さを先に判定し、小さいコードや CRUD 中心のコードには DDD を当てない
- チームが ADR で記録した判断は、一般論の設計思想より優先する

## 必要なもの

- Claude Code
- [uv](https://docs.astral.sh/uv/)（推奨）。解析器の依存（tree-sitter など）を初回に自動で取得する
- uv がなければ python3 と、`tools/requirements.txt` の依存を自分で入れる

対応言語は TypeScript と Python。

## インストール

```text
/plugin marketplace add <このリポジトリの URL かローカルのパス>
/plugin install sumidashi@sumidashi
```

導入したら、対象のリポジトリで1回だけ次を実行する。層マップ・用語集・業務ルール台帳の下書きをコードから作り、確認のうえで書き込む。

```text
/sumidashi:setup
```

## コマンド

| コマンド | 用途 |
| --- | --- |
| `/sumidashi:review [パス...]` | 差分（既定は main との差分）かパスをレビューする。総評・指摘一覧・要確認・採点を出す |
| `/sumidashi:check <思想名> [パス...]` | 1つの思想だけで見る |
| `/sumidashi:plan <やりたいこと>` | 設計相談。層・境界・主要な型の案を2つまで出す |
| `/sumidashi:explain <チェックID>` | チェックの原則・理由・違反例・修正例を解説する |
| `/sumidashi:setup` | 設定ファイル・用語集・業務ルール台帳の下書きを作る |
| `/sumidashi:adr-review <パス>` | ADR の書き方と中身をレビューする |
| `/sumidashi:adr-draft` | 保留になった指摘や繰り返される例外から ADR の下書きを作る |
| `/sumidashi:glossary-draft` | コードから用語集の下書きを作る |
| `/sumidashi:rules-draft` | コードの条件分岐から業務ルール台帳の下書きを作る |

コマンドを打たなくても、「設計を見て」「このリファクタの方針は」のような依頼で design-router スキルが読み込まれ、同じ手順で進む。

ファイルを書き換えるのは、利用者が承認したときだけ。レビューの中間ファイルは一時ディレクトリに置き、コードや結果を外部に送らない。

## 収録している思想

| 思想 | チェックIDの接頭辞 | 中身 |
| --- | --- | --- |
| clean-architecture | CA- | 依存性ルール、境界の越え方、ユースケースの責務（12個） |
| ddd-tactical | DDD- | 集約・エンティティ・値オブジェクト・リポジトリ・ドメインイベント（15個） |
| adr | ADR- | ADR による例外、コードと ADR の整合、ADR 自体のレビュー |
| glossary | GLO- | ドメイン用語集とコードの照合 |
| model-commonality | MDL- | 共通化の見落としと誤った共通化 |
| business | BIZ- | 業務ルール台帳・受け入れ条件とコードの整合 |
| logic-placement | PLC-・SCL- | ロジックの置き場所と、水平スケールを妨げる構造 |

チェックの一覧は `bin/sumidashi catalog`、1つの解説は `/sumidashi:explain <ID>` で見られる。

## v0.1 の状態

v0.1 は評価の仕組みを固める段階。既定で有効なのは、評価の出荷ゲート（チェックごとに適合率 0.85 以上・再現率 0.85 以上）を通った static のチェックだけ。

| ID | 名前 |
| --- | --- |
| CA-DEP-01 | ドメイン層が外側の層に依存している |
| CA-DEP-02 | ドメイン層がフレームワーク・ORM・I/O ライブラリに依存している |
| CA-DEP-03 | アプリケーション層がアダプタ層・インフラ層に依存している |
| CA-DEP-04 | 層をまたぐ循環依存がある |
| CA-BND-02 | ユースケースの入出力に HTTP・Web フレームワークの型を使っている |
| DDD-ENT-03 | エンティティの状態を外から直接書き換えられる |
| DDD-VO-02 | 値オブジェクトが可変になっている |
| DDD-REP-02 | リポジトリのインターフェースが永続化の技術を表に出している |
| DDD-EVT-01 | ドメインイベントの名前が過去形になっていない |

hybrid・llm のチェック（集約の不変条件、貧血ドメインモデルなど）は定義済みだが、評価用の fixtures が揃うまで draft として既定で無効にしている。精度の保証はないが、設定で `experimental: true` にすれば試せる。

ADR による例外（Accepted の ADR の `scope` と `exempts`）は v0.1 から効く。

## 設定

`.claude/sumidashi.yml` に置く。すべて省略でき、省略した項目は規模判定と層マップの自動推定で決まる。全項目は [schemas/config.schema.json](schemas/config.schema.json)。

```yaml
version: 1
strictness: standard          # lenient（Low・Info を出さない）| standard | strict（要確認も指摘一覧に出す）
philosophies:
  clean-architecture: auto    # auto | on | off
  ddd-tactical: auto
layers:                       # 自動推定が外れるときだけ書く
  src/core/**: domain
  src/services/**: application
  src/routes/**: adapter
  src/db/**: infrastructure
disabled_checks: [DDD-EVT-01]
experimental: false           # true で draft のチェックも走らせる
adr:
  path: docs/adr
onboarding_until: 2026-11-02  # この日までは適合率 0.9 以上のチェックだけを使う
hooks:
  pre_pr_check: true          # gh pr create の前に High だけを簡易実行して警告する
```

## ADR で例外にする

ADR のフロントマターに、対象の範囲と外れてよいチェックを書く。Status が Accepted の ADR だけが効く。

```yaml
---
status: accepted
date: 2026-09-12
scope: [src/reporting/**]
exempts: [CA-BND-01, DDD-ENT-02]
---
# 0007. 集計系は ORM モデルを境界越えで直接使う
```

範囲内の該当する指摘は Info に下がり、ADR 番号が添えられる。正しさに関わる DDD-AGG-01・DDD-AGG-02・DDD-VO-01 は、例外にしても Low に留まり毎回表示される。

## 評価

チェックごとに、違反・グレー・非違反のサンプル（fixtures）と期待する指摘を持ち、適合率と再現率を測る。

```bash
uv run --no-project --with-requirements tools/requirements.txt python tools/dev/run_evals.py -v
```

`--write` を付けると結果を `evals/results/latest.json` に書く。実行時は、このファイルで出荷ゲートを通ったチェックだけを有効にする。1ケースは `evals/fixtures/<チェックIDの小文字>/<ケース>/` の小さなリポジトリで、期待する指摘は `evals/expected/` に置く。

v0.1 の9チェックは、評価ですべて適合率・再現率 1.00 だった。ただし fixtures と解析器は同じ判定規則（[static チェックの判定規則](docs/static-checks.md)）から作ったので、この数字は規則どおりに実装できていることを示すだけで、実際のリポジトリでの精度は示さない。

設計知識の検証（SHACL）やテストの実行方法は、[実装の設計](docs/architecture.md) の「開発」にまとめた。

## CI で使う

static のチェックだけなら、Claude Code を通さずに解析器を直接呼べる。`--fail-on` に重大度を渡すと、それ以上の指摘があるとき終了コード 1 で終わる。

```bash
bin/sumidashi review --base origin/main --fail-on High
```

`--format json` で report.json と同じ形を標準出力に出す。形は [schemas/report.schema.json](schemas/report.schema.json)。

差分を取るにはマージベースまでの履歴が要る。GitHub Actions の `actions/checkout` は既定で最新の1コミットしか取らないので、`fetch-depth: 0` を付ける。`--base` に渡した比較先が見つからないときは、全体に広げずに終了コード 2 で止まる。

## ディレクトリ構成

```text
.claude-plugin/     plugin.json・marketplace.json
skills/             思想ごとのスキル（SKILL.md・checks.yml・references/）と design-router
agents/             principle-reviewer（1思想を担当するサブエージェント）
commands/           /sumidashi:* のコマンド
hooks/              PR 作成前の簡易チェック
schemas/            checks.yml・指摘・設定・facts・report の JSON Schema
ontology/           設計知識の語彙と SHACL の形状
generated/          ビルドの生成物（実行時に読む索引）
tools/              解析器（tools/sumidashi）と開発用スクリプト（tools/dev）
bin/sumidashi       解析器の入口
evals/              fixtures・期待する指摘・評価結果
docs/               要件定義・実装の設計・判断の記録
```

## 詳しい資料

- [要件定義](docs/設計思想プラグイン%20要件定義.md)
- [実装の設計](docs/architecture.md): CLI の契約、層マップ、適用判定、finalize の処理順
- [static チェックの判定規則](docs/static-checks.md)
- [実装で決めたこと](docs/decisions.md): 要件定義の未決事項の扱いと、要件にない判断
- [チェック一覧](docs/check-catalog.md): checks.yml から生成した一覧と評価の状態
