import json
import math
import numpy as np
import scipy.stats as st

def analyze_phase_telemetry(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    details = data["details"]
    n_pairs = len(details)
    phases = ["opening", "midgame", "pre_endgame", "endgame"]

    total_per_game_spreads = [d["net_spread"] / 2.0 for d in details]

    print(f"Loaded {n_pairs} duplicate pairs from {file_path}")
    print(f"Overall Net Spread: {np.mean(total_per_game_spreads):+.2f} pts/game")

    phase_stats = {}
    for ph in phases:
        spreads = [d["phase_spreads"][ph] for d in details]
        mean_s = float(np.mean(spreads))
        std_s = float(np.std(spreads, ddof=1))
        se_s = std_s / math.sqrt(n_pairs)
        t_stat = mean_s / se_s if se_s > 0 else 0.0
        p_val_t = float(st.t.sf(abs(t_stat), df=n_pairs - 1) * 2.0)
        ci95_s = 1.95996 * se_s

        wins = sum(1 for s in spreads if s > 0)
        losses = sum(1 for s in spreads if s < 0)
        draws = sum(1 for s in spreads if s == 0)
        p_hat = (wins + 0.5 * draws) / n_pairs

        # Two proportion z-test against 0.50
        p0 = 0.50
        se_z = math.sqrt(p0 * (1.0 - p0) / n_pairs)
        z_stat = (p_hat - p0) / se_z
        p_val_z = float(st.norm.sf(abs(z_stat)) * 2.0)

        # Wilson interval
        z = 1.95996
        denom = 1.0 + (z**2) / n_pairs
        center = (p_hat + (z**2) / (2.0 * n_pairs)) / denom
        margin = (z * math.sqrt((p_hat * (1.0 - p_hat) / n_pairs) + (z**2) / (4.0 * (n_pairs**2)))) / denom
        wilson_lower = center - margin
        wilson_upper = center + margin

        # Correlation with total margin
        corr, corr_p = st.pearsonr(spreads, total_per_game_spreads)

        phase_stats[ph] = {
            "mean_spread_pts": round(mean_s, 2),
            "std_spread_pts": round(std_s, 2),
            "se_spread_pts": round(se_s, 2),
            "ci95_spread_pts": [round(mean_s - ci95_s, 2), round(mean_s + ci95_s, 2)],
            "t_statistic": round(t_stat, 2),
            "p_value_t": float(f"{p_val_t:.4e}"),
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "win_rate": round(p_hat * 100.0, 2),
            "z_statistic": round(z_stat, 2),
            "p_value_z": float(f"{p_val_z:.4e}"),
            "wilson_ci95": [round(wilson_lower * 100.0, 2), round(wilson_upper * 100.0, 2)],
            "pearson_r_with_total": round(corr, 3),
            "pearson_p": float(f"{corr_p:.4e}"),
        }

        print(f"\nPhase: {ph.upper()}")
        print(f"  Spread: {mean_s:+.2f} ± {ci95_s:.2f} pts (SE={se_s:.2f}, t={t_stat:.2f}, p={p_val_t:.4f})")
        print(f"  Record: {wins}W - {losses}L - {draws}D (WR: {p_hat*100:.1f}%, Z={z_stat:.2f}, p={p_val_z:.4f})")
        print(f"  Wilson 95% CI: [{wilson_lower*100:.1f}%, {wilson_upper*100:.1f}%]")
        print(f"  Pearson r with total spread: {corr:.3f} (p={corr_p:.4f})")

    return phase_stats

if __name__ == "__main__":
    analyze_phase_telemetry("data/tournaments/run_20261109_171805_V4-Champion_vs_Base-MAGPIE_80g_dup_m2_phase_sensitivity.json")
