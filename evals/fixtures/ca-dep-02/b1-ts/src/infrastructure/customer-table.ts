import { Entity, PrimaryColumn, Column } from "typeorm";

@Entity("customers")
export class CustomerTable {
  @PrimaryColumn()
  id!: string;

  @Column()
  email!: string;
}
