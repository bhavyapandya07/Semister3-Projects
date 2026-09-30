# API examples

Start the app first. In PowerShell, set reusable values. Replace the example IDs with actual IDs from the seeded database.

```powershell
$api = "http://localhost:5000/api"
$token = "<ACCESS_TOKEN_FROM_LOGIN>"
$headers = @{ Authorization = "Bearer $token" }
$courseId = "<COURSE_OBJECT_ID>"
$studentId = "<STUDENT_OBJECT_ID>"
$enrollmentId = "<ENROLLMENT_OBJECT_ID>"
```

All examples use `curl.exe` (the executable, not PowerShell's `curl` alias).

## Health and authentication

```powershell
curl.exe -i "$api/health"
curl.exe -i -X POST "$api/auth/register" -H "Content-Type: application/json" -d '{"name":"A Student","email":"new.student@srms.edu","password":"A-Long-Password!2026","rollNumber":"R00001"}'
curl.exe -i -c cookies.txt -X POST "$api/auth/login" -H "Content-Type: application/json" -d '{"email":"admin@srms.edu","password":"StudentResult!2026"}'
curl.exe -i -b cookies.txt -c cookies.txt -X POST "$api/auth/refresh"
curl.exe -i -b cookies.txt -X POST "$api/auth/logout"
curl.exe -i "$api/auth/me" -H "Authorization: Bearer $token"
curl.exe -i -X PATCH "$api/auth/password" -H "Authorization: Bearer $token" -H "Content-Type: application/json" -d '{"currentPassword":"StudentResult!2026","newPassword":"An-Even-Longer!2026"}'
```

## Students

```powershell
curl.exe -i "$api/students" -H "Authorization: Bearer $token"
curl.exe -i "$api/students/$studentId" -H "Authorization: Bearer $token"
curl.exe -i -X POST "$api/students" -H "Authorization: Bearer $token" -H "Content-Type: application/json" -d '{"rollNumber":"R03000","name":"New Student","program":"B.Tech","semester":3,"department":"CS"}'
curl.exe -i -X PUT "$api/students/$studentId" -H "Authorization: Bearer $token" -H "Content-Type: application/json" -d '{"name":"Updated Student"}'
curl.exe -i -X DELETE "$api/students/$studentId" -H "Authorization: Bearer $token"
curl.exe -i "$api/students/eligible-for-course/$courseId" -H "Authorization: Bearer $token"
```

## Courses

```powershell
curl.exe -i "$api/courses" -H "Authorization: Bearer $token"
curl.exe -i "$api/courses/$courseId" -H "Authorization: Bearer $token"
curl.exe -i -X POST "$api/courses" -H "Authorization: Bearer $token" -H "Content-Type: application/json" -d '{"code":"CS301","title":"Data Systems","credits":3,"maxMarks":100,"department":"CS","faculty":"<FACULTY_USER_ID>","gradingScheme":"absolute"}'
curl.exe -i -X PUT "$api/courses/$courseId" -H "Authorization: Bearer $token" -H "Content-Type: application/json" -d '{"title":"Updated Course Title"}'
curl.exe -i -X DELETE "$api/courses/$courseId" -H "Authorization: Bearer $token"
```

## Enrollments and CSV

```powershell
curl.exe -i "$api/enrollments/course/$courseId" -H "Authorization: Bearer $token"
curl.exe -i "$api/enrollments/$enrollmentId" -H "Authorization: Bearer $token"
curl.exe -i -X POST "$api/enrollments" -H "Authorization: Bearer $token" -H "Content-Type: application/json" -d '{"student":"<STUDENT_OBJECT_ID>","course":"<COURSE_OBJECT_ID>","semester":4,"assessments":[{"kind":"internal","marks":18,"maxMarks":20},{"kind":"midterm","marks":25,"maxMarks":30},{"kind":"final","marks":40,"maxMarks":50}]}'
curl.exe -i -X PUT "$api/enrollments/$enrollmentId/marks" -H "Authorization: Bearer $token" -H "Content-Type: application/json" -d '{"assessments":[{"kind":"internal","marks":18,"maxMarks":20},{"kind":"midterm","marks":25,"maxMarks":30},{"kind":"final","marks":40,"maxMarks":50}]}'
curl.exe -i -X POST "$api/enrollments/$enrollmentId/publish" -H "Authorization: Bearer $token"
curl.exe -i -X PATCH "$api/enrollments/$enrollmentId/amend" -H "Authorization: Bearer $token" -H "Content-Type: application/json" -d '{"kind":"final","marks":39,"reason":"Approved correction"}'
curl.exe -i -X DELETE "$api/enrollments/$enrollmentId" -H "Authorization: Bearer $token"
curl.exe -i -X POST "$api/enrollments/import" -H "Authorization: Bearer $token" -F "file=@grades.csv"
```

## Reports

```powershell
curl.exe -i "$api/reports/course/$courseId/summary" -H "Authorization: Bearer $token"
curl.exe -i "$api/reports/course/$courseId/histogram" -H "Authorization: Bearer $token"
curl.exe -i "$api/reports/student/$studentId/transcript" -H "Authorization: Bearer $token"
curl.exe -i "$api/reports/toppers?semester=4&limit=10" -H "Authorization: Bearer $token"
curl.exe -i "$api/reports/course/$courseId/toppers?semester=4&limit=10" -H "Authorization: Bearer $token"
curl.exe -i "$api/reports/enrollments-by-month?year=2026" -H "Authorization: Bearer $token"
```
