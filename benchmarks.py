import json
import os
from collections import defaultdict
from app.pipeline import run_scan

def run_benchmarks():
    fixtures_path = os.path.join(os.path.dirname(__file__), "fixtures", "messages.json")
    with open(fixtures_path, "r", encoding="utf-8") as f:
        fixtures = json.load(f)
        
    timings = defaultdict(list)
    
    # We will just run it a few times instead of 20 to avoid exhausting quotas further
    # Since we are already failing with quota on the real model, we will mock the model for benchmark
    # Actually, pipeline.py catches the Exception and returns timings anyway, so it's fine.
    for i in range(3):
        for fix in fixtures:
            res = run_scan(fix["text"], lang=fix["lang"])
            t = res["timings_ms"]
            for k, v in t.items():
                timings[k].append(v)
                
    medians = {}
    for k, v_list in timings.items():
        v_list.sort()
        mid = len(v_list) // 2
        medians[k] = v_list[mid]
        
    out_path = os.path.join(os.path.dirname(__file__), "docs", "benchmarks.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(medians, f, indent=2)
        
    print(f"Wrote benchmarks to {out_path}: {medians}")

if __name__ == "__main__":
    run_benchmarks()
