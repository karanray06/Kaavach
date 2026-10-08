import pytest
from app.dna import simhash, hamming_distance, assign_campaign

def test_simhash_stability():
    t1 = "urgent your bank account is blocked"
    t2 = "urgent your bank account is blocked"
    assert simhash(t1) == simhash(t2)

def test_hamming_distance():
    h1 = int("101010", 2)
    h2 = int("100010", 2)
    assert hamming_distance(h1, h2) == 1

def test_assign_campaign():
    store = {}
    
    # First scan
    t1 = "urgent update kyc at <URL> or account blocked"
    c1 = assign_campaign(t1, "FAKE_KYC", store)
    
    assert c1["id"] == "C-0001"
    assert c1["variant_no"] == 1
    
    # Second scan, same tactic, very similar text
    t2 = "urgent update kyc at <URL> or account blocked today"
    c2 = assign_campaign(t2, "FAKE_KYC", store)
    
    assert c2["id"] == "C-0001"
    assert c2["variant_no"] == 2
    
    # Third scan, different tactic
    t3 = "you won lottery <AMT> contact <PHONE>"
    c3 = assign_campaign(t3, "LOTTERY_SCAM", store)
    
    assert c3["id"] == "C-0002"
    assert c3["variant_no"] == 1
