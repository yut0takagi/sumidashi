import { Pool } from "pg";
import { User } from "../domain/user";

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

function toUser(row: { id: number; name: string; email: string; created_at: Date }): User {
  const user = new User();
  user.id = row.id;
  user.name = row.name;
  user.email = row.email;
  user.createdAt = row.created_at;
  return user;
}

export async function selectUsers(limit: number, offset: number): Promise<User[]> {
  const { rows } = await pool.query(
    "select id, name, email, created_at from users order by id limit $1 offset $2",
    [limit, offset],
  );
  return rows.map(toUser);
}

export async function selectUser(id: number): Promise<User | null> {
  const { rows } = await pool.query(
    "select id, name, email, created_at from users where id = $1",
    [id],
  );
  return rows[0] ? toUser(rows[0]) : null;
}

export async function insertUser(name: string, email: string): Promise<User> {
  const { rows } = await pool.query(
    "insert into users (name, email) values ($1, $2) returning id, name, email, created_at",
    [name, email],
  );
  return toUser(rows[0]);
}

export async function updateUser(id: number, name: string, email: string): Promise<User | null> {
  const { rows } = await pool.query(
    "update users set name = $2, email = $3 where id = $1 returning id, name, email, created_at",
    [id, name, email],
  );
  return rows[0] ? toUser(rows[0]) : null;
}

export async function deleteUser(id: number): Promise<boolean> {
  const result = await pool.query("delete from users where id = $1", [id]);
  return (result.rowCount ?? 0) > 0;
}

export async function countUsers(): Promise<number> {
  const { rows } = await pool.query("select count(*)::int as n from users");
  return rows[0].n;
}
