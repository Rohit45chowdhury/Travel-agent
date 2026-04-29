import sqlite3

DB_NAME = "chat.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        role TEXT,
        content TEXT
    )
    """)

    conn.commit()
    conn.close()

# user

def register_user(name, email, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    try:
        c.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (name, email, password)
        )
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()


def login_user(email, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute(
        "SELECT name FROM users WHERE email=? AND password=?",
        (email, password)
    )

    user = c.fetchone()
    conn.close()

    return user  # None or (name,)


# SAVE MESSAGE

def save_message(session_id, role, content):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute(
        "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, role, content)
    )

    conn.commit()
    conn.close()


# LOAD CHAT

def load_messages(session_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute(
        "SELECT role, content FROM messages WHERE session_id=?",
        (session_id,)
    )

    rows = c.fetchall()
    conn.close()

    return [{"role": r[0], "content": r[1]} for r in rows]

# add all chat

def get_all_sessions():
    conn = sqlite3.connect("chat.db")
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT session_id FROM messages ORDER BY rowid DESC")
    sessions = cursor.fetchall()

    conn.close()
    return [s[0] for s in sessions]


# memory
def init_memory():
  
    conn = sqlite3.connect("chat.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            memory TEXT
        )
    """)

    conn.commit()
    conn.close()

def save_memory(user_id, memory):

    conn = sqlite3.connect("chat.db")
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO memory (user_id, memory) VALUES (?, ?)",
        (user_id, memory)
    )

    conn.commit()
    conn.close()


def load_memory(user_id):
    conn = sqlite3.connect("chat.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT memory FROM memory WHERE user_id=?",
        (user_id,)
    )

    rows = cursor.fetchall()
    conn.close()

    return [r[0] for r in rows]



# CLEAR CHAT

def clear_chat(session_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
    conn.commit()
    conn.close()