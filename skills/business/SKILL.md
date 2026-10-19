---
name: business
description: 設計が業務の要求とルールを正しく反映しているかを、業務ルール台帳（docs/business-rules.yml）とチケットの受け入れ条件に照らして見るときに使う。施策の良し悪しは判定しない。/sumidashi:review・/sumidashi:rules-draft から読み込まれる。チェックIDは BIZ- で始まる。
---

# business

書かれた業務要求とコードの整合だけを見る。根拠のない「ビジネス的にはこうすべき」という意見は出さない。チェックの全文は [checks.yml](checks.yml)。

## 入力

- 業務ルール台帳 `docs/business-rules.yml`（設定の `business_rules.path` で変更可）: ルールID、ルールの文、根拠（規約・契約・法令・社内決定）、変更頻度、重要度、実装箇所、テスト
- サブドメインの分類: 台帳で各領域を core（競争力の源泉）・supporting・generic に分ける
- PR に紐づくチケットの受け入れ条件: PR 本文のリンクから取る。取れなければ利用者に貼ってもらう

```yaml
- id: BR-012
  rule: 会員ランクがゴールド以上の注文は、送料を無料にする
  basis: 会員規約 第8条
  subdomain: core
  change_frequency: high      # 年に数回、キャンペーンで条件が変わる
  consistency: immediate      # SCL-02・DDD-AGG-03 の判定に使う（immediate | eventual）
  implemented_in: [src/order/domain/shipping-fee.ts]
  tests: [tests/order/shipping-fee.spec.ts]
```

## チェック一覧

| ID | 名前 | 判定方式 | 既定の重大度 | 収録 |
| --- | --- | --- | --- | --- |
| BIZ-01 | 台帳と実装の断絶 | static | High | v1.5 |
| BIZ-02 | 同じルールの実装の食い違い | hybrid | High | v1.5 |
| BIZ-03 | 変わりやすいルールのハードコード | hybrid | Medium | v1.5 |
| BIZ-04 | 業務ルールのテスト欠落 | static | Medium | v1.5 |
| BIZ-05 | 受け入れ条件との不一致 | llm | High | v1 |
| BIZ-06 | 金額・数量・日時の扱いの誤り | hybrid | High | v1 |
| BIZ-07 | 台帳にない業務ルール | llm | Low | v1.5 |
| BIZ-08 | 設計の重さと業務上の重要度のずれ | llm | Info | v1.5 |

v0.1 ではすべて draft。台帳がないリポジトリでは BIZ-01〜04・07・08 を走らせない。BIZ-05・06 は台帳なしでも動く。

## 判定するとき

- BIZ-05: 受け入れ条件を1つずつ「入力・条件・期待する結果」に分け、差分のコードがそれを満たすかを確かめる。満たしていない、または逆の動きをするものを指摘する。受け入れ条件が手に入らなければ走らせない
- BIZ-06: 金額に浮動小数（number・float）を使っている、台帳と違う丸め、タイムゾーンを持たない日時で締め日を判定している、など。候補は解析器が出し（金額らしい名前の float、`new Date()` と日付の比較など）、業務上の誤りかを LLM が確かめる
- BIZ-03: change_frequency が high のルールの閾値・率・期間が、コードに直書きされている
- BIZ-08: generic な領域に重い設計（集約・イベント・CQRS）をしている、または core の領域がトランザクションスクリプトのまま複雑になっている。記録として残すだけなので Info

## 重大度への反映（v1.5）

- 台帳で core に分類された領域の指摘は、全系統で1段上げる（High は据え置き）
- generic の領域では、DDD 戦術系と MDL 系の指摘を1段下げる

業務上の重要度に応じて、どこで設計の手間をかけるかを変えるため。

## 業務ルール台帳の下書きを作るとき

`/sumidashi:rules-draft` の手順。

1. ドメイン層とアプリケーション層の条件分岐のうち、業務上の条件（金額・数量・日付・会員区分・状態）で分かれているものを集める
2. 分岐1つを1ルールとし、「〜のとき、〜する」の文に直す。閾値や率はコードから引いた値をそのまま書く
3. `implemented_in` に分岐のあるファイル、`tests` にその条件を確かめているテストを書く。テストが見つからなければ空のままにする
4. `basis`・`subdomain`・`change_frequency`・`consistency` はコードから決まらないので「要確認」とし、利用者に埋めてもらう
5. 同じ条件が複数箇所にあれば1ルールにまとめ、`implemented_in` に全部並べる（BIZ-02 の候補になる）
6. 下書きを見せ、承認されてから `docs/business-rules.yml` に書く
