import { DomainEvent } from "./domain-event";

export class UserLoggedIn extends DomainEvent {
  constructor(readonly userId: string) {
    super();
  }
}

export class PasswordReset extends DomainEvent {
  constructor(readonly userId: string) {
    super();
  }
}
