import { Invoice } from "./invoice";

export interface InvoiceRepository {
  findById(id: string): Promise<Invoice | null>;
  search(where: string): Promise<Invoice[]>;
  findByRaw(sql: string, params: unknown[]): Promise<Invoice[]>;
  countBy(filter: Record<string, unknown>): Promise<number>;
  save(invoice: Invoice): Promise<void>;
}
