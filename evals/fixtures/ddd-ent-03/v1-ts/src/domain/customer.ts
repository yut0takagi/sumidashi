export class Customer {
  constructor(
    readonly id: string,
    public email: string,
    private name: string,
  ) {}

  rename(name: string): void {
    if (name.trim() === "") throw new Error("name is required");
    this.name = name;
  }
}
