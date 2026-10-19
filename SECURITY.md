# セキュリティ

## 対応するバージョン

修正は最新のリリース（いまは 0.1.x）にだけ入れる。

## 脆弱性を報告する

脆弱性は公開の Issue に書かず、GitHub の非公開の報告で送る。リポジトリの「Security」タブで「Report a vulnerability」を押すと、管理者にだけ見える報告を作れる。手順は [GitHub のドキュメント](https://docs.github.com/ja/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability) にある。

報告には、再現の手順と、影響を受けるバージョンを書いてほしい。

sumidashi は、レビューするリポジトリのコードを読み、`git` を呼び出し、承認されたときだけファイルを書く。次のような問題は脆弱性として扱う。

- レビューするリポジトリの中身によって、解析器やフックが意図しないコマンドを実行する
- 承認なしにファイルを書き換える、または対象のリポジトリの外に書き込む
- コードや解析結果を外部に送る
