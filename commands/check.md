---
description: 特定の設計思想だけでコードを見る（例: /sumidashi:check ddd-tactical src/order）
argument-hint: "<思想名> [パス...] [--base <ref>] [--all]"
---

# /sumidashi:check

1つの設計思想だけでレビューする。手順は `/sumidashi:review` と同じで、対象の思想を絞る点だけが違う。

引数: `$ARGUMENTS`

1つ目の引数が思想名、残りが対象（パス、`--base`、`--all`）。

## 手順

1. 思想名を確かめる。次で一覧が出る。一覧にない名前なら、近い名前を挙げて聞き直す

   ```bash
   "${CLAUDE_PLUGIN_ROOT}/bin/sumidashi" catalog --format md
   ```

   思想名は clean-architecture・ddd-tactical・adr・glossary・model-commonality・business・logic-placement のどれか。

2. 作業ディレクトリを作る

   ```bash
   WORK="$(mktemp -d "${TMPDIR:-/tmp}/sumidashi.XXXXXX")"; echo "$WORK"
   ```

3. 思想を絞って解析する（`<思想名>` と `<残りの引数>` は $ARGUMENTS から分けたもの）

   ```bash
   "${CLAUDE_PLUGIN_ROOT}/bin/sumidashi" collect <残りの引数> --philosophy <思想名> --out "$WORK"
   ```

4. 以降は `/sumidashi:review` の手順3〜7と同じ。principle-reviewer は指定の思想の分だけ起動する

## 適用判定との関係

明示して呼ばれた思想でも、facts.json の `applicability` で「適用しない」となっていれば、その理由（層マップが推定できない、CRUD 中心など）を先に伝える。そのうえで、どうしても見たいと言われたら、設定の `philosophies` で `on` を明示する方法を案内する。解析器の判定を飛ばして走らせない。過剰設計の勧めを入口で止めるため。
