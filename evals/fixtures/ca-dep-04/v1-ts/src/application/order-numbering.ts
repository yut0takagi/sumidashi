import { SequenceTable } from "../infrastructure/sequence-table";

const sequences = new SequenceTable();

export function nextOrderNumber(): string {
  return `ORD-${sequences.next("order").toString().padStart(8, "0")}`;
}
