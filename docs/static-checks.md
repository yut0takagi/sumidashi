# static チェックの判定規則

checks.yml の criteria を、解析器が実装する粒度まで細かくしたもの。解析器（`tools/sumidashi/checks/`）と評価用の fixtures は、どちらもこの文書に合わせる。食い違いが見つかったら、この文書を直してから両方を合わせる。

## 共通

**対象外のファイル**:
パスに `tests`・`test`・`__tests__` のディレクトリを含むもの、`*.spec.*`・`*.test.*`・`test_*.py`・`*_test.py`・`conftest.py`・`*.d.ts`、`generated`・`node_modules`・`.venv`・`venv`・`dist`・`build`・`migrations` 配下。

**行番号**: 1始まり。location の start_line と end_line は、その構文要素の最初と最後の行。名前の行と書いたものは、識別子のある行（start_line = end_line）。

**型だけの import**:

- TypeScript: `import type { X } from` と、すべての指定子に `type` が付いた `import { type X, type Y } from`。`export type { X } from` も型だけとみなす
- Python: `if TYPE_CHECKING:`（`typing.TYPE_CHECKING` を含む）の中の import

**import の解決**:

- TypeScript: 相対パス（`./`・`../`）と、ルートの tsconfig.json の `baseUrl`・`paths`。拡張子は `.ts` `.tsx` `.js` `.jsx` `.mts` `.cts` を補い、ディレクトリなら `index.*` を探す。`.js` で書かれた import は `.ts` にも読み替える。`require()`・動的 `import()`・`export ... from` も import として扱う
- Python: 相対 import はパッケージの位置から、絶対 import はソースルート（既定は `.` と `src`、設定の `source_roots`）から解決する。`from a.b import c` は `a/b/c.py` を先に探し、なければ `a/b.py`・`a/b/__init__.py` を指す
- 解決できない import は外部パッケージ。パッケージ名は先頭のセグメント（`@scope/name` はスコープ付きの2セグメント）。Python は先頭のモジュール名と、`django.db` のようなサブモジュールの両方で台帳を引く

**層の深さ**: domain・shared が0、application が1、adapter・infrastructure が2、main が3。

**エンティティ**: ドメイン層のクラスで、識別子を持つもの。識別子とは、`id`・`_id`・`#id` という名前のフィールド・コンストラクタの引数プロパティ・getter・property、または `<クラス名の先頭小文字>Id`（Python は `<クラス名のスネークケース>_id`）。ただし名前が Dto・DTO・Props・Input・Output・Command・Query・Event・Error・Exception で終わるクラスと、値オブジェクトの基底を継承するクラスは除く。

**値オブジェクト**: ドメイン層のクラスで、識別子を持たず、次のどれかに当たるもの。名前による除外はエンティティと同じものに Config・Settings を足す。

- 名前に ValueObject を含む型を継承・実装している
- `equals` メソッド（Python は `__eq__`）を持つ
- Python の `@dataclass`・attrs の `@define`・`@frozen`・`@attr.s` が付いている

**ガード**: setter の本体に、`if`・`throw`（Python は `raise`）・`assert`、または名前が assert・validate・ensure・check・guard で始まる関数の呼び出しがあること。

## CA-DEP-01・CA-DEP-03

- 依存元の層が domain（DEP-01）または application（DEP-03）のファイルで、解決先のファイルの層が「依存してよい向き」の表で × になる import を、import 文1つにつき1件出す
- 型だけの import なら borderline、それ以外は violation
- 解決先が層なし（unmapped）なら出さない

## CA-DEP-02

- ドメイン層のファイルの外部パッケージの import を、フレームワーク台帳（`tools/sumidashi/frameworks.py`）で引く
- 分類が web・orm・db・http・cloud・messaging・di・ui・io なら violation。型だけの import でも violation のまま（重大度だけ Medium に下げる）
- 分類が validation なら borderline
- 台帳にない、または allow の分類なら出さない

## CA-DEP-04

- 全ファイルの import（型だけのものを含む）で依存グラフを作り、強連結成分のうち、2つ以上の層のファイルを含むものを循環とする
- 型だけの import の辺を除いたグラフでも、同じファイルたちが2つ以上の層にまたがる強連結成分に残れば violation。残らなければ borderline
- 指摘は循環1つにつき1件。location は、循環の中の辺（両端が同じ強連結成分にある import）のうち、深さの浅い層から深い層へ向かうもの。複数あれば依存元の層の深さ、パス、行の昇順で最初のもの。そうした辺がなければ、層をまたぐ辺のうちパス・行の昇順で最初のもの

## CA-BND-02

- 対象はアプリケーション層の公開関数・公開メソッド。TypeScript は export された関数（アロー関数を含む）と、export されたクラスの private・protected・`#` でないメソッド（コンストラクタを含む）。Python は `_` で始まらない関数とメソッド。`__init__` などの dunder は公開とみなす
- Web フレームワーク（台帳の web）から import した名前が、引数か戻り値の型注釈に単語として出たら、その関数・メソッドにつき1件 violation。location は名前の行
- Web フレームワークから import した文のうち、どの名前も公開シグネチャに出ないものは、import 文1つにつき1件 borderline。ただし DI 用のデコレータ（Injectable・Inject・Module・Optional・forwardRef・Logger）だけの import は出さない

## DDD-ENT-03

対象はエンティティ。次を1メンバーにつき1件出す。

violation:

- TypeScript: アクセス修飾子がないか public で、readonly でも static でもないフィールド。`public` が付き readonly でないコンストラクタの引数プロパティ。ガードのない公開の `set` アクセサ。本体が `this.<名前> = ...` の1文だけの公開メソッド `setXxx`
- Python: frozen でない dataclass・attrs のクラス（`@define`・`@mutable`・`@attr.s`）の、`_` で始まらないフィールド（クラス本体の型注釈つきの宣言）。そうでないクラスの `__init__` で代入する、`_` で始まらない `self.<名前>`（同じ名前は最初の代入だけ）。ガードのない `@<名前>.setter`。本体が `self.<名前> = ...` の1文だけの `set_xxx`

borderline:

- TypeScript: 公開で readonly だが、型が変更できるコレクション（`T[]`・`Array<T>`・`Map`・`Set`・`Record`）のフィールド。`this.<フィールド>` をそのまま返す公開 getter で、そのフィールドか getter の型が変更できるコレクションのもの
- Python: `self._<名前>` をそのまま返す `@property` で、その属性が `__init__` で list・dict・set（リテラル、`list()` などの呼び出し、型注釈）として初期化されているもの

`ReadonlyArray`・`readonly T[]`・`ReadonlyMap`・`ReadonlySet`・`tuple`・`frozenset` は変更できないコレクションとして扱う。

## DDD-VO-02

対象は値オブジェクト。1メンバー（または1文）につき1件出す。

violation:

- TypeScript: 公開で readonly でないフィールド。`public` が付き readonly でない引数プロパティ。`set` アクセサ（公開かどうかを問わない。アクセサ1つで1件とし、その中の代入は別に数えない）。コンストラクタ・`set` アクセサ・static メソッド以外のメソッドの中の `this.<名前>` への代入・複合代入・`++`・`--`（その文の行）。コンストラクタ以外のメソッドの中の `this.<名前>.push(` など配列を変更するメソッドの呼び出し（push・pop・shift・unshift・splice・sort・reverse）
- Python: frozen でない `@dataclass`（デコレータの行）。attrs の `@define`・`@attr.s` で frozen でないもの（デコレータの行）。dataclass でないクラスの `__init__` で代入する、`_` で始まらない `self.<名前>`。`__init__`・`__post_init__`・`__new__`・`__setstate__`・setter・`@staticmethod` 以外のメソッドの中の `self.<名前>` への代入（その文の行）。`@<名前>.setter`（setter 1つで1件とし、その中の代入は別に数えない）

borderline:

- TypeScript: 公開で readonly だが、型が変更できるコレクションのフィールド。private・protected のものは外から触れないので出さない
- Python: frozen な dataclass で、型注釈が `list`・`List`・`dict`・`Dict`・`set`・`Set` のフィールド

## DDD-REP-02

- 対象は、ドメイン層・アプリケーション層にある、名前が Repository・Repo で終わるインターフェース・抽象クラス・クラス
- ORM 名: 台帳の orm・db から import した名前と、`import * as x`・`import x`・`import sqlalchemy as sa` のような名前空間の別名
- 公開メソッドの引数か戻り値の型注釈に ORM 名が単語として出たら、そのメソッドにつき1件 violation（名前の行）
- 継承・実装の対象に ORM 名があれば、その型につき1件 violation（型の名前の行）
- violation でないメソッドで、引数の名前が sql・query・where・filter・raw・rawQuery・condition・conditions のどれかで、型が `string`・`str`・`Record<...>`・`object`・`any`・`unknown`・`dict`・`Dict[...]`・`Mapping[...]` のものがあれば、そのメソッドにつき1件 borderline（名前の行）

## DDD-EVT-01

- 対象: ドメイン層で、名前が Event で終わるクラス・インターフェース・型エイリアス、または名前が Event で終わる型を継承・実装するクラス・インターフェース
- 除外: 名前が Handler・Listener・Subscriber・Bus・Dispatcher・Publisher・Emitter・Store・Queue で終わるもの。基底の型（Event・DomainEvent・BaseEvent・IntegrationEvent・AbstractEvent・EventBase）
- 名前から末尾の Event と、`V2` のような版の接尾辞を除き、キャメルケースで語に分ける（`URLChanged` → URL・Changed）
- 語が1つならその語を、2つ以上なら2語目以降を調べる。どれかが過去分詞なら問題なし
  - 過去分詞: `ed` で終わる語（ただし Feed・Seed・Need・Speed・Bed・Shed・Red・Bread・Thread・Breed・Deed・Weed・Embed・Hundred は除く）、または不規則変化の一覧（Sent・Paid・Built・Made・Held・Sold・Bought・Brought・Taken・Given・Written・Chosen・Frozen・Done・Begun・Run・Won・Lost・Found・Left・Kept・Set・Reset・Put・Cut・Shut・Split・Read・Met・Led・Told・Shown・Known・Drawn・Withdrawn・Seen・Gone・Spent・Bound・Hidden・Broken・Forgotten・Stolen・Spoken・Driven・Overridden・Undone・Rebuilt・Resent など。完全な一覧は実装の `PAST_IRREGULAR`）
- 過去分詞がなく、最後の語が -ion・-ment・-al・-ure・-ance・-ence で終わるなら borderline
- それ以外は violation
- location は型の名前の行
