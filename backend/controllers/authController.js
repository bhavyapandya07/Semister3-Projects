const jwt = require("jsonwebtoken");
const User = require("../models/User");

// The JWT deliberately carries only identity + role + department, never a
// list of "owned" courses — ownership is always re-checked against the DB
// per request (see middleware/ownsCourse.js). Baking permissions into the
// token is exactly what this project's spec says not to do.
async function login(req, res) {
  const { email, password } = req.body;
  const user = await User.findOne({ email }).populate("student", "_id");
  if (!user || !(await user.checkPassword(password))) {
    return res.status(401).json({ error: "Invalid credentials" });
  }

  const payload = {
    sub: user._id.toString(),
    role: user.role,
    department: user.department,
    studentId: user.student ? user.student._id.toString() : undefined,
  };

  const token = jwt.sign(payload, process.env.JWT_SECRET, {
    expiresIn: process.env.JWT_EXPIRES_IN || "8h",
  });

  res.json({ token, user: payload });
}

module.exports = { login };
