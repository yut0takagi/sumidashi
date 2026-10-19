import { Entity, PrimaryColumn, Column } from "typeorm";

@Entity("subscriptions")
export class SubscriptionTable {
  @PrimaryColumn()
  id!: string;

  @Column()
  expiresAt!: Date;
}
