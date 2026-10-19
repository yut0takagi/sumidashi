# sumidashi 実装の設計

要件定義（`docs/設計思想プラグイン 要件定義.md`）を実装に落とすときの約束事をまとめる。
要件定義に書かれていない判断は `docs/decisions.md` に記録する。

## 全体の流れ

```text
/sumidashi:review
  └─ sumidashi collect      静的解析。層マップ・規模・適用判定・static の指摘・hybrid の候補を facts.json に出す
  └─ principle-reviewer ×N  思想ごとに並列。hybrid の候補と llm の判定質問だけを見て、指摘を JSON で返す
  └─ sumidashi finalize     全指摘をまとめ、ADR 例外・重大度の調整・重複統合・衝突裁定・厳しさの適用をかけて report を出す
```

static だけで済む場面（CI、PR 作成前の hook）では `sumidashi review` が collect と finalize を続けて実行する。

LLM が新しい指摘を作れるのは detection.type が llm のチェックだけ。hybrid のチェックでは、facts.json の候補にない箇所を指摘してはいけない（要件定義「判定の仕組み」）。

## ディレクトリ

| パス | 中身 |
| --- | --- |
| `.claude-plugin/` | plugin.json と marketplace.json |
| `skills/<思想>/` | SKILL.md（200行以内）、checks.yml、references/ |
| `skills/design-router/` | 規模判定・思想選択・衝突裁定。conflicts.yml に衝突の裁定を持つ |
| `agents/principle-reviewer.md` | 1思想を担当するレビュー用サブエージェント |
| `commands/` | `/sumidashi:*` のスラッシュコマンド |
| `hooks/pre-pr-check.json` | `gh pr create` の前に High だけを簡易実行して警告する（ブロックしない） |
| `schemas/` | checks.yml・指摘・設定・facts・report の JSON Schema |
| `ontology/` | 設計知識の語彙（vocabulary.ttl）と SHACL の形状（shapes.ttl） |
| `generated/` | ビルドの生成物。index.json（実行時に読む索引）と knowledge.ttl。コミットする |
| `tools/sumidashi/` | 解析器の Python パッケージ |
| `tools/dev/` | 開発用のスクリプト（ビルド、検証、評価） |
| `bin/sumidashi` | 解析器の入口。uv があれば `uv run` で依存を解決し、なければ python3 で動かす |
| `evals/fixtures/<check-id小文字>/<ケース>/` | 1ケース=1ディレクトリの小さなリポジトリ |
| `evals/expected/<check-id小文字>/<ケース>.json` | そのケースで期待する指摘 |
| `evals/results/latest.json` | 最新の評価結果。出荷ゲートの判定に使う |

## 解析器の CLI

入口は `${CLAUDE_PLUGIN_ROOT}/bin/sumidashi`。どのサブコマンドも `--root`（既定はカレントディレクトリ）で対象リポジトリを指す。

| サブコマンド | 用途 |
| --- | --- |
| `collect [PATH...] [--base REF] [--all] [--philosophy ID] [--checks ID,...] --out DIR` | 静的解析を実行し、`DIR/facts.json` を書く |
| `finalize --facts FILE [--llm FILE...] --out DIR` | facts の static の指摘と LLM の指摘をまとめ、`DIR/report.json` と `DIR/report.md` を書く |
| `review [PATH...] [--base REF] [--all] [--min-severity S] [--out DIR] [--format md\|json]` | collect と finalize を続けて実行する。`--out` がなければ Markdown を標準出力に出す |
| `layers [--write-config FILE]` | 層マップと規模の推定を表示する。`--write-config` で設定ファイルの下書きを書く |
| `explain ID` | チェックの定義、原則、出典、fixtures、このリポジトリで例外にしている ADR を表示する |
| `catalog [--philosophy ID] [--format md\|json]` | チェックの一覧と、評価の出荷ゲートの状態を表示する |
| `adr` | ADR の読み込み結果（Status・scope・exempts・形式）を表示する |
| `export depcruise\|importlinter` | 層マップから dependency-cruiser・import-linter の設定を生成する |
| `hook pre-pr` | hook 用。標準入力の hook の JSON を読み、`gh pr create` のときだけ High のチェックを実行して警告を返す |

対象は次のように決める。

- `PATH` を渡せば、そのパス配下のファイルが対象
- `PATH` がなく `--all` もなければ、`--base`（既定は main。なければ master）とのマージベースからの差分が対象。コミットしていない変更と、git が追跡していない新しいファイルも含む
- 既定の比較先が見つからないとき（git がない、main・master がない）は全体を対象にし、そのことを notes に残す。`--base` で明示した比較先とのマージベースが取れないときは、全体に広げずに終了コード 2 で止める
- 差分モードでは、依存グラフは全ファイルから作り、指摘は変更されたファイルの変更行に掛かるものだけを出す

## 層マップ

層は `domain` `application` `adapter` `infrastructure` `main` `shared` の6つ。`ignore` は解析の対象外。

依存してよい向きは次の表のとおり。行の層から列の層への import を表す。

| 依存元 \ 依存先 | domain | application | adapter | infrastructure | main | shared |
| --- | --- | --- | --- | --- | --- | --- |
| domain | ○ | × | × | × | × | ○ |
| application | ○ | ○ | × | × | × | ○ |
| adapter | ○ | ○ | ○ | ○ | × | ○ |
| infrastructure | ○ | ○ | ○ | ○ | × | ○ |
| main | ○ | ○ | ○ | ○ | ○ | ○ |
| shared | × | × | × | × | × | ○ |

層は次の手順で推定する。

1. 設定の `layers`（glob → 層）に当たれば、それに従う。複数の glob に当たったら、最初のワイルドカードより前の部分が最も長い glob を採る
2. パスのディレクトリ名を強いキーワードに照らし、当たったものの中で最も外側（ルートに近い）のものを採る
3. 当たらなければ、ファイル名が `main.ts`・`main.py` なら main
4. それでも決まらなければ、弱いキーワードの中で最も外側のものを採る
5. どれにも当たらなければ層なし（unmapped）

| 層 | 強いキーワード | 弱いキーワード |
| --- | --- | --- |
| domain | domain、domains、domain-model、domain_model | なし |
| application | application、usecase、usecases、use-case、use-cases、use_case、use_cases、interactor、interactors | なし |
| adapter | adapters、adapter、presentation | controllers、controller、handlers、handler、routes、routers、api、web、http、rest、graphql、resolvers、views、cli、presenters、interfaces、ui |
| infrastructure | infrastructure、infra、persistence | db、database、gateways、external、clients、orm、storage |
| main | composition-root、composition_root、bootstrap、di、container | なし |
| shared | shared、shared-kernel、shared_kernel、sharedkernel | common |

`src/api/domain/order.ts` は、弱いキーワードの api より強いキーワードの domain が勝つので domain になる。`entities` や `models` だけのディレクトリは、層を決められないので unmapped のまま残す。

`domain` があり、かつ domain・application・adapter・infrastructure のうち2つ以上が見つかれば、層マップは「推定できる」とする。

## 適用判定

要件定義の表をそのまま実装する。CRUD 中心かどうかの静的な目安は、ドメイン層の行数がテスト以外の全体の 10% 未満であること。ルーター（LLM）はこの目安を上書きしてよく、上書きした理由を総評に書く。

| 条件 | clean-architecture | ddd-tactical |
| --- | --- | --- |
| 層マップが推定できない | CA-DEP 系のみ、重大度を1段下げる | 適用しない |
| CRUD 中心 | CA-DEP 系のみ | 適用しない |
| 集約らしき型（ルートと、ルートが所有する子のエンティティ）が推定できない | 通常どおり | ENT・VO 系のみ |
| 設定の philosophies で on・off を明示 | 設定に従う | 設定に従う |

## チェックの有効・無効

1. status が draft のチェックは、設定の `experimental: true` のときだけ走る
2. status が ready のチェックは、`evals/results/latest.json` で出荷ゲートを通っていれば既定で有効
3. 設定の `enabled_checks` は 2 のゲートを無視して有効にする。`disabled_checks` は何よりも優先して無効にする
4. `onboarding_until` の日付までは、適合率 0.9 以上のチェックだけを有効にし、strictness の strict を standard に読み替える

出荷ゲートは、チェックごとに適合率 0.85 以上かつ再現率 0.85 以上。holdout のケースがあれば holdout だけで判定する。

## finalize の処理順

1. 適用判定で外れた思想・チェックの指摘を落とす
2. チェック固有の escalate・deescalate を適用する。そのあとで、適用判定の「重大度を1段下げる」を掛ける（固有ルールが決めた重大度からの相対で下げる）
3. ADR による例外: Accepted の ADR の scope に入り、exempts に当たる指摘を Info にして ADR 番号を添える。DDD-AGG-01・DDD-AGG-02・DDD-VO-01 は Low に留める
4. business 台帳の core・generic による重大度の調整（v1.5）
5. 全チェック共通の調整: 直近90日の変更回数が上位10% のファイルなら1段上げる。カバレッジがあり、該当行がテストで一度も実行されていなければ1段上げる（High は据え置き）
6. also_accept による重複の統合
7. 衝突裁定（design-router/conflicts.yml と要件定義の4つのルール）。負けた側は status を held にして理由を残す
8. verdict が borderline の指摘を「要確認」に回す。strict なら指摘一覧に出す
9. 厳しさ: lenient なら Low と Info を出さない
10. 同じチェックIDの指摘が5件を超えたら、6件目以降を aggregated にして「同種の違反が N 件」とまとめる
11. 思想ごとの採点（0〜10点）と、直すと上がる点数

## 採点

思想ごとに、10点から指摘の重みを引く。重みは High 3点、Medium 1.5点、Low 0.5点、Info 0点で、0点を下限にする。
held・merged・filtered の指摘と「要確認」は引かない。aggregated にまとめた指摘は引く。
走らせたチェックが1つもない思想には点を付けない。見ていない思想が満点に見えるのを防ぐため。

「何を直せば何点上がるか」は、指摘を重みの大きい順に並べ、上から順に直していったときの点数（`score_after`）で示す。
その1件だけを直したときに上がる点（`gain`）も残す。ただし、その1件を直しても減点が10点以上残るときは、点数が下限の0点のままなので gain は0になる。
そのため report.md では、点数が0点から上がり始めるまでの指摘を「上から N 件を直すと X 点」の1行にまとめ、そのあとを1件ずつ並べる。減点の合計は `total_deduction` に残す。

`report.scores: false` を設定すると、採点を出さない（report.json の scores は null）。

## 評価

- 1ケース=1ディレクトリ。ケースの中に `.claude/sumidashi.yml` を置けば、そのケースだけ設定を変えられる
- 評価は、思想の適用判定を on に固定して実行する（チェックの判定の精度だけを測るため）。適用判定そのものは `evals/fixtures/_applicability/` のケースで別に測る
- 各ケースは、そのケースのチェックIDだけを走らせて採点する。ほかのチェックの指摘は数えない
- 突き合わせ: ファイルが同じで行範囲が重なれば一致とみなす。期待1件に指摘1件までで、1つの指摘を2つの期待に当てることはしない
- 期待が violation のケースでは、期待どおりの violation を TP、期待にない violation を FP、出なかった期待を FN と数える
- 期待が borderline のケースは、適合率・再現率に数えない。borderline として出せたかを別の指標（borderline 一致率）で出す
- 期待が not_violation のケースで出た violation は FP
- 再現性: 同じ入力に5回かけ、High・Medium の指摘集合の Jaccard 係数の平均を出す
- 適用判定の評価は、出荷ゲートを無視してすべての ready のチェックを走らせ、思想ごとの mode・severity_shift・指摘数の上限を期待と比べる

## 開発

依存は uv が解決する。開発時だけ使うものは `--with` で足す。

```bash
R="uv run --no-project --with-requirements tools/requirements.txt"

# checks.yml・principles.yml・conflicts.yml を検証し、generated/ と docs/check-catalog.md を作り直す
$R --with jsonschema --with rdflib python tools/dev/build_knowledge.py

# 設計知識を SHACL で検証する（--adr-root REPO で、そのリポジトリの ADR も検証する）
$R --with rdflib --with pyshacl python tools/dev/validate_knowledge.py

# 評価を実行し、evals/results/latest.json を書き直す
$R python tools/dev/run_evals.py --write -v

# テスト
$R --with pytest --with jsonschema --with rdflib --with pyshacl python -m pytest tests
```

CI（`.github/workflows/ci.yml`）は Python 3.10 と 3.13 で次を確かめ、どれかが外れたら落ちる。

- `build_knowledge.py --check`: 生成物がコミットされたものと一致する
- `validate_knowledge.py`: SHACL に適合する
- `run_evals.py --check`: ready のチェックが出荷ゲートを通り、適用判定のケースが期待どおりで、`latest.json` のゲート結果が今回の結果と食い違わない。実行時はコミット済みの `latest.json` でチェックを有効にするので、チェックの実装や fixtures を変えたら `--write` で書き直してコミットする
- pytest
