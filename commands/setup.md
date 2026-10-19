---
description: 設定ファイル・用語集・業務ルール台帳の下書きをコードから作り、確認のうえで書き込む（初回に1回）
argument-hint: ""
---

# /sumidashi:setup

導入時に1回だけ実行する。層マップ・用語集・業務ルール台帳の下書きをコードから作り、利用者は確認して直すだけにする。ADR・用語集・台帳を手で書かせないことが目的。

## 手順

### 1. 作業ディレクトリを作る

```bash
WORK="$(mktemp -d "${TMPDIR:-/tmp}/sumidashi.XXXXXX")"; echo "$WORK"
```

### 2. 層マップと設定ファイルの下書き

```bash
"${CLAUDE_PLUGIN_ROOT}/bin/sumidashi" layers --write-config "$WORK/sumidashi.yml"
```

表示された層ごとのディレクトリと行数、unmapped のディレクトリを利用者に見せ、外れているところを聞く。直す点があれば `$WORK/sumidashi.yml` の `layers` を直す。

下書きには次も入れる。

- `onboarding_until`: 今日から14日後の日付。導入直後は適合率 0.9 以上のチェックだけを使い、strict を使えないようにするため
- `strictness: standard`
- `hooks.pre_pr_check`: `gh pr create` の前に High のチェックだけを簡易実行して警告するか。利用者に聞いて true か false を入れる（ブロックはしない）

### 3. 用語集の下書き

`docs/glossary.yml`（設定の `glossary.path`）がなければ、glossary スキルの「用語集の下書きを作るとき」の手順で `$WORK/glossary.yml` を作る。あればこの段は飛ばす。

### 4. 業務ルール台帳の下書き

`docs/business-rules.yml` がなければ、business スキルの「業務ルール台帳の下書きを作るとき」の手順で `$WORK/business-rules.yml` を作る。あればこの段は飛ばす。

### 5. ADR の確認

```bash
"${CLAUDE_PLUGIN_ROOT}/bin/sumidashi" adr
```

ADR があれば、読み込めたか（形式不明のものがないか）と、`scope`・`exempts` を持つものがいくつあるかを伝える。ADR の書き換えはしない。

### 6. 確認して書き込む

下書き3つの要点（層の対応、用語の数と「要確認」の数、ルールの数と「要確認」の数）を示し、書き込んでよいかを聞く。承認されたものだけを次へ書く。

| 下書き | 書き込み先 |
| --- | --- |
| `$WORK/sumidashi.yml` | `.claude/sumidashi.yml` |
| `$WORK/glossary.yml` | `docs/glossary.yml` |
| `$WORK/business-rules.yml` | `docs/business-rules.yml` |

既にファイルがある場合は上書きしない。差分を見せ、どうするかを聞く。

### 7. 最初のレビュー

書き込みが終わったら、`/sumidashi:review --all` か、直近の差分での `/sumidashi:review` を勧める。

## 守ること

- 利用者が承認するまで、リポジトリにファイルを書かない
- 推測した業務上の意味には「要確認」を付け、事実のように書かない
- 外部への送信はしない
