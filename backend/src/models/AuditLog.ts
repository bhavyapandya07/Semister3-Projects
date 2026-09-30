import { Schema, model } from "mongoose";
const schema = new Schema({
  enrollment: { type: Schema.Types.ObjectId, ref: "Enrollment", required: true, index: true },
  changedBy: { type: Schema.Types.ObjectId, ref: "User", required: true },
  field: { type: String, required: true },
  oldValue: { type: Schema.Types.Mixed, required: true },
  newValue: { type: Schema.Types.Mixed, required: true },
  reason: { type: String, required: true, trim: true },
}, { timestamps: true });
export const AuditLog = model("AuditLog", schema);
