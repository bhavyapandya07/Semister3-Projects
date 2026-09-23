const express = require("express");
const { requireAuth, requireRole } = require("../middleware/auth");
const ctrl = require("../controllers/studentController");

const router = express.Router();
router.use(requireAuth);

router.get("/", requireRole("faculty", "hod", "admin"), ctrl.list);
router.get("/:id", ctrl.getById); // internal IDOR check for role=student
router.post("/", requireRole("admin"), ctrl.create);
router.put("/:id", requireRole("admin"), ctrl.update);
router.delete("/:id", requireRole("admin"), ctrl.remove);

module.exports = router;
