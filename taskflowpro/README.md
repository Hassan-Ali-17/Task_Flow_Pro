# TaskFlow Pro — Full Stack Setup Guide

## Requirements
- Python 3.8+ (with standard library)
- PyJWT: `pip install PyJWT`
- Flask: `pip install flask`

## Quick Start

```bash
# 1. Install dependencies (only PyJWT and Flask needed)
pip install flask PyJWT

# 2. Run the server
cd backend
python app.py

# 3. Open browser
http://localhost:5000
```

## Project Structure
```
taskflowpro/
├── backend/
│   ├── app.py          # Flask backend (all API routes)
│   └── taskflow.db     # SQLite database (auto-created)
├── frontend/
│   └── templates/
│       ├── index.html  # Login / Signup page
│       └── app.html    # Main dashboard
└── run.sh              # Quick start script
```

## Features
- ✅ User Registration & Login (JWT auth)
- ✅ Create Team (auto invite code) or Join Team
- ✅ Assign any task type: Coding, Design, Document, Marketing, HR, Finance, Research
- ✅ Manager Dashboard with stats (total, pending, completed, overdue)
- ✅ Task assignment to specific members
- ✅ Task submission by members
- ✅ Reference materials per task
- ✅ Team member management
- ✅ Notifications system
- ✅ Invite code sharing
