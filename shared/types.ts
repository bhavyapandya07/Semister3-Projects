export type Role = "student" | "faculty" | "hod" | "admin";

export interface SessionUser {
  id: string;
  name: string;
  email: string;
  role: Role;
  department?: string;
  studentId?: string;
}

export interface ApiError {
  error: string;
  details?: unknown;
}

export interface AssessmentInput {
  kind: "internal" | "midterm" | "final";
  marks: number;
  maxMarks: number;
}

export interface CreateEnrollmentInput {
  student: string;
  course: string;
  semester: number;
  assessments: AssessmentInput[];
}

export interface CourseSummary {
  count: number;
  average: number;
  passRate: number;
  highest: number;
  lowest: number;
}

export interface Transcript {
  courses: Array<{
    courseCode: string;
    courseTitle: string;
    credits: number;
    semester: number;
    totalMarks: number;
    grade: string;
  }>;
  gpa: number;
}

export interface Page<T> { items: T[]; total: number; page: number; pageSize: number; }
export interface ApiResult<T> { data: T; requestId?: string; }
