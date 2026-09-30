# Student Result Management System (P4)

This is a TypeScript + Express + MongoDB API and a separate React + TypeScript frontend. `shared/types.ts` is imported by both programs for the HTTP contract. The original supplied project is retained in `reference/`; run the upgraded app from this directory.

## Run on Windows

Prerequisites: Node.js 20 or newer and MongoDB Community Server running locally.

1. Open PowerShell in this `srms` folder (the folder containing this README).
2. Install the workspace dependencies once:

   ```powershell
   npm install
   ```

3. Create the backend environment file:

   ```powershell
   Copy-Item backend\.env.example backend\.env
   ```

   For local development, the example connects to a separate database named `srms_p4`. Set `JWT_SECRET` to a private random value of at least 32 characters before using real data.

4. Create the demo dataset. This clears and recreates the `srms_p4` database, so only run it when you are comfortable resetting this demo database:

   ```powershell
   npm run seed
   ```

5. Start the API and frontend together:

   ```powershell
   npm run dev
   ```

   Keep this window open. The API is at `http://localhost:5000`; the React app is at `http://localhost:5173`. Check the API at [http://localhost:5000/api/health](http://localhost:5000/api/health).

6. Sign in at `http://localhost:5173` with one of these seeded accounts. All demo passwords are `StudentResult!2026`.

   | Role | Email |
   |---|---|
   | Admin | `admin@srms.edu` |
   | HOD | `hod@srms.edu` |
   | Faculty | `faculty1@srms.edu` |
   | Student | `student1@srms.edu` |

Stop the processes with **Ctrl+C**. The database data remains, and next time you only need `npm run dev`; do not seed again unless you want a reset.

## Common commands

```powershell
npm run build
npm test
npm run benchmark:toppers -w backend
```

The benchmark expects the seed dataset with 10,000 enrollment records. To run the concurrency demonstration, start `npm run dev`, upload a 10,000-row CSV from **CSV import**, and request `http://localhost:5000/api/health` from another browser tab or terminal while the import is running. Record the observed response and timing under `evidence/` for submission; no measurements or screenshots are fabricated in this repository.

## CSV format

Header: `rollNumber,courseCode,semester,internal,midterm,final`. Marks are checked per row; allowed maxima are 20, 30, and 50. The import streams rows, processes 500-row batches with `bulkWrite`, reports progress in the API log, and returns row-level failure reasons.

## API outline

| Method and path | Access | Behavior |
|---|---|---|
| `POST /api/auth/register` | Public | Register against an existing student roll number |
| `POST /api/auth/login` | Public, rate limited | Access token plus rotating HttpOnly refresh cookie |
| `POST /api/auth/refresh` | Refresh cookie | Rotate session and issue a new access token |
| `POST /api/auth/logout` | Refresh cookie | Revoke refresh session, return 204 |
| `GET /api/auth/me` | Authenticated | Current account |
| `PATCH /api/auth/password` | Authenticated | Change password and revoke previous sessions |
| `/api/students` | Authenticated; writes admin only | Student CRUD; student reads are own-record only |
| `/api/courses` | Authenticated; writes admin only | Course CRUD |
| `/api/enrollments` | Faculty/HOD/admin, course scoped | Enrollment CRUD, publish, audit-tracked amendment |
| `GET /api/reports/course/:id/summary` | Faculty/HOD/admin, course scoped | One aggregation for count, mean, pass rate, extrema |
| `GET /api/reports/course/:id/histogram` | Faculty/HOD/admin, course scoped | `$bucket` grade histogram |
| `GET /api/reports/student/:id/transcript` | Authenticated; students own only | `$lookup` transcript and weighted GPA |
| `GET /api/reports/toppers?semester=4&limit=10` | Authenticated | Aggregated ranks; students see rank/name only |
| `GET /api/reports/course/:id/toppers` | Enrolled students or course staff | Course ranks with role-based projection |
| `GET /api/reports/enrollments-by-month?year=2026` | Faculty/HOD/admin | Monthly `$group`, zero-filled months |
| `POST /api/enrollments/import` | Faculty/HOD/admin | Streaming CSV bulk import with per-row outcomes |

Every API route has a `curl.exe` example in [`API_EXAMPLES.md`](API_EXAMPLES.md). It includes the auth cookie flow, CRUD verbs, reports, and CSV upload.

## Technical notes

- `backend/src/app.ts` exports the app without listening; only `backend/src/server.ts` calls `listen()`.
- The frontend keeps short-lived access tokens in local storage and refresh tokens in an HttpOnly cookie. See `DESIGN.md` for the XSS/CSRF tradeoff.
- Permission matrix and architecture are in `DESIGN.md`; threat write-up is in `SECURITY.md`; module map is in `MODULES.md`.
- Test source is in `backend/__tests__`. The MongoDB memory-server suite may need network access the first time to obtain its MongoDB binary.

## Verification recorded for this copy

- `npm run build`: passed for shared types, strict TypeScript backend, and React frontend.
- `npm test`: 3 suites and 17 tests passed, including a 10,000-row CSV import with a health request during processing.
- `npm audit`: 0 vulnerabilities at dependency install time.
- Toppers benchmark output is in `evidence/benchmark.md`.
