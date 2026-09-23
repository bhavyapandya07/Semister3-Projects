const mongoose = require("mongoose");

const courseSchema = new mongoose.Schema(
  {
    code: { type: String, required: true, unique: true, index: true },
    title: { type: String, required: true },
    credits: { type: Number, required: true, min: 1 },
    maxMarks: { type: Number, required: true, default: 100 },
    department: { type: String, required: true, index: true },
    // The relationship that authorization hinges on: "faculty may enter marks
    // for courses they teach" is decided by comparing this field, not the JWT.
    faculty: { type: mongoose.Schema.Types.ObjectId, ref: "User", required: true, index: true },
    gradingScheme: {
      type: String,
      enum: ["absolute", "relative"],
      default: "absolute",
    },
  },
  { timestamps: true }
);

module.exports = mongoose.model("Course", courseSchema);
