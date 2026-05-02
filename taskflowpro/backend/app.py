import os, sqlite3, hashlib, hmac, jwt, json, random, string, re
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory, g

# ── Groq AI Feedback ───────────────────────────────────────────────────────────
try:
    from groq import Groq
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")    
    _groq_client = Groq(api_key=GROQ_API_KEY)
    GROQ_ENABLED = True
    print('[TaskFlowPro] Groq AI feedback: ENABLED')
except Exception as _ge:
    _groq_client = None
    GROQ_ENABLED = False
    print(f'[TaskFlowPro] Groq AI feedback: DISABLED ({_ge})')

_TASK_CONTEXT = {
    'coding':    'a software programming task — evaluate code logic, correctness, efficiency, and best practices',
    'document':  'a written document task — evaluate clarity, structure, grammar, completeness, and tone',
    'marketing': 'a marketing task — evaluate persuasiveness, audience alignment, brand tone, and call-to-action',
    'hr':        'a human resources task — evaluate policy clarity, inclusivity, and professional language',
    'research':  'an academic or professional research task — evaluate depth, citations, reasoning, and accuracy',
    'design':    'a design brief task — evaluate clarity of direction, completeness, and feasibility',
    'finance':   'a financial analysis task — evaluate accuracy, methodology, and risk consideration',
    'custom':    'a general work task — evaluate overall quality, completeness, and relevance',
}

_AI_SYSTEM = """You are TaskFlow Pro's AI reviewer. You give honest, specific, constructive feedback on team task submissions.
Always respond in valid JSON with exactly these keys:
  score (integer 0-100),
  issues (array of 2-3 concise strings describing problems),
  suggestions (array of 2-3 actionable improvement strings),
  summary (one sentence overall assessment)
No extra text outside the JSON."""

def generate_ai_feedback(task_title, task_type, submission_text):
    if not GROQ_ENABLED:
        print('[AI Feedback] Groq not enabled')
        return None
    if not submission_text:
        print('[AI Feedback] Empty submission')
        return None
    ctx = _TASK_CONTEXT.get((task_type or 'custom').lower(), _TASK_CONTEXT['custom'])
    # For JSON submissions (design/marketing/hr/finance), extract readable text
    display_text = submission_text[:3000]
    try:
        parsed = json.loads(submission_text)
        display_text = ' '.join(str(v) for v in parsed.values() if v)[:3000]
    except Exception:
        pass
    user_msg = (
        f"Task type: {task_type} ({ctx})\n"
        f"Task title: {task_title}\n"
        f"Submission:\n{display_text}\n\n"
        f"Evaluate this submission and respond ONLY with a JSON object."
    )
    try:
        resp = _groq_client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[
                {'role': 'system', 'content': _AI_SYSTEM},
                {'role': 'user',   'content': user_msg}
            ],
            max_tokens=600,
            temperature=0.3
        )
        raw = resp.choices[0].message.content.strip()
        print(f'[AI Feedback] Raw response: {raw[:200]}')
        # Strip markdown code fences if present
        raw = re.sub(r'^```json\s*', '', raw)
        raw = re.sub(r'^```\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw).strip()
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        data = json.loads(match.group()) if match else json.loads(raw)
        score = max(0, min(100, int(data.get('score', 50))))
        issues = data.get('issues', [])
        suggestions = data.get('suggestions', [])
        # Handle if issues/suggestions are strings instead of arrays
        if isinstance(issues, str): issues = [issues]
        if isinstance(suggestions, str): suggestions = [suggestions]
        result = {
            'score':       score,
            'issues':      issues,
            'suggestions': suggestions,
            'summary':     str(data.get('summary', '')),
        }
        print(f'[AI Feedback] Success: score={score}')
        return result
    except Exception as e:
        print(f'[AI Feedback] Error: {e}')
        return None

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
FRONT_DIR = os.path.join(BASE_DIR, '..', 'frontend')
DB_PATH   = os.path.join(BASE_DIR, 'taskflow.db')
SECRET    = 'taskflowpro-secret-key-2026'

app = Flask(
    __name__,
    static_folder   = os.path.join(FRONT_DIR, 'static'),
    template_folder = os.path.join(FRONT_DIR, 'templates'),
)

@app.after_request
def add_cors(r):
    r.headers['Access-Control-Allow-Origin']  = '*'
    r.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    r.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    return r

@app.before_request
def handle_options():
    if request.method == 'OPTIONS':
        return jsonify({'ok': True}), 200

# ── Global error handlers so Flask ALWAYS returns JSON, never HTML ────────────
@app.errorhandler(400)
def bad_request(e):
    return jsonify({'error': str(e.description) or 'Bad request'}), 400

@app.errorhandler(401)
def unauthorized(e):
    return jsonify({'error': 'Unauthorized'}), 401

@app.errorhandler(403)
def forbidden(e):
    return jsonify({'error': 'Forbidden'}), 403

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({'error': 'Method not allowed'}), 405

@app.errorhandler(409)
def conflict(e):
    return jsonify({'error': str(e.description) or 'Conflict'}), 409

@app.errorhandler(415)
def unsupported_media(e):
    return jsonify({'error': 'Unsupported media type — ensure Content-Type is application/json'}), 415

@app.errorhandler(500)
def server_error(e):
    import traceback
    traceback.print_exc()
    return jsonify({'error': 'Internal server error. Check server console for details.'}), 500

@app.errorhandler(Exception)
def unhandled_exception(e):
    import traceback
    traceback.print_exc()
    return jsonify({'error': f'Server error: {str(e)}'}), 500

def get_json():
    """Parse JSON body regardless of Content-Type header."""
    # Try standard Flask JSON parsing first
    if request.is_json:
        result = request.get_json(silent=True, force=True)
        if result is not None:
            return result
    # Fall back to raw body parsing
    try:
        raw = request.data
        if raw:
            return json.loads(raw.decode('utf-8'))
    except Exception:
        pass
    # Try form data as last resort
    try:
        if request.form:
            return dict(request.form)
    except Exception:
        pass
    return {}

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db: db.close()

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            domain TEXT DEFAULT 'Mixed',
            invite_code TEXT UNIQUE NOT NULL,
            manager_id INTEGER NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (manager_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS team_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT DEFAULT 'member',
            joined_at TEXT DEFAULT (datetime('now')),
            UNIQUE(team_id, user_id),
            FOREIGN KEY (team_id) REFERENCES teams(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            task_type TEXT DEFAULT 'General',
            language TEXT DEFAULT '',
            deadline TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            priority TEXT DEFAULT 'medium',
            created_by INTEGER NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (team_id) REFERENCES teams(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS task_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            submission_text TEXT DEFAULT '',
            submitted_at TEXT DEFAULT '',
            ai_feedback TEXT DEFAULT '',
            UNIQUE(task_id, user_id),
            FOREIGN KEY (task_id) REFERENCES tasks(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS task_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            title TEXT DEFAULT '',
            url TEXT DEFAULT '',
            material_type TEXT DEFAULT 'link',
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            recipient_id INTEGER DEFAULT NULL,  -- NULL = group message
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (team_id) REFERENCES teams(id),
            FOREIGN KEY (sender_id) REFERENCES users(id)
        );
        CREATE INDEX IF NOT EXISTS idx_chat_team ON chat_messages(team_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_chat_dm ON chat_messages(sender_id, recipient_id);

        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            type TEXT DEFAULT 'info',
            is_read INTEGER DEFAULT 0,
            task_id INTEGER DEFAULT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        -- Add task_id column to existing notifications if missing (migration)
        PRAGMA ignore_check_constraints=ON;
        CREATE TABLE IF NOT EXISTS task_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (task_id) REFERENCES tasks(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS task_votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            UNIQUE(task_id, user_id),
            FOREIGN KEY (task_id) REFERENCES tasks(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS time_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            minutes INTEGER NOT NULL DEFAULT 0,
            note TEXT DEFAULT '',
            logged_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (task_id) REFERENCES tasks(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS user_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            points INTEGER DEFAULT 0,
            streak_days INTEGER DEFAULT 0,
            last_activity TEXT DEFAULT '',
            UNIQUE(user_id, team_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (team_id) REFERENCES teams(id)
        );
    """)
    db.commit()
    db.close()
    # Migration: add task_id to notifications if missing
    try:
        db.execute('ALTER TABLE notifications ADD COLUMN task_id INTEGER DEFAULT NULL')
        db.commit()
    except Exception:
        pass  # column already exists
    print("Database ready:", DB_PATH)

def hash_password(pw):
    salt = os.urandom(32)
    key  = hashlib.pbkdf2_hmac('sha256', pw.encode(), salt, 100000)
    return salt.hex() + ':' + key.hex()

def verify_password(pw, stored):
    try:
        salt_h, key_h = stored.split(':')
        salt = bytes.fromhex(salt_h)
        key  = bytes.fromhex(key_h)
        new  = hashlib.pbkdf2_hmac('sha256', pw.encode(), salt, 100000)
        return hmac.compare_digest(key, new)
    except Exception:
        return False

def make_token(uid):
    payload = {'user_id': uid, 'exp': datetime.now(timezone.utc) + timedelta(days=7)}
    return jwt.encode(payload, SECRET, algorithm='HS256')

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth  = request.headers.get('Authorization', '')
        token = auth.replace('Bearer ', '').strip()
        if not token:
            return jsonify({'error': 'Authentication required'}), 401
        try:
            data = jwt.decode(token, SECRET, algorithms=['HS256'])
            db   = get_db()
            user = db.execute('SELECT * FROM users WHERE id=?', (data['user_id'],)).fetchone()
            if not user:
                return jsonify({'error': 'User not found'}), 401
            g.current_user = dict(user)
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Session expired, please log in again'}), 401
        except Exception:
            return jsonify({'error': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated

def rand_code(n=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=n))

# ── Pages ──────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory(os.path.join(FRONT_DIR, 'templates'), 'index.html')

@app.route('/app')
@app.route('/app/')
def dashboard():
    return send_from_directory(os.path.join(FRONT_DIR, 'templates'), 'app.html')

# ── Auth ───────────────────────────────────────────────────────────────────────
@app.route('/api/auth/register', methods=['POST', 'OPTIONS'])
def register():
    try:
        d        = get_json()
        username = (d.get('username') or '').strip()
        email    = (d.get('email')    or '').strip().lower()
        password =  d.get('password') or ''
        if not username:
            return jsonify({'error': 'Full name is required'}), 400
        if not email:
            return jsonify({'error': 'Email address is required'}), 400
        if not password:
            return jsonify({'error': 'Password is required'}), 400
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        if '@' not in email or '.' not in email:
            return jsonify({'error': 'Please enter a valid email address'}), 400
        db = get_db()
        if db.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone():
            return jsonify({'error': 'This email is already registered. Please sign in.'}), 409
        if db.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone():
            return jsonify({'error': 'This name is already taken. Please choose another.'}), 409
        cur = db.execute(
            'INSERT INTO users (username, email, password_hash) VALUES (?,?,?)',
            (username, email, hash_password(password))
        )
        db.commit()
        uid = cur.lastrowid
        return jsonify({'token': make_token(uid), 'user': {'id': uid, 'username': username, 'email': email}}), 201
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500

@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
def login():
    try:
        d        = get_json()
        email    = (d.get('email')    or '').strip().lower()
        password =  d.get('password') or ''
        if not email:
            return jsonify({'error': 'Email address is required'}), 400
        if not password:
            return jsonify({'error': 'Password is required'}), 400
        db   = get_db()
        user = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        if not user or not verify_password(password, user['password_hash']):
            return jsonify({'error': 'Incorrect email or password'}), 401
        uid = user['id']
        return jsonify({'token': make_token(uid), 'user': {'id': uid, 'username': user['username'], 'email': user['email']}})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'error': f'Login failed: {str(e)}'}), 500

@app.route('/api/auth/me', methods=['GET'])
@token_required
def me():
    u = g.current_user
    return jsonify({'id': u['id'], 'username': u['username'], 'email': u['email']})

# ── Teams ──────────────────────────────────────────────────────────────────────
@app.route('/api/teams', methods=['POST'])
@token_required
def create_team():
    d    = get_json()
    name = (d.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Team name is required'}), 400
    db  = get_db()
    uid = g.current_user['id']
    code = rand_code()
    while db.execute('SELECT id FROM teams WHERE invite_code=?', (code,)).fetchone():
        code = rand_code()
    cur = db.execute(
        'INSERT INTO teams (name, description, domain, invite_code, manager_id) VALUES (?,?,?,?,?)',
        (name, d.get('description', ''), d.get('domain', 'Mixed'), code, uid)
    )
    tid = cur.lastrowid
    db.execute('INSERT INTO team_members (team_id, user_id, role) VALUES (?,?,?)', (tid, uid, 'manager'))
    db.commit()
    team = dict(db.execute('SELECT * FROM teams WHERE id=?', (tid,)).fetchone())
    return jsonify(team), 201

@app.route('/api/teams/join', methods=['POST'])
@token_required
def join_team():
    d    = get_json()
    code = (d.get('invite_code') or '').strip().upper()
    if not code:
        return jsonify({'error': 'Invite code is required'}), 400
    db   = get_db()
    uid  = g.current_user['id']
    team = db.execute('SELECT * FROM teams WHERE invite_code=?', (code,)).fetchone()
    if not team:
        return jsonify({'error': 'Invalid invite code. Please check and try again.'}), 404
    if db.execute('SELECT id FROM team_members WHERE team_id=? AND user_id=?', (team['id'], uid)).fetchone():
        return jsonify({'error': 'You are already a member of this team'}), 409
    db.execute('INSERT INTO team_members (team_id, user_id, role) VALUES (?,?,?)', (team['id'], uid, 'member'))
    db.execute('INSERT INTO notifications (user_id, message, type) VALUES (?,?,?)',
        (team['manager_id'], f"{g.current_user['username']} joined your team \"{team['name']}\"", 'info'))
    db.commit()
    return jsonify(dict(team))

@app.route('/api/teams/my', methods=['GET'])
@token_required
def my_teams():
    db  = get_db()
    uid = g.current_user['id']
    rows = db.execute('''
        SELECT t.*, tm.role,
            (SELECT COUNT(*) FROM team_members WHERE team_id=t.id) AS member_count,
            (SELECT COUNT(*) FROM tasks WHERE team_id=t.id) AS task_count
        FROM teams t JOIN team_members tm ON t.id=tm.team_id
        WHERE tm.user_id=? ORDER BY t.created_at DESC
    ''', (uid,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/teams/<int:tid>', methods=['GET'])
@token_required
def get_team(tid):
    db  = get_db()
    uid = g.current_user['id']
    mem = db.execute('SELECT * FROM team_members WHERE team_id=? AND user_id=?', (tid, uid)).fetchone()
    if not mem:
        return jsonify({'error': 'You are not a member of this team'}), 403
    team = db.execute('SELECT * FROM teams WHERE id=?', (tid,)).fetchone()
    if not team:
        return jsonify({'error': 'Team not found'}), 404
    members = db.execute('''
        SELECT u.id, u.username, u.email, tm.role, tm.joined_at
        FROM users u JOIN team_members tm ON u.id=tm.user_id
        WHERE tm.team_id=? ORDER BY tm.role DESC, tm.joined_at ASC
    ''', (tid,)).fetchall()
    return jsonify({'team': dict(team), 'members': [dict(m) for m in members], 'my_role': mem['role']})

@app.route('/api/teams/<int:tid>/stats', methods=['GET'])
@token_required
def team_stats(tid):
    db  = get_db()
    uid = g.current_user['id']
    if not db.execute('SELECT id FROM team_members WHERE team_id=? AND user_id=?', (tid, uid)).fetchone():
        return jsonify({'error': 'Access denied'}), 403
    def q(sql, *args):
        return db.execute(sql, args).fetchone()[0]
    by_type = db.execute('SELECT task_type, COUNT(*) c FROM tasks WHERE team_id=? GROUP BY task_type', (tid,)).fetchall()
    return jsonify({
        'total':     q('SELECT COUNT(*) FROM tasks WHERE team_id=?', tid),
        'pending':   q("SELECT COUNT(*) FROM tasks WHERE team_id=? AND status='pending'", tid),
        'completed': q("SELECT COUNT(*) FROM tasks WHERE team_id=? AND status='completed'", tid),
        'overdue':   q("SELECT COUNT(*) FROM tasks WHERE team_id=? AND status='overdue'", tid),
        'submitted': q("SELECT COUNT(*) FROM tasks WHERE team_id=? AND status='submitted'", tid),
        'members':   q('SELECT COUNT(*) FROM team_members WHERE team_id=?', tid),
        'by_type':   [dict(r) for r in by_type],
    })

# ── Tasks ──────────────────────────────────────────────────────────────────────
def _enrich(db, t):
    td = dict(t)
    td['assignments'] = [dict(a) for a in db.execute('''
        SELECT ta.*, u.username, u.email
        FROM task_assignments ta JOIN users u ON ta.user_id=u.id
        WHERE ta.task_id=?
    ''', (t['id'],)).fetchall()]
    td['materials'] = [dict(m) for m in
        db.execute('SELECT * FROM task_materials WHERE task_id=?', (t['id'],)).fetchall()]
    if td.get('deadline') and td['status'] == 'pending':
        try:
            if datetime.fromisoformat(td['deadline']) < datetime.now():
                db.execute("UPDATE tasks SET status='overdue' WHERE id=?", (t['id'],))
                # Also mark all pending assignments as overdue
                db.execute("UPDATE task_assignments SET status='overdue' WHERE task_id=? AND status='pending'", (t['id'],))
                db.commit()
                td['status'] = 'overdue'
                # Update assignments in the dict too
                for a in td['assignments']:
                    if a['status'] == 'pending':
                        a['status'] = 'overdue'
        except Exception:
            pass
    return td

def _check_deadline_reminders(db, tasks):
    """SR-27: Generate 24-hour deadline reminder notifications for upcoming tasks."""
    now = datetime.now()
    window = now + timedelta(hours=24)
    for t in tasks:
        td = dict(t)
        if not td.get('deadline') or td['status'] not in ('pending',):
            continue
        try:
            dl = datetime.fromisoformat(td['deadline'])
        except Exception:
            continue
        # Task deadline is within 24 hours from now AND hasn't passed yet
        if now < dl <= window:
            # Get all assigned users for this task
            assignees = db.execute('SELECT user_id FROM task_assignments WHERE task_id=? AND status="pending"', (td['id'],)).fetchall()
            for row in assignees:
                uid = row['user_id']
                # Check if we already sent a deadline_reminder for this task+user
                existing = db.execute(
                    "SELECT id FROM notifications WHERE user_id=? AND task_id=? AND type='deadline_reminder'",
                    (uid, td['id'])
                ).fetchone()
                if not existing:
                    hours_left = int((dl - now).total_seconds() // 3600)
                    db.execute(
                        'INSERT INTO notifications (user_id, message, type, task_id) VALUES (?,?,?,?)',
                        (uid, f'⏰ Deadline in ~{hours_left}h: "{td["title"]}"', 'deadline_reminder', td['id'])
                    )
            db.commit()

@app.route('/api/teams/<int:tid>/tasks', methods=['POST'])
@token_required
def create_task(tid):
    db  = get_db()
    uid = g.current_user['id']
    mem = db.execute('SELECT * FROM team_members WHERE team_id=? AND user_id=?', (tid, uid)).fetchone()
    if not mem or mem['role'] != 'manager':
        return jsonify({'error': 'Only the team manager can create tasks'}), 403
    d     = get_json()
    title = (d.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'Task title is required'}), 400
    cur = db.execute(
        'INSERT INTO tasks (team_id,title,description,task_type,language,deadline,priority,created_by) VALUES (?,?,?,?,?,?,?,?)',
        (tid, title, d.get('description',''), d.get('task_type','General'),
         d.get('language',''), d.get('deadline',''), d.get('priority','medium'), uid)
    )
    task_id = cur.lastrowid
    for aid in (d.get('assignees') or []):
        db.execute('INSERT OR IGNORE INTO task_assignments (task_id, user_id) VALUES (?,?)', (task_id, aid))
        db.execute('INSERT INTO notifications (user_id, message, type) VALUES (?,?,?)',
            (aid, f"New task assigned: \"{title}\"", 'task'))
    for mat in (d.get('materials') or []):
        if mat.get('url') or mat.get('title'):
            db.execute('INSERT INTO task_materials (task_id,title,url,material_type) VALUES (?,?,?,?)',
                (task_id, mat.get('title',''), mat.get('url',''), mat.get('type','link')))
    db.commit()
    task = db.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone()
    return jsonify(_enrich(db, task)), 201

@app.route('/api/teams/<int:tid>/tasks', methods=['GET'])
@token_required
def get_tasks(tid):
    db  = get_db()
    uid = g.current_user['id']
    mem = db.execute('SELECT * FROM team_members WHERE team_id=? AND user_id=?', (tid, uid)).fetchone()
    if not mem:
        return jsonify({'error': 'Access denied'}), 403
    # Fetch all team tasks to run deadline checks on them
    all_team_tasks = db.execute('SELECT * FROM tasks WHERE team_id=? ORDER BY created_at DESC', (tid,)).fetchall()
    # SR-27: Check for 24-hour deadline reminders
    _check_deadline_reminders(db, all_team_tasks)
    if mem['role'] == 'manager':
        rows = all_team_tasks
    else:
        rows = db.execute('''
            SELECT t.* FROM tasks t
            JOIN task_assignments ta ON t.id=ta.task_id
            WHERE t.team_id=? AND ta.user_id=?
            ORDER BY t.created_at DESC
        ''', (tid, uid)).fetchall()
    return jsonify([_enrich(db, t) for t in rows])

@app.route('/api/teams/<int:tid>/task-badge', methods=['GET'])
@token_required
def task_badge(tid):
    """Return pending task count for the nav badge. Managers see total pending, members see their own."""
    db  = get_db()
    uid = g.current_user['id']
    mem = db.execute('SELECT * FROM team_members WHERE team_id=? AND user_id=?', (tid, uid)).fetchone()
    if not mem:
        return jsonify({'error': 'Access denied'}), 403
    if mem['role'] == 'manager':
        count = db.execute("SELECT COUNT(*) FROM tasks WHERE team_id=? AND status='pending'", (tid,)).fetchone()[0]
    else:
        count = db.execute('''
            SELECT COUNT(*) FROM tasks t
            JOIN task_assignments ta ON t.id=ta.task_id
            WHERE t.team_id=? AND ta.user_id=? AND ta.status='pending'
        ''', (tid, uid)).fetchone()[0]
    return jsonify({'pending': count})

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
@token_required
def get_task(task_id):
    db   = get_db()
    uid  = g.current_user['id']
    task = db.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone()
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    if not db.execute('SELECT id FROM team_members WHERE team_id=? AND user_id=?', (task['team_id'], uid)).fetchone():
        return jsonify({'error': 'Access denied'}), 403
    return jsonify(_enrich(db, task))

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@token_required
def update_task(task_id):
    db   = get_db()
    uid  = g.current_user['id']
    task = db.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone()
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    mem = db.execute('SELECT * FROM team_members WHERE team_id=? AND user_id=?', (task['team_id'], uid)).fetchone()
    if not mem or mem['role'] != 'manager':
        return jsonify({'error': 'Only managers can edit tasks'}), 403
    d = get_json()
    new_title = d.get('title', task['title'])
    new_desc  = d.get('description', task['description'])
    new_dl    = d.get('deadline', task['deadline'])
    new_pri   = d.get('priority', task['priority'])
    new_sts   = d.get('status', task['status'])
    new_type  = d.get('task_type', task['task_type'])
    new_lang  = d.get('language', task['language'])
    db.execute('''UPDATE tasks SET title=?,description=?,deadline=?,priority=?,status=?,task_type=?,language=? WHERE id=?''',
        (new_title, new_desc, new_dl, new_pri, new_sts, new_type, new_lang, task_id))
    # Notify all assigned members
    assignees = db.execute('SELECT user_id FROM task_assignments WHERE task_id=?', (task_id,)).fetchall()
    editor = g.current_user['username']
    for row in assignees:
        if row['user_id'] != uid:
            db.execute('INSERT INTO notifications (user_id, message, type, task_id) VALUES (?,?,?,?)',
                (row['user_id'], f'{editor} updated task: "{new_title}"', 'task_updated', task_id))
    db.commit()
    return jsonify(_enrich(db, db.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone()))

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@token_required
def delete_task(task_id):
    db   = get_db()
    uid  = g.current_user['id']
    task = db.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone()
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    mem = db.execute('SELECT * FROM team_members WHERE team_id=? AND user_id=?', (task['team_id'], uid)).fetchone()
    if not mem or mem['role'] != 'manager':
        return jsonify({'error': 'Only managers can delete tasks'}), 403
    db.execute('DELETE FROM task_assignments WHERE task_id=?', (task_id,))
    db.execute('DELETE FROM task_materials WHERE task_id=?',   (task_id,))
    db.execute('DELETE FROM tasks WHERE id=?',                 (task_id,))
    db.commit()
    return jsonify({'message': 'Task deleted'})

@app.route('/api/tasks/<int:task_id>/submit', methods=['POST'])
@token_required
def submit_task(task_id):
    db   = get_db()
    uid  = g.current_user['id']
    asgn = db.execute('SELECT * FROM task_assignments WHERE task_id=? AND user_id=?', (task_id, uid)).fetchone()
    if not asgn:
        return jsonify({'error': 'This task is not assigned to you'}), 403
    task = db.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone()
    if task and task['deadline']:
        try:
            if datetime.fromisoformat(task['deadline']) < datetime.now():
                return jsonify({'error': 'Deadline has passed, submission is closed'}), 400
        except Exception:
            pass
    d    = get_json()
    text = (d.get('submission_text') or '').strip()
    if not text:
        return jsonify({'error': 'Submission cannot be empty'}), 400
    now = datetime.now().isoformat()
    # Auto-add ai_feedback column if it doesn't exist
    try:
        db.execute('ALTER TABLE task_assignments ADD COLUMN ai_feedback TEXT DEFAULT ""')
        db.commit()
    except Exception:
        pass

    # Generate AI feedback
    task_type = task['task_type'] if 'task_type' in task.keys() else 'General'
    print(f'[Submit] Generating AI feedback for task_type={task_type}, title={task["title"]}, text_len={len(text)}')
    ai = generate_ai_feedback(task['title'], task_type, text)
    ai_json = json.dumps(ai) if ai else ''

    db.execute('UPDATE task_assignments SET status=?,submission_text=?,submitted_at=?,ai_feedback=? WHERE task_id=? AND user_id=?',
        ('submitted', text, now, ai_json, task_id, uid))
    remaining = db.execute(
        "SELECT COUNT(*) FROM task_assignments WHERE task_id=? AND status!='submitted'", (task_id,)
    ).fetchone()[0]
    if remaining == 0:
        db.execute("UPDATE tasks SET status='completed' WHERE id=?", (task_id,))
    team = db.execute('SELECT manager_id FROM teams WHERE id=?', (task['team_id'],)).fetchone()
    if team:
        db.execute('INSERT INTO notifications (user_id, message, type) VALUES (?,?,?)',
            (team['manager_id'], f"{g.current_user['username']} submitted: \"{task['title']}\"", 'submission'))
    db.commit()

    if ai:
        return jsonify({'message': 'Submitted successfully', 'ai_feedback': ai})
    return jsonify({'message': 'Submitted successfully'})

# ── Notifications ──────────────────────────────────────────────────────────────
@app.route('/api/notifications', methods=['GET'])
@token_required
def get_notifs():
    db = get_db()
    # Auto-add task_id column if it doesn't exist (one-time migration for existing DBs)
    try:
        db.execute('ALTER TABLE notifications ADD COLUMN task_id INTEGER DEFAULT NULL')
        db.commit()
    except Exception:
        pass  # already exists
    try:
        rows = db.execute(
            'SELECT id, user_id, message, type, is_read, task_id, created_at FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 50',
            (g.current_user['id'],)).fetchall()
    except Exception:
        # Final fallback: select without task_id and add None manually
        rows = db.execute(
            'SELECT id, user_id, message, type, is_read, created_at FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 50',
            (g.current_user['id'],)).fetchall()
        return jsonify([dict(r, task_id=None) for r in rows])
    return jsonify([dict(r) for r in rows])

@app.route('/api/notifications/read', methods=['PUT'])
@token_required
def mark_read():
    db = get_db()
    db.execute('UPDATE notifications SET is_read=1 WHERE user_id=?', (g.current_user['id'],))
    db.commit()
    return jsonify({'message': 'All marked as read'})

# ── Code Runner ────────────────────────────────────────────────────────────────
import subprocess, tempfile, sys as _sys

LANG_CONFIG = {
    'python':     {'ext': '.py',   'cmd': lambda f: [_sys.executable, f]},
    'javascript': {'ext': '.js',   'cmd': lambda f: [_find_cmd('node'), f]},
    'cpp':        {'ext': '.cpp',  'cmd': lambda f: None,  'compile': lambda f, o: ['g++', '-std=c++17', '-O2', '-o', o, f]},
    'java':       {'ext': '.java', 'cmd': lambda f: None,  'compile': lambda f, d: [_find_cmd('javac'), '-d', d, f], 'run': lambda cls, d: [_find_cmd('java'), '-cp', d, cls]},
    'typescript': {'ext': '.ts',   'cmd': lambda f: [_find_cmd('node'), '--input-type=module']},
    'go':         {'ext': '.go',   'cmd': lambda f: ['go', 'run', f]},
    'rust':       {'ext': '.rs',   'cmd': lambda f: None},
    'csharp':     {'ext': '.cs',   'cmd': lambda f: None},
    'php':        {'ext': '.php',  'cmd': lambda f: [_find_cmd('php'), f]},
    'ruby':       {'ext': '.rb',   'cmd': lambda f: [_find_cmd('ruby'), f]},
}

import shutil as _shutil
import sys as _sys_platform

# ── Windows common install paths for each tool ───────────────────────────────
# Resolve Scoop user directory dynamically
import os as _os
_SCOOP_SHIMS = _os.path.expandvars(r'%USERPROFILE%\scoop\shims')
_SCOOP_APPS  = _os.path.expandvars(r'%USERPROFILE%\scoop\apps')

_WIN_PATHS = {
    'node': [
        # Scoop (most common on user installs)
        _os.path.join(_SCOOP_SHIMS, 'node.cmd'),
        _os.path.join(_SCOOP_SHIMS, 'node.exe'),
        _os.path.join(_SCOOP_APPS, 'nodejs', 'current', 'node.exe'),
        _os.path.join(_SCOOP_APPS, 'nodejs-lts', 'current', 'node.exe'),
        # Traditional installs
        r'C:\Program Files\nodejs\node.exe',
        r'C:\Program Files (x86)\nodejs\node.exe',
    ],
    'php': [
        # Scoop
        _os.path.join(_SCOOP_SHIMS, 'php.cmd'),
        _os.path.join(_SCOOP_SHIMS, 'php.exe'),
        _os.path.join(_SCOOP_APPS, 'php', 'current', 'php.exe'),
        # Traditional installs
        r'C:\php\php.exe',
        r'C:\php8\php.exe',
        r'C:\xampp\php\php.exe',
        r'C:\laragon\bin\php\php8.1.10-Win32-vs16-x64\php.exe',
        r'C:\wamp64\bin\php\php8.0.0\php.exe',
    ],
    'ruby': [
        # Scoop
        _os.path.join(_SCOOP_SHIMS, 'ruby.cmd'),
        _os.path.join(_SCOOP_SHIMS, 'ruby.exe'),
        _os.path.join(_SCOOP_APPS, 'ruby', 'current', 'bin', 'ruby.exe'),
        # Traditional installs
        r'C:\Ruby33-x64\bin\ruby.exe',
        r'C:\Ruby32-x64\bin\ruby.exe',
        r'C:\Ruby31-x64\bin\ruby.exe',
        r'C:\Ruby30-x64\bin\ruby.exe',
        r'C:\Ruby\bin\ruby.exe',
    ],
    'javac': [
        r'C:\Program Files\Eclipse Adoptium\jdk-21.0.1.12-hotspot\bin\javac.exe',
        r'C:\Program Files\Eclipse Adoptium\jdk-17.0.9.9-hotspot\bin\javac.exe',
        r'C:\Program Files\Java\jdk-21\bin\javac.exe',
        r'C:\Program Files\Java\jdk-17\bin\javac.exe',
        r'C:\Program Files\Java\jdk-11\bin\javac.exe',
        r'C:\Program Files\Microsoft\jdk-17.0.9.8-hotspot\bin\javac.exe',
    ],
    'java': [
        r'C:\Program Files\Eclipse Adoptium\jdk-21.0.1.12-hotspot\bin\java.exe',
        r'C:\Program Files\Eclipse Adoptium\jdk-17.0.9.9-hotspot\bin\java.exe',
        r'C:\Program Files\Java\jdk-21\bin\java.exe',
        r'C:\Program Files\Java\jdk-17\bin\java.exe',
        r'C:\Program Files\Java\jdk-11\bin\java.exe',
        r'C:\Program Files\Microsoft\jdk-17.0.9.8-hotspot\bin\java.exe',
    ],
}

def _find_cmd(cmd):
    """Find executable path - checks PATH, Scoop shims, then common Windows install dirs."""
    import os

    # 0. Inject Scoop shims into current process PATH if not already there
    scoop_shims = os.path.expandvars(r'%USERPROFILE%\scoop\shims')
    if os.path.isdir(scoop_shims) and scoop_shims not in os.environ.get('PATH', ''):
        os.environ['PATH'] = scoop_shims + os.pathsep + os.environ.get('PATH', '')

    # 1. Try plain name (works if it's in PATH)
    found = _shutil.which(cmd)
    if found:
        return found

    # 2. Windows: try .cmd / .exe extensions (Scoop uses .cmd shims)
    if _sys_platform.platform == 'win32':
        for ext in ['.cmd', '.exe', '.bat']:
            found = _shutil.which(cmd + ext)
            if found:
                return found

        # 3. Check known paths list (Scoop + traditional installs)
        for path in _WIN_PATHS.get(cmd, []):
            if os.path.isfile(path):
                return path

        # 4. Scan Program Files as last resort
        import glob
        for pf in [r'C:\Program Files', r'C:\Program Files (x86)']:
            matches = glob.glob(pf + r'\**\{}.exe'.format(cmd), recursive=True)
            if matches:
                return matches[0]

    return cmd  # fallback


def _available(cmd):
    """Check if a command exists anywhere we can find it."""
    path = _find_cmd(cmd)
    if os.path.isfile(path):
        return True
    try:
        r = subprocess.run([path, '--version'], capture_output=True, timeout=5)
        return True  # any response means it ran
    except FileNotFoundError:
        return False
    except Exception:
        return False

@app.route('/api/run', methods=['POST'])
def run_code():
    """Execute code server-side and return stdout/stderr."""
    try:
        d       = get_json()
        code    = d.get('code', '')
        lang    = (d.get('language') or 'python').lower().strip()
        stdin   = d.get('stdin', '') or ''
        timeout = min(int(d.get('timeout', 10)), 15)  # max 15s

        if not code.strip():
            return jsonify({'stdout': '', 'stderr': '', 'error': 'No code provided.', 'exit_code': 1})

        with tempfile.TemporaryDirectory() as tmpdir:
            # ── Python ──────────────────────────────────────────
            if lang == 'python':
                fpath = os.path.join(tmpdir, 'solution.py')
                with open(fpath, 'w') as f: f.write(code)
                result = subprocess.run(
                    [_sys.executable, fpath],
                    input=stdin, capture_output=True, text=True, timeout=timeout, cwd=tmpdir)
                return jsonify({'stdout': result.stdout, 'stderr': result.stderr, 'exit_code': result.returncode})

            # ── JavaScript / Node.js ─────────────────────────────
            elif lang in ('javascript', 'typescript'):
                if not _available('node'):
                    return jsonify({'stdout':'','stderr':'','error':'Node.js not found. Make sure it is installed and restart the server.','exit_code':1})
                # For TypeScript, strip type annotations (basic support)
                run_code_str = code
                if lang == 'typescript':
                    import re
                    run_code_str = re.sub(r':\s*\w+(\[\])?', '', code)
                    run_code_str = re.sub(r'<\w+>', '', run_code_str)
                fpath = os.path.join(tmpdir, 'solution.js')
                with open(fpath, 'w') as f: f.write(run_code_str)
                result = subprocess.run([_find_cmd('node'), fpath], input=stdin, capture_output=True, text=True, timeout=timeout, cwd=tmpdir, env=os.environ)
                return jsonify({'stdout': result.stdout, 'stderr': result.stderr, 'exit_code': result.returncode})

            # ── C++ ──────────────────────────────────────────────
            elif lang == 'cpp':
                if not _available('g++'):
                    return jsonify({'stdout':'','stderr':'','error':'g++ not installed','exit_code':1})
                src  = os.path.join(tmpdir, 'solution.cpp')
                exe  = os.path.join(tmpdir, 'solution')
                with open(src, 'w') as f: f.write(code)
                # Compile
                comp = subprocess.run(['g++', '-std=c++17', '-O2', '-o', exe, src],
                    capture_output=True, text=True, timeout=30, cwd=tmpdir)
                if comp.returncode != 0:
                    return jsonify({'stdout': '', 'stderr': comp.stderr, 'exit_code': comp.returncode,
                                    'compile_error': comp.stderr})
                # Run
                result = subprocess.run([exe], input=stdin, capture_output=True, text=True, timeout=timeout, cwd=tmpdir)
                return jsonify({'stdout': result.stdout, 'stderr': result.stderr, 'exit_code': result.returncode})

            # ── Java ─────────────────────────────────────────────
            elif lang == 'java':
                if not _available('javac'):
                    return jsonify({'stdout':'','stderr':'','error':'Java not installed','exit_code':1})
                # Find class name
                import re
                cls_match = re.search(r'public\s+class\s+(\w+)', code)
                cls_name  = cls_match.group(1) if cls_match else 'Solution'
                src = os.path.join(tmpdir, cls_name + '.java')
                with open(src, 'w') as f: f.write(code)
                comp = subprocess.run([_find_cmd('javac'), src], capture_output=True, text=True, timeout=30, cwd=tmpdir)
                if comp.returncode != 0:
                    return jsonify({'stdout':'','stderr':comp.stderr,'exit_code':comp.returncode,'compile_error':comp.stderr})
                result = subprocess.run([_find_cmd('java'), '-cp', tmpdir, cls_name],
                    input=stdin, capture_output=True, text=True, timeout=timeout, cwd=tmpdir)
                return jsonify({'stdout': result.stdout, 'stderr': result.stderr, 'exit_code': result.returncode})

            # ── Go ───────────────────────────────────────────────
            elif lang == 'go':
                if not _available('go'):
                    return jsonify({'stdout':'','stderr':'','error':'Go not installed','exit_code':1})
                fpath = os.path.join(tmpdir, 'main.go')
                with open(fpath, 'w') as f: f.write(code)
                result = subprocess.run(['go', 'run', fpath], input=stdin, capture_output=True, text=True, timeout=timeout, cwd=tmpdir)
                return jsonify({'stdout': result.stdout, 'stderr': result.stderr, 'exit_code': result.returncode})

            # ── Ruby ─────────────────────────────────────────────
            elif lang == 'ruby':
                if not _available('ruby'):
                    return jsonify({'stdout':'','stderr':'','error':'Ruby not installed','exit_code':1})
                fpath = os.path.join(tmpdir, 'solution.rb')
                with open(fpath, 'w') as f: f.write(code)
                result = subprocess.run([_find_cmd('ruby'), fpath], input=stdin, capture_output=True, text=True, timeout=timeout, cwd=tmpdir, env=os.environ)
                return jsonify({'stdout': result.stdout, 'stderr': result.stderr, 'exit_code': result.returncode})

            # ── PHP ──────────────────────────────────────────────
            elif lang == 'php':
                if not _available('php'):
                    return jsonify({'stdout':'','stderr':'','error':'PHP not found. Make sure it is installed and restart the server.','exit_code':1})
                fpath = os.path.join(tmpdir, 'solution.php')
                with open(fpath, 'w') as f: f.write(code)
                result = subprocess.run([_find_cmd('php'), fpath], input=stdin, capture_output=True, text=True, timeout=timeout, cwd=tmpdir, env=os.environ)
                return jsonify({'stdout': result.stdout, 'stderr': result.stderr, 'exit_code': result.returncode})

            # ── Rust ─────────────────────────────────────────────
            elif lang == 'rust':
                if not _available('rustc'):
                    return jsonify({'stdout':'','stderr':'','error':'Rust (rustc) not installed on this server. Code saved for review.','exit_code':1})
                src = os.path.join(tmpdir, 'solution.rs')
                exe = os.path.join(tmpdir, 'solution')
                with open(src, 'w') as f: f.write(code)
                comp = subprocess.run(['rustc', '-o', exe, src], capture_output=True, text=True, timeout=60)
                if comp.returncode != 0:
                    return jsonify({'stdout':'','stderr':comp.stderr,'exit_code':comp.returncode,'compile_error':comp.stderr})
                result = subprocess.run([exe], input=stdin, capture_output=True, text=True, timeout=timeout)
                return jsonify({'stdout': result.stdout, 'stderr': result.stderr, 'exit_code': result.returncode})

            # ── C# ───────────────────────────────────────────────
            elif lang == 'csharp':
                if not _available('dotnet'):
                    return jsonify({'stdout':'','stderr':'','error':'dotnet not installed on this server. Code saved for review.','exit_code':1})
                # Use dotnet-script or csc
                fpath = os.path.join(tmpdir, 'Program.cs')
                with open(fpath, 'w') as f: f.write(code)
                result = subprocess.run(['dotnet-script', fpath], input=stdin, capture_output=True, text=True, timeout=timeout)
                return jsonify({'stdout': result.stdout, 'stderr': result.stderr, 'exit_code': result.returncode})

            else:
                return jsonify({'stdout': '', 'stderr': '', 'error': f'Language "{lang}" not supported.', 'exit_code': 1})

    except subprocess.TimeoutExpired:
        return jsonify({'stdout': '', 'stderr': '', 'error': f'Execution timed out after {timeout}s', 'exit_code': 124})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({'stdout': '', 'stderr': '', 'error': f'Server error: {str(e)}', 'exit_code': 1})


# ── Check available languages ─────────────────────────────────────────────────
@app.route('/api/run/languages', methods=['GET'])
def available_languages():
    """Return which languages are available on the server."""
    langs = {
        'python':     _available('python3'),
        'javascript': _available('node'),
        'cpp':        _available('g++'),
        'java':       _available('javac'),
        'go':         _available('go'),
        'ruby':       _available('ruby'),
        'php':        _available('php'),
        'rust':       _available('rustc'),
        'typescript': _available('node'),  # runs as JS
        'csharp':     _available('dotnet'),
    }
    return jsonify(langs)

# ═══════════════════════════════════════════════════════════════════════
# COMMENTS
# ═══════════════════════════════════════════════════════════════════════
@app.route('/api/tasks/<int:task_id>/comments', methods=['GET'])
@token_required
def get_comments(task_id):
    uid = g.current_user['id']
    task = g.db.execute('SELECT team_id FROM tasks WHERE id=?', (task_id,)).fetchone()
    if not task: return jsonify({'error': 'Not found'}), 404
    mem = g.db.execute('SELECT id FROM team_members WHERE team_id=? AND user_id=?', (task['team_id'], uid)).fetchone()
    if not mem: return jsonify({'error': 'Forbidden'}), 403
    rows = g.db.execute('''
        SELECT c.id, c.content, c.created_at, u.username, u.id as user_id
        FROM task_comments c JOIN users u ON c.user_id=u.id
        WHERE c.task_id=? ORDER BY c.created_at ASC
    ''', (task_id,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/tasks/<int:task_id>/comments', methods=['POST'])
@token_required
def add_comment(task_id):
    import re as _re
    uid = g.current_user['id']
    task = g.db.execute('SELECT team_id, title FROM tasks WHERE id=?', (task_id,)).fetchone()
    if not task: return jsonify({'error': 'Not found'}), 404
    mem = g.db.execute('SELECT id FROM team_members WHERE team_id=? AND user_id=?', (task['team_id'], uid)).fetchone()
    if not mem: return jsonify({'error': 'Forbidden'}), 403
    data = request.get_json()
    content = (data.get('content') or '').strip()
    if not content: return jsonify({'error': 'Empty comment'}), 400
    g.db.execute('INSERT INTO task_comments (task_id, user_id, content) VALUES (?,?,?)', (task_id, uid, content))
    g.db.commit()
    award_points(uid, task['team_id'], 2, 'comment')
    # Parse @mentions and notify each mentioned teammate
    commenter = g.db.execute('SELECT username FROM users WHERE id=?', (uid,)).fetchone()
    cname = commenter['username'] if commenter else 'Someone'
    mentioned = set(_re.findall(r'@([A-Za-z0-9_]+)', content))
    for uname in mentioned:
        target = g.db.execute(
            'SELECT u.id FROM users u JOIN team_members tm ON u.id=tm.user_id WHERE u.username=? AND tm.team_id=?',
            (uname, task['team_id'])).fetchone()
        if target and target['id'] != uid:
            msg = '@{} mentioned you in: "{}"'.format(cname, task['title'][:40])
            g.db.execute(
                'INSERT INTO notifications (user_id, message, type, task_id) VALUES (?,?,?,?)',
                (target['id'], msg, 'mention', task_id))
    g.db.commit()
    return jsonify({'ok': True, 'mentions': list(mentioned)})

@app.route('/api/tasks/<int:task_id>/comments/<int:cid>', methods=['DELETE'])
@token_required
def delete_comment(task_id, cid):
    uid = g.current_user['id']
    row = g.db.execute('SELECT user_id FROM task_comments WHERE id=? AND task_id=?', (cid, task_id)).fetchone()
    if not row: return jsonify({'error': 'Not found'}), 404
    if row['user_id'] != uid:
        mem = g.db.execute('''SELECT role FROM team_members tm JOIN tasks t ON tm.team_id=t.team_id
            WHERE t.id=? AND tm.user_id=?''', (task_id, uid)).fetchone()
        if not mem or mem['role'] != 'manager': return jsonify({'error': 'Forbidden'}), 403
    g.db.execute('DELETE FROM task_comments WHERE id=?', (cid,))
    g.db.commit()
    return jsonify({'ok': True})

# ═══════════════════════════════════════════════════════════════════════
# VOTES (Priority upvoting)
# ═══════════════════════════════════════════════════════════════════════
@app.route('/api/tasks/<int:task_id>/vote', methods=['POST'])
@token_required
def vote_task(task_id):
    uid = g.current_user['id']
    task = g.db.execute('SELECT team_id FROM tasks WHERE id=?', (task_id,)).fetchone()
    if not task: return jsonify({'error': 'Not found'}), 404
    mem = g.db.execute('SELECT id FROM team_members WHERE team_id=? AND user_id=?', (task['team_id'], uid)).fetchone()
    if not mem: return jsonify({'error': 'Forbidden'}), 403
    existing = g.db.execute('SELECT id FROM task_votes WHERE task_id=? AND user_id=?', (task_id, uid)).fetchone()
    if existing:
        g.db.execute('DELETE FROM task_votes WHERE task_id=? AND user_id=?', (task_id, uid))
        g.db.commit()
        count = g.db.execute('SELECT COUNT(*) as c FROM task_votes WHERE task_id=?', (task_id,)).fetchone()['c']
        return jsonify({'voted': False, 'votes': count})
    g.db.execute('INSERT INTO task_votes (task_id, user_id) VALUES (?,?)', (task_id, uid))
    g.db.commit()
    count = g.db.execute('SELECT COUNT(*) as c FROM task_votes WHERE task_id=?', (task_id,)).fetchone()['c']
    return jsonify({'voted': True, 'votes': count})

@app.route('/api/tasks/<int:task_id>/votes', methods=['GET'])
@token_required
def get_votes(task_id):
    uid = g.current_user['id']
    count = g.db.execute('SELECT COUNT(*) as c FROM task_votes WHERE task_id=?', (task_id,)).fetchone()['c']
    voted = g.db.execute('SELECT id FROM task_votes WHERE task_id=? AND user_id=?', (task_id, uid)).fetchone()
    return jsonify({'votes': count, 'voted': bool(voted)})

# ═══════════════════════════════════════════════════════════════════════
# TIME TRACKING
# ═══════════════════════════════════════════════════════════════════════
@app.route('/api/tasks/<int:task_id>/time', methods=['POST'])
@token_required
def log_time(task_id):
    uid = g.current_user['id']
    task = g.db.execute('SELECT team_id FROM tasks WHERE id=?', (task_id,)).fetchone()
    if not task: return jsonify({'error': 'Not found'}), 404
    data = request.get_json()
    minutes = int(data.get('minutes', 0))
    note = (data.get('note') or '').strip()[:200]
    if minutes <= 0: return jsonify({'error': 'Invalid duration'}), 400
    g.db.execute('INSERT INTO time_logs (task_id, user_id, minutes, note) VALUES (?,?,?,?)', (task_id, uid, minutes, note))
    g.db.commit()
    # Award points for logging time (1 pt per 15 min, max 10)
    pts = min(10, minutes // 15)
    if pts > 0: award_points(uid, task['team_id'], pts, 'time_log')
    total = g.db.execute('SELECT COALESCE(SUM(minutes),0) as t FROM time_logs WHERE task_id=? AND user_id=?', (task_id, uid)).fetchone()['t']
    return jsonify({'ok': True, 'total_minutes': total})

@app.route('/api/tasks/<int:task_id>/time', methods=['GET'])
@token_required
def get_time(task_id):
    uid = g.current_user['id']
    my_total = g.db.execute('SELECT COALESCE(SUM(minutes),0) as t FROM time_logs WHERE task_id=? AND user_id=?', (task_id, uid)).fetchone()['t']
    task_total = g.db.execute('SELECT COALESCE(SUM(minutes),0) as t FROM time_logs WHERE task_id=?', (task_id,)).fetchone()['t']
    logs = g.db.execute('''SELECT tl.minutes, tl.note, tl.logged_at, u.username
        FROM time_logs tl JOIN users u ON tl.user_id=u.id
        WHERE tl.task_id=? ORDER BY tl.logged_at DESC LIMIT 20''', (task_id,)).fetchall()
    return jsonify({'my_minutes': my_total, 'total_minutes': task_total, 'logs': [dict(r) for r in logs]})

# ═══════════════════════════════════════════════════════════════════════
# GAMIFICATION - Points & Leaderboard
# ═══════════════════════════════════════════════════════════════════════
def award_points(user_id, team_id, pts, reason=''):
    try:
        import datetime
        today = datetime.date.today().isoformat()
        row = g.db.execute('SELECT * FROM user_points WHERE user_id=? AND team_id=?', (user_id, team_id)).fetchone()
        if row:
            streak = row['streak_days']
            if row['last_activity'] == today:
                pass  # same day, keep streak
            elif row['last_activity'] and (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(row['last_activity'])).days == 1:
                streak += 1  # consecutive day
            else:
                streak = 1  # reset
            bonus = min(streak, 7)  # streak bonus up to 7
            g.db.execute('''UPDATE user_points SET points=points+?, streak_days=?, last_activity=?
                WHERE user_id=? AND team_id=?''', (pts + bonus, streak, today, user_id, team_id))
        else:
            g.db.execute('''INSERT INTO user_points (user_id, team_id, points, streak_days, last_activity)
                VALUES (?,?,?,1,?)''', (user_id, team_id, pts + 1, today))
        g.db.commit()
    except Exception as e:
        pass  # non-critical

@app.route('/api/teams/<int:tid>/leaderboard', methods=['GET'])
@token_required
def get_leaderboard(tid):
    uid = g.current_user['id']
    mem = g.db.execute('SELECT id FROM team_members WHERE team_id=? AND user_id=?', (tid, uid)).fetchone()
    if not mem: return jsonify({'error': 'Forbidden'}), 403
    rows = g.db.execute('''
        SELECT u.username, u.id, COALESCE(up.points,0) as points,
               COALESCE(up.streak_days,0) as streak_days,
               COALESCE(up.last_activity,'') as last_activity,
               (SELECT COUNT(*) FROM task_assignments ta WHERE ta.user_id=u.id AND ta.status='submitted'
                AND ta.task_id IN (SELECT id FROM tasks WHERE team_id=?)) as completions,
               (SELECT COUNT(*) FROM task_comments tc WHERE tc.user_id=u.id
                AND tc.task_id IN (SELECT id FROM tasks WHERE team_id=?)) as comments
        FROM team_members tm JOIN users u ON tm.user_id=u.id
        LEFT JOIN user_points up ON up.user_id=u.id AND up.team_id=?
        WHERE tm.team_id=?
        ORDER BY points DESC
    ''', (tid, tid, tid, tid)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/teams/<int:tid>/analytics', methods=['GET'])
@token_required
def get_analytics(tid):
    uid = g.current_user['id']
    mem = g.db.execute('SELECT role FROM team_members WHERE team_id=? AND user_id=?', (tid, uid)).fetchone()
    if not mem: return jsonify({'error': 'Forbidden'}), 403
    # Task status breakdown
    status_rows = g.db.execute('''SELECT status, COUNT(*) as count FROM tasks WHERE team_id=? GROUP BY status''', (tid,)).fetchall()
    # Task type breakdown
    type_rows = g.db.execute('''SELECT task_type, COUNT(*) as count FROM tasks WHERE team_id=? GROUP BY task_type''', (tid,)).fetchall()
    # Per-member stats
    member_rows = g.db.execute('''
        SELECT u.username, u.id,
            COUNT(ta.id) as assigned,
            SUM(CASE WHEN ta.status='submitted' THEN 1 ELSE 0 END) as completed,
            COALESCE(SUM(tl.minutes),0) as total_minutes,
            COALESCE(up.points,0) as points
        FROM team_members tm
        JOIN users u ON tm.user_id=u.id
        LEFT JOIN task_assignments ta ON ta.user_id=u.id AND ta.task_id IN (SELECT id FROM tasks WHERE team_id=?)
        LEFT JOIN time_logs tl ON tl.user_id=u.id AND tl.task_id IN (SELECT id FROM tasks WHERE team_id=?)
        LEFT JOIN user_points up ON up.user_id=u.id AND up.team_id=?
        WHERE tm.team_id=?
        GROUP BY u.id
    ''', (tid, tid, tid, tid)).fetchall()
    # Total team time
    total_time = g.db.execute('''SELECT COALESCE(SUM(tl.minutes),0) as t FROM time_logs tl
        JOIN tasks tk ON tl.task_id=tk.id WHERE tk.team_id=?''', (tid,)).fetchone()['t']
    # Completion rate over time (last 7 tasks)
    timeline = g.db.execute('''SELECT date(submitted_at) as day, COUNT(*) as count
        FROM task_assignments ta JOIN tasks t ON ta.task_id=t.id
        WHERE t.team_id=? AND ta.status='submitted'
        GROUP BY day ORDER BY day DESC LIMIT 7''', (tid,)).fetchall()
    total_tasks = g.db.execute('SELECT COUNT(*) as c FROM tasks WHERE team_id=?',(tid,)).fetchone()['c']
    completed_tasks = g.db.execute("SELECT COUNT(*) as c FROM task_assignments WHERE status='submitted' AND task_id IN (SELECT id FROM tasks WHERE team_id=?)",(tid,)).fetchone()['c']
    team_info = g.db.execute('SELECT name FROM teams WHERE id=?',(tid,)).fetchone()
    members_count = g.db.execute('SELECT COUNT(*) as c FROM team_members WHERE team_id=?',(tid,)).fetchone()['c']
    return jsonify({
        'status_breakdown': [dict(r) for r in status_rows],
        'type_breakdown': [dict(r) for r in type_rows],
        'members': [dict(r) for r in member_rows],
        'total_time_minutes': total_time,
        'timeline': [dict(r) for r in timeline],
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'completion_rate': round(completed_tasks/total_tasks*100) if total_tasks else 0,
        'team_name': team_info['name'] if team_info else '',
        'team_department': '',
        'members_count': members_count
    })

# Award points on task submission (patch into submit endpoint)


@app.route('/api/run/diagnose', methods=['GET'])
def diagnose_langs():
    """Shows exactly where Python finds each language executable."""
    import os, sys
    results = {}
    for cmd in ['node', 'php', 'ruby', 'java', 'javac', 'python', 'g++']:
        found_path = _find_cmd(cmd)
        exists = os.path.isfile(found_path) if os.path.isabs(found_path) else False
        try:
            r = subprocess.run([found_path, '--version'], capture_output=True, timeout=5, text=True)
            version = (r.stdout or r.stderr or '').strip().split('')[0]
            working = True
        except FileNotFoundError:
            version = 'NOT FOUND IN PATH'
            working = False
        except Exception as e:
            version = str(e)
            working = False
        results[cmd] = {
            'resolved_path': found_path,
            'file_exists': exists,
            'working': working,
            'version': version,
        }
    results['_python_path'] = sys.executable
    results['_platform'] = sys.platform
    results['_PATH'] = os.environ.get('PATH', '')
    return jsonify(results)


# ═══════════════════════════════════════════════════════════════════════
# MEMBER ROLES MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════
ALLOWED_ROLES = ['manager', 'vice_head', 'team_lead', 'senior', 'member']

@app.route('/api/teams/<int:tid>/members/<int:uid>/role', methods=['PUT'])
@token_required
def update_member_role(tid, uid):
    me = g.current_user['id']
    my_mem = g.db.execute('SELECT role FROM team_members WHERE team_id=? AND user_id=?', (tid, me)).fetchone()
    if not my_mem or my_mem['role'] != 'manager':
        return jsonify({'error': 'Only the manager can change roles'}), 403
    if uid == me:
        return jsonify({'error': 'Cannot change your own role'}), 400
    data = request.get_json()
    new_role = (data.get('role') or '').strip().lower()
    if new_role not in ALLOWED_ROLES:
        return jsonify({'error': 'Invalid role. Allowed: '+', '.join(ALLOWED_ROLES)}), 400
    if new_role == 'manager':
        return jsonify({'error': 'Cannot assign another manager. Transfer ownership instead.'}), 400
    target = g.db.execute('SELECT id FROM team_members WHERE team_id=? AND user_id=?', (tid, uid)).fetchone()
    if not target:
        return jsonify({'error': 'Member not found'}), 404
    g.db.execute('UPDATE team_members SET role=? WHERE team_id=? AND user_id=?', (new_role, tid, uid))
    g.db.commit()
    username = g.db.execute('SELECT username FROM users WHERE id=?', (uid,)).fetchone()
    uname = username['username'] if username else 'Member'
    # Notify the member
    g.db.execute('INSERT INTO notifications (user_id, message, type) VALUES (?,?,?)',
        (uid, f'Your role in the team has been updated to: {new_role.replace("_"," ").title()}', 'info'))
    g.db.commit()
    return jsonify({'ok': True, 'role': new_role, 'username': uname})

@app.route('/api/teams/<int:tid>/members/<int:uid>', methods=['DELETE'])
@token_required
def remove_member(tid, uid):
    me = g.current_user['id']
    my_mem = g.db.execute('SELECT role FROM team_members WHERE team_id=? AND user_id=?', (tid, me)).fetchone()
    if not my_mem or my_mem['role'] != 'manager':
        return jsonify({'error': 'Only the manager can remove members'}), 403
    if uid == me:
        return jsonify({'error': 'Cannot remove yourself'}), 400
    g.db.execute('DELETE FROM team_members WHERE team_id=? AND user_id=?', (tid, uid))
    g.db.commit()
    return jsonify({'ok': True})


# ── AI Chat Assistant ──────────────────────────────────────────────────────────
@app.route('/api/ai/chat', methods=['POST'])
@token_required
def ai_chat():
    if not GROQ_ENABLED:
        return jsonify({'error': 'AI assistant not available'}), 503
    d = get_json()
    system_prompt = d.get('system', 'You are a helpful coding assistant.')
    messages = d.get('messages', [])
    if not messages:
        return jsonify({'error': 'No messages provided'}), 400
    # Validate messages
    clean = [{'role': m['role'], 'content': str(m['content'])[:4000]}
             for m in messages if m.get('role') in ('user','assistant') and m.get('content')]
    if not clean:
        return jsonify({'error': 'Invalid messages'}), 400
    try:
        resp = _groq_client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{'role': 'system', 'content': system_prompt}] + clean,
            max_tokens=1024,
            temperature=0.5
        )
        reply = resp.choices[0].message.content.strip()
        return jsonify({'reply': reply})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# CHAT API
# ══════════════════════════════════════════════════════════════════════════════

@app.route('/api/teams/<int:tid>/chat/group', methods=['GET'])
@token_required
def get_group_messages(tid):
    db  = get_db()
    uid = g.current_user['id']
    mem = db.execute('SELECT 1 FROM team_members WHERE team_id=? AND user_id=?', (tid, uid)).fetchone()
    if not mem:
        return jsonify({'error': 'Not a member'}), 403
    msgs = db.execute('''
        SELECT cm.id, cm.message, cm.created_at, cm.sender_id,
               u.username, u.id as uid
        FROM chat_messages cm
        JOIN users u ON u.id = cm.sender_id
        WHERE cm.team_id=? AND cm.recipient_id IS NULL
        ORDER BY cm.created_at ASC LIMIT 200
    ''', (tid,)).fetchall()
    return jsonify([dict(m) for m in msgs])

@app.route('/api/teams/<int:tid>/chat/group', methods=['POST'])
@token_required
def send_group_message(tid):
    db  = get_db()
    uid = g.current_user['id']
    mem = db.execute('SELECT 1 FROM team_members WHERE team_id=? AND user_id=?', (tid, uid)).fetchone()
    if not mem:
        return jsonify({'error': 'Not a member'}), 403
    d   = get_json()
    msg = (d.get('message') or '').strip()
    if not msg:
        return jsonify({'error': 'Message cannot be empty'}), 400
    cur = db.execute(
        'INSERT INTO chat_messages (team_id, sender_id, recipient_id, message) VALUES (?,?,NULL,?)',
        (tid, uid, msg)
    )
    # Notify every other member in the team
    sender_name = g.current_user['username']
    team_name   = db.execute('SELECT name FROM teams WHERE id=?', (tid,)).fetchone()['name']
    other_members = db.execute(
        'SELECT user_id FROM team_members WHERE team_id=? AND user_id!=?', (tid, uid)
    ).fetchall()
    preview = msg[:60] + ('…' if len(msg) > 60 else '')
    for row in other_members:
        db.execute(
            'INSERT INTO notifications (user_id, message, type) VALUES (?,?,?)',
            (row['user_id'], f'{sender_name} in {team_name}: "{preview}"', 'chat_group')
        )
    db.commit()
    row = db.execute('''SELECT cm.id, cm.message, cm.created_at, cm.sender_id, u.username
                        FROM chat_messages cm JOIN users u ON u.id=cm.sender_id
                        WHERE cm.id=?''', (cur.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201

@app.route('/api/teams/<int:tid>/chat/dm/<int:other_uid>', methods=['GET'])
@token_required
def get_dm_messages(tid, other_uid):
    db  = get_db()
    uid = g.current_user['id']
    mem = db.execute('SELECT 1 FROM team_members WHERE team_id=? AND user_id=?', (tid, uid)).fetchone()
    if not mem:
        return jsonify({'error': 'Not a member'}), 403
    msgs = db.execute('''
        SELECT cm.id, cm.message, cm.created_at, cm.sender_id, cm.is_read,
               u.username
        FROM chat_messages cm
        JOIN users u ON u.id = cm.sender_id
        WHERE cm.team_id=?
          AND ((cm.sender_id=? AND cm.recipient_id=?)
            OR (cm.sender_id=? AND cm.recipient_id=?))
        ORDER BY cm.created_at ASC LIMIT 200
    ''', (tid, uid, other_uid, other_uid, uid)).fetchall()
    # Mark as read
    db.execute('''UPDATE chat_messages SET is_read=1
                  WHERE team_id=? AND sender_id=? AND recipient_id=? AND is_read=0''',
               (tid, other_uid, uid))
    db.commit()
    return jsonify([dict(m) for m in msgs])

@app.route('/api/teams/<int:tid>/chat/dm/<int:other_uid>', methods=['POST'])
@token_required
def send_dm_message(tid, other_uid):
    db  = get_db()
    uid = g.current_user['id']
    mem = db.execute('SELECT 1 FROM team_members WHERE team_id=? AND user_id=?', (tid, uid)).fetchone()
    if not mem:
        return jsonify({'error': 'Not a member'}), 403
    d   = get_json()
    msg = (d.get('message') or '').strip()
    if not msg:
        return jsonify({'error': 'Message cannot be empty'}), 400
    cur = db.execute(
        'INSERT INTO chat_messages (team_id, sender_id, recipient_id, message) VALUES (?,?,?,?)',
        (tid, uid, other_uid, msg)
    )
    # Notify recipient
    sender_name = g.current_user['username']
    preview = msg[:60] + ('…' if len(msg) > 60 else '')
    db.execute(
        'INSERT INTO notifications (user_id, message, type) VALUES (?,?,?)',
        (other_uid, f'💬 {sender_name}: "{preview}"', 'chat_dm')
    )
    db.commit()
    row = db.execute('''SELECT cm.id, cm.message, cm.created_at, cm.sender_id, u.username
                        FROM chat_messages cm JOIN users u ON u.id=cm.sender_id
                        WHERE cm.id=?''', (cur.lastrowid,)).fetchone()
    return jsonify(dict(row)), 201

@app.route('/api/teams/<int:tid>/chat/unread', methods=['GET'])
@token_required
def get_unread_counts(tid):
    db  = get_db()
    uid = g.current_user['id']
    rows = db.execute('''
        SELECT sender_id, COUNT(*) as cnt
        FROM chat_messages
        WHERE team_id=? AND recipient_id=? AND is_read=0
        GROUP BY sender_id
    ''', (tid, uid)).fetchall()
    return jsonify({str(r['sender_id']): r['cnt'] for r in rows})


if __name__ == '__main__':
    init_db()
    print("TaskFlow Pro running at http://localhost:5000")
    app.run(debug=True, port=5000, host='0.0.0.0')