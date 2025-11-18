"""
Drift Detection for Data Quality
Detects distribution drift in user/symbol distributions and feature distributions
"""
import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import seaborn as sns

def detect_distribution_drift(
    reference_data: pd.Series,
    current_data: pd.Series,
    test_name: str = "KS"
) -> Dict:
    """
    Detect distribution drift using statistical tests
    
    Args:
        reference_data: Reference distribution (training data)
        current_data: Current distribution (production data)
        test_name: Statistical test to use ("KS" for Kolmogorov-Smirnov, "chi2" for chi-square)
    
    Returns:
        dict with drift detection results
    """
    if len(reference_data) == 0 or len(current_data) == 0:
        return {
            'drift_detected': False,
            'test_statistic': 0.0,
            'p_value': 1.0,
            'message': 'Insufficient data'
        }
    
    if test_name == "KS":
        # Kolmogorov-Smirnov test for continuous distributions
        statistic, p_value = stats.ks_2samp(reference_data, current_data)
        drift_detected = p_value < 0.05  # Significant drift if p < 0.05
    elif test_name == "chi2":
        # Chi-square test for categorical distributions
        # Create bins for continuous data
        bins = np.linspace(
            min(reference_data.min(), current_data.min()),
            max(reference_data.max(), current_data.max()),
            10
        )
        ref_counts, _ = np.histogram(reference_data, bins=bins)
        curr_counts, _ = np.histogram(current_data, bins=bins)
        
        # Normalize to frequencies
        ref_freq = ref_counts / ref_counts.sum() if ref_counts.sum() > 0 else ref_counts
        curr_freq = curr_counts / curr_counts.sum() if curr_counts.sum() > 0 else curr_counts
        
        # Chi-square test
        statistic, p_value = stats.chisquare(curr_freq * len(current_data), ref_freq * len(reference_data))
        drift_detected = p_value < 0.05
    else:
        raise ValueError(f"Unknown test: {test_name}")
    
    return {
        'drift_detected': drift_detected,
        'test_statistic': statistic,
        'p_value': p_value,
        'test_name': test_name,
        'reference_mean': reference_data.mean(),
        'current_mean': current_data.mean(),
        'reference_std': reference_data.std(),
        'current_std': current_data.std(),
        'message': f"Drift {'detected' if drift_detected else 'not detected'} (p={p_value:.4f})"
    }

def detect_symbol_distribution_drift(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    symbol_col: str = 'symbol'
) -> Dict:
    """
    Detect drift in symbol distribution
    
    Args:
        reference_df: Reference data
        current_df: Current data
        symbol_col: Column name for symbols
    
    Returns:
        dict with drift detection results
    """
    ref_symbols = reference_df[symbol_col].value_counts(normalize=True)
    curr_symbols = current_df[symbol_col].value_counts(normalize=True)
    
    # Get all symbols
    all_symbols = set(ref_symbols.index) | set(curr_symbols.index)
    
    # Create aligned frequency vectors
    ref_freq = [ref_symbols.get(s, 0) for s in all_symbols]
    curr_freq = [curr_symbols.get(s, 0) for s in all_symbols]
    
    # Chi-square test
    statistic, p_value = stats.chisquare(curr_freq, ref_freq)
    drift_detected = p_value < 0.05
    
    return {
        'drift_detected': drift_detected,
        'test_statistic': statistic,
        'p_value': p_value,
        'reference_distribution': ref_symbols.to_dict(),
        'current_distribution': curr_symbols.to_dict(),
        'message': f"Symbol distribution drift {'detected' if drift_detected else 'not detected'} (p={p_value:.4f})"
    }

def detect_feature_drift(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    feature_cols: List[str] = None
) -> Dict:
    """
    Detect drift in feature distributions
    
    Args:
        reference_df: Reference data
        current_df: Current data
        feature_cols: List of feature columns to check (None = all numeric columns)
    
    Returns:
        dict with drift detection results per feature
    """
    if feature_cols is None:
        feature_cols = reference_df.select_dtypes(include=[np.number]).columns.tolist()
    
    results = {}
    
    for col in feature_cols:
        if col not in reference_df.columns or col not in current_df.columns:
            continue
        
        ref_data = reference_df[col].dropna()
        curr_data = current_df[col].dropna()
        
        if len(ref_data) == 0 or len(curr_data) == 0:
            continue
        
        drift_result = detect_distribution_drift(ref_data, curr_data, test_name="KS")
        results[col] = drift_result
    
    # Overall drift detection
    any_drift = any(r['drift_detected'] for r in results.values())
    
    return {
        'overall_drift_detected': any_drift,
        'features_checked': len(results),
        'features_with_drift': sum(1 for r in results.values() if r['drift_detected']),
        'feature_results': results
    }

def plot_drift_comparison(
    reference_data: pd.Series,
    current_data: pd.Series,
    feature_name: str,
    save_path: str = None
):
    """
    Plot comparison of reference vs current distributions
    
    Args:
        reference_data: Reference distribution
        current_data: Current distribution
        feature_name: Name of the feature
        save_path: Path to save the plot (optional)
    """
    plt.figure(figsize=(10, 6))
    
    plt.hist(reference_data, bins=30, alpha=0.5, label='Reference', density=True)
    plt.hist(current_data, bins=30, alpha=0.5, label='Current', density=True)
    
    plt.xlabel(feature_name)
    plt.ylabel('Density')
    plt.title(f'Distribution Drift: {feature_name}')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Plot saved to {save_path}")
    
    plt.close()

def generate_drift_report(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    output_path: str = "drift_report.html"
) -> str:
    """
    Generate HTML drift detection report
    
    Args:
        reference_df: Reference data
        current_df: Current data
        output_path: Path to save HTML report
    
    Returns:
        HTML report as string
    """
    html = ["<html><head><title>Drift Detection Report</title></head><body>"]
    html.append("<h1>Data Drift Detection Report</h1>")
    
    # Symbol distribution drift
    if 'symbol' in reference_df.columns and 'symbol' in current_df.columns:
        symbol_drift = detect_symbol_distribution_drift(reference_df, current_df)
        html.append("<h2>Symbol Distribution Drift</h2>")
        html.append(f"<p><b>Drift Detected:</b> {symbol_drift['drift_detected']}</p>")
        html.append(f"<p><b>P-value:</b> {symbol_drift['p_value']:.4f}</p>")
    
    # Feature drift
    feature_drift = detect_feature_drift(reference_df, current_df)
    html.append("<h2>Feature Distribution Drift</h2>")
    html.append(f"<p><b>Overall Drift:</b> {feature_drift['overall_drift_detected']}</p>")
    html.append(f"<p><b>Features with Drift:</b> {feature_drift['features_with_drift']}/{feature_drift['features_checked']}</p>")
    
    html.append("<table border='1'><tr><th>Feature</th><th>Drift Detected</th><th>P-value</th></tr>")
    for feature, result in feature_drift['feature_results'].items():
        html.append(f"<tr><td>{feature}</td><td>{result['drift_detected']}</td><td>{result['p_value']:.4f}</td></tr>")
    html.append("</table>")
    
    html.append("</body></html>")
    
    report_html = "\n".join(html)
    
    if output_path:
        with open(output_path, 'w') as f:
            f.write(report_html)
        print(f"Report saved to {output_path}")
    
    return report_html

if __name__ == "__main__":
    print("Drift Detection Module")
    print("Import this module to use drift detection functions")

