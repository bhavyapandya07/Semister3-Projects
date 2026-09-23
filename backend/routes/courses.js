const express = require("express");
const { requireAuth, requireRole } = require("../middleware/auth");
const ctrl = require("../controllers/courseController");

const router = express.Router();
router.use(requireAuth);

router.get("/", ctrl.list);
router.post("/", requireRole("admin"), ctrl.create);
router.put("/:id", requireRole("admin"), ctrl.update);
router.delete("/:id", requireRole("admin"), ctrl.remove);

module.exports = router;
