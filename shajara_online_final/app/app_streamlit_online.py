# app/app_streamlit_online.py
import os, requests, json, io, re, unicodedata
import pandas as pd
import streamlit as st
import altair as alt
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="SHAJARA – Early Warning Dashboard", layout="wide")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

# ---------------------- Load data from Supabase ----------------------
@st.cache_data(ttl=300)
def load_posts(limit=5000):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return pd.DataFrame(), "no-supabase"
    q = f"{SUPABASE_URL}/rest/v1/posts?select=*&order=datetime_utc.desc&limit={limit}"
    r = requests.get(q, headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}, timeout=15)
    r.raise_for_status()
    df = pd.DataFrame(r.json())
    if df.empty:
        for c in ["text","admin_area","tension_level","datetime_utc","collected_at_utc","post_url","source_name"]:
            df[c] = ""
        return df, SUPABASE_URL
    d1 = pd.to_datetime(df.get("datetime_utc"), errors="coerce", utc=True)
    d2 = pd.to_datetime(df.get("collected_at_utc"), errors="coerce", utc=True)
    df["datetime_utc"] = d1.fillna(d2)
    # normalize tension level (fallback simple rules)
    tl = df.get("tension_level", pd.Series([""]*len(df))).astype(str).str.strip().str.title()
    tl = tl.replace({"Nan":"", "None":"", "":""})
    def infer(txt):
        s = str(txt).lower()
        if any(k in s for k in ["قتل","تفجير","هجوم","اشتباك","خطف","ثأر","رصاص","قذيفه","قذيفة","سلاح","حرب"]): return "High"
        if any(k in s for k in ["توتر","احتجاج","مظاهرة","اعتصام","تحشيد","تحريض","اغلاق","قطع طريق"]): return "Medium"
        if any(k in s for k in ["خلاف","شجار","مشادة","مشكل","عراك"]): return "Low"
        return "Unclassified"
    tl = tl.mask(tl.eq(""), df["text"].apply(infer).str.title())
    df["tension_level"] = tl.str.title()
    return df, SUPABASE_URL

df, data_src = load_posts()
st.sidebar.success(f"Source: {'Supabase' if data_src!='no-supabase' else 'No Supabase configured'}")

# ---------------------- Filters ----------------------
st.sidebar.header("Filters")
if df.empty:
    min_d = pd.Timestamp.today()
    max_d = pd.Timestamp.today()
else:
    min_d = pd.to_datetime(df["datetime_utc"]).min()
    max_d = pd.to_datetime(df["datetime_utc"]).max()
start = st.sidebar.date_input("From", min_d.date())
end   = st.sidebar.date_input("To",   max_d.date())
levels = ["High","Medium","Low","Unclassified"]
present = [l for l in levels if l in (df.get("tension_level", pd.Series()).astype(str).unique().tolist())] or levels
sel_lvls = st.sidebar.multiselect("Tension levels", options=levels, default=present)

mask = pd.Series([True]*len(df)) if not df.empty else pd.Series([], dtype=bool)
if not df.empty and "datetime_utc" in df.columns and not df["datetime_utc"].isna().all():
    mask &= (df["datetime_utc"].dt.date >= start) & (df["datetime_utc"].dt.date <= end)
if sel_lvls and not df.empty:
    mask &= df["tension_level"].astype(str).isin(sel_lvls)
df_f = df[mask].copy() if not df.empty else df.copy()

# ---------------------- Metrics ----------------------
c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("Total posts", len(df_f))
with c2: st.metric("High-Risk",  int(df_f["tension_level"].astype(str).str.lower().str.contains("high").sum() if not df_f.empty else 0))
with c3: st.metric("Medium-Risk",int(df_f["tension_level"].astype(str).str.lower().str.contains("medium").sum() if not df_f.empty else 0))
with c4: st.metric("Low-Risk",   int(df_f["tension_level"].astype(str).str.lower().str.contains("low").sum() if not df_f.empty else 0))
st.markdown("---")

# ---------------------- Risk over time ----------------------
st.subheader("📈 Risk over Time (stacked)")
if not df_f.empty and "datetime_utc" in df_f.columns and not df_f["datetime_utc"].isna().all():
    tmp = df_f.copy()
    tmp["date_only"] = tmp["datetime_utc"].dt.date
    grp = tmp.groupby(["date_only","tension_level"]).size().reset_index(name="count")
    order = ["High","Medium","Low","Unclassified"]
    grp["tension_level"] = pd.Categorical(grp["tension_level"], order, ordered=True)
    chart = alt.Chart(grp).mark_area().encode(
        x=alt.X("date_only:T", title="Date"),
        y=alt.Y("count:Q", stack="zero", title="Posts"),
        color=alt.Color("tension_level:N", sort=order, legend=alt.Legend(title="Level"))
    ).properties(height=300)
    st.altair_chart(chart, use_container_width=True)
else:
    st.info("لا توجد تواريخ صالحة للعرض.")
st.markdown("---")

# ---------------------- Latest High-Risk ----------------------
st.subheader("⚠️ Latest High-Risk Posts")
if not df_f.empty:
    latest = df_f[df_f["tension_level"].astype(str).str.lower().str.contains("high")].sort_values("datetime_utc", ascending=False)
    st.dataframe(latest[["datetime_utc","source_name","text","post_url","admin_area"]], use_container_width=True)
else:
    st.warning("لا توجد بيانات بعد. شغّل الـCollectors أو استورد CSV في Supabase.")

st_autorefresh(interval=1000 * 60 * 60 * 3, key="auto_refresh")
