# pois_real.py
# Curated POI lists for 20 Indian cities (30 places each).
# Each POI includes: id, name, category, duration_mins,
# approx_travel_mins_from_hotel, approx_cost_from_hotel, travel_to (pairwise travel/time cost).
#
# Deterministic travel times & costs are generated using seeded RNG so values are reproducible.
# This file is mock/demo data (names are real/curated, travel times/costs are approximations).

import random
from typing import Dict, List

# curated 30 POIs per city (real or plausible place names)
POIS_BY_CITY = {
    "Mumbai": [
        "Gateway of India", "Chhatrapati Shivaji Maharaj Terminus", "Marine Drive",
        "Juhu Beach", "Girgaum Chowpatty", "Haji Ali Dargah", "Colaba Causeway",
        "Siddhivinayak Temple", "Bandra-Worli Sea Link (view)", "Phool Gully / Fashion Street",
        "Sanjay Gandhi National Park", "Elephanta Caves", "Jehangir Art Gallery",
        "Prince of Wales Museum (Chhatrapati Shivaji Maharaj Vastu Sangrahalaya)",
        "Banganga Tank", "Taraporewala Aquarium", "Global Vipassana Pagoda",
        "Bandra's Street Art", "Worli Sea Face", "Powai Lake",
        "Khotachiwadi (heritage village)", "Dharavi (guided microtour)", "Mount Mary Church",
        "Aksa Beach", "Mahalaxmi Dhobi Ghat (viewpoint)", "Film City (view/drive-by)",
        "Versova Beach", "Mani Bhavan Gandhi Museum", "Arthur Road Jail (historic view)",
        "Bhau Daji Lad Museum"
    ],
    "Delhi": [
        "Red Fort", "Qutub Minar", "India Gate", "Humayun's Tomb", "Lotus Temple",
        "Akshardham Temple", "Jama Masjid", "Connaught Place (CP)", "Chandni Chowk",
        "Raj Ghat", "National Museum", "Lodhi Garden", "Hauz Khas Village",
        "Dilli Haat", "Purana Qila", "Bangla Sahib Gurudwara", "India Habitat Centre",
        "Gandhi Smriti", "Nizamuddin Dargah", "Shankar's International Dolls Museum",
        "Khan Market", "National Rail Museum", "Garden of Five Senses",
        "Select Citywalk (Saket)", "Majnu Ka Tilla", "Mehrauli Archaeological Park",
        "Agrasen ki Baoli", "Sunder Nursery", "Tomb of Itimad-ud-Daulah (replica)",
        "Hastkala (craft bazaar)"
    ],
    "Bengaluru": [
        "Lalbagh Botanical Garden", "Bangalore Palace", "Cubbon Park", "UB City Mall",
        "Tipu Sultan's Summer Palace", "Bannerghatta National Park", "Commercial Street",
        "Vidhana Soudha (view)", "ISKCON Temple", "Nandi Hills (nearby day trip)",
        "Wonderla Amusement Park", "HAL Aerospace Museum", "M.G. Road", "Brigade Road",
        "Ulsoor Lake", "Tipu's Drop viewpoint", "Art Galleries (Venkatappa Art Gallery)",
        "Phoenix Marketcity (Whitefield)", "Indiranagar nightlife strip",
        "KR Market (city market)", "Nrityagram (dance village)", "Ranganathittu-style park (birding)",
        "Forum Mall", "St. Mark's Cathedral", "Jawaharlal Nehru Planetarium",
        "Freedom Park", "Sankey Tank", "Dodda Ganesha Temple", "Chunchi Falls (day trip)",
        "Turahalli Forest"
    ],
    "Chennai": [
        "Marina Beach", "Kapaleeshwarar Temple", "Fort St. George", "San Thome Basilica",
        "Government Museum (Egmore)", "Elliot's Beach (Besant Nagar)", "Valluvar Kottam",
        "Mahabalipuram (nearby)", "Dakshina Chitra (culture museum)", "Chennai Rail Museum",
        "Guindy National Park", "VGP Universal Kingdom", "Anna Centenary Library",
        "Pondy Bazaar (shopping)", "Express Avenue Mall", "Semmozhi Poonga", "Sri Parthasarathy Temple",
        "Theosophical Society (Adyar)", "Mylapore walk", "Covelong / Kovalam (nearby)",
        "Royapuram Fishing Harbour", "Govt. Museum Amphitheatre", "Besant Nagar promenade",
        "Arignar Anna Zoological Park (Vandalur)", "Cholamandal Artists Village", "Besant Nagar market",
        "Marundeeswarar Temple", "Kasimedu Fishing Harbour", "Phoenix Marketcity (Velachery)", "Heritage walks (George Town)"
    ],
    "Kolkata": [
        "Victoria Memorial", "Howrah Bridge", "Dakshineswar Kali Temple", "Kalighat Temple",
        "Indian Museum", "Park Street", "Eco Park (New Town)", "Science City",
        "Prinsep Ghat", "Marble Palace", "St. Paul's Cathedral", "New Market (Hogg Market)",
        "Kumartuli (potter quarter)", "Nakhoda Mosque", "Rabindra Sarobar", "Alipore Zoo",
        "Mother House (Mother Teresa)", "Salt Lake Stadium (view)", "College Street Book Market",
        "Birla Planetarium", "South Park Street Cemetery", "Nicco Park (amusement)", "Belur Math",
        "Qawwali/heritage alleys", "Kolkata Tram rides", "Gateway of Kolkata (Prinsep area)",
        "Town Hall view", "Burrabazar (market)", "Jorasanko Thakur Bari", "Barisha Chandi Temple"
    ],
    "Goa": [
        "Baga Beach", "Calangute Beach", "Anjuna Beach", "Vagator Beach", "Palolem Beach",
        "Colva Beach", "Fort Aguada", "Basilica of Bom Jesus", "Chapora Fort", "Dudhsagar Falls",
        "Old Goa Churches (Heritage)", "Anjuna Flea Market", "Mapusa Market", "Arpora Saturday Night Market",
        "Sinquerim Beach", "Cabo de Rama Fort", "Morjim Beach", "Ashwem Beach", "Mandrem Beach",
        "Divar Island (ferry)", "Spice Plantations (Ponda)", "Salim Ali Bird Sanctuary",
        "Mosques & Temples of Ponda", "Fontainhas Latin Quarter (Panaji)", "River cruises on Mandovi",
        "Ancestral house museums", "Sernabatim/Betul lighthouse", "Reis Magos Fort", "Bogmalo Beach", "Butterfly Conservatory"
    ],
    "Jaipur": [
        "Amer Fort", "Hawa Mahal", "City Palace", "Jantar Mantar", "Nahargarh Fort",
        "Jaigarh Fort", "Albert Hall Museum", "Jal Mahal", "Birla Mandir", "Markets of Johari & Bapu",
        "Galta Ji (Monkey Temple)", "Chokhi Dhani (cultural village)", "Ram Niwas Garden",
        "Gaitore Cenotaphs", "Sisodia Rani Garden", "Elefantastic (elephant sanctuary tours)",
        "Central Park (Jaipur)", "Handloom & handicraft emporiums", "Nahargarh biological park",
        "Panna Meena Ka Kund", "Bagru & Sanganer (print villages)", "Kanak Vrindavan",
        "Museum of Indology", "Jawahar Kala Kendra", "Amber Light & sound show", "Raja Bhoj Art House",
        "City heritage walks", "Vintage car museum", "Rambagh Palace view"
    ],
    "Udaipur": [
        "City Palace Udaipur", "Lake Pichola (boat)", "Jag Mandir", "Jagdish Temple",
        "Saheliyon ki Bari", "Bagore Ki Haveli", "Fateh Sagar Lake", "Monsoon Palace",
        "Vintage Car Museum", "Gulab Bagh", "Shilpgram (craft village)", "Badi Lake",
        "Ahar Cenotaphs", "Ambrai Ghat", "Rang Sagar", "Doodh Talai", "Jag Mandir Garden",
        "Cottage industry tours", "Local markets (Hathi Pol)", "Sajjangarh Fort",
        "Vintage Ghat views", "Udaipur heritage walk", "Crystal Gallery", "Fateh Sagar Ropeway",
        "Suryamukh Point", "Cultural folk dance shows", "Eklingji temple", "Kumbhalgarh day trip", "Local boat concerts", "Food street (Tripolia Bazaar)"
    ],
    "Agra": [
        "Taj Mahal", "Agra Fort", "Mehtab Bagh", "Itmad-ud-Daulah (Baby Taj)", "Fatehpur Sikri (nearby)",
        "Akbar's Tomb (Sikandra)", "Anguri Bagh", "Shah Jahan Park", "Keetham/Sur Sarovar Bird Sanctuary",
        "Kinari Bazaar", "Marble workshops", "Taj Museum", "Mankameshwar Temple", "Chini ka Rauza",
        "Rang Mahal ruins", "Local produce markets", "Jama Masjid Agra", "Mughal-era walks",
        "Heritage hotels (lobby experiences)", "Shopping for marble inlay", "Kalakriti Cultural & Convention Centre",
        "Day trip to Bharatpur (Keoladeo)", "Riverfront walks on Yamuna", "Food street (Sadar)",
        "Ram Bagh", "Historic step wells", "Agra Cantonment walking areas", "Local art museums", "Tomb of Akbar the Great", "Heritage photography spots"
    ],
    "Varanasi": [
        "Dashashwamedh Ghat", "Assi Ghat", "Kashi Vishwanath Temple", "Manikarnika Ghat",
        "Ramnagar Fort", "Banaras Hindu University campus", "Sarnath (nearby)", "Durga Temple",
        "Bharat Kala Bhavan", "Benares Gharana music centers", "Ghats boat ride at dawn",
        "Tulsi Manas Mandir", "Bharat Mata Temple", "Chet Singh Ghat", "Alamgir Mosque",
        "Ramnagar Museum", "Local silk weaving workshops", "Kedar Ghat", "Harishchandra Ghat",
        "Vishalakshi Temple", "Tulsi Ghat", "Music & classical concert venues", "Candle-making markets",
        "Sankat Mochan Hanuman Temple", "Banaras textile markets", "Laxmi Vilas Palace (view)",
        "Ravidas Temple", "Food walk (sweet shops)", "Boat ghats around the island", "Banaras Sculpture Park"
    ],
    "Amritsar": [
        "Golden Temple (Harmandir Sahib)", "Jallianwala Bagh", "Wagah Border ceremony", "Partition Museum",
        "Durgiana Temple", "Hall Bazaar", "Akal Takht", "Pul Kanjari (nearby)", "Gobindgarh Fort",
        "Rambagh Gardens", "Heritage walk old city", "Local Punjabi food streets", "Rati Ram Bazaar",
        "Maharaja Ranjit Singh Museum", "Company Bagh", "Durgiana complex markets", "Atwal Hospital area (heritage)",
        "Khalsa College (view)", "Central Amritsar markets", "Bhandari bridge viewpoints",
        "Punjabi rural craft centers", "Saragarhi memorials", "Old city's step wells", "Cultural performances",
        "Attari Bazaar", "Gurudwara Mata Kaulan", "Local sweet shops", "Peaceful ghats", "Village tours outside city", "Amritsar Art Gallery"
    ],
    "Lucknow": [
        "Bara Imambara", "Rumi Darwaza", "Chota Imambara", "Hazratganj", "La Martiniere Lucknow",
        "Ambedkar Memorial Park", "British Residency", "Kathak performance venues", "Aminabad market",
        "Dr. B.R. Ambedkar Park", "Gomti Riverfront", "Kaiserbagh Palace remains", "Janeshwar Mishra Park",
        "Satkhanda", "Lucknow Zoo", "Residency Museum", "Ganjingh", "Local kebab trails (Tunday Kababi area)",
        "State Museum Lucknow", "Lucknow Shehnai & classical music spots", "Sheesh Mahal", "British-era churches",
        "Local Chikankari craft centers", "Archaeological sites", "Cultural festivals venues", "Picnic spots near Gomti", "Shrines & temples walks", "Coffee house heritage", "Heritage photo spots", "Vintage architecture street"
    ],
    "Shimla": [
        "The Ridge", "Mall Road", "Christ Church", "Jakhu Temple", "Kufri (nearby)",
        "Indian Institute of Advanced Study", "Scandal Point", "Mall Road shops", "Tara Devi Temple", "Shimla State Museum",
        "Annandale", "Chadwick Falls", "Summer Hill", "Viceregal Lodge (now IIAS)", "Gaiety Theatre",
        "Hatu Peak daytrip", "Naldehra (golf & views)", "Toy Train (Kalka–Shimla) station", "Shimla Heritage walk",
        "Boileauganj market", "Shimla Observatory", "Kali Bari Temple Shimla", "Kalka viewpoint", "Basholi artspace",
        "Christ Church lawns", "Social clubs heritage", "Local Himalayan food streets", "Timber trails (nearby)", "Orchard walks", "Birdwatching spots"
    ],
    "Manali": [
        "Hadimba Temple", "Solang Valley", "Rohtang Pass (seasonal)", "Manu Temple", "Old Manali cafes",
        "Vashisht hot springs", "Mall Road Manali", "Jogini Falls", "Naggar Castle (nearby)", "Beas River views",
        "Van Vihar", "Tibetan monasteries", "Bhrigu Lake trek start (nearby)", "Sethan village", "Paragliding at Solang",
        "Manali Gompa", "Art galleries & craft bazaar", "Local markets", "River rafting centers (Beas)",
        "Adventure parks", "Day trips to Kullu", "Hanogi Mata Temple", "Nature walks", "Wildlife park", "Picnic spots", "Campsites", "Old bridges", "Local handicraft shops", "Himachali cuisine places", "Photogenic viewpoints"
    ],
    "Srinagar": [
        "Dal Lake (houseboats)", "Shankaracharya Temple", "Mughal Gardens (Shalimar Bagh)", "Nishat Bagh",
        "Hazratbal Shrine", "Pari Mahal", "Old City markets (Lal Chowk)", "Floating vegetable market", "Shankaracharya Hill",
        "Char Chinar (on island)", "Nigeen Lake", "Tulip Garden (seasonal)", "Hari Parbat Fort",
        "Wular Lake (day trip)", "Market of Lal Chowk", "Local Kashmiri handicraft bazaar", "Sufi music venues",
        "Paper mâché workshops", "Kashmiri cuisine eateries", "Shikara rides", "Botanical corners", "Gundpora walks",
        "Khanqah-e-Moula", "Aali Kadal area", "Old wooden mosques", "Handloom centers", "Gulmarg day trip (nearby)", "Pahalgam day trip", "Local gardens", "Gandola/ropeway viewpoints"
    ],
    "Leh": [
        "Leh Palace", "Shanti Stupa", "Hall of Fame (army museum)", "Spituk Monastery", "Thiksey Monastery",
        "Hemis Monastery (nearby)", "Nubra Valley (day trips)", "Pangong Tso (day trip)", "Khardung La (drive)",
        "Local Leh market (Tibetan market)", "Shey Palace", "Magnetic Hill", "Sangam (Indus-Zanskar confluence)",
        "Monastery festivals", "Sham Valley hike", "Phyang Monastery", "Leh bazaar foodstalls", "Pangong viewpoint",
        "Chadar trail info point (seasonal)", "Leh viewpoint at Stok", "Yak farms (photo ops)", "Local craft shops",
        "Alchi Day trip", "Likir Monastery", "Fotedar Museum (small)", "Tsomoriri (long day trip)", "Horse riding spots", "High altitude gardens", "Riverside picnic spots", "Sky-view points"
    ],
    "Munnar": [
        "Tea Gardens (rolling hills)", "Eravikulam National Park", "Mattupetty Dam", "Top Station viewpoint",
        "Kundala Lake", "Anamudi Peak (views)", "Tea Museum (Kanan Devan)", "Attukal Waterfalls", "Chinnar Wildlife Sanctuary (nearby)",
        "Echo Point", "Blossom Park", "Devikulam Lake", "Pothamedu Viewpoint", "Nyayamakad Waterfalls", "Lockhart Gap",
        "Kolukkumalai (tea estate drive)", "Local spice plantations", "Kundala Dam pedal boating", "Chithirapuram", "Hydel Park",
        "Rose Garden", "Local craft markets", "Munnar town walk", "St. Thomas Church", "Mattupetty boat rides", "Shola forests", "Birdwatching points", "Eco trails", "Tea tasting centers", "Camping spots"
    ],
    "Kochi": [
        "Fort Kochi (historic area)", "Chinese Fishing Nets", "Mattancherry Palace", "Jew Town & Synagogue",
        "St. Francis Church", "Marine Drive Kochi", "Kerala Folklore Museum", "Paradesi Synagogue", "Hill Palace Museum",
        "Cherai Beach", "Ernakulam Market", "Kochi Biennale venues", "Muziris heritage walk", "Willington Island",
        "Bolgatty Palace", "Kerala Kathakali performances", "Kerala cuisine food streets", "Vypin Island", "Backwater boat rides",
        "Vypeen lighthouse", "Local art galleries", "Fort Kochi street art", "Kumbalangi (fishing village)", "Santa Cruz Basilica",
        "Marine aquarium", "Shopping at Lulu Mall", "Chittoor temple area", "Local coir workshops", "Folklore festivals", "Dutch Cemetery"
    ],
    "Pune": [
        "Shaniwar Wada", "Aga Khan Palace", "Dagdusheth Ganapati Temple", "Osho Ashram (Pune) view", "Sinhagad Fort",
        "Pataleshwar Cave Temple", "Koregaon Park (shops & cafes)", "Bund Garden", "Raja Dinkar Kelkar Museum",
        "Parvati Hill & Temple", "Pune Okayama Friendship Garden", "Pu La Deshpande Garden", "Fergusson College (walk)",
        "Pune University area", "Pune street food lanes (Jangli Maharaj Road)", "Phoenix Marketcity Pune",
        "Dagdu Seth Ganpati area", "Khadakwasla Dam (nearby)", "Mulshi lake (day trip)", "Pune Okayama Garden",
        "National War Memorial Southern Command", "Laxmi Road markets", "Shinde Chhatri", "Pune heritage walks",
        "Studio visits & arts hubs", "Local classical music venues", "Shopping arcades", "Baner Pashan hills", "IT parks visit spots", "Film city tours"
    ],
    "Hyderabad": [
        "Charminar", "Golconda Fort", "Hussain Sagar Lake", "Ramoji Film City", "Chowmahalla Palace",
        "Birla Mandir (Hyderabad)", "Salar Jung Museum", "Qutb Shahi Tombs", "Laad Bazaar (Choodi bazaar)",
        "Nehru Zoological Park", "Shilparamam arts village", "Snow World", "Osmania University (heritage)", "Paigah Tombs",
        "Tank Bund", "Falaknuma Palace (view)", "Mecca Masjid", "Hitech City (drive-by)", "Bikanervala food streets",
        "Lumbini Park", "NTR Gardens", "Hussain Sagar boating", "Local biryani lanes", "Jawaharlal Nehru Technological Park view",
        "ISKCON Hyderabad", "Golconda Light show", "Salar Jung art walks", "Qutub Shahi heritage walk", "Local craft bazaars"
    ]
}

# ensure every city above has 30 names; if less, we'll pad with generated descriptive names later

DEFAULT_CATEGORIES = ["sightseeing","historic","temple","museum","market","nature","beach","viewpoint","park","cultural"]

def _ensure_30(names_list, city, seed_base):
    """Ensure list of length 30 by appending sensible variations if needed."""
    out = list(names_list)
    idx = 1
    while len(out) < 30:
        # append city + descriptor
        candidate = f"{city} Landmark {idx}"
        if candidate not in out:
            out.append(candidate)
        idx += 1
    return out[:30]

def get_pois_map(destinations: List[Dict], seed: int = 42) -> Dict[str, List[Dict]]:
    """
    Build POI objects for each destination in the destinations list.
    destinations: list of dicts with keys 'id' and 'name'
    returns: { destination_id: [poi_dict,...] }
    """
    pois_map = {}
    for di, dest in enumerate(destinations):
        city_name = dest.get("name", f"City{di}")
        dest_id = dest.get("id", f"dest_{di}")
        curated = POIS_BY_CITY.get(city_name, [])
        curated30 = _ensure_30(curated, city_name, seed + di)
        rng_base = seed + di * 101

        poi_list = []
        for i, pname in enumerate(curated30):
            rng = random.Random(rng_base + i * 13)
            # choose a category heuristically from name or default
            category = None
            lname = pname.lower()
            if any(k in lname for k in ["temple","mandir","gurudwara","mosque"]):
                category = "temple"
            elif any(k in lname for k in ["museum","gallery","palace","fort"]):
                category = "historic"
            elif any(k in lname for k in ["beach","lake","river","falls"]):
                category = "nature"
            elif any(k in lname for k in ["market","bazaar","mall","street"]):
                category = "market"
            elif any(k in lname for k in ["garden","park","botanic"]):
                category = "park"
            else:
                category = rng.choice(DEFAULT_CATEGORIES)

            duration = rng.choice([45, 60, 75, 90, 120])
            mins_from_hotel = rng.choice([8,10,12,15,18,20,25,30,35,40])
            cost_from_hotel = int(max(15, mins_from_hotel * rng.uniform(2.0, 5.5)))

            poi_id = f"{dest_id}_poi_{i}"
            poi = {
                "id": poi_id,
                "name": pname,
                "category": category,
                "duration_mins": duration,
                "approx_travel_mins_from_hotel": mins_from_hotel,
                "approx_cost_from_hotel": cost_from_hotel,
                "travel_to": {}
            }
            poi_list.append(poi)

        # fill pairwise travel_to (symmetric-ish)
        for i, p in enumerate(poi_list):
            for j, q in enumerate(poi_list):
                if i == j:
                    p["travel_to"][q["id"]] = {"mins": 0, "cost": 0}
                    continue
                rng = random.Random(rng_base + i * 37 + j * 17)
                mins = int(rng.uniform(5, 60))
                cost = int(max(10, mins * rng.uniform(1.2, 4.0)))
                p["travel_to"][q["id"]] = {"mins": mins, "cost": cost}

        pois_map[dest_id] = poi_list
    return pois_map

# Quick demo when run directly
if __name__ == "__main__":
    # example destinations similar to app's default list
    sample_dest = [{"id":"dest_0","name":"Mumbai"},{"id":"dest_4","name":"Kolkata"},{"id":"dest_12","name":"Shimla"}]
    pois = get_pois_map(sample_dest, seed=999)
    for k,v in pois.items():
        print(k, len(v), v[0])
