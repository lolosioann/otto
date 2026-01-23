"""Visualize migration benchmark results for thesis.

Run with: PYTHONPATH=. uv run python test_scripts/visualize_benchmarks.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Configuration
BENCHMARK_DIR = Path("thesis/benchmarks")
OUTPUT_DIR = Path("thesis/plots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Style
plt.style.use("seaborn-v0_8-whitegrid")
sns.set_palette("husl")
FIGSIZE = (10, 6)
DPI = 300  # Higher DPI for PDF
FORMAT = "pdf"  # Vector format for thesis


def load_latest_benchmark() -> pd.DataFrame:
    """Load the most recent benchmark CSV."""
    csv_files = sorted(BENCHMARK_DIR.glob("migration_benchmarks_*.csv"))
    if not csv_files:
        raise FileNotFoundError("No benchmark files found")
    latest = csv_files[-1]
    print(f"Loading: {latest}")
    df = pd.read_csv(latest)
    # Filter successful runs only
    df = df[df["success"]].copy()
    # Convert transfer size to KB
    df["transfer_size_kb"] = df["transfer_size_bytes"] / 1024
    # Convert transfer size to MB
    df["transfer_size_mb"] = df["transfer_size_bytes"] / (1024 * 1024)
    return df


def plot_total_time_by_strategy(df: pd.DataFrame):
    """Box plot of total migration time by strategy."""
    fig, ax = plt.subplots(figsize=FIGSIZE)

    order = ["stop_start", "export_import", "swarm"]
    labels = ["Stop/Start", "Export/Import", "Swarm"]

    sns.boxplot(
        data=df,
        x="strategy",
        y="total_time_s",
        order=order,
        ax=ax,
        palette="Set2",
    )

    ax.set_xticklabels(labels)
    ax.set_xlabel("Migration Strategy")
    ax.set_ylabel("Total Migration Time (s)")
    ax.set_title("Migration Time by Strategy")

    # Add median annotations
    medians = df.groupby("strategy")["total_time_s"].median()
    for i, strat in enumerate(order):
        if strat in medians:
            ax.annotate(
                f"{medians[strat]:.2f}s",
                xy=(i, medians[strat]),
                xytext=(10, 0),
                textcoords="offset points",
                fontsize=9,
                color="black",
            )

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f"01_total_time_by_strategy.{FORMAT}", dpi=DPI)
    plt.close()
    print(f"Saved: 01_total_time_by_strategy.{FORMAT}")


def plot_time_by_image(df: pd.DataFrame):
    """Grouped bar chart of migration time by image and strategy."""
    fig, ax = plt.subplots(figsize=(12, 6))

    # Aggregate by image and strategy
    agg = df.groupby(["image_label", "strategy"])["total_time_s"].agg(["mean", "std"]).reset_index()

    image_order = ["busybox", "alpine", "nginx", "python"]
    strategy_order = ["stop_start", "export_import", "swarm"]
    strategy_labels = {
        "stop_start": "Stop/Start",
        "export_import": "Export/Import",
        "swarm": "Swarm",
    }

    x = np.arange(len(image_order))
    width = 0.25

    for i, strat in enumerate(strategy_order):
        strat_data = agg[agg["strategy"] == strat]
        means = []
        stds = []
        for img in image_order:
            row = strat_data[strat_data["image_label"] == img]
            if len(row) > 0:
                means.append(row["mean"].values[0])
                stds.append(row["std"].values[0])
            else:
                means.append(0)
                stds.append(0)

        ax.bar(
            x + i * width,
            means,
            width,
            label=strategy_labels[strat],
            yerr=stds,
            capsize=3,
        )

    ax.set_xlabel("Container Image")
    ax.set_ylabel("Migration Time (s)")
    ax.set_title("Migration Time by Image and Strategy")
    ax.set_xticks(x + width)
    ax.set_xticklabels(image_order)
    ax.legend()

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f"02_time_by_image.{FORMAT}", dpi=DPI)
    plt.close()
    print(f"Saved: 02_time_by_image.{FORMAT}")


def plot_time_by_filesystem_state(df: pd.DataFrame):
    """Migration time by filesystem state (SSH strategies only)."""
    fig, ax = plt.subplots(figsize=FIGSIZE)

    # Filter to SSH strategies only (swarm doesn't have fs state variation)
    ssh_df = df[df["strategy"].isin(["stop_start", "export_import"])]

    fs_order = ["empty", "small", "medium"]
    fs_labels = ["Empty", "100KB", "1MB"]

    sns.boxplot(
        data=ssh_df,
        x="filesystem_state",
        y="total_time_s",
        hue="strategy",
        order=fs_order,
        ax=ax,
        palette="Set2",
    )

    ax.set_xticklabels(fs_labels)
    ax.set_xlabel("Filesystem State")
    ax.set_ylabel("Total Migration Time (s)")
    ax.set_title("Migration Time by Filesystem State (SSH Strategies)")
    ax.legend(title="Strategy", labels=["Stop/Start", "Export/Import"])

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f"03_time_by_filesystem_state.{FORMAT}", dpi=DPI)
    plt.close()
    print(f"Saved: 03_time_by_filesystem_state.{FORMAT}")


def plot_transfer_size(df: pd.DataFrame):
    """Transfer size by image (export/import only)."""
    fig, ax = plt.subplots(figsize=FIGSIZE)

    # Filter to export_import only
    export_df = df[df["strategy"] == "export_import"]

    image_order = ["busybox", "alpine", "nginx", "python"]

    sns.barplot(
        data=export_df,
        x="image_label",
        y="transfer_size_mb",
        order=image_order,
        ax=ax,
        palette="Blues_d",
        errorbar="sd",
    )

    ax.set_xlabel("Container Image")
    ax.set_ylabel("Transfer Size (MB)")
    ax.set_title("Container Export Size by Image")

    # Add value labels
    for i, img in enumerate(image_order):
        img_data = export_df[export_df["image_label"] == img]
        if len(img_data) > 0:
            mean_size = img_data["transfer_size_mb"].mean()
            ax.annotate(
                f"{mean_size:.1f} MB",
                xy=(i, mean_size),
                xytext=(0, 5),
                textcoords="offset points",
                ha="center",
                fontsize=9,
            )

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f"04_transfer_size.{FORMAT}", dpi=DPI)
    plt.close()
    print(f"Saved: 04_transfer_size.{FORMAT}")


def plot_time_breakdown(df: pd.DataFrame):
    """Stacked bar chart showing time breakdown (export, import, start)."""
    fig, ax = plt.subplots(figsize=(12, 6))

    # Filter to export_import (has all phases)
    export_df = df[df["strategy"] == "export_import"]

    # Aggregate by image
    image_order = ["busybox", "alpine", "nginx", "python"]

    export_times = []
    import_times = []
    start_times = []

    for img in image_order:
        img_data = export_df[export_df["image_label"] == img]
        export_times.append(img_data["export_time_s"].mean())
        import_times.append(img_data["import_time_s"].mean())
        start_times.append(img_data["start_time_s"].mean())

    x = np.arange(len(image_order))
    width = 0.6

    ax.bar(x, export_times, width, label="Export", color="#2ecc71")
    ax.bar(x, import_times, width, bottom=export_times, label="Import", color="#3498db")
    ax.bar(
        x,
        start_times,
        width,
        bottom=np.array(export_times) + np.array(import_times),
        label="Start",
        color="#e74c3c",
    )

    ax.set_xlabel("Container Image")
    ax.set_ylabel("Time (s)")
    ax.set_title("Migration Time Breakdown (Export/Import Strategy)")
    ax.set_xticks(x)
    ax.set_xticklabels(image_order)
    ax.legend()

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f"05_time_breakdown.{FORMAT}", dpi=DPI)
    plt.close()
    print(f"Saved: 05_time_breakdown.{FORMAT}")


def plot_strategy_comparison_violin(df: pd.DataFrame):
    """Violin plot comparing strategies."""
    fig, ax = plt.subplots(figsize=FIGSIZE)

    order = ["stop_start", "export_import", "swarm"]
    labels = ["Stop/Start", "Export/Import", "Swarm"]

    sns.violinplot(
        data=df,
        x="strategy",
        y="total_time_s",
        order=order,
        ax=ax,
        palette="Set2",
        inner="box",
    )

    ax.set_xticklabels(labels)
    ax.set_xlabel("Migration Strategy")
    ax.set_ylabel("Total Migration Time (s)")
    ax.set_title("Migration Time Distribution by Strategy")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f"06_strategy_violin.{FORMAT}", dpi=DPI)
    plt.close()
    print(f"Saved: 06_strategy_violin.{FORMAT}")


def plot_export_import_detail(df: pd.DataFrame):
    """Detailed comparison for export/import strategy across images and fs states."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    export_df = df[df["strategy"] == "export_import"]

    # Left: by image
    sns.boxplot(
        data=export_df,
        x="image_label",
        y="total_time_s",
        order=["busybox", "alpine", "nginx", "python"],
        ax=axes[0],
        palette="Greens",
    )
    axes[0].set_xlabel("Container Image")
    axes[0].set_ylabel("Total Migration Time (s)")
    axes[0].set_title("Export/Import: Time by Image")

    # Right: by filesystem state
    sns.boxplot(
        data=export_df,
        x="filesystem_state",
        y="total_time_s",
        order=["empty", "small", "medium"],
        ax=axes[1],
        palette="Blues",
    )
    axes[1].set_xticklabels(["Empty", "100KB", "1MB"])
    axes[1].set_xlabel("Filesystem State")
    axes[1].set_ylabel("Total Migration Time (s)")
    axes[1].set_title("Export/Import: Time by Filesystem State")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f"07_export_import_detail.{FORMAT}", dpi=DPI)
    plt.close()
    print(f"Saved: 07_export_import_detail.{FORMAT}")


def generate_summary_table(df: pd.DataFrame):
    """Generate summary statistics table."""
    print("\n" + "=" * 60)
    print("SUMMARY STATISTICS")
    print("=" * 60)

    # By strategy
    print("\nBy Strategy:")
    strategy_stats = (
        df.groupby("strategy")["total_time_s"]
        .agg(["count", "mean", "std", "min", "max", "median"])
        .round(3)
    )
    strategy_stats.columns = ["N", "Mean(s)", "Std(s)", "Min(s)", "Max(s)", "Median(s)"]
    print(strategy_stats.to_string())

    # By image (export_import only)
    print("\nBy Image (Export/Import only):")
    export_df = df[df["strategy"] == "export_import"]
    image_stats = (
        export_df.groupby("image_label")
        .agg(
            {
                "total_time_s": ["mean", "std"],
                "transfer_size_mb": "mean",
            }
        )
        .round(3)
    )
    image_stats.columns = ["Time Mean(s)", "Time Std(s)", "Size(MB)"]
    print(image_stats.to_string())

    # Save to CSV
    strategy_stats.to_csv(OUTPUT_DIR / "summary_by_strategy.csv")
    image_stats.to_csv(OUTPUT_DIR / "summary_by_image.csv")
    print(f"\nSummary tables saved to {OUTPUT_DIR}")

    return strategy_stats, image_stats


def main():
    """Generate all plots."""
    print("=" * 60)
    print("Migration Benchmark Visualization")
    print("=" * 60)

    df = load_latest_benchmark()
    print(f"Loaded {len(df)} successful benchmark runs")
    print(f"Strategies: {df['strategy'].unique()}")
    print(f"Images: {df['image_label'].unique()}")
    print(f"Filesystem states: {df['filesystem_state'].unique()}")

    print(f"\nGenerating plots in {OUTPUT_DIR}...")

    plot_total_time_by_strategy(df)
    plot_time_by_image(df)
    plot_time_by_filesystem_state(df)
    plot_transfer_size(df)
    plot_time_breakdown(df)
    plot_strategy_comparison_violin(df)
    plot_export_import_detail(df)

    generate_summary_table(df)

    print("\n" + "=" * 60)
    print("All plots generated successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
