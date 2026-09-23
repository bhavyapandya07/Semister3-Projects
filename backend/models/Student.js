const mongoose = require("mongoose");

const studentSchema = new mongoose.Schema(
  {
    rollNumber: { type: String, required: true, unique: true, index: true },
    name: { type: String, required: true },
    program: { type: String, required: true },
    semester: { type: Number, required: true, min: 1, max: 12 },
    department: { type: String, required: true, index: true },
    // Links this student record to a login user account (for self-service auth checks)
    user: { type: mongoose.Schema.Types.ObjectId, ref: "User" },
  },
  { timestamps: true }
);

module.exports = mongoose.model("Student", studentSchema);
