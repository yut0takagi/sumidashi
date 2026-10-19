---
name: ddd-tactical
description: DDD 戦術設計（集約・エンティティ・値オブジェクト・リポジトリ・ドメインサービス・ドメインイベント）でコードを判定するときに使う。design-router か /sumidashi:review・/sumidashi:check から読み込まれる。チェックIDは DDD- で始まる。
---

# ddd-tactical

ドメインの不変条件とデータ整合を、ドメインオブジェクト自身に守らせるための判定をまとめたスキル。チェックの全文は [checks.yml](checks.yml) にある。ここには判定するときの要点だけを置く。

## 当てる前に

ddd-tactical は、小さいコードに当てると過剰設計を勧めることになる。design-router の適用判定に必ず従う。

- 層マップが推定できない、または CRUD 中心なら、このスキルは走らせない
- 集約らしき型（ルートと、ルートが所有する子のエンティティ）が推定できなければ、ENT・VO 系だけを走らせる
- business 台帳で generic に分類された領域では、DDD 系の指摘を1段下げる（v1.5）

## 守らせる原則

| 原則 | 中身 | 出典 |
| --- | --- | --- |
| ddd.aggregate-root-access | 集約内部の状態はルートのメソッドを通してのみ変える | Evans 6章 |
| ddd.aggregate-invariants | 集約の不変条件は集約自身が守る | Evans 6章、Vernon 10章 |
| ddd.one-aggregate-per-transaction | 1トランザクションで変更する集約は1つ | Vernon 10章 |
| ddd.reference-by-id | 他の集約は ID で参照する | Vernon 10章 |
| ddd.entity-identity | エンティティは同一性で区別する | Evans 5章 |
| ddd.rich-domain-model | 業務ルールはデータを持つオブジェクトに置く | Evans 5章、Fowler |
| ddd.intention-revealing-mutation | 状態は意図を表すメソッドからだけ変える | Evans 10章、Vernon 5章 |
| ddd.value-object-immutability | 値オブジェクトは不変 | Evans 5章 |
| ddd.self-validating-value | 値オブジェクトは生成時に自分を検証する | Vernon 6章 |
| ddd.explicit-domain-types | 業務上の値は専用の型で表す | Vernon 6章、Fowler |
| ddd.repository-per-aggregate | リポジトリは集約ルートごと | Evans 6章 |
| ddd.persistence-ignorance | リポジトリは永続化の技術を表に出さない | Evans 6章、Vernon 12章 |
| ddd.domain-service-scope | ドメインサービスには、1つのオブジェクトに属さない操作だけを置く | Evans 5章 |
| ddd.domain-event-as-fact | ドメインイベントは起きた事実を過去形で表す | Vernon 8章 |

## チェック一覧

| ID | 名前 | 判定方式 | 既定の重大度 | v0.1 |
| --- | --- | --- | --- | --- |
| DDD-AGG-01 | 集約の外から内部エンティティを直接変更している | hybrid | High | draft |
| DDD-AGG-02 | 集約の不変条件を集約の外で検証している | llm | High | draft |
| DDD-AGG-03 | 1つのトランザクションで複数の集約を更新している | hybrid | Medium | draft |
| DDD-AGG-04 | 他の集約をオブジェクト参照で保持している | hybrid | Medium | draft |
| DDD-ENT-01 | エンティティの等価性が識別子で決まっていない | hybrid | Medium | draft |
| DDD-ENT-02 | エンティティが貧血ドメインモデルになっている | llm | Medium | draft |
| DDD-ENT-03 | エンティティの状態を外から直接書き換えられる | static | Medium | ready |
| DDD-VO-01 | 値オブジェクトが生成時に自分を検証していない | hybrid | High | draft |
| DDD-VO-02 | 値オブジェクトが可変になっている | static | Medium | ready |
| DDD-VO-03 | 業務上の値をプリミティブ型のまま扱っている | hybrid | Low | draft |
| DDD-REP-01 | リポジトリが集約単位になっていない | llm | Medium | draft |
| DDD-REP-02 | リポジトリのインターフェースが永続化の技術を表に出している | static | Medium | ready |
| DDD-SRV-01 | 1つのエンティティで完結する判断がサービスにある | llm | Medium | draft |
| DDD-EVT-01 | ドメインイベントの名前が過去形になっていない | static | Low | ready |
| DDD-EVT-02 | ドメインイベントがデータ変更の通知になっている | llm | Low | draft |

正しさに関わる3つ（DDD-AGG-01・DDD-AGG-02・DDD-VO-01）は、ADR で例外にしても Info ではなく Low に留まり、毎回表示される。

## エンティティと値オブジェクトの見分け方

解析器は次の規則で推定し、facts.json の `scale.entities`・`scale.value_objects` に出す。LLM はこの推定を前提に判定し、推定が明らかに外れていれば borderline にして理由を書く。

- エンティティ: ドメイン層のクラスで、`id`・`_id`・`<クラス名>Id` などの識別子を持つもの
- 値オブジェクト: 識別子を持たず、ValueObject を継承する、`equals`・`__eq__` を持つ、または dataclass であるもの
- どちらも、名前が Dto・Props・Command・Query・Event・Error などで終わるクラスは除く

細部は `docs/static-checks.md`。

## hybrid・llm のチェックを判定するとき

1. facts.json の `candidates` から担当するチェックIDの候補を取り出す。`scale.aggregate_candidates` で集約のルートと子を確かめる
2. 候補ごとに `detection.question` に YES / NO で答え、根拠の行を控える
3. criteria と exclusions に照らして violation か borderline を決める。hybrid では候補にない箇所を指摘しない
4. llm のチェック（DDD-AGG-02・ENT-02・REP-01・SRV-01・EVT-02）は、ドメイン層とアプリケーション層を読み、エビデンスの行を示せるときだけ指摘する
5. 即時の一貫性が要るか（DDD-AGG-03）のように、答えが業務ルール台帳やチームの判断にあるなら borderline

判定でよく迷うところ:

- DDD-AGG-01 と DDD-ENT-03: ENT-03 は「書き換えられる口がある」こと（クラスの定義）、AGG-01 は「実際に集約の外から書き換えている」こと（呼び出し側）。両方当たれば両方出す
- DDD-AGG-02: 入力の形式検証や認可は不変条件ではない。「明細は最大100件」「確定済みの注文には明細を足せない」は不変条件
- DDD-ENT-02: 業務ルールがほとんどないマスタデータ（都道府県など）は borderline
- DDD-SRV-01: 複数の集約にまたがる判断や、為替レートのような外部の情報を要する計算はドメインサービスでよい
- DDD-EVT-02: CDC 用の統合イベントだと明示されていれば除外

## 修正の示し方

- 修正方針は checks.yml の `fix_patterns` から選び、該当コードに当てはめた差分案を添える
- ロジックの移し先を勧めるときは、logic-placement のロジック配置の判定手順（Q1〜Q6）で結論を出し、どの Q で決まったかを `suggestion.placement` に書く（例:「Q2 ではい。送料の判断は Order の状態だけで決まるので Order のメソッドに移す」）
- 集約の分割や結果整合への切り替えは変更が大きい。tradeoff に変更ファイル数と、放置した場合の不整合の具体例を書く

## 例

- TypeScript: [references/examples-ts.md](references/examples-ts.md)
- Python: [references/examples-py.md](references/examples-py.md)
