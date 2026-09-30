import { AbsoluteGrading, GradingScheme, RelativeGrading } from "../src/grading/GradingScheme";

describe("grading hierarchy", () => {
  it("keeps the base class abstract", () => { const Base = GradingScheme as unknown as new (maxMarks: number) => GradingScheme; expect(() => new Base(100)).toThrow("abstract"); });
  it("computes fixed absolute grade bands", () => { const scheme = new AbsoluteGrading(100); expect(scheme.computeGrade(95)).toBe("A"); expect(scheme.computeGrade(65)).toBe("D"); });
  it("uses cohort statistics for relative grading", () => { const scheme = new RelativeGrading(100); expect(scheme.computeGrade(100, [50, 60, 70, 80, 90])).toBe("A"); });
});
