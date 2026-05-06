import sqlite3
import os
from datetime import datetime

DB_NAME = "toyamas_finance.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Accounts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            balance REAL DEFAULT 0,
            currency TEXT DEFAULT 'IDR'
        )
    ''')
    
    # Budgets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            limit_amount REAL NOT NULL,
            period TEXT DEFAULT 'monthly'
        )
    ''')
    
    # Transactions table (Expanded)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            account_id INTEGER,
            type TEXT NOT NULL, -- 'masuk' or 'keluar'
            amount REAL NOT NULL, -- normalized amount in IDR (or primary currency)
            currency TEXT DEFAULT 'IDR',
            original_amount REAL,
            description TEXT NOT NULL,
            sentiment_score INTEGER, -- 1-5
            group_id INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        )
    ''')
    
    # Groups table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_group_id INTEGER UNIQUE,
            name TEXT
        )
    ''')
    
    # Debts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS debts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            debtor_id INTEGER,
            creditor_id INTEGER,
            amount REAL,
            description TEXT,
            FOREIGN KEY (group_id) REFERENCES groups(id)
        )
    ''')

    conn.commit()
    conn.close()

# --- Account Operations ---
def add_account(chat_id, name, balance=0, currency='IDR'):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO accounts (chat_id, name, balance, currency) VALUES (?, ?, ?, ?)', 
                   (chat_id, name, balance, currency))
    conn.commit()
    conn.close()

def get_accounts(chat_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, balance, currency FROM accounts WHERE chat_id = ?', (chat_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "balance": r[2], "currency": r[3]} for r in rows]

# --- Budget Operations ---
def set_budget(chat_id, category, limit_amount):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM budgets WHERE chat_id = ? AND category = ?', (chat_id, category))
    cursor.execute('INSERT INTO budgets (chat_id, category, limit_amount) VALUES (?, ?, ?)', 
                   (chat_id, category, limit_amount))
    conn.commit()
    conn.close()

def get_budgets(chat_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT category, limit_amount FROM budgets WHERE chat_id = ?', (chat_id,))
    rows = cursor.fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}

# --- Transaction Operations ---
def add_transaction(chat_id, type_, amount, description, account_id=None, currency='IDR', original_amount=None, sentiment=None, group_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transactions (chat_id, type, amount, description, account_id, currency, original_amount, sentiment_score, group_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (chat_id, type_, amount, description, account_id, currency, original_amount or amount, sentiment, group_id))
    
    # Update account balance if provided
    if account_id:
        adjustment = amount if type_ == 'masuk' else -amount
        cursor.execute('UPDATE accounts SET balance = balance + ? WHERE id = ?', (adjustment, account_id))
        
    conn.commit()
    conn.close()

def get_transactions(chat_id, limit=50):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.id, t.type, t.amount, t.description, t.timestamp, a.name, t.currency, t.sentiment_score
        FROM transactions t
        LEFT JOIN accounts a ON t.account_id = a.id
        WHERE t.chat_id = ?
        ORDER BY t.timestamp DESC LIMIT ?
    ''', (chat_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "type": r[1], "amount": r[2], "description": r[3], "timestamp": r[4], "account": r[5], "currency": r[6], "sentiment": r[7]} for r in rows]

# --- Group & Debt Operations ---
def ensure_group(telegram_group_id, name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO groups (telegram_group_id, name) VALUES (?, ?)', (telegram_group_id, name))
    cursor.execute('SELECT id FROM groups WHERE telegram_group_id = ?', (telegram_group_id,))
    group_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return group_id

def add_debt(group_id, debtor_id, creditor_id, amount, description):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO debts (group_id, debtor_id, creditor_id, amount, description) VALUES (?, ?, ?, ?, ?)',
                   (group_id, debtor_id, creditor_id, amount, description))
    conn.commit()
    conn.close()

def get_debts(group_id):
    conn = get_connection()
    cursor = conn.cursor()
    # This is a simplified debt view. In a real app, you'd aggregate these.
    cursor.execute('''
        SELECT debtor_id, creditor_id, SUM(amount), description
        FROM debts
        WHERE group_id = ?
        GROUP BY debtor_id, creditor_id
    ''', (group_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"debtor": r[0], "creditor": r[1], "amount": r[2]} for r in rows]

def get_group_id_by_telegram_id(telegram_group_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM groups WHERE telegram_group_id = ?', (telegram_group_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None
