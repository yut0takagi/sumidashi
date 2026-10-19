import { IssueInvoice } from "../application/issue-invoice";

export async function handleIssue(useCase: IssueInvoice, id: string, amount: number) {
  const invoice = await useCase.execute(id, amount);
  return { id: invoice.id };
}
