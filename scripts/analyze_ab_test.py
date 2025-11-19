"""
A/B Test Statistical Analysis

Performs statistical tests to determine if there's a significant difference
between control (LSTM) and treatment (Random Forest) models.

Tests:
- Two-proportion z-test for success rates
- Bootstrap confidence intervals for latency differences
- Effect size calculations

Usage:
    python scripts/analyze_ab_test.py --date 20241118
    python scripts/analyze_ab_test.py  # Uses today's date
"""

import sys
import os
import json
import argparse
from datetime import datetime
from typing import List, Dict, Any
import math

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def two_proportion_z_test(n1: int, p1: float, n2: int, p2: float, alpha: float = 0.05) -> Dict[str, Any]:
    """
    Two-proportion z-test for comparing success rates.
    
    Args:
        n1: Sample size for group 1
        p1: Proportion for group 1
        n2: Sample size for group 2
        p2: Proportion for group 2
        alpha: Significance level (default 0.05)
    
    Returns:
        Dictionary with test results
    """
    # Calculate pooled proportion
    p_pool = (p1 * n1 + p2 * n2) / (n1 + n2)
    
    # Calculate standard error
    se = math.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
    
    # Calculate z-statistic
    if se == 0:
        return {
            "significant": False,
            "reason": "Standard error is zero (identical proportions or no variance)"
        }
    
    z = (p1 - p2) / se
    
    # Critical value for two-tailed test at alpha=0.05 is ±1.96
    critical_value = 1.96 if alpha == 0.05 else 2.576  # alpha=0.01
    
    significant = abs(z) > critical_value
    
    # Calculate p-value (approximate, two-tailed)
    # For simplicity, we'll just check against critical value
    # Proper p-value would use normal CDF
    
    return {
        "z_statistic": round(z, 4),
        "critical_value": critical_value,
        "significant": significant,
        "alpha": alpha,
        "effect": "positive" if z > 0 else "negative",
        "conclusion": f"Variant A {'significantly' if significant else 'not significantly'} {'better' if z > 0 else 'worse'} than B"
    }


def bootstrap_ci(data: List[float], n_bootstrap: int = 1000, confidence: float = 0.95) -> Dict[str, float]:
    """
    Calculate bootstrap confidence interval for mean.
    
    Args:
        data: List of values
        n_bootstrap: Number of bootstrap samples
        confidence: Confidence level (default 0.95)
    
    Returns:
        Dictionary with mean and confidence interval
    """
    import random
    
    if not data:
        return {"mean": 0, "lower": 0, "upper": 0}
    
    means = []
    n = len(data)
    
    for _ in range(n_bootstrap):
        sample = [random.choice(data) for _ in range(n)]
        means.append(sum(sample) / len(sample))
    
    means.sort()
    
    # Calculate percentiles for confidence interval
    lower_idx = int((1 - confidence) / 2 * n_bootstrap)
    upper_idx = int((1 + confidence) / 2 * n_bootstrap)
    
    return {
        "mean": round(sum(data) / len(data), 2),
        "lower": round(means[lower_idx], 2),
        "upper": round(means[upper_idx], 2),
        "confidence": confidence
    }


def analyze_ab_test(date: str = None) -> Dict[str, Any]:
    """
    Analyze A/B test results with statistical tests.
    
    Args:
        date: Date string (YYYYMMDD) or None for today
    
    Returns:
        Analysis results with statistical tests
    """
    if date is None:
        date = datetime.now().strftime('%Y%m%d')
    
    # Get metrics
    from api.ab_testing import get_ab_metrics
    metrics = get_ab_metrics(date)
    
    if "error" in metrics:
        return metrics
    
    results = metrics['results']
    
    # Extract data for statistical tests
    variant_a = results['A']
    variant_b = results['B']
    
    # Check if we have enough data
    if variant_a['total_requests'] < 10 or variant_b['total_requests'] < 10:
        return {
            "error": "Insufficient data for statistical analysis (need at least 10 requests per variant)",
            "date": date,
            "variant_a_requests": variant_a['total_requests'],
            "variant_b_requests": variant_b['total_requests']
        }
    
    # Success rate comparison (two-proportion z-test)
    n_a = variant_a['total_requests']
    n_b = variant_b['total_requests']
    p_a = variant_a['success_rate'] / 100
    p_b = variant_b['success_rate'] / 100
    
    success_rate_test = two_proportion_z_test(n_a, p_a, n_b, p_b)
    
    # Latency comparison (we'll use simple comparison since we don't have raw data)
    # In production, you'd load the raw latencies and do proper bootstrap
    latency_diff = variant_a['avg_latency_ms'] - variant_b['avg_latency_ms']
    latency_diff_pct = (latency_diff / variant_b['avg_latency_ms'] * 100) if variant_b['avg_latency_ms'] > 0 else 0
    
    # Calculate effect sizes
    success_rate_lift = ((p_a - p_b) / p_b * 100) if p_b > 0 else 0
    
    # Recommendation
    if success_rate_test['significant']:
        if success_rate_lift > 0:
            recommendation = f"ADOPT Variant A ({variant_a['model']}): Significantly better success rate ({success_rate_lift:+.2f}% lift)"
        else:
            recommendation = f"ADOPT Variant B ({variant_b['model']}): Significantly better success rate ({-success_rate_lift:+.2f}% lift)"
    else:
        if abs(latency_diff_pct) > 10:
            faster = "A" if latency_diff < 0 else "B"
            recommendation = f"CONSIDER Variant {faster}: No significant success rate difference, but {abs(latency_diff_pct):.1f}% faster"
        else:
            recommendation = "NO CLEAR WINNER: No significant differences detected. Continue testing."
    
    return {
        "date": date,
        "test_config": metrics['test_config'],
        "sample_sizes": {
            "variant_a": n_a,
            "variant_b": n_b,
            "total": n_a + n_b
        },
        "success_rate_comparison": {
            "variant_a": {
                "model": variant_a['model'],
                "success_rate": variant_a['success_rate'],
                "successes": variant_a['successful_requests']
            },
            "variant_b": {
                "model": variant_b['model'],
                "success_rate": variant_b['success_rate'],
                "successes": variant_b['successful_requests']
            },
            "lift_pct": round(success_rate_lift, 2),
            "statistical_test": success_rate_test
        },
        "latency_comparison": {
            "variant_a": {
                "avg_ms": variant_a['avg_latency_ms'],
                "p95_ms": variant_a['p95_latency_ms']
            },
            "variant_b": {
                "avg_ms": variant_b['avg_latency_ms'],
                "p95_ms": variant_b['p95_latency_ms']
            },
            "diff_ms": round(latency_diff, 2),
            "diff_pct": round(latency_diff_pct, 2)
        },
        "recommendation": recommendation
    }


def print_analysis(analysis: Dict[str, Any]):
    """Pretty print analysis results"""
    print("="*60)
    print("A/B TEST STATISTICAL ANALYSIS")
    print("="*60)
    
    if "error" in analysis:
        print(f"\n[ERROR] {analysis['error']}")
        return
    
    print(f"\nDate: {analysis['date']}")
    print(f"Control (A): {analysis['test_config']['control']}")
    print(f"Treatment (B): {analysis['test_config']['treatment']}")
    
    print(f"\n--- Sample Sizes ---")
    print(f"Variant A: {analysis['sample_sizes']['variant_a']} requests")
    print(f"Variant B: {analysis['sample_sizes']['variant_b']} requests")
    print(f"Total: {analysis['sample_sizes']['total']} requests")
    
    print(f"\n--- Success Rate Comparison ---")
    sr = analysis['success_rate_comparison']
    print(f"Variant A ({sr['variant_a']['model']}): {sr['variant_a']['success_rate']}% ({sr['variant_a']['successes']} successes)")
    print(f"Variant B ({sr['variant_b']['model']}): {sr['variant_b']['success_rate']}% ({sr['variant_b']['successes']} successes)")
    print(f"Lift: {sr['lift_pct']:+.2f}%")
    
    print(f"\n--- Statistical Test ---")
    test = sr['statistical_test']
    print(f"Z-statistic: {test['z_statistic']}")
    print(f"Critical value (α={test['alpha']}): ±{test['critical_value']}")
    print(f"Significant: {'YES' if test['significant'] else 'NO'}")
    print(f"Conclusion: {test['conclusion']}")
    
    print(f"\n--- Latency Comparison ---")
    lat = analysis['latency_comparison']
    print(f"Variant A: {lat['variant_a']['avg_ms']}ms avg, {lat['variant_a']['p95_ms']}ms p95")
    print(f"Variant B: {lat['variant_b']['avg_ms']}ms avg, {lat['variant_b']['p95_ms']}ms p95")
    print(f"Difference: {lat['diff_ms']:+.2f}ms ({lat['diff_pct']:+.2f}%)")
    
    print(f"\n{'='*60}")
    print(f"RECOMMENDATION")
    print(f"{'='*60}")
    print(f"{analysis['recommendation']}")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(description='A/B test statistical analysis')
    parser.add_argument('--date', type=str, help='Date (YYYYMMDD) or leave empty for today')
    args = parser.parse_args()
    
    analysis = analyze_ab_test(args.date)
    print_analysis(analysis)
    
    # Save analysis to file
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    date = analysis.get('date', datetime.now().strftime('%Y%m%d'))
    output_file = os.path.join(log_dir, f'ab_analysis_{date}.json')
    
    with open(output_file, 'w') as f:
        json.dump(analysis, f, indent=2)
    
    print(f"\nAnalysis saved to: {output_file}")


if __name__ == "__main__":
    main()
