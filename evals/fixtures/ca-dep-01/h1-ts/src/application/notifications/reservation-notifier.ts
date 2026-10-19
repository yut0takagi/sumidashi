import { Reservation } from "@/domain/reservation";

export class ReservationNotifier {
  notify(reservation: Reservation): string {
    return `reserved: ${reservation.id}`;
  }
}
