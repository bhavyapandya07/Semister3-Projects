# Student Result Management System (SRMS)

Welcome to the **Student Result Management System (SRMS)**! This project is a comprehensive, full-stack web application designed to manage student enrollments, courses, and academic results efficiently. It features a robust role-based access control system catering to Students, Faculty, Head of Departments (HOD), and Administrators.

The application is built using a modern TypeScript stack, with an **Express + MongoDB API** backend and a **React + Vite** frontend. A shared types directory ensures a strict HTTP contract between the client and server.

## 🌟 Key Features

- **Role-Based Access Control (RBAC):** Distinct roles and permissions for Admins, HODs, Faculty, and Students.
- **Secure Authentication:** JWT-based authentication with short-lived access tokens and rotating HttpOnly refresh cookies for enhanced security against XSS and CSRF attacks.
- **Result & Grade Management:** Faculty can manage course enrollments, grade students, and publish results.
- **Bulk CSV Import:** High-performance streaming CSV import for batch uploading student marks. Processes data in chunks and yields to the event loop, ensuring the server remains responsive even during 10,000+ row imports.
- **Advanced Analytics & Reports:** Uses MongoDB Aggregation pipelines to generate course summaries, grade histograms, student transcripts with weighted GPAs, and semester topper lists.
- **Audit Trails:** Comprehensive audit logging for any amendments made to published results.

## 🛠️ Technology Stack

- **Backend:** Node.js, Express.js, TypeScript, MongoDB, Mongoose
- **Frontend:** React, TypeScript, Vite, CSS (Responsive Grid/Flexbox)
- **Shared:** TypeScript interfaces for API requests, responses, and data models.

## 📂 Project Structure

```text
📦 AWT (Workspace Root)
 ┣ 📂 backend/     # Express API, MongoDB models, business logic, and scripts
 ┣ 📂 frontend/    # React SPA built with Vite
 ┣ 📂 shared/      # Shared TypeScript types for API contracts
 ┣ 📜 README.md    # You are here!
 ┣ 📜 DESIGN.md    # Architecture, DB schema, and design decisions
 ┣ 📜 MODULES.md   # Module-to-code map
 ┣ 📜 SECURITY.md  # Threat model and security mechanisms
 ┗ 📜 API_EXAMPLES.md # Example cURL requests for the API
```

## 🚀 Getting Started

Follow these steps to run the project locally on your machine.

### Prerequisites

- **Node.js:** v20 or newer
- **MongoDB:** Community Server running locally (default port `27017`)

### 1. Installation

Open your terminal (PowerShell or Bash) in the root folder of this project (`AWT`) and install all workspace dependencies:

```bash
npm install
```

### 2. Environment Setup

Create the backend environment variables file by copying the example file:

**Windows (PowerShell):**
```powershell
Copy-Item backend\.env.example backend\.env
```
**Mac/Linux:**
```bash
cp backend/.env.example backend/.env
```

*(Note: For local development, the app connects to a local database named `srms_p4`. If you plan to use real data, ensure you change `JWT_SECRET` in `backend/.env` to a strong, random 32+ character string.)*

### 3. Seed Demo Data

Create the demo dataset to easily test the application. 
> ⚠️ **Warning:** This command will clear and recreate the `srms_p4` database. Only run it when you want to reset the demo database.

```bash
npm run seed
```

### 4. Run the Application

Start both the backend API and the frontend development server simultaneously:

```bash
npm run dev
```

Keep this terminal window open. 
- The **Backend API** will run at: `http://localhost:5000` (Health check: [http://localhost:5000/api/health](http://localhost:5000/api/health))
- The **Frontend App** will run at: `http://localhost:5173`

*(To stop the servers, simply press `Ctrl + C` in the terminal.)*

---

## 👥 Usage & Demo Accounts

Navigate to `http://localhost:5173` in your browser. You can sign in using any of the seeded accounts to explore different role perspectives. 

**All demo accounts share the same password:** `StudentResult!2026`

| Role | Email Address | Access Level |
|---|---|---|
| **Admin** | `admin@srms.edu` | Full system access, CRUD for users/courses |
| **HOD** | `hod@srms.edu` | Department-level read/write access |
| **Faculty** | `faculty1@srms.edu` | Course-level management, grading, imports |
| **Student** | `student1@srms.edu` | View own transcript and toppers list |

## 📜 Additional Documentation

For deeper technical insights, please refer to the following documents included in the repository:
- [**DESIGN.md**](./DESIGN.md) - Database schema, authorization matrix, token storage decisions.
- [**MODULES.md**](./MODULES.md) - Module mappings and project-specific complex logic.
- [**SECURITY.md**](./SECURITY.md) - Threat model, rate limiting, and security best practices.
- [**API_EXAMPLES.md**](./API_EXAMPLES.md) - Detailed API routes and `curl` examples.

## ⚡ Common Development Commands

```bash
# Build the backend, frontend, and shared packages
npm run build

# Run the test suites
npm test

# Run the database aggregation benchmark for Toppers (requires seeded DB)
npm run benchmark:toppers -w backend
```
