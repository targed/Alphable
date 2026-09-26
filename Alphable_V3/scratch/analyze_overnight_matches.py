"""
Analyze the overnight series against HastyBot:
- 75 completed matches
- 69 with full Macondo engine analysis
- Complete breakdown of performance, bingos, leaves, exchanges, and blunders.
"""
import glob
import json
import os
import re
import statistics
from collections import defaultdict

def parse_gcg(gcg_path):
    """
    Parse a GCG file to extract players and turn history.
    """
    if not os.path.exists(gcg_path):
        return None
    
    with open(gcg_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
        
    p1, p2 = None, None
    moves = []
    
    for line in lines:
        line = line.strip()
        if line.startswith('#player1'):
            parts = line.split()
            if len(parts) >= 2:
                p1 = parts[1]
        elif line.startswith('#player2'):
            parts = line.split()
            if len(parts) >= 2:
                p2 = parts[1]
        elif line.startswith('>'):
            # Example turn line:
            # >HastyBot: BFJLRRT -BFJLRT +0 0
            # >kwgccvimcnigrudnyn: ALNNSTX 8G LANX +22 22
            # >kwgccvimcnigrudnyn: (LRT) +6 492
            # >kwgccvimcnigrudnyn: - +0 350 (pass)
            m = re.match(r'>([^:]+):\s*([^\s]+)?\s+(.+)', line)
            if not m:
                continue
            player = m.group(1).strip()
            rest = line[len(player) + 2:].strip()
            
            # Check for end-game deduction line: e.g. >HastyBot: (LRT) +6 492
            end_m = re.match(r'\((\w+)\)\s+([+-]\d+)\s+(\d+)', rest)
            if end_m:
                moves.append({
                    'player': player,
                    'is_end_deduction': True,
                    'rack_remaining': end_m.group(1),
                    'pts': int(end_m.group(2)),
                    'cum_score': int(end_m.group(3))
                })
                continue
                
            tokens = rest.split()
            if len(tokens) >= 3:
                rack = tokens[0]
                # last token is cumulative score
                try:
                    cum_score = int(tokens[-1])
                    pts_token = tokens[-2]
                    pts = int(pts_token.replace('+', '')) if pts_token.startswith('+') or pts_token.startswith('-') else 0
                    play_tokens = tokens[1:-2]
                    play_str = " ".join(play_tokens)
                    is_exchange = play_str.startswith('-')
                    is_pass = play_str == '-'
                    is_bingo = (pts >= 50 and len(rack) == 7 and not is_exchange and not is_pass)
                    
                    moves.append({
                        'player': player,
                        'is_end_deduction': False,
                        'rack': rack,
                        'play': play_str,
                        'pts': pts,
                        'cum_score': cum_score,
                        'is_exchange': is_exchange,
                        'is_pass': is_pass,
                        'is_bingo': is_bingo
                    })
                except Exception:
                    continue
                    
    return {'p1': p1, 'p2': p2, 'moves': moves}

def run_analysis():
    files = sorted(list(set(glob.glob('data/woogles/summaries/run_20260925_*_summary.json') + glob.glob('data/woogles/summaries/run_20260926_*_summary.json'))))
    overnight_files = [f for f in files if os.path.basename(f) >= 'run_20260925_234142']
    
    matches_dict = {}
    for f in overnight_files:
        with open(f) as fp:
            d = json.load(fp)
        mid = d.get('match_id')
        s0, s1 = d.get('final_score', [0, 0])
        if s0 + s1 > 200:
            matches_dict[mid] = d

    print(f"Total Unique Valid Matches Analyzed: {len(matches_dict)}")
    
    alphable_wins = 0
    hasty_wins = 0
    draws = 0
    
    alphable_scores = []
    hasty_scores = []
    score_diffs = []
    
    alphable_bingos_list = []
    hasty_bingos_list = []
    
    alphable_turns_pts = []
    hasty_turns_pts = []
    
    alphable_exchanges = 0
    hasty_exchanges = 0
    
    alphable_moves_count = 0
    hasty_moves_count = 0
    
    # Analyze GCG files
    for mid, mdata in matches_dict.items():
        s0, s1 = mdata['final_score']
        alphable_scores.append(s0)
        hasty_scores.append(s1)
        score_diffs.append(s0 - s1)
        
        winner = mdata['winner']
        if winner == 'kwgccvimcnigrudnyn':
            alphable_wins += 1
        elif winner == 'HastyBot':
            hasty_wins += 1
        else:
            draws += 1
            
        gcg_path = mdata.get('gcg_file')
        if not gcg_path or not os.path.exists(gcg_path):
            gcg_path = os.path.join(mdata.get('match_folder', ''), 'game.gcg')
            
        if os.path.exists(gcg_path):
            parsed = parse_gcg(gcg_path)
            if parsed and parsed['moves']:
                a_bingos = 0
                h_bingos = 0
                for mv in parsed['moves']:
                    if mv.get('is_end_deduction'):
                        continue
                    is_alphable = (mv['player'] == 'kwgccvimcnigrudnyn')
                    if is_alphable:
                        alphable_moves_count += 1
                        alphable_turns_pts.append(mv['pts'])
                        if mv['is_bingo']:
                            a_bingos += 1
                        if mv['is_exchange']:
                            alphable_exchanges += 1
                    else:
                        hasty_moves_count += 1
                        hasty_turns_pts.append(mv['pts'])
                        if mv['is_bingo']:
                            h_bingos += 1
                        if mv['is_exchange']:
                            hasty_exchanges += 1
                alphable_bingos_list.append(a_bingos)
                hasty_bingos_list.append(h_bingos)

    print("\n" + "="*60)
    print("MATCH PERFORMANCE METRICS")
    print("="*60)
    print(f"Total Matches: {len(matches_dict)}")
    print(f"Alphable Wins: {alphable_wins} ({alphable_wins/len(matches_dict)*100:.1f}%)")
    print(f"HastyBot Wins: {hasty_wins} ({hasty_wins/len(matches_dict)*100:.1f}%)")
    print(f"Draws: {draws}")
    print(f"Mean Alphable Score: {statistics.mean(alphable_scores):.1f} ± {statistics.stdev(alphable_scores):.1f} (Min: {min(alphable_scores)}, Max: {max(alphable_scores)})")
    print(f"Mean HastyBot Score: {statistics.mean(hasty_scores):.1f} ± {statistics.stdev(hasty_scores):.1f} (Min: {min(hasty_scores)}, Max: {max(hasty_scores)})")
    print(f"Mean Score Margin: {statistics.mean(score_diffs):.1f} (Median: {statistics.median(score_diffs):.1f})")

    if alphable_bingos_list:
        print("\n" + "="*60)
        print("BINGO & SCORING METRICS (From 71 GCG files)")
        print("="*60)
        print(f"Mean Bingos/Game - Alphable: {statistics.mean(alphable_bingos_list):.2f} (Total: {sum(alphable_bingos_list)})")
        print(f"Mean Bingos/Game - HastyBot: {statistics.mean(hasty_bingos_list):.2f} (Total: {sum(hasty_bingos_list)})")
        print(f"Mean Points/Turn - Alphable: {statistics.mean(alphable_turns_pts):.2f}")
        print(f"Mean Points/Turn - HastyBot: {statistics.mean(hasty_turns_pts):.2f}")
        print(f"Total Exchanges - Alphable: {alphable_exchanges} ({alphable_exchanges/alphable_moves_count*100:.1f}% of turns)")
        print(f"Total Exchanges - HastyBot: {hasty_exchanges} ({hasty_exchanges/hasty_moves_count*100:.1f}% of turns)")
        
        # Turn point distribution
        print("\nPoint Distributions per Move:")
        def get_dist(pts_list):
            d = {'0 (Exch/Pass)': 0, '1-19': 0, '20-39': 0, '40-59': 0, '60+': 0}
            for p in pts_list:
                if p == 0:
                    d['0 (Exch/Pass)'] += 1
                elif p < 20:
                    d['1-19'] += 1
                elif p < 40:
                    d['20-39'] += 1
                elif p < 60:
                    d['40-59'] += 1
                else:
                    d['60+'] += 1
            return {k: f"{v} ({v/len(pts_list)*100:.1f}%)" for k, v in d.items()}
            
        print("Alphable Move Distribution:", get_dist(alphable_turns_pts))
        print("HastyBot Move Distribution:", get_dist(hasty_turns_pts))

    # Now Analyze Macondo Engine Sugggestions from analysis.json
    print("\n" + "="*60)
    print("MACONDO ENGINE EQUITY & BLUNDER ANALYSIS (From 69 Games)")
    print("="*60)
    
    alphable_equity_losses = []
    hasty_equity_losses = []
    
    blunders_by_loss = defaultdict(int) # loss > 5, 10, 20, 30
    alphable_missed_bingos = 0
    total_alphable_analyzed_turns = 0
    
    # Store individual large blunders for review
    notable_blunders = []
    
    for mid, mdata in matches_dict.items():
        analysis_path = os.path.join(mdata.get('match_folder', ''), 'analysis.json')
        replay_path = os.path.join(mdata.get('match_folder', ''), 'replay.json')
        gcg_path = os.path.join(mdata.get('match_folder', ''), 'game.gcg')
        
        if not os.path.exists(analysis_path) or not os.path.exists(gcg_path):
            continue
            
        with open(analysis_path) as af:
            analysis_data = json.load(af)
            
        parsed = parse_gcg(gcg_path)
        if not parsed or not parsed['moves']:
            continue
            
        moves = [m for m in parsed['moves'] if not m.get('is_end_deduction')]
        
        # In Woogles analysis, each entry corresponds to a turn
        for turn_idx, entry in enumerate(analysis_data):
            if turn_idx >= len(moves):
                break
            mv = moves[turn_idx]
            is_alphable = (mv['player'] == 'kwgccvimcnigrudnyn')
            suggestions = entry.get('suggestions', [])
            if not suggestions:
                continue
                
            best_equity = suggestions[0]['equity']
            
            # Find the played move in suggestions or estimate its equity
            played_word = mv['play']
            # Find matching suggestion
            matched_sugg = None
            for s in suggestions:
                # Normal move
                w = s.get('word', '')
                coords = s.get('coords', '')
                if mv['is_exchange']:
                    if 'Exch.' in w:
                        matched_sugg = s
                        break
                elif mv['is_pass']:
                    if w == 'Pass':
                        matched_sugg = s
                        break
                else:
                    # e.g. "8G LANX" or word contains played letters
                    clean_w = w.replace('.', '').upper()
                    clean_play = played_word.replace('.', '').upper()
                    if clean_w in clean_play or clean_play in clean_w or (coords and coords in played_word):
                        matched_sugg = s
                        break
                        
            if matched_sugg:
                played_equity = matched_sugg['equity']
            else:
                # If move not in top 10 suggestions, lower bound equity loss
                last_sugg_equity = suggestions[-1]['equity']
                played_equity = last_sugg_equity - 2.0 # conservative estimate
                
            equity_loss = best_equity - played_equity
            if equity_loss < 0:
                equity_loss = 0.0
                
            if is_alphable:
                alphable_equity_losses.append(equity_loss)
                total_alphable_analyzed_turns += 1
                if equity_loss > 5.0:
                    blunders_by_loss['Loss > 5 pts'] += 1
                if equity_loss > 10.0:
                    blunders_by_loss['Loss > 10 pts'] += 1
                if equity_loss > 20.0:
                    blunders_by_loss['Loss > 20 pts'] += 1
                if equity_loss > 30.0:
                    blunders_by_loss['Loss > 30 pts'] += 1
                    
                # Check if best suggestion was a bingo (>= 50 pts) and Alphable played a non-bingo
                if suggestions[0].get('points', 0) >= 50 and not mv['is_bingo']:
                    alphable_missed_bingos += 1
                    notable_blunders.append({
                        'match_id': mid,
                        'turn': turn_idx + 1,
                        'rack': mv['rack'],
                        'played': mv['play'],
                        'played_pts': mv['pts'],
                        'best_word': suggestions[0].get('word'),
                        'best_coords': suggestions[0].get('coords'),
                        'best_pts': suggestions[0].get('points'),
                        'loss': equity_loss
                    })
            else:
                hasty_equity_losses.append(equity_loss)

    print(f"Analyzed Turns - Alphable: {len(alphable_equity_losses)}, HastyBot: {len(hasty_equity_losses)}")
    print(f"Mean Equity Loss/Turn - Alphable: {statistics.mean(alphable_equity_losses):.2f} pts")
    print(f"Mean Equity Loss/Turn - HastyBot: {statistics.mean(hasty_equity_losses):.2f} pts")
    print(f"Alphable Total Equity Sacrificed per Game (~12 turns): {statistics.mean(alphable_equity_losses)*12:.1f} pts!")
    print(f"HastyBot Total Equity Sacrificed per Game (~12 turns): {statistics.mean(hasty_equity_losses)*12:.1f} pts")
    
    print("\nAlphable Blunder Frequency:")
    for k, v in blunders_by_loss.items():
        print(f"  {k}: {v} times ({v/total_alphable_analyzed_turns*100:.1f}% of turns)")
        
    print(f"\nAlphable Missed Bingos (Engine found a 50+ pt play, Alphable played non-bingo): {alphable_missed_bingos}")
    
    print("\nSample Notable Missed Bingos & Major Blunders:")
    for b in notable_blunders[:8]:
        print(f"  Match {b['match_id']} (Turn {b['turn']}): Rack=[{b['rack']}]")
        print(f"    Played: {b['played']} (+{b['played_pts']} pts)")
        print(f"    Best Engine: {b['best_coords']} {b['best_word']} (+{b['best_pts']} pts) | Loss: -{b['loss']:.1f} equity")
        print()

if __name__ == '__main__':
    run_analysis()
