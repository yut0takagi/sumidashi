import type { Contact } from "@prisma/client";
import { prisma } from "../prisma/client";

export class ContactService {
  findAll(): Promise<Contact[]> {
    return prisma.contact.findMany();
  }

  findOne(id: number): Promise<Contact | null> {
    return prisma.contact.findUnique({ where: { id } });
  }

  create(name: string, email: string): Promise<Contact> {
    return prisma.contact.create({ data: { name, email } });
  }

  update(id: number, data: Partial<Pick<Contact, "name" | "email">>): Promise<Contact> {
    return prisma.contact.update({ where: { id }, data });
  }

  remove(id: number): Promise<Contact> {
    return prisma.contact.delete({ where: { id } });
  }
}
