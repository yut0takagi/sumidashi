import { RoomId } from "@/domain/room-id";
import { SystemClock } from "@/infrastructure/clock/system-clock";

export class Reservation {
  private constructor(
    readonly id: string,
    readonly roomId: RoomId,
    readonly reservedAt: Date,
  ) {}

  static reserve(id: string, roomId: RoomId): Reservation {
    return new Reservation(id, roomId, new SystemClock().now());
  }
}
