require("dotenv").config();
const express = require("express");
const connectDB = require("./config/db");

const authRoutes = require("./routes/auth");
const studentRoutes = require("./routes/students");
const courseRoutes = require("./routes/courses");
const enrollmentRoutes = require("./routes/enrollments");
const reportRoutes = require("./routes/reports");

const app = express();
app.use(express.json());

app.get("/api/health", (req, res) => res.json({ ok: true }));
app.use("/api/auth", authRoutes);
app.use("/api/students", studentRoutes);
app.use("/api/courses", courseRoutes);
app.use("/api/enrollments", enrollmentRoutes);
app.use("/api/reports", reportRoutes);

// central error handler
app.use((err, req, res, next) => {
  console.error(err);
  res.status(err.status || 500).json({ error: err.message || "Internal server error" });
});

const PORT = process.env.PORT || 5000;

connectDB()
  .then(() => app.listen(PORT, () => console.log(`[server] listening on :${PORT}`)))
  .catch((err) => {
    console.error("[db] connection failed", err);
    process.exit(1);
  });

module.exports = app;
