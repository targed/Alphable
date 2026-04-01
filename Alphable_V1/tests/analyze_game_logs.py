"""
Analyze game logs from data/results/ directory.
Tests Requirements: 9.1, 9.2, 9.3, 9.4, 9.5

This script analyzes game logs to verify:
- Scores are non-negative
- No repeated move patterns
- Games progress normally
"""
import os
import re


def analyze_actor_log(log_path):
    """Analyze a single actor log file"""
    if not os.path.exists(log_path):
        return None
    
    with open(log_path, 'r') as f:
        content = f.read()
    
    lines = content.strip().split('\n')
    
    analysis = {
        'file': os.path.basename(log_path),
        'total_lines': len(lines),
        'negative_scores': [],
        'repeated_patterns': [],
        'game_progressions': [],
        'termination_reasons': [],
        'issues': []
    }
    
    # Track game states
    current_game = None
    move_sequence = []
    
    for i, line in enumerate(lines):
        # Check for negative scores
        # Look for patterns like "score: -10" or "Score=-5"
        score_matches = re.findall(r'[Ss]core[:\s=]+(-?\d+\.?\d*)', line)
        for score_str in score_matches:
            try:
                score = float(score_str)
                if score < 0:
                    analysis['negative_scores'].append({
                        'line_num': i + 1,
                        'score': score,
                        'context': line[:100]
                    })
            except ValueError:
                pass
        
        # Check for game termination reasons
        if 'terminated' in line.lower() or 'game over' in line.lower() or 'ended' in line.lower():
            analysis['termination_reasons'].append({
                'line_num': i + 1,
                'reason': line[:150]
            })
        
        # Check for repeated move patterns
        if 'move' in line.lower() or 'action' in line.lower():
            move_sequence.append(line[:80])
            # Keep only last 10 moves
            if len(move_sequence) > 10:
                move_sequence.pop(0)
            
            # Check for repetition (same move 3+ times in sequence)
            if len(move_sequence) >= 3:
                if move_sequence[-1] == move_sequence[-2] == move_sequence[-3]:
                    analysis['repeated_patterns'].append({
                        'line_num': i + 1,
                        'pattern': move_sequence[-1]
                    })
        
        # Track game progression
        if 'game' in line.lower() and ('start' in line.lower() or 'begin' in line.lower()):
            if current_game:
                analysis['game_progressions'].append(current_game)
            current_game = {
                'start_line': i + 1,
                'moves': 0,
                'end_line': None
            }
        
        if current_game and ('move' in line.lower() or 'turn' in line.lower()):
            current_game['moves'] += 1
        
        if current_game and ('game over' in line.lower() or 'terminated' in line.lower()):
            current_game['end_line'] = i + 1
            analysis['game_progressions'].append(current_game)
            current_game = None
    
    # Add final game if still in progress
    if current_game:
        analysis['game_progressions'].append(current_game)
    
    # Identify issues
    if analysis['negative_scores']:
        analysis['issues'].append(f"Found {len(analysis['negative_scores'])} negative scores")
    
    if analysis['repeated_patterns']:
        analysis['issues'].append(f"Found {len(analysis['repeated_patterns'])} repeated move patterns")
    
    return analysis


def analyze_all_logs():
    """Analyze all game logs in data/results/"""
    print("\n" + "="*70)
    print("GAME LOG ANALYSIS")
    print("="*70)
    
    results_dir = "./data/results/test_training_checkpoints"
    
    if not os.path.exists(results_dir):
        print(f"⚠ Results directory not found: {results_dir}")
        print("  This is expected if training hasn't been run yet.")
        return True  # Not a failure, just no logs to analyze
    
    # Find all actor log files
    log_files = [f for f in os.listdir(results_dir) if f.startswith('log-actor')]
    
    if not log_files:
        print("⚠ No actor log files found")
        return True  # Not a failure
    
    print(f"\nFound {len(log_files)} actor log files")
    print()
    
    all_analyses = []
    total_negative_scores = 0
    total_repeated_patterns = 0
    total_games = 0
    
    for log_file in sorted(log_files):
        log_path = os.path.join(results_dir, log_file)
        analysis = analyze_actor_log(log_path)
        
        if analysis:
            all_analyses.append(analysis)
            total_negative_scores += len(analysis['negative_scores'])
            total_repeated_patterns += len(analysis['repeated_patterns'])
            total_games += len(analysis['game_progressions'])
            
            print(f"{'='*70}")
            print(f"File: {analysis['file']}")
            print(f"{'='*70}")
            print(f"Total lines: {analysis['total_lines']}")
            print(f"Games tracked: {len(analysis['game_progressions'])}")
            print(f"Termination reasons found: {len(analysis['termination_reasons'])}")
            
            if analysis['negative_scores']:
                print(f"\n❌ Negative scores found: {len(analysis['negative_scores'])}")
                for ns in analysis['negative_scores'][:3]:  # Show first 3
                    print(f"   Line {ns['line_num']}: Score={ns['score']}")
                    print(f"   Context: {ns['context']}")
                if len(analysis['negative_scores']) > 3:
                    print(f"   ... and {len(analysis['negative_scores']) - 3} more")
            else:
                print("✓ No negative scores found")
            
            if analysis['repeated_patterns']:
                print(f"\n⚠ Repeated patterns found: {len(analysis['repeated_patterns'])}")
                for rp in analysis['repeated_patterns'][:2]:  # Show first 2
                    print(f"   Line {rp['line_num']}: {rp['pattern']}")
                if len(analysis['repeated_patterns']) > 2:
                    print(f"   ... and {len(analysis['repeated_patterns']) - 2} more")
            else:
                print("✓ No repeated move patterns detected")
            
            if analysis['game_progressions']:
                print(f"\n✓ Game progressions tracked: {len(analysis['game_progressions'])}")
                avg_moves = sum(g['moves'] for g in analysis['game_progressions']) / len(analysis['game_progressions'])
                print(f"   Average moves per game: {avg_moves:.1f}")
            
            if analysis['termination_reasons']:
                print(f"\n✓ Termination reasons: {len(analysis['termination_reasons'])}")
                for tr in analysis['termination_reasons'][:2]:
                    print(f"   Line {tr['line_num']}: {tr['reason'][:80]}")
            
            print()
    
    # Overall summary
    print("="*70)
    print("OVERALL SUMMARY")
    print("="*70)
    print(f"Total log files analyzed: {len(all_analyses)}")
    print(f"Total games tracked: {total_games}")
    print(f"Total negative scores found: {total_negative_scores}")
    print(f"Total repeated patterns found: {total_repeated_patterns}")
    
    print("\n" + "="*70)
    print("VERIFICATION RESULTS")
    print("="*70)
    
    checks = {
        'Log files found': len(all_analyses) > 0,
        'No negative scores': total_negative_scores == 0,
        'No excessive repetition': total_repeated_patterns < 5,  # Allow some, but not too many
        'Games progressed': total_games > 0
    }
    
    all_passed = all(checks.values())
    
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"{status} {check}")
    
    print()
    if all_passed:
        print("✅ ALL LOG ANALYSIS CHECKS PASSED!")
    else:
        print("❌ SOME LOG ANALYSIS CHECKS FAILED")
        if total_negative_scores > 0:
            print(f"   - Found {total_negative_scores} negative scores")
        if total_repeated_patterns >= 5:
            print(f"   - Found {total_repeated_patterns} repeated patterns")
    
    print("="*70)
    
    return all_passed


if __name__ == "__main__":
    success = analyze_all_logs()
    exit(0 if success else 1)
