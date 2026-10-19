---
description: 差分かパスを設計思想のチェックでレビューし、総評・指摘一覧・要確認・採点を出す
argument-hint: "[パス...] [--base <ref>] [--all]"
---

# /sumidashi:review

対象のコードを、適用すると判定された設計思想のチェックでレビューする。事実で決まるものは解析器が確定し、解釈が要る判定だけを principle-reviewer に任せる。

引数: `$ARGUMENTS`

- パスを渡されたら、そのパス配下が対象
- 何も渡されなければ、現在のブランチの main とのマージベースからの差分が対象（main がなければ master）
- `--base <ref>` で比較先を変える。`--all` でリポジトリ全体

## 手順

### 1. 作業ディレクトリを作る

中間ファイルは利用者のリポジトリに書かない。

```bash
WORK="$(mktemp -d "${TMPDIR:-/tmp}/sumidashi.XXXXXX")"; echo "$WORK"
```

以降のコマンドでは、表示されたパスをそのまま使う。

### 2. 静的解析（collect）

```bash
"${CLAUDE_PLUGIN_ROOT}/bin/sumidashi" collect $ARGUMENTS --out "$WORK"
```

失敗したら、エラーをそのまま利用者に見せて止まる。uv も python3 の依存（tree-sitter など）もない環境では、uv のインストールを勧める。差分が空なら「対象の変更がない」と伝えて終わる。

### 3. facts.json を読む

`$WORK/facts.json` から次を確かめる。

- `layer_map`: 層マップの出どころ（設定か推定か）と、推定できたか
- `applicability`: 思想ごとの適用結果と理由
- `active_checks`: 今回走らせるチェック。detection が hybrid・llm のものを思想ごとにまとめる（draft のチェックは、設定の experimental が true のときだけここに入っている）
- `candidates`: hybrid のチェックの候補

design-router スキルの適用判定（`skills/design-router/references/scale-matrix.md`）と照らし、推定が明らかに外れていると思ったら、総評に理由を1文で書き、設定の `layers` や `philosophies` で直すことを提案する。解析器の判定を黙って書き換えない。

### 4. principle-reviewer を思想ごとに並列で起動する

`active_checks` に hybrid・llm のチェックがある思想ごとに、principle-reviewer（subagent_type は `sumidashi:principle-reviewer`）を1つずつ起動する。すべて1つのメッセージでまとめて呼び、並列に走らせる。hybrid・llm のチェックが1つもなければ、この段は飛ばす。

プロンプトには次を書く。

```text
facts: <WORK>/facts.json
philosophy: <思想ID>
plugin_root: ${CLAUDE_PLUGIN_ROOT} を展開した絶対パス
checks: <その思想の hybrid・llm のチェックID をカンマ区切り>
out: <WORK>/llm-<思想ID>.json
language: <利用者の言語。既定は ja>
```

各サブエージェントは `out` に指摘の配列を書いて、パスと件数を返す。返ってこなかった思想があれば、総評にその旨を書いて続ける。

### 5. まとめる（finalize）

```bash
"${CLAUDE_PLUGIN_ROOT}/bin/sumidashi" finalize --facts "$WORK/facts.json" --llm "$WORK"/llm-*.json --out "$WORK"
```

LLM の指摘ファイルがなければ `--llm` を付けない。finalize が ADR による例外、重大度の調整、重複の統合、衝突の裁定、厳しさの適用、採点をかけ、`$WORK/report.md` と `$WORK/report.json` を書く。

### 6. 結果を示す

`$WORK/report.md` を読み、次の順で示す。チェックID・重大度・判定は report のとおりに書き、言い換えたり上下させたりしない。

1. 総評: 重大度 High が1件でもあれば冒頭に「High が N 件」と出し、その一覧を書く。続けて、適用した思想と適用しなかった思想（理由つき）、全体の傾向を3〜5文で
2. 指摘一覧: 重大度の高い順。1件ごとに、チェックID・重大度・場所（`ファイル:開始行-終了行`）・エビデンス・原則（出典）・修正方針（差分案があれば添える）・判定方式・トレードオフ
3. 要確認（borderline）: 判定に必要な情報がコードの外にあるもの。何を確かめれば決まるかを1文ずつ
4. 衝突により保留: 勝った側のチェックIDと裁定ルール、保留にした指摘の要約
5. 採点: 思想ごとの0〜10点と、何を直せば何点上がるか（設定で採点を切っていれば出さない）

同じチェックIDの指摘が5件を超えた分は「同種の違反が N 件」とまとめて示す。最後に report.md と report.json のパスを1行で示す。

### 7. 修正について

修正は差分案を示すところまで。利用者が「直して」と言ったときだけ、その指摘の範囲でファイルを書き換える。同じ判断が繰り返し保留になっているなら、`/sumidashi:adr-draft` で ADR の起票を勧める。

## 守ること

- 外部への送信はしない
- 解析器（static）の指摘を LLM の判断で消したり作り直したりしない。誤りだと思うものは「誤検知の疑い」として理由を添え、そのまま残す
- 一般論だけの指摘を足さない
