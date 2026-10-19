# チェック一覧

`tools/dev/build_knowledge.py` が checks.yml と評価結果から生成する。手で編集しない。

状態が ready のチェックは、評価の出荷ゲート（適合率・再現率とも 0.85 以上）を通ると既定で有効になる。draft のチェックは、設定の `experimental: true` のときだけ走る。

## クリーンアーキテクチャ（clean-architecture）

依存性ルール、境界の越え方、ユースケースの責務

| ID | 名前 | 判定 | 状態 | 重大度 | リリース | 評価 |
| --- | --- | --- | --- | --- | --- | --- |
| CA-DEP-01 | ドメイン層が外側の層に依存している | static | ready | High | v1 | P 1.00 / R 1.00（通過） |
| CA-DEP-02 | ドメイン層がフレームワーク・ORM・I/O ライブラリに依存している | static | ready | High | v1 | P 1.00 / R 1.00（通過） |
| CA-DEP-03 | アプリケーション層がアダプタ層・インフラ層に依存している | static | ready | High | v1 | P 1.00 / R 1.00（通過） |
| CA-DEP-04 | 層をまたぐ循環依存がある | static | ready | High | v1 | P 1.00 / R 1.00（通過） |
| CA-BND-01 | ORM のモデルがそのまま境界を越えている | hybrid | draft | Medium | v1 | - |
| CA-BND-02 | ユースケースの入出力に HTTP・Web フレームワークの型を使っている | static | ready | Medium | v1 | P 1.00 / R 1.00（通過） |
| CA-BND-03 | アプリケーション層が外部 I/O をポートを介さずに直接使っている | hybrid | draft | High | v1 | - |
| CA-UC-01 | コントローラ・ハンドラに業務ロジックがある | hybrid | draft | Medium | v1 | - |
| CA-UC-02 | 1つのユースケースが複数のアクターの目的を抱えている | llm | draft | Low | v1 | - |
| CA-UC-03 | ユースケースが表示の形式を組み立てている | llm | draft | Low | v1 | - |
| CA-HUM-01 | I/O と業務の判断が分離されていない | llm | draft | Medium | v1 | - |
| CA-MAIN-01 | 具象の組み立てがコンポジションルートの外に散らばっている | hybrid | draft | Low | v1 | - |

## DDD 戦術設計（ddd-tactical）

集約・エンティティ・値オブジェクト・リポジトリ・ドメインサービス・ドメインイベント

| ID | 名前 | 判定 | 状態 | 重大度 | リリース | 評価 |
| --- | --- | --- | --- | --- | --- | --- |
| DDD-AGG-01 | 集約の外から内部エンティティを直接変更している | hybrid | draft | High | v1 | - |
| DDD-AGG-02 | 集約の不変条件を集約の外で検証している | llm | draft | High | v1 | - |
| DDD-AGG-03 | 1つのトランザクションで複数の集約を更新している | hybrid | draft | Medium | v1 | - |
| DDD-AGG-04 | 他の集約をオブジェクト参照で保持している | hybrid | draft | Medium | v1 | - |
| DDD-ENT-01 | エンティティの等価性が識別子で決まっていない | hybrid | draft | Medium | v1 | - |
| DDD-ENT-02 | エンティティが貧血ドメインモデルになっている | llm | draft | Medium | v1 | - |
| DDD-ENT-03 | エンティティの状態を外から直接書き換えられる | static | ready | Medium | v1 | P 1.00 / R 1.00（通過） |
| DDD-VO-01 | 値オブジェクトが生成時に自分を検証していない | hybrid | draft | High | v1 | - |
| DDD-VO-02 | 値オブジェクトが可変になっている | static | ready | Medium | v1 | P 1.00 / R 1.00（通過） |
| DDD-VO-03 | 業務上の値をプリミティブ型のまま扱っている | hybrid | draft | Low | v1 | - |
| DDD-REP-01 | リポジトリが集約単位になっていない | llm | draft | Medium | v1 | - |
| DDD-REP-02 | リポジトリのインターフェースが永続化の技術を表に出している | static | ready | Medium | v1 | P 1.00 / R 1.00（通過） |
| DDD-SRV-01 | 1つのエンティティで完結する判断がサービスにある | llm | draft | Medium | v1 | - |
| DDD-EVT-01 | ドメインイベントの名前が過去形になっていない | static | ready | Low | v1 | P 1.00 / R 1.00（通過） |
| DDD-EVT-02 | ドメインイベントが業務上の出来事ではなくデータ変更の通知になっている | llm | draft | Low | v1 | - |

## ADR（Architecture Decision Record）（adr）

ADR による例外、コードと ADR の整合、ADR 自体のレビュー

| ID | 名前 | 判定 | 状態 | 重大度 | リリース | 評価 |
| --- | --- | --- | --- | --- | --- | --- |
| ADR-CMP-01 | Accepted の ADR の決定に反するコードがある | llm | draft | High | v1 | - |
| ADR-CMP-02 | Superseded の ADR の決定に沿った実装が新しく追加されている | hybrid | draft | Medium | v1 | - |
| ADR-CMP-03 | ADR で例外にしたチェックが scope の外でも破られている | static | draft | Medium | v1 | - |
| ADR-DOC-01 | ADR に必須の項目が欠けている | static | draft | Medium | v1 | - |
| ADR-DOC-02 | ADR に検討した代替案が書かれていない | llm | draft | Medium | v1 | - |
| ADR-DOC-03 | ADR の帰結に良い面しか書かれていない | llm | draft | Low | v1 | - |
| ADR-DOC-04 | ADR が原則から外れることを明示していない | llm | draft | Medium | v1 | - |
| ADR-DOC-05 | ADR の適用範囲が書かれていない | hybrid | draft | Low | v1 | - |
| ADR-DOC-06 | ADR が既存の Accepted の ADR と矛盾している | llm | draft | High | v1 | - |

## ドメイン用語（glossary）

ドメイン用語オントロジー（用語集）とコードの照合

| ID | 名前 | 判定 | 状態 | 重大度 | リリース | 評価 |
| --- | --- | --- | --- | --- | --- | --- |
| GLO-01 | ドメイン層の名前に用語集にない業務用語が使われている | hybrid | draft | Low | v1 | - |
| GLO-02 | 同じ概念が同じコンテキストの中で別々の名前で呼ばれている | static | draft | Medium | v1 | - |
| GLO-03 | 同じ名前が同じコンテキストの中で別の概念を指している | llm | draft | Medium | v1 | - |
| GLO-04 | 用語集の関係とコードの構造が食い違っている | hybrid | draft | Medium | v1 | - |
| GLO-05 | 非推奨の用語が新しいコードに使われている | static | draft | Low | v1 | - |
| GLO-06 | 用語集そのものに欠陥がある | static | draft | Low | v1 | - |

## モデルの共通化（model-commonality）

共通化すべきモデルの見落としと、誤った共通化

| ID | 名前 | 判定 | 状態 | 重大度 | リリース | 評価 |
| --- | --- | --- | --- | --- | --- | --- |
| MDL-01 | 同じ概念を表す型が重複して定義されている | hybrid | draft | Medium | v1 | - |
| MDL-02 | 同じ業務計算が複数の場所で別々に実装されている | hybrid | draft | High | v1 | - |
| MDL-03 | 値オブジェクトにすべき値の組がバラの引数で散らばっている | hybrid | draft | Medium | v1 | - |
| MDL-04 | 状態・区分が文字列や数値のリテラルのまま散らばっている | static | draft | Medium | v1 | - |
| MDL-05 | 別の概念を1つの型にまとめた誤った共通化がある | llm | draft | Medium | v1 | - |
| MDL-06 | 共有カーネルにある型を再定義している | static | draft | Low | v1 | - |

## ビジネス視点（business）

業務ルール台帳・受け入れ条件とコードの整合

| ID | 名前 | 判定 | 状態 | 重大度 | リリース | 評価 |
| --- | --- | --- | --- | --- | --- | --- |
| BIZ-01 | 台帳の業務ルールと実装が辿れない | static | draft | High | v1.5 | - |
| BIZ-02 | 同じ業務ルールの実装どうしで条件や値が食い違っている | hybrid | draft | High | v1.5 | - |
| BIZ-03 | 変わりやすい業務ルールの値がコードに直書きされている | hybrid | draft | Medium | v1.5 | - |
| BIZ-04 | 重要な業務ルールに境界のテストがない | static | draft | Medium | v1.5 | - |
| BIZ-05 | チケットの受け入れ条件をコードが満たしていない | llm | draft | High | v1 | - |
| BIZ-06 | 金額・数量・日時の扱いに誤りがある | hybrid | draft | High | v1 | - |
| BIZ-07 | 台帳にない業務ルールがコードにある | llm | draft | Low | v1.5 | - |
| BIZ-08 | 設計の重さが業務上の重要度と合っていない | llm | draft | Info | v1.5 | - |

## ロジックの配置とスケール（logic-placement）

ロジックの置き場所の判定と、水平スケールを妨げる構造

| ID | 名前 | 判定 | 状態 | 重大度 | リリース | 評価 |
| --- | --- | --- | --- | --- | --- | --- |
| PLC-01 | エンティティ・値オブジェクトが外部を呼んでいる | static | draft | High | v1 | - |
| PLC-02 | ドメインサービスが手順を調整している | hybrid | draft | Medium | v1 | - |
| PLC-03 | アプリケーションサービスに業務判断がある | llm | draft | Medium | v1 | - |
| SCL-01 | サービスがリクエストをまたぐ状態を持っている | hybrid | draft | High | v1.5 | - |
| SCL-02 | 即時でなくてよい処理を同じトランザクションで同期的に実行している | llm | draft | Medium | v1.5 | - |
| SCL-03 | ドメインロジックのために過剰に読み込んでいる | hybrid | draft | Medium | v1.5 | - |
| SCL-04 | 読み取り専用の画面を集約経由で組み立てている | llm | draft | Low | v1.5 | - |
| SCL-05 | 更新が1つの集約インスタンスに集中している | llm | draft | Medium | v1.5 | - |

## 衝突の裁定

| 組 | 裁定 |
| --- | --- |
| MDL-01 と MDL-05 | R3-FEWER-FILES |
| CA-DEP-01 と MDL-01 | R2-DEPENDENCY |
| CA-DEP-03 と MDL-01 | R2-DEPENDENCY |
| MDL-05 と MDL-06 | R3-FEWER-FILES |
