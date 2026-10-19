import { Todo } from "../models/todo";

export async function listTodos(): Promise<Todo[]> {
  return Todo.findAll({ order: [["id", "ASC"]] });
}

export async function createTodo(title: string): Promise<Todo> {
  return Todo.create({ title });
}

export async function updateTodo(id: number, done: boolean): Promise<Todo | null> {
  const todo = await Todo.findByPk(id);
  if (!todo) return null;
  todo.done = done;
  await todo.save();
  return todo;
}

export async function deleteTodo(id: number): Promise<boolean> {
  return (await Todo.destroy({ where: { id } })) > 0;
}
