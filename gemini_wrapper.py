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

# try to import requests for optional remote calls; not required for local fallback
try:
    import requests
except Exception:
    requests = None

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

def _parse_budget_string_local(s: str) -> Optional[int]:
    if s is None:
        return None
    s = str(s).strip().lower()
    s = s.replace("₹", "").replace("rs.", "").replace("rs", "").replace("inr", "").replace("$", "").replace("usd", "")
    s = s.strip()
    m = re.match(r"^([0-9,\.]+)\s*([km]?)$", s)
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

def _parse_search_local(query: str) -> Dict[str, Any]:
    """Simple local parser to extract destination-like tokens, tags and budget."""
    q = (query or "").lower()
    out = {
        "destination_id": None,
        "destination": None,
        "origin": None,
        "tags": [],
        "budget_max": None,
        "trip_type": None,
        "nights": None,
        "max_stops": None
    }
    keywords = ["beach","adventure","family","romantic","nightlife","budget","luxury","trek","weekend","relax","hiking","culture","spiritual"]
    for w in keywords:
        if w in q and w not in out["tags"]:
            out["tags"].append(w)
    # numbers like 'under 12000' / 'under 12k'
    m = re.search(r"(?:under|below|upto|up to|less than)\s*([0-9,\.kKmM]+)", q)
    if m:
        val = m.group(1)
        parsed = _parse_budget_string_local(val)
        out["budget_max"] = parsed
    # nights
    m2 = re.search(r"(\d+)\s*(?:nights|night|days|day)", q)
    if m2:
        try:
            out["nights"] = int(m2.group(1))
        except:
            out["nights"] = None
    # max stops
    m3 = re.search(r"max(?:imum)?\s*stops?\s*(?:[:=]?\s*)?([0-9])", q)
    if m3:
        try:
            out["max_stops"] = int(m3.group(1))
        except:
            out["max_stops"] = None
    # simple city mapping (lowercase tokens)
    city_map = {
        "goa":"dest_5","mumbai":"dest_0","kolkata":"dest_4","leh":"dest_15","shimla":"dest_12",
        "delhi":"dest_1","bangalore":"dest_2","bengaluru":"dest_2","chennai":"dest_3","jaipur":"dest_6",
        "manali":"dest_13","agra":"dest_8","varanasi":"dest_9","hyderabad":"dest_19","pune":"dest_18"
    }
    for k,v in city_map.items():
        if re.search(r'\b' + re.escape(k) + r'\b', q):
            out["destination_id"] = v
            out["destination"] = k.title()
            break
    # detect origin using "from"
    mfrom = re.search(r'\bfrom\s+([a-zA-Z ]+)', q)
    if mfrom:
        candidate = mfrom.group(1).strip().split()[0]
        candidate = candidate.lower()
        # try map
        if candidate in city_map:
            out["origin"] = candidate.title()
        else:
            out["origin"] = candidate.title()
    # detect explicit "to <city>" if present and origin wasn't set from "from"
    mto = re.search(r'\bto\s+([a-zA-Z ]+)', q)
    if mto:
        candidate = mto.group(1).strip().split()[0]
        candidate = candidate.lower()
        if candidate in city_map:
            out["destination_id"] = city_map[candidate]
            out["destination"] = candidate.title()
        else:
            if not out["destination"]:
                out["destination"] = candidate.title()
    if "train" in q: out["trip_type"] = "trains"
    if "flight" in q or "air" in q: out["trip_type"] = "flights"
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

# Helper to robustly extract the first JSON object from a string
def _safe_extract_json(s: str) -> Optional[Dict[str,Any]]:
    if not s:
        return None
    # try to find the first { ... } block
    # handle nested braces by balancing
    start = s.find('{')
    if start == -1:
        return None
    depth = 0
    end = None
    for i in range(start, len(s)):
        if s[i] == '{':
            depth += 1
        elif s[i] == '}':
            depth -= 1
            if depth == 0:
                end = i
                break
    if end is None:
        # fallback: try regex crude match
        m = re.search(r'\{.*\}', s, flags=re.DOTALL)
        if not m:
            return None
        candidate = m.group(0)
    else:
        candidate = s[start:end+1]
    try:
        return json.loads(candidate)
    except Exception:
        # try replacing single quotes (risky) and python-style None/True/False -> null/true/false
        cand = candidate.replace("'", '"')
        cand = re.sub(r'\bNone\b', 'null', cand)
        cand = re.sub(r'\bTrue\b', 'true', cand)
        cand = re.sub(r'\bFalse\b', 'false', cand)
        try:
            return json.loads(cand)
        except Exception:
            return None

def _call_remote_parse(query: str, user_profile: Optional[Dict[str,Any]] = None) -> Optional[str]:
    """
    If requests is available and USE_GEMINI True, attempt a remote call. Returns raw text response or None.
    This is a minimal generic example for an OpenAI/Groq-compatible chat endpoint. Adapt to your provider.
    """
    if not requests:
        return None
    if not USE_GEMINI:
        return None
    # construct a prompt instructing strict JSON output
    profile_json = json.dumps(user_profile or {}, ensure_ascii=False)
    prompt = f"""
You are a travel search parser. Given the query and the user's profile, return STRICT JSON with only the fields:
destination, destination_id, origin, trip_type, nights, budget_max, tags, max_stops.

user_profile: {profile_json}
text: \"\"\"{query}\"\"\"

Return ONLY valid JSON (no explanation). Use null for missing values.
"""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are a JSON parser that must return only JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
        "max_tokens": 400
    }
    attempts = 0
    while attempts <= _MAX_RETRIES:
        try:
            resp = requests.post(GENERATE_URL, headers=headers, json=payload, timeout=DEFAULT_TIMEOUT)
            if resp.status_code != 200:
                attempts += 1
                time.sleep(_RETRY_BACKOFF * attempts)
                continue
            j = resp.json()
            # try to extract text depending on response shape
            # common OpenAI-like shape: choices[0].message.content
            text_out = None
            if isinstance(j, dict):
                if "choices" in j and isinstance(j["choices"], list) and len(j["choices"])>0:
                    ch = j["choices"][0]
                    if isinstance(ch, dict):
                        if "message" in ch and isinstance(ch["message"], dict):
                            text_out = ch["message"].get("content")
                        else:
                            text_out = ch.get("text") or ch.get("message")
                elif "text" in j:
                    text_out = j.get("text")
                else:
                    # some providers place content differently; try to stringify
                    text_out = json.dumps(j)
            else:
                text_out = str(j)
            return text_out
        except Exception:
            attempts += 1
            time.sleep(_RETRY_BACKOFF * attempts)
    return None

def parse_search_with_gemini(query: str, user_profile: Optional[Dict[str,Any]] = None) -> Dict[str, Any]:
    """
    Parse free-text query into JSON signals. If USE_GEMINI True and remote call succeeds,
    parse the returned JSON. Otherwise fall back to the local parser.
    Returns a dict with keys similar to the local parser.
    """
    try:
        # attempt remote parse if enabled
        if USE_GEMINI:
            text_out = _call_remote_parse(query, user_profile=user_profile)
            if text_out:
                parsed_json = _safe_extract_json(text_out)
                if parsed_json:
                    # sanitize and normalize keys we expect
                    allowed = {"destination","destination_id","origin","trip_type","nights","budget_max","tags","max_stops"}
                    parsed = {k: parsed_json.get(k, None) for k in allowed}
                    # normalize types
                    if isinstance(parsed.get("budget_max"), str):
                        parsed["budget_max"] = _parse_budget_string_local(parsed["budget_max"])
                    if parsed.get("nights") is not None:
                        try:
                            parsed["nights"] = int(parsed["nights"])
                        except:
                            parsed["nights"] = None
                    if parsed.get("max_stops") is not None:
                        try:
                            parsed["max_stops"] = int(parsed["max_stops"])
                        except:
                            parsed["max_stops"] = None
                    if parsed.get("tags") is None:
                        parsed["tags"] = []
                    elif isinstance(parsed.get("tags"), str):
                        parsed["tags"] = [t.strip() for t in parsed["tags"].split(",") if t.strip()]
                    # if destination present but no destination_id, leave as-is (app layer will try to resolve)
                    return parsed
        # fallback to local parser
        return _parse_search_local(query or "")
    except Exception:
        try:
            traceback.print_exc()
        except:
            pass
        return _parse_search_local(query or "")

def choose_hotel_with_gemini(candidates: List[Dict[str,Any]], user_profile: Dict[str,Any], user_past_trips: Optional[List[Dict[str,Any]]] = None, reason_max_tokens: int = 60) -> Optional[Dict[str,Any]]:
    """
    Choose a single best hotel from candidates, returning {"hotel_id":..., "reason":...}
    Uses a local heuristic: tries to match budget and interests. If remote LLM is enabled
    you can extend this function to call the LLM for a human-readable reason.
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
