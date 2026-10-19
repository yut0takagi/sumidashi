# 規模・思想・厳しさの対応表

design-router が「どの思想を、どの範囲と厳しさで当てるか」を決めるときの表。解析器（`sumidashi collect`）が facts.json の `applicability` に同じ判定を書くので、ふだんはその結果をそのまま使う。

## 判定に使う事実

facts.json の `scale` と `layer_map` に入っている。

| 事実 | 中身 |
| --- | --- |
| `layer_map.estimable` | domain が見つかり、domain・application・adapter・infrastructure のうち2つ以上が見つかったか |
| `scale.loc_by_layer` | 層ごとの行数（テストと生成コードを除く） |
| `scale.domain_ratio` | ドメイン層の行数 ÷ テスト以外の全体の行数 |
| `scale.aggregate_candidates` | 集約らしき型。識別子を持つドメインのクラスのうち、別のエンティティ（またはそのコレクション）をフィールドに持つもの |
| `scale.entities`・`scale.value_objects` | エンティティ・値オブジェクトと推定したクラス |

## 適用の表

上の行から順に見て、最初に当たった行を使う。設定の `philosophies` で on・off を明示した思想は、この表より設定を優先する。

| # | 条件 | clean-architecture | ddd-tactical |
| --- | --- | --- | --- |
| 1 | 層マップが推定できない（全部1ディレクトリなど） | CA-DEP 系のみ。重大度を1段下げる | 適用しない |
| 2 | CRUD 中心（domain_ratio が 0.10 未満、またはルーターの判断） | CA-DEP 系のみ | 適用しない |
| 3 | 集約らしき型が推定できない | 通常どおり | ENT・VO 系のみ（AGG・REP・SRV・EVT 系を外す） |
| 4 | 上のどれにも当たらない | 通常どおり | 通常どおり |

adr・glossary・model-commonality・business・logic-placement は、入力（ADR・用語集・業務ルール台帳）があるかどうかで決まる。

| 思想 | 走らせる条件 |
| --- | --- |
| adr | `docs/adr/`（設定の `adr.path`）に ADR がある。ADR がなければ ADR-CMP 系は走らない |
| glossary | `docs/glossary.yml` がある。なければ走らせず、`/sumidashi:glossary-draft` を勧める |
| model-commonality | ddd-tactical を適用するとき。generic の領域では指摘を1段下げる |
| business | 台帳があれば全部。台帳がなければ BIZ-05・06 だけ |
| logic-placement | ddd-tactical を適用するとき。PLC-01 は層マップが推定できれば走る |

## CRUD 中心かどうかをルーターが上書きするとき

静的な目安（domain_ratio）は行数しか見ていない。次のようなときは、コードを読んで上書きしてよい。上書きしたら総評に理由を1文で書く。

- ドメイン層は小さいが、状態遷移や金額の計算など業務ルールが詰まっている → CRUD 中心ではない
- ドメイン層の行数は多いが、ほとんどが getter・setter と型定義で、判断がない → CRUD 中心
- ドメイン層というディレクトリがなく、業務ルールがサービスに散っている → 層マップが推定できない扱い（行1）。CRUD 中心とはしない

## 厳しさ

| 設定 | 効果 |
| --- | --- |
| `lenient` | Low と Info を出さない |
| `standard` | 既定 |
| `strict` | borderline も指摘一覧に出す |

導入から2週間（設定の `onboarding_until` まで）は strict を standard として扱い、適合率 0.9 以上のチェックだけを使う。最初に外して信用を失わないため。

## 小規模のときの衝突

v1 で想定している衝突は1つ。CA-BND-01（境界で ORM モデルを使うな、変換層を足せ）と、小規模判定による「層を増やすな」がぶつかる。この場合は規模判定を優先し、CA-BND-01 を Info に下げる。小規模の目安は、行1か行2に当たること。
