"""
Property analyzer.

Queries the database and generates:
- Summary statistics dict
- Interactive Plotly figures
- A self-contained HTML report written to data/processed/
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from loguru import logger
from sqlalchemy import create_engine, text

from config.settings import DATABASE_URL, PROCESSED_DIR


class PropertyAnalyzer:
    """Reads from the SQLite DB and produces analysis artefacts."""

    def __init__(self, db_url: str = DATABASE_URL) -> None:
        self.engine = create_engine(db_url)

    # ── Data loading ──────────────────────────────────────────────────────────

    def load_properties(self, run_date: Optional[date] = None) -> pd.DataFrame:
        """Load properties for a specific date, or all dates."""
        query = "SELECT * FROM properties WHERE 1=1"
        params: dict = {}
        if run_date:
            query += " AND date_scraped = :date"
            params["date"] = run_date.isoformat()
        df = pd.read_sql(text(query), self.engine, params=params)
        logger.info(f"Loaded {len(df)} records for analysis (date={run_date})")
        return df

    def load_run_history(self) -> pd.DataFrame:
        return pd.read_sql(
            "SELECT * FROM scrape_runs WHERE status='success' ORDER BY date_scraped",
            self.engine,
        )

    # ── Statistics ────────────────────────────────────────────────────────────

    def summary_stats(self, df: pd.DataFrame) -> dict:
        """Return a dict of key summary statistics."""
        return {
            "total_properties": len(df),
            "total_value_php": df["price_php"].sum(),
            "avg_price_php": df["price_php"].mean(),
            "median_price_php": df["price_php"].median(),
            "avg_lot_area_sqm": df["lot_area_sqm"].mean(),
            "median_price_per_sqm": df["price_per_sqm"].median(),
            "unique_provinces": df["province"].nunique(),
            "unique_regions": df["region"].nunique(),
            "category_counts": df["category"].value_counts().to_dict(),
        }

    # ── Deal scoring ──────────────────────────────────────────────────────────

    def compute_deal_score(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add a relative 'deal_score' column (0–100).

        Score = how far below the category median price-per-sqm this property is.
        Higher = better deal relative to similar properties.
        A score of 0 means at or above the median.
        """
        df = df.copy()
        medians = df.groupby("category")["price_per_sqm"].transform("median")
        df["deal_score"] = ((medians - df["price_per_sqm"]) / medians * 100).clip(0, 100)
        return df

    # ── Figures ───────────────────────────────────────────────────────────────

    def fig_category_pie(self, df: pd.DataFrame) -> go.Figure:
        counts = df["category"].value_counts()
        return px.pie(
            values=counts.values,
            names=counts.index,
            title="Property Breakdown by Category",
            hole=0.35,
        )

    def fig_price_histogram(self, df: pd.DataFrame) -> go.Figure:
 
        plot_df = df.copy()
        plot_df["price_php"] = pd.to_numeric(plot_df["price_php"], errors="coerce")
        plot_df = plot_df[plot_df["price_php"] > 0].copy()
 
        if plot_df.empty:
            logger.warning("fig_price_histogram: no valid price_php values to plot")
            return go.Figure(layout={"title": "Price Distribution — no data available"})
 
        plot_df["category"] = plot_df["category"].fillna("Unknown")
        plot_df["log10_price"] = np.log10(plot_df["price_php"])
 
        fig = px.histogram(
            plot_df,
            x="log10_price",
            color="category",
            nbins=50,
            title="Price Distribution by Category (log scale)",
            labels={"log10_price": "Price (PHP)", "count": "# Properties"},
            barmode="overlay",
            opacity=0.75,
        )
 
        # Relabel x-axis ticks to readable PHP amounts
        fig.update_xaxes(
            tickvals=[4.7, 5, 5.3, 5.7, 6, 6.7, 7, 7.7, 8],
            ticktext=["₱50K","₱100K", "₱200K", "₱500K", "₱1M", "₱5M", "₱10M", "₱50M", "₱100M"],
            title_text="Price (PHP)",
        )
        fig.update_layout(bargap=0.05)
        return fig


    def fig_top_provinces(self, df: pd.DataFrame, top_n: int = 15) -> go.Figure:
        top = (
            df.groupby("province")
            .agg(count=("property_acct_no", "count"), median_price=("price_php", "median"))
            .reset_index()
            .sort_values("count", ascending=False)
            .head(top_n)
        )
        fig = px.bar(
            top,
            x="count",
            y="province",
            orientation="h",
            color="median_price",
            color_continuous_scale="Blues",
            title=f"Top {top_n} Provinces by Number of Listings",
            labels={"count": "# Properties", "median_price": "Median Price (PHP)"},
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        return fig

    def fig_price_per_sqm_boxplot(self, df: pd.DataFrame) -> go.Figure:
        # Clip extreme outliers for readability
        p99 = df["price_per_sqm"].quantile(0.99)
        filtered = df[df["price_per_sqm"].between(0, p99, inclusive="left")]
        return px.box(
            filtered,
            x="category",
            y="price_per_sqm",
            color="category",
            title="Price per sqm by Category  (99th-pct cutoff)",
            labels={"price_per_sqm": "PHP / sqm"},
        )

    def fig_region_map_treemap(self, df: pd.DataFrame) -> go.Figure:
        agg = (
            df.groupby(["region", "category"])
            .agg(count=("property_acct_no", "count"))
            .reset_index()
        )
        return px.treemap(
            agg,
            path=["region", "category"],
            values="count",
            title="Property Distribution — Region → Category",
            color="count",
            color_continuous_scale="Teal",
        )

    def fig_run_trend(self) -> go.Figure:
        """Line chart of available properties per scrape date."""
        history = self.load_run_history()
        if history.empty:
            return go.Figure(layout={"title": "No run history yet"})
        return px.line(
            history,
            x="date_scraped",
            y="records_extracted",
            markers=True,
            title="Total Properties Available Over Time",
            labels={"records_extracted": "# Properties", "date_scraped": "Date"},
        )

    def fig_top_deals(self, df: pd.DataFrame, top_n: int = 25) -> go.Figure:
        """Bar chart of the top N properties by deal score."""
        df = self.compute_deal_score(df)
        top = df[df["deal_score"] > 0].nlargest(top_n, "deal_score")
        top["label"] = top["city"]  + ", " + top["province"].fillna("?") + "|" + top["property_acct_no"]
        chart_height = max(400, 300 + (len(top) * 20))
        return px.bar(
            top,
            x="deal_score",
            y="property_acct_no", # 1. Keep this UNIQUE so rows don't smash together
            orientation="h",
            color="category",
            title=f"Top {top_n} Potential Deals (vs Category Median Price/sqm)",
            labels={"deal_score": "Deal Score (0–100, higher = cheaper vs peers)", "property_acct_no": ""},
            height=chart_height,
        ).update_layout(yaxis={"categoryorder": "total ascending",
                                "dtick": 1,                  # <-- Forces Plotly to show EVERY label
                                "tickfont": {"size": 12},     # <-- Reduces font size so they fit comfortably
                                "automargin": True,            # <-- Prevents long labels from getting cut off
                                "tickmode": "array",
                                "tickvals": top["property_acct_no"],
                                "ticktext": top["label"],
                            
                            }, yaxis_title = "Address | Property Acct. No.")

    # ── Report export ─────────────────────────────────────────────────────────

    def export_report(
        self,
        run_date: Optional[date] = None,
        output_dir: Optional[Path] = None,
    ) -> Optional[Path]:
        """
        Generate a self-contained interactive HTML analysis report.

        Args:
            run_date:   Filter to a specific scrape date (None = all data).
            output_dir: Where to save the HTML file (default: data/processed/).

        Returns:
            Path to the generated HTML file, or None if no data.
        """
        output_dir = output_dir or PROCESSED_DIR
        df = self.load_properties(run_date)
        if df.empty:
            logger.warning("No data available — report not generated.")
            return None

        stats = self.summary_stats(df)
        date_label = run_date.isoformat() if run_date else "all"

        # Generate all figures
        figs = [
            self.fig_category_pie(df),
            self.fig_price_histogram(df),
            self.fig_top_provinces(df),
            self.fig_price_per_sqm_boxplot(df),
            self.fig_region_map_treemap(df),
            self.fig_top_deals(df),
            # self.fig_run_trend(),
        ]

        # Embed into a single HTML file (plotly CDN loaded once)
        def to_div(fig: go.Figure, first: bool = False) -> str:
            return fig.to_html(
                full_html=False,
                include_plotlyjs="cdn" if first else False,
            )

        stat_rows = "".join(
            f"<tr><td>{k.replace('_', ' ').title()}</td><td><b>{v:,.2f}</b></td></tr>"
            if isinstance(v, float)
            else f"<tr><td>{k.replace('_', ' ').title()}</td><td><b>{v:,}</b></td></tr>"
            for k, v in stats.items()
            if not isinstance(v, dict)
        )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Real Estate Listings Report</title>
  <style>
    body {{ font-family: 'Segoe UI', sans-serif; max-width: 1200px; margin: 0 auto; padding: 24px; background:#f7f8fa; }}
    h1 {{ color: #1a2e44; }}
    h2 {{ color: #2c5f8a; border-bottom: 2px solid #2c5f8a; padding-bottom: 4px; }}
    table {{ border-collapse: collapse; margin: 16px 0; }}
    td {{ padding: 6px 16px; border: 1px solid #ddd; }}
    tr:nth-child(even) {{ background: #f0f4f8; }}
    .chart-wrap {{ background: white; border-radius: 8px; padding: 12px; margin: 16px 0; box-shadow: 0 1px 4px rgba(0,0,0,.1); }}
  </style>
</head>
<body>
  <h1>🏠 PH Real Estate Listings Report</h1>
  <p><b>Source:</b> Bangko Sentral ng Pilipinas (BSP) &nbsp;|&nbsp;
     <b>Date:</b> {date.today()} &nbsp;|&nbsp;
     <b>Total listings:</b> {stats['total_properties']:,}</p>

  <h2>Summary Statistics</h2>
  <table>{stat_rows}</table>

  {"".join(f'<div class="chart-wrap">{to_div(fig, i==0)}</div>' for i, fig in enumerate(figs))}
</body>
</html>"""

        output_path = output_dir / f"analysis.html"
        output_path.write_text(html, encoding="utf-8")
        logger.success(f"Report saved: {output_path}")
        return output_path
