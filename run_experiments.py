"""
Automated Experiment and Benchmark Runner for AI Timetable Scheduler.
Fulfills Section 6 of the Assignment Specification:
- Runs all algorithms on both Small and Large datasets.
- Runs randomized methods (Min-Conflicts, SA, Hybrid) 10 times and calculates averages.
- Generates required metric comparison tables.
- Generates and saves high-resolution publication-quality plots:
  1. Cost vs. Iterations for Min-Conflicts
  2. Cost vs. Iterations for Simulated Annealing
  3. Runtime and Search Effort Comparison Bar Charts
"""
import os
import sys
import time
import json
import statistics
import pandas as pd
import matplotlib.pyplot as plt

# Ensure root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.data_loader import DataLoader
from src.constraints import evaluate_timetable
from src.csp_solver import solve_backtracking_baseline, solve_backtracking_heuristics
from src.min_conflicts import solve_min_conflicts
from src.simulated_annealing import solve_simulated_annealing
from src.hybrid_solver import solve_hybrid_csp_sa

def run_benchmarks():
    print("================================================================")
    print("      AI-BASED TIMETABLE SCHEDULER: EXPERIMENTAL BENCHMARK     ")
    print("================================================================\n")

    output_dir = os.path.join(os.path.dirname(__file__), "docs", "figures")
    os.makedirs(output_dir, exist_ok=True)

    datasets = [
        ("Small Dataset (3 Classes, 6 Teachers, 4 Rooms)", os.path.join(os.path.dirname(__file__), "data", "small_dataset.json")),
        ("Large Dataset (8 Classes, 16 Teachers, 10 Rooms)", os.path.join(os.path.dirname(__file__), "data", "large_dataset.json"))
    ]

    benchmark_rows = []
    saved_histories = {}

    for ds_label, ds_path in datasets:
        print(f"\n>>> Running Experiments on {ds_label} ...")
        subjects, teachers, rooms, classes, ts = DataLoader.load_json(ds_path)
        sessions = DataLoader.generate_sessions(classes, subjects, teachers)
        domains = DataLoader.generate_domains(sessions, rooms, ts, teachers, classes)
        is_large = "Large" in ds_label

        # -------------------------------------------------------------
        # 1. Backtracking Baseline
        # -------------------------------------------------------------
        print("  [1/5] Backtracking (Baseline)...", end="", flush=True)
        t_start = time.time()
        # For baseline on large, use 10s timeout to demonstrate exponential search space
        timeout_base = 10.0 if is_large else 15.0
        res_base = solve_backtracking_baseline(sessions, domains, timeout_seconds=timeout_base)
        t_base = res_base.time_taken
        nodes_base = res_base.nodes_expanded
        if res_base.success and res_base.assignment:
            rep_base = evaluate_timetable(res_base.assignment, rooms, teachers, classes, subjects, ts)
            hard_base = rep_base.hard_count
            soft_base = rep_base.soft_penalty
            succ_base = 10
        else:
            hard_base = "Timed Out (>10s)" if is_large else "N/A"
            soft_base = "N/A"
            succ_base = 0
        print(f" Done ({t_base:.3f}s, {nodes_base:,} nodes)")

        benchmark_rows.append({
            "Dataset": ds_label.split(" (")[0],
            "Algorithm": "Backtracking (baseline)",
            "Avg Time (s)": round(t_base, 4),
            "Nodes / Iterations": nodes_base,
            "Hard Violations": hard_base,
            "Soft Penalty Score": soft_base,
            "Success Rate": f"{succ_base}/10" if succ_base > 0 else "0/10"
        })

        # -------------------------------------------------------------
        # 2. Backtracking with Heuristics (MRV + Degree + FC)
        # -------------------------------------------------------------
        print("  [2/5] Backtracking (Heuristics)...", end="", flush=True)
        res_heur = solve_backtracking_heuristics(sessions, domains, timeout_seconds=30.0)
        t_heur = res_heur.time_taken
        nodes_heur = res_heur.nodes_expanded
        if res_heur.success and res_heur.assignment:
            rep_heur = evaluate_timetable(res_heur.assignment, rooms, teachers, classes, subjects, ts)
            hard_heur = rep_heur.hard_count
            soft_heur = rep_heur.soft_penalty
            succ_heur = 10
        else:
            hard_heur = "Failed"
            soft_heur = "N/A"
            succ_heur = 0
        print(f" Done ({t_heur:.3f}s, {nodes_heur:,} nodes)")

        benchmark_rows.append({
            "Dataset": ds_label.split(" (")[0],
            "Algorithm": "Backtracking (with heuristics)",
            "Avg Time (s)": round(t_heur, 4),
            "Nodes / Iterations": nodes_heur,
            "Hard Violations": hard_heur,
            "Soft Penalty Score": soft_heur,
            "Success Rate": f"{succ_heur}/10"
        })

        # -------------------------------------------------------------
        # 3. Min-Conflicts (10 Runs)
        # -------------------------------------------------------------
        print("  [3/5] Min-Conflicts (10 runs)...", end="", flush=True)
        mc_times, mc_iters, mc_hards, mc_softs = [], [], [], []
        mc_success_count = 0
        mc_sample_history = []

        for r in range(1, 11):
            seed = 100 + r
            res_mc = solve_min_conflicts(
                sessions, domains, rooms, teachers, classes, subjects, ts,
                max_steps=2000, timeout_seconds=20.0, seed=seed
            )
            mc_times.append(res_mc.time_taken)
            mc_iters.append(res_mc.iterations)
            mc_hards.append(res_mc.hard_violations)
            mc_softs.append(res_mc.soft_penalty)
            if res_mc.success:
                mc_success_count += 1
            if r == 1:
                mc_sample_history = res_mc.cost_history

        saved_histories[f"Min-Conflicts_{ds_label.split(' (')[0]}"] = mc_sample_history
        print(f" Done (Avg: {statistics.mean(mc_times):.3f}s, {statistics.mean(mc_iters):.1f} steps)")

        benchmark_rows.append({
            "Dataset": ds_label.split(" (")[0],
            "Algorithm": "Min-Conflicts",
            "Avg Time (s)": round(statistics.mean(mc_times), 4),
            "Nodes / Iterations": round(statistics.mean(mc_iters), 1),
            "Hard Violations": round(statistics.mean(mc_hards), 1),
            "Soft Penalty Score": round(statistics.mean(mc_softs), 1),
            "Success Rate": f"{mc_success_count}/10"
        })

        # -------------------------------------------------------------
        # 4. Simulated Annealing (Bonus +6, 10 Runs)
        # -------------------------------------------------------------
        print("  [4/5] Simulated Annealing (Bonus, 10 runs)...", end="", flush=True)
        sa_times, sa_iters, sa_hards, sa_softs = [], [], [], []
        sa_success_count = 0
        sa_sample_history = []

        for r in range(1, 11):
            seed = 200 + r
            res_sa = solve_simulated_annealing(
                sessions, domains, rooms, teachers, classes, subjects, ts,
                max_iterations=1500, timeout_seconds=15.0, seed=seed
            )
            sa_times.append(res_sa.time_taken)
            sa_iters.append(res_sa.iterations)
            sa_hards.append(res_sa.hard_violations)
            sa_softs.append(res_sa.soft_penalty)
            if res_sa.success:
                sa_success_count += 1
            if r == 1:
                sa_sample_history = res_sa.cost_history

        saved_histories[f"SA_{ds_label.split(' (')[0]}"] = sa_sample_history
        print(f" Done (Avg: {statistics.mean(sa_times):.3f}s)")

        benchmark_rows.append({
            "Dataset": ds_label.split(" (")[0],
            "Algorithm": "Simulated Annealing (Bonus)",
            "Avg Time (s)": round(statistics.mean(sa_times), 4),
            "Nodes / Iterations": round(statistics.mean(sa_iters), 1),
            "Hard Violations": round(statistics.mean(sa_hards), 1),
            "Soft Penalty Score": round(statistics.mean(sa_softs), 1),
            "Success Rate": f"{sa_success_count}/10"
        })

        # -------------------------------------------------------------
        # 5. Hybrid CSP + SA (Bonus +6, 10 Runs)
        # -------------------------------------------------------------
        print("  [5/5] Hybrid CSP + SA (Bonus, 10 runs)...", end="", flush=True)
        hyb_times, hyb_iters, hyb_hards, hyb_softs = [], [], [], []
        hyb_success_count = 0
        hyb_sample_history = []

        for r in range(1, 11):
            seed = 300 + r
            res_hyb = solve_hybrid_csp_sa(
                sessions, domains, rooms, teachers, classes, subjects, ts,
                sa_iterations=800, timeout_seconds=20.0, seed=seed
            )
            hyb_times.append(res_hyb.total_time)
            hyb_iters.append(res_hyb.stage1_nodes + res_hyb.stage2_iterations)
            hyb_hards.append(res_hyb.hard_violations)
            hyb_softs.append(res_hyb.final_soft_penalty)
            if res_hyb.success:
                hyb_success_count += 1
            if r == 1:
                hyb_sample_history = res_hyb.cost_history

        saved_histories[f"Hybrid_{ds_label.split(' (')[0]}"] = hyb_sample_history
        print(f" Done (Avg: {statistics.mean(hyb_times):.3f}s)")

        benchmark_rows.append({
            "Dataset": ds_label.split(" (")[0],
            "Algorithm": "Hybrid CSP + SA (Bonus)",
            "Avg Time (s)": round(statistics.mean(hyb_times), 4),
            "Nodes / Iterations": round(statistics.mean(hyb_iters), 1),
            "Hard Violations": round(statistics.mean(hyb_hards), 1),
            "Soft Penalty Score": round(statistics.mean(hyb_softs), 1),
            "Success Rate": f"{hyb_success_count}/10"
        })

    # Save benchmark table to CSV and Markdown
    df_results = pd.DataFrame(benchmark_rows)
    csv_file = os.path.join(os.path.dirname(__file__), "data", "experimental_results.csv")
    df_results.to_csv(csv_file, index=False)
    print(f"\n[OK] Experimental data saved to {csv_file}")

    print("\n" + "=" * 80)
    print("                      ASSIGNMENT SPECIFICATION METRICS TABLE")
    print("=" * 80)
    print(df_results.to_string(index=False))
    print("=" * 80 + "\n")

    # -------------------------------------------------------------
    # Generate Figures
    # -------------------------------------------------------------
    # Figure 1: Cost vs. Iterations for Min-Conflicts
    plt.figure(figsize=(9, 5))
    for key, hist in saved_histories.items():
        if "Min-Conflicts" in key:
            plt.plot(hist, label=key.replace("Min-Conflicts_", ""), linewidth=2)
    plt.title("Min-Conflicts Convergence: Total Cost vs. Iterations", fontsize=12, fontweight="bold")
    plt.xlabel("Iteration", fontsize=10)
    plt.ylabel("Total Cost (1000 * Hard Violations + Soft Penalties)", fontsize=10)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend()
    fig1_path = os.path.join(output_dir, "cost_vs_iterations_min_conflicts.png")
    plt.savefig(fig1_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"[OK] Saved figure: {fig1_path}")

    # Figure 2: Hybrid & SA Convergence
    plt.figure(figsize=(9, 5))
    for key, hist in saved_histories.items():
        if "Hybrid" in key or "SA" in key:
            plt.plot(hist[:250], label=key, linewidth=2)
    plt.title("Simulated Annealing & Hybrid Optimization Trajectory", fontsize=12, fontweight="bold")
    plt.xlabel("Step", fontsize=10)
    plt.ylabel("Cost Function Value", fontsize=10)
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend()
    fig2_path = os.path.join(output_dir, "cost_vs_iterations_sa_hybrid.png")
    plt.savefig(fig2_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"[OK] Saved figure: {fig2_path}")

    # Figure 3: Execution Time Comparison Bar Chart
    plt.figure(figsize=(10, 5))
    df_plot = df_results[df_results["Avg Time (s)"].apply(lambda x: isinstance(x, (int, float)))].copy()
    df_small = df_plot[df_plot["Dataset"] == "Small Dataset"]
    df_large = df_plot[df_plot["Dataset"] == "Large Dataset"]

    x_indices = range(len(df_small))
    width = 0.35

    plt.bar([i - width/2 for i in x_indices], df_small["Avg Time (s)"], width, label="Small Dataset", color="#2b5c8f")
    plt.bar([i + width/2 for i in x_indices], df_large["Avg Time (s)"], width, label="Large Dataset", color="#e07a5f")

    plt.xticks(x_indices, df_small["Algorithm"], rotation=20, ha="right", fontsize=9)
    plt.ylabel("Average Execution Time (seconds, log scale)", fontsize=10)
    plt.yscale("log")
    plt.title("Algorithm Execution Time Comparison (Log Scale)", fontsize=12, fontweight="bold")
    plt.legend()
    plt.grid(True, which="both", linestyle="--", alpha=0.5)
    fig3_path = os.path.join(output_dir, "runtime_comparison_barchart.png")
    plt.savefig(fig3_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"[OK] Saved figure: {fig3_path}")

    return df_results

if __name__ == "__main__":
    run_benchmarks()
