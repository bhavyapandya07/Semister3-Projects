import bcrypt from "bcryptjs";
import { HydratedDocument, Schema, model } from "mongoose";
import type { Role } from "@srms/shared";

export interface UserShape {
  name: string;
  email: string;
  passwordHash: string;
  role: Role;
  department?: string;
  student?: Schema.Types.ObjectId;
  refreshTokenVersion: number;
  refreshTokenHash?: string;
  isActive: boolean;
  lastLoginAt?: Date;
}
export type UserDocument = HydratedDocument<UserShape>;

const schema = new Schema<UserShape>({
  name: { type: String, required: true, trim: true },
  email: { type: String, required: true, unique: true, lowercase: true, trim: true, match: /^\S+@\S+\.\S+$/ },
  passwordHash: { type: String, required: true, select: false },
  role: { type: String, enum: ["student", "faculty", "hod", "admin"], required: true },
  department: String,
  student: { type: Schema.Types.ObjectId, ref: "Student", unique: true, sparse: true },
  refreshTokenVersion: { type: Number, default: 0 },
  refreshTokenHash: { type: String, select: false },
  isActive: { type: Boolean, default: true },
  lastLoginAt: Date,
}, { timestamps: true });

schema.pre("save", async function () {
  if (!this.isModified("passwordHash")) return;
  this.passwordHash = await bcrypt.hash(this.passwordHash, 12);
});
schema.methods.toJSON = function () {
  const value = this.toObject();
  delete value.passwordHash;
  delete value.refreshTokenHash;
  return value;
};

export const User = model<UserShape>("User", schema);
