import { type ReorderSettings, type SupplierLeadTime } from "../application/reorder-settings";
import { Inventory } from "./inventory";

export function needsReorder(
  inventory: Inventory,
  settings: ReorderSettings,
  leadTime: SupplierLeadTime,
): boolean {
  return inventory.available() < settings.minimum + leadTime.days * settings.dailyDemand;
}
