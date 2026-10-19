import { User } from "../domain/user";
import {
  countUsers,
  deleteUser,
  insertUser,
  selectUser,
  selectUsers,
  updateUser,
} from "../infrastructure/user-table";

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  perPage: number;
}

export async function listUsers(page: number, perPage: number): Promise<Page<User>> {
  const [items, total] = await Promise.all([
    selectUsers(perPage, (page - 1) * perPage),
    countUsers(),
  ]);
  return { items, total, page, perPage };
}

export function getUser(id: number): Promise<User | null> {
  return selectUser(id);
}

export function createUser(name: string, email: string): Promise<User> {
  return insertUser(name.trim(), email.trim().toLowerCase());
}

export function editUser(id: number, name: string, email: string): Promise<User | null> {
  return updateUser(id, name.trim(), email.trim().toLowerCase());
}

export function removeUser(id: number): Promise<boolean> {
  return deleteUser(id);
}
