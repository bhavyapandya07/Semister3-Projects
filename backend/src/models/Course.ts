import { Schema, model } from "mongoose";
const schema = new Schema({
  code: { type: String, required: true, unique: true, uppercase: true, trim: true },
  title: { type: String, required: true, trim: true },
  credits: { type: Number, required: true, min: 1 },
  maxMarks: { type: Number, required: true, min: 1 },
  department: { type: String, required: true, index: true },
  faculty: { type: Schema.Types.ObjectId, ref: "User", required: true, index: true },
  gradingScheme: { type: String, enum: ["absolute", "relative"], default: "absolute" },
}, { timestamps: true });
export const Course = model("Course", schema);
