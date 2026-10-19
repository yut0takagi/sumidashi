import { Repository } from "typeorm";
import { Product } from "./product";

export interface ProductRepository extends Repository<Product> {
  findBySku(sku: string): Promise<Product | null>;
}
