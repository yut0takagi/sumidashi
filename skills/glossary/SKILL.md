---
name: glossary
description: ドメイン用語集（docs/glossary.yml）をコードの命名と型の関係に照合するときに使う。ユビキタス言語がコードとずれていないかを見る。/sumidashi:review・/sumidashi:glossary-draft から読み込まれる。チェックIDは GLO- で始まる。
---

# glossary

ユビキタス言語を、概念と関係を持つ機械可読な用語集として持ち、コードの命名と型の関係に照らす。用語集が「読むだけの Wiki ページ」で終わり、コードとずれていくのを防ぐため。チェックの全文は [checks.yml](checks.yml)。

## 用語集の形式

人が書くのは `docs/glossary.yml`（設定の `glossary.path` で変更可）。プラグインはこれを SKOS（用語・同義語・上位下位）と OWL の最小限の語彙（部分・全体、関連）に変換して使う。最初から Turtle を書かせると誰も更新しなくなるので、書く形式と使う形式を分けている。

```yaml
context: order          # 境界づけられたコンテキスト
terms:
  - term: 注文
    code_names: [Order]
    definition: 顧客が確定した購入の単位。確定後は明細を追加できない
    synonyms_deprecated: [オーダー, Purchase]
    relations:
      has_part: [注文明細]     # 集約の内部
      refers_to: [顧客]        # ID 参照
  - term: 注文明細
    code_names: [OrderLine]
    definition: 注文に含まれる商品と数量の組
```

## チェック一覧

| ID | 名前 | 判定方式 | 既定の重大度 |
| --- | --- | --- | --- |
| GLO-01 | 用語集にない業務用語 | hybrid | Low |
| GLO-02 | 同義語の混在 | static | Medium |
| GLO-03 | 多義語 | llm | Medium |
| GLO-04 | 関係の食い違い | hybrid | Medium |
| GLO-05 | 非推奨語の使用 | static | Low |
| GLO-06 | 用語集の欠陥 | static | Low |

v0.1 ではすべて draft。

## 走らせる条件

- 用語集がないリポジトリでは GLO 系を走らせない。代わりに `/sumidashi:glossary-draft` でコードから下書きを作ることを勧める
- 対象はドメイン層の公開型・公開メソッドの名前（GLO-01）と、同じコンテキスト内の命名（GLO-02・03・05）

## 判定するとき

- GLO-01: ドメイン層の公開型・公開メソッドの名前を語に分け、業務上の語（技術用語、汎用の動詞を除く）が `code_names` にも `term` にもなければ候補。業務上の語かどうかを LLM が確かめる
- GLO-02: 同じ概念が同じコンテキスト内で2つ以上の名前で呼ばれる。`code_names` と `synonyms_deprecated` の併用を含む
- GLO-03: 同じ名前が同じコンテキスト内で別の概念を指して使われる。定義文とコード上の使われ方を比べる
- GLO-04: `has_part` がコード上で集約内部の所有になっていない、または `refers_to` がオブジェクト参照になっている
- GLO-05: `synonyms_deprecated` の語が新しいコード（差分）に出る
- GLO-06: 定義が空、循環した定義、`code_names` の重複

## 重複の扱い

GLO-04 は DDD-AGG-04（他の集約を ID で参照する）と同じ箇所を指すことがある。その場合は DDD-AGG-04 を主、GLO-04 を also_accept として扱い、重複して出さない。

## 用語集の下書きを作るとき

`/sumidashi:glossary-draft` の手順。

1. ドメイン層のクラス名・列挙型・公開メソッドの名前を集める（解析器の facts.json の `scale.entities`・`scale.value_objects` を起点にする）
2. コメント・docstring・テスト名から、業務上の言葉（日本語の呼び名）を拾う
3. 用語ごとに `term`・`code_names`・`definition` の案を作る。定義はコードから読み取れる事実（何を持つか、何ができないか）だけで書き、推測した業務上の意味には「要確認」と付ける
4. 集約のルートと子の関係から `has_part`、ID で持っている関係から `refers_to` を埋める
5. 同じ概念に複数の名前が使われていれば、どれを正にするかを利用者に聞く（勝手に決めない）
6. 下書きを見せ、承認されてから `docs/glossary.yml` に書く
