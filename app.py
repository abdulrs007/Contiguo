import io
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
import streamlit as st
import folium
from streamlit_folium import st_folium
from branca.colormap import LinearColormap

st.set_page_config(page_title="Territory Viewer", layout="wide")
st.title("🗺️ Contiguous Territory Viewer Prototype")
st.caption("Upload a territories GeoJSON (dissolved by territory) to see KPIs and a colorized map.")

# --- Sidebar: file input ---
st.sidebar.header("Data")
default_path = Path("out/run_001/territories.geojson")
uploaded = st.sidebar.file_uploader("Upload territories.geojson", type=["geojson", "json"])

# --- Load data ---
gdf = None
if uploaded is not None:
    try:
        gdf = gpd.read_file(io.BytesIO(uploaded.getvalue()))
    except Exception as e:
        st.error(f"Could not read uploaded file: {e}")
elif default_path.exists():
    st.sidebar.info(f"Using default: {default_path}")
    gdf = gpd.read_file(default_path)
else:
    st.sidebar.warning("Upload a GeoJSON to begin (or place one at out/run_001/territories.geojson).")

if gdf is not None and not gdf.empty:
    # Ensure WGS84 for web display
    try:
        gdf = gdf.to_crs(4326)
    except Exception:
        pass

    # Expect columns: territory (int/str), weight (float). If missing 'weight', assume 1 per feature.
    if "territory" not in gdf.columns:
        st.warning("No 'territory' column found. Using a single territory = 0.")
        gdf["territory"] = 0

    if "weight" not in gdf.columns:
        gdf["weight"] = 1.0

    # Summaries
    per_terr = gdf.groupby("territory", as_index=False)["weight"].sum().rename(
        columns={"weight": "actual"}
    )
    n_terr = per_terr["territory"].nunique()
    grand_total = float(per_terr["actual"].sum())
    target = grand_total / max(1, n_terr)
    per_terr["target"] = target
    per_terr["deviation"] = per_terr["actual"] - per_terr["target"]
    per_terr["pct_dev"] = np.where(
        per_terr["target"] != 0, per_terr["deviation"] / per_terr["target"], 0.0
    )

    # KPI chips
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    worst = per_terr.loc[per_terr["pct_dev"].abs().idxmax()]
    kpi1.metric("Territories", n_terr)
    kpi2.metric("Total Weight", f"{grand_total:,.2f}")
    kpi3.metric("Target / Territory", f"{target:,.2f}")
    kpi4.metric(
        "Max |Deviation|",
        f"{abs(worst['deviation']):,.2f}",
        f"{worst['pct_dev']*100:+.1f}% (Terr {worst['territory']})",
    )

    # Territory table (sortable)
    st.subheader("Per-Territory Summary")
    st.dataframe(
        per_terr.sort_values("territory").reset_index(drop=True),
        use_container_width=True,
    )

    # --- Map coloring by deviation % ---
    # Build a dev% lookup for the style function
    dev_lookup = dict(zip(per_terr["territory"], per_terr["pct_dev"]))

    # Symmetric color scale around 0
    max_abs = max(0.01, float(np.abs(per_terr["pct_dev"]).max()))
    # clamp to at least +/-10% so small datasets have a visible ramp
    max_abs = max(max_abs, 0.10)
    cmap = LinearColormap(
        colors=["#2c7bb6", "#ffffbf", "#d7191c"],  # blue → yellow → red
        vmin=-max_abs,
        vmax=+max_abs,
    )
    cmap.caption = "Deviation from target (fraction of target)"

    def style_fn(feat):
        terr = feat["properties"].get("territory")
        dev = float(dev_lookup.get(terr, 0.0))
        # clip to scale range for stable colors
        dev = max(-max_abs, min(max_abs, dev))
        color = cmap(dev)
        return {
            "color": "#444444",
            "weight": 1,
            "fillColor": color,
            "fillOpacity": 0.7,
        }

    # Map center
    try:
        c = gdf.geometry.unary_union.centroid
        center = [float(c.y), float(c.x)]
    except Exception:
        center = [0.0, 0.0]

    # Toggle labels
    label_fields = [c for c in ["territory", "actual", "target", "deviation", "pct_dev"] if c in per_terr.columns]
    show_tooltips = st.checkbox("Show tooltips", value=True)

    # Join summary fields back to polygons (by territory) to show in tooltip
    gdf_disp = gdf.merge(per_terr, on="territory", how="left")

    # Build map
    st.subheader("Map")
    m = folium.Map(location=center, zoom_start=6)
    gj = folium.GeoJson(
        gdf_disp,
        name="Territories",
        style_function=style_fn,
        tooltip=folium.GeoJsonTooltip(
            fields=[f for f in ["territory", "actual", "target", "deviation", "pct_dev"] if f in gdf_disp.columns],
            aliases=["Territory", "Actual", "Target", "Deviation", "Pct Dev"],
        ),
        show=True,
    )
    gj.add_to(m)
    cmap.add_to(m)
    folium.LayerControl(collapsed=True).add_to(m)
    st_folium(m, width=None, height=640)

else:
    st.info("Upload a GeoJSON file in the sidebar to begin.")
