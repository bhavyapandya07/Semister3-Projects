const mongoose = require("mongoose");

const assessmentSchema = new mongoose.Schema(
  {
    kind: { type: String, enum: ["internal", "midterm", "final"], required: true },
    marks: { type: Number, required: true, min: 0 },
    maxMarks: { type: Number, required: true },
  },
  { _id: false }
);

const enrollmentSchema = new mongoose.Schema(
  {
    student: { type: mongoose.Schema.Types.ObjectId, ref: "Student", required: true, index: true },
    course: { type: mongoose.Schema.Types.ObjectId, ref: "Course", required: true, index: true },
    semester: { type: Number, required: true },
    assessments: { type: [assessmentSchema], default: [] },
    totalMarks: { type: Number, default: 0 },
    grade: { type: String, default: null },
    // Marks entry is append-only once published (see models/AuditLog.js).
    // Amending a published mark must go through the audit-logged path, never
    // a direct field overwrite.
    published: { type: Boolean, default: false },
    completedAt: { type: Date },
  },
  { timestamps: true }
);

enrollmentSchema.index({ student: 1, course: 1 }, { unique: true });
// Supports enrollments-by-month reports on completedAt/createdAt.
enrollmentSchema.index({ completedAt: 1 });

module.exports = mongoose.model("Enrollment", enrollmentSchema);
