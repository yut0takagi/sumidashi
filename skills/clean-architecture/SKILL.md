---
name: clean-architecture
description: クリーンアーキテクチャ（依存性ルール・境界の越え方・ユースケースの責務）でコードを判定するときに使う。design-router か /sumidashi:review・/sumidashi:check から読み込まれる。チェックIDは CA- で始まる。
---

# clean-architecture

依存の向きを内側（方針）にそろえ、業務ルールをフレームワークや DB から守るための判定をまとめたスキル。チェックの全文（判定基準・除外条件・修正パターン・fixtures）は [checks.yml](checks.yml) にある。ここには判定するときの要点だけを置く。

## 守らせる原則

| 原則 | 中身 | 出典 |
| --- | --- | --- |
| ca.dependency-rule | ソースの依存は内側へだけ向け、内側は外側の名前を知らない | Martin『Clean Architecture』22章 |
| ca.framework-independence | 業務ルールをフレームワーク・DB・UI から独立させる | 同 22章・32章 |
| ca.acyclic-dependencies | 依存グラフに循環を作らない | 同 14章 |
| ca.boundary-data | 境界を越えるデータは内側で定義した単純な構造にする | 同 22章 |
| ca.ports-and-adapters | 内側が外部を使うときは、内側のインターフェースを外側が実装する | 同 11章、Cockburn |
| ca.use-case-responsibility | アプリケーション固有の業務ルールはユースケースに置く | 同 20章・22章 |
| ca.humble-object | I/O と判断を分ける | 同 23章 |
| ca.main-component | 具象の生成と組み立ては Main に閉じ込める | 同 26章 |

## チェック一覧

| ID | 名前 | 判定方式 | 既定の重大度 | v0.1 |
| --- | --- | --- | --- | --- |
| CA-DEP-01 | ドメイン層が外側の層に依存している | static | High | ready |
| CA-DEP-02 | ドメイン層がフレームワーク・ORM・I/O ライブラリに依存している | static | High | ready |
| CA-DEP-03 | アプリケーション層がアダプタ層・インフラ層に依存している | static | High | ready |
| CA-DEP-04 | 層をまたぐ循環依存がある | static | High | ready |
| CA-BND-01 | ORM のモデルがそのまま境界を越えている | hybrid | Medium | draft |
| CA-BND-02 | ユースケースの入出力に HTTP・Web フレームワークの型を使っている | static | Medium | ready |
| CA-BND-03 | アプリケーション層が外部 I/O をポートを介さずに直接使っている | hybrid | High | draft |
| CA-UC-01 | コントローラ・ハンドラに業務ロジックがある | hybrid | Medium | draft |
| CA-UC-02 | 1つのユースケースが複数のアクターの目的を抱えている | llm | Low | draft |
| CA-UC-03 | ユースケースが表示の形式を組み立てている | llm | Low | draft |
| CA-HUM-01 | I/O と業務の判断が分離されていない | llm | Medium | draft |
| CA-MAIN-01 | 具象の組み立てがコンポジションルートの外に散らばっている | hybrid | Low | draft |

static のチェック（CA-DEP 系と CA-BND-02）は解析器が確定する。LLM が判定を覆したり、同じ指摘を作り直したりしない。判定規則の細部は `docs/static-checks.md`。

## hybrid・llm のチェックを判定するとき

principle-reviewer としてこのスキルを担当するときの手順。

1. facts.json の `candidates` から、担当するチェックIDの候補を取り出す
2. 候補ごとに、checks.yml の `detection.question` に YES / NO で答える。答えの根拠になる行を必ず控える
3. YES なら criteria.violation と exclusions を照らし、当たれば violation、criteria.borderline に当たれば borderline
4. hybrid のチェックでは、候補にない箇所を新たに指摘しない
5. llm のチェック（CA-UC-02・CA-UC-03・CA-HUM-01）は、対象の層のファイルを読み、question に YES と答えられてエビデンスの行を示せるときだけ指摘する
6. 判定に必要な情報がコードの外にある（業務上の意図、チームの方針）なら borderline にする

判定でよく迷うところ:

- CA-BND-03 と CA-DEP-02 の違い: CA-DEP-02 はドメイン層、CA-BND-03 はアプリケーション層が対象。ロガーやトランザクション管理は borderline
- CA-UC-01: 入力形式の検証（必須項目、文字数）や HTTP ステータスの選択は業務ロジックではない。「この状態の注文はキャンセルできない」「合計が1万円以上なら送料無料」は業務ロジック
- CA-HUM-01: I/O を先頭でまとめて取得しているだけなら borderline。判断の途中で I/O を呼び、その結果でまた判断していれば violation
- CA-MAIN-01: エンティティ・値オブジェクト・ドメインイベントの `new` は組み立てではない

## 修正の示し方

- 修正方針は checks.yml の `fix_patterns` から選び、該当コードに当てはめた差分案を添える
- 依存の逆転を勧めるときは、どの層にどんな名前のインターフェースを置くかまで書く（例: `src/application/ports/payment-gateway.ts` に `PaymentGateway` を定義し、`src/infrastructure/stripe-payment-gateway.ts` が実装する）
- 直すコストは「変更するファイル数」で示す。直さない場合の影響は、変更の波及やテストのしにくさで具体的に書く

## 小さいコードへの当て方

層マップが推定できない、または CRUD 中心のプロジェクトでは、design-router の判定により CA-DEP 系だけを走らせる。そのとき層を増やす方向の修正（CA-BND-01 の変換層など）は勧めない。規模の判定は [design-router の scale-matrix](../design-router/references/scale-matrix.md)。

## 例

違反例と修正例は言語別に置いている。必要なときだけ読む。

- TypeScript: [references/examples-ts.md](references/examples-ts.md)
- Python: [references/examples-py.md](references/examples-py.md)
