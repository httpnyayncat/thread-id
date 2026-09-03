import io
import json
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="THREAD-ID", page_icon="🧵", layout="wide")

DATA_PATH = Path(__file__).parent / "demo_products.csv"

# Research-backed material heuristics for the prototype.
# These are NOT official LCA factors. They are transparent prototype weights.
MATERIAL_BASE = {
    "organic cotton": 88,
    "hemp": 90,
    "linen": 86,
    "recycled cotton": 84,
    "recycled polyester": 78,
    "wool": 72,
    "cotton": 65,
    "viscose": 62,
    "silk": 60,
    "nylon": 48,
    "polyester": 45,
    "acrylic": 35,
}

def normalize_material(s):
    s = str(s).lower()
    # Blend scoring: average recognized material scores, weighted by rough equal shares.
    parts = re.split(r"\s*\+\s*|\s*/\s*|,| and ", s)
    scores = []
    for part in parts:
        p = part.strip()
        if not p:
            continue
        matches = [(k, v) for k, v in MATERIAL_BASE.items() if k in p]
        if matches:
            scores.append(max(matches, key=lambda x: len(x[0]))[1])
    return sum(scores) / len(scores) if scores else 50

def circularity_score(row):
    material = normalize_material(row["material"])
    recycled = float(row["recycled_pct"])
    repair = 100 if bool(row["repairable"]) else 35
    recycle = 100 if bool(row["recyclable"]) else 30

    # Prototype score, intentionally separate from an LCA.
    score = (
        0.40 * material
        + 0.20 * min(recycled, 100)
        + 0.20 * repair
        + 0.20 * recycle
    )
    return round(max(0, min(100, score)))

def action(score):
    if score >= 80:
        return "Keep in use → repair → resell → recycle"
    if score >= 65:
        return "Keep in use → repair/resell → recycle if possible"
    if score >= 50:
        return "Prioritize reuse and repair; verify local recycling options"
    return "Prioritize longer use/reuse; seek specialized textile recycling"

def prepare(df):
    df = df.copy()
    required = ["product_id","product_name","category","material","recycled_pct",
                "repairable","recyclable","country","brand"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("Missing columns: " + ", ".join(missing))
    df["recycled_pct"] = pd.to_numeric(df["recycled_pct"], errors="coerce").fillna(0).clip(0,100)
    df["repairable"] = df["repairable"].astype(str).str.lower().isin(["true","1","yes","y"])
    df["recyclable"] = df["recyclable"].astype(str).str.lower().isin(["true","1","yes","y"])
    df["score"] = df.apply(circularity_score, axis=1)
    df["recommended_action"] = df["score"].apply(action)
    return df

@st.cache_data
def load_demo():
    return prepare(pd.read_csv(DATA_PATH))

st.markdown("""
<style>
.block-container {max-width: 1200px; padding-top: 2rem;}
.hero {padding: 1.2rem 0 0.7rem 0;}
.hero h1 {font-size: 3.2rem; margin-bottom: 0.1rem;}
.hero p {font-size: 1.15rem; color: #666;}
.card {border:1px solid #ddd; border-radius:16px; padding:18px; margin-bottom:12px;}
.score {font-size:3.3rem; font-weight:700;}
.small {color:#666; font-size:.9rem;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
<h1>THREAD-ID</h1>
<p>A prototype international digital product passport for the secondhand fashion economy.</p>
</div>
""", unsafe_allow_html=True)

st.info(
    "Prototype for a Digital Cooperation research project. The score is a transparent research prototype, "
    "not an official environmental footprint or certification."
)

with st.sidebar:
    st.header("Data")
    uploaded = st.file_uploader(
        "Upload a CSV with the required fields",
        type=["csv"],
        help="Required: product_id, product_name, category, material, recycled_pct, repairable, recyclable, country, brand"
    )
    if uploaded:
        try:
            df = prepare(pd.read_csv(uploaded))
            st.success(f"Loaded {len(df):,} records.")
        except Exception as e:
            st.error(str(e))
            df = load_demo()
    else:
        df = load_demo()
        st.caption("Using the included demo dataset.")

    st.divider()
    st.header("Passport fields")
    st.write("Product ID")
    st.write("Material composition")
    st.write("Recycled content")
    st.write("Origin")
    st.write("Repairability")
    st.write("Recyclability")
    st.write("Lifecycle recommendation")

tab1, tab2, tab3, tab4 = st.tabs(["Product Passport", "Dataset Explorer", "System Design", "Research Notes"])

with tab1:
    st.subheader("Look up a product")
    options = df["product_id"].tolist()
    selected = st.selectbox("Product ID", options)
    row = df.loc[df.product_id == selected].iloc[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("Circularity score", f"{row.score}/100")
    c2.metric("Recycled content", f"{row.recycled_pct:.0f}%")
    c3.metric("Country of production", row.country)

    st.markdown(f"""
    <div class="card">
    <h2>{row.product_name}</h2>
    <p><b>Brand/source:</b> {row.brand}</p>
    <p><b>Category:</b> {row.category}</p>
    <p><b>Material:</b> {row.material}</p>
    <p><b>Repairable:</b> {"Yes" if row.repairable else "No"} &nbsp; | &nbsp;
       <b>Recyclable:</b> {"Yes" if row.recyclable else "No"}</p>
    <p><b>Lifecycle recommendation:</b> {row.recommended_action}</p>
    </div>
    """, unsafe_allow_html=True)

    passport = {
        "protocol": "THREAD-ID prototype v0.1",
        "product_id": row.product_id,
        "product_name": row.product_name,
        "category": row.category,
        "material": row.material,
        "recycled_content_percent": float(row.recycled_pct),
        "country_of_production": row.country,
        "repairable": bool(row.repairable),
        "recyclable": bool(row.recyclable),
        "prototype_circularity_score": int(row.score),
        "recommended_action": row.recommended_action,
    }
    st.download_button(
        "Download digital passport (JSON)",
        data=json.dumps(passport, indent=2),
        file_name=f"{row.product_id}_passport.json",
        mime="application/json",
    )

with tab2:
    st.subheader("What does the dataset show?")
    m1, m2, m3 = st.columns(3)
    m1.metric("Products", f"{len(df):,}")
    m2.metric("Average score", f"{df.score.mean():.1f}/100")
    m3.metric("Countries", f"{df.country.nunique():,}")

    chart = px.histogram(df, x="score", nbins=10, title="Distribution of prototype circularity scores")
    st.plotly_chart(chart, use_container_width=True)

    by_material = (
        df.assign(material_group=df.material.str.split(r"\s*\+\s*").str[0])
          .groupby("material_group", as_index=False)["score"].mean()
          .sort_values("score", ascending=False)
    )
    chart2 = px.bar(by_material, x="material_group", y="score", title="Average score by material group")
    st.plotly_chart(chart2, use_container_width=True)

    st.dataframe(
        df[["product_id","product_name","category","material","recycled_pct","country","score","recommended_action"]],
        use_container_width=True,
        hide_index=True
    )

with tab3:
    st.subheader("THREAD-ID protocol")
    st.markdown("""
    **1. Persistent identity** — each garment receives a unique product identifier.

    **2. Interoperable data** — core fields use machine-readable, standardized formats so systems in
    different countries can exchange information.

    **3. Lifecycle continuity** — the passport is designed to remain useful during resale, repair,
    reuse and recycling.

    **4. Role-based access** — consumers see product/lifecycle information; authorized economic operators
    and authorities can receive additional compliance or traceability information.

    **5. No consumer profile in the passport** — the prototype does not store names, addresses, or
    other personal information.

    **6. Open governance** — countries and stakeholders would agree on the minimum schema, identifiers,
    update rules, and interoperability requirements.
    """)

    st.subheader("Why international cooperation?")
    st.write(
        "A garment can cross borders multiple times during manufacturing, sale, resale and end-of-life. "
        "A shared data standard would reduce the risk that useful product information disappears when the "
        "garment moves between companies, marketplaces or countries."
    )

with tab4:
    st.subheader("Important methodology note")
    st.write(
        "This prototype separates product-data interoperability from environmental LCA. "
        "The circularity score uses transparent heuristic weights so the software can demonstrate the "
        "concept without pretending that a student-built score is an official footprint."
    )
    st.write(
        "For the research version, replace the demo material heuristics with documented LCA factors and "
        "test the protocol against a real garment dataset."
    )

    st.subheader("Recommended research datasets")
    st.markdown("""
    - **Harmonized fast-fashion garment variants:** 47,522 H&M/Uniqlo color-specific variants with
      material composition and garment metadata.
    - **Norway post-consumer garments:** 16,464 discarded/donated garments with weight, fiber blend,
      color, brand, production year/country and other item-level attributes.
    - **Fast Fashion Eco Commitment:** 277 Zara items with price, composition and eco-tagging.
    - **Open Source LCA Database for Footwear & Apparel:** LCA impact scores for textile/apparel processes.
    """)

st.caption("THREAD-ID prototype • Digital Cooperation + circular fashion • v0.1")
