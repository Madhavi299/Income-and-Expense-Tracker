-- Personal Income & Expense Tracker with Login
-- Run in DBeaver connected to expense_tracker.
-- Existing tables/data are preserved; this creates tables only if absent.

CREATE TABLE IF NOT EXISTS public.users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'user';
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

CREATE TABLE IF NOT EXISTS public.activity_logs (
    id SERIAL PRIMARY KEY,
    actor_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
    target_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
    action VARCHAR(80) NOT NULL,
    details VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS public.transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
    transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('Income', 'Expense')),
    category VARCHAR(100) NOT NULL,
    transaction_date DATE NOT NULL,
    description TEXT,
    source VARCHAR(50) NOT NULL DEFAULT 'Manual',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transactions_user_id
    ON public.transactions(user_id);

CREATE INDEX IF NOT EXISTS idx_transactions_user_date
    ON public.transactions(user_id, transaction_date DESC);

CREATE INDEX IF NOT EXISTS idx_activity_logs_created_at
    ON public.activity_logs(created_at DESC);
