import axios from "axios";

export class BillingClient {
  async charge(subscriptionId: string): Promise<void> {
    await axios.post(`https://billing.example.com/charge/${subscriptionId}`);
  }
}
