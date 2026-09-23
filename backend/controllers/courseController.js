const Course = require("../models/Course");
const cache = require("../middleware/courseOwnershipCache");

async function list(req, res) {
  const filter = req.user.role === "hod" ? { department: req.user.department } : {};
  const courses = await Course.find(filter).populate("faculty", "name email").lean();
  res.json(courses);
}

async function create(req, res) {
  const course = await Course.create(req.body);
  res.status(201).json(course);
}

async function update(req, res) {
  const course = await Course.findByIdAndUpdate(req.params.id, req.body, { new: true });
  if (!course) return res.status(404).json({ error: "Not found" });
  // Faculty (and department) may have just changed — invalidate immediately
  // so ownsCourse never authorizes against a stale cached assignment.
  cache.invalidate(String(course._id));
  res.json(course);
}

async function remove(req, res) {
  const course = await Course.findByIdAndDelete(req.params.id);
  if (!course) return res.status(404).json({ error: "Not found" });
  cache.invalidate(String(course._id));
  res.status(204).end();
}

module.exports = { list, create, update, remove };
