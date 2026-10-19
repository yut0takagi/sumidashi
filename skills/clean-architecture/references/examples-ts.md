# clean-architecture の例（TypeScript）

層は `src/domain`・`src/application`・`src/adapters`・`src/infrastructure` に分かれている前提。

## CA-DEP-01 ドメイン層が外側の層に依存している

違反: ドメインのエンティティが、インフラ層のリポジトリ実装を import している。

```ts
// src/domain/order.ts
import { PgOrderRepository } from "../infrastructure/pg-order-repository"; // ← CA-DEP-01

export class Order {
  async reload(repo: PgOrderRepository) { /* ... */ }
}
```

修正: ドメイン層にインターフェースを置き、インフラ層に実装させる。

```ts
// src/domain/order-repository.ts
export interface OrderRepository {
  findById(id: OrderId): Promise<Order | null>;
  save(order: Order): Promise<void>;
}

// src/infrastructure/pg-order-repository.ts
import { OrderRepository } from "../domain/order-repository";
export class PgOrderRepository implements OrderRepository { /* ... */ }
```

`import type { X } from "../infrastructure/..."` のように型だけを参照している場合は borderline（要確認）になる。実行時の依存はないが、ソースの依存は残っている。

## CA-DEP-02 ドメイン層がフレームワーク・ORM・I/O ライブラリに依存している

違反: ドメインのクラスに TypeORM のデコレータが付いている。

```ts
// src/domain/customer.ts
import { Entity, PrimaryColumn, Column } from "typeorm"; // ← CA-DEP-02

@Entity()
export class Customer {
  @PrimaryColumn() id!: string;
  @Column() email!: string;
}
```

修正: 永続化モデルをインフラ層に分け、ドメインの型とはリポジトリ実装の中で変換する。

```ts
// src/domain/customer.ts
export class Customer {
  constructor(private readonly _id: CustomerId, private _email: EmailAddress) {}
}

// src/infrastructure/customer-record.ts
import { Entity, PrimaryColumn, Column } from "typeorm";
@Entity("customers")
export class CustomerRecord { /* ... */ }
```

`zod` や `class-validator` は borderline。業務ルールの表現に使っているのか、外部入力の検証なのかはコードだけでは決まらない。

## CA-DEP-03 アプリケーション層がアダプタ層・インフラ層に依存している

違反:

```ts
// src/application/place-order.ts
import { StripeClient } from "../infrastructure/stripe-client"; // ← CA-DEP-03

export class PlaceOrder {
  private readonly stripe = new StripeClient();
}
```

修正: アプリケーション層にポートを定義し、コンストラクタで受け取る。生成は Main に移す。

```ts
// src/application/ports/payment-gateway.ts
export interface PaymentGateway {
  charge(amount: Money, customerId: CustomerId): Promise<PaymentResult>;
}

// src/application/place-order.ts
export class PlaceOrder {
  constructor(private readonly payments: PaymentGateway) {}
}
```

## CA-DEP-04 層をまたぐ循環依存がある

違反: ドメインとインフラが互いに import している。指摘はドメインからインフラへ向かう import 文に付く。

```ts
// src/domain/order.ts
import { orderTable } from "../infrastructure/schema"; // ← CA-DEP-04（ここに付く）

// src/infrastructure/schema.ts
import { OrderStatus } from "../domain/order";
```

修正: 内側から外側へ向かう import を、ドメイン層に置いたインターフェースへの依存に置き換えるか、両方が使う型を内側に移す。

## CA-BND-02 ユースケースの入出力に HTTP・Web フレームワークの型を使っている

違反: ユースケースが express の Request と Response を受け取っている。

```ts
// src/application/register-user.ts
import { Request, Response } from "express";

export class RegisterUser {
  async execute(req: Request, res: Response): Promise<void> { // ← CA-BND-02
    const user = User.register(req.body.email);
    res.status(201).json({ id: user.id });
  }
}
```

修正: ユースケースの入出力の型をアプリケーション層に定義し、変換をコントローラに移す。

```ts
// src/application/register-user.ts
export type RegisterUserInput = { email: string };
export type RegisterUserOutput = { userId: string };

export class RegisterUser {
  async execute(input: RegisterUserInput): Promise<RegisterUserOutput> { /* ... */ }
}

// src/adapters/http/user-controller.ts
import { Request, Response } from "express";
export async function postUser(req: Request, res: Response) {
  const out = await registerUser.execute({ email: req.body.email });
  res.status(201).json(out);
}
```

import しているが公開シグネチャに出さず本体の中だけで使っている場合は borderline になる。

## CA-BND-03 アプリケーション層が外部 I/O をポートを介さずに直接使っている（draft）

違反:

```ts
// src/application/notify-shipment.ts
import axios from "axios";

export class NotifyShipment {
  async execute(orderId: string) {
    await axios.post("https://hooks.example.com/shipped", { orderId }); // ← CA-BND-03
  }
}
```

修正: `ShipmentNotifier` のようなポートをアプリケーション層に定義し、axios を使う実装をインフラ層に置く。ロガーやトランザクション管理を直接使っている程度なら borderline。

## CA-UC-01 コントローラ・ハンドラに業務ロジックがある（draft）

違反: 送料の計算がコントローラにある。

```ts
// src/adapters/http/checkout-controller.ts
export async function checkout(req: Request, res: Response) {
  const order = await orders.findById(req.params.id);
  const shippingFee = order.total >= 10000 ? 0 : 500; // ← 業務ルール
  // ...
}
```

修正: `order.shippingFee()` のようにドメインへ移し、コントローラは入力の変換とユースケースの呼び出しだけにする。

## CA-BND-01 ORM のモデルがそのまま境界を越えている（draft）

違反: ユースケースが Prisma の生成型をそのまま返している。

```ts
import { User as PrismaUser } from "@prisma/client";

export class GetUser {
  async execute(id: string): Promise<PrismaUser> { /* ... */ }
}
```

修正: 出力用の型をアプリケーション層に定義し、変換はリポジトリ実装で行う。小規模と判定されたプロジェクトでは Info に下がる（層を増やすコストのほうが大きいため）。
