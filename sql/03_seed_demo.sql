USE DATABASE KAVACH;
USE SCHEMA CORE;

-- Insert a demo campaign
INSERT INTO CAMPAIGNS (campaign_id, first_seen, last_seen, variant_count, primary_tactic, centroid_simhash)
VALUES ('C-DEMO-01', DATEADD(day, -5, CURRENT_TIMESTAMP()), CURRENT_TIMESTAMP(), 14, 'FAKE_KYC', 123456789);

-- Insert a few scans
INSERT INTO SCANS (scan_id, ts, lang, input_type, channel, verdict, risk_score, primary_tactic, campaign_id, is_demo)
VALUES 
    ('scan-demo-1', DATEADD(day, -4, CURRENT_TIMESTAMP()), 'en', 'text', 'sms', 'LIKELY_SCAM', 0.85, 'FAKE_KYC', 'C-DEMO-01', TRUE),
    ('scan-demo-2', DATEADD(day, -2, CURRENT_TIMESTAMP()), 'hi', 'text', 'sms', 'LIKELY_SCAM', 0.90, 'FAKE_KYC', 'C-DEMO-01', TRUE);

-- Insert indicators
INSERT INTO INDICATORS (scan_id, ioc_type, ioc_hash, ioc_display, is_demo)
VALUES 
    ('scan-demo-1', 'url', 'hash1', 'sbi***', TRUE),
    ('scan-demo-2', 'url', 'hash1', 'sbi***', TRUE);
