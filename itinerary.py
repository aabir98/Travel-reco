# itinerary.py
"""
Generates deterministic itineraries from POIs (no hallucinations).
Returns days with lists of POI dicts (from pois_map) assigned to morning/afternoon/evening.
"""

from datetime import datetime, timedelta
import random

def generate_itinerary(destination_id, start_date_str=None, nights=2, interests=None, pace="normal", pois_map=None):
    if not start_date_str:
        start_date = datetime.today().date()
    else:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except Exception:
            start_date = datetime.today().date()

    num_days = max(1, nights + 1)
    pois = pois_map.get(destination_id, []) if pois_map else []
    # assign score by interest overlap
    def poi_score(p):
        score = 0
        if interests:
            for t in interests:
                if t in (p.get("category","") or "") or t in (p.get("name","").lower() or ""):
                    score += 1
        score += random.Random(p.get("id", "")).random() * 0.1
        return score

    sorted_pois = sorted(pois, key=poi_score, reverse=True)
    # decide slots per day
    slots_by_pace = {"relaxed":2, "normal":3, "packed":4}
    slots = slots_by_pace.get(pace, 3)
    days=[]
    idx=0
    for d in range(num_days):
        date = start_date + timedelta(days=d)
        day_pois = sorted_pois[idx: idx+slots]
        idx += slots
        morning = day_pois[0:1]
        afternoon = day_pois[1:2] if len(day_pois)>1 else []
        evening = day_pois[2:3] if len(day_pois)>2 else []
        days.append({
            "date": date.isoformat(),
            "morning": [p for p in morning],
            "afternoon": [p for p in afternoon],
            "evening": [p for p in evening]
        })
    return {"destination_id": destination_id, "start_date": start_date.isoformat(), "nights": nights, "days": days}
