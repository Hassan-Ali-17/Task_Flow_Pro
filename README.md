<div align="center">

```
████████╗ █████╗ ███████╗██╗  ██╗  ███████╗██╗      ██████╗ ██╗    ██╗
╚══██╔══╝██╔══██╗██╔════╝██║ ██╔╝  ██╔════╝██║     ██╔═══██╗██║    ██║
   ██║   ███████║███████╗█████╔╝   █████╗  ██║     ██║   ██║██║ █╗ ██║
   ██║   ██╔══██║╚════██║██╔═██╗   ██╔══╝  ██║     ██║   ██║██║███╗██║
   ██║   ██║  ██║███████║██║  ██╗  ██║     ███████╗╚██████╔╝╚███╔███╔╝
   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝  ╚═╝     ╚══════╝ ╚═════╝  ╚══╝╚══╝

 ██████╗ ██████╗  ██████╗
 ██╔══██╗██╔══██╗██╔═══██╗
 ██████╔╝██████╔╝██║   ██║
 ██╔═══╝ ██╔══██╗██║   ██║
 ██║     ██║  ██║╚██████╔╝
 ╚═╝     ╚═╝  ╚═╝ ╚═════╝
```
### *AI-Powered Universal Team Task Management Platform*

> **TaskFlow Pro** — An AI-powered team task management platform for every domain. Assign coding, design, HR, marketing & more. Built-in compiler, smart deadlines, and AI feedback. One workspace. Every team.

---

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.x-000000?style=for-the-badge&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![JWT](https://img.shields.io/badge/JWT-Auth-FB015B?style=for-the-badge&logo=jsonwebtokens&logoColor=white)
![AI Powered](https://img.shields.io/badge/AI-Powered-FF6F00?style=for-the-badge&logo=openai&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge)

> **One platform. Every team. Any task.**  
> TaskFlow Pro eliminates tool fragmentation by combining universal task assignment, an integrated code compiler, and AI-powered feedback — all in a single workspace.

</div>

---

## 👨‍💻 Team

This project was built as **Course Assignment 2 — Project 1** for the Software Engineering course.

<table>
  <tr>
    <td align="center">
      <strong>Hassan Ali Shah</strong><br/>
      Student ID: BSCS24040<br/>
      <a href="https://github.com/Hassan-Ali-17">🔗 GitHub</a>
    </td>
    <td align="center">
      <strong>Abdul Moeed</strong><br/>
      Student ID: BSCS24140<br/>
      <a href="https://github.com/abdul888-888">🔗 GitHub</a>
    </td>
  </tr>
</table>

---
---

## 🚀 What Is TaskFlow Pro?

Most task management tools are built for *one* kind of team. **TaskFlow Pro is built for every team.**

Inspired by the flexibility of Google Classroom, the execution model of LeetCode, and the dashboard power of Jira — TaskFlow Pro fills a gap no existing platform does: **universal, domain-agnostic task management with an integrated code compiler and AI-powered deliverable feedback.**

A manager can:
- 🐛 Assign a software engineer to **fix a bug** — with a built-in compiler to write & run code
- 🎨 Ask a designer to **create an infographic** — with file upload and AI design feedback  
- 📄 Instruct HR to **draft a policy document** — with writing quality analysis
- 📊 Request a finance intern to **complete a spreadsheet analysis** — all in one place

**All from the same interface. All with AI feedback. All tracked in one dashboard.**

---

## ✨ Features

| Feature | Description |
|--------|-------------|
| 🔐 **JWT Authentication** | Secure registration, login, and session management with 24-hour tokens |
| 👥 **Team Management** | Create a team or join one via a unique 8-character invite code |
| 📋 **Universal Task Assignment** | Assign *any* task type — Coding, Design, Document, Marketing, HR, Finance, Research, or Custom |
| 💻 **Integrated Code Compiler** | Write, run, and submit Python, C++, Java, JS code directly in the browser (for Coding tasks) |
| 🤖 **AI Feedback Engine** | Automated quality scores, issue detection, and improvement suggestions for *every* task type |
| 📊 **Manager Dashboard** | Full team visibility — statuses, task type breakdowns, overdue alerts, per-member progress |
| 📁 **Reference Material Sharing** | Attach PDFs, URLs, videos, briefs to tasks or share team-wide (à la Google Classroom) |
| 🔔 **Smart Notifications** | In-app deadline reminders 24 hours before tasks are due |
| 🔒 **Role-Based Access Control** | Managers manage; Members execute. Clear permissions enforced at every level |
| 📜 **Submission Audit Log** | Immutable log of all submissions with timestamps and AI feedback results |

---

## 🎯 Supported Task Types

```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ 💻 Code │   │🎨 Design│  │ 📄 Docs │  │🔬Research│
└──────────┘  └──────────┘  └──────────┘  └──────────┘
┌──────────────┐   ┌──────────┐  ┌──────────┐  ┌──────────┐
│ 📣 Marketing│    │ 👔 HR   │  │💰 Finance│ │ ✏️ Custom│
└──────────────┘   └──────────┘  └──────────┘  └──────────┘
```

The task type tag system is designed as an **open enumeration** — new categories (Legal, Operations, Sales...) can be added with zero changes to core schema or UI logic.

---

## 🛠️ Tech Stack

```
Frontend          Backend           Database          AI / Services
──────────        ──────────        ──────────        ──────────────
HTML/CSS/JS   →   Flask (Python)  → SQLite           OpenAI GPT-4 API
Jinja2 Templates  JWT Auth          bcrypt hashing    Judge0 / Docker
                  RESTful API       RBAC Enforcement  HuggingFace Models
```

---

## ⚡ Quick Start

### Prerequisites

- Python 3.8+
- pip

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/Hassan-Ali-17/Task_Flow_Pro.git
cd taskflow-pro

# 2. Install dependencies
pip install flask PyJWT bcrypt

# 3. Start the server
cd backend
python app.py

# 4. Open your browser
# → http://localhost:5000
```

That's it. No Docker. No complicated setup. Just Python and a browser.

---

## 📁 Project Structure

```
taskflowpro/
│
├── backend/
│   ├── app.py              # Flask backend — all API routes & business logic
│   └── taskflow.db         # SQLite database (auto-created on first run)
│
├── frontend/
│   └── templates/
│       ├── index.html      # Login / Signup page
│       └── app.html        # Main dashboard (Manager + Member views)
│
├── run.sh                  # One-click quick start script
└── README.md               # You are here
```

---

## 🗺️ System Architecture

```
                    ┌─────────────────────────────────┐
                    │          Frontend (Browser)     │
                    │     HTML + CSS + Vanilla JS     │
                    └────────────────┬────────────────┘
                                     │ HTTP / REST
                    ┌────────────────▼────────────────┐
                    │         Flask Backend           │
                    │   JWT Auth │ RBAC │ REST API    │
                    └──────┬─────────────┬────────────┘
                           │             │
              ┌────────────▼──┐   ┌──────▼────────────────┐
              │   SQLite DB   │   │   External Services   │
              │  Tasks, Users │   │  AI API │ Judge0 API  │
              │  Teams, Logs  │   │  (Feedback + Compile) │
              └───────────────┘   └───────────────────────┘
```

---

## 📐 Key Requirements at a Glance

### Functional
- ✅ User registration with bcrypt password hashing
- ✅ JWT tokens (24hr validity, refreshable on active session)
- ✅ Unique 8-character alphanumeric team invite codes
- ✅ Task schema: `task_id`, `title`, `description`, `task_type_tag`, `deadline`, `assigned_to`, `status`, `attached_materials`
- ✅ Task statuses: `Pending → In Progress → Submitted → Reviewed` (auto `Overdue` when deadline passes)
- ✅ File uploads up to 50MB per submission/material
- ✅ Sandboxed code execution (stdout, stderr, execution time)
- ✅ AI feedback: quality score (0–100), key issues, improvement suggestions
- ✅ Manager dashboard with per-member completion rates

### Non-Functional
- ⚡ **Performance**: API responds to 95% of requests within 500ms at 200 req/s
- 🔒 **Security**: bcrypt hashing + HTTPS/TLS + sandboxed code execution (no network access)
- 📈 **Scalability**: Modular, horizontally scalable — compiler, ML, and core services scale independently
- 🛡️ **Reliability**: Automated DB backups every 24 hours, point-in-time recovery within 1 hour
- 🌐 **Compatibility**: Chrome, Firefox, Safari, Edge (latest 2 major versions) on desktop & mobile
- 🧪 **Maintainability**: ≥70% unit test coverage on all backend service modules

---

## 📋 Use Cases

<details>
<summary><strong>UC-01: User Registration</strong></summary>

**Flow**: User provides username, email, password → system validates → bcrypt hashes password → account created → redirected to login.

**Validations**: Valid email format, 8+ char password with uppercase + number, unique email check.

</details>

<details>
<summary><strong>UC-02: Create or Join a Team</strong></summary>

**Create**: Enter team name + domain → 8-char invite code generated → user becomes Manager.  
**Join**: Enter invite code → validated → user added as Team Member → redirected to workspace.

</details>

<details>
<summary><strong>UC-03: Assign a Task</strong></summary>

**Manager flow**: Fill title, description, task type tag, deadline, select members, optionally attach materials → system validates → task saved → in-app notifications sent to assigned members.

</details>

<details>
<summary><strong>UC-04: Submit Task Deliverable</strong></summary>

**Member flow**: View task → prepare deliverable (code / file / text / link) → optionally run code → submit → AI generates feedback (score + issues + suggestions) → status updated to Submitted.

</details>

<details>
<summary><strong>UC-05: View Manager Dashboard</strong></summary>

**Dashboard shows**: Total tasks, pending/submitted/reviewed/overdue counts, task type breakdown chart, filterable task table, per-member progress pages.

</details>

---

## 🤖 AI-Powered Feedback Demo

The Gradio demo showcases the core ML functionality: AI-powered task feedback across every domain.

**Input**: Task type + submitted deliverable  
**Output**: Quality/relevance score (0–100) + key issues + improvement suggestions

> 🔗 **Live Gradio Demo**: [https://d17bbe34215cdd61ef.gradio.live](https://d17bbe34215cdd61ef.gradio.live)

The AI prompt adapts based on task type:
- `Coding` → code review, complexity analysis, bug detection
- `Document` → writing quality, structure, clarity
- `Research` → relevance, depth, source quality
- `Marketing` → campaign alignment, messaging, audience fit
- `Design` → visual hierarchy, brand consistency, usability


## 📚 References & Inspiration

| Tool | What We Learned From It |
|------|--------------------------|
| **Google Classroom** | Assignment model, resource sharing, team-scoped workspace |
| **LeetCode** | Code execution environment, sandboxed compiler concept |
| **Jira / Trello** | Task management dashboard, status tracking |
| **Microsoft Teams Assignments** | Cross-domain task workflows for non-technical users |

*SRS structure follows Figure 4.17 — Software Engineering by Ian Sommerville, 10th Edition.*

---

## 📄 License

This project is submitted as a **confidential group assignment**. All rights reserved by the authors.

---

<div align="center">

**Built with ☕ and 🤖 by Hassan & Moeed — BSCS 4th Sem, March 2026**

*"One platform. Every team. Any task."*

</div>
