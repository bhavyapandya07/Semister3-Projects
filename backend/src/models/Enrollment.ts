import { Schema, model } from "mongoose";
const assessment = new Schema({
  kind: { type: String, enum: ["internal", "midterm", "final"], required: true },
  marks: { type: Number, required: true, min: 0 },
  maxMarks: { type: Number, required: true, min: 1 },
}, { _id: false });
const schema = new Schema({
  student: { type: Schema.Types.ObjectId, ref: "Student", required: true, index: true },
  course: { type: Schema.Types.ObjectId, ref: "Course", required: true, index: true },
  semester: { type: Number, required: true, min: 1, max: 12 },
  assessments: { type: [assessment], default: [] },
  totalMarks: { type: Number, default: 0 },
  grade: { type: String, default: null },
  published: { type: Boolean, default: false },
  completedAt: Date,
}, { timestamps: true });
schema.index({ student: 1, course: 1 }, { unique: true });
schema.index({ completedAt: 1 });
export const Enrollment = model("Enrollment", schema);
