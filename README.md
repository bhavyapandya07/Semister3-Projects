

# P4 — Student Result Management System

Project Members
- Bhavya Pandya
- Adarsh Madivala
- Avatar Pacharane
- Vaishnavi Magadum
- Sakshi Paradkar

## Setup

```bash
cd backend
npm install
cp .env.example .env        # edit MONGO_URI / JWT_SECRET if needed
npm run seed                # creates users, courses, students, 10k enrollments
npm run dev                 # or: npm start
```

Open `frontend/index.html` directly in a browser (it points at
`http://localhost:5000/api`). Demo logins are printed at the end of the
seed script, password `password123` for all.

Run the benchmark (after seeding):

```bash
npm run benchmark:toppers
```

## Where pipelines live — decision and defense

**Decision: pipelines live in `controllers/reportController.js`, one
function per endpoint, not in the model files and not in a separate
repository layer.**

Why not the model: Mongoose model files in this codebase define shape and
validation (`Student.js`, `Course.js`, `Enrollment.js`) — putting `$lookup`
chains there would make a schema file responsible for cross-collection
business questions ("what's the pass rate"), which is a different concern
than "what does a document look like." It also makes every pipeline a
static method the model has to expose, which doesn't compose well when a
report needs two collections that don't have an obvious "owning" model
(toppers needs `Enrollment` + `Student`; whose static should that be?).

Why not a separate repository module: for CRUD, a repository layer earns
its keep by hiding query mechanics behind a stable interface multiple
callers share. Reports here aren't reused elsewhere — each is hit by
exactly one route — so an extra layer would just be indirection between
the route and the pipeline with no second caller to justify it.

Controllers already are "the place that turns an HTTP request into a
Mongoose call" for every other endpoint in this project (see
`enrollmentController.js`, `studentController.js`). Reports fit the same
description — the pipeline stages *are* the query, in the same sense a
`findById` call is the query for a CRUD route — so putting them in
controllers keeps the codebase's existing convention consistent instead
of introducing a second pattern.

## Proving the pipeline earns its place

`scripts/benchmarkToppers.js` implements toppers twice against the same
10,000-enrollment seed and reports wall-clock time and RSS delta for
each:

- **Pipeline** (`$match` → `$group` → `$sort` → `$limit` → `$lookup`):
  MongoDB does the folding and sorting server-side; Node receives only
  the final 10 rows. Work happens in the database process.
- **`find()` + JS `reduce`**: every matching enrollment document
  (thousands, not 10) is deserialized into a JS object and shipped
  across the wire, then folded and sorted inside the Node process. Work
  happens in the application process, and it scales with the *match*
  size, not the *result* size — this is exactly why the JS approach's
  memory delta grows with dataset size while the pipeline's does not.

Run it yourself; numbers will vary by machine, but the shape of the
result (pipeline: fewer bytes over the wire, flat memory profile;
reduce: proportional-to-N memory and GC pressure) is the point, not a
specific millisecond figure.

## Bulk import without blocking the event loop

`utils/csvImport.js` streams the uploaded file with `csv-parser`
(`fs.createReadStream` → pipe), buffers rows into `BATCH_SIZE`-row
chunks, and writes each chunk with a single `Enrollment.bulkWrite(...,
{ ordered: false })` call. The stream is explicitly paused while a chunk
is being resolved/validated and resumed after, which bounds memory on
very large files and creates natural yield points for the event loop
between chunks — the server keeps answering other requests during an
import (verify with `curl localhost:5000/api/health` in another
terminal while a large import is running).

`ordered: false` means one bad row in a batch doesn't abort the whole
batch. Per-row failures are collected and returned in the response as
`{ row, reason }` rather than failing the request — rejecting the whole
file was rejected as the default because the spec explicitly asks for a
per-row report of what failed and why; only a caller who wants
all-or-nothing semantics would need that, and this project doesn't
require it.

## Grade computation as a class hierarchy

`grading/GradingScheme.js`: an abstract `GradingScheme` base class
(throws if instantiated directly, throws if `computeGrade` isn't
overridden) with two subclasses:

- `AbsoluteGrading` — fixed percentage cutoffs against `maxMarks`.
- `RelativeGrading` — bell-curve cutoffs derived from the cohort's mean
  and standard deviation, so the same raw score can land a different
  letter grade in a hard course vs. an easy one.

`createGradingScheme(kind, maxMarks)` is the one place that branches on
which subclass to build; every caller (`enrollmentController.js`,
`utils/csvImport.js`) just calls `.computeGrade(...)` polymorphically.

## Roles & relationship-based authorization

| Role | May do |
|---|---|
| student | Read only their own transcript, marks, and rank |
| faculty | Read the full roster and enter/amend marks for their **assigned courses only**; read aggregate reports for those courses |
| hod | Everything within their own department |
| admin | CRUD students/courses/assignments; run any report |

`Course.faculty` is a reference. `middleware/ownsCourse.js` loads the
course and compares `course.faculty` against `req.user.sub` for
faculty, or `course.department` against `req.user.department` for hod —
admin bypasses the check entirely. This can't be decided from the JWT
alone by design: the token carries identity + role + department, never
a baked-in list of owned courses, so ownership is always freshly
resolved against the database.

Marks-entry routes are keyed by enrollment id, not course id, so
`middleware/ownsEnrollmentCourse.js` resolves the enrollment's course
first and delegates to the same `ownsCourse` logic — one rule, one
implementation, not two.

**Caching, with an invalidation argument**: `middleware/courseOwnershipCache.js`
caches `courseId -> {facultyId, department}` for 60s to avoid a DB hit on
every single marks-entry request from a faculty member working through
one course's roster. The invalidation contract is narrow and therefore
checkable: the only write that can change a course's ownership is
`courseController.update` (or delete), and both call
`cache.invalidate(courseId)` before responding — that's the only place
staleness could be introduced, and it's covered. A 60s TTL is also a
backstop in case some other write path is added later and forgets to
invalidate.

### The three authorization cases from the spec

1. **IDOR on transcript** — `routes/reports.js` checks
   `req.params.studentId === req.user.studentId` for role `student`
   before the transcript pipeline ever runs, returning 403 on mismatch.
   Also enforced a second time in `studentController.getById` for the
   student CRUD read, since that route exposes the same personal record
   through a different door.

2. **Toppers, subtler case** — same aggregation pipeline for everyone;
   the `$project`/response shape differs by role. `reportController.js`
   builds the full ranked table, then for `role === "student"` maps it
   down to `{rank, name, rollNumber}` for every row except the caller's
   own (which keeps `totalMarks`). A student can never see a
   classmate's marks through this endpoint, only the ranking.

3. **Append-only marks after publication** — `Enrollment.published`
   flips to `true` via `POST /enrollments/:id/publish`. After that,
   `PUT /enrollments/:id/marks` returns 409 and directs the caller to
   `PATCH /enrollments/:id/amend`, which requires a non-empty `reason`,
   writes an `AuditLog` row with the old and new value, and only then
   updates the mark. There is no code path that lets a published mark
   change without leaving that trail.

Bulk import inherits all of this: `utils/csvImport.js` pre-loads the
uploader's own courses once, then checks every row's `courseCode`
against that set before writing it — a row for a course the uploader
doesn't teach is rejected with a reason and the import continues, it
does not abort the file (see "Bulk import" above for why rejecting the
whole file was not the default).

## API surface

| Endpoint | Pipeline / behavior |
|---|---|
| `GET /api/reports/course/:id/summary` | count, average, pass rate, highest, lowest — one `$group` |
| `GET /api/reports/course/:id/histogram` | `$bucket` over grade-band boundaries |
| `GET /api/reports/student/:id/transcript` | `$lookup` + credit-weighted GPA, IDOR-guarded |
| `GET /api/reports/toppers?semester=&limit=` | `$lookup` + `$group` + `$sort`, role-projected |
| `GET /api/reports/course/:id/toppers` | same shape, scoped to one course |
| `GET /api/reports/enrollments-by-month?year=` | `$group` on `$month`, zero-filled in JS |
| `POST /api/enrollments/import` | streaming CSV, `bulkWrite`, per-row auth + error report |

Plus full CRUD on `/api/students`, `/api/courses`, and enrollment
create/marks/publish/amend as described above.

## What's stubbed vs. real

This is a working scaffold, not a polished product: no refresh tokens,
no rate limiting on login, no automated test suite, and the frontend is
a single deliberately plain HTML file (matches the project's own
"hand-rolled CSS bar chart, no charting library" constraint) rather than
a component framework. The parts the spec calls out as "the hard
parts" — pipeline placement, the benchmark, non-blocking bulk import,
the grading class hierarchy, and all three authorization cases — are
fully implemented and are the parts worth reading closely.
