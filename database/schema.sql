CREATE DATABASE IF NOT EXISTS lead_agent;
USE lead_agent;

CREATE TABLE IF NOT EXISTS leads (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    website VARCHAR(500) NULL,
    industry VARCHAR(150) NULL,
    city VARCHAR(150) NULL,
    country VARCHAR(150) NULL,
    contact_email VARCHAR(255) NULL,
    source VARCHAR(100) NULL,
    score TINYINT UNSIGNED NULL,
    opportunity VARCHAR(255) NULL,
    analysis JSON NULL,
    outreach_draft TEXT NULL,
    status ENUM('new','analyzed','approved','contacted','replied','discarded') NOT NULL DEFAULT 'new',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_leads_status (status),
    INDEX idx_leads_score (score),
    INDEX idx_leads_industry (industry)
);
