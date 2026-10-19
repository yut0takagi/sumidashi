import { EntityManager, Repository } from "typeorm";
import { Order } from "../domain/order";
import { OrderRepository, OrderSearchQuery } from "../domain/order-repository";
import { OrderSpecification } from "../domain/order-specification";

export class TypeOrmOrderRepository implements OrderRepository {
  constructor(
    private readonly repo: Repository<Order>,
    private readonly manager: EntityManager,
  ) {}

  findById(id: string): Promise<Order | null> {
    return this.repo.findOneBy({ id });
  }

  async findSatisfying(spec: OrderSpecification): Promise<Order[]> {
    return (await this.repo.find()).filter((o) => spec.isSatisfiedBy(o));
  }

  search(query: OrderSearchQuery): Promise<Order[]> {
    return this.repo.find({ where: { id: query.customerId } });
  }

  async save(order: Order): Promise<void> {
    await this.manager.save(order);
  }
}
