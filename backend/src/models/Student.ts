import { Schema, model } from "mongoose";
const schema = new Schema({
  rollNumber: { type: String, required: true, unique: true, trim: true },
  name: { type: String, required: true, trim: true },
  program: { type: String, required: true },
  semester: { type: Number, required: true, min: 1, max: 12 },
  department: { type: String, required: true, index: true },
}, { timestamps: true });
export const Student = model("Student", schema);
