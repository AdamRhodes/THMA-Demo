-- THMA Integration Demo — Azure SQL Schema
-- Run this in Azure Portal > Query Editor after creating the database.

-- ============================================================
-- Tables
-- ============================================================

CREATE TABLE accounts (
    id          INT IDENTITY(1,1) PRIMARY KEY,
    sf_id       NVARCHAR(18)  NOT NULL UNIQUE,
    name        NVARCHAR(255) NOT NULL,
    industry    NVARCHAR(255) NULL,
    type        NVARCHAR(255) NULL,
    website     NVARCHAR(500) NULL,
    phone       NVARCHAR(40)  NULL,
    billing_city  NVARCHAR(255) NULL,
    billing_state NVARCHAR(255) NULL,
    annual_revenue DECIMAL(18,2) NULL,
    created_date   DATETIME2     NULL,
    synced_at      DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME()
);

CREATE TABLE contacts (
    id          INT IDENTITY(1,1) PRIMARY KEY,
    sf_id       NVARCHAR(18)  NOT NULL UNIQUE,
    account_id  NVARCHAR(18)  NULL,
    first_name  NVARCHAR(255) NULL,
    last_name   NVARCHAR(255) NOT NULL,
    email       NVARCHAR(255) NULL,
    phone       NVARCHAR(40)  NULL,
    title       NVARCHAR(255) NULL,
    department  NVARCHAR(255) NULL,
    created_date   DATETIME2     NULL,
    synced_at      DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT fk_contacts_account FOREIGN KEY (account_id)
        REFERENCES accounts(sf_id)
);

CREATE TABLE opportunities (
    id          INT IDENTITY(1,1) PRIMARY KEY,
    sf_id       NVARCHAR(18)  NOT NULL UNIQUE,
    account_id  NVARCHAR(18)  NULL,
    name        NVARCHAR(255) NOT NULL,
    stage_name  NVARCHAR(255) NULL,
    amount      DECIMAL(18,2) NULL,
    close_date  DATE          NULL,
    probability DECIMAL(5,2)  NULL,
    created_date   DATETIME2     NULL,
    synced_at      DATETIME2     NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT fk_opportunities_account FOREIGN KEY (account_id)
        REFERENCES accounts(sf_id)
);

CREATE TABLE sync_log (
    id                INT IDENTITY(1,1) PRIMARY KEY,
    run_id            UNIQUEIDENTIFIER NOT NULL,
    status            NVARCHAR(20)     NOT NULL,  -- running, success, failed
    started_at        DATETIME2        NOT NULL DEFAULT SYSUTCDATETIME(),
    completed_at      DATETIME2        NULL,
    records_extracted INT              NULL,
    records_loaded    INT              NULL,
    error_message     NVARCHAR(MAX)    NULL
);

-- ============================================================
-- Indexes
-- ============================================================

CREATE INDEX ix_contacts_account_id      ON contacts(account_id);
CREATE INDEX ix_opportunities_account_id ON opportunities(account_id);
CREATE INDEX ix_sync_log_run_id          ON sync_log(run_id);
CREATE INDEX ix_sync_log_started_at      ON sync_log(started_at DESC);

-- ============================================================
-- Views
-- ============================================================

CREATE VIEW vw_pipeline_summary AS
SELECT
    stage_name,
    COUNT(*)        AS deal_count,
    SUM(amount)     AS total_amount,
    AVG(amount)     AS avg_amount,
    AVG(probability) AS avg_probability
FROM opportunities
GROUP BY stage_name;

CREATE VIEW vw_account_contacts AS
SELECT
    a.sf_id       AS account_sf_id,
    a.name        AS account_name,
    a.industry,
    c.sf_id       AS contact_sf_id,
    c.first_name,
    c.last_name,
    c.email,
    c.title,
    c.department
FROM accounts a
LEFT JOIN contacts c ON c.account_id = a.sf_id;
