import { Pool } from "pg";
import { Order } from "../domain/order";
import { OrderRepository } from "../domain/order-repository";

export class PostgresOrderRepository implements OrderRepository {
  private readonly pool = new Pool();

  async findById(id: string): Promise<Order | null> {
    const { rows } = await this.pool.query("select * from orders where id = $1", [id]);
    return rows[0] ? new Order(rows[0].id, rows[0].customer_id) : null;
  }

  async save(order: Order): Promise<void> {
    await this.pool.query("insert into orders (id, customer_id) values ($1, $2)", [
      order.id,
      order.customerId,
    ]);
  }
}
