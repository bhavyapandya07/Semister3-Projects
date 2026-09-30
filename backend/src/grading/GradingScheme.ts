export abstract class GradingScheme {
  constructor(protected readonly maxMarks: number) {
    if (new.target === GradingScheme) throw new Error("GradingScheme is abstract");
  }
  abstract computeGrade(total: number, cohort?: number[]): string;
}

export class AbsoluteGrading extends GradingScheme {
  override computeGrade(total: number): string {
    const pct = total / this.maxMarks;
    if (pct >= 0.9) return "A";
    if (pct >= 0.8) return "B";
    if (pct >= 0.7) return "C";
    if (pct >= 0.6) return "D";
    return "F";
  }
}

export class RelativeGrading extends GradingScheme {
  override computeGrade(total: number, cohort: number[] = []): string {
    if (cohort.length < 2) return new AbsoluteGrading(this.maxMarks).computeGrade(total);
    const mean = cohort.reduce((a, b) => a + b, 0) / cohort.length;
    const sd = Math.sqrt(cohort.reduce((s, x) => s + (x - mean) ** 2, 0) / cohort.length) || 1;
    const z = (total - mean) / sd;
    if (z >= 1) return "A";
    if (z >= 0.25) return "B";
    if (z >= -0.25) return "C";
    if (z >= -1) return "D";
    return "F";
  }
}

export function createGradingScheme(kind: string, maxMarks: number): GradingScheme {
  return kind === "relative" ? new RelativeGrading(maxMarks) : new AbsoluteGrading(maxMarks);
}
