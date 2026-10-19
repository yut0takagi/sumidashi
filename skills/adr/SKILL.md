---
name: adr
description: ADR（Architecture Decision Record）を、設計思想と並ぶプロジェクト固有の判断基準として扱うときに使う。ADR による指摘の例外、コードと ADR の整合、ADR 自体のレビュー、ADR 起票の下書き。/sumidashi:review・/sumidashi:adr-review・/sumidashi:adr-draft から読み込まれる。チェックIDは ADR- で始まる。
---

# adr

一般論の設計思想より、そのチームが記録して合意した判断を優先する。そのために ADR を読み、指摘の例外と整合チェックに使う。チェックの全文は [checks.yml](checks.yml)。

## ADR に対してやること

| 機能 | 中身 | 入口 |
| --- | --- | --- |
| ① ADR による例外 | Accepted の ADR で原則から外れると記録された箇所は、指摘を Info に下げ、ADR 番号を添える | `/sumidashi:review`（finalize が自動でかける） |
| ② コードと ADR の整合 | Accepted の ADR の決定に反するコードを指摘する | `/sumidashi:review` |
| ③ ADR 自体のレビュー | 新規・更新された ADR の書き方と中身を見る | `/sumidashi:adr-review <パス>` |
| ④ ADR 起票の提案 | 衝突で保留にした指摘や、繰り返される例外から ADR の下書きを作る | `/sumidashi:adr-draft` |

## ADR の読み込み

- 置き場所は既定で `docs/adr/`。設定の `adr.path` で変えられる
- Michael Nygard 形式と MADR を読む。どちらでもなければ見出しから Status・Context・Decision・Consequences を推定し、推定できない ADR は「形式不明」として①②の対象外にする
- 使うのは Status が Accepted のものだけ。Superseded は置き換え先をたどり、Proposed・Deprecated は参照しない
- 解析器の読み込み結果は `"${CLAUDE_PLUGIN_ROOT}/bin/sumidashi" adr` で見られる

①②には、ADR ごとに機械が読める適用範囲が要る。フロントマターに `scope`（対象のパスやモジュール）と `exempts`（外れてよいチェックID）を書く。

```yaml
---
status: accepted
date: 2026-09-12
scope: [src/reporting/**]
exempts: [CA-BND-01, DDD-ENT-02]
---
# 0007. 集計系は ORM モデルを境界越えで直接使う
```

- `scope` がない ADR は②の対象にするが、①の例外には使わない（範囲が曖昧なまま指摘を消さないため）
- 正しさに関わるチェック（DDD-AGG-01・DDD-AGG-02・DDD-VO-01）は、exempts に入っていても Info ではなく Low に留め、毎回表示する

## チェック一覧

| ID | 名前 | 判定方式 | 既定の重大度 |
| --- | --- | --- | --- |
| ADR-CMP-01 | 決定に反するコード | llm | High |
| ADR-CMP-02 | 古い ADR に従っている | hybrid | Medium |
| ADR-CMP-03 | 例外の範囲外への拡大 | static | Medium |
| ADR-DOC-01 | 必須項目の欠落 | static | Medium |
| ADR-DOC-02 | 代替案がない | llm | Medium |
| ADR-DOC-03 | 帰結が一面的 | llm | Low |
| ADR-DOC-04 | 原則からの逸脱が明示されていない | llm | Medium |
| ADR-DOC-05 | 適用範囲が書かれていない | hybrid | Low |
| ADR-DOC-06 | 既存 ADR との矛盾 | llm | High |

v0.1 ではすべて draft。①の例外は finalize に組み込み済みで、チェックの有効・無効に関係なく働く。

## ADR-CMP 系（コードとの整合）を判定するとき

1. Accepted の ADR ごとに、Decision の文を「何をする／何をしない」の形に言い換える
2. `scope` に当たるファイルのうち、差分に含まれるものを読む
3. 決定と逆の実装があれば ADR-CMP-01。根拠に ADR 番号と Decision の該当文を引く
4. Superseded の ADR の決定に沿った実装が新しく追加されていれば ADR-CMP-02
5. ADR-CMP-03 は解析器が確定する（exempts のチェックが scope の外で同じ理由で破られている）

決定の文が曖昧で、コードが反しているかを決められないときは borderline。

## ADR-DOC 系（ADR 自体のレビュー）を判定するとき

ADR-DOC 系は書き方の指摘であって、決定の良し悪しは判定しない。

- ADR-DOC-01: Status・Context・Decision・Consequences のどれかがない、または1文未満
- ADR-DOC-02: 検討した代替案と、採らなかった理由が書かれていない
- ADR-DOC-03: Consequences に良い面しか書かれていない
- ADR-DOC-04: 決定内容が v1 のチェックに当たるのに、どの原則から外れるかと理由が書かれていない
- ADR-DOC-05: `scope` がなく、本文からも対象が特定できない
- ADR-DOC-06: Accepted の別 ADR と決定が矛盾し、Supersedes の記載もない

決定そのものへの意見は、v1 のチェックに当たる場合にだけ、該当チェックIDと一緒に「この判断で失うもの」として添える。

## ADR の下書きを作るとき（④）

- 材料は report の「衝突により保留」と、同じチェックIDの例外が繰り返される箇所
- Nygard 形式で、フロントマターに `status: proposed`・`scope`・`exempts` を入れる
- Context には、どの指摘が何件、どこで出ているかを事実として書く
- Decision は利用者が決めるので、選択肢を2つまで並べ、空欄のまま渡す
- 書き込むのは利用者が承認してから
