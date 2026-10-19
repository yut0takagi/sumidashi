---
name: design-router
description: 設計相談とコードレビューの入口。「設計」「アーキテクチャ」「リファクタ」「レビュー」「責務の置き場所」「層の分け方」「集約」「DDD」「クリーンアーキテクチャ」などの依頼、または design / architecture / refactor / code review / layering / aggregate / clean architecture の依頼で読み込む。層マップを推定し、どの設計思想をどの厳しさで当てるかを決め、思想どうしの衝突を裁定する。
---

# design-router

sumidashi の入口のスキル。設計思想ごとのスキル（clean-architecture・ddd-tactical など）を直接使う前に、ここで「そもそも当てるか」「どの範囲で当てるか」を決める。過剰設計の勧めを、出力の段階ではなく入口で止めるのが役目。

## このスキルが受け持つこと

1. 層マップの推定（どのディレクトリがどの層か）
2. 適用判定（規模と複雑さから、どの思想のどのチェックを走らせるか）
3. 思想間の衝突の裁定（同じ箇所に逆向きの修正を勧める指摘が出たとき）
4. 設計相談（`/sumidashi:plan`）とレビュー（`/sumidashi:review`）の手順への振り分け

## 依頼の振り分け

| 依頼の形 | やること |
| --- | --- |
| 新機能の設計相談、「どこに置くべきか」 | `/sumidashi:plan` の手順に沿う |
| PR・差分・ファイルのレビュー | `/sumidashi:review` の手順に沿う |
| 特定の思想だけで見てほしい | `/sumidashi:check <思想名>` の手順に沿う |
| チェックIDや原則の意味を知りたい | `/sumidashi:explain <チェックID>` の手順に沿う |
| 初めて導入する | `/sumidashi:setup` を勧める |

コマンドを打たれていなくても、依頼の形から上の手順を選んで進めてよい。

## 解析器の呼び方

事実で決まるものは解析器で確定する。LLM の判断で層や依存を推測しない。

```bash
"${CLAUDE_PLUGIN_ROOT}/bin/sumidashi" layers             # 層マップと規模の推定を見る
"${CLAUDE_PLUGIN_ROOT}/bin/sumidashi" collect --out "$WORK"   # 差分を解析して facts.json を書く
"${CLAUDE_PLUGIN_ROOT}/bin/sumidashi" catalog            # チェックの一覧と出荷ゲートの状態
```

`$WORK` は `$TMPDIR` の下に作った作業ディレクトリ。利用者のリポジトリには書かない。

## 思想とスキルの対応表

思想を1つ足すときは、スキルフォルダを1つ追加し、この表に1行足す。

| 思想 | スキル | チェックIDの接頭辞 | 収録 |
| --- | --- | --- | --- |
| clean-architecture | `skills/clean-architecture` | CA- | v1 |
| ddd-tactical | `skills/ddd-tactical` | DDD- | v1 |
| adr | `skills/adr` | ADR- | v1 |
| glossary | `skills/glossary` | GLO- | v1 |
| model-commonality | `skills/model-commonality` | MDL- | v1 |
| business | `skills/business` | BIZ- | v1.5（BIZ-05・06 は v1） |
| logic-placement | `skills/logic-placement` | PLC-・SCL- | v1（SCL 系は v1.5） |

各スキルのチェックの全文は、そのスキルの `checks.yml` にある。SKILL.md には要点だけを置く。

## 適用判定

facts.json の `applicability` に、解析器が決めた結果と理由が入っている。表の全文は [references/scale-matrix.md](references/scale-matrix.md)。

| 条件 | clean-architecture | ddd-tactical |
| --- | --- | --- |
| 層マップが推定できない | CA-DEP 系のみ、重大度を1段下げる | 適用しない |
| CRUD 中心 | CA-DEP 系のみ | 適用しない |
| 集約らしき型が推定できない | 通常どおり | ENT・VO 系のみ |
| 設定で on・off を明示 | 設定に従う | 設定に従う |

CRUD 中心かどうかの静的な目安は「ドメイン層の行数がテスト以外の全体の 10% 未満」。コードを読んで、目安と違う判断（ドメイン層は小さいが業務ルールが濃い、など）をしてよい。上書きしたときは、総評に理由を1文で書く。

層マップの推定の仕方と、推定が外れたときの直し方は [references/layer-map.md](references/layer-map.md)。

## チェックの有効・無効

- status が ready で、評価の出荷ゲートを通ったチェックだけが既定で有効
- status が draft のチェック（v0.1 では hybrid・llm のすべて）は、設定の `experimental: true` のときだけ走る
- 設定の `disabled_checks` は何よりも優先する
- `onboarding_until` の日付までは、適合率 0.9 以上のチェックだけを使い、strict は standard として扱う

## 判定と重大度

判定（verdict）は violation・borderline の2つを出す。not_violation は出さない。

| 判定 | 扱い |
| --- | --- |
| violation | 指摘一覧に出す |
| borderline | 「要確認」欄に出す。判定に必要な情報がコードの外にあるときもここ |

重大度は High・Medium・Low・Info の4段階。書き手の印象で上下させない。上下させるのは、checks.yml の escalate・deescalate、ADR による例外、変更頻度とカバレッジによる共通の調整だけで、どれも finalize が機械的にかける。

## 衝突の裁定

同じ箇所に複数のチェックが逆向きの修正を勧めたら、次の順で裁定する。詳細と v1 で想定している衝突の例は [references/conflict-rules.md](references/conflict-rules.md)。

0. ADR による例外を先に当てる（正しさに関わる DDD-AGG-01・02、DDD-VO-01 は Info でなく Low に留める）
1. 正しさに関わる指摘（重大度 High）を優先する
2. 依存方向に関わる指摘（CA-DEP 系）を、内部構造の指摘（DDD-AGG 系の分割など）より優先する
3. それでも決まらなければ、変更ファイル数が少ない修正案を採る
4. 採らなかった側の指摘は消さず、「衝突により保留」として理由付きで残す

finalize が機械的に裁定できる衝突は design-router の `conflicts.yml` に書いてある。LLM の指摘どうしの衝突で conflicts.yml にないものは、同じ順で裁定し、総評に理由を書く。

## 出力のきまり

- 総評 → 指摘一覧 → 要確認 → 採点の順に出す
- 重大度 High が1件でもあれば、総評の冒頭に出す
- 指摘1件には、チェックID・重大度・場所（ファイルと行範囲）・エビデンス・原則・修正方針・判定と判定方式・トレードオフを必ず付ける（`schemas/finding.schema.json`）
- 一般論だけの指摘は出さない。根拠はコード上のエビデンスに紐づける
- 原則には出典を、ADR で例外にした指摘には ADR 番号を添える
- 出力言語は利用者の言語に合わせる。チェックIDと原典の用語は英語のまま残す

## してはいけないこと

- 解析器が出した層マップや依存関係を、推測で上書きする（推定が外れていたら、設定の `layers` で直すよう利用者に勧める）
- 小さいコードや CRUD 中心のコードに、集約・リポジトリ・ドメインイベントの導入を勧める
- 利用者の承認なしにファイルを書き換える。修正は差分案として示すところまで
- コードやレビュー結果を外部に送る
