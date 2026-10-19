import express from "express";
import { todos } from "./routes/todos";

export const app = express();
app.use(express.json());
app.use("/todos", todos);
