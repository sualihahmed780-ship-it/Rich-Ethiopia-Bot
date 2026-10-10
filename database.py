import aiosqlite
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from config import DATABASE_PATH, BOOKS_DIR

os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
os.makedirs(BOOKS_DIR, exist_ok=True)


async def init_db():
    """Create all tables if they do not exist."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")

        # Users table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                language TEXT DEFAULT 'en',
                created_at TEXT NOT NULL,
                trial_used INTEGER DEFAULT 0,
                trial_start TEXT,
                trial_end TEXT
            )
        """)

        # Membership plans (can be edited by admin)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS membership_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name_en TEXT NOT NULL,
                name_am TEXT NOT NULL,
                duration_days INTEGER NOT NULL,
                price_etb REAL NOT NULL,
                is_lifetime INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                sort_order INTEGER DEFAULT 0
            )
        """)

        # User memberships
        await db.execute("""
            CREATE TABLE IF NOT EXISTS memberships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan_id INTEGER,
                plan_name TEXT,
                start_date TEXT NOT NULL,
                end_date TEXT,
                is_lifetime INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                payment_id INTEGER,
                activated_by INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # Books
        await db.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title_en TEXT NOT NULL,
                title_am TEXT,
                description_en TEXT,
                description_am TEXT,
                category TEXT NOT NULL,
                price_etb REAL NOT NULL,
                preview_text TEXT,
                file_path TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
        """)

        # Book purchases
        await db.execute("""
            CREATE TABLE IF NOT EXISTS book_purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                book_id INTEGER NOT NULL,
                payment_id INTEGER,
                purchased_at TEXT NOT NULL,
                delivered INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (book_id) REFERENCES books(id)
            )
        """)

        # Payment methods (banks)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payment_methods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                account_name TEXT,
                account_number TEXT,
                instructions TEXT,
                is_active INTEGER DEFAULT 1,
                sort_order INTEGER DEFAULT 0
            )
        """)

        # Payment requests
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                payment_type TEXT NOT NULL,  -- 'membership' or 'book'
                reference_id INTEGER,        -- plan_id or book_id
                amount_etb REAL NOT NULL,
                method_id INTEGER,
                transaction_ref TEXT,
                receipt_file_id TEXT,
                status TEXT DEFAULT 'pending',  -- pending, approved, rejected, more_info
                admin_note TEXT,
                created_at TEXT NOT NULL,
                processed_at TEXT,
                processed_by INTEGER,
                UNIQUE(transaction_ref),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # Audit log
        await db.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                action TEXT NOT NULL,
                details TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # Seed default membership plans if empty
        cursor = await db.execute("SELECT COUNT(*) FROM membership_plans")
        count = (await cursor.fetchone())[0]
        if count == 0:
            plans = [
                ("Weekly", "ሳምንታዊ", 7, 50.0, 0, 1),
                ("Monthly", "ወርሃዊ", 30, 100.0, 0, 2),
                ("Yearly", "አመታዊ", 365, 1000.0, 0, 3),
                ("Lifetime", "የሕይወት ዘመን", 0, 2000.0, 1, 4),
            ]
            for name_en, name_am, days, price, lifetime, order in plans:
                await db.execute(
                    """INSERT INTO membership_plans 
                       (name_en, name_am, duration_days, price_etb, is_lifetime, sort_order)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (name_en, name_am, days, price, lifetime, order)
                )

        # Seed default payment methods (empty details - admin must fill)
        cursor = await db.execute("SELECT COUNT(*) FROM payment_methods")
        count = (await cursor.fetchone())[0]
        if count == 0:
            methods = [
                ("Telebirr", 1),
                ("Commercial Bank of Ethiopia", 2),
                ("Bank of Abyssinia", 3),
                ("Awash Bank", 4),
                ("Dashen Bank", 5),
                ("Hibret Bank", 6),
            ]
            for name, order in methods:
                await db.execute(
                    "INSERT INTO payment_methods (name, sort_order) VALUES (?, ?)",
                    (name, order)
                )

        await db.commit()


# ====================== USER HELPERS ======================

async def get_or_create_user(user_id: int, username: str = None, full_name: str = None) -> Dict:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row:
            return dict(row)

        now = datetime.utcnow().isoformat()
        await db.execute(
            "INSERT INTO users (user_id, username, full_name, created_at) VALUES (?, ?, ?, ?)",
            (user_id, username, full_name, now)
        )
        await db.commit()
        return {
            "user_id": user_id,
            "username": username,
            "full_name": full_name,
            "language": "en",
            "created_at": now,
            "trial_used": 0,
            "trial_start": None,
            "trial_end": None
        }


async def update_user_language(user_id: int, language: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE users SET language = ? WHERE user_id = ?", (language, user_id))
        await db.commit()


async def get_user(user_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


# ====================== TRIAL ======================

async def can_use_trial(user_id: int) -> bool:
    user = await get_user(user_id)
    if not user:
        return True
    return user["trial_used"] == 0


async def start_trial(user_id: int) -> Dict:
    now = datetime.utcnow()
    end = now + timedelta(seconds=3600)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """UPDATE users SET trial_used = 1, trial_start = ?, trial_end = ?
               WHERE user_id = ?""",
            (now.isoformat(), end.isoformat(), user_id)
        )
        await db.commit()
    return {"start": now.isoformat(), "end": end.isoformat()}


async def get_active_trial(user_id: int) -> Optional[Dict]:
    user = await get_user(user_id)
    if not user or not user["trial_end"]:
        return None
    end = datetime.fromisoformat(user["trial_end"])
    if datetime.utcnow() < end:
        return {"start": user["trial_start"], "end": user["trial_end"]}
    return None


# ====================== MEMBERSHIP PLANS ======================

async def get_active_plans() -> List[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM membership_plans WHERE is_active = 1 ORDER BY sort_order"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_plan(plan_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM membership_plans WHERE id = ?", (plan_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


# ====================== MEMBERSHIPS ======================

async def get_active_membership(user_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT * FROM memberships 
               WHERE user_id = ? AND status = 'active'
               ORDER BY id DESC LIMIT 1""",
            (user_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        m = dict(row)
        if m["is_lifetime"]:
            return m
        if m["end_date"]:
            end = datetime.fromisoformat(m["end_date"])
            if datetime.utcnow() < end:
                return m
            # Mark as expired
            await db.execute(
                "UPDATE memberships SET status = 'expired' WHERE id = ?", (m["id"],)
            )
            await db.commit()
        return None


async def activate_membership(user_id: int, plan: Dict, payment_id: int, admin_id: int) -> int:
    now = datetime.utcnow()
    if plan["is_lifetime"]:
        end_date = None
        is_lifetime = 1
    else:
        end_date = (now + timedelta(days=plan["duration_days"])).isoformat()
        is_lifetime = 0

    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Deactivate any previous active membership
        await db.execute(
            "UPDATE memberships SET status = 'replaced' WHERE user_id = ? AND status = 'active'",
            (user_id,)
        )
        cursor = await db.execute(
            """INSERT INTO memberships 
               (user_id, plan_id, plan_name, start_date, end_date, is_lifetime, status, payment_id, activated_by, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)""",
            (user_id, plan["id"], plan["name_en"], now.isoformat(), end_date, is_lifetime, payment_id, admin_id, now.isoformat())
        )
        await db.commit()
        return cursor.lastrowid


async def revoke_membership(user_id: int, admin_id: int, reason: str = ""):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE memberships SET status = 'revoked' WHERE user_id = ? AND status = 'active'",
            (user_id,)
        )
        await db.execute(
            "INSERT INTO audit_log (admin_id, action, details, created_at) VALUES (?, ?, ?, ?)",
            (admin_id, "revoke_membership", f"user={user_id} reason={reason}", datetime.utcnow().isoformat())
        )
        await db.commit()


async def get_expired_memberships() -> List[Dict]:
    """Return memberships that have expired but still marked active (non-lifetime)."""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT * FROM memberships 
               WHERE status = 'active' AND is_lifetime = 0 AND end_date < ?""",
            (now,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def mark_membership_expired(membership_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE memberships SET status = 'expired' WHERE id = ?", (membership_id,)
        )
        await db.commit()


# ====================== BOOKS ======================

async def get_categories() -> List[str]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT DISTINCT category FROM books WHERE is_active = 1 ORDER BY category"
        )
        rows = await cursor.fetchall()
        return [r[0] for r in rows]


async def get_books_by_category(category: str) -> List[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM books WHERE category = ? AND is_active = 1 ORDER BY title_en",
            (category,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_book(book_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def add_book(title_en: str, category: str, price: float, description_en: str = "",
                   title_am: str = "", description_am: str = "", preview: str = "",
                   file_path: str = None) -> int:
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO books 
               (title_en, title_am, description_en, description_am, category, price_etb, preview_text, file_path, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (title_en, title_am, description_en, description_am, category, price, preview, file_path, now)
        )
        await db.commit()
        return cursor.lastrowid


async def update_book(book_id: int, **kwargs):
    allowed = ["title_en", "title_am", "description_en", "description_am", "category",
               "price_etb", "preview_text", "file_path", "is_active"]
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    updates["updated_at"] = datetime.utcnow().isoformat()
    sets = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [book_id]
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(f"UPDATE books SET {sets} WHERE id = ?", values)
        await db.commit()


async def delete_book(book_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE books SET is_active = 0 WHERE id = ?", (book_id,))
        await db.commit()


async def has_purchased_book(user_id: int, book_id: int) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT id FROM book_purchases WHERE user_id = ? AND book_id = ?",
            (user_id, book_id)
        )
        return await cursor.fetchone() is not None


async def record_book_purchase(user_id: int, book_id: int, payment_id: int):
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """INSERT INTO book_purchases (user_id, book_id, payment_id, purchased_at, delivered)
               VALUES (?, ?, ?, ?, 1)""",
            (user_id, book_id, payment_id, now)
        )
        await db.commit()


# ====================== PAYMENT METHODS ======================

async def get_payment_methods() -> List[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM payment_methods WHERE is_active = 1 ORDER BY sort_order"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def get_payment_method(method_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM payment_methods WHERE id = ?", (method_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_payment_method(method_id: int, account_name: str = None,
                                 account_number: str = None, instructions: str = None):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """UPDATE payment_methods 
               SET account_name = COALESCE(?, account_name),
                   account_number = COALESCE(?, account_number),
                   instructions = COALESCE(?, instructions)
               WHERE id = ?""",
            (account_name, account_number, instructions, method_id)
        )
        await db.commit()


# ====================== PAYMENTS ======================

async def create_payment(user_id: int, payment_type: str, reference_id: int,
                         amount: float, method_id: int, transaction_ref: str = None,
                         receipt_file_id: str = None) -> int:
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            cursor = await db.execute(
                """INSERT INTO payments 
                   (user_id, payment_type, reference_id, amount_etb, method_id, 
                    transaction_ref, receipt_file_id, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)""",
                (user_id, payment_type, reference_id, amount, method_id,
                 transaction_ref, receipt_file_id, now)
            )
            await db.commit()
            return cursor.lastrowid
        except aiosqlite.IntegrityError:
            # Duplicate transaction_ref
            return -1


async def get_payment(payment_id: int) -> Optional[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_pending_payments() -> List[Dict]:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM payments WHERE status = 'pending' ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def update_payment_status(payment_id: int, status: str, admin_id: int, note: str = None):
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """UPDATE payments 
               SET status = ?, processed_at = ?, processed_by = ?, admin_note = ?
               WHERE id = ?""",
            (status, now, admin_id, note, payment_id)
        )
        await db.execute(
            "INSERT INTO audit_log (admin_id, action, details, created_at) VALUES (?, ?, ?, ?)",
            (admin_id, f"payment_{status}", f"payment_id={payment_id} note={note}", now)
        )
        await db.commit()


async def is_transaction_used(transaction_ref: str) -> bool:
    if not transaction_ref:
        return False
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT id FROM payments WHERE transaction_ref = ? AND status IN ('pending', 'approved')",
            (transaction_ref,)
        )
        return await cursor.fetchone() is not None


# ====================== STATS & AUDIT ======================

async def get_basic_stats() -> Dict:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM memberships WHERE status = 'active'"
        )
        active_members = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM payments WHERE status = 'approved'"
        )
        approved_payments = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COALESCE(SUM(amount_etb), 0) FROM payments WHERE status = 'approved'"
        )
        total_revenue = (await cursor.fetchone())[0]

        cursor = await db.execute(
            "SELECT COUNT(*) FROM payments WHERE status = 'pending'"
        )
        pending = (await cursor.fetchone())[0]

        return {
            "total_users": total_users,
            "active_members": active_members,
            "approved_payments": approved_payments,
            "total_revenue": total_revenue,
            "pending_payments": pending
        }


async def log_action(admin_id: int, action: str, details: str = ""):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO audit_log (admin_id, action, details, created_at) VALUES (?, ?, ?, ?)",
            (admin_id, action, details, datetime.utcnow().isoformat())
        )
        await db.commit()
