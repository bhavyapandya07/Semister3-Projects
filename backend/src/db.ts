import mongoose from "mongoose";
export async function connectDB(uri = process.env.MONGO_URI) {
  if (!uri) throw new Error("MONGO_URI is required");
  await mongoose.connect(uri);
}
