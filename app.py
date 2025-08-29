import os
from typing import Dict, List
from flask import Flask, render_template, jsonify, request, send_file, abort
import pandas as pd

# ----------- Paths -----------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(APP_DIR, "templates")
STATIC_DIR = os.path.join(APP_DIR, "static")

EXCEL_NAME = "India-Advocate -1750.xlsx"         # <- keep the file in project root
EXCEL_PATH = os.path.join(APP_DIR, EXCEL_NAME)
CSV_CACHE = os.path.join(APP_DIR, "advocates_cache.csv")

# ----------- Fuzzy column matching -----------
ALIASES: Dict[str, List[str]] = {
    "Business Name": ["advocate name", "name", "full name", "lawyer", "firm", "office", "company", "practice"],
    "Owner Name":    ["owner", "contact person", "principal", "proprietor", "head", "lead"],
    "City":          ["city", "district", "town"],
    "State":         ["state", "province", "region"],
    "Mobile Number": ["mobile", "phone", "contact", "mobile number", "phone number", "cell", "whatsapp"],
}

# ----------- Data load & normalize -----------
def read_dataset() -> pd.DataFrame:
    """Load Excel if present, else cached CSV; cache when loading Excel."""
    if os.path.exists(EXCEL_PATH):
        df = pd.read_excel(EXCEL_PATH, sheet_name=0)
        df.to_csv(CSV_CACHE, index=False)
    elif os.path.exists(CSV_CACHE):
        df = pd.read_csv(CSV_CACHE)
    else:
        abort(500, f"Missing dataset: {EXCEL_NAME} (or {os.path.basename(CSV_CACHE)})")
    return df

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map arbitrary headers to canonical ones and lightly clean."""
    lowered = {c.lower().strip(): c for c in df.columns}

    def pick(expected_key: str) -> str:
        for alias in ALIASES[expected_key]:
            for low, orig in lowered.items():
                if alias in low:
                    return orig
        return ""

    col_business = pick("Business Name")
    col_owner    = pick("Owner Name")
    col_city     = pick("City")
    col_state    = pick("State")

    # Find one or more phone-like columns
    phone_candidates = []
    for alias in ALIASES["Mobile Number"]:
        for low, orig in lowered.items():
            if alias in low and orig not in phone_candidates:
                phone_candidates.append(orig)
    col_phone = phone_candidates[0] if phone_candidates else ""

    out = pd.DataFrame()

    # Business/Owner fallback logic
    if col_business:
        out["Business Name"] = df[col_business]
    elif col_owner:
        out["Business Name"] = df[col_owner]
    else:
        out["Business Name"] = df.iloc[:, 0].astype(str)

    out["Owner Name"] = df[col_owner] if col_owner else out["Business Name"]
    out["City"]  = df[col_city] if col_city else ""
    out["State"] = df[col_state] if col_state else ""

    if col_phone:
        phones = df[col_phone].astype(str)
        if len(phone_candidates) > 1:
            for extra in phone_candidates[1:]:
                s = df[extra].astype(str)
                # fill empty with next candidate
                phones = phones.mask(phones.str.strip().isin(["", "nan", "None"]), s)
        out["Mobile Number"] = phones
    else:
        out["Mobile Number"] = ""

    # Clean
    for c in ["Business Name", "Owner Name", "City", "State", "Mobile Number"]:
        out[c] = (
            out[c]
            .astype(str)
            .str.strip()
            .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "NaN": pd.NA}, regex=False)
        )

    return out

# ----------- App -----------
app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)

_raw_df = read_dataset()
df = normalize_columns(_raw_df)

# Pre-compute a simple duplicate flag (not persisted)
dup_mask = df.duplicated(subset=["Business Name", "City", "State"], keep=False)

# ----------- Routes (pages) -----------
@app.route("/")
def index():
    return render_template("dashboard.html")

@app.route("/download/csv")
def download_csv():
    out_path = os.path.join(APP_DIR, "advocates_normalized.csv")
    df.to_csv(out_path, index=False)
    return send_file(out_path, as_attachment=True, download_name="advocates.csv")

# ----------- APIs (charts & table) -----------
@app.route("/api/summary")
def api_summary():
    total = int(len(df))
    unique_states = int(df["State"].nunique(dropna=True))
    unique_cities = int(df["City"].nunique(dropna=True))
    unique_owners = int(df["Owner Name"].nunique(dropna=True))
    phones_present = int(df["Mobile Number"].notna().sum())
    phones_missing = int(df["Mobile Number"].isna().sum())
    dup_count = int(dup_mask.sum())

    return jsonify({
        "total_records": total,
        "unique_states": unique_states,
        "unique_cities": unique_cities,
        "unique_owners": unique_owners,
        "phones_present": phones_present,
        "phones_missing": phones_missing,
        "potential_duplicates": dup_count
    })

@app.route("/api/top-states")
def api_top_states():
    limit = int(request.args.get("limit", 12))
    g = (df.groupby("State", dropna=False).size()
           .reset_index(name="count")
           .sort_values("count", ascending=False)
           .head(limit))
    g["State"] = g["State"].fillna("Unknown")
    return jsonify(g.to_dict(orient="records"))

@app.route("/api/top-cities")
def api_top_cities():
    limit = int(request.args.get("limit", 20))
    g = (df.groupby(["State", "City"], dropna=False).size()
           .reset_index(name="count")
           .sort_values("count", ascending=False)
           .head(limit))
    g["State"] = g["State"].fillna("Unknown")
    g["City"] = g["City"].fillna("Unknown")
    return jsonify(g.to_dict(orient="records"))

@app.route("/api/phones-by-state")
def api_phones_by_state():
    limit = int(request.args.get("limit", 12))
    d = df.assign(has_phone=df["Mobile Number"].notna())
    g = (d.groupby("State", dropna=False)["has_phone"]
           .agg(with_phone="sum", total="count")
           .reset_index())
    g["rate"] = (g["with_phone"] / g["total"]).fillna(0.0)
    g["State"] = g["State"].fillna("Unknown")
    g = g.sort_values("total", ascending=False).head(limit)
    return jsonify(g.to_dict(orient="records"))

@app.route("/api/treemap-states")
def api_treemap_states():
    """Return counts per state for a treemap."""
    g = (df.groupby("State", dropna=False).size()
           .reset_index(name="count")
           .sort_values("count", ascending=False))
    g["State"] = g["State"].fillna("Unknown")
    return jsonify(g.to_dict(orient="records"))

@app.route("/api/state-city-heatmap")
def api_state_city_heatmap():
    """Pivot of counts City x State for heatmap (top N states, top M cities)."""
    top_states = int(request.args.get("states", 10))
    top_cities = int(request.args.get("cities", 15))

    gs = (df.groupby("State", dropna=False).size().sort_values(ascending=False).head(top_states))
    top_state_vals = list(gs.index)

    gc = (df[df["State"].isin(top_state_vals)]
          .groupby("City", dropna=False)
          .size().sort_values(ascending=False).head(top_cities))
    top_city_vals = list(gc.index)

    d = df[df["State"].isin(top_state_vals) & df["City"].isin(top_city_vals)]
    p = (d
         .groupby(["City", "State"])
         .size()
         .reset_index(name="count"))

    # Return a dense matrix payload for easier plotting
    states = [s if pd.notna(s) else "Unknown" for s in top_state_vals]
    cities = [c if pd.notna(c) else "Unknown" for c in top_city_vals]
    grid = [[0]*len(states) for _ in range(len(cities))]
    m = {( (row["City"] if pd.notna(row["City"]) else "Unknown"),
           (row["State"] if pd.notna(row["State"]) else "Unknown") ): int(row["count"])
         for _, row in p.iterrows()}
    for i, c in enumerate(cities):
        for j, s in enumerate(states):
            grid[i][j] = m.get((c, s), 0)

    return jsonify({"states": states, "cities": cities, "z": grid})

@app.route("/api/table")
def api_table():
    """
    Server-side table endpoint.
    Query:
      - start:  offset
      - length: page size
      - search[value]: global search
    """
    start = int(request.args.get("start", 0))
    length = int(request.args.get("length", 25))
    search = request.args.get("search[value]", "").strip().lower()

    filtered = df
    if search:
        mask = (
            df["Business Name"].astype(str).str.lower().str.contains(search, na=False) |
            df["Owner Name"].astype(str).str.lower().str.contains(search, na=False) |
            df["City"].astype(str).str.lower().str.contains(search, na=False) |
            df["State"].astype(str).str.lower().str.contains(search, na=False) |
            df["Mobile Number"].astype(str).str.lower().str.contains(search, na=False)
        )
        filtered = df[mask]

    total_records = len(df)
    total_filtered = len(filtered)
    page = filtered.iloc[start:start+length].fillna("")
    return jsonify({
        "recordsTotal": total_records,
        "recordsFiltered": total_filtered,
        "data": page.to_dict(orient="records")
    })

# ----------- Main -----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
