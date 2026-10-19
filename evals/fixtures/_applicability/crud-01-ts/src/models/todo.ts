import { DataTypes, Model, Sequelize } from "sequelize";

export class Todo extends Model {
  declare id: number;
  declare title: string;
  declare done: boolean;
}

export function initTodo(sequelize: Sequelize): void {
  Todo.init(
    {
      id: { type: DataTypes.INTEGER, autoIncrement: true, primaryKey: true },
      title: { type: DataTypes.STRING, allowNull: false },
      done: { type: DataTypes.BOOLEAN, defaultValue: false },
    },
    { sequelize, tableName: "todos" },
  );
}
