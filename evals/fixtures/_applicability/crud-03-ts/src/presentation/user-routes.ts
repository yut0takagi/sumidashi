import { Router } from "express";
import { createUser, editUser, getUser, listUsers, removeUser } from "../application/user-service";

export const userRoutes = Router();

userRoutes.get("/", async (req, res) => {
  const page = Number(req.query.page ?? 1);
  const perPage = Math.min(Number(req.query.perPage ?? 20), 100);
  res.json(await listUsers(page, perPage));
});

userRoutes.get("/:id", async (req, res) => {
  const user = await getUser(Number(req.params.id));
  if (!user) return res.sendStatus(404);
  res.json(user);
});

userRoutes.post("/", async (req, res) => {
  const { name, email } = req.body ?? {};
  if (typeof name !== "string" || typeof email !== "string") {
    return res.status(400).json({ error: "name and email are required" });
  }
  res.status(201).json(await createUser(name, email));
});

userRoutes.put("/:id", async (req, res) => {
  const { name, email } = req.body ?? {};
  if (typeof name !== "string" || typeof email !== "string") {
    return res.status(400).json({ error: "name and email are required" });
  }
  const user = await editUser(Number(req.params.id), name, email);
  if (!user) return res.sendStatus(404);
  res.json(user);
});

userRoutes.delete("/:id", async (req, res) => {
  res.sendStatus((await removeUser(Number(req.params.id))) ? 204 : 404);
});
