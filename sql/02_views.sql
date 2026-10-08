USE DATABASE KAVACH;
USE SCHEMA CORE;

CREATE OR REPLACE VIEW V_TRENDING_TACTICS AS
SELECT 
    primary_tactic,
    COUNT(*) as current_count,
    0 as delta_vs_prior
FROM SCANS
WHERE ts >= DATEADD(day, -7, CURRENT_TIMESTAMP())
  AND is_demo = FALSE
GROUP BY primary_tactic;

CREATE OR REPLACE VIEW V_CAMPAIGN_GROWTH AS
SELECT 
    campaign_id,
    DATE_TRUNC('day', ts) as day,
    COUNT(*) as daily_variants
FROM SCANS
WHERE is_demo = FALSE
GROUP BY campaign_id, DATE_TRUNC('day', ts);

CREATE OR REPLACE VIEW V_SEEN_BEFORE AS
SELECT 
    ioc_hash,
    COUNT(*) as seen_count,
    MIN(ts) as first_seen,
    MAX(ts) as last_seen
FROM INDICATORS
WHERE is_demo = FALSE
GROUP BY ioc_hash;

-- Stub view for CoCo dataset join
CREATE OR REPLACE VIEW V_CONTEXT_STUB AS
SELECT
    s.scan_id,
    s.primary_tactic
FROM SCANS s
WHERE s.is_demo = FALSE;
