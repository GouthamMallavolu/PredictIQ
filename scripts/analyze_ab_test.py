"""
Analyze A/B Test Results

This script reads the A/B test log file and performs a statistical analysis
to determine if there is a significant difference between the variants.
"""
import json
import pandas as pd
from statsmodels.stats.proportion import proportions_ztest
import numpy as np
import argparse

LOG_FILE_PATH = "logs/ab_test_results.jsonl"

def analyze_ab_test_results(log_file: str = LOG_FILE_PATH):
    """
    Analyzes the A/B test results from the log file.

    Args:
        log_file: Path to the A/B test log file.
    """
    try:
        with open(log_file, 'r') as f:
            records = [json.loads(line) for line in f]
        df = pd.DataFrame(records)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading or parsing log file: {e}")
        return

    if df.empty:
        print("No A/B test data to analyze.")
        return

    # --- KPI Calculation ---
    summary = df.groupby('variant').agg(
        total_requests=('user_id', 'count'),
        successful_requests=('success', lambda x: x.sum()),
        avg_latency_ms=('latency_ms', 'mean')
    ).reset_index()

    summary['error_rate'] = 1 - (summary['successful_requests'] / summary['total_requests'])

    print("--- A/B Test KPI Summary ---")
    print(summary)
    print("\n" + "="*30 + "\n")

    # --- Statistical Significance Test (Z-test for proportions) ---
    control = summary[summary['variant'] == 'A']
    challenger = summary[summary['variant'] == 'B']

    if control.empty or challenger.empty:
        print("Could not perform statistical test: one or both variants have no data.")
        return

    # We are testing the difference in *successful* requests
    count = np.array([
        control['successful_requests'].iloc[0],
        challenger['successful_requests'].iloc[0]
    ])
    
    nobs = np.array([
        control['total_requests'].iloc[0],
        challenger['total_requests'].iloc[0]
    ])

    if np.any(nobs == 0):
        print("Cannot perform z-test because one group has zero observations.")
        return

    stat, p_value = proportions_ztest(count, nobs, alternative='two-sided')

    print("--- Statistical Test: Two-Proportion Z-Test (for Success Rate) ---")
    print(f"Control (A) Successes: {count[0]} / {nobs[0]}")
    print(f"Challenger (B) Successes: {count[1]} / {nobs[1]}")
    print(f"Z-statistic: {stat:.4f}")
    print(f"P-value: {p_value:.4f}")

    # --- Conclusion ---
    alpha = 0.05  # Significance level
    print(f"\nSignificance level (alpha): {alpha}")

    if p_value < alpha:
        if count[1] / nobs[1] > count[0] / nobs[0]:
            print("Conclusion: The result is statistically significant. Variant B (Challenger) has a higher success rate.")
        else:
            print("Conclusion: The result is statistically significant. Variant A (Control) has a higher success rate.")
    else:
        print("Conclusion: The result is not statistically significant. There is no meaningful difference in success rates between the variants.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze A/B test results.")
    parser.add_argument(
        '--file',
        type=str,
        default=LOG_FILE_PATH,
        help=f"Path to the A/B test log file (default: {LOG_FILE_PATH})"
    )
    args = parser.parse_args()
    
    analyze_ab_test_results(log_file=args.file)
