# Security notes and checks

## NoSQL injection

An unsafe query such as `User.findOne(req.body)` could interpret `{ "email": { "$ne": null } }` as a MongoDB operator and match an unintended account. This project parses request bodies through Zod schemas, then uses explicit fields such as `email.toLowerCase()` in fixed queries. It never passes a request object directly into a MongoDB filter.

## Mass assignment

Updates are parsed against resource-specific schemas and run Mongoose validators. User role, password hash, refresh hash, token version, and activation state are not accepted by public registration or ordinary resource edit shapes. Only the authenticated password-change service changes password hashes; hashing occurs in the model's guarded `pre('save')` hook.

## IDOR transcript check

Use a valid student bearer token and request another student's transcript:

```powershell
curl.exe -i -H "Authorization: Bearer <STUDENT_ACCESS_TOKEN>" http://localhost:5000/api/reports/student/<OTHER_STUDENT_ID>/transcript
```

Expected after the guard: `403 Forbidden`. The route middleware checks the linked student id before calling the aggregation service. For an own-record control, replace the id with the authenticated student's id; it should return 200. The same rule protects `GET /api/students/:id` and enrollment reads.

## Authentication, session, and logs

- Passwords use bcryptjs cost 12 and are hashed in a guarded model hook; login returns the same 401 message for unknown email and wrong password.
- Login is limited to 5 attempts per IP per 15 minutes. Refresh cookies are HttpOnly, SameSite=Lax, rotated on refresh, versioned, and stored server-side only as a bcrypt hash. Access JWTs expire in 15 minutes and check the account's token version on every authenticated request.
- Password changes clear the refresh hash and increment the version, invalidating prior access and refresh tokens.
- Request logging records request id, status, and elapsed time only. It does not log credentials, tokens, or request bodies.
- Authorization is enforced in API middleware. Hiding frontend navigation is only a usability feature.

## Remaining deployment work

This is a local course project, not a hardened public deployment. Use HTTPS, a strong private `JWT_SECRET`, `COOKIE_SECURE=true`, restrictive network/database access, and review rate-limit storage for multi-instance hosting. The test suite includes 401/403, IDOR, expired/tampered tokens, password-change invalidation, CRUD, duplicate 409, validation 422, report pipeline, and grading tests. Run it locally before submission and attach actual output/screenshots to `evidence/`; expected results above are not a captured test transcript.
