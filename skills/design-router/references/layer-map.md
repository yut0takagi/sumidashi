# 層マップ

層マップは「どのファイルがどの層に属するか」の対応。clean-architecture の依存チェックも、ddd-tactical のエンティティ・値オブジェクトの推定も、すべてこの上で動く。層マップが外れていると指摘も外れるので、推定結果は最初に利用者に確かめてもらう。

## 層の種類

| 層 | 中身 | 深さ |
| --- | --- | --- |
| `domain` | エンティティ・値オブジェクト・ドメインサービス・ドメインイベント・リポジトリのインターフェース | 0 |
| `shared` | 共有カーネル。どの層から使ってもよい型 | 0 |
| `application` | ユースケース・アプリケーションサービス・ポート | 1 |
| `adapter` | コントローラ・ハンドラ・プレゼンタ・ルート定義 | 2 |
| `infrastructure` | リポジトリ実装・外部 API クライアント・ORM のモデル | 2 |
| `main` | コンポジションルート（依存の組み立て）・起動処理 | 3 |
| `ignore` | 解析しない | ― |

依存してよいのは、深さが同じか浅い層へ向かう import だけ（adapter と infrastructure は互いに依存してよい）。shared は shared 以外に依存しない。詳しい表は `docs/architecture.md` の「層マップ」。

## 自動推定の仕方

1. 設定の `layers`（glob → 層）に当たれば、それに従う
2. パスのディレクトリ名をキーワードに照らす
   - 強いキーワード: domain・application・usecases・use-cases・use_cases・interactors・infrastructure・infra・adapters・presentation など
   - 弱いキーワード: api・handlers・controllers・routes・web・http・db・persistence・gateways など
   - 強いキーワードの中で最もルートに近いものを採る。なければ弱いキーワードの中で最もルートに近いもの
3. どれにも当たらなければ層なし（unmapped）。unmapped のファイルへの import は依存チェックの対象にならない

`src/order/domain/model/order.ts` は domain、`src/application/handlers/x.ts` は application（強いキーワードが勝つ）、`src/api/domain/x.ts` は domain になる。

`models`・`services`・`repositories`・`app`・`core`・`lib` は、プロジェクトによって意味が違うのでキーワードにしていない。Django の `models.py` は ORM、Next.js の `app/` はルーティング、というように取り違えやすいため。

## 推定できるかの判定

domain が見つかり、さらに domain・application・adapter・infrastructure のうち2つ以上が見つかれば「推定できる」。推定できないときは、CA-DEP 系だけを重大度を1段下げて走らせ、ddd-tactical は走らせない。

## 推定を確かめる

```bash
"${CLAUDE_PLUGIN_ROOT}/bin/sumidashi" layers
```

層ごとのディレクトリと行数、unmapped のディレクトリが出る。利用者に見せて、外れているところを聞く。

## 推定を直す

`.claude/sumidashi.yml` の `layers` に glob を書く。設定は自動推定より優先する。

```yaml
layers:
  src/core/**: domain
  src/services/**: application
  src/routes/**: adapter
  src/db/**: infrastructure
  src/main.ts: main
  src/legacy/**: ignore
```

`/sumidashi:setup` を実行すると、自動推定の結果をこの形の下書きにして見せる。利用者が確かめてから書き込む。

## 複数のコンテキストがあるとき

モジュラーモノリスで `src/<コンテキスト>/<層>/` のように並んでいれば、自動推定でそのまま層が取れる（コンテキスト名がキーワードと重ならない限り）。コンテキストの境界の正しさ（ddd-strategic）は v3 で扱う。いまはコンテキストをまたぐ import を指摘しない。
