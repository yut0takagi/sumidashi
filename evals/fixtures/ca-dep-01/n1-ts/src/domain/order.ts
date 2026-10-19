import { v4 as uuid } from "uuid";
import { OrderLine } from "./order-line";
import { Result, ok, err } from "../shared/result";

// 永続化は infrastructure 側のリポジトリ実装が受け持つ
export class Order {
  private readonly lines: OrderLine[] = [];

  private constructor(readonly id: string) {}

  static create(): Order {
    return new Order(uuid());
  }

  addLine(line: OrderLine): Result<void, string> {
    if (this.lines.length >= 20) return err("明細は20行までです");
    this.lines.push(line);
    return ok(undefined);
  }
}
