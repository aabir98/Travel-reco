# gemini_wrapper.py
# Minimal wrapper providing local fallbacks. Remote LLM (Groq/Gemini) is disabled by default
# to avoid quota problems for student POCs. Set USE_GEMINI=True and configure GROQ_API_KEY
# if you want to use a remote provider.

import json
import random
import re
import time
import traceback
from typing import Any, Dict, Optional, List

# ---------------- CONFIG ----------------
# If you want to enable a remote LLM provider (Groq/Gemini), set USE_GEMINI=True
# and populate GROQ_API_KEY and GENERATE_URL. For POCs and student projects, keep False.
USE_GEMINI = False

# If you set USE_GEMINI True, configure below (not used when USE_GEMINI=False)
GROQ_API_KEY = "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"  # set your key if enabling remote calls (keep private)
GROQ_MODEL = "llama-3.1-8b-instant"
GENERATE_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_TIMEOUT = 12

# small retry/backoff config (used only if USE_GEMINI True)
_MAX_RETRIES = 2
_RETRY_BACKOFF = 1.25

# ----------------------------------------

def _fmt_price_local(x):
    try:
        return f"₹{int(x):,}"
    except Exception:
        try:
            return f"₹{float(x):,}"
        except Exception:
            return str(x)

def _explain_fallback(item: Dict[str, Any]) -> str:
    """Short one-line explanation fallback used when remote LLM is disabled or fails."""
    try:
        name = item.get("name", "This option")
        rating = item.get("rating")
        price = item.get("price")
        tags = item.get("tags", []) or []
        parts = []
        if rating:
            parts.append(f"{rating}★")
        if price:
            parts.append(_fmt_price_local(price))
        if tags:
            parts.append(", ".join(tags[:2]))
        tail = " • ".join(parts) if parts else ""
        if tail:
            return f"{name} — {tail}"
        return f"{name} — Good match for your profile."
    except Exception:
        return "A recommended option that fits your profile."

def _parse_search_local(query: str) -> Dict[str, Any]:
    """Simple local parser to extract destination-like tokens, tags and budget."""
    q = (query or "").lower()
    out = {"destination_id": None, "tags": [], "budget_max": None, "trip_type": None, "nights": None}
    keywords = ["beach","adventure","family","romantic","nightlife","budget","luxury","trek","weekend","relax","hiking","culture","spiritual"]
    for w in keywords:
        if w in q and w not in out["tags"]:
            out["tags"].append(w)
    # numbers like 'under 12000' / 'under 12k'
    m = re.search(r"(?:under|below|upto|up to|less than)\s*([0-9,\.kKmM]+)", q)
    if m:
        val = m.group(1)
        # normalize k/m
        try:
            if val.endswith("k"):
                out["budget_max"] = int(float(val[:-1].replace(",","")) * 1000)
            elif val.endswith("m"):
                out["budget_max"] = int(float(val[:-1].replace(",","")) * 1000000)
            else:
                out["budget_max"] = int(float(val.replace(",","")))
        except:
            out["budget_max"] = None
    # nights
    m2 = re.search(r"(\d+)\s*(?:nights|night|days|day)", q)
    if m2:
        try:
            out["nights"] = int(m2.group(1))
        except:
            out["nights"] = None
    # simple city mapping (lowercase tokens)
    city_map = {
        "goa":"dest_5","mumbai":"dest_0","kolkata":"dest_4","leh":"dest_15","shimla":"dest_12",
        "delhi":"dest_1","bangalore":"dest_2","bengaluru":"dest_2","chennai":"dest_3","jaipur":"dest_6",
        "manali":"dest_13","agra":"dest_8","varanasi":"dest_9","hyderabad":"dest_19","pune":"dest_18"
    }
    for k,v in city_map.items():
        if k in q:
            out["destination_id"] = v
            break
    if "train" in q: out["trip_type"] = "train"
    if "flight" in q: out["trip_type"] = "flight"
    if "itiner" in q or "plan" in q or "itinerary" in q: out["trip_type"] = out.get("trip_type") or "itinerary"
    return out

# Public API functions (keeps same names used by app.py)

def explain_with_gemini(item: Dict[str, Any], user_profile: Optional[Dict[str,Any]] = None, parsed_search: Optional[Dict[str,Any]] = None) -> str:
    """
    Return a short explanation string for UI.
    By default this uses the local fallback to avoid remote quota issues.
    """
    # If you want to use a remote provider, implement the remote call here conditioned on USE_GEMINI.
    # For now, we use local deterministic fallback.
    return _explain_fallback(item)

def parse_search_with_gemini(query: str) -> Dict[str, Any]:
    """
    Parse free-text query into JSON signals. Uses a local parser in this POC to avoid quota problems.
    """
    # If USE_GEMINI True, you could attempt a remote parse and fall back to local if that fails.
    return _parse_search_local(query)

def choose_hotel_with_gemini(candidates: List[Dict[str,Any]], user_profile: Dict[str,Any], user_past_trips: Optional[List[Dict[str,Any]]] = None, reason_max_tokens: int = 60) -> Optional[Dict[str,Any]]:
    """
    Choose a single best hotel from candidates, returning {"hotel_id":..., "reason":...}
    Uses a local heuristic: tries to match budget and interests.
    """
    try:
        if not candidates:
            return None
        # if user has budget range, prefer hotels within that range
        budget = user_profile.get("budget", {}) if user_profile else {}
        bmin = budget.get("min", 0)
        bmax = budget.get("max", None)

        # simple scoring: tag overlap + closeness to budget + rating
        def local_score(h):
            score = 0.0
            # tag overlap with user interests
            interests = user_profile.get("interests", []) if user_profile else []
            if interests:
                score += sum(1 for t in h.get("tags", []) if t in interests) * 1.5
            # rating
            score += (h.get("rating", 3.0) - 2.0) * 0.5
            # budget closeness
            price = h.get("price", 0)
            if bmax:
                # prefer <= bmax strongly
                if price <= bmax:
                    score += 1.2
                    score += max(0, 0.5 - (abs(price - (bmax))/max(1,bmax)))
                else:
                    score -= 0.6 * ((price - bmax) / max(1, bmax))
            return score

        # if candidates contain items with 'score' field, use that first
        if any("score" in c for c in candidates):
            candidates = sorted(candidates, key=lambda x: x.get("score",0), reverse=True)
            best = candidates[0]
            return {"hotel_id": best.get("id"), "reason": f"Top scored hotel ({best.get('rating','?')}★, { _fmt_price_local(best.get('price',0)) })"}

        best = max(candidates, key=local_score)
        reason = f"Recommended: {best.get('rating','?')}★ • { _fmt_price_local(best.get('price',0)) }"
        return {"hotel_id": best.get("id"), "reason": reason}
    except Exception as e:
        try:
            traceback.print_exc()
        except:
            pass
        return None
