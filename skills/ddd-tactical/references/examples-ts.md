# ddd-tactical の例（TypeScript）

ドメイン層は `src/domain` にある前提。

## DDD-ENT-03 エンティティの状態を外から直接書き換えられる

違反: 識別子を持つ Order に、公開で readonly でないフィールドと、代入するだけの setter がある。

```ts
// src/domain/order.ts
export class Order {
  constructor(public readonly id: OrderId) {}
  status: OrderStatus = "draft";          // ← DDD-ENT-03（公開の可変フィールド）
  setStatus(s: OrderStatus) {             // ← DDD-ENT-03（代入するだけの setXxx）
    this.status = s;
  }
}
```

修正: フィールドを非公開にし、状態の変更を意図を表すメソッドにする。

```ts
export class Order {
  private _status: OrderStatus = "draft";
  constructor(public readonly id: OrderId) {}

  get status(): OrderStatus { return this._status; }

  confirm(): void {
    if (this._status !== "draft") throw new OrderAlreadyConfirmed(this.id);
    this._status = "confirmed";
  }
}
```

borderline: `readonly lines: OrderLine[]` のように、書き換えはできないが中身が変更できる配列を公開している。`ReadonlyArray<OrderLine>` を返せば問題なし。

## DDD-VO-02 値オブジェクトが可変になっている

違反:

```ts
// src/domain/money.ts
export class Money {
  constructor(public amount: number, public readonly currency: Currency) {} // ← amount が可変
  add(other: Money): void {
    this.amount += other.amount;   // ← DDD-VO-02（コンストラクタ以外での代入）
  }
  equals(other: Money) { return this.amount === other.amount && this.currency === other.currency; }
}
```

修正: すべて readonly にし、変更系のメソッドは新しいインスタンスを返す。

```ts
export class Money {
  constructor(readonly amount: number, readonly currency: Currency) {}
  add(other: Money): Money {
    if (other.currency !== this.currency) throw new CurrencyMismatch();
    return new Money(this.amount + other.amount, this.currency);
  }
}
```

## DDD-REP-02 リポジトリのインターフェースが永続化の技術を表に出している

違反: ドメインのリポジトリが TypeORM の型を受け取っている。

```ts
// src/domain/order-repository.ts
import { FindOptionsWhere } from "typeorm";

export interface OrderRepository {
  find(where: FindOptionsWhere<OrderRecord>): Promise<Order[]>; // ← DDD-REP-02
  save(order: Order): Promise<void>;
}
```

修正: ドメインの言葉で検索の意図を表す。

```ts
export interface OrderRepository {
  findById(id: OrderId): Promise<Order | null>;
  findUnshippedBy(customerId: CustomerId): Promise<Order[]>;
  save(order: Order): Promise<void>;
}
```

borderline: `query(sql: string)` や `find(where: Record<string, unknown>)` のように、生のクエリ条件を受け取る。

## DDD-EVT-01 ドメインイベントの名前が過去形になっていない

```ts
// src/domain/events.ts
export class PlaceOrderEvent extends DomainEvent {}     // ← DDD-EVT-01（命令形）
export class OrderCancellationEvent extends DomainEvent {} // ← borderline（名詞形）
export class OrderPlaced extends DomainEvent {}          // 問題なし
export class ItemAddedToCart extends DomainEvent {}      // 問題なし（2語目以降に過去分詞）
```

修正: 「何が起きたか」を過去形で表す（PlaceOrderEvent → OrderPlaced、OrderCancellationEvent → OrderCancelled）。

## DDD-AGG-01 集約の外から内部エンティティを直接変更している（draft）

違反: アプリケーションサービスが、Order の内部の OrderLine を直接書き換えている。

```ts
// src/application/change-quantity.ts
const order = await orders.findById(orderId);
const line = order.lines.find((l) => l.productId === productId)!;
line.quantity = newQuantity; // ← DDD-AGG-01（合計上限の検証を迂回）
await orders.save(order);
```

修正: 変更をルートのメソッドに移し、ルートで不変条件を確かめる。

```ts
// src/domain/order.ts
changeQuantity(productId: ProductId, quantity: Quantity): void {
  const line = this.lineFor(productId);
  const next = this.totalQuantity() - line.quantity.value + quantity.value;
  if (next > Order.MAX_ITEMS) throw new OrderLimitExceeded(this.id);
  line.changeQuantity(quantity);
}
```

## DDD-AGG-02 集約の不変条件を集約の外で検証している（draft）

違反: 「確定済みの注文には明細を足せない」をサービスで確かめ、Order 自身は確かめていない。

```ts
// src/application/add-item.ts
if (order.status === "confirmed") throw new Error("confirmed");
order.addLine(productId, quantity); // Order.addLine は status を見ない
```

修正: `Order.addLine` の中で状態を確かめ、ドメインの例外を投げる。サービス側の if は消す。

## DDD-VO-01 値オブジェクトが生成時に自分を検証していない（draft）

違反:

```ts
export class EmailAddress {
  constructor(readonly value: string) {} // どんな文字列でも作れる
}
```

修正:

```ts
export class EmailAddress {
  private constructor(readonly value: string) {}
  static of(value: string): EmailAddress {
    if (!/^[^@\s]+@[^@\s]+$/.test(value)) throw new InvalidEmailAddress(value);
    return new EmailAddress(value);
  }
}
```

上の修正のように、コンストラクタを非公開にして検証をファクトリに置く形は borderline（要確認）になる。ファクトリを経由しない生成の道（再構築用のメソッドなど）が残っていないかを人が確かめる。
