import { Router } from "express";
import { createTodo, deleteTodo, listTodos, updateTodo } from "../services/todo-service";

export const todos = Router();

todos.get("/", async (_req, res) => {
  res.json(await listTodos());
});

todos.post("/", async (req, res) => {
  res.status(201).json(await createTodo(req.body.title));
});

todos.patch("/:id", async (req, res) => {
  const todo = await updateTodo(Number(req.params.id), Boolean(req.body.done));
  if (!todo) return res.sendStatus(404);
  res.json(todo);
});

todos.delete("/:id", async (req, res) => {
  res.sendStatus((await deleteTodo(Number(req.params.id))) ? 204 : 404);
});
