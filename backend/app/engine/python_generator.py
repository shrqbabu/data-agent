"""Python Analytics & Data Engineering Script Generator.

Generates reproducible, production-grade Python scripts used to clean,
deduplicate, compute metrics, and visualize datasets with Pandas, NumPy,
Matplotlib, and Seaborn.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.engine.context import SchemaModel
from app.engine.metric_registry import MetricRegistry


class PythonScriptItem(BaseModel):
    title: str
    purpose: str
    python_code: str
    libraries: List[str]


def generate_python_scripts(registry: MetricRegistry, model: SchemaModel, prompt: str = "") -> List[Dict[str, Any]]:
    """Generate production-ready Python analysis scripts tailored to the dataset."""
    scripts: List[PythonScriptItem] = []

    table_name = "data"
    amount_col = (model.amount_columns and model.amount_columns[0]) or (model.numeric_columns and model.numeric_columns[0]) or "amount"
    date_col = (model.date_columns and model.date_columns[0]) or "date"
    cat_col = (model.categorical_columns and model.categorical_columns[0]) or "category"

    # 1. Ingestion, Profiling & Deduplication Script
    dedup_code = f"""import pandas as pd
import numpy as np

def clean_and_profile_dataset(file_path: str) -> pd.DataFrame:
    \"\"\"Ingests dataset, calculates duplicates vs uniques, and handles nulls.\"\"\"
    # 1. Read file
    if file_path.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(file_path)
    else:
        df = pd.read_csv(file_path, on_bad_lines='skip')
    
    # 2. Header normalization
    df.columns = [str(c).strip() for c in df.columns]
    total_records = len(df)
    
    # 3. Deduplication audit
    duplicate_rows = int(df.duplicated().sum())
    unique_records = total_records - duplicate_rows
    dup_pct = (duplicate_rows / total_records) * 100 if total_records > 0 else 0.0
    
    print(f"Total Rows Ingested: {{total_records:,}}")
    print(f"Unique Records: {{unique_records:,}}")
    print(f"Duplicate Rows Identified: {{duplicate_rows:,}} ({{dup_pct:.2f}}%)")
    
    # Remove exact duplicate rows
    df_cleaned = df.drop_duplicates().copy()
    
    # 4. Handle date & numeric types
    if '{date_col}' in df_cleaned.columns:
        df_cleaned['{date_col}'] = pd.to_datetime(df_cleaned['{date_col}'], errors='coerce')
    
    if '{amount_col}' in df_cleaned.columns:
        df_cleaned['{amount_col}'] = pd.to_numeric(df_cleaned['{amount_col}'], errors='coerce').fillna(0.0)
    
    return df_cleaned

if __name__ == "__main__":
    df = clean_and_profile_dataset("dataset.csv")
    print("Dataset cleaned successfully. Shape:", df.shape)
"""
    scripts.append(PythonScriptItem(
        title="1. Data Ingestion, Profiling & Deduplication Pipeline",
        purpose="Loads CSV/Excel, calculates exact unique vs duplicate records, drops duplicates, and casts data types.",
        python_code=dedup_code,
        libraries=["pandas", "numpy"]
    ))

    # 2. Business KPI & Metric Aggregation Script
    kpi_code = f"""import pandas as pd
import numpy as np

def compute_executive_metrics(df: pd.DataFrame) -> dict:
    \"\"\"Calculates verified financial & operational metrics.\"\"\"
    metrics = {{}}
    
    # Total & Average Aggregations
    if '{amount_col}' in df.columns:
        total_vol = df['{amount_col}'].sum()
        avg_val = df['{amount_col}'].mean()
        median_val = df['{amount_col}'].median()
        metrics['Total_{amount_col}'] = float(total_vol)
        metrics['Average_{amount_col}'] = float(avg_val)
        metrics['Median_{amount_col}'] = float(median_val)
    
    # Categorical Breakdown & Pareto 80/20
    if '{cat_col}' in df.columns and '{amount_col}' in df.columns:
        cat_grouped = df.groupby('{cat_col}')['{amount_col}'].sum().sort_values(ascending=False)
        cat_cum_pct = (cat_grouped.cumsum() / cat_grouped.sum()) * 100
        top_20_pct_count = int(np.ceil(0.20 * len(cat_grouped)))
        pareto_volume = cat_grouped.head(top_20_pct_count).sum()
        pareto_share = (pareto_volume / cat_grouped.sum()) * 100 if cat_grouped.sum() > 0 else 0.0
        
        metrics['Top_Category'] = str(cat_grouped.index[0]) if not cat_grouped.empty else 'N/A'
        metrics['Pareto_Top_20_Share_Pct'] = float(pareto_share)
    
    # Temporal / Monthly Trend
    if '{date_col}' in df.columns and '{amount_col}' in df.columns:
        monthly = df.set_index('{date_col}').resample('ME')['{amount_col}'].sum()
        mom_growth = monthly.pct_change() * 100
        metrics['Latest_Month_Volume'] = float(monthly.iloc[-1]) if not monthly.empty else 0.0
        metrics['Latest_MoM_Growth_Pct'] = float(mom_growth.iloc[-1]) if len(mom_growth) > 1 else 0.0

    return metrics
"""
    scripts.append(PythonScriptItem(
        title="2. Executive KPI Aggregation & Pareto Analysis",
        purpose="Computes deterministic business aggregations, Month-over-Month (MoM) growth, and 80/20 Pareto distribution.",
        python_code=kpi_code,
        libraries=["pandas", "numpy"]
    ))

    # 3. High-Resolution Dashboard Visualization Script
    viz_code = f"""import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

def render_executive_charts(df: pd.DataFrame, output_path: str = "dashboard_charts.png"):
    \"\"\"Generates publication-quality charts matching the executive dashboard visual.\"\"\"
    plt.style.use('dark_background')
    fig, axes = plt.subplots(1, 2, figsize=(16, 6), facecolor='#0A0E17')
    for ax in axes:
        ax.set_facecolor('#131A29')
    
    # Chart 1: Monthly Trend
    if '{date_col}' in df.columns and '{amount_col}' in df.columns:
        monthly = df.set_index('{date_col}').resample('ME')['{amount_col}'].sum().reset_index()
        axes[0].plot(monthly['{date_col}'].dt.strftime('%b %Y'), monthly['{amount_col}'], 
                     color='#00F2FE', linewidth=2.5, marker='o', markersize=6)
        axes[0].set_title("Temporal Revenue / Volume Trend", color='white', fontsize=12, fontweight='bold')
        axes[0].tick_params(axis='x', rotation=45, colors='#94A3B8')
        axes[0].tick_params(axis='y', colors='#94A3B8')
        axes[0].grid(True, linestyle='--', alpha=0.2, color='#64748B')

    # Chart 2: Category Distribution
    if '{cat_col}' in df.columns and '{amount_col}' in df.columns:
        top_cats = df.groupby('{cat_col}')['{amount_col}'].sum().sort_values(ascending=False).head(6)
        sns.barplot(x=top_cats.values, y=top_cats.index, ax=axes[1], palette='viridis')
        axes[1].set_title("Top 6 Category Contribution", color='white', fontsize=12, fontweight='bold')
        axes[1].tick_params(colors='#94A3B8')
        axes[1].grid(True, linestyle='--', alpha=0.2, color='#64748B')
        
    plt.tight_layout()
    plt.savefig(output_path, dpi=220, bbox_inches='tight', facecolor=fig.get_facecolor())
    print(f"Dashboard visuals saved to {{output_path}}")
"""
    scripts.append(PythonScriptItem(
        title="3. High-Resolution Dashboard Visualization Script",
        purpose="Matplotlib & Seaborn script to render dark-mode executive charts matching the report.",
        python_code=viz_code,
        libraries=["matplotlib", "seaborn", "pandas"]
    ))

    return [s.dict() for s in scripts]
