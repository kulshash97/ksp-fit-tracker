import os
import io
import re
import json
import base64
import urllib.request
from datetime import date
from PIL import Image, ImageOps
from fpdf import FPDF
import streamlit as st

st.set_page_config(
    page_title="KSP Fitness OS",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp {
        background: radial-gradient(circle at top right, #111927 0%, #0b0f17 55%, #080b10 100%);
        color: #e6edf3;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .hero-banner {
        background: linear-gradient(120deg, rgba(22, 27, 34, 0.95) 0%, rgba(17, 29, 48, 0.92) 100%);
        border: 1px solid #2b3544;
        border-left: 4px solid #38bdf8;
        border-radius: 14px;
        padding: 18px 22px;
        margin-bottom: 16px;
        box-shadow: 0 10px 28px rgba(0, 0, 0, 0.35);
    }
    .metric-card {
        background: linear-gradient(145deg, #151b24 0%, #1c2430 100%);
        border: 1px solid #2b3544;
        border-top: 3px solid #38bdf8;
        border-radius: 12px;
        padding: 18px;
        text-align: center;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.25);
    }
    .metric-title {
        color: #94a3b8;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }
    .metric-value {
        color: #f8fafc;
        font-size: 1.85rem;
        font-weight: 800;
        margin-top: 6px;
    }
    .metric-subtext {
        color: #34d399;
        font-size: 0.82rem;
        font-weight: 600;
        margin-top: 4px;
    }
    .ex-card {
        background: rgba(21, 27, 36, 0.88);
        border: 1px solid #26303f;
        border-radius: 12px;
        padding: 14px 18px;
        margin-top: 14px;
        margin-bottom: 8px;
    }
    .ex-summary-pill {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 0.88rem;
        color: #cbd5e1;
        margin-top: 6px;
    }
    .scan-card {
        background: #151b24;
        border: 1px solid #2b3544;
        border-radius: 12px;
        padding: 16px;
        margin-top: 10px;
    }
    .tier-card {
        background: #151b24;
        border-radius: 12px;
        padding: 16px;
        border: 1px solid #2b3544;
        height: 100%;
    }
    div[data-testid="stButton"] > button {
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

DATA_FILE = "fitness_os_data.json"

BAR_OPTIONS = {
    "Olympic Straight Rod (20.0 kg)": 20.0,
    "Zig-Zag / EZ Curl Rod (7.5 kg)": 7.5,
    "Standard Straight Rod (10.0 kg)": 10.0,
    "Heavy Olympic / Custom (25.0 kg)": 25.0,
}

def clean_pdf_str(text):
    if not isinstance(text, str):
        text = str(text)
    replacements = {
        "₹": "Rs.", "→": "->", "•": "-", "—": "-", "–": "-",
        "“": '"', "”": '"', "’": "'", "‘": "'",
        "⚡": "", "🥗": "", "🏋️": "", "📊": "", "📑": "",
        "🔍": "", "🌅": "", "☀️": "", "🌙": "", "💡": "",
        "➕": "+", "➖": "-", "💾": "", "📥": "", "⏱️": ""
    }
    for orig, rep in replacements.items():
        text = text.replace(orig, rep)
    return text.encode("latin-1", "replace").decode("latin-1")

def load_all_users():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {}

def save_all_users(all_data):
    with open(DATA_FILE, "w") as f:
        json.dump(all_data, f, indent=4)

if "all_users_db" not in st.session_state:
    st.session_state.all_users_db = load_all_users()

query_user = st.query_params.get("user", None)
if "logged_in_user" not in st.session_state:
    if query_user and query_user in st.session_state.all_users_db:
        st.session_state.logged_in_user = query_user
    else:
        st.session_state.logged_in_user = None

if not st.session_state.logged_in_user:
    st.markdown("<h1 style='text-align:center;'>⚡ KSP Fitness OS</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#94a3b8;'>Sign in or create a quick PIN profile to keep your body stats, workouts, and diet private.</p>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1, 2, 1])
    with col_m:
        with st.form("login_form"):
            username_input = st.text_input("Your Name or Mobile Number", placeholder="e.g. Shashank").strip()
            pin_input = st.text_input("4-Digit Private PIN", type="password", max_chars=4, placeholder="e.g. 1234").strip()
            submit_login = st.form_submit_button("🔐 Access My Dashboard", type="primary", use_container_width=True)
            if submit_login:
                if not username_input or len(pin_input) < 4:
                    st.error("Please enter your Name/Mobile and a 4-digit PIN.")
                else:
                    user_key = username_input.lower()
                    db = st.session_state.all_users_db
                    if user_key in db:
                        saved_pin = db[user_key].get("pin", "")
                        if saved_pin and saved_pin != pin_input:
                            st.error("❌ Incorrect PIN for this profile.")
                        else:
                            db[user_key]["pin"] = pin_input
                            save_all_users(db)
                            st.session_state.logged_in_user = user_key
                            st.query_params["user"] = user_key
                            st.rerun()
                    else:
                        db[user_key] = {
                            "display_name": username_input.title(),
                            "pin": pin_input,
                            "workouts": {},
                            "profile": {
                                "height_cm": 160.0, "weight_kg": 75.0, "age": 29, "sex": "Male",
                                "smm_kg": 29.4, "body_fat_pct": 30.5, "visceral_level": 10,
                                "target_kcal": 1579, "target_protein": 115,
                                "recommended_split": "Bro Split (6-Day Complete Hypertrophy & Daily Cardio Finisher)",
                                "diet_preference": "Pure Vegetarian"
                            }
                        }
                        save_all_users(db)
                        st.session_state.logged_in_user = user_key
                        st.query_params["user"] = user_key
                        st.rerun()
    st.stop()

active_key = st.session_state.logged_in_user
user_data = st.session_state.all_users_db[active_key]
display_name = user_data.get("display_name", active_key.title())
profile = user_data["profile"]
profile.setdefault("age", 28)
profile.setdefault("sex", "Male")

def persist_current_user():
    st.session_state.all_users_db[active_key] = user_data
    save_all_users(st.session_state.all_users_db)

st.sidebar.markdown("## ⚡ KSP Fitness OS")
st.sidebar.success(f"👤 Logged in: **{display_name}**")
if st.sidebar.button("🚪 Logout / Switch User"):
    st.session_state.logged_in_user = None
    st.query_params.clear()
    st.rerun()

def get_gemini_api_key():
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        try:
            key = st.secrets.get("GEMINI_API_KEY")
        except Exception:
            key = None
    return key

def calculate_anthropometric_baseline(height_cm, weight_kg, age, sex):
    if height_cm <= 0 or weight_kg <= 0:
        return 22.0, 22.0
    bmi = weight_kg / ((height_cm / 100.0) ** 2)
    sex_factor = 1 if sex == "Male" else 0
    effective_age = min(age, 40)
    deurenberg_bf = (1.20 * bmi) + (0.23 * effective_age) - (10.8 * sex_factor) - 5.4
    indian_adjusted_bf = max(10.0, min(48.0, deurenberg_bf + 2.0))
    return round(bmi, 1), round(indian_adjusted_bf, 1)

def analyze_physique_fusion_ai(pil_image, height_cm, weight_kg, age, sex):
    fixed_img = ImageOps.exif_transpose(pil_image)
    if fixed_img.mode in ("RGBA", "P"):
        fixed_img = fixed_img.convert("RGB")
    bmi, baseline_bf = calculate_anthropometric_baseline(height_cm, weight_kg, age, sex)
    api_key = get_gemini_api_key()
    if not api_key:
        return {
            "estimated_bf_num": baseline_bf,
            "estimated_body_fat_range": f"{round(baseline_bf-1.5,1)}% - {round(baseline_bf+1.5,1)}%",
            "frame_analysis": f"⚠️ GEMINI_API_KEY not found in Streamlit Secrets. Showing formula baseline for {height_cm}cm / {weight_kg}kg (BMI {bmi}).",
            "recommendation": "Add GEMINI_API_KEY in Streamlit App Settings -> Secrets to enable live photo vision."
        }
    sys_prompt = (
        "You are an expert clinical anthropometrist and body-composition specialist. "
        f"Subject Biometrics: Height {height_cm} cm, Weight {weight_kg} kg, Age {age}, Sex {sex}, BMI {bmi}. "
        f"Statistical BMI Baseline: {baseline_bf}%. "
        "Return ONLY valid JSON with exact keys: "
        '{"estimated_bf_num": float, "estimated_body_fat_range": "XX% - YY%", "frame_analysis": "specific visual observation", "recommendation": "tailored diet and lifting advice"}'
    )
    try:
        fixed_img.thumbnail((1024, 1024))
        buffered = io.BytesIO()
        fixed_img.save(buffered, format="JPEG", quality=85)
        img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        parts = [
            {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
            {"text": f"Analyze this person's actual visual leanness vs their {height_cm}cm, {weight_kg}kg stats."}
        ]
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": parts}],
            "systemInstruction": {"parts": [{"text": sys_prompt}]},
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.15}
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as response:
            resp_data = json.loads(response.read().decode("utf-8"))
            return json.loads(resp_data["candidates"][0]["content"]["parts"][0]["text"])
    except Exception as e:
        return {
            "estimated_bf_num": baseline_bf,
            "estimated_body_fat_range": f"{round(baseline_bf-1.5,1)}% - {round(baseline_bf+1.5,1)}%",
            "frame_analysis": f"⚠️ Vision API error ({str(e)[:70]}). Math baseline used for {height_cm}cm / {weight_kg}kg.",
            "recommendation": "Check GEMINI_API_KEY in Streamlit Secrets or retry scan."
        }

def analyze_food_universally(text_query=None, pil_image=None):
    api_key = get_gemini_api_key()
    sys_instruction = (
        "You are an expert clinical and sports nutritionist specializing in Indian and global diets. "
        "Analyze the user's food query or photo. Return ONLY a valid JSON object with these exact keys:\n"
        '{"item_name": "name", "portion_description": "serving", "calories": kcal_num, "protein": p_num, "carbs": c_num, "fat": f_num, "fiber": fib_num, "dietary_notes": "tip"}'
    )
    if api_key:
        try:
            parts = []
            if text_query:
                parts.append({"text": f"Calculate exact nutritional profile for: '{text_query}'"})
            if pil_image:
                fixed_img = ImageOps.exif_transpose(pil_image)
                if fixed_img.mode in ("RGBA", "P"):
                    fixed_img = fixed_img.convert("RGB")
                fixed_img.thumbnail((1024, 1024))
                buffered = io.BytesIO()
                fixed_img.save(buffered, format="JPEG", quality=85)
                img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
                parts.append({"inline_data": {"mime_type": "image/jpeg", "data": img_b64}})
                parts.append({"text": "Identify the food/dish in this image, estimate portion size, and calculate exact macros."})
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": parts}],
                "systemInstruction": {"parts": [{"text": sys_instruction}]},
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=14) as response:
                resp_data = json.loads(response.read().decode("utf-8"))
                return json.loads(resp_data["candidates"][0]["content"]["parts"][0]["text"])
        except Exception:
            pass

    q = (text_query or "").lower()
    count_m = re.search(r"^(\d+(\.\d+)?)", q)
    qty = float(count_m.group(1)) if count_m else 1.0
    if "bann" in q or "banana" in q or "kela" in q:
        return {"item_name": "Banana", "portion_description": f"{qty} unit(s)", "calories": round(95*qty,1), "protein": round(1.2*qty,1), "carbs": round(24*qty,1), "fat": 0.3, "fiber": 2.6, "dietary_notes": "Fast-acting glycogen source."}
    elif "chilla" in q or "cheela" in q or "chila" in q:
        return {"item_name": "Moong / Besan Chilla", "portion_description": f"{qty} piece(s)", "calories": round(165*qty,1), "protein": round(9.0*qty,1), "carbs": round(21*qty,1), "fat": 4.0, "fiber": 3.5, "dietary_notes": "High complex carb & moderate protein vegetarian staple."}
    return {"item_name": text_query.title() if text_query else "Scanned Meal", "portion_description": f"{qty} serving", "calories": round(240*qty,1), "protein": round(12*qty,1), "carbs": round(30*qty,1), "fat": 7.0, "fiber": 3.0, "dietary_notes": "Clean whole-food macro balance."}

DIET_MATRIX = {
    ("Pure Vegetarian", "Tier 1"): {
        "meals": [
            ("🌅 MEAL 1: PRE/POST WORKOUT", "Sattu Power Chhas + Banana", "~₹18", "12g", "240 kcal", "40g Chana Sattu stirred in 250ml thin buttermilk with black salt, roasted jeera, and lemon + 1 small banana."),
            ("☀️ MEAL 2: HIGH-VOLUME LUNCH", "10-Min Soya Bhurji + Curd + 2 Roti", "~₹32", "42g", "510 kcal", "60g dry soya chunks (boiled, pulsed & sauteed with onions/tomatoes/chilli) + 150g fresh curd + 2 phulkas."),
            ("🌙 MEAL 3: EVENING & DINNER", "Moong Sprouts Chaat + Paneer/Chilla", "~₹35", "38g", "460 kcal", "100g sprouted moong chaat with cucumber and roasted chana + 1 medium besan chilla or 60g low-cost paneer.")
        ],
        "groceries": [
            ("Soya Chunks (Bulk Pack)", "2.0 kg", "₹220", "1,040 g protein", "₹0.21 / g (Highest ROI)"),
            ("Chana Sattu Powder", "1.5 kg", "₹210", "300 g protein", "₹0.70 / g"),
            ("Moong Dal (Sprouts & Chilla)", "2.0 kg", "₹260", "480 g protein", "₹0.54 / g"),
            ("Roasted Bengal Gram (Chana)", "1.0 kg", "₹140", "190 g protein", "₹0.73 / g"),
            ("Fresh Milk (for Daily Curd)", "10 Litres", "₹450", "320 g protein", "₹1.40 / g"),
            ("Seasonal Greens, Onions & Bananas", "30 Days", "₹600", "Micronutrients & Fiber", "Baseline Vitality")
        ],
        "total_cost": "₹1,880", "total_prot": "~3,600g Protein", "avg_roi": "~₹0.52 / g Net Average"
    },
    ("Pure Vegetarian", "Tier 2"): {
        "meals": [
            ("🌅 MEAL 1: POST WORKOUT", "Pea/Plant Protein Shake + Oats", "~₹65", "28g", "260 kcal", "1 scoop pure pea protein isolate blended with chilled water + 35g rolled oats and cinnamon."),
            ("☀️ MEAL 2: HIGH-PROTEIN LUNCH", "Low-Fat Paneer Tikka Bowl + Dal", "~₹75", "36g", "520 kcal", "120g pan-grilled low-fat paneer + 1 bowl thick moong dal + cucumber salad and 1 whole-wheat roti."),
            ("🌙 MEAL 3: EVENING & DINNER", "Soya Stir Fry + Curd & Peanuts", "~₹40", "38g", "430 kcal", "50g dry soya chunks tossed with capsicum, broccoli & soy sauce + 150g curd with roasted peanuts.")
        ],
        "groceries": [
            ("Plant / Pea Protein Isolate", "1.0 kg (30 scoops)", "₹1,600", "720 g protein", "₹2.20 / g"),
            ("Low-Fat Dairy Paneer", "4.0 kg", "₹1,400", "720 g protein", "₹1.94 / g"),
            ("Soya Chunks & Dal Blend", "2.0 kg", "₹240", "800 g protein", "₹0.30 / g"),
            ("Rolled Oats & Peanut Butter", "1.5 kg total", "₹550", "250 g protein", "₹2.20 / g"),
            ("Curd & Fresh Seasonal Veggies", "30 Days", "₹850", "250 g protein", "Healthy Gut & Satiety")
        ],
        "total_cost": "₹4,640", "total_prot": "~3,600g Protein", "avg_roi": "~₹1.28 / g Net Average"
    },
    ("Pure Vegetarian", "Tier 3"): {
        "meals": [
            ("🌅 MEAL 1: POST WORKOUT", "Whey Isolate + Berries Smoothie", "~₹140", "30g", "240 kcal", "1 scoop imported whey protein isolate + unsweetened almond milk + chia seeds and blueberries."),
            ("☀️ MEAL 2: ARTISANAL LUNCH", "Seared Organic Tofu + Greek Yogurt Bowl", "~₹180", "40g", "490 kcal", "150g organic pan-seared tofu + 150g Greek Yogurt + quinoa, edamame & avocado salad."),
            ("🌙 MEAL 3: GOURMET DINNER", "Grilled Cottage Cheese + Asparagus", "~₹160", "38g", "450 kcal", "130g grilled malai-free cottage cheese + 60g steamed edamame beans and roasted greens.")
        ],
        "groceries": [
            ("Whey Protein Isolate (Imported)", "2.0 kg (60 scoops)", "₹5,500", "1,620 g protein", "₹3.39 / g"),
            ("Artisanal Tofu & High-End Paneer", "5.0 kg", "₹2,200", "900 g protein", "₹2.44 / g"),
            ("Greek Yogurt Tubs", "24 Cups", "₹1,680", "192 g protein", "₹8.75 / g"),
            ("Chia, Almond Butter & Berries", "Monthly", "₹1,200", "Healthy Fats & Fiber", "Peak Bioavailability")
        ],
        "total_cost": "₹10,580", "total_prot": "~3,600g Protein", "avg_roi": "~₹2.93 / g Net Average"
    },
    ("Eggetarian / Non-Veg", "Tier 1"): {
        "meals": [
            ("🌅 MEAL 1: PRE/POST WORKOUT", "4 Boiled Eggs (2 Whole + 2 Whites) + Banana", "~₹28", "20g", "260 kcal", "2 whole boiled eggs + 2 egg whites seasoned with black pepper & rock salt + 1 banana."),
            ("☀️ MEAL 2: HIGH-VOLUME LUNCH", "Chicken Liver / Keema Curry + 2 Roti", "~₹42", "45g", "520 kcal", "150g spiced chicken liver or lean chicken keema sauteed with minimal oil + 2 phulkas + onion salad."),
            ("🌙 MEAL 3: EVENING & DINNER", "Egg Bhurji (3 Eggs) + Soya Chunks", "~₹32", "42g", "450 kcal", "3-egg masala bhurji mixed with 30g boiled soya granules + 1 cup buttermilk.")
        ],
        "groceries": [
            ("Whole Farm Eggs (Bulk Trays)", "150 Eggs (5 Trays)", "₹900", "900 g protein", "₹1.00 / g"),
            ("Chicken Liver / Lean Cuts", "3.0 kg", "₹660", "630 g protein", "₹1.04 / g"),
            ("Soya Chunks (Protein Booster)", "1.5 kg", "₹165", "780 g protein", "₹0.21 / g (Highest ROI)"),
            ("Atta, Buttermilk & Seasonal Veggies", "30 Days", "₹650", "Fiber & Micronutrients", "Satiety & Recovery")
        ],
        "total_cost": "₹2,375", "total_prot": "~3,600g Protein", "avg_roi": "~₹0.66 / g Net Average"
    },
    ("Eggetarian / Non-Veg", "Tier 2"): {
        "meals": [
            ("🌅 MEAL 1: POST WORKOUT", "4 Egg Whites + 2 Whole Omelette + Oats", "~₹55", "30g", "320 kcal", "Fluffy masala omelette (2 whole + 4 whites) + 35g rolled oats porridge."),
            ("☀️ MEAL 2: HIGH-PROTEIN LUNCH", "200g Grilled Chicken Breast + Rice/Roti", "~₹85", "48g", "490 kcal", "200g herb-marinated pan-seared chicken breast + 1 cup steamed rice/2 rotis + cucumber raita."),
            ("🌙 MEAL 3: EVENING & DINNER", "Rohu/Katla Fish Curry or Chicken Salad", "~₹75", "38g", "410 kcal", "150g local river fish curry or shredded chicken tikka salad with mint chutney.")
        ],
        "groceries": [
            ("Boneless Chicken Breast", "6.0 kg", "₹1,920", "1,380 g protein", "₹1.39 / g"),
            ("Whole Eggs", "120 Eggs (4 Trays)", "₹720", "720 g protein", "₹1.00 / g"),
            ("Local Fish (Rohu / Katla)", "2.0 kg", "₹600", "380 g protein", "₹1.57 / g"),
            ("Curd, Oats & Fresh Greens", "30 Days", "₹950", "Gut Health & Fiber", "Balanced Recomp")
        ],
        "total_cost": "₹4,190", "total_prot": "~3,600g Protein", "avg_roi": "~₹1.16 / g Net Average"
    },
    ("Eggetarian / Non-Veg", "Tier 3"): {
        "meals": [
            ("🌅 MEAL 1: POST WORKOUT", "Whey Isolate + 3 Pasture-Raised Eggs", "~₹155", "42g", "330 kcal", "1 scoop imported whey isolate + 3 poached/scrambled free-range eggs + sourdough toast."),
            ("☀️ MEAL 2: GOURMET LUNCH", "Grilled Salmon / Prawns + Quinoa Bowl", "~₹260", "42g", "480 kcal", "160g grilled Norwegian salmon or tiger prawns + quinoa, avocado & roasted bell peppers."),
            ("🌙 MEAL 3: LEAN DINNER", "200g Sous-Vide Chicken Breast + Greek Yogurt", "~₹150", "46g", "420 kcal", "200g herb-roasted chicken breast + 100g Greek yogurt tzatziki dip and asparagus.")
        ],
        "groceries": [
            ("Whey Protein Isolate (2kg Tub)", "1 Tub", "₹5,400", "1,620 g protein", "₹3.33 / g"),
            ("Salmon Fillets & Tiger Prawns", "3.0 kg", "₹3,200", "660 g protein", "₹4.84 / g"),
            ("Free-Range Eggs & Chicken Breast", "4.0 kg + 60 Eggs", "₹1,900", "1,280 g protein", "₹1.48 / g"),
            ("Avocado, Quinoa & Greek Yogurt", "Monthly", "₹1,400", "Omega-3 & Probiotics", "Peak Performance")
        ],
        "total_cost": "₹11,900", "total_prot": "~3,600g Protein", "avg_roi": "~₹3.30 / g Net Average"
    }
}

WORKOUT_SYSTEMS = {
    "Bro Split (6-Day Complete Hypertrophy & Daily Cardio Finisher)": {
        "Day 1 & 4: Back & Biceps (Mon / Thu)": [
            ("1. Lat Pulldown / Assisted Pull-Ups (Lat Width Compound)", "machine"),
            ("2. Seated Cable Row / Machine Row (Mid-Back Thickness)", "machine"),
            ("3. Single-Arm Dumbbell Row (Unilateral Lats & Rhomboids)", "per_side"),
            ("4. Straight-Arm Lat Pulldown & Rear Delt Fly (Upper Back/Rear Delts)", "machine"),
            ("5. Standing Dumbbell / Barbell Biceps Curls (Biceps Peak)", "barbell"),
            ("6. Dumbbell Hammer Curls (Brachialis & Forearms)", "per_side"),
            ("7. Dead Bug & Forearm Plank Hold (Core Stability)", "duration"),
            ("8. Finisher: 5m Stationary Cycle + 15m Incline Walk (15% @ 2.5-3.0 km/h)", "duration")
        ],
        "Day 2 & 5: Chest & Triceps (Tue / Fri)": [
            ("1. Flat Barbell / Machine Chest Press (Mid-Chest Compound)", "barbell"),
            ("2. Incline Dumbbell Press (Upper Clavicular Chest)", "per_side"),
            ("3. Pec Deck / Cable Chest Flyes (Inner & Lower Chest Isolation)", "machine"),
            ("4. Overhead Dumbbell / Cable Triceps Extension (Triceps Long Head)", "per_side"),
            ("5. Rope Triceps Pushdowns (Lateral & Medial Triceps Heads)", "machine"),
            ("6. Hanging Leg Raises & Forearm Plank (Core Stability)", "duration"),
            ("7. Finisher: 5m Stationary Cycle + 15m Incline Walk (15% @ 2.5-3.0 km/h)", "duration")
        ],
        "Day 3 & 6: Legs & Shoulders (Wed / Sat)": [
            ("1. Barbell Squat / Heavy Leg Press (Quad & Glute Compound)", "barbell"),
            ("2. Romanian Deadlifts (RDLs - Hamstrings & Glutes)", "barbell"),
            ("3. Seated Dumbbell Overhead Press (Anterior & Medial Delts)", "per_side"),
            ("4. Walking Lunges / Bulgarian Split Squats (Unilateral Legs)", "per_side"),
            ("5. Leg Extension & Seated Leg Curl Superset (Quad/Ham Isolation)", "machine"),
            ("6. Standing Lateral Raises & Standing Calf Raises (Side Delts & Calves)", "per_side"),
            ("7. Dead Bug & Deep Squat Hold Decompression (Core & Hip Mobility)", "duration"),
            ("8. Finisher: 5m Light Cycle + 15m Incline Walk (15% @ 2.5-3.0 km/h)", "duration")
        ]
    },
    "Upper / Lower (Metabolic Density - 4-Day Split)": {
        "Upper Power & Density (Mon / Thu)": [
            ("1. Flat Bench Press / Machine Chest Press (Heavy Compound)", "barbell"),
            ("2. Lat Pulldown / Assisted Pull-Ups (Vertical Pull)", "machine"),
            ("3. Incline Dumbbell Press (Upper Chest)", "per_side"),
            ("4. Seated Cable Row (Mid-Back Thickness)", "machine"),
            ("5. Standing Dumbbell Lateral Raises (Side Delts)", "per_side"),
            ("6. Rope Triceps Pushdowns & Dumbbell Curls (Arms)", "machine"),
            ("7. Finisher: 5m Stationary Cycle + 15m Incline Walk (15%)", "duration")
        ],
        "Lower Compound & Posterior Chain (Tue / Fri)": [
            ("1. Barbell Squat / Heavy Leg Press (Quad Compound)", "barbell"),
            ("2. Romanian Deadlifts (RDLs - Posterior Chain)", "barbell"),
            ("3. Walking Lunges / Bulgarian Split Squats (Unilateral)", "per_side"),
            ("4. Leg Curl / Leg Extension Superset (Isolation)", "machine"),
            ("5. Standing Calf Raises & Core Hollow Hold", "machine"),
            ("6. Finisher: 5m Light Cycle + 15m Incline Walk (15%)", "duration")
        ]
    },
    "Push / Pull / Legs (Recomp Split - Optimal for BF 18% - 25%)": {
        "Push Day (Chest, Shoulders & Triceps)": [
            ("1. Flat Bench Press / Machine Chest Press (Compound)", "barbell"),
            ("2. Overhead Dumbbell Press (Shoulder Compound)", "per_side"),
            ("3. Incline Dumbbell / Machine Press (Upper Chest)", "per_side"),
            ("4. Pec Deck Flyes & Lateral Raises", "machine"),
            ("5. Triceps Pushdowns & Overhead Extension", "machine"),
            ("6. Finisher: 5m Cycle + 15m Incline Walk (15%)", "duration")
        ],
        "Pull Day (Back, Rear Delts & Biceps)": [
            ("1. Lat Pulldown / Assisted Pull-Ups (Compound Width)", "machine"),
            ("2. Seated Cable Row / Machine Row (Compound Thickness)", "machine"),
            ("3. Single-Arm Dumbbell Row & Rear Delt Fly", "per_side"),
            ("4. Dumbbell Biceps Curls & Hammer Curls", "per_side"),
            ("5. Finisher: 5m Cycle + 15m Incline Walk (15%)", "duration")
        ],
        "Leg Day (Quads, Hamstrings, Calves & Core)": [
            ("1. Barbell Squat / Leg Press (Primary Compound)", "barbell"),
            ("2. Romanian Deadlifts (RDLs - Hamstring/Glute Compound)", "barbell"),
            ("3. Bulgarian Split Squats & Leg Extensions/Curls", "per_side"),
            ("4. Standing Calf Raises & Hanging Leg Raises", "machine"),
            ("5. Finisher: 5m Light Cycle + 15m Incline Walk (15%)", "duration")
        ]
    }
}

def recalibrate_user_targets(weight_kg, bfp):
    lean_mass = weight_kg * (1.0 - (bfp / 100.0))
    recommended_protein = max(int(round(lean_mass * 2.2)), 95)
    bmr = 370 + (21.6 * lean_mass)
    tdee = bmr * 1.35
    if bfp > 24.0:
        target_kcal = int(round(tdee - 450))
    elif bfp >= 18.0:
        target_kcal = int(round(tdee - 250))
    else:
        target_kcal = int(round(tdee + 150))
    if bfp > 25.0:
        recommended_split = "Bro Split (6-Day Complete Hypertrophy & Daily Cardio Finisher)"
    elif bfp >= 18.0:
        recommended_split = "Push / Pull / Legs (Recomp Split - Optimal for BF 18% - 25%)"
    else:
        recommended_split = "Bro Split (6-Day Complete Hypertrophy & Daily Cardio Finisher)"
    profile["weight_kg"] = weight_kg
    profile["body_fat_pct"] = bfp
    profile["target_kcal"] = target_kcal
    profile["target_protein"] = recommended_protein
    profile["recommended_split"] = recommended_split
    persist_current_user()

def build_pdf_document(log_date, workout_data):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_fill_color(15, 23, 42)
    pdf.rect(0, 0, 210, 32, 'F')
    pdf.set_text_color(56, 189, 248)
    pdf.set_font('Helvetica', 'B', 15)
    pdf.set_xy(10, 8)
    pdf.cell(190, 8, clean_pdf_str("KSP FITNESS OS - PERFORMANCE WORKOUT LOG"), ln=True, align='C')
    pdf.set_text_color(203, 213, 225)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(190, 6, clean_pdf_str(f"Athlete: {display_name} | Session Date: {log_date}"), ln=True, align='C')
    pdf.ln(12)
    pdf.set_text_color(20, 20, 20)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 7, clean_pdf_str(f"Program Split: {workout_data.get('split', 'Bro Split')}"), ln=True)
    pdf.cell(0, 7, clean_pdf_str(f"Total Weight Lifted (Tonnage): {workout_data.get('grand_total_volume_kg', 0)} kg"), ln=True)
    pdf.cell(0, 7, clean_pdf_str(f"Total Calorie Burn: ~{workout_data.get('total_calories_burned', 0)} kcal"), ln=True)
    pdf.ln(4)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, clean_pdf_str("DETAILED EXERCISE & DURATION LOG"), ln=True)
    pdf.ln(2)
    for ex_name, details in workout_data.get('exercises', {}).items():
        pdf.set_fill_color(241, 245, 249)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(15, 23, 42)
        if details.get("entry_mode") == "duration":
            dur_val = details.get("duration_value", 0)
            dur_unit = details.get("duration_unit", "Minutes")
            notes_txt = f" ({details.get('notes')})" if details.get("notes") else ""
            pdf.cell(190, 7, clean_pdf_str(f"  {ex_name} | Time: {dur_val} {dur_unit}{notes_txt} | Burn: ~{details.get('exercise_kcal', 0)} kcal"), border=1, ln=True, fill=True)
        else:
            pdf.cell(190, 7, clean_pdf_str(f"  {ex_name} | Volume: {details.get('exercise_volume', 0)} kg | Burn: ~{details.get('exercise_kcal', 0)} kcal"), border=1, ln=True, fill=True)
            pdf.set_font('Helvetica', '', 9)
            pdf.set_text_color(40, 40, 40)
            for s in details.get('sets', []):
                pdf.cell(190, 6, clean_pdf_str(f"      Set {s.get('set', 1)}: {s.get('total_weight', 0.0)} kg total ({s.get('reps', 0)} reps) -> Volume: {s.get('volume', 0)} kg [{s.get('calc_type', '')}]"), border='LR', ln=True)
            pdf.cell(190, 1, '', border='T', ln=True)
        pdf.ln(3)
    return bytes(pdf.output())

def build_diet_pdf(profile_data, diet_pref, tier_choice):
    tier_key = "Tier 1" if "Tier 1" in tier_choice else ("Tier 2" if "Tier 2" in tier_choice else "Tier 3")
    plan_data = DIET_MATRIX.get((diet_pref, tier_key), DIET_MATRIX[("Pure Vegetarian", "Tier 1")])
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_fill_color(15, 23, 42)
    pdf.rect(0, 0, 210, 32, 'F')
    pdf.set_text_color(56, 189, 248)
    pdf.set_font('Helvetica', 'B', 15)
    pdf.set_xy(10, 8)
    pdf.cell(190, 8, clean_pdf_str("KSP FITNESS OS - 30-DAY BUDGET & MEAL ARCHITECT"), ln=True, align='C')
    pdf.set_text_color(203, 213, 225)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(190, 6, clean_pdf_str(f"User: {display_name} | Pref: {diet_pref} | {tier_choice}"), ln=True, align='C')
    pdf.ln(12)
    pdf.set_text_color(20, 20, 20)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 7, clean_pdf_str(f"Target Daily Calories: {profile_data.get('target_kcal', 1579)} kcal"), ln=True)
    pdf.cell(0, 7, clean_pdf_str(f"Target Daily Protein Floor: {profile_data.get('target_protein', 115)} g/day"), ln=True)
    pdf.cell(0, 7, clean_pdf_str(f"Weight: {profile_data.get('weight_kg', 75.0)} kg | Body Fat: {profile_data.get('body_fat_pct', 30.5)}%"), ln=True)
    pdf.ln(4)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, clean_pdf_str("DAILY MEAL STRUCTURE"), ln=True)
    for m_tag, m_title, m_cost, m_prot, m_cals, m_desc in plan_data["meals"]:
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(0, 6, clean_pdf_str(f"  {m_title} ({m_prot} Protein | {m_cals} | {m_cost})"), ln=True)
        pdf.set_font('Helvetica', '', 9)
        pdf.multi_cell(190, 5, clean_pdf_str(f"    {m_desc}"))
        pdf.ln(2)
    pdf.ln(3)
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, clean_pdf_str("ESTIMATED 30-DAY GROCERY HAUL & BUDGET"), ln=True)
    pdf.set_font('Helvetica', '', 10)
    for itm, qty, prc, prot_y, roi in plan_data["groceries"]:
        pdf.cell(190, 6, clean_pdf_str(f"  - {itm} [{qty}] -> {prc} ({prot_y} | {roi})"), ln=True)
    pdf.ln(3)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 7, clean_pdf_str(f"Total Monthly Investment: {plan_data['total_cost']} ({plan_data['avg_roi']})"), ln=True)
    return bytes(pdf.output())

menu = st.sidebar.radio("Navigation", [
    "📊 Dashboard & BMI",
    "📑 InBody & Body Composition",
    "🥗 Smart Diet & Budget Planner",
    "🏋️ Adaptive Workout Logger",
    "🔍 Universal Food & Macro AI"
])

if menu == "📊 Dashboard & BMI":
    st.markdown(f"""<div class="hero-banner">
        <h2 style="margin:0; color:#f8fafc;">⚡ Performance Dashboard — {display_name}</h2>
        <p style="margin:4px 0 0 0; color:#94a3b8; font-size:0.92rem;">Body Recomposition Telemetry &bull; Caloric Deficit &amp; Progressive Overload Command</p>
    </div>""", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"""<div class="metric-card"><div class="metric-title">Daily Calories</div><div class="metric-value">{profile.get('target_kcal', 1579)}</div><div class="metric-subtext">kcal / day</div></div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class="metric-card"><div class="metric-title">Daily Protein</div><div class="metric-value">{profile.get('target_protein', 115)}g</div><div class="metric-subtext">Body Fat: {profile.get('body_fat_pct', 30.5)}%</div></div>""", unsafe_allow_html=True)
    c3.markdown("""<div class="metric-card"><div class="metric-title">Cardio Finisher</div><div class="metric-value">5m + 15m</div><div class="metric-subtext">Cycle + 15% Incline Walk</div></div>""", unsafe_allow_html=True)
    c4.markdown(f"""<div class="metric-card"><div class="metric-title">Active Split</div><div class="metric-value" style="font-size: 1.0rem; margin-top: 10px;">{profile.get('recommended_split', 'Bro Split')}</div><div class="metric-subtext">Synced</div></div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("⚖️ Biometric Health & BMI Analyzer")
    b1, b2 = st.columns(2)
    with b1:
        h_cm = st.number_input("Height (cm)", value=float(profile.get("height_cm", 160.0)), step=0.5)
        w_kg = st.number_input("Current Weight (kg)", value=float(profile.get("weight_kg", 75.0)), step=0.1)
        if st.button("💾 Save Height & Weight"):
            profile["height_cm"] = h_cm
            profile["weight_kg"] = w_kg
            recalibrate_user_targets(w_kg, profile.get("body_fat_pct", 30.5))
            st.success("Vitals saved!")
            st.rerun()
    with b2:
        if h_cm > 0 and w_kg > 0:
            bmi = round(w_kg / ((h_cm / 100.0) ** 2), 2)
            cat, col = ("Normal Weight", "#34d399") if 18.5 <= bmi < 23.0 else (("Overweight (Indian Cut-Off)", "#fbbf24") if 23.0 <= bmi < 25.0 else ("Obese Range", "#f87171"))
            st.markdown(f"""<div style="background-color: #151b24; border-left: 5px solid {col}; padding: 18px; border-radius: 10px; margin-top: 15px;">
                <div style="font-size: 0.9rem; color: #94a3b8;">Calculated Body Mass Index (BMI)</div>
                <div style="font-size: 2.2rem; font-weight: bold; color: {col};">{bmi} kg/m²</div>
                <div style="font-size: 1rem; color: #e6edf3;">Classification: <strong>{cat}</strong></div>
            </div>""", unsafe_allow_html=True)

elif menu == "📑 InBody & Body Composition":
    st.title("📑 InBody / DEXA & Multimodal Vision Engine")
    tab_photo, tab_scan = st.tabs(["📸 AI Photo + Biometric Fusion Scanner", "📊 Manual InBody / DEXA Entry"])
    with tab_photo:
        st.subheader("📸 Multimodal Body Fat Estimator (Photo + Height/Weight Fusion)")
        st.caption("Fuses your height, weight, age, and South Asian body-composition baseline with visual muscle-vs-fat detection.")
        user_photo = st.file_uploader("Step 1: Upload Full / Upper Body Photo", type=["jpg", "jpeg", "png"], key="user_photo_vision")
        if user_photo:
            raw_img = Image.open(user_photo)
            upright_img = ImageOps.exif_transpose(raw_img)
            col_img, col_bio = st.columns([1, 1.3])
            with col_img:
                st.image(upright_img, caption="Orientation-Corrected Snapshot", width=280)
            with col_bio:
                st.markdown("#### Step 2: Confirm Biometrics for Accurate Scaling")
                f_h = st.number_input("Height (cm)", min_value=120.0, max_value=230.0, value=float(profile.get("height_cm", 160.0)), step=0.5, key="fusion_h")
                f_w = st.number_input("Weight (kg)", min_value=30.0, max_value=200.0, value=float(profile.get("weight_kg", 75.0)), step=0.1, key="fusion_w")
                c_age, c_sex = st.columns(2)
                with c_age:
                    f_age = st.number_input("Age", min_value=14, max_value=90, value=int(profile.get("age", 29)), step=1, key="fusion_age")
                with c_sex:
                    f_sex = st.selectbox("Sex", ["Male", "Female"], index=0 if profile.get("sex", "Male") == "Male" else 1, key="fusion_sex")
                if st.button("🔍 Run Fused AI Physique Analysis", type="primary", use_container_width=True):
                    profile["height_cm"] = f_h
                    profile["weight_kg"] = f_w
                    profile["age"] = f_age
                    profile["sex"] = f_sex
                    persist_current_user()
                    with st.spinner("Fusing stature-to-weight density with visual muscle & fat contours..."):
                        st.session_state.last_vision_scan = analyze_physique_fusion_ai(upright_img, f_h, f_w, f_age, f_sex)
            if "last_vision_scan" in st.session_state:
                vres = st.session_state.last_vision_scan
                est_num = float(vres.get("estimated_bf_num", 30.5))
                st.markdown(f"""<div class="scan-card">
                    <h4 style="color:#38bdf8; margin-bottom:6px;">🔍 Fused Anthropometric + Vision Breakdown</h4>
                    <p style="font-size: 1.2rem;"><strong>Calibrated Body Fat Range:</strong> <span style="color:#34d399; font-weight:bold;">{vres.get('estimated_body_fat_range', '')}</span></p>
                    <p><strong>Physique & Mass Analysis:</strong> {vres.get('frame_analysis', '')}</p>
                    <p style="color:#94a3b8; font-size:0.9rem;"><strong>Protocol:</strong> {vres.get('recommendation', '')}</p>
                </div>""", unsafe_allow_html=True)
                if st.button(f"⚡ Sync {est_num}% Body Fat & {f_w} kg to My Dashboard & Split"):
                    recalibrate_user_targets(f_w, est_num)
                    st.success(f"✅ Dashboard, calories, and workout split updated to {est_num}% body fat!")
                    st.rerun()
    with tab_scan:
        st.subheader("InBody / DEXA Telemetry")
        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1:
            scan_weight = st.number_input("Scale Weight (kg)", value=float(profile.get("weight_kg", 75.0)), step=0.1)
        with sc2:
            scan_smm = st.number_input("Skeletal Muscle Mass (kg)", value=float(profile.get("smm_kg", 29.4)), step=0.1)
        with sc3:
            scan_bfp = st.number_input("Body Fat Percentage (%)", value=float(profile.get("body_fat_pct", 30.5)), step=0.1)
        with sc4:
            scan_vfl = st.number_input("Visceral Fat Level", value=int(profile.get("visceral_level", 10)), step=1)
        if st.button("🚀 Recalibrate App & Workout Plan", type="primary"):
            profile["smm_kg"] = scan_smm
            profile["visceral_level"] = scan_vfl
            recalibrate_user_targets(scan_weight, scan_bfp)
            st.success("✅ Profile calibrated!")
            st.rerun()

elif menu == "🥗 Smart Diet & Budget Planner":
    st.title(f"🥗 Smart Diet & Budget Architect — {display_name}")
    st.markdown("Precision nutritional engineering: High protein, high fiber, minimal calorie density, and maximum rupee value.")
    t_cals = profile.get('target_kcal', 1579)
    t_prot = profile.get('target_protein', 115)
    top_c1, top_c2, top_c3 = st.columns([1, 1.2, 1.8])
    with top_c1:
        diet_type = st.radio("Dietary Preference", ["Pure Vegetarian", "Eggetarian / Non-Veg"], horizontal=True)
    with top_c2:
        tier = st.selectbox("Select Investment Tier", [
            "Tier 1: High-ROI Budget (Rs. 1,800 - Rs. 2,500/mo)",
            "Tier 2: Balanced Mid-Range (Rs. 3,800 - Rs. 5,000/mo)",
            "Tier 3: Premium Convenience (Rs. 7,500 - Rs. 10,000+/mo)"
        ])
    with top_c3:
        st.markdown(f"""<div style="background:#151b24; border:1px solid #2b3544; border-radius:8px; padding:10px 14px;">
            <span style="color:#94a3b8; font-size:0.85rem;">CALIBRATED MACRO BLUEPRINT</span><br>
            <strong>{t_cals} kcal/day</strong> &bull; <span style="color:#34d399; font-weight:bold;">{t_prot}g Protein</span> &bull; <span>~32g Fiber</span>
        </div>""", unsafe_allow_html=True)
    tier_key = "Tier 1" if "Tier 1" in tier else ("Tier 2" if "Tier 2" in tier else "Tier 3")
    active_plan = DIET_MATRIX.get((diet_type, tier_key), DIET_MATRIX[("Pure Vegetarian", "Tier 1")])
    st.markdown("---")
    st.subheader(f"🍱 Daily Meal Blueprint ({diet_type} • {tier_key})")
    m_cols = st.columns(3)
    colors = ["#34d399", "#38bdf8", "#fbbf24"]
    for idx, (m_tag, m_title, m_cost, m_prot, m_cals, m_desc) in enumerate(active_plan["meals"]):
        with m_cols[idx]:
            st.markdown(f"""<div class="tier-card">
                <span style="color:{colors[idx]}; font-weight:bold;">{m_tag}</span>
                <h4 style="margin:4px 0;">{m_title}</h4>
                <p style="color:#94a3b8; font-size:0.85rem;"><strong>Cost:</strong> {m_cost} | <strong>Protein:</strong> {m_prot} | <strong>Cals:</strong> {m_cals}</p>
                <p style="font-size:0.9rem;">{m_desc}</p>
            </div>""", unsafe_allow_html=True)
    st.markdown("---")
    st.subheader("🛒 30-Day Bulk Grocery Haul & Spending Forecast")
    g_tab1, g_tab2 = st.tabs(["📋 Itemized Shopping List", "👨‍🍳 10-Minute Batch Cook Recipes"])
    with g_tab1:
        table_md = "| Item | Monthly Quantity | Estimated Cost | Protein Yield | Value Metric (₹/g Protein) |\n| :--- | :--- | :--- | :--- | :--- |\n"
        for itm, qty, prc, prot_y, roi in active_plan["groceries"]:
            table_md += f"| **{itm}** | {qty} | {prc} | {prot_y} | **{roi}** |\n"
        table_md += f"| **TOTAL MONTHLY INVESTMENT** | | **{active_plan['total_cost']}** | **{active_plan['total_prot']}** | **{active_plan['avg_roi']}** |\n"
        st.markdown(table_md)
    with g_tab2:
        if diet_type == "Pure Vegetarian":
            st.markdown("""
            #### 1. 10-Minute Soya Keema Bhurji (31g Protein | ₹8 cost)
- Boil 60g soya chunks in salted water for 5 minutes. Squeeze dry and pulse in mixer for 3 seconds. Saute with green chilli, turmeric, salt, and 1 tsp mustard oil for 3 minutes.
            #### 2. No-Cook Electrolyte Sattu Shake (12g Protein | ₹12 cost)
- Mix 40g chana sattu in 250ml cold water with black salt, roasted jeera, and half a lemon.
            """)
        else:
            st.markdown("""
            #### 1. 8-Minute High-Protein Egg & Soya Bhurji (38g Protein | ₹26 cost)
- Soak 30g soya granules in hot water for 4 mins, squeeze dry, and scramble with 3 whole eggs, onions, and spices.
            #### 2. 10-Minute Pan-Seared Pepper Chicken Breast (46g Protein | ₹65 cost)
- Slice 200g chicken breast into thin strips and sear on a hot pan with garlic, crushed pepper, and lemon juice for 4 mins per side.
            """)
    st.markdown("---")
    st.subheader("📄 Download Customized 30-Day Diet & Grocery Plan (PDF)")
    diet_pdf_bytes = build_diet_pdf(profile, diet_type, tier)
    b64_diet = base64.b64encode(diet_pdf_bytes).decode('utf-8')
    st.markdown(f'<a href="data:application/pdf;base64,{b64_diet}" download="KSP_30Day_Diet_{display_name}.pdf" target="_blank" style="display: inline-block; padding: 10px 18px; background-color: #16a34a; color: white; border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 6px;">📥 Download 30-Day Diet & Budget PDF</a>', unsafe_allow_html=True)

elif menu == "🏋️ Adaptive Workout Logger":
    st.markdown("""<div class="hero-banner">
        <h2 style="margin:0; color:#f8fafc;">🏋️ Adaptive Workout, Per-Side Load &amp; Time Logger</h2>
        <p style="margin:4px 0 0 0; color:#94a3b8; font-size:0.92rem;">Separate per-side dumbbell &amp; barbell plate math + dedicated Seconds/Minutes tracking for core &amp; cardio</p>
    </div>""", unsafe_allow_html=True)

    system_keys = list(WORKOUT_SYSTEMS.keys())
    saved_rec = profile.get("recommended_split", system_keys[0])
    default_sys_idx = system_keys.index(saved_rec) if saved_rec in system_keys else 0

    col_sys, col_day, col_date = st.columns([2, 2, 1])
    with col_sys:
        chosen_system = st.selectbox("Training System", system_keys, index=default_sys_idx)
    with col_day:
        available_days = list(WORKOUT_SYSTEMS[chosen_system].keys())
        split_choice = st.selectbox("Select Workout Day", available_days)
    with col_date:
        session_date = st.date_input("Date", value=date.today())
        log_date = session_date.strftime("%Y-%m-%d")

    exercises = WORKOUT_SYSTEMS[chosen_system][split_choice]
    user_weight = float(profile.get("weight_kg", 75.0))

    if "exercise_set_counts" not in st.session_state:
        st.session_state.exercise_set_counts = {}

    session_workout_data = {}
    grand_total_volume = 0.0
    grand_total_cals = 0.0

    for idx, (ex, ex_type) in enumerate(exercises):
        st.markdown(f"""<div class="ex-card">
            <div style="font-size:1.08rem; font-weight:700; color:#f8fafc;">{idx + 1}. {ex}</div>
        </div>""", unsafe_allow_html=True)

        if ex_type == "duration":
            is_cardio = any(w in ex.lower() for w in ["cardio", "finisher", "walk", "cycle", "treadmill", "elliptical", "liss"])
            default_unit_idx = 1 if is_cardio else 0
            default_dur = 20 if is_cardio else 45

            d_col1, d_col2, d_col3 = st.columns([1.5, 1.2, 2.3])
            with d_col1:
                dur_val = st.number_input(
                    "Duration",
                    min_value=0.0,
                    step=1.0 if default_unit_idx == 1 else 5.0,
                    value=float(default_dur),
                    key=f"{active_key}_{log_date}_{ex}_dur_val"
                )
            with d_col2:
                dur_unit = st.selectbox(
                    "Unit",
                    ["Seconds", "Minutes"],
                    index=default_unit_idx,
                    key=f"{active_key}_{log_date}_{ex}_dur_unit"
                )
            with d_col3:
                dur_notes = st.text_input(
                    "Incline / Speed / Hold Notes",
                    placeholder="e.g. 15% incline @ 2.5 km/h + 5m cycle, or 3x45s plank",
                    key=f"{active_key}_{log_date}_{ex}_dur_notes"
                )

            minutes_equiv = (dur_val / 60.0) if dur_unit == "Seconds" else dur_val
            met_rate = 7.2 if is_cardio else 3.5
            ex_kcal = round(((met_rate * 3.5 * user_weight) / 200.0) * minutes_equiv, 1) if dur_val > 0 else 0.0
            grand_total_cals += ex_kcal

            st.markdown(f"""<div class="ex-summary-pill">
                ⏱️ Logged Time: <strong>{dur_val:g} {dur_unit}</strong> &nbsp;|&nbsp; Estimated Burn: <span style="color:#34d399; font-weight:700;">~{ex_kcal} kcal</span>
            </div>""", unsafe_allow_html=True)

            session_workout_data[ex] = {
                "entry_mode": "duration",
                "duration_value": dur_val,
                "duration_unit": dur_unit,
                "notes": dur_notes.strip(),
                "sets": [],
                "exercise_volume": 0.0,
                "exercise_kcal": ex_kcal
            }
        else:
            set_count_key = f"{active_key}_{log_date}_{ex}_count"
            if set_count_key not in st.session_state.exercise_set_counts:
                st.session_state.exercise_set_counts[set_count_key] = 3
            current_sets = st.session_state.exercise_set_counts[set_count_key]

            ctrl1, ctrl2, mode_col, bar_col = st.columns([1, 1, 2.2, 2.0])
            with ctrl1:
                if st.button("➕ Add Set", key=f"add_{active_key}_{ex}_{idx}"):
                    st.session_state.exercise_set_counts[set_count_key] += 1
                    st.rerun()
            with ctrl2:
                if st.button("➖ Remove Set", key=f"sub_{active_key}_{ex}_{idx}") and current_sets > 1:
                    st.session_state.exercise_set_counts[set_count_key] -= 1
                    st.rerun()

            mode_options = [
                "Dumbbell (Weight Each Side x 2)",
                "Barbell (Plate Each Side x 2 + Bar)",
                "Machine / Single Direct Weight"
            ]
            default_mode_idx = 1 if ex_type == "barbell" else (0 if ex_type == "per_side" else 2)
            with mode_col:
                calc_mode = st.selectbox(
                    "Equipment & Weight Formula",
                    mode_options,
                    index=default_mode_idx,
                    key=f"{active_key}_{log_date}_{ex}_mode"
                )

            bar_weight = 0.0
            bar_label = ""
            if "Barbell" in calc_mode:
                with bar_col:
                    bar_choice = st.selectbox(
                        "Barbell Rod Type",
                        list(BAR_OPTIONS.keys()),
                        index=0,
                        key=f"{active_key}_{log_date}_{ex}_bar"
                    )
                    bar_weight = BAR_OPTIONS[bar_choice]
                    bar_label = bar_choice
            else:
                with bar_col:
                    st.markdown("<div style='padding-top:26px; color:#94a3b8; font-size:0.85rem;'>" + ("Two dumbbells paired (Left + Right)" if "Dumbbell" in calc_mode else "Direct stack / pin weight") + "</div>", unsafe_allow_html=True)

            ex_sets = []
            ex_volume = 0.0
            ex_cals = 0.0

            h1, h2, h3, h4 = st.columns([1, 2, 2, 2.5])
            h1.markdown("<span style='color:#94a3b8; font-size:0.82rem; font-weight:700;'>SET</span>", unsafe_allow_html=True)
            wt_header = "EACH SIDE (kg)" if ("Dumbbell" in calc_mode or "Barbell" in calc_mode) else "WEIGHT (kg)"
            h2.markdown(f"<span style='color:#94a3b8; font-size:0.82rem; font-weight:700;'>{wt_header}</span>", unsafe_allow_html=True)
            h3.markdown("<span style='color:#94a3b8; font-size:0.82rem; font-weight:700;'>REPS</span>", unsafe_allow_html=True)
            h4.markdown("<span style='color:#94a3b8; font-size:0.82rem; font-weight:700;'>TOTAL LOAD, VOLUME & BURN</span>", unsafe_allow_html=True)

            for s in range(1, current_sets + 1):
                sc1, sc2, sc3, sc4 = st.columns([1, 2, 2, 2.5])
                sc1.markdown(f"<div style='padding-top:8px;'><strong>Set {s}</strong></div>", unsafe_allow_html=True)
                input_wt = sc2.number_input(
                    f"Wt_{s}",
                    min_value=0.0,
                    step=1.25,
                    key=f"{active_key}_{log_date}_{ex}_s{s}_wt",
                    label_visibility="collapsed"
                )
                s_rp = sc3.number_input(
                    f"Reps_{s}",
                    min_value=0,
                    step=1,
                    value=10,
                    key=f"{active_key}_{log_date}_{ex}_s{s}_rp",
                    label_visibility="collapsed"
                )

                if "Dumbbell" in calc_mode:
                    effective_total_wt = round(input_wt * 2.0, 2) if input_wt > 0 else 0.0
                    calc_note = f"{input_wt:g}kg each side (x2)"
                elif "Barbell" in calc_mode:
                    effective_total_wt = round((input_wt * 2.0) + bar_weight, 2) if (input_wt > 0 or bar_weight > 0) and s_rp > 0 and input_wt > 0 else (bar_weight if input_wt == 0 and s_rp > 0 and st.session_state.get(f"{active_key}_{log_date}_{ex}_include_bar", False) else (round((input_wt * 2.0) + bar_weight, 2) if input_wt > 0 else 0.0))
                    calc_note = f"{input_wt:g}kg/side + {bar_weight:g}kg bar"
                else:
                    effective_total_wt = round(input_wt, 2)
                    calc_note = f"{input_wt:g}kg direct"

                set_vol = round(effective_total_wt * s_rp, 1)
                set_kcal = round((0.14 * user_weight) + (0.0022 * set_vol), 1) if (effective_total_wt > 0 and s_rp > 0) else 0.0
                ex_volume += set_vol
                ex_cals += set_kcal

                sc4.markdown(
                    f"<div style='padding-top:6px;'><strong>{effective_total_wt:g} kg</strong> &times; {s_rp} = <strong>{set_vol:g} kg</strong> | <span style='color:#34d399; font-weight:600;'>~{set_kcal} kcal</span></div>",
                    unsafe_allow_html=True
                )
                ex_sets.append({
                    "set": s,
                    "side_or_input_weight": input_wt,
                    "total_weight": effective_total_wt,
                    "reps": s_rp,
                    "volume": set_vol,
                    "calc_type": calc_note
                })

            grand_total_volume += ex_volume
            grand_total_cals += ex_cals

            st.markdown(f"""<div class="ex-summary-pill">
                Exercise Total Volume: <strong>{round(ex_volume, 1):g} kg</strong> &nbsp;|&nbsp; Exercise Burn: <span style="color:#34d399; font-weight:700;">~{round(ex_cals, 1)} kcal</span>
            </div>""", unsafe_allow_html=True)

            session_workout_data[ex] = {
                "entry_mode": "sets",
                "sets": ex_sets,
                "exercise_volume": round(ex_volume, 1),
                "exercise_kcal": round(ex_cals, 1)
            }

    st.markdown("---")
    s_col1, s_col2 = st.columns(2)
    s_col1.metric("Total Session Tonnage", f"{round(grand_total_volume, 1):g} kg")
    s_col2.metric("Estimated Total Session Burn", f"~{round(grand_total_cals, 1)} kcal")

    if st.button("💾 Lock & Persist Workout Session", type="primary"):
        user_data.setdefault("workouts", {})[log_date] = {
            "split": f"{chosen_system} - {split_choice}",
            "exercises": session_workout_data,
            "grand_total_volume_kg": round(grand_total_volume, 1),
            "total_calories_burned": round(grand_total_cals, 1)
        }
        persist_current_user()
        st.success(f"✅ Workout saved for {display_name}!")

    if log_date in user_data.get("workouts", {}):
        pdf_bytes = build_pdf_document(log_date, user_data["workouts"][log_date])
        b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        st.markdown(
            f'<a href="data:application/pdf;base64,{b64_pdf}" download="KSP_Workout_{display_name}_{log_date}.pdf" target="_blank" style="display: inline-block; padding: 10px 18px; background-color: #16a34a; color: white; border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 10px;">📥 Download Workout PDF</a>',
            unsafe_allow_html=True
        )

elif menu == "🔍 Universal Food & Macro AI":
    st.title("🔍 Universal Food & Macro AI")
    st.markdown("Multimodal nutrition intelligence: Type any regional Indian dish or snap a photo of your meal plate for instant macro breakdown.")
    tab_text, tab_photo = st.tabs(["💬 Natural Language Query", "📸 Real Meal / Food Photo"])
    with tab_text:
        user_query = st.text_input("Describe your food naturally:", placeholder="e.g. '2 medium bananas', 'moong dal chilla with mint chutney', '150g paneer bhurji'")
        if st.button("🚀 Analyze Nutrition", type="primary", key="btn_text_macro"):
            if not user_query.strip():
                st.warning("Please type a food description first.")
            else:
                with st.spinner("AI analyzing nutrition & portion metrics..."):
                    res = analyze_food_universally(text_query=user_query)
                    st.markdown(f"""<div class="scan-card">
                        <h3 style="color:#38bdf8; margin-bottom: 2px;">{res.get('item_name', 'Analyzed Item')}</h3>
                        <p style="color:#94a3b8;">Serving: <strong>{res.get('portion_description', '')}</strong></p>
                        <p style="color:#34d399; font-size:0.95rem;">💡 <em>{res.get('dietary_notes', '')}</em></p>
                    </div>""", unsafe_allow_html=True)
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Calories", f"{res.get('calories', 0)} kcal")
                    m2.metric("Protein", f"{res.get('protein', 0)} g")
                    m3.metric("Carbs", f"{res.get('carbs', 0)} g")
                    m4.metric("Fat", f"{res.get('fat', 0)} g")
    with tab_photo:
        st.markdown("Upload or take a photo of any meal, plate, snack, or fruit:")
        photo_file = st.file_uploader("Upload Meal Photo", type=["jpg", "jpeg", "png"], key="universal_meal_img")
        if photo_file:
            raw_meal_img = Image.open(photo_file)
            pil_img = ImageOps.exif_transpose(raw_meal_img)
            st.image(pil_img, caption="Meal Uploaded", width=340)
            if st.button("🔍 AI Vision Scan Meal", type="primary", key="btn_photo_macro"):
                with st.spinner("Analyzing dish contents, ingredients, and portion weight..."):
                    res = analyze_food_universally(pil_image=pil_img)
                    st.markdown(f"""<div class="scan-card">
                        <h3 style="color:#38bdf8; margin-bottom: 2px;">{res.get('item_name', 'Recognized Plate')}</h3>
                        <p style="color:#94a3b8;">Estimated Serving: <strong>{res.get('portion_description', '')}</strong></p>
                        <p style="color:#34d399; font-size:0.95rem;">💡 <em>{res.get('dietary_notes', '')}</em></p>
                    </div>""", unsafe_allow_html=True)
                    p1, p2, p3, p4 = st.columns(4)
                    p1.metric("Calories", f"{res.get('calories', 0)} kcal")
                    p2.metric("Protein", f"{res.get('protein', 0)} g")
                    p3.metric("Carbs", f"{res.get('carbs', 0)} g")
                    p4.metric("Fat", f"{res.get('fat', 0)} g")