# ddd-tactical の例（Python）

ドメイン層は `src/shop/domain` にある前提。

## DDD-ENT-03 エンティティの状態を外から直接書き換えられる

違反: 識別子を持つ Order が、公開属性と代入するだけの setter を持っている。

```python
# src/shop/domain/order.py
class Order:
    def __init__(self, order_id: OrderId) -> None:
        self.id = order_id          # ← DDD-ENT-03
        self.status = "draft"       # ← DDD-ENT-03

    def set_status(self, status: str) -> None:  # ← DDD-ENT-03（代入するだけ）
        self.status = status
```

frozen でない dataclass の公開フィールドも同じ扱い。

```python
@dataclass
class Order:
    id: OrderId
    status: str = "draft"           # ← DDD-ENT-03
```

修正: 属性を `_` 始まりにし、読み取りは property、変更は意図を表すメソッドにする。

```python
class Order:
    def __init__(self, order_id: OrderId) -> None:
        self._id = order_id
        self._status = OrderStatus.DRAFT

    @property
    def id(self) -> OrderId:
        return self._id

    def confirm(self) -> None:
        if self._status is not OrderStatus.DRAFT:
            raise OrderAlreadyConfirmed(self._id)
        self._status = OrderStatus.CONFIRMED
```

borderline: `self._lines = []` をそのまま返す `@property def lines(self)`。`tuple(self._lines)` を返せば問題なし。

## DDD-VO-02 値オブジェクトが可変になっている

違反:

```python
# src/shop/domain/money.py
@dataclass                          # ← DDD-VO-02（frozen でない dataclass）
class Money:
    amount: Decimal
    currency: str

    def add(self, other: "Money") -> None:
        self.amount += other.amount  # ← DDD-VO-02（__init__ 以外での代入）
```

修正:

```python
@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def add(self, other: "Money") -> "Money":
        if other.currency != self.currency:
            raise CurrencyMismatch(self.currency, other.currency)
        return Money(self.amount + other.amount, self.currency)
```

borderline: frozen でも `tags: list[str]` のように中身が変更できる型のフィールドがある。`tuple[str, ...]` か `frozenset` にする。

## DDD-REP-02 リポジトリのインターフェースが永続化の技術を表に出している

違反:

```python
# src/shop/domain/order_repository.py
from sqlalchemy.orm import Session
from sqlalchemy import Select


class OrderRepository(Protocol):
    def find(self, stmt: Select) -> list[Order]: ...       # ← DDD-REP-02
    def save(self, order: Order, session: Session) -> None: ...  # ← DDD-REP-02
```

Django の `QuerySet` を返すメソッドも同じ扱い。

修正: ドメインの型と識別子だけでインターフェースを定義する。Session の受け渡しはインフラ層の Unit of Work に閉じ込める。

```python
class OrderRepository(Protocol):
    def get(self, order_id: OrderId) -> Order | None: ...
    def list_unshipped(self, customer_id: CustomerId) -> list[Order]: ...
    def add(self, order: Order) -> None: ...
```

borderline: `def search(self, where: dict) -> list[Order]` のように生のクエリ条件を受け取る。

## DDD-EVT-01 ドメインイベントの名前が過去形になっていない

```python
class PlaceOrderEvent(DomainEvent): ...     # ← DDD-EVT-01（命令形）
class OrderShippingEvent(DomainEvent): ...  # ← DDD-EVT-01（進行形）
class PaymentApprovalEvent(DomainEvent): ... # ← borderline（名詞形）
class OrderPlaced(DomainEvent): ...         # 問題なし
class UserLoggedIn(DomainEvent): ...        # 問題なし
```

## DDD-AGG-01 集約の外から内部エンティティを直接変更している（draft）

違反:

```python
# src/shop/application/change_quantity.py
order = orders.get(order_id)
line = next(l for l in order.lines if l.product_id == product_id)
line.quantity = new_quantity  # ← DDD-AGG-01（ルートの上限チェックを迂回）
```

修正: `order.change_quantity(product_id, new_quantity)` をルートに用意し、上限の検証をそこで行う。

## DDD-AGG-02 集約の不変条件を集約の外で検証している（draft）

違反:

```python
# src/shop/application/add_item.py
if order.status == "confirmed":
    raise ValueError("confirmed")
order.add_line(product_id, quantity)  # add_line は status を見ない
```

修正: `Order.add_line` の中で状態を確かめ、ドメインの例外を投げる。

## DDD-VO-01 値オブジェクトが生成時に自分を検証していない（draft）

違反:

```python
@dataclass(frozen=True)
class Quantity:
    value: int   # 0 以下でも作れる
```

修正:

```python
@dataclass(frozen=True)
class Quantity:
    value: int

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise InvalidQuantity(self.value)
```
