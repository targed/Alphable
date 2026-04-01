"""
Integration test: Run full game simulations with random agents.
Tests Requirements: All (comprehensive integration test)

This test plays 10 complete games with random agents and verifies:
- No negative scores occur
- Games terminate properly
- No infinite loops or stuck states
"""
import pyspiel
import numpy as np
import scrabble  # Register the game


def play_random_game(game_num, max_moves=500, verbose=False):
    """
    Play a complete game with random agents.
    Returns game statistics and whether it completed successfully.
    """
    game = pyspiel.load_game("scrabble")
    state = game.new_initial_state()
    
    move_count = 0
    stats = {
        'game_num': game_num,
        'completed': False,
        'moves': 0,
        'final_scores': [0.0, 0.0],
        'min_score_p0': float('inf'),
        'min_score_p1': float('inf'),
        'termination_reason': None,
        'stuck': False,
        'negative_score_detected': False
    }
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Starting Game {game_num}")
        print(f"{'='*60}")
    
    while not state.is_terminal() and move_count < max_moves:
        # Get legal actions
        legal = state.legal_actions()
        
        if not legal:
            if verbose:
                print(f"Move {move_count}: No legal actions available!")
            stats['stuck'] = True
            break
        
        # Choose random action
        action = np.random.choice(legal)
        
        # Track scores before move
        scores_before = list(state.scores)
        
        # Apply action
        state.apply_action(action)
        move_count += 1
        
        # Track minimum scores
        stats['min_score_p0'] = min(stats['min_score_p0'], state.scores[0])
        stats['min_score_p1'] = min(stats['min_score_p1'], state.scores[1])
        
        # Check for negative scores
        if state.scores[0] < 0 or state.scores[1] < 0:
            stats['negative_score_detected'] = True
            if verbose:
                print(f"❌ NEGATIVE SCORE DETECTED at move {move_count}!")
                print(f"   Scores: P0={state.scores[0]:.1f}, P1={state.scores[1]:.1f}")
        
        if verbose and move_count % 50 == 0:
            print(f"Move {move_count}: Scores P0={state.scores[0]:.1f}, P1={state.scores[1]:.1f}")
    
    # Game ended
    stats['moves'] = move_count
    stats['completed'] = state.is_terminal()
    stats['final_scores'] = state.returns()
    stats['termination_reason'] = state.termination_reason
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Game {game_num} Complete")
        print(f"{'='*60}")
        print(f"Moves: {stats['moves']}")
        print(f"Final Scores: P0={stats['final_scores'][0]:.1f}, P1={stats['final_scores'][1]:.1f}")
        print(f"Termination: {stats['termination_reason']}")
        print(f"Min Scores: P0={stats['min_score_p0']:.1f}, P1={stats['min_score_p1']:.1f}")
    
    return stats


def test_full_game_simulations():
    """Run 10 complete games and verify all requirements"""
    print("\n" + "="*70)
    print("INTEGRATION TEST: Full Game Simulations")
    print("="*70)
    print("Running 10 complete games with random agents...")
    print()
    
    num_games = 10
    all_stats = []
    
    for i in range(1, num_games + 1):
        stats = play_random_game(i, verbose=(i == 1))  # Verbose for first game only
        all_stats.append(stats)
        
        # Quick status update
        status = "✓" if stats['completed'] and not stats['negative_score_detected'] else "✗"
        print(f"{status} Game {i}: {stats['moves']} moves, "
              f"Scores=[{stats['final_scores'][0]:.1f}, {stats['final_scores'][1]:.1f}], "
              f"Reason: {stats['termination_reason']}")
    
    print("\n" + "="*70)
    print("VERIFICATION RESULTS")
    print("="*70)
    
    # Verify no negative scores
    negative_scores = [s for s in all_stats if s['negative_score_detected']]
    if negative_scores:
        print(f"❌ FAILED: {len(negative_scores)} games had negative scores")
        for s in negative_scores:
            print(f"   Game {s['game_num']}: Min scores P0={s['min_score_p0']:.1f}, P1={s['min_score_p1']:.1f}")
    else:
        print("✓ PASSED: No negative scores detected in any game")
    
    # Verify all games terminated
    incomplete_games = [s for s in all_stats if not s['completed']]
    if incomplete_games:
        print(f"❌ FAILED: {len(incomplete_games)} games did not terminate properly")
        for s in incomplete_games:
            print(f"   Game {s['game_num']}: {s['moves']} moves, stuck={s['stuck']}")
    else:
        print("✓ PASSED: All games terminated properly")
    
    # Verify no stuck states
    stuck_games = [s for s in all_stats if s['stuck']]
    if stuck_games:
        print(f"❌ FAILED: {len(stuck_games)} games got stuck")
        for s in stuck_games:
            print(f"   Game {s['game_num']}: Stuck at move {s['moves']}")
    else:
        print("✓ PASSED: No games got stuck in infinite loops")
    
    # Statistics summary
    print("\n" + "="*70)
    print("STATISTICS SUMMARY")
    print("="*70)
    
    total_moves = sum(s['moves'] for s in all_stats)
    avg_moves = total_moves / num_games
    min_moves = min(s['moves'] for s in all_stats)
    max_moves = max(s['moves'] for s in all_stats)
    
    print(f"Total moves across all games: {total_moves}")
    print(f"Average moves per game: {avg_moves:.1f}")
    print(f"Min moves: {min_moves}")
    print(f"Max moves: {max_moves}")
    
    # Score statistics
    all_final_scores = [score for s in all_stats for score in s['final_scores']]
    avg_final_score = sum(all_final_scores) / len(all_final_scores)
    min_final_score = min(all_final_scores)
    max_final_score = max(all_final_scores)
    
    print(f"\nFinal score statistics:")
    print(f"Average final score: {avg_final_score:.1f}")
    print(f"Min final score: {min_final_score:.1f}")
    print(f"Max final score: {max_final_score:.1f}")
    
    # Termination reasons
    print(f"\nTermination reasons:")
    termination_counts = {}
    for s in all_stats:
        reason = s['termination_reason'] or 'Unknown'
        termination_counts[reason] = termination_counts.get(reason, 0) + 1
    
    for reason, count in sorted(termination_counts.items(), key=lambda x: -x[1]):
        print(f"  {reason}: {count} games")
    
    # Overall result
    print("\n" + "="*70)
    all_passed = (len(negative_scores) == 0 and 
                  len(incomplete_games) == 0 and 
                  len(stuck_games) == 0)
    
    if all_passed:
        print("✅ ALL INTEGRATION TESTS PASSED!")
    else:
        print("❌ SOME INTEGRATION TESTS FAILED")
        print("\nFailure summary:")
        if negative_scores:
            print(f"  - {len(negative_scores)} games with negative scores")
        if incomplete_games:
            print(f"  - {len(incomplete_games)} games did not terminate")
        if stuck_games:
            print(f"  - {len(stuck_games)} games got stuck")
    
    print("="*70)
    
    # Assert for test framework
    assert len(negative_scores) == 0, f"{len(negative_scores)} games had negative scores"
    assert len(incomplete_games) == 0, f"{len(incomplete_games)} games did not terminate"
    assert len(stuck_games) == 0, f"{len(stuck_games)} games got stuck"
    
    return all_stats


if __name__ == "__main__":
    test_full_game_simulations()
