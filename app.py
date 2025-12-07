# app.py — Integrated & updated (fixed undefined functions)
import streamlit as st
import streamlit.components.v1 as components
import random
import json
import time
import re
import urllib.parse
import html as _html
from datetime import date, timedelta
from dateutil import parser as dateparser

from scorer import score_item
from gemini_wrapper import explain_with_gemini, parse_search_with_gemini, choose_hotel_with_gemini, USE_GEMINI
from itinerary import generate_itinerary
from pois_real import get_pois_map   # keep the same external files you had

# page config
st.set_page_config(page_title="Travel Reco — Fixed Parser", layout="wide")

# --------------------------- CSS ---------------------------
APP_CSS = """
<style>
main .block-container { max-width: 1200px; margin-left:auto; margin-right:auto; padding-left:16px; padding-right:16px; }
.header-row { display:flex; align-items:center; justify-content:space-between; gap:12px; }
.brand { font-size:22px; font-weight:700; }
.subtle { color:#6c6c70; font-size:13px; }
.card-row { display:flex; flex-wrap:wrap; gap:12px; margin-top:12px; }
.hotel-card { width:260px; border-radius:10px; box-shadow:0 6px 18px rgba(0,0,0,0.08); overflow:hidden; background:white; }
.hotel-thumb { width:100%; height:150px; object-fit:cover; display:block; }
.hotel-body { padding:10px; }
.hotel-explain { margin-top:8px; font-size:12px; color:#555; }
.small-meta { font-size:13px; color:#666; }
.poi-card { width:320px; border-radius:10px; box-shadow:0 6px 18px rgba(0,0,0,0.06); overflow:hidden; background:white; }
.poi-thumb { width:100%; height:180px; object-fit:cover; display:block; }
.poi-body { padding:10px; }
.itinerary-day { border-radius:8px; padding:8px; background:#fbfbfd; margin-bottom:8px; }
.icon-row { display:flex; gap:8px; align-items:center; }
.logo-small { width:28px; height:28px; border-radius:6px; display:inline-block; }
.right-col { position:sticky; top:12px; }
pre, code, .stMarkdown, .stText, .hotel-explain { white-space: pre-wrap !important; word-break: break-word !important; max-width: 100%; }
@media (max-width: 900px){
  .hotel-card{ width:47%; }
  .header-row { flex-direction:column; align-items:flex-start; gap:8px; }
}
</style>
"""
st.markdown(APP_CSS, unsafe_allow_html=True)

PALETTE = ["#ea1e63", "#131314", "#e8e4f2", "#f6a4c8", "#ca356c", "#fdd5ed", "#86838b", "#dc6a96"]

def format_rupee(amt):
    try:
        return f"₹{int(amt):,}"
    except Exception:
        try:
            return f"₹{float(amt):,}"
        except Exception:
            return f"₹{amt}"

def make_svg_thumbnail(text, bg_color="#e8e4f2", fg_color="#131314", w=320, h=180):
    label = "".join([p[0] for p in text.split()][:2]).upper()
    short = (text[:20] + '...') if len(text) > 20 else text
    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}' viewBox='0 0 {w} {h}'>
      <rect width='100%' height='100%' rx='8' fill='{bg_color}' />
      <text x='50%' y='44%' dominant-baseline='middle' text-anchor='middle' font-family='Arial, Helvetica, sans-serif' font-size='56' fill='{fg_color}' font-weight='700'>{label}</text>
      <text x='50%' y='78%' dominant-baseline='middle' text-anchor='middle' font-family='Arial' font-size='16' fill='{fg_color}'>{short}</text>
    </svg>"""
    svg_encoded = urllib.parse.quote(svg)
    return f"data:image/svg+xml;utf8,{svg_encoded}"

def make_stock_photo(seed_id, w=640, h=420):
    seed = abs(hash(seed_id)) % 1000
    return f"https://picsum.photos/seed/{seed}/{w}/{h}"

def make_poi_photo(poi_id, w=640, h=360):
    # use separate seed space so POIs look different from hotels
    seed = abs(hash("poi_" + poi_id)) % 1000
    return f"https://picsum.photos/seed/{seed}/{w}/{h}"

def make_logo_svg(kind="flight"):
    if kind == "flight":
        svg = """<svg xmlns='http://www.w3.org/2000/svg' width='56' height='56' viewBox='0 0 24 24'>
            <rect rx='6' width='100%' height='100%' fill='#e8f4ff'/>
            <path d='M2 19l20-7-8-2-9 4v5z' fill='#2b7cff'/>
        </svg>"""
    else:
        svg = """<svg xmlns='http://www.w3.org/2000/svg' width='56' height='56' viewBox='0 0 24 24'>
            <rect rx='6' width='100%' height='100%' fill='#f7f8e8'/>
            <path d='M7 3h10v10H7z' fill='#7aa02b'/>
            <path d='M4 15h16v2H4z' fill='#a4c76b' />
        </svg>"""
    return "data:image/svg+xml;utf8," + urllib.parse.quote(svg)

def hotel_card_html(photo_url, hotel):
    name = _html.escape(hotel["name"])
    price = format_rupee(hotel["price"])
    rating = hotel["rating"]
    tags = _html.escape(", ".join(hotel.get("tags", [])))
    html_block = f"""
    <div class="hotel-card">
      <img class="hotel-thumb" src="{photo_url}" />
      <div class="hotel-body">
        <div style="font-weight:700;font-size:15px">{name}</div>
        <div class="small-meta" style="margin-top:6px">{tags}</div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-top:10px">
          <div style="font-weight:700">{price}</div>
          <div style="background:#f1f1f1;padding:6px;border-radius:6px;font-size:12px">{rating}★</div>
        </div>
      </div>
    </div>
    """
    return html_block

def poi_card_html(photo_url, poi, minutes_from_hotel=None, cost_from_hotel=None):
    name = _html.escape(poi["name"])
    cat = _html.escape(poi.get("category",""))
    mins = f"{minutes_from_hotel} mins" if minutes_from_hotel is not None else f"{poi.get('approx_travel_mins_from_hotel','?')} mins"
    cost = format_rupee(cost_from_hotel) if cost_from_hotel is not None else format_rupee(poi.get("approx_cost_from_hotel",0))
    html = f"""
    <div class="poi-card">
      <img class="poi-thumb" src="{photo_url}" />
      <div class="poi-body">
        <div style="font-weight:700;font-size:15px">{name}</div>
        <div class="small-meta" style="margin-top:6px">{cat} • {mins} • {cost}</div>
        <div style="margin-top:8px;font-size:13px;color:#444">{_html.escape(poi.get('description',''))}</div>
      </div>
    </div>
    """
    return html

def render_parsed_summary(parsed, dest_map):
    if not parsed:
        return None
    parts = []
    dst = parsed.get("destination_id")
    if dst and dst in dest_map:
        parts.append(f"Destination: **{dest_map[dst]['name']}**")
    elif parsed.get("destination"):
        parts.append(f"Destination: **{parsed.get('destination')}**")
    origin = parsed.get("origin") or parsed.get("from")
    if origin:
        parts.append(f"Origin: **{origin}**")
    tags = parsed.get("tags") or []
    if tags:
        parts.append("Tags: " + ", ".join(tags))
    bm = parsed.get("budget_max") or parsed.get("max_price")
    if bm:
        try:
            parts.append(f"Budget max: **{format_rupee(bm)}**")
        except Exception:
            parts.append(f"Budget max: **{bm}**")
    tt = parsed.get("trip_type")
    if tt:
        parts.append(f"Trip type: **{tt}**")
    nights = parsed.get("nights")
    if nights:
        parts.append(f"Nights: **{nights}**")
    if not parts:
        return None
    return " · ".join(parts)

# --------------------------- Mock data generation (unchanged) ---------------------------
@st.cache_data
def generate_mock_data(seed=42):
    random.seed(seed)
    city_list = [
        "Mumbai","Delhi","Bengaluru","Chennai","Kolkata","Goa","Jaipur","Udaipur","Agra","Varanasi",
        "Amritsar","Lucknow","Shimla","Manali","Srinagar","Leh","Munnar","Kochi","Pune","Hyderabad"
    ]
    destinations = []
    for i, city in enumerate(city_list):
        destinations.append({
            "id": f"dest_{i}",
            "name": city,
            "avg_price": random.randint(4000,15000),
            "tags": random.sample(["beach","culture","mountains","adventure","nature","relax","city","heritage","shopping","spiritual"], 2),
            "seasonality": round(random.uniform(0.4,1.0),2)
        })

    hotels=[]
    for i in range(30):
        dest = random.choice(destinations)
        price = random.randint(500,10000)
        rating = round(random.uniform(2.0,4.9),1)
        hotels.append({
            "id": f"hotel_{i}",
            "name": f"{dest['name']} Hotel {i}",
            "destination_id": dest["id"],
            "price": price,
            "rating": rating,
            "tags": random.sample(dest["tags"] + ["pool","spa","wifi","family","budget","luxury","boutique"], 3),
            "popularity": round(random.random(),2)
        })

    airlines = ["Air India","IndiGo","SpiceJet","Vistara","GoAir","AirAsia"]
    flights=[]
    total_targets = 400
    per_dest_min = 10
    for idx_dest, dest in enumerate(destinations):
        nd = random.randint(per_dest_min, max(per_dest_min, 20))
        for idx in range(nd):
            dep = random.choice(["Mumbai","Delhi","Bengaluru","Chennai","Kolkata","Hyderabad","Pune"])
            arr = dest["name"]
            stops = random.choice([0,0,0,1])
            duration = random.randint(60, 600) + stops*60
            price = random.randint(1500, 15000)
            flights.append({
                "id": f"flight_{dest['id']}_{idx}",
                "airline": random.choice(airlines),
                "from": dep,
                "to": arr,
                "stops": stops,
                "duration_mins": duration,
                "price": price,
                "departure_time": f"{random.randint(0,23):02d}:{random.choice([0,15,30,45]):02d}",
                "arrival_time": None,
                "layovers": [] if stops==0 else [random.choice(["DXB","SIN","BKK","DEL","BLR"])]
            })
    while len(flights) < total_targets:
        dest = random.choice(destinations)
        idx = len(flights)
        dep = random.choice(["Mumbai","Delhi","Bengaluru"])
        arr = dest["name"]
        stops = random.choice([0,1])
        duration = random.randint(60, 600) + stops*60
        price = random.randint(1500,15000)
        flights.append({
            "id": f"flight_extra_{idx}",
            "airline": random.choice(airlines),
            "from": dep,
            "to": arr,
            "stops": stops,
            "duration_mins": duration,
            "price": price,
            "departure_time": f"{random.randint(0,23):02d}:{random.choice([0,15,30,45]):02d}",
            "arrival_time": None,
            "layovers": [] if stops==0 else [random.choice(["SIN","DXB","KUL","DEL"])]
        })

    train_dest_candidates = random.sample(destinations, 15)
    trains=[]
    total_train_target = 300
    for dest in train_dest_candidates:
        for t in range(12 + random.randint(0,8)):
            trains.append({
                "id": f"train_{dest['id']}_{t}",
                "from": random.choice(["Mumbai","Delhi","Chennai","Kolkata","Bengaluru","Hyderabad"]),
                "to": dest["name"],
                "duration_mins": random.randint(120, 1800),
                "price": random.randint(300, 3000),
                "departure_time": f"{random.randint(0,23):02d}:{random.choice([0,15,30,45]):02d}",
                "arrival_time": None,
                "class": random.choice(["Sleeper","3A","2A","CC"])
            })
    while len(trains) < total_train_target:
        dest = random.choice(train_dest_candidates)
        idx = len(trains)
        trains.append({
            "id": f"train_extra_{idx}",
            "from": random.choice(["Mumbai","Delhi","Chennai"]),
            "to": dest["name"],
            "duration_mins": random.randint(120, 1800),
            "price": random.randint(300, 3000),
            "departure_time": f"{random.randint(0,23):02d}:{random.choice([0,15,30,45]):02d}",
            "arrival_time": None,
            "class": random.choice(["Sleeper","3A","2A","CC"])
        })

    users = [
        {"id":"user_anna","name":"Anna (Budget Beach Lover)","profile":{"trip_type":"solo","budget":{"min":5000,"max":12000},"interests":["beach","nightlife"]},
         "past_trips":[{"destination_id":"dest_5","year":2023,"tags":["beach","nightlife"]},{"destination_id":"dest_3","year":2022,"tags":["relax","culture"]}]},
        {"id":"user_raj","name":"Raj (Adventure Seeker)","profile":{"trip_type":"couple","budget":{"min":10000,"max":20000},"interests":["adventure","nature","photography"]},
         "past_trips":[{"destination_id":"dest_2","year":2024,"tags":["adventure"]},{"destination_id":"dest_14","year":2021,"tags":["photography","nature"]}]},
        {"id":"user_sara","name":"Sara (Family Relax)","profile":{"trip_type":"family","budget":{"min":8000,"max":15000},"interests":["family","relax","culture"]},
         "past_trips":[{"destination_id":"dest_12","year":2022,"tags":["family","mountains"]},{"destination_id":"dest_8","year":2020,"tags":["heritage","culture"]}]}
    ]

    return {
        "destinations": destinations,
        "hotels": hotels,
        "flights": flights,
        "trains": trains,
        "users": users
    }

data = generate_mock_data()
destinations = data["destinations"]
hotels = data["hotels"]
flights = data["flights"]
trains = data["trains"]
users = data["users"]
user_map = {u["id"]:u for u in users}
dest_map = {d["id"]:d for d in destinations}
pois_map = get_pois_map(destinations, seed=42)

# --------------------------- City resolution & other helpers (unchanged) ---------------------------
KNOWN_CITY_NAMES = set([d["name"].lower() for d in destinations] + ["mumbai","delhi","bengaluru","chennai","kolkata","hyderabad","pune","goa","jaipur","udaipur","agra","varanasi","amritsar","lucknow","shimla","manali","srinagar","leh","munnar","kochi"])

def resolve_city_name(name):
    if not name: return None
    s = str(name).strip().lower()
    if s in KNOWN_CITY_NAMES:
        for d in destinations:
            if d["name"].lower() == s:
                return d["name"]
        return s.title()
    # startswith or substring heuristics
    for d in destinations:
        dn = d["name"].lower()
        if dn.startswith(s) or s.startswith(dn) or s in dn or dn in s:
            return d["name"]
    s2 = re.sub(r'\b(to|from)\b', '', s).strip()
    for d in destinations:
        dn = d["name"].lower()
        if s2 and (s2 == dn or s2 in dn or dn in s2):
            return d["name"]
    return None

def detect_destination_in_text(text):
    if not text: return None
    t_lower = text.lower()
    matches = []
    for d in destinations:
        name_lower = d["name"].lower()
        for m in re.finditer(r'\b' + re.escape(name_lower) + r'\b', t_lower):
            matches.append((d["id"], name_lower, m.start(), m.end()))
    if not matches: return None
    to_match = re.search(r'\bto\b', t_lower)
    if to_match:
        to_pos = to_match.end()
        after_to = [m for m in matches if m[2] >= to_pos]
        if after_to:
            chosen = sorted(after_to, key=lambda x: x[2])[0]
            return chosen[0]
    chosen = sorted(matches, key=lambda x: x[2])[-1]
    return chosen[0]

def detect_origin_in_text(text):
    if not text: return None
    t_lower = text.lower()
    matches = []
    for cname in KNOWN_CITY_NAMES:
        for m in re.finditer(r'\b' + re.escape(cname) + r'\b', t_lower):
            matches.append((cname, m.start(), m.end()))
    if not matches: return None
    from_match = re.search(r'\bfrom\b', t_lower)
    if from_match:
        from_pos = from_match.end()
        after_from = [m for m in matches if m[1] >= from_pos]
        if after_from:
            chosen = sorted(after_from, key=lambda x: x[1])[0]
            return resolve_city_name(chosen[0])
    to_match = re.search(r'\bto\b', t_lower)
    if to_match:
        to_pos = to_match.start()
        before_to = [m for m in matches if m[2] <= to_pos]
        if before_to:
            chosen = sorted(before_to, key=lambda x: x[1])[-1]
            return resolve_city_name(chosen[0])
    chosen = sorted(matches, key=lambda x: x[1])[0]
    return resolve_city_name(chosen[0])

# budget parsing helpers
def _parse_budget_string(s):
    if s is None: return None
    s = str(s).lower().strip()
    s = s.replace("₹", "").replace("rs.", "").replace("rs", "").replace("inr", "").replace("$", "").replace("usd", "").strip()
    m = re.search(r"([0-9]+(?:[.,][0-9]+)?)\s*([km]?)", s)
    if m:
        num = m.group(1).replace(",", "")
        suf = m.group(2)
        try:
            val = float(num)
            if suf == "k":
                val = val * 1000.0
            elif suf == "m":
                val = val * 1000000.0
            return int(val)
        except:
            return None
    m2 = re.search(r"([0-9][0-9,\.]+)", s)
    if m2:
        try:
            return int(float(m2.group(1).replace(",", "")))
        except:
            return None
    return None

def _normalize_max_price(p):
    if p is None: return None
    if isinstance(p, (int, float)):
        try:
            return int(p)
        except:
            return None
    try:
        return _parse_budget_string(p)
    except:
        return None

# Wrapper parse_search (uses gemini_wrapper.parse_search_with_gemini but falls back)
def parse_search(text):
    if not text or text.strip() == "": return {}
    if "search_cache" not in st.session_state:
        st.session_state["search_cache"] = {}
    if text in st.session_state["search_cache"]:
        return st.session_state["search_cache"][text]

    field_sources = {}
    parsed = {}
    try:
        parsed = parse_search_with_gemini(text) or {}
        for k in parsed.keys():
            field_sources[k] = "gemini" if USE_GEMINI else "heuristic"
    except Exception:
        parsed = {}
    parsed.setdefault("tags", [])

    if parsed.get("from") and not parsed.get("origin"):
        parsed["origin"] = parsed.get("from"); field_sources.setdefault("origin", "gemini")

    # destination resolution heuristics
    if parsed.get("destination_id"):
        if parsed.get("destination_id") not in dest_map:
            parsed.pop("destination_id", None)
            field_sources.pop("destination_id", None)
    if not parsed.get("destination_id"):
        if parsed.get("destination") and isinstance(parsed.get("destination"), str):
            resolved = resolve_city_name(parsed.get("destination"))
            if resolved:
                for did, d in dest_map.items():
                    if d["name"].lower() == resolved.lower():
                        parsed["destination_id"] = did
                        field_sources["destination_id"] = field_sources.get("destination", "heuristic")
                        break
        if not parsed.get("destination_id"):
            dest_id_local = detect_destination_in_text(text)
            if dest_id_local:
                parsed["destination_id"] = dest_id_local
                field_sources["destination_id"] = "heuristic"

    # origin
    origin_val = parsed.get("origin") or parsed.get("from") or parsed.get("source") or None
    if origin_val:
        resolved_origin = resolve_city_name(origin_val)
        if resolved_origin:
            parsed["origin"] = resolved_origin
            field_sources["origin"] = field_sources.get("origin", "gemini" if parsed.get("from") or parsed.get("origin") else "heuristic")
        else:
            parsed["origin"] = origin_val
            field_sources["origin"] = field_sources.get("origin","gemini")
    else:
        detected_origin = detect_origin_in_text(text)
        if detected_origin:
            parsed["origin"] = detected_origin
            field_sources["origin"] = "heuristic"

    # budget normalization
    budget_val = None
    if isinstance(parsed.get("budget_max"), (int, float)):
        budget_val = int(parsed.get("budget_max")); field_sources.setdefault("budget_max", "gemini")
    elif parsed.get("max_price") and isinstance(parsed.get("max_price"), (int, float)):
        budget_val = int(parsed.get("max_price")); field_sources.setdefault("max_price", "gemini")
    elif parsed.get("budget_max"):
        budget_val = _parse_budget_string(parsed.get("budget_max")); field_sources.setdefault("budget_max", "gemini")
    elif parsed.get("max_price"):
        budget_val = _parse_budget_string(parsed.get("max_price")); field_sources.setdefault("max_price", "gemini")
    elif parsed.get("budget"):
        budget_val = _parse_budget_string(parsed.get("budget")); field_sources.setdefault("budget", "gemini")
    if budget_val is None:
        m = re.search(r"(?:under|below|less than|up to|upto)\s*([0-9\.,kKmM₹$usd ]+)", text, flags=re.IGNORECASE)
        if m:
            budget_val = _parse_budget_string(m.group(1))
            field_sources["budget_max"] = "heuristic"
    if budget_val is not None:
        parsed["budget_max"] = int(budget_val)

    if parsed.get("nights") is None:
        m = re.search(r'(\d+)\s*(?:nights|night)', text, flags=re.IGNORECASE)
        if m:
            try:
                parsed["nights"] = int(m.group(1)); field_sources["nights"] = "heuristic"
            except:
                pass

    parsed["_field_sources"] = field_sources
    st.session_state["search_cache"][text] = parsed
    return parsed

# --------------------------- Session state bootstrap ---------------------------
if "events" not in st.session_state: st.session_state["events"] = []
if "search_cache" not in st.session_state: st.session_state["search_cache"] = {}
if "explain_cache" not in st.session_state: st.session_state["explain_cache"] = {}
if "show_sidebar" not in st.session_state: st.session_state["show_sidebar"] = True
if "last_query" not in st.session_state: st.session_state["last_query"] = ""
if "last_parsed" not in st.session_state: st.session_state["last_parsed"] = {}
if "last_mode" not in st.session_state: st.session_state["last_mode"] = None
if "last_it_plan" not in st.session_state: st.session_state["last_it_plan"] = None
if "chosen_hotel_cache" not in st.session_state: st.session_state["chosen_hotel_cache"] = {}
if "quick_explore_cache" not in st.session_state: st.session_state["quick_explore_cache"] = {}
if "explore_dest" not in st.session_state: st.session_state["explore_dest"] = None

def log_event(event_type, user_id, item_id):
    st.session_state["events"].append({"event":event_type,"user":user_id,"item":item_id,"ts": int(time.time())})

# --------------------------- Helper functions added to fix Pylance warnings ---------------------------

def destination_recommendations(user_profile, parsed_signals, limit=6):
    """
    Return a list of destination dicts (from 'destinations') ranked for the user.
    Heuristic: tag overlap + seasonality - price distance from user's budget (if available).
    """
    interests = (user_profile.get("interests") or []) + (parsed_signals.get("tags") or [])
    budget_max = parsed_signals.get("budget_max") or user_profile.get("budget", {}).get("max")
    def score_dest(d):
        s = 0.0
        # tag overlap
        for t in interests:
            if t in d.get("tags", []):
                s += 2.0
        # seasonality a small bonus
        s += float(d.get("seasonality", 0.6))
        # price closeness (prefer avg_price <= budget_max)
        if budget_max:
            s += max(0, (1.0 - abs(d.get("avg_price",0) - budget_max) / (budget_max + 1)) ) * 0.5
        return s
    ranked = sorted(destinations, key=score_dest, reverse=True)[:limit]
    return ranked

def hotel_recommendations(user_profile, parsed_signals, limit=6):
    """
    Return hotel dicts scored using scorer.score_item and parsed filters.
    """
    # filter by destination if present
    dest_id = parsed_signals.get("destination_id")
    cand = hotels
    if dest_id:
        cand = [h for h in hotels if h["destination_id"] == dest_id]
    # budget filter
    budget = parsed_signals.get("budget_max") or user_profile.get("budget", {}).get("max")
    if budget:
        cand = [h for h in cand if h.get("price", 999999) <= budget or abs(h.get("price",0)-budget) < budget*0.5]
    # sort by our scorer (higher is better)
    scored = sorted(cand, key=lambda x: score_item(x, user_profile, user_past_trips=user_map.get(st.session_state.get("active_user_id", users[0]["id"]), {}).get("past_trips", [])), reverse=True)
    return scored[:limit]

def filter_flights(filters: dict):
    """
    filters: {"from": str or None, "to": str or None, "max_price": int or None, "max_stops": int or None}
    """
    res = flights
    f_from = filters.get("from")
    f_to = filters.get("to")
    max_price = filters.get("max_price")
    max_stops = filters.get("max_stops")
    if f_from:
        res = [f for f in res if f["from"].lower() == f_from.lower()]
    if f_to:
        res = [f for f in res if f["to"].lower() == f_to.lower()]
    if max_price:
        res = [f for f in res if f["price"] <= max_price]
    if max_stops is not None:
        res = [f for f in res if f["stops"] <= max_stops]
    # sort by price then duration
    res = sorted(res, key=lambda x: (x["price"], x["duration_mins"]))
    return res

def filter_trains(filters: dict):
    """
    filters: {"from": str or None, "to": str or None, "seat_class": str or None, "max_price": int or None}
    """
    res = trains
    f_from = filters.get("from")
    f_to = filters.get("to")
    seat_class = filters.get("seat_class")
    max_price = filters.get("max_price")
    if f_from:
        res = [t for t in res if t["from"].lower() == f_from.lower()]
    if f_to:
        res = [t for t in res if t["to"].lower() == f_to.lower()]
    if seat_class:
        res = [t for t in res if t.get("class") == seat_class]
    if max_price:
        res = [t for t in res if t["price"] <= max_price]
    res = sorted(res, key=lambda x: (x["price"], x["duration_mins"]))
    return res

# --------------------------- Helper: build explore view (now accepts active_user_id) ---------------------------
def build_explore_view(dest_id, user_profile, parsed_signals, active_user_id):
    """
    Returns structured data for the Explore view:
    - recommended_hotel (full hotel dict)
    - hotel_reason (text)
    - poi_list sorted & limited
    - itinerary (from generate_itinerary)
    """
    dest = dest_map.get(dest_id)
    if not dest:
        return None

    # candidate hotels in dest
    hotels_in_dest = [h for h in hotels if h["destination_id"] == dest_id]
    # use choose_hotel_with_gemini (fallbacks to local heuristic) to pick one
    candidate_short = []
    for c in hotels_in_dest:
        candidate_short.append({
            "id": c.get("id"),
            "name": c.get("name"),
            "price": c.get("price"),
            "rating": c.get("rating"),
            "tags": c.get("tags", [])[:5]
        })
    choice = choose_hotel_with_gemini(candidate_short, user_profile, user_past_trips=user_map.get(active_user_id, {}).get("past_trips", []))
    chosen_hotel = None
    reason_text = ""
    if choice and choice.get("hotel_id"):
        hid = choice.get("hotel_id")
        chosen_hotel = next((h for h in hotels_in_dest if h["id"] == hid), None)
        reason_text = choice.get("reason", "")
    # fallback: pick nearest to budget or cheapest
    if not chosen_hotel:
        budget_max = parsed_signals.get("budget_max") if parsed_signals else None
        if budget_max:
            # pick hotel <= budget_max and closest to budget_max, else cheapest
            under = [h for h in hotels_in_dest if h["price"] <= budget_max]
            if under:
                chosen_hotel = sorted(under, key=lambda x: abs(x["price"] - budget_max))[0]
            else:
                chosen_hotel = sorted(hotels_in_dest, key=lambda x: x["price"])[0] if hotels_in_dest else None
        else:
            chosen_hotel = sorted(hotels_in_dest, key=lambda x: x.get("price", 999999))[0] if hotels_in_dest else None
        if chosen_hotel:
            reason_text = f"Auto-picked: {chosen_hotel.get('rating','?')}★ • {format_rupee(chosen_hotel.get('price',0))}"

    # POIs (get up to 8 most relevant)
    pois = pois_map.get(dest_id, [])[:30]
    # rank POIs by interest overlap from parsed_signals or user_profile
    interests = parsed_signals.get("tags", []) if parsed_signals else []
    interests = interests or user_profile.get("interests", [])
    def poi_rank(p):
        r = 0
        if interests:
            for t in interests:
                if t in p.get("category","") or t in p.get("name","").lower():
                    r += 2
        # prefer closer to hotel
        r -= p.get("approx_travel_mins_from_hotel", 999)/100.0
        return r
    pois_sorted = sorted(pois, key=poi_rank, reverse=True)[:10]

    # itinerary generation uses our itinerary module
    nights = parsed_signals.get("nights") if parsed_signals and parsed_signals.get("nights") else 2
    it = generate_itinerary(dest_id, start_date_str=None, nights=nights, interests=interests, pace="normal", pois_map=pois_map)

    return {
        "destination": dest,
        "recommended_hotel": chosen_hotel,
        "hotel_reason": reason_text,
        "pois": pois_sorted,
        "itinerary": it
    }

# --------------------------- UI Layout ---------------------------
cols = st.columns([0.6,5,0.6])
with cols[0]:
    if st.button("☰", key="burger_btn"): st.session_state["show_sidebar"] = not st.session_state["show_sidebar"]
with cols[1]:
    st.markdown("<div class='header-row'><div><span class='brand'>Travel Reco</span><div class='subtle'>Personalized recommendations for you</div></div></div>", unsafe_allow_html=True)
    active_user_preview = st.empty()
with cols[2]:
    st.markdown("")

with st.sidebar:
    if st.session_state.get("show_sidebar", True):
        st.header("Controls")
        active_user_id = st.selectbox("Mock user", [u["id"] for u in users], index=0, format_func=lambda x: user_map[x]["name"])
        results_limit = st.slider("Results per page", 3, 12, 6)
        st.markdown("---")
        st.markdown("Classic filters (use tabs in main area)")
        st.markdown("LLM remote provider is currently disabled by default to avoid quota issues.")
    else:
        st.write("Sidebar collapsed — click ☰ to open")
        if "active_user_id" not in st.session_state:
            active_user_id = users[0]["id"]
            st.session_state["active_user_id"] = active_user_id
        else:
            active_user_id = st.session_state.get("active_user_id", users[0]["id"])
        results_limit = st.session_state.get("results_limit", 6)

st.session_state["active_user_id"] = active_user_id
st.session_state["results_limit"] = results_limit
active_profile = user_map[active_user_id]["profile"]
active_user_preview.markdown(f"<div style='font-size:14px;color:#333;'>Welcome, <strong>{user_map[active_user_id]['name'].split()[0]}</strong> — here's what's recommended for you.</div>", unsafe_allow_html=True)

main_col, side_col = st.columns([3,1])

with side_col:
    st.markdown("### Quick Ask (LLM-enabled)")
    query = st.text_input("Ask (e.g. 'flights to Kolkata under 5k')", key="side_query", value=st.session_state.get("last_query",""))
    run_query = st.button("Ask", key="side_go")
    parsed_preview = st.empty()
    show_parser_debug = st.checkbox("Show parser debug", value=False, key="parser_debug")
    st.markdown("---")
    st.markdown("#### Quick actions")
    prompts = []
    interests = active_profile.get("interests", []) or []
    budget_max = active_profile.get("budget", {}).get("max", None)
    if interests:
        prompts.append(f"Weekend {interests[0]} getaway under {budget_max} for 2 nights")
    prompts.append(f"Cheap flights to Goa under {budget_max}")
    prompts.append(f"Family 3-night itinerary to a calm hill station within {budget_max}")
    for i, p in enumerate(prompts):
        if st.button(p, key=f"quick_prompt_{i}"):
            parsed_p = {}
            try:
                parsed_p = parse_search(p)
            except Exception:
                parsed_p = {}
            st.session_state["last_query"] = p
            st.session_state["last_parsed"] = parsed_p
            ql = p.lower()
            if any(w in ql for w in ["flight","flights","air","plane"]):
                st.session_state["last_mode"] = "flights"
            elif any(w in ql for w in ["train","trains"]):
                st.session_state["last_mode"] = "trains"
            elif any(w in ql for w in ["hotel","hotels","stay","room"]):
                st.session_state["last_mode"] = "hotels"
            elif any(w in ql for w in ["itinerary","itiner","plan","days","timeline"]):
                st.session_state["last_mode"] = "itinerary"
            else:
                st.session_state["last_mode"] = "mixed"
            did = st.session_state["last_parsed"].get("destination_id")
            if did:
                # pre-generate explore content and store in quick_explore_cache
                ev = build_explore_view(did, active_profile, st.session_state.get("last_parsed", {}), active_user_id)
                if ev:
                    key = f"quick_explore::{active_user_id}::{did}"
                    st.session_state["quick_explore_cache"][key] = f"Quick Explore — {ev['destination']['name']}: {ev['hotel_reason']}"
            # no rerun; UI will update in-place

    st.markdown("---")
    st.markdown("#### Quick Explore")
    shown = 0
    items = list(st.session_state.get("quick_explore_cache", {}).items())[::-1]
    for k, v in items:
        if not k.startswith(f"quick_explore::{active_user_id}::"): continue
        st.markdown(v)
        st.markdown("---")
        shown += 1
        if shown >= 6: break
    if shown == 0:
        st.markdown("_No quick explores yet — click 'Explore <City>' cards in Recommendations to generate one._")

    if run_query and query:
        parsed = {}
        try:
            parsed = parse_search(query)
        except Exception:
            parsed = {}
        st.session_state["last_query"] = query
        st.session_state["last_parsed"] = parsed
        ql = query.lower()
        if any(w in ql for w in ["flight","flights","air","plane"]):
            mode="flights"
        elif any(w in ql for w in ["train","trains"]):
            mode="trains"
        elif any(w in ql for w in ["hotel","hotels","stay","room"]):
            mode="hotels"
        elif any(w in ql for w in ["itinerary","itiner","plan","days","timeline"]):
            mode="itinerary"
        else:
            mode="mixed"
        st.session_state["last_mode"] = mode
        summary = render_parsed_summary(parsed, dest_map)
        if summary:
            parsed_preview.markdown(f"**Interpreted:** {summary}")
        else:
            parsed_preview.markdown("*No explicit destination/tags/budget detected*")
        if show_parser_debug:
            st.markdown("**Raw parsed object**")
            st.json(parsed)
            fs = parsed.get("_field_sources", {})
            st.markdown("**Field sources (gemini vs heuristic)**")
            st.json(fs)
    else:
        parsed = st.session_state.get("last_parsed", {}) if st.session_state.get("last_query") else {}
        mode = st.session_state.get("last_mode", None)
        if parsed:
            summary = render_parsed_summary(parsed, dest_map)
            if summary:
                parsed_preview.markdown(f"**Interpreted:** {summary}")
            else:
                parsed_preview.markdown("*No explicit destination/tags/budget detected*")
        else:
            parsed_preview.markdown("_Enter a query and press Ask_")

# --------------------------- Main area ---------------------------
with main_col:
    st.markdown("### Main")
    tabs = st.tabs(["Recommendations","Flights","Trains","Hotels"])
    tab0, tab1, tab2, tab3 = tabs

    with tab0:
        st.markdown("## Recommendations")
        parsed = st.session_state.get("last_parsed", {}) if st.session_state.get("last_query") else {}
        user_query = st.session_state.get("last_query", "") or ""
        mode = st.session_state.get("last_mode", None)

        st.markdown("### Quick summary")
        if not user_query:
            st.info("Use the right-hand 'Quick Ask' to request recommendations.")
        else:
            st.markdown(f"**Query:** {user_query}")
            if parsed:
                summary = render_parsed_summary(parsed, dest_map)
                if summary:
                    st.markdown("**Interpreted:** " + summary)
        if mode:
            st.markdown(f"**Detected intent:** {mode}")

        st.markdown("### Top destinations for you")
        dests = destination_recommendations(active_profile, parsed, limit=6)
        cols = st.columns(3)
        for i, d in enumerate(dests):
            c = cols[i % 3]
            with c:
                thumb = make_svg_thumbnail(d["name"], bg_color=PALETTE[i % len(PALETTE)])
                st.image(thumb, use_column_width=True, caption=f"{d['name']} • {', '.join(d['tags'])}")
                if st.button(f"Explore {d['name']}", key=f"explore_dest_{d['id']}"):
                    # set session explore flag and keep parsed signals
                    st.session_state["explore_dest"] = d["id"]
                    st.session_state["last_parsed"] = {**parsed, "destination_id": d["id"]}
                    # also pre-generate quick_explore cache entry
                    ev = build_explore_view(d["id"], active_profile, st.session_state.get("last_parsed", {}), active_user_id)
                    if ev:
                        key = f"quick_explore::{active_user_id}::{d['id']}"
                        st.session_state["quick_explore_cache"][key] = f"Quick Explore — {ev['destination']['name']}: {ev['hotel_reason']}"

        # If user has requested to explore a city, render Explore view inline
        if st.session_state.get("explore_dest"):
            ed = st.session_state.get("explore_dest")
            st.markdown("---")
            st.markdown(f"## Explore — {dest_map[ed]['name']}")
            view = build_explore_view(ed, active_profile, st.session_state.get("last_parsed", {}), active_user_id)
            if view is None:
                st.info("No data for that destination.")
            else:
                # Recommended hotel display
                rec_h = view.get("recommended_hotel")
                if rec_h:
                    st.markdown("### Recommended hotel")
                    c1, c2 = st.columns([2,4])
                    with c1:
                        hphoto = make_stock_photo(rec_h["id"], w=540, h=340)
                        st.image(hphoto, use_column_width=True)
                    with c2:
                        st.markdown(f"**{rec_h['name']}**")
                        st.markdown(f"{', '.join(rec_h.get('tags', []))}")
                        st.markdown(f"Rating: **{rec_h['rating']}★**")
                        st.markdown(f"Price: **{format_rupee(rec_h['price'])}**")
                        st.markdown(f"Why recommended: {view.get('hotel_reason')}")
                        if st.button("Select this hotel", key=f"select_h_{rec_h['id']}"):
                            st.session_state["chosen_hotel"] = rec_h["id"]
                            st.success("Hotel selected for itinerary and distance calculations.")

                # POIs grid
                st.markdown("### Attractions & POIs")
                poi_htmls = []
                for p in view.get("pois", []):
                    pid = p["id"]
                    photo = make_poi_photo(pid, w=640, h=360)
                    # compute travel & cost from chosen hotel if available; else use approx fields
                    minutes = p.get("approx_travel_mins_from_hotel")
                    cost = p.get("approx_cost_from_hotel")
                    poi_htmls.append(poi_card_html(photo, p, minutes_from_hotel=minutes, cost_from_hotel=cost))
                if poi_htmls:
                    row_html = "<div style='display:flex;flex-wrap:wrap;gap:12px;'>" + "".join(poi_htmls) + "</div>"
                    components.html(row_html, height=760, scrolling=True)

                # Itinerary section
                st.markdown("### Suggested itinerary (mock deterministic)")
                it = view.get("itinerary", {})
                for day in it.get("days", []):
                    st.markdown(f"<div class='itinerary-day'><strong>{day['date']}</strong></div>", unsafe_allow_html=True)
                    for slot in ["morning","afternoon","evening"]:
                        items = day.get(slot, [])
                        if items:
                            cols = st.columns(len(items))
                            for idx, poi in enumerate(items):
                                with cols[idx]:
                                    ph = make_poi_photo(poi["id"], w=320, h=180)
                                    st.image(ph, use_column_width=True, caption=f"{poi['name']} ({poi.get('approx_travel_mins_from_hotel')} mins from hotel)")
                                    st.markdown(f"**{slot.title()}** — {poi['name']}")
                        else:
                            st.markdown(f"*{slot.title()}: No recommendation*")
                st.markdown("---")
                if st.button("Close explore", key="close_explore"):
                    st.session_state["explore_dest"] = None

        # quick hotels (as before)
        if st.session_state.get("_show_top_hotels") or mode in ["hotels","mixed"]:
            st.markdown("### Top hotels (quick)")
            recs = hotel_recommendations(active_profile, parsed, limit=6)
            if not recs:
                st.info("No hotels found for that query")
            else:
                card_htmls = []
                for i, hotel in enumerate(recs):
                    photo = make_stock_photo(hotel["id"])
                    base_card = hotel_card_html(photo, hotel)
                    key = f"{active_user_id}_{hotel['id']}"
                    if key not in st.session_state["explain_cache"]:
                        st.session_state["explain_cache"][key] = explain_with_gemini(hotel, active_profile, parsed)
                    expl_html = f"<div class='hotel-explain'>{st.session_state['explain_cache'][key]}</div>"
                    card_with_expl = base_card.replace("<!--EXPLAIN-->", expl_html)
                    card_htmls.append(card_with_expl)
                if card_htmls:
                    full_html = "<div class='card-row'>" + "".join(card_htmls) + "</div>"
                    components.html(full_html, height=380, scrolling=True)

    # Flights / Trains / Hotels tabs (functional)
    with tab1:
        st.markdown("## Flights")
        c1, c2 = st.columns([1,2])
        with c1:
            st.markdown("### Filters")
            parsed = st.session_state.get("last_parsed", {}) if st.session_state.get("last_query") else {}
            to_default = None
            if parsed.get("destination_id"):
                to_default = dest_map[parsed["destination_id"]]["name"]
            from_default = parsed.get("origin") or None
            price_default = parsed.get("budget_max") or 15000
            stops_default = parsed.get("max_stops") if parsed.get("max_stops") is not None else 2

            origins = ["Any","Mumbai","Delhi","Bengaluru","Chennai","Kolkata","Hyderabad","Pune"]
            from_idx = 0
            if from_default and from_default in origins:
                from_idx = origins.index(from_default)
            from_city = st.selectbox("From", origins, index=from_idx, key="flt_from_main")
            to_options = ["Any"] + [d["name"] for d in destinations]
            to_idx = 0
            if to_default and to_default in to_options:
                to_idx = to_options.index(to_default)
            to_city = st.selectbox("To", to_options, index=to_idx, key="flt_to_main")
            max_price = st.number_input("Max price (₹)", value=int(price_default) if price_default else 15000, key="flt_max_price")
            max_stops = st.selectbox("Max stops", [0,1,2], index=0 if stops_default==0 else (1 if stops_default==1 else 2), key="flt_max_stops")
            apply_f = st.button("Apply flight filters", key="apply_flights_main")

        with c2:
            st.markdown("### Results")
            if apply_f:
                to_val = None if to_city == "Any" else to_city
                from_val = None if from_city == "Any" else from_city
                res = filter_flights({"from": from_val, "to": to_val, "max_price": max_price, "max_stops": max_stops})
            else:
                parsed = st.session_state.get("last_parsed", {}) if st.session_state.get("last_query") else {}
                origin_val = parsed.get("origin")
                to_val = None
                if parsed.get("destination_id"):
                    to_val = dest_map[parsed["destination_id"]]["name"]
                elif parsed.get("destination"):
                    to_val = resolve_city_name(parsed.get("destination"))
                max_price = _normalize_max_price(parsed.get("budget_max") or parsed.get("max_price")) or 15000
                max_stops = parsed.get("max_stops")
                res = filter_flights({"from": origin_val, "to": to_val, "max_price": max_price, "max_stops": max_stops})

            if not res:
                st.info("No flights found with those filters")
            else:
                for flight in res[:results_limit]:
                    logo = make_logo_svg("flight")
                    st.markdown(f"<div class='icon-row'><img src='{logo}' class='logo-small'/> <strong>{flight['airline']}</strong> — {flight['from']} → {flight['to']} • {format_rupee(flight['price'])} • {flight['stops']} stops</div>", unsafe_allow_html=True)
                    if st.button(f"Book flight {flight['id']}", key=f"book_f_{flight['id']}"):
                        log_event("book_flight", active_user_id, flight["id"])
                        st.success("Flight booked (mock)")

    with tab2:
        st.markdown("## Trains")
        c1, c2 = st.columns([1,2])
        with c1:
            st.markdown("### Filters")
            parsed = st.session_state.get("last_parsed", {}) if st.session_state.get("last_query") else {}
            from_default = parsed.get("origin")
            to_default = None
            if parsed.get("destination_id"):
                to_default = dest_map[parsed["destination_id"]]["name"]
            max_price_default = parsed.get("budget_max") or 3000

            origins = ["Any","Mumbai","Delhi","Bengaluru","Chennai","Kolkata","Hyderabad","Pune"]
            from_idx = 0
            if from_default and from_default in origins:
                from_idx = origins.index(from_default)
            t_from = st.selectbox("From", origins, index=from_idx, key="trn_from_main")
            t_to_options = ["Any"] + [d["name"] for d in destinations]
            t_to_idx = 0
            if to_default and to_default in t_to_options:
                t_to_idx = t_to_options.index(to_default)
            t_to = st.selectbox("To", t_to_options, index=t_to_idx, key="trn_to_main")
            seat_class = st.selectbox("Class", ["Any","Sleeper","3A","2A","CC"], index=0, key="trn_class_main")
            max_price_train = st.number_input("Max price (₹)", value=int(max_price_default), key="trn_max_price")
            apply_t = st.button("Apply train filters", key="apply_trains_main")
        with c2:
            st.markdown("### Results")
            if apply_t:
                from_val = None if t_from=="Any" else t_from
                to_val = None if t_to=="Any" else t_to
                tres = filter_trains({"from": from_val, "to": to_val, "seat_class": None if seat_class=="Any" else seat_class, "max_price": max_price_train})
            else:
                parsed = st.session_state.get("last_parsed", {}) if st.session_state.get("last_query") else {}
                origin_val = parsed.get("origin")
                to_val = None
                if parsed.get("destination_id"):
                    to_val = dest_map[parsed["destination_id"]]["name"]
                max_price_train = _normalize_max_price(parsed.get("budget_max")) or 3000
                tres = filter_trains({"from": origin_val, "to": to_val, "seat_class": None, "max_price": max_price_train})

            if not tres:
                st.info("No trains found")
            else:
                for train in tres[:results_limit]:
                    logo = make_logo_svg("train")
                    st.markdown(f"<div class='icon-row'><img src='{logo}' class='logo-small'/> <strong>Train</strong> — {train['from']} → {train['to']} • {format_rupee(train['price'])} • {train['class']}</div>", unsafe_allow_html=True)
                    if st.button(f"Book train {train['id']}", key=f"book_t_{train['id']}"):
                        log_event("book_train", active_user_id, train['id'])
                        st.success("Train booked (mock)")

    with tab3:
        st.markdown("## Hotels")
        c1, c2 = st.columns([1,2])
        with c1:
            st.markdown("### Filters")
            parsed = st.session_state.get("last_parsed", {}) if st.session_state.get("last_query") else {}
            dest_default = None
            if parsed.get("destination_id"):
                dest_default = dest_map[parsed["destination_id"]]["name"]
            price_default = parsed.get("budget_max") or 8000
            rating_default = 3.5

            dest_options = ["Any"] + [d["name"] for d in destinations]
            dest_idx = 0
            if dest_default and dest_default in dest_options:
                dest_idx = dest_options.index(dest_default)
            dest_choice = st.selectbox("Destination", dest_options, index=dest_idx, key="htl_dest_main")
            price_range = st.slider("Price range (₹)", 500, 10000, (500, int(price_default) if price_default else 8000), key="htl_price_main")
            min_rating = st.slider("Min rating", 2.0, 5.0, float(rating_default), key="htl_rating_main")
            apply_h = st.button("Apply hotel filters", key="apply_hotels_main")
        with c2:
            st.markdown("### Results")
            if apply_h:
                res = [h for h in hotels if (dest_choice=="Any" or dest_map[h["destination_id"]]["name"]==dest_choice) and price_range[0] <= h["price"] <= price_range[1] and h["rating"]>=min_rating]
            else:
                parsed = st.session_state.get("last_parsed", {}) if st.session_state.get("last_query") else {}
                dflt_dest = None
                if parsed.get("destination_id"):
                    dflt_dest = dest_map[parsed["destination_id"]]["name"]
                budget = _normalize_max_price(parsed.get("budget_max")) or None
                res = hotels
                if dflt_dest:
                    res = [h for h in res if dest_map[h["destination_id"]]["name"]==dflt_dest]
                if budget:
                    res = [h for h in res if h["price"] <= budget]
                res = sorted(res, key=lambda x: score_item(x, active_profile, user_past_trips=user_map[active_user_id].get("past_trips", [])), reverse=True)

            if not res:
                st.info("No hotels found")
            else:
                card_htmls = []
                for i, hotel in enumerate(res[:results_limit]):
                    photo = make_stock_photo(hotel["id"])
                    base_card = hotel_card_html(photo, hotel)
                    key = f"{active_user_id}_{hotel['id']}"
                    if key not in st.session_state["explain_cache"]:
                        st.session_state["explain_cache"][key] = explain_with_gemini(hotel, active_profile, st.session_state.get("last_parsed", {}))
                    expl_html = f"<div class='hotel-explain'>{st.session_state['explain_cache'][key]}</div>"
                    card_htmls.append(base_card.replace("<!--EXPLAIN-->", expl_html))
                if card_htmls:
                    full_html = "<div class='card-row'>" + "".join(card_htmls) + "</div>"
                    components.html(full_html, height=380, scrolling=True)

                for hotel in res[:results_limit]:
                    if st.button(f"Book (mock) - {hotel['name']}", key=f"book_h_{hotel['id']}"):
                        log_event("book_hotel", active_user_id, hotel["id"])
                        st.success("Booked (mock)")

st.markdown("---")
st.markdown("**Notes**: this prototype uses generated mock data. Remote LLM is disabled by default to avoid quota issues; toggle `USE_GEMINI` in gemini_wrapper.py if you have a paid quota and want to re-enable LLM calls.")
