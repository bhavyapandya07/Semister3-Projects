/**
 * Abstract base. Subclasses decide HOW a numeric score becomes a letter
 * grade; callers never branch on scheme type themselves — that branching
 * lives once, in the factory at the bottom of this file.
 */
class GradingScheme {
  constructor(maxMarks) {
    if (new.target === GradingScheme) {
      throw new Error("GradingScheme is abstract and cannot be instantiated directly");
    }
    this.maxMarks = maxMarks;
  }

  /**
   * @param {number} totalMarks - this student's score
   * @param {number[]} [courseMarks] - every student's totalMarks in the course,
   *   only required by schemes that grade on a curve
   * @returns {string} letter grade
   */
  // eslint-disable-next-line no-unused-vars
  computeGrade(totalMarks, courseMarks) {
    throw new Error("computeGrade() must be implemented by a subclass");
  }
}

/**
 * Fixed cutoffs against maxMarks. No knowledge of how anyone else scored.
 */
class AbsoluteGrading extends GradingScheme {
  static CUTOFFS = [
    { min: 0.9, grade: "A" },
    { min: 0.8, grade: "B" },
    { min: 0.7, grade: "C" },
    { min: 0.6, grade: "D" },
    { min: 0.0, grade: "F" },
  ];

  computeGrade(totalMarks) {
    const pct = totalMarks / this.maxMarks;
    const band = AbsoluteGrading.CUTOFFS.find((c) => pct >= c.min);
    return band.grade;
  }
}

/**
 * Grades on a curve: cutoffs are derived from this cohort's mean/stddev
 * (a standard bell-curve scheme), so the SAME raw score can produce a
 * different letter grade in a hard course vs an easy one.
 */
class RelativeGrading extends GradingScheme {
  static BANDS = [
    { z: 1.0, grade: "A" },
    { z: 0.25, grade: "B" },
    { z: -0.25, grade: "C" },
    { z: -1.0, grade: "D" },
    { z: -Infinity, grade: "F" },
  ];

  computeGrade(totalMarks, courseMarks) {
    if (!courseMarks || courseMarks.length < 2) {
      // Not enough cohort data to curve against; fall back to absolute.
      return new AbsoluteGrading(this.maxMarks).computeGrade(totalMarks);
    }
    const mean = courseMarks.reduce((a, b) => a + b, 0) / courseMarks.length;
    const variance =
      courseMarks.reduce((a, b) => a + (b - mean) ** 2, 0) / courseMarks.length;
    const stddev = Math.sqrt(variance) || 1; // avoid divide-by-zero if uniform
    const z = (totalMarks - mean) / stddev;
    const band = RelativeGrading.BANDS.find((b) => z >= b.z);
    return band.grade;
  }
}

function createGradingScheme(kind, maxMarks) {
  switch (kind) {
    case "relative":
      return new RelativeGrading(maxMarks);
    case "absolute":
    default:
      return new AbsoluteGrading(maxMarks);
  }
}

module.exports = { GradingScheme, AbsoluteGrading, RelativeGrading, createGradingScheme };
