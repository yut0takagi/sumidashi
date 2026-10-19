# clean-architecture の例（Python）

パッケージは `src/shop/domain`・`src/shop/application`・`src/shop/adapters`・`src/shop/infrastructure` に分かれている前提。import の解決は、既定でリポジトリのルートと `src` をソースルートとして扱う。

## CA-DEP-01 ドメイン層が外側の層に依存している

違反:

```python
# src/shop/domain/order.py
from shop.infrastructure.sql_order_repository import SqlOrderRepository  # ← CA-DEP-01


class Order:
    def reload(self, repo: SqlOrderRepository) -> None: ...
```

修正: ドメイン層に抽象を置き、インフラ層に実装させる。

```python
# src/shop/domain/order_repository.py
from typing import Protocol


class OrderRepository(Protocol):
    def get(self, order_id: OrderId) -> Order | None: ...
    def add(self, order: Order) -> None: ...


# src/shop/infrastructure/sql_order_repository.py
from shop.domain.order_repository import OrderRepository


class SqlOrderRepository(OrderRepository): ...
```

`if TYPE_CHECKING:` の中の import だけで参照している場合は borderline（要確認）。

## CA-DEP-02 ドメイン層がフレームワーク・ORM・I/O ライブラリに依存している

違反: ドメインのクラスが SQLAlchemy のモデルを継承している。

```python
# src/shop/domain/customer.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column  # ← CA-DEP-02


class Customer(DeclarativeBase):
    id: Mapped[str] = mapped_column(primary_key=True)
    email: Mapped[str]
```

修正: ドメインの型は素の Python で書き、ORM のマッピングはインフラ層に置く（命令的マッピングか、別のレコード型への変換）。

```python
# src/shop/domain/customer.py
class Customer:
    def __init__(self, customer_id: CustomerId, email: EmailAddress) -> None:
        self._id = customer_id
        self._email = email
```

`requests`・`boto3`・`subprocess` も同じ扱い。`pydantic` は borderline。

## CA-DEP-03 アプリケーション層がアダプタ層・インフラ層に依存している

違反:

```python
# src/shop/application/place_order.py
from shop.infrastructure.stripe_client import StripeClient  # ← CA-DEP-03


class PlaceOrder:
    def __init__(self) -> None:
        self._stripe = StripeClient()
```

修正: アプリケーション層にポートを定義し、コンストラクタで受け取る。

```python
# src/shop/application/ports.py
class PaymentGateway(Protocol):
    def charge(self, amount: Money, customer_id: CustomerId) -> PaymentResult: ...


# src/shop/application/place_order.py
class PlaceOrder:
    def __init__(self, payments: PaymentGateway) -> None:
        self._payments = payments
```

## CA-DEP-04 層をまたぐ循環依存がある

違反: ドメインとインフラが互いに import している。指摘はドメインからインフラへ向かう import に付く。

```python
# src/shop/domain/order.py
from shop.infrastructure.tables import order_table  # ← CA-DEP-04（ここに付く）

# src/shop/infrastructure/tables.py
from shop.domain.order import OrderStatus
```

関数の中で import して実行時の循環を避けていても、ソースの循環は残るので指摘する。`if TYPE_CHECKING:` の import でしか循環しないなら borderline。

## CA-BND-02 ユースケースの入出力に HTTP・Web フレームワークの型を使っている

違反:

```python
# src/shop/application/register_user.py
from fastapi import Request


class RegisterUser:
    async def execute(self, request: Request) -> dict:  # ← CA-BND-02
        body = await request.json()
        ...
```

修正: 入力の型をアプリケーション層に定義し、変換をルート関数に移す。

```python
# src/shop/application/register_user.py
@dataclass(frozen=True)
class RegisterUserInput:
    email: str


class RegisterUser:
    def execute(self, data: RegisterUserInput) -> RegisterUserOutput: ...


# src/shop/adapters/api/users.py
from fastapi import Request


@router.post("/users")
async def post_user(request: Request):
    body = await request.json()
    return register_user.execute(RegisterUserInput(email=body["email"]))
```

Flask の `request` のように、import しているが公開シグネチャに出さないものは borderline。

## CA-BND-03 アプリケーション層が外部 I/O をポートを介さずに直接使っている（draft）

違反:

```python
# src/shop/application/notify_shipment.py
import requests


class NotifyShipment:
    def execute(self, order_id: str) -> None:
        requests.post("https://hooks.example.com/shipped", json={"order_id": order_id})  # ← CA-BND-03
```

修正: `ShipmentNotifier` のポートをアプリケーション層に定義し、requests を使う実装をインフラ層に置く。

## CA-HUM-01 I/O と業務の判断が分離されていない（draft）

違反: 判断の途中で現在時刻と DB を読んでいる。

```python
def can_cancel(order_id: str) -> bool:
    order = repo.get(order_id)
    if order.status == "shipped":
        return False
    return datetime.now() - order.placed_at < timedelta(hours=24)
```

修正: 取得と判断を分け、判断は値を引数に受ける関数（またはドメインのメソッド）にする。

```python
class Order:
    def can_cancel(self, now: datetime) -> bool:
        return self.status != OrderStatus.SHIPPED and now - self.placed_at < timedelta(hours=24)
```
