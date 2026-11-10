import json
import math
import numpy as np
import scipy.stats as st

def analyze_dataset(file_path, name):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    details = data.get("details", [])
    total_games = data.get("total_games", len(details) * 2)
    n_pairs = len(details)

    print(f"=== {name} ===")
    print(f"Total Games: {total_games}, Duplicate Pairs: {n_pairs}")

    if not details:
        print("No detail records found.")
        return data

    pair_net_spreads = [p["net_spread"] for p in details]
    per_game_spreads = [s / 2.0 for s in pair_net_spreads]

    # Spread statistics (per-game spread d_i = net_spread / 2)
    mean_spread = float(np.mean(per_game_spreads))
    std_spread = float(np.std(per_game_spreads, ddof=1))
    se_spread = std_spread / math.sqrt(n_pairs)
    t_stat = mean_spread / se_spread
    df = n_pairs - 1
    p_val_t = float(st.t.sf(abs(t_stat), df=df) * 2.0)
    ci95_spread = 1.95996 * se_spread

    # Win rate statistics
    wins = sum(1 for p in details if p["net_spread"] > 0)
    losses = sum(1 for p in details if p["net_spread"] < 0)
    draws = sum(1 for p in details if p["net_spread"] == 0)
    x = wins + 0.5 * draws
    p_hat = x / n_pairs

    # Two-proportion z-test (H0: p0 = 0.50)
    p0 = 0.50
    se_z = math.sqrt(p0 * (1.0 - p0) / n_pairs)
    z_stat = (p_hat - p0) / se_z
    p_val_z = float(st.norm.sf(abs(z_stat)) * 2.0)

    # Wilson score interval (without continuity correction)
    z = 1.95996
    denom = 1.0 + (z**2) / n_pairs
    center = (p_hat + (z**2) / (2.0 * n_pairs)) / denom
    margin = (z * math.sqrt((p_hat * (1.0 - p_hat) / n_pairs) + (z**2) / (4.0 * (n_pairs**2)))) / denom
    wilson_lower = center - margin
    wilson_upper = center + margin

    # Wilson score interval with continuity correction (Fleiss)
    w_cc_lower = (2*n_pairs*p_hat + z**2 - 1 - z * math.sqrt(z**2 - (2 + 1/n_pairs) + 4*p_hat*(n_pairs*(1-p_hat) + 1))) / (2*(n_pairs + z**2))
    w_cc_upper = (2*n_pairs*p_hat + z**2 + 1 + z * math.sqrt(z**2 + (2 - 1/n_pairs) + 4*p_hat*(n_pairs*(1-p_hat) - 1))) / (2*(n_pairs + z**2))

    # Wald normal approximation interval
    wald_se = math.sqrt(p_hat * (1.0 - p_hat) / n_pairs)
    wald_lower = p_hat - z * wald_se
    wald_upper = p_hat + z * wald_se

    # First move advantage decomposition
    # Game A: P1=Seat 1, P2=Seat 2
    gameA_diffs = [p["p1_gameA_score"] - p["p2_gameA_score"] for p in details]
    # Game B: P2=Seat 1, P1=Seat 2 -> P2 score - P1 score
    gameB_diffs = [p["p2_gameB_score"] - p["p1_gameB_score"] for p in details]

    mean_diff_A = float(np.mean(gameA_diffs))
    mean_diff_B = float(np.mean(gameB_diffs))

    first_move_adv = (mean_diff_A + mean_diff_B) / 2.0
    net_skill_edge = (mean_diff_A - mean_diff_B) / 2.0

    print(f"Wins: {wins}, Losses: {losses}, Draws: {draws}")
    print(f"Win Rate: {p_hat*100:.3f}%")
    print(f"Z-statistic: {z_stat:.4f}, p-val (Z): {p_val_z:.6e}")
    print(f"Wilson 95% CI: [{wilson_lower*100:.2f}%, {wilson_upper*100:.2f}%]")
    print(f"Wilson CC 95% CI: [{w_cc_lower*100:.2f}%, {w_cc_upper*100:.2f}%]")
    print(f"Wald 95% CI: [{wald_lower*100:.2f}%, {wald_upper*100:.2f}%]")
    print(f"Mean Spread (per game): {mean_spread:.4f} pts (SE = {se_spread:.4f})")
    print(f"Spread 95% CI: [{mean_spread - ci95_spread:.2f}, {mean_spread + ci95_spread:.2f}] pts")
    print(f"t-statistic: {t_stat:.4f}, df: {df}, p-val (t): {p_val_t:.6e}")
    print(f"Game A (P1 1st) Margin: {mean_diff_A:.2f} pts")
    print(f"Game B (P2 1st) Margin: {mean_diff_B:.2f} pts")
    print(f"Seat 1 Advantage: {first_move_adv:.2f} pts")
    print(f"Isolated Algorithmic Advantage: {net_skill_edge:.2f} pts")

    # Block analysis if n_pairs >= 1000
    if n_pairs >= 1000:
        block_size = 1000
        n_blocks = n_pairs // block_size
        print(f"\n--- Consistency Across {n_blocks} Blocks of {block_size} Pairs ---")
        for b in range(n_blocks):
            sub = per_game_spreads[b*block_size : (b+1)*block_size]
            sub_details = details[b*block_size : (b+1)*block_size]
            sub_mean = float(np.mean(sub))
            sub_se = float(np.std(sub, ddof=1)) / math.sqrt(len(sub))
            sub_t = sub_mean / sub_se
            sub_w = sum(1 for p in sub_details if p["net_spread"] > 0)
            sub_d = sum(1 for p in sub_details if p["net_spread"] == 0)
            sub_wr = (sub_w + 0.5 * sub_d) / len(sub_details)
            print(f"Block {b+1} (Pairs {b*block_size+1}..{(b+1)*block_size}): WR={sub_wr*100:.2f}%, Spread={sub_mean:+.2f} pts, t={sub_t:.2f}")

    return {
        "n_pairs": n_pairs,
        "total_games": total_games,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "win_rate": p_hat,
        "z_statistic": z_stat,
        "p_value_z": p_val_z,
        "wilson_ci95": [wilson_lower, wilson_upper],
        "wilson_cc_ci95": [w_cc_lower, w_cc_upper],
        "wald_ci95": [wald_lower, wald_upper],
        "mean_spread_per_game": mean_spread,
        "se_spread": se_spread,
        "t_statistic": t_stat,
        "df": df,
        "p_value_t": p_val_t,
        "ci95_spread": [mean_spread - ci95_spread, mean_spread + ci95_spread],
        "first_move_advantage": first_move_adv,
        "net_skill_edge": net_skill_edge,
    }

if __name__ == "__main__":
    analyze_dataset("data/tournaments/run_20261015_215837_V4-Champion_vs_Base-MAGPIE_3000g_dup.json", "3,000-Game Duplicate Benchmark")
    print("\n" + "="*60 + "\n")
    analyze_dataset("data/tournaments/run_20261016_155029_V4-Champion_vs_Base-MAGPIE_10000g_dup.json", "10,000-Game Duplicate Benchmark")
