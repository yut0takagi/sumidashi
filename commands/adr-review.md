---
description: 新規・更新された ADR の書き方と中身を、型と設計思想の両面からレビューする
argument-hint: "<ADR のパス>（省略時は差分に含まれる ADR）"
---

# /sumidashi:adr-review

ADR 自体をレビューする（ADR-DOC 系）。決定の良し悪しは判定せず、書き方の不足と、既存の ADR・設計思想との関係を指摘する。

引数: `$ARGUMENTS`

## 手順

1. 対象を決める
   - パスを渡されたら、そのファイル（ディレクトリならその中の ADR すべて）
   - 渡されなければ、main とのマージベースからの差分に含まれる ADR（設定の `adr.path`、既定は `docs/adr/` 配下）

2. 解析器で読み込み結果を見る

   ```bash
   "${CLAUDE_PLUGIN_ROOT}/bin/sumidashi" adr
   ```

   対象の ADR の形式（Nygard・MADR・形式不明）、Status、scope、exempts と、既存の Accepted の ADR の一覧を確かめる。

3. adr スキル（`${CLAUDE_PLUGIN_ROOT}/skills/adr/SKILL.md`）と checks.yml の ADR-DOC 系を読み、ADR ごとに判定する

   | ID | 見ること |
   | --- | --- |
   | ADR-DOC-01 | Status・Context・Decision・Consequences のどれかがない、または1文未満 |
   | ADR-DOC-02 | 検討した代替案と、採らなかった理由がない |
   | ADR-DOC-03 | Consequences に良い面しか書かれていない |
   | ADR-DOC-04 | 決定が v1 のチェックに当たるのに、どの原則から外れるかと理由が書かれていない |
   | ADR-DOC-05 | `scope` がなく、本文からも対象が特定できない |
   | ADR-DOC-06 | Accepted の別 ADR と決定が矛盾し、Supersedes の記載もない |

   ADR-DOC-04 は、決定の内容を `sumidashi catalog` のチェックと照らす。当たるチェックがあれば、そのIDを exempts に書くことと、「この判断で失うもの」を Consequences に書くことを勧める。

4. 指摘を `/sumidashi:review` と同じ形（チェックID・重大度・場所・エビデンス・原則・修正方針・判定・トレードオフ）で示す。location は ADR ファイルの該当する見出しの行

5. 直し方は、足すべき見出しと文の案として示す。ADR の書き換えは、利用者が承認したときだけ行う

## 守ること

- 決定そのものの良し悪しを判定しない。意見を添えるのは、v1 のチェックに当たる場合に「この判断で失うもの」としてだけ
- 決定の文を勝手に書き換えない
- 外部への送信はしない
