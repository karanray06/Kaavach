import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app.pipeline import run_scan

def validate():
    test_text = "URGENT: Your SBI account is blocked. Update KYC at http://sbi-kyc-verify-now.com to avoid charges."
    print("Testing pipeline with:")
    print(f"'{test_text}'\n")
    
    res = run_scan(test_text)
    
    print("RESULT:")
    print(f"Verdict: {res.get('verdict')}")
    print(f"Risk Score: {res.get('risk_score')}")
    print(f"Tactics: {res.get('tactics')}")
    print(f"Explanation: {res.get('explanation')}")
    print(f"Campaign: {res.get('campaign')}")
    
    if res.get('verdict') in ["LIKELY_SCAM", "SUSPICIOUS"]:
        print("\n[PASS] Pipeline correctly identified scam.")
    else:
        print("\n[FAIL] Pipeline did not flag the scam.")

if __name__ == "__main__":
    validate()
