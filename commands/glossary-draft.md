---
description: コードからドメイン用語集（docs/glossary.yml）の下書きを作り、確認のうえで書き込む
argument-hint: "[対象のパス]"
---

# /sumidashi:glossary-draft

用語集がないリポジトリで、ドメイン層のコードから用語集の下書きを作る。用語集ができると、GLO 系のチェック（同義語の混在、非推奨語の使用など）が走るようになる。

引数: `$ARGUMENTS`（省略時はドメイン層全体）

## 手順

1. 作業ディレクトリを作り、解析器で層マップとドメインの型を取る

   ```bash
   WORK="$(mktemp -d "${TMPDIR:-/tmp}/sumidashi.XXXXXX")"; echo "$WORK"
   "${CLAUDE_PLUGIN_ROOT}/bin/sumidashi" collect --all --out "$WORK"
   ```

   引数でパスを渡されたら、`--all` の代わりにそのパスを渡す。

   `$WORK/facts.json` の `layer_map.files` でドメイン層のファイルを、`scale.entities`・`scale.value_objects`・`scale.aggregate_candidates` で型の推定を取る。

2. glossary スキル（`${CLAUDE_PLUGIN_ROOT}/skills/glossary/SKILL.md`）の「用語集の下書きを作るとき」の手順で `$WORK/glossary.yml` を作る

3. 既存の用語集（設定の `glossary.path`、既定は `docs/glossary.yml`）があれば、上書きせず、足りない用語だけを追加する案にする

4. 次を示して確認を取る
   - 用語の数、コンテキストの数
   - 「要確認」を付けた定義の一覧
   - 同じ概念に複数の名前が使われている箇所（どれを正にするかを聞く）

5. 承認されたら書き込む。承認されるまで書き込まない

## 守ること

- 定義はコードから読み取れる事実（何を持つか、何ができないか）で書く。推測した業務上の意味には「要確認」を付ける
- どの名前を正にするかを勝手に決めない
- 外部への送信はしない
