const Student = require("../models/Student");

async function list(req, res) {
  const filter = req.user.role === "hod" ? { department: req.user.department } : {};
  const students = await Student.find(filter).lean();
  res.json(students);
}

async function getById(req, res) {
  // IDOR guard: a student may only ever read their own record. This is
  // enforced here in addition to the transcript endpoint because this
  // route exposes program/semester/department too.
  if (req.user.role === "student" && req.params.id !== req.user.studentId) {
    return res.status(403).json({ error: "You may only view your own record" });
  }
  const student = await Student.findById(req.params.id).lean();
  if (!student) return res.status(404).json({ error: "Not found" });
  if (req.user.role === "hod" && student.department !== req.user.department) {
    return res.status(403).json({ error: "Outside your department" });
  }
  res.json(student);
}

async function create(req, res) {
  const student = await Student.create(req.body);
  res.status(201).json(student);
}

async function update(req, res) {
  const student = await Student.findByIdAndUpdate(req.params.id, req.body, { new: true });
  if (!student) return res.status(404).json({ error: "Not found" });
  res.json(student);
}

async function remove(req, res) {
  const student = await Student.findByIdAndDelete(req.params.id);
  if (!student) return res.status(404).json({ error: "Not found" });
  res.status(204).end();
}

module.exports = { list, getById, create, update, remove };
