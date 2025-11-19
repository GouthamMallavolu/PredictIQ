# A/B Testing Framework

This document outlines the design, implementation, and analysis of the A/B testing framework for the FinSightAI API.

## 1. Experiment Design

The goal of this experiment is to compare the performance of two different prediction models to determine which one provides a better user experience.

-   **Hypothesis**: The LSTM model (challenger) will have a lower error rate than the Random Forest model (control) without a significant negative impact on latency.
-   **Primary KPI**: Success Rate (defined as `1 - Error Rate`). A higher success rate is better.
-   **Secondary KPI**: Request Latency. A lower latency is better.

### Variants

-   **Variant A (Control)**: Serves predictions from the **Random Forest** model (`random_forest`).
-   **Variant B (Challenger)**: Serves predictions from the **LSTM** model (`lstm`).

### User Splitting

Users are split into two groups (A and B) with a 50/50 distribution. The assignment is consistent for each user, meaning a specific user will always be in the same group. This is achieved by hashing the `user_id` and using a modulo operator.

## 2. Implementation

The A/B testing logic is implemented in the `api/ab_testing.py` module and integrated into the `/recommend` endpoint in `api/main.py`.

When a user makes a request to `/recommend` without specifying a model, the following happens:
1.  The user's `user_id` is used to assign them to either Variant A or Variant B.
2.  The corresponding model for that variant is selected.
3.  The prediction is made using the selected model.
4.  A log entry is created in `logs/ab_test_results.jsonl` recording the user, their assigned variant, the model used, the request latency, and whether the request was successful.

## 3. Statistical Analysis

To determine the winner of the experiment, we use a statistical approach to ensure our decision is data-driven and not based on random chance.

The `scripts/analyze_ab_test.py` script performs this analysis.

### How to Run the Analysis

1.  Ensure you have run some traffic against the `/recommend` endpoint to generate log data.
2.  From the project root, run the following command in your terminal:

    ```bash
    python scripts/analyze_ab_test.py
    ```

### Statistical Test Used

We use a **two-proportion z-test** to compare the success rates of Variant A and Variant B.

-   **Null Hypothesis (H₀)**: There is no difference in the success rates between the control (Random Forest) and the challenger (LSTM).
-   **Alternative Hypothesis (H₁)**: There is a difference in the success rates.

The script calculates a **p-value**. In simple terms, the p-value is the probability of observing the results we did if the null hypothesis were true.

### Interpreting the Results

We use a **significance level (alpha)** of 0.05. This is a standard threshold in statistics.

-   **If p-value < 0.05**: We **reject the null hypothesis**. This means the observed difference is statistically significant. We can confidently conclude that one model performs better than the other. The script will declare a winner based on which variant had the higher success rate.
-   **If p-value >= 0.05**: We **fail to reject the null hypothesis**. This means we do not have enough evidence to say that the difference between the models is real. The observed difference could just be due to random noise. The script will conclude that there is no clear winner.

## 4. Making a Decision

Based on the output of the analysis script:

-   **If a winner is declared**: We have a data-driven reason to make the winning model the new default for all users.
-   **If there is no clear winner**: We can choose to continue the experiment to collect more data or conclude that both models perform similarly and choose one based on other factors (e.g., lower latency, lower computational cost).
