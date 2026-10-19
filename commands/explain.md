---
description: チェックIDの原則・理由・違反例・修正例を解説する（学習用）
argument-hint: "<チェックID>（例: DDD-AGG-01）"
---

# /sumidashi:explain

チェック1つを、原則 → 出典 → 違反例 → 修正例 → このリポジトリでの状況、の順に解説する。レビューで出た指摘の意味を確かめるときと、設計思想を学ぶときに使う。

引数: `$ARGUMENTS`

## 手順

1. 引数を大文字にそろえ、チェックIDの形（`DDD-AGG-01` など）か確かめる。形が違えば、`sumidashi catalog` の一覧から近いものを挙げて聞き直す

2. 解析器で、知識グラフをたどった結果を取る

   ```bash
   "${CLAUDE_PLUGIN_ROOT}/bin/sumidashi" explain <チェックID>
   ```

   出力には、チェックの定義、守らせる原則と出典、関連・衝突するチェック、fixtures（違反・グレー・非違反のサンプル）、このリポジトリで例外にしている ADR が入っている。

3. 必要に応じて次を読む
   - `${CLAUDE_PLUGIN_ROOT}/skills/<思想>/checks.yml` の該当エントリ
   - `${CLAUDE_PLUGIN_ROOT}/skills/<思想>/references/examples-ts.md`・`examples-py.md`（利用者のリポジトリの言語に合わせて片方）
   - fixtures のファイル（`${CLAUDE_PLUGIN_ROOT}/evals/fixtures/` 配下）

4. 次の形で答える

```markdown
## <チェックID> <名前>

**原則**: <principle を1文で>（出典: <source>）

**なぜ守るのか**: <破ると何が起きるかを、具体的な不具合や変更コストで2〜3文>

**違反になる例**
<短いコード。利用者の言語で>

**直し方**
<修正後のコード。fix_patterns のどれを当てたかを1文で>

**似ているが違反ではない例**: <criteria.not_violation を具体例で>
**要確認になる例**: <criteria.borderline を具体例で>

**このリポジトリでは**: <例外にしている ADR があれば番号と理由。なければ「例外なし」>

**関連するチェック**: <related と、衝突するチェックがあれば裁定のルール>
```

## 守ること

- 例は fixtures か references の例をもとにする。原典にない主張を足さない
- 出典は checks.yml の source をそのまま書く。章番号を推測で補わない
- 「なぜ」は一般論で終わらせず、どんな不具合や変更コストにつながるかまで書く
- 利用者が続けて質問したら、関連するチェックの解説や、利用者のコードでの当てはめに進んでよい
