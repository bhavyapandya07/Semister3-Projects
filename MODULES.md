# Module-to-code map

| Module | Project evidence |
|---|---|
| 1 — Node.js/event loop | `backend/src/services/import.service.ts` streams CSV and yields during awaited 500-row `bulkWrite` batches; `DESIGN.md` explains the choice. |
| 2 — HTTP | `backend/src/routes/` status behavior, `backend/src/middleware/errors.ts` consistent errors, `backend/src/middleware/requestMetadata.ts` request IDs and API version headers. |
| 3 — MongoDB/Mongoose | `backend/src/models/Student.ts`, `Course.ts`, `Enrollment.ts`, `AuditLog.ts`; references and embedded assessments; `Enrollment` unique index. |
| 4 — MVC | `backend/src/models/`, `services/`, `controllers/`, `routes/`, and `app.ts`/`server.ts` split. Services contain DB/business operations; routes declare guards. |
| 5 — TypeScript | `backend/tsconfig.json` enables `strict`; `shared/types.ts` defines API roles, requests, response shapes, and generic `Page<T>` used from both programs. |
| 6 — React components | `frontend/src/App.tsx`, `auth/ProtectedRoute.tsx`, and separate page components compose the UI; no monolithic App file. |
| 7 — Lists and CSS | `ResultsPage.tsx`, `DashboardPage.tsx`, and `TranscriptPage.tsx` render keyed lists; `frontend/src/style.css` provides responsive grid/flex and chart bars. |
| 8 — Forms/state | `LoginPage.tsx`, `RegisterPage.tsx`, and `MarksPage.tsx` use controlled React state and client validation. |
| 9 — Integration | `frontend/src/api/client.ts` owns all fetch calls and token refresh; `backend/src/app.ts` configures credentialed CORS; pages render loading/error states. |
| 10 — Authentication/authorization | `backend/src/services/auth.service.ts`, `middleware/authenticate.ts`, `middleware/ownership.ts`, `routes/`, and frontend `AuthContext`/`ProtectedRoute`. |

## Project-specific hard parts

- Aggregation-vs-reduce benchmark: `backend/scripts/benchmarkToppers.ts` (`npm run benchmark:toppers -w backend`).
- Streaming, batched CSV import, per-row failures, progress: `backend/src/services/import.service.ts`.
- Grading hierarchy: `backend/src/grading/GradingScheme.ts`; tests in `backend/__tests__/grading.test.ts`.
- Authorization and audit paths: `backend/src/middleware/ownership.ts`, `backend/src/routes/report.routes.ts`, `backend/src/services/enrollment.service.ts`; API/security tests in `backend/__tests__/api.test.ts`.

Record actual benchmark output, CSV health-probe result, and screenshots in `evidence/` before submission; machine-specific evidence is intentionally not invented.
