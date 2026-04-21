"""
FlowMind AI — EV Charging Station Synthetic Dataset Generator
Generates ~50,000 booking records across 90 days.
Run: pip install pandas numpy && python generate_ev_data.py
"""

import sqlite3, random, math
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

# ── CONFIG ──────────────────────────────────────
SEED = 42;  random.seed(SEED);  np.random.seed(SEED)
DAYS = 90
START_DATE = datetime(2024, 10, 1)
RECORDS_PER_DAY_BASE = 560
NO_SHOW_BASE = 0.22
DB_PATH = "ev_charging.db"
CSV_PATH = "ev_charging_bookings.csv"

# ── STATIONS (Auto-generate ~100 Bangalore stations) ──────────────

BANGALORE_ZONES = [
    ("MG Road", 12.9716, 77.5946),
    ("Whitefield", 12.9698, 77.7500),
    ("Hebbal", 13.0358, 77.5970),
    ("Koramangala", 12.9352, 77.6245),
    ("HSR Layout", 12.9116, 77.6389),
    ("Indiranagar", 12.9784, 77.6408),
    ("Electronic City", 12.8399, 77.6770),
    ("Jayanagar", 12.9308, 77.5800),
    ("Yelahanka", 13.1007, 77.5963),
    ("Marathahalli", 12.9591, 77.7009),
    ("BTM Layout", 12.9166, 77.6101),
    ("Rajajinagar", 12.9916, 77.5540),
    ("Banashankari", 12.9250, 77.5468),
    ("Malleshwaram", 13.0030, 77.5647),
    ("Bellandur", 12.9279, 77.6784),
]

def generate_station(idx):
    zone_name, base_lat, base_lng = random.choice(BANGALORE_ZONES)
    
    # Add slight geo variation (~1–3 km spread)
    lat = base_lat + np.random.uniform(-0.02, 0.02)
    lng = base_lng + np.random.uniform(-0.02, 0.02)

    return {
        "station_id": f"STN_{idx:03d}",
        "name": f"{zone_name} EV Hub {idx}",
        "location": zone_name,
        "lat": round(lat, 6),
        "lng": round(lng, 6),
        "slow_slots": random.randint(2, 6),
        "fast_slots": random.randint(2, 5),
        "rapid_slots": random.randint(1, 3),
    }

STATIONS = [generate_station(i) for i in range(100)]
CHARGER_TYPES   = ["slow", "fast", "rapid"]
CHARGER_DUR     = {"slow":(90,180), "fast":(30,60), "rapid":(15,30)}
CHARGER_WEIGHTS = [0.30, 0.50, 0.20]
USER_IDS        = [f"USR_{i:04d}" for i in range(200)]

user_noshow = {u: float(np.clip(np.random.normal(NO_SHOW_BASE,0.12),0.05,0.70)) for u in USER_IDS}
user_pref   = {u: np.random.choice(CHARGER_TYPES, p=CHARGER_WEIGHTS) for u in USER_IDS}

# ── DEMAND SHAPE ────────────────────────────────
def hour_weight(h):
    m = math.exp(-0.5*((h-9)/1.2)**2)
    e = 1.3*math.exp(-0.5*((h-18)/1.5)**2)
    return (0.05 if h<6 or h>22 else 0.15) + m + e

def day_weight(d):   return 1.30 if d.weekday()>=5 else 1.0
def event_spike(d):  return 1.60 if random.Random(d.toordinal()).random()<0.05 else 1.0

# ── NO-SHOW MODEL ───────────────────────────────
def noshow(uid, start, made_at, ctype, is_wknd):
    lead = min((start - made_at).total_seconds()/3600/72, 1.0)
    p = user_noshow[uid] + 0.10*lead
    if ctype=="rapid": p += 0.05
    if is_wknd:        p -= 0.03
    return random.random() < float(np.clip(p, 0.05, 0.75))

# ── RECORD BUILDER ───────────────────────────────
def make_booking(ts, station):
    uid   = random.choice(USER_IDS)
    ctype = user_pref[uid] if random.random()<0.65 else np.random.choice(CHARGER_TYPES,p=CHARGER_WEIGHTS)
    dur   = random.randint(*CHARGER_DUR[ctype])
    lead  = random.randint(5, 2880)
    made  = ts - timedelta(minutes=lead)
    b_end = ts + timedelta(minutes=dur)
    iswk  = ts.weekday()>=5
    ns    = noshow(uid, ts, made, ctype, iswk)
    a_s   = (ts + timedelta(minutes=random.randint(0,10))) if not ns else None
    a_e   = (a_s + timedelta(minutes=max(dur+random.randint(-5,10),5))) if a_s else None
    fmt   = lambda d: d.strftime("%Y-%m-%d %H:%M:%S") if d else None
    return {
        "booking_id":"PLACEHOLDER","station_id":station["station_id"],
        "user_id":uid,"charger_type":ctype,
        "booking_made_at":fmt(made),"timestamp":fmt(ts),
        "booking_start":fmt(ts),"booking_end":fmt(b_end),
        "actual_start":fmt(a_s),"actual_end":fmt(a_e),
        "no_show":int(ns),"duration_booked_mins":dur,
        "lead_time_hours":round(lead/60,2),"is_weekend":int(iswk),
        "day_of_week":ts.strftime("%A"),"hour_of_day":ts.hour,
    }

# ── GENERATE ────────────────────────────────────
print("Generating dataset...")
records = []
for d in range(DAYS):
    date  = START_DATE + timedelta(days=d)
    dmult = day_weight(date) * event_spike(date)
    for h in range(24):
        n = max(0, int(np.random.poisson(RECORDS_PER_DAY_BASE * hour_weight(h) * dmult / 24)))
        for _ in range(n):
            ts = date.replace(hour=h, minute=random.randint(0,59), second=0)
            records.append(make_booking(ts, random.choice(STATIONS)))
    if (d+1)%30==0: print(f"  {d+1}/{DAYS} days — {len(records):,} records")

df = pd.DataFrame(records).sort_values("booking_start").reset_index(drop=True)
df["booking_id"] = [f"BK{i:07d}" for i in range(len(df))]

# ── STATS ───────────────────────────────────────
print(f"\nTotal bookings : {len(df):,}")
print(f"No-show rate   : {df['no_show'].mean():.1%}")
print(f"Date range     : {df['booking_start'].min()} → {df['booking_start'].max()}")
print("Charger split  :", df["charger_type"].value_counts().to_dict())

# ── SAVE ────────────────────────────────────────
stations_df = pd.DataFrame(STATIONS)
users_df    = pd.DataFrame([{
    "user_id":u,"noshow_tendency":round(user_noshow[u],3),
    "preferred_charger":user_pref[u],
    "registered_date":(START_DATE-timedelta(days=random.randint(30,730))).strftime("%Y-%m-%d")
} for u in USER_IDS])

conn = sqlite3.connect(DB_PATH)
df.to_sql("bookings", conn, if_exists="replace", index=False)
stations_df.to_sql("stations", conn, if_exists="replace", index=False)
users_df.to_sql("users", conn, if_exists="replace", index=False)
for idx in ["CREATE INDEX IF NOT EXISTS idx_st ON bookings(station_id,booking_start)",
            "CREATE INDEX IF NOT EXISTS idx_u  ON bookings(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_ns ON bookings(no_show)",
            "CREATE INDEX IF NOT EXISTS idx_hr ON bookings(hour_of_day)"]:
    conn.execute(idx)
conn.commit(); conn.close()

df.to_csv(CSV_PATH, index=False)
print(f"\nSaved → {DB_PATH} + {CSV_PATH}")
print("Done!")