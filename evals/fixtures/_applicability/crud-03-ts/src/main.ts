import express from "express";
import { userRoutes } from "./presentation/user-routes";

const app = express();
app.use(express.json());
app.use("/users", userRoutes);
app.listen(Number(process.env.PORT ?? 3000));
