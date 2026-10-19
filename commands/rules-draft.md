---
description: コードの条件分岐から業務ルール台帳（docs/business-rules.yml）の下書きを作り、確認のうえで書き込む
argument-hint: "[対象のパス]"
---

# /sumidashi:rules-draft

業務ルール台帳がないリポジトリで、コードの条件分岐から台帳の下書きを作る。台帳ができると、BIZ 系のチェック（台帳と実装の断絶、変わりやすいルールのハードコードなど）が走るようになる。

引数: `$ARGUMENTS`（省略時はドメイン層とアプリケーション層の全体）

## 手順

1. 作業ディレクトリを作り、層マップを取る

   ```bash
   WORK="$(mktemp -d "${TMPDIR:-/tmp}/sumidashi.XXXXXX")"; echo "$WORK"
   "${CLAUDE_PLUGIN_ROOT}/bin/sumidashi" collect --all --out "$WORK"
   ```

   引数でパスを渡されたら、`--all` の代わりにそのパスを渡す。

2. business スキル（`${CLAUDE_PLUGIN_ROOT}/skills/business/SKILL.md`）の「業務ルール台帳の下書きを作るとき」の手順で `$WORK/business-rules.yml` を作る。ルールIDは `BR-001` から振る

3. 既存の台帳（設定の `business_rules.path`、既定は `docs/business-rules.yml`）があれば、上書きせず、台帳にない分岐だけを追加の案にする（BIZ-07 の候補と同じもの）

4. 次を示して確認を取る
   - ルールの数と、複数箇所で実装されているルール（食い違いの候補）
   - テストが見つからなかったルール
   - `basis`・`subdomain`・`change_frequency`・`consistency` を「要確認」にしたルールの一覧（利用者に埋めてもらう）

5. 承認されたら書き込む。承認されるまで書き込まない

## 守ること

- 閾値や率はコードから引いた値をそのまま書く。丸めたり、あるべき値に直したりしない
- ルールの根拠やサブドメインの分類を推測で埋めない
- 施策の良し悪しを書かない
- 外部への送信はしない
