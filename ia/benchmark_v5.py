import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if BASE_DIR not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from brain import FreevBrain

def main():
    print("Initializing FreevBrain...")
    brain = FreevBrain()
    
    if not brain.trained:
        print("Brain not trained. Training now...")
        brain.train()
    
    print(f"Brain status: {brain.status()}")
    
    eval_file = BASE_DIR / "freev_eval.txt"
    data_file = eval_file if eval_file.exists() else brain._find_data_file()
    if not data_file:
        print("Benchmark file not found.")
        return
    
    print(f"Loading test pairs from {data_file}...")
    pairs = brain.tester.load_test_file(str(data_file))
    if not pairs:
        print("No test pairs found.")
        return
    
    sample = pairs[:200]
    print(f"Running benchmark on {len(sample)} pairs...")
    metrics = brain.tester.run_benchmark(brain, sample)
    
    print("\n" + "="*40)
    print(f"📊 Benchmark Results:")
    print(f"  Accuracy      : {metrics['accuracy']*100:.1f}%")
    print(f"  Avg Confidence: {metrics['avg_confidence']*100:.1f}%")
    print(f"  Avg Time      : {metrics['avg_response_time_ms']:.1f} ms/response")
    print("="*40)

if __name__ == "__main__":
    main()
