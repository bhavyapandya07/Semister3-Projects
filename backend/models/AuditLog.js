const mongoose = require("mongoose");

// The threat model this exists for: a faculty member amending a mark after
// publication. Every amendment writes one of these instead of mutating
// history silently.
const auditLogSchema = new mongoose.Schema(
  {
    enrollment: { type: mongoose.Schema.Types.ObjectId, ref: "Enrollment", required: true, index: true },
    changedBy: { type: mongoose.Schema.Types.ObjectId, ref: "User", required: true },
    field: { type: String, required: true }, // e.g. "assessments.final.marks"
    oldValue: { type: mongoose.Schema.Types.Mixed },
    newValue: { type: mongoose.Schema.Types.Mixed },
    reason: { type: String, required: true },
  },
  { timestamps: true }
);

module.exports = mongoose.model("AuditLog", auditLogSchema);
