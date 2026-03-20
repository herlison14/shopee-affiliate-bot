"""
CRM Database Layer — SQLite
Todas as operações CRUD para o sistema CRM.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = _PROJECT_ROOT / "data" / "crm.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Cria todas as tabelas se não existirem."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.executescript("""
        -- Usuários CRM
        CREATE TABLE IF NOT EXISTS crm_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            role TEXT DEFAULT 'vendedor',  -- admin, gerente, vendedor, visualizador
            avatar TEXT,
            meta_mensal REAL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        -- Pipelines (funis de venda)
        CREATE TABLE IF NOT EXISTS pipelines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        -- Etapas do funil
        CREATE TABLE IF NOT EXISTS stages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pipeline_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            color TEXT DEFAULT '#4D9FFF',
            probability INTEGER DEFAULT 50,
            FOREIGN KEY (pipeline_id) REFERENCES pipelines(id) ON DELETE CASCADE
        );

        -- Tags
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            color TEXT DEFAULT '#888888',
            entity_type TEXT DEFAULT 'all'
        );

        -- Empresas
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            cnpj TEXT,
            sector TEXT,
            size TEXT,
            website TEXT,
            address TEXT,
            phone TEXT,
            email TEXT,
            notes TEXT,
            tags TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        );

        -- Contatos
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            company_id INTEGER,
            cargo TEXT,
            email TEXT,
            phone TEXT,
            whatsapp TEXT,
            linkedin TEXT,
            address TEXT,
            tags TEXT DEFAULT '[]',
            score INTEGER DEFAULT 0,
            avatar TEXT,
            notes TEXT,
            custom_fields TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE SET NULL
        );

        -- Negócios (Deals)
        CREATE TABLE IF NOT EXISTS deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            value REAL DEFAULT 0,
            currency TEXT DEFAULT 'BRL',
            stage_id INTEGER,
            pipeline_id INTEGER,
            contact_id INTEGER,
            company_id INTEGER,
            owner TEXT,
            close_date TEXT,
            probability INTEGER DEFAULT 50,
            status TEXT DEFAULT 'aberto',  -- aberto, ganho, perdido
            lost_reason TEXT,
            notes TEXT,
            tags TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (stage_id) REFERENCES stages(id) ON DELETE SET NULL,
            FOREIGN KEY (pipeline_id) REFERENCES pipelines(id) ON DELETE SET NULL,
            FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE SET NULL,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE SET NULL
        );

        -- Histórico de movimentações no pipeline
        CREATE TABLE IF NOT EXISTS deal_stage_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deal_id INTEGER NOT NULL,
            from_stage TEXT,
            to_stage TEXT NOT NULL,
            moved_by TEXT,
            moved_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (deal_id) REFERENCES deals(id) ON DELETE CASCADE
        );

        -- Atividades (Agenda CRM)
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,  -- ligacao, email, reuniao, tarefa, whatsapp, almoco, prazo
            title TEXT NOT NULL,
            description TEXT,
            deal_id INTEGER,
            contact_id INTEGER,
            company_id INTEGER,
            owner TEXT,
            due_date TEXT,
            due_time TEXT,
            duration INTEGER DEFAULT 30,  -- minutos
            status TEXT DEFAULT 'pendente',  -- pendente, concluida, atrasada
            recurrence TEXT,  -- none, daily, weekly, monthly
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (deal_id) REFERENCES deals(id) ON DELETE SET NULL,
            FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE SET NULL,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE SET NULL
        );

        -- Notas
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            deal_id INTEGER,
            contact_id INTEGER,
            company_id INTEGER,
            author TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (deal_id) REFERENCES deals(id) ON DELETE CASCADE,
            FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
        );

        -- Catálogo de Produtos/Serviços
        CREATE TABLE IF NOT EXISTS crm_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT,
            price REAL DEFAULT 0,
            currency TEXT DEFAULT 'BRL',
            category TEXT,
            description TEXT,
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        -- Produtos vinculados a negócios
        CREATE TABLE IF NOT EXISTS deal_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deal_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            unit_price REAL,
            discount_pct REAL DEFAULT 0,
            FOREIGN KEY (deal_id) REFERENCES deals(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES crm_products(id) ON DELETE CASCADE
        );

        -- Automações
        CREATE TABLE IF NOT EXISTS automations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            trigger_type TEXT NOT NULL,
            trigger_config TEXT DEFAULT '{}',
            conditions TEXT DEFAULT '[]',
            actions TEXT DEFAULT '[]',
            active INTEGER DEFAULT 1,
            executions INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );

        -- Índices de performance
        CREATE INDEX IF NOT EXISTS idx_deals_stage ON deals(stage_id);
        CREATE INDEX IF NOT EXISTS idx_deals_status ON deals(status);
        CREATE INDEX IF NOT EXISTS idx_deals_pipeline ON deals(pipeline_id);
        CREATE INDEX IF NOT EXISTS idx_contacts_company ON contacts(company_id);
        CREATE INDEX IF NOT EXISTS idx_activities_due ON activities(due_date);
        CREATE INDEX IF NOT EXISTS idx_activities_status ON activities(status);
        CREATE INDEX IF NOT EXISTS idx_notes_deal ON notes(deal_id);
        """)

        # Seed inicial: pipeline padrão
        row = conn.execute("SELECT COUNT(*) FROM pipelines").fetchone()[0]
        if row == 0:
            _seed_defaults(conn)


def _seed_defaults(conn: sqlite3.Connection):
    """Insere dados padrão na primeira inicialização."""
    conn.execute("INSERT INTO pipelines (name, description) VALUES (?, ?)",
                 ("Pipeline Principal", "Funil de vendas padrão"))
    pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    stages = [
        (pid, "Prospecção",   0, "#888888", 10),
        (pid, "Qualificação", 1, "#4D9FFF", 25),
        (pid, "Proposta",     2, "#FFD700", 50),
        (pid, "Negociação",   3, "#FF8C00", 75),
        (pid, "Fechado",      4, "#00C851", 95),
    ]
    conn.executemany(
        "INSERT INTO stages (pipeline_id, name, position, color, probability) VALUES (?,?,?,?,?)",
        stages)

    conn.execute("""
        INSERT INTO crm_users (name, email, role)
        VALUES ('Herlison', 'herlison14@gmail.com', 'admin')
    """)

    tags_data = [
        ("VIP", "#FFD700"), ("Lead Quente", "#FF4444"), ("Lead Frio", "#4D9FFF"),
        ("Indicação", "#00C851"), ("Follow-up", "#FF8C00"), ("Inativo", "#888888"),
    ]
    conn.executemany("INSERT OR IGNORE INTO tags (name, color) VALUES (?,?)", tags_data)

    products = [
        ("Consultoria", "CONS-001", 500.0, "BRL", "Serviços", "Hora de consultoria"),
        ("Pacote Básico", "PKG-001", 1200.0, "BRL", "Pacotes", "Pacote mensal básico"),
        ("Pacote Premium", "PKG-002", 3500.0, "BRL", "Pacotes", "Pacote mensal premium"),
    ]
    conn.executemany(
        "INSERT INTO crm_products (name, code, price, currency, category, description) VALUES (?,?,?,?,?,?)",
        products)

    conn.execute("""
        INSERT INTO automations (name, trigger_type, trigger_config, actions)
        VALUES (
            'Notificar negócio ganho',
            'deal_status_changed',
            '{"status": "ganho"}',
            '[{"type": "notify", "message": "Parabéns! Negócio fechado!"}]'
        )
    """)


# ── Pipelines & Stages ─────────────────────────────────────────────────────────

def get_pipelines():
    with get_connection() as c:
        return [dict(r) for r in c.execute("SELECT * FROM pipelines ORDER BY id").fetchall()]

def get_stages(pipeline_id: int):
    with get_connection() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM stages WHERE pipeline_id=? ORDER BY position", (pipeline_id,)
        ).fetchall()]

def create_stage(pipeline_id: int, name: str, color: str = "#4D9FFF", probability: int = 50):
    with get_connection() as c:
        pos = c.execute("SELECT COALESCE(MAX(position)+1,0) FROM stages WHERE pipeline_id=?",
                        (pipeline_id,)).fetchone()[0]
        c.execute("INSERT INTO stages (pipeline_id, name, position, color, probability) VALUES (?,?,?,?,?)",
                  (pipeline_id, name, pos, color, probability))

def delete_stage(stage_id: int):
    with get_connection() as c:
        c.execute("DELETE FROM stages WHERE id=?", (stage_id,))


# ── Contacts ──────────────────────────────────────────────────────────────────

def get_contacts(search: str = "", company_id: int = None, limit: int = 200):
    q = "SELECT c.*, co.name as company_name FROM contacts c LEFT JOIN companies co ON c.company_id=co.id WHERE 1=1"
    params = []
    if search:
        q += " AND (c.name LIKE ? OR c.email LIKE ? OR c.phone LIKE ?)"
        params += [f"%{search}%"] * 3
    if company_id:
        q += " AND c.company_id=?"
        params.append(company_id)
    q += " ORDER BY c.updated_at DESC LIMIT ?"
    params.append(limit)
    with get_connection() as c:
        return [dict(r) for r in c.execute(q, params).fetchall()]

def get_contact(contact_id: int):
    with get_connection() as c:
        r = c.execute("SELECT c.*, co.name as company_name FROM contacts c LEFT JOIN companies co ON c.company_id=co.id WHERE c.id=?", (contact_id,)).fetchone()
        return dict(r) if r else None

def create_contact(data: dict) -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = {
        "name": data.get("name", ""), "company_id": data.get("company_id"),
        "cargo": data.get("cargo", ""), "email": data.get("email", ""),
        "phone": data.get("phone", ""), "whatsapp": data.get("whatsapp", ""),
        "linkedin": data.get("linkedin", ""), "address": data.get("address", ""),
        "tags": json.dumps(data.get("tags", [])), "score": data.get("score", 0),
        "notes": data.get("notes", ""), "updated_at": now,
    }
    with get_connection() as c:
        c.execute("""
            INSERT INTO contacts (name, company_id, cargo, email, phone, whatsapp, linkedin, address, tags, score, notes, updated_at)
            VALUES (:name, :company_id, :cargo, :email, :phone, :whatsapp, :linkedin, :address, :tags, :score, :notes, :updated_at)
        """, row)
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]

def update_contact(contact_id: int, data: dict):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["updated_at"] = now
    data["tags"] = json.dumps(data.get("tags", []))
    cols = ", ".join(f"{k}=:{k}" for k in data if k != "id")
    with get_connection() as c:
        c.execute(f"UPDATE contacts SET {cols} WHERE id=:id", {**data, "id": contact_id})

def delete_contact(contact_id: int):
    with get_connection() as c:
        c.execute("DELETE FROM contacts WHERE id=?", (contact_id,))

def count_contacts():
    with get_connection() as c:
        return c.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]


# ── Companies ─────────────────────────────────────────────────────────────────

def get_companies(search: str = "", limit: int = 200):
    q = """
        SELECT co.*, COUNT(DISTINCT c.id) as contact_count, COUNT(DISTINCT d.id) as deal_count
        FROM companies co
        LEFT JOIN contacts c ON c.company_id=co.id
        LEFT JOIN deals d ON d.company_id=co.id
        WHERE 1=1
    """
    params = []
    if search:
        q += " AND (co.name LIKE ? OR co.cnpj LIKE ? OR co.sector LIKE ?)"
        params += [f"%{search}%"] * 3
    q += " GROUP BY co.id ORDER BY co.updated_at DESC LIMIT ?"
    params.append(limit)
    with get_connection() as c:
        return [dict(r) for r in c.execute(q, params).fetchall()]

def get_company(company_id: int):
    with get_connection() as c:
        r = c.execute("SELECT * FROM companies WHERE id=?", (company_id,)).fetchone()
        return dict(r) if r else None

def create_company(data: dict) -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = {
        "name": data.get("name", ""), "cnpj": data.get("cnpj", ""),
        "sector": data.get("sector", ""), "size": data.get("size", ""),
        "website": data.get("website", ""), "address": data.get("address", ""),
        "phone": data.get("phone", ""), "email": data.get("email", ""),
        "notes": data.get("notes", ""), "tags": json.dumps(data.get("tags", [])),
        "updated_at": now,
    }
    with get_connection() as c:
        c.execute("""
            INSERT INTO companies (name, cnpj, sector, size, website, address, phone, email, notes, tags, updated_at)
            VALUES (:name, :cnpj, :sector, :size, :website, :address, :phone, :email, :notes, :tags, :updated_at)
        """, row)
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]

def update_company(company_id: int, data: dict):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["updated_at"] = now
    data["tags"] = json.dumps(data.get("tags", []))
    cols = ", ".join(f"{k}=:{k}" for k in data if k != "id")
    with get_connection() as c:
        c.execute(f"UPDATE companies SET {cols} WHERE id=:id", {**data, "id": company_id})

def delete_company(company_id: int):
    with get_connection() as c:
        c.execute("DELETE FROM companies WHERE id=?", (company_id,))

def count_companies():
    with get_connection() as c:
        return c.execute("SELECT COUNT(*) FROM companies").fetchone()[0]


# ── Deals ─────────────────────────────────────────────────────────────────────

def get_deals(pipeline_id: int = None, stage_id: int = None, status: str = "aberto",
              search: str = "", owner: str = "", limit: int = 500):
    q = """
        SELECT d.*,
               s.name as stage_name, s.color as stage_color,
               c.name as contact_name, co.name as company_name
        FROM deals d
        LEFT JOIN stages s ON d.stage_id=s.id
        LEFT JOIN contacts c ON d.contact_id=c.id
        LEFT JOIN companies co ON d.company_id=co.id
        WHERE 1=1
    """
    params = []
    if pipeline_id:
        q += " AND d.pipeline_id=?"
        params.append(pipeline_id)
    if stage_id:
        q += " AND d.stage_id=?"
        params.append(stage_id)
    if status:
        q += " AND d.status=?"
        params.append(status)
    if search:
        q += " AND (d.title LIKE ? OR c.name LIKE ? OR co.name LIKE ?)"
        params += [f"%{search}%"] * 3
    if owner:
        q += " AND d.owner=?"
        params.append(owner)
    q += " ORDER BY d.updated_at DESC LIMIT ?"
    params.append(limit)
    with get_connection() as c:
        return [dict(r) for r in c.execute(q, params).fetchall()]

def get_deal(deal_id: int):
    with get_connection() as c:
        r = c.execute("""
            SELECT d.*, s.name as stage_name, c.name as contact_name, co.name as company_name
            FROM deals d
            LEFT JOIN stages s ON d.stage_id=s.id
            LEFT JOIN contacts c ON d.contact_id=c.id
            LEFT JOIN companies co ON d.company_id=co.id
            WHERE d.id=?
        """, (deal_id,)).fetchone()
        return dict(r) if r else None

def create_deal(data: dict) -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = {
        "title": data.get("title", ""), "value": data.get("value", 0),
        "currency": data.get("currency", "BRL"), "stage_id": data.get("stage_id"),
        "pipeline_id": data.get("pipeline_id"), "contact_id": data.get("contact_id"),
        "company_id": data.get("company_id"), "owner": data.get("owner", ""),
        "close_date": data.get("close_date", ""), "probability": data.get("probability", 50),
        "status": data.get("status", "aberto"), "notes": data.get("notes", ""),
        "tags": json.dumps(data.get("tags", [])), "updated_at": now,
    }
    with get_connection() as c:
        c.execute("""
            INSERT INTO deals (title, value, currency, stage_id, pipeline_id, contact_id, company_id,
                               owner, close_date, probability, status, notes, tags, updated_at)
            VALUES (:title, :value, :currency, :stage_id, :pipeline_id, :contact_id, :company_id,
                    :owner, :close_date, :probability, :status, :notes, :tags, :updated_at)
        """, row)
        deal_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        if data.get("stage_id"):
            stage = c.execute("SELECT name FROM stages WHERE id=?", (data["stage_id"],)).fetchone()
            c.execute("INSERT INTO deal_stage_history (deal_id, from_stage, to_stage, moved_by) VALUES (?,?,?,?)",
                      (deal_id, None, stage["name"] if stage else "?", data.get("owner", "sistema")))
        return deal_id

def update_deal(deal_id: int, data: dict):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    old = get_deal(deal_id)
    data["updated_at"] = now
    if "tags" in data:
        data["tags"] = json.dumps(data["tags"])
    cols = ", ".join(f"{k}=:{k}" for k in data if k != "id")
    with get_connection() as c:
        c.execute(f"UPDATE deals SET {cols} WHERE id=:id", {**data, "id": deal_id})
        if "stage_id" in data and old and old.get("stage_id") != data["stage_id"]:
            old_stage = c.execute("SELECT name FROM stages WHERE id=?", (old["stage_id"],)).fetchone()
            new_stage = c.execute("SELECT name FROM stages WHERE id=?", (data["stage_id"],)).fetchone()
            c.execute("INSERT INTO deal_stage_history (deal_id, from_stage, to_stage, moved_by) VALUES (?,?,?,?)",
                      (deal_id, old_stage["name"] if old_stage else "?",
                       new_stage["name"] if new_stage else "?", data.get("owner", "sistema")))

def delete_deal(deal_id: int):
    with get_connection() as c:
        c.execute("DELETE FROM deals WHERE id=?", (deal_id,))

def move_deal_stage(deal_id: int, new_stage_id: int, moved_by: str = "usuário"):
    update_deal(deal_id, {"stage_id": new_stage_id, "owner": moved_by})

def count_deals(status: str = "aberto"):
    with get_connection() as c:
        return c.execute("SELECT COUNT(*) FROM deals WHERE status=?", (status,)).fetchone()[0]

def sum_deals_value(status: str = "aberto"):
    with get_connection() as c:
        v = c.execute("SELECT COALESCE(SUM(value),0) FROM deals WHERE status=?", (status,)).fetchone()[0]
        return v or 0.0

def get_deal_stage_history(deal_id: int):
    with get_connection() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM deal_stage_history WHERE deal_id=? ORDER BY moved_at DESC",
            (deal_id,)).fetchall()]


# ── Activities ────────────────────────────────────────────────────────────────

def get_activities(status: str = None, owner: str = "", date_from: str = None,
                   date_to: str = None, deal_id: int = None, contact_id: int = None, limit: int = 200):
    q = """
        SELECT a.*,
               c.name as contact_name, co.name as company_name, d.title as deal_title
        FROM activities a
        LEFT JOIN contacts c ON a.contact_id=c.id
        LEFT JOIN companies co ON a.company_id=co.id
        LEFT JOIN deals d ON a.deal_id=d.id
        WHERE 1=1
    """
    params = []
    if status:
        q += " AND a.status=?"
        params.append(status)
    if owner:
        q += " AND a.owner=?"
        params.append(owner)
    if date_from:
        q += " AND a.due_date>=?"
        params.append(date_from)
    if date_to:
        q += " AND a.due_date<=?"
        params.append(date_to)
    if deal_id:
        q += " AND a.deal_id=?"
        params.append(deal_id)
    if contact_id:
        q += " AND a.contact_id=?"
        params.append(contact_id)
    q += " ORDER BY a.due_date ASC, a.due_time ASC LIMIT ?"
    params.append(limit)
    with get_connection() as c:
        return [dict(r) for r in c.execute(q, params).fetchall()]

def create_activity(data: dict) -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = {
        "type": data.get("type", "tarefa"), "title": data.get("title", ""),
        "description": data.get("description", ""), "deal_id": data.get("deal_id"),
        "contact_id": data.get("contact_id"), "company_id": data.get("company_id"),
        "owner": data.get("owner", ""), "due_date": data.get("due_date", ""),
        "due_time": data.get("due_time", ""), "duration": data.get("duration", 30),
        "status": data.get("status", "pendente"), "recurrence": data.get("recurrence", "none"),
        "updated_at": now,
    }
    with get_connection() as c:
        c.execute("""
            INSERT INTO activities (type, title, description, deal_id, contact_id, company_id,
                                    owner, due_date, due_time, duration, status, recurrence, updated_at)
            VALUES (:type, :title, :description, :deal_id, :contact_id, :company_id,
                    :owner, :due_date, :due_time, :duration, :status, :recurrence, :updated_at)
        """, row)
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]

def update_activity_status(activity_id: int, status: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as c:
        c.execute("UPDATE activities SET status=?, updated_at=? WHERE id=?", (status, now, activity_id))

def delete_activity(activity_id: int):
    with get_connection() as c:
        c.execute("DELETE FROM activities WHERE id=?", (activity_id,))

def count_activities(status: str = "pendente"):
    with get_connection() as c:
        return c.execute("SELECT COUNT(*) FROM activities WHERE status=?", (status,)).fetchone()[0]


# ── Notes ─────────────────────────────────────────────────────────────────────

def get_notes(deal_id: int = None, contact_id: int = None, company_id: int = None, limit: int = 50):
    q = "SELECT * FROM notes WHERE 1=1"
    params = []
    if deal_id:
        q += " AND deal_id=?"; params.append(deal_id)
    if contact_id:
        q += " AND contact_id=?"; params.append(contact_id)
    if company_id:
        q += " AND company_id=?"; params.append(company_id)
    q += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with get_connection() as c:
        return [dict(r) for r in c.execute(q, params).fetchall()]

def create_note(content: str, deal_id=None, contact_id=None, company_id=None, author="sistema"):
    with get_connection() as c:
        c.execute("INSERT INTO notes (content, deal_id, contact_id, company_id, author) VALUES (?,?,?,?,?)",
                  (content, deal_id, contact_id, company_id, author))

def delete_note(note_id: int):
    with get_connection() as c:
        c.execute("DELETE FROM notes WHERE id=?", (note_id,))


# ── Products ──────────────────────────────────────────────────────────────────

def get_crm_products(search: str = ""):
    q = "SELECT * FROM crm_products WHERE active=1"
    params = []
    if search:
        q += " AND (name LIKE ? OR code LIKE ? OR category LIKE ?)"
        params += [f"%{search}%"] * 3
    q += " ORDER BY name"
    with get_connection() as c:
        return [dict(r) for r in c.execute(q, params).fetchall()]

def create_crm_product(data: dict) -> int:
    with get_connection() as c:
        c.execute("INSERT INTO crm_products (name, code, price, currency, category, description) VALUES (?,?,?,?,?,?)",
                  (data["name"], data.get("code", ""), data.get("price", 0),
                   data.get("currency", "BRL"), data.get("category", ""), data.get("description", "")))
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]

def delete_crm_product(product_id: int):
    with get_connection() as c:
        c.execute("UPDATE crm_products SET active=0 WHERE id=?", (product_id,))


# ── Reports ───────────────────────────────────────────────────────────────────

def get_pipeline_summary(pipeline_id: int):
    with get_connection() as c:
        rows = c.execute("""
            SELECT s.id, s.name, s.color, s.position,
                   COUNT(d.id) as deal_count,
                   COALESCE(SUM(d.value), 0) as total_value,
                   COALESCE(AVG(d.probability), 0) as avg_probability
            FROM stages s
            LEFT JOIN deals d ON d.stage_id=s.id AND d.status='aberto'
            WHERE s.pipeline_id=?
            GROUP BY s.id, s.name, s.color, s.position
            ORDER BY s.position
        """, (pipeline_id,)).fetchall()
        return [dict(r) for r in rows]

def get_deals_by_month(months: int = 6):
    with get_connection() as c:
        rows = c.execute("""
            SELECT strftime('%Y-%m', created_at) as month,
                   COUNT(*) as total,
                   SUM(CASE WHEN status='ganho' THEN 1 ELSE 0 END) as ganhos,
                   COALESCE(SUM(CASE WHEN status='ganho' THEN value ELSE 0 END), 0) as receita
            FROM deals
            WHERE created_at >= date('now', ?)
            GROUP BY month ORDER BY month
        """, (f"-{months} months",)).fetchall()
        return [dict(r) for r in rows]

def get_conversion_rate():
    with get_connection() as c:
        total = c.execute("SELECT COUNT(*) FROM deals WHERE status IN ('ganho','perdido')").fetchone()[0]
        ganhos = c.execute("SELECT COUNT(*) FROM deals WHERE status='ganho'").fetchone()[0]
        return round((ganhos / total * 100) if total > 0 else 0, 1)

def get_activities_summary():
    with get_connection() as c:
        rows = c.execute("""
            SELECT type, status, COUNT(*) as count
            FROM activities
            GROUP BY type, status
        """).fetchall()
        return [dict(r) for r in rows]

def get_top_owners(limit: int = 5):
    with get_connection() as c:
        rows = c.execute("""
            SELECT owner,
                   COUNT(*) as total_deals,
                   SUM(CASE WHEN status='ganho' THEN 1 ELSE 0 END) as ganhos,
                   COALESCE(SUM(CASE WHEN status='ganho' THEN value ELSE 0 END), 0) as receita
            FROM deals
            WHERE owner IS NOT NULL AND owner != ''
            GROUP BY owner ORDER BY receita DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

def get_users():
    with get_connection() as c:
        return [dict(r) for r in c.execute("SELECT * FROM crm_users ORDER BY name").fetchall()]

def get_tags():
    with get_connection() as c:
        return [dict(r) for r in c.execute("SELECT * FROM tags ORDER BY name").fetchall()]

def get_automations():
    with get_connection() as c:
        return [dict(r) for r in c.execute("SELECT * FROM automations ORDER BY created_at DESC").fetchall()]

def toggle_automation(automation_id: int, active: bool):
    with get_connection() as c:
        c.execute("UPDATE automations SET active=? WHERE id=?", (1 if active else 0, automation_id))

def create_automation(data: dict) -> int:
    with get_connection() as c:
        c.execute("""
            INSERT INTO automations (name, trigger_type, trigger_config, conditions, actions, active)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (data["name"], data["trigger_type"],
              json.dumps(data.get("trigger_config", {})),
              json.dumps(data.get("conditions", [])),
              json.dumps(data.get("actions", [])),
              1))
        return c.execute("SELECT last_insert_rowid()").fetchone()[0]
