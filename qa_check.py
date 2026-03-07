"""QA/QC checks for the ERCOT screener dashboard."""
import pandas as pd
from src.config import SETTINGS
from src.presentation.texas_map import build_location_map_frame

metrics = pd.read_parquet(SETTINGS.metrics_path(SETTINGS.target_year))
battery = pd.read_parquet(SETTINGS.battery_value_path(SETTINGS.target_year))
mf = build_location_map_frame(metrics, battery)

print("=== LABEL OVERLAP CHECK ===")
print("Looking for locations with similar lat/lon that might overlap...")
print()

for i in range(len(mf)):
    for j in range(i + 1, len(mf)):
        lat_diff = abs(mf.iloc[i]["lat"] - mf.iloc[j]["lat"])
        lon_diff = abs(mf.iloc[i]["lon"] - mf.iloc[j]["lon"])
        if lat_diff < 1.0 and lon_diff < 1.0:
            loc_a = mf.iloc[i]["location"]
            loc_b = mf.iloc[j]["location"]
            tp_a = mf.iloc[i]["text_position"]
            tp_b = mf.iloc[j]["text_position"]
            print(f"  CLOSE: {loc_a} ({mf.iloc[i]['lat']:.2f}, {mf.iloc[i]['lon']:.2f}) text={tp_a}")
            print(f"     vs  {loc_b} ({mf.iloc[j]['lat']:.2f}, {mf.iloc[j]['lon']:.2f}) text={tp_b}")
            if tp_a == tp_b:
                print("     ** SAME text_position — labels WILL overlap **")
            print()

print()
print("=== KPI ACCURACY CHECK ===")
top = metrics.iloc[0]
print(f"Top location by score: {top['location']} (score: {top['battery_opportunity_score']:.1f})")
print(f"Its daily spread: ${top['avg_daily_spread']:.1f}/MWh")
print(f"Its neg hours: {top['pct_negative']:.1f}%")
print()

actual_top_spread = metrics.loc[metrics["avg_daily_spread"].idxmax()]
print(f"Actual highest spread: {actual_top_spread['location']} ${actual_top_spread['avg_daily_spread']:.1f}/MWh")
if actual_top_spread["location"] != top["location"]:
    print("  NOTE: #1 by score != #1 by spread. KPIs show #1-ranked location values, not global max.")

actual_top_neg = metrics.loc[metrics["pct_negative"].idxmax()]
print(f"Actual highest neg%: {actual_top_neg['location']} {actual_top_neg['pct_negative']:.1f}%")

best_batt = battery.sort_values("annual_battery_gross_margin_usd", ascending=False).iloc[0]
print(f"Top battery margin: {best_batt['location']} ${best_batt['annual_battery_gross_margin_usd']:,.0f}/yr")

print()
print("=== SCORE COMPONENT WEIGHTS ===")
w = SETTINGS.metric_weights
total_w = w.pct_negative + w.pct_below_20 + w.avg_daily_spread + w.pct_above_100
print(f"Weights sum to {total_w:.2f} (should be 1.00)")

print()
print("=== ALL QA CHECKS COMPLETE ===")
