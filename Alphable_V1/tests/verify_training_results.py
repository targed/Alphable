"""
Verify AlphaZero training results from test run.
"""
import os
import json

def verify_training_results():
    """Verify the training test results"""
    print("\n" + "="*70)
    print("VERIFICATION: AlphaZero Training Test Results")
    print("="*70)
    
    checkpoint_dir = "./data/results/test_training_checkpoints"
    
    if not os.path.exists(checkpoint_dir):
        print(f"❌ Checkpoint directory not found: {checkpoint_dir}")
        return False
    
    # Check for checkpoint files
    checkpoint_files = os.listdir(checkpoint_dir)
    print(f"\n✓ Checkpoint directory exists: {len(checkpoint_files)} files")
    
    # Check learner log
    learner_log = os.path.join(checkpoint_dir, "learner.jsonl")
    if not os.path.exists(learner_log):
        print(f"❌ Learner log not found")
        return False
    
    print(f"✓ Learner log found")
    
    # Parse learner log
    with open(learner_log, 'r') as f:
        log_entries = []
        for line in f:
            if line.strip():
                try:
                    log_entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    
    if not log_entries:
        print("❌ No log entries found")
        return False
    
    print(f"✓ Log entries: {len(log_entries)}")
    
    # Show training progression
    print("\nTraining Progression:")
    for entry in log_entries:
        step = entry.get('step', 'N/A')
        games = entry.get('total_trajectories', 'N/A')
        policy_loss = entry.get('loss', {}).get('policy', 'N/A')
        value_loss = entry.get('loss', {}).get('value', 'N/A')
        print(f"  Step {step}: {games} games, Policy Loss={policy_loss:.3f}, Value Loss={value_loss:.3f}")
    
    # Check for negative scores in actor logs
    print("\n" + "="*70)
    print("Checking for negative scores in game logs...")
    print("="*70)
    
    actor_logs = [f for f in checkpoint_files if f.startswith('log-actor')]
    negative_score_found = False
    
    for log_file in actor_logs:
        log_path = os.path.join(checkpoint_dir, log_file)
        with open(log_path, 'r') as f:
            content = f.read()
            lines = content.strip().split('\n')
            
            # Look for negative scores
            for line in lines:
                if 'score' in line.lower() and '-' in line:
                    # Check if it's actually a negative score (not just a dash)
                    if 'score' in line.lower() and any(f'-{i}' in line for i in range(10)):
                        print(f"⚠ Potential negative score in {log_file}: {line[:100]}")
                        negative_score_found = True
    
    if not negative_score_found:
        print("✓ No negative scores found in game logs")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    checks = {
        'Checkpoint directory exists': True,
        'Learner log exists': True,
        'Log entries found': len(log_entries) > 0,
        'Training progressed': len(log_entries) >= 5,  # At least 5 steps
        'No negative scores': not negative_score_found
    }
    
    all_passed = all(checks.values())
    
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"{status} {check}")
    
    print()
    if all_passed:
        print("✅ ALL ALPHAZERO TRAINING CHECKS PASSED!")
    else:
        print("⚠ SOME CHECKS FAILED")
    
    print("="*70)
    
    return all_passed


if __name__ == "__main__":
    success = verify_training_results()
    exit(0 if success else 1)
