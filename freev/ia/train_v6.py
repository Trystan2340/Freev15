import sys
import os
from pathlib import Path

# Add the project directory to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from brain import FreevBrain

def main():
    print("🚀 Initializing FreevBrain v6...")
    brain = FreevBrain()
    
    print("🧹 Cleaning old brain file to force retraining...")
    if brain.BRAIN_FILE.exists():
        brain.BRAIN_FILE.unlink()
        
    print("🧠 Training TransformerBrain weights (MLP)...")
    brain.train_mlp(epochs=5)
    
    print(f"✅ Training complete. Status: {brain.status()}")
    
    data_file = brain._find_data_file()
    print(f"Loading test pairs from {data_file}...")
    pairs = brain.tester.load_test_file(str(data_file))
    
    # Run benchmark on 50 random pairs from the NEW data
    import random
    sample = random.sample(pairs, 50) if len(pairs) > 50 else pairs
    
    print(f"📊 Running v6 Benchmark on {len(sample)} pairs...")
    metrics = brain.tester.run_benchmark(brain, sample)
    
    print("\n" + "="*40)
    print(f"📊 v6 Benchmark Results:")
    print(f"  Accuracy      : {metrics['accuracy']*100:.1f}%")
    print(f"  Avg Confidence: {metrics['avg_confidence']*100:.1f}%")
    print(f"  Avg Time      : {metrics['avg_response_time_ms']:.1f} ms/response")
    print("="*40)
    
    # Test a complex question
    q = "Explique moi comment fonctionne une boucle for en Python et donne un exemple"
    print(f"\nUser > {q}")
    resp = brain.respond(q)
    print(f"Freev> {resp}")

if __name__ == "__main__":
    main()
