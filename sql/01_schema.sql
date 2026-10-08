CREATE DATABASE IF NOT EXISTS KAVACH;
USE DATABASE KAVACH;
CREATE SCHEMA IF NOT EXISTS CORE;
USE SCHEMA CORE;

CREATE TABLE IF NOT EXISTS SCANS (
    scan_id STRING,
    ts TIMESTAMP_NTZ,
    lang STRING,
    input_type STRING,
    channel STRING,
    verdict STRING,
    risk_score FLOAT,
    primary_tactic STRING,
    tactics ARRAY,
    campaign_id STRING,
    dna_simhash NUMBER,
    timings VARIANT,
    is_demo BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS INDICATORS (
    scan_id STRING,
    ioc_type STRING,
    ioc_hash STRING,
    ioc_display STRING,
    tld STRING,
    ts TIMESTAMP_NTZ,
    is_demo BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS CAMPAIGNS (
    campaign_id STRING,
    first_seen TIMESTAMP_NTZ,
    last_seen TIMESTAMP_NTZ,
    variant_count NUMBER,
    primary_tactic STRING,
    centroid_simhash NUMBER
);
