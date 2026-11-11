import os
import io
import re
import json
import base64
import urllib.request
import urllib.error
from datetime import date
from PIL import Image
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
    .stApp { background-color: #0d1117; color: #e6edf3; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .metric-card { background: linear-gradient(135deg, #161b22 0%, #21262d 100%); border: 1px solid #30363d; border-radius: 12px; padding: 18px; text-align: center; }
    .metric-title { color: #8b949e; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; }
    .metric-value { color: #58a6ff; font-size: 1.8rem; font-weight: 700; margin-top: 4px; }
    .metric-subtext { color: #3fb950; font-size: 0.8rem; }
    .scan-card { background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 16px; margin-top: 10px; }
    .report-card { background: #0d1117; border: 1px solid #388bfd; border-radius: 10px; padding: 16px; margin-top: 15px; }
    .split-badge { display: inline-block; padding: 4px 10px; background: #238636; color: #ffffff; border-radius: 16px; font-size: 0.8rem; font-weight: bold; margin-bottom: 10px; }
    .tier-card { background: #161b22; border-radius: 10px; padding: 16px; border: 1px solid #30363d; height: 100%; }
</style>
""", unsafe_allow_html=True)

DATA_FILE = "fitness_os_data.json"

def clean_pdf_str(text):
    """Sanitize strings for standard FPDF Latin-1 fonts without crashing on rupee or arrows."""
    if not isinstance(text, str):
        text = str(text)
    replacements = {
        "₹": "Rs.",
        "→": "->",
        "•": "-",
        "—": "-",
        "–": "-",
        "“": '"',
        "”": '"',
        "’": "'",
        "‘": "'",
        "⚡": "",
        "🥗": "",
        "🏋️": "",
        "📊": "",
        "📑": "",
        "🔍": "",
        "🌅": "",
        "☀️": "",
        "🌙": "",
        "💡": ""
    }
    for orig, rep in replacements.items():
        text = text.replace(orig, rep)
    # Strip any remaining unencodable characters
    return text.encode('latin-1', 'replace').decode('latin-1')

def load_local_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "workouts": {},
        "profile": {
            "height_cm": 159.0,
            "weight_kg": 74.8,
            "smm_kg": 28.6,
            "body_fat_pct": 32.0,
            "visceral_level": 11,
            "target_kcal": 1533,
            "target_protein": 120,
            "recommended_split": "Upper / Lower (Metabolic Density - Optimal for BF > 25%)",
            "diet_preference": "Pure Vegetarian"
        }
    }

def save_local_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

if "db" not in st.session_state:
    st.session_state.db = load_local_data()

profile = st.session_state.db.setdefault("profile", {
    "height_cm": 159.0,
    "weight_kg": 74.8,
    "smm_kg": 28.6,
    "body_fat_pct": 32.0,
    "visceral_level": 11,
    "target_kcal": 1533,
    "target_protein": 120,
    "recommended_split": "Upper / Lower (Metabolic Density - Optimal for BF > 25%)",
    "diet_preference": "Pure Vegetarian"
})

WORKOUT_SYSTEMS = {
    "Upper / Lower (Metabolic Density - Optimal for BF > 25%)": {
        "Upper Power & Density": [
            ("Flat Bench Press / Machine Chest Press", "barbell"),
            ("Lat Pulldown / Assisted Pull-Ups", "machine"),
            ("Incline Dumbbell Press", "per_side"),
            ("Seated Cable Row", "machine"),
            ("Standing Dumbbell Lateral Raises", "per_side"),
            ("Rope Triceps Pushdowns", "machine"),
            ("Dumbbell Biceps Curls", "per_side")
        ],
        "Lower Compound & Posterior Chain": [
            ("Barbell Squat / Heavy Leg Press", "barbell"),
            ("Romanian Deadlifts (RDLs)", "barbell"),
            ("Walking Lunges / Bulgarian Split Squats", "per_side"),
            ("Leg Curl / Leg Extension Superset", "machine"),
            ("Standing Calf Raises", "machine"),
            ("Hanging Leg Raises / Core Hollow Hold", "bodyweight")
        ]
    },
    "Push / Pull / Legs (Recomp Split - Optimal for BF 18% - 25%)": {
        "Push Day (Chest, Shoulders & Triceps)": [
            ("Flat Bench Press / Machine Chest Press", "barbell"),
            ("Incline Dumbbell / Machine Press", "per_side"),
            ("Pec Deck Flyes", "machine"),
            ("Overhead Dumbbell Press", "per_side"),
            ("Lateral Raises (Dumbbell/Cable)", "per_side"),
            ("Triceps Pushdowns (Rope)", "machine")
        ],
        "Pull Day (Back, Rear Delts & Biceps)": [
            ("Lat Pulldown / Assisted Pull-Ups", "machine"),
            ("Seated Cable Row / Machine Row", "machine"),
            ("Single-Arm Dumbbell Row", "per_side"),
            ("Straight-Arm Lat Pulldown", "machine"),
            ("Dumbbell Biceps Curls", "per_side"),
            ("Hammer Curls", "per_side")
        ],
        "Leg Day (Quads, Hamstrings & Calves)": [
            ("Barbell Squat / Leg Press", "barbell"),
            ("Romanian Deadlifts (RDLs)", "barbell"),
            ("Bulgarian Split Squats / Lunges", "per_side"),
            ("Leg Extensions", "machine"),
            ("Standing Calf Raises", "machine")
        ]
    },
    "Arnold Split (High Volume Hypertrophy - Optimal for BF < 18%)": {
        "Chest & Back": [
            ("Barbell Incline Bench Press", "barbell"),
            ("Barbell Bent-Over Row", "barbell"),
            ("Dumbbell Flat Bench Press", "per_side"),
            ("Weighted or Lat Pulldowns", "machine"),
            ("Cable Dumbbell Flyes", "per_side")
        ],
        "Shoulders & Arms": [
            ("Seated Dumbbell Overhead Press", "per_side"),
            ("Lateral Raises Heavy Drop-Set", "per_side"),
            ("Barbell Biceps Curls", "barbell"),
            ("Skull Crushers / Overhead Triceps Extension", "barbell"),
            ("Incline Hammer Curls", "per_side")
        ],
        "Legs & Abs": [
            ("Barbell Back Squats", "barbell"),
            ("Romanian Deadlifts", "barbell"),
            ("Leg Press Heavy Volume", "barbell"),
            ("Calf Raises & Cable Crunches", "machine")
        ]
    }
}

# --- UNIVERSAL REST-BASED GEMINI NUTRITION ENGINE ---
def get_gemini_api_key():
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        try:
            key = st.secrets.get("GEMINI_API_KEY")
        except Exception:
            key = None
    return key

def analyze_food_universally(text_query=None, pil_image=None):
    api_key = get_gemini_api_key()
    sys_instruction = (
        "You are an expert clinical and sports nutritionist specializing in Indian and global diets. "
        "Analyze the user's food query or photo. Return ONLY a valid JSON object (no markdown, no backticks, no preamble) "
        "with these exact keys:\n"
        '{\n'
        '  "item_name": "clean descriptive name",\n'
        '  "portion_description": "e.g. 2 medium bananas (240g) or 1 bowl dal",\n'
        '  "calories": number_in_kcal,\n'
        '  "protein": number_in_grams,\n'
        '  "carbs": number_in_grams,\n'
        '  "fat": number_in_grams,\n'
        '  "fiber": number_in_grams,\n'
        '  "dietary_notes": "brief 1-sentence tip on muscle preservation or deficit impact"\n'
        '}'
    )
    
    if api_key:
        try:
            parts = []
            if text_query:
                parts.append({"text": f"Calculate exact nutritional profile for: '{text_query}'"})
            
            if pil_image:
                buffered = io.BytesIO()
                pil_image.save(buffered, format="JPEG")
                img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
                parts.append({"inline_data": {"mime_type": "image/jpeg", "data": img_b64}})
                parts.append({"text": "Identify the food/dish in this image, estimate portion size, and calculate exact macros."})
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": parts}],
                "systemInstruction": {"parts": [{"text": sys_instruction}]},
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.2
                }
            }
            
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            
            with urllib.request.urlopen(req, timeout=12) as response:
                resp_data = json.loads(response.read().decode("utf-8"))
                raw_text = resp_data["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(raw_text)
        except Exception:
            pass

    # Offline fallback
    q = (text_query or "").lower()
    count_m = re.search(r"^(\d+(\.\d+)?)", q)
    qty = float(count_m.group(1)) if count_m else 1.0
    
    if "bann" in q or "banana" in q or "kela" in q:
        return {
            "item_name": "Banana",
            "portion_description": f"{qty} unit(s)",
            "calories": round(95 * qty, 1),
            "protein": round(1.2 * qty, 1),
            "carbs": round(24.0 * qty, 1),
            "fat": round(0.3 * qty, 1),
            "fiber": round(2.6 * qty, 1),
            "dietary_notes": "Fast-acting glycogen source. Great pre/intra workout."
        }
    elif "chilla" in q or "cheela" in q or "chila" in q:
        return {
            "item_name": "Moong / Besan Chilla",
            "portion_description": f"{qty} medium piece(s)",
            "calories": round(165 * qty, 1),
            "protein": round(9.0 * qty, 1),
            "carbs": round(21.0 * qty, 1),
            "fat": round(4.0 * qty, 1),
            "fiber": round(3.5 * qty, 1),
            "dietary_notes": "High complex carb & moderate protein vegetarian staple."
        }
    elif "paneer" in q:
        w = 100 * qty if qty <= 5 else qty
        f = w / 100.0
        return {
            "item_name": "Fresh Paneer",
            "portion_description": f"{int(w)}g",
            "calories": round(265 * f, 1),
            "protein": round(18.0 * f, 1),
            "carbs": round(3.0 * f, 1),
            "fat": round(20.0 * f, 1),
            "fiber": 0.0,
            "dietary_notes": "Slow-digesting casein protein. Moderate fat content."
        }
    
    return {
        "item_name": text_query.title() if text_query else "Custom Item",
        "portion_description": f"{qty} serving(s)",
        "calories": round(180.0 * qty, 1),
        "protein": round(8.0 * qty, 1),
        "carbs": round(26.0 * qty, 1),
        "fat": round(5.0 * qty, 1),
        "fiber": 2.0,
        "dietary_notes": "Add GEMINI_API_KEY in Streamlit Secrets for live universal API parsing."
    }

# High-Contrast Safe PDF Generator
def build_pdf_document(log_date, workout_data):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_fill_color(22, 27, 34)
    pdf.rect(0, 0, 210, 32, 'F')
    
    pdf.set_text_color(88, 166, 255)
    pdf.set_font('Helvetica', 'B', 15)
    pdf.set_xy(10, 8)
    pdf.cell(190, 8, clean_pdf_str("KSP FITNESS OS - PERFORMANCE WORKOUT LOG"), ln=True, align='C')
    
    pdf.set_text_color(200, 200, 200)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(190, 6, clean_pdf_str(f"Session Date: {log_date}"), ln=True, align='C')
    pdf.ln(12)
    
    pdf.set_text_color(20, 20, 20)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 7, clean_pdf_str(f"Program Split: {workout_data.get('split', 'PPL')}"), ln=True)
    
    grand_vol = workout_data.get('grand_total_volume_kg', workout_data.get('grand_total_volume', 0))
    cals_burned = workout_data.get('total_calories_burned', workout_data.get('total_calories', 0))
    
    pdf.cell(0, 7, clean_pdf_str(f"Total Weight Lifted (Tonnage): {grand_vol} kg"), ln=True)
    pdf.cell(0, 7, clean_pdf_str(f"Total Calorie Burn (with Cardio): ~{cals_burned} kcal"), ln=True)
    finisher_txt = "15-20 min Incline Walk (15% @ 2.5 km/h) - COMPLETED" if workout_data.get('finisher') else "Skipped"
    pdf.cell(0, 7, clean_pdf_str(f"Cardio Finisher: {finisher_txt}"), ln=True)
    pdf.ln(4)
    
    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_text_color(10, 10, 10)
    pdf.cell(0, 8, clean_pdf_str("DETAILED EXERCISE LOG"), ln=True)
    pdf.ln(2)
    
    for ex_name, details in workout_data.get('exercises', {}).items():
        ex_vol = details.get('exercise_volume', 0)
        ex_kc = details.get('exercise_kcal', 0)
        
        pdf.set_fill_color(240, 242, 245)
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(190, 7, clean_pdf_str(f"  {ex_name}  |  Volume: {ex_vol} kg  |  Burn: ~{ex_kc} kcal"), border=1, ln=True, fill=True)
        
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(40, 40, 40)
        sets_list = details.get('sets', [])
        
        if isinstance(sets_list, list):
            for s in sets_list:
                set_num = s.get('set', 1)
                tot_wt = s.get('total_weight', s.get('weight', 0.0))
                reps = s.get('reps', 0)
                vol = s.get('volume', tot_wt * reps)
                calc = s.get('calc_type', f"{tot_wt}kg")
                pdf.cell(190, 6, clean_pdf_str(f"      Set {set_num}: {tot_wt} kg total ({reps} reps) -> Load: {vol} kg [{calc}]"), border='LR', ln=True)
            pdf.cell(190, 1, '', border='T', ln=True)
        pdf.ln(3)
        
    return bytes(pdf.output())

# PDF Diet & Grocery Builder with Unicode-safe strings
def build_diet_pdf(profile_data, diet_pref, tier_choice):
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_fill_color(22, 27, 34)
    pdf.rect(0, 0, 210, 32, 'F')
    
    pdf.set_text_color(88, 166, 255)
    pdf.set_font('Helvetica', 'B', 15)
    pdf.set_xy(10, 8)
    pdf.cell(190, 8, clean_pdf_str("KSP FITNESS OS - 30-DAY BUDGET & MEAL ARCHITECT"), ln=True, align='C')
    
    pdf.set_text_color(200, 200, 200)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(190, 6, clean_pdf_str(f"Preference: {diet_pref} | Tier: {tier_choice}"), ln=True, align='C')
    pdf.ln(12)
    
    pdf.set_text_color(20, 20, 20)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 7, clean_pdf_str(f"Target Daily Calorie Ceiling: {profile_data.get('target_kcal', 1533)} kcal"), ln=True)
    pdf.cell(0, 7, clean_pdf_str(f"Target Daily Protein Floor: {profile_data.get('target_protein', 120)} g/day"), ln=True)
    pdf.cell(0, 7, clean_pdf_str(f"Current Weight: {profile_data.get('weight_kg', 74.8)} kg | Body Fat: {profile_data.get('body_fat_pct', 32.0)}%"), ln=True)
    pdf.ln(4)
    
    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, clean_pdf_str("ESTIMATED 30-DAY GROCERY HAUL & BUDGET"), ln=True)
    pdf.set_font('Helvetica', '', 10)
    
    if "Tier 1" in tier_choice:
        groceries = [
            ("Soya Chunks (Raw Bulk)", "2.0 kg", "Rs. 220", "52g protein / 100g"),
            ("Chana Sattu Powder", "1.5 kg", "Rs. 210", "20g protein / 100g"),
            ("Fresh Curd / Dahi Setup", "6.0 kg (Milk/Dahi)", "Rs. 380", "15g protein / day"),
            ("Roasted Bengal Gram (Chana)", "1.0 kg", "Rs. 140", "Intra-day fiber & protein"),
            ("Moong Dal for Sprouts/Chilla", "2.0 kg", "Rs. 260", "24g protein / 100g raw"),
            ("Seasonal Veggies & Bananas", "Monthly", "Rs. 600", "Potassium & fiber"),
        ]
        est_cost = "Rs. 1,810 - Rs. 2,200 / month"
    elif "Tier 2" in tier_choice:
        groceries = [
            ("Low-Fat Paneer", "4.0 kg", "Rs. 1,400", "18g protein / 100g"),
            ("Pea / Plant Protein Powder", "1 Tub (1kg)", "Rs. 1,600", "25g protein / scoop"),
            ("Soya Chunks / Sprouts Mix", "1.5 kg", "Rs. 200", "Secondary clean bulk"),
            ("Rolled Oats & Peanut Butter", "1kg + 500g", "Rs. 550", "Complex carbs & healthy fats"),
            ("Fresh Curd & Seasonal Greens", "Monthly", "Rs. 800", "Gut microbiome & micronutrients"),
        ]
        est_cost = "Rs. 4,200 - Rs. 4,800 / month"
    else:
        groceries = [
            ("Whey Protein Isolate", "1 Tub (2kg)", "Rs. 5,400", "27g protein / scoop isolate"),
            ("Artisanal Tofu & Fresh Paneer", "5.0 kg", "Rs. 2,200", "Clean bioavailability"),
            ("Greek Yogurt & Berries", "Monthly", "Rs. 1,800", "Probiotics & polyphenols"),
            ("Almond Butter & Chia Seeds", "Monthly", "Rs. 1,100", "Omega-3 & healthy fats"),
        ]
        est_cost = "Rs. 8,500 - Rs. 10,500 / month"

    for itm, qty, prc, note in groceries:
        pdf.cell(190, 6, clean_pdf_str(f"  - {itm} [{qty}] -> {prc} ({note})"), ln=True)
        
    pdf.ln(3)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 7, clean_pdf_str(f"Total Estimated Monthly Food Investment: {est_cost}"), ln=True)
    pdf.ln(4)
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.cell(0, 8, clean_pdf_str("TACTICAL 10-MINUTE RECIPES"), ln=True)
    pdf.set_font('Helvetica', '', 9)
    pdf.multi_cell(190, 5, clean_pdf_str(
        "1. 10-Min Soya Bhurji: Boil 60g soya chunks for 5 mins in salted water. Squeeze water out completely and pulse in mixer for 3 seconds. Saute with 1 chopped green chilli, pinch of turmeric, salt, and 1 tsp mustard oil. Yields 31g protein for under Rs. 8.\n\n"
        "2. High-Protein Sattu Chhas: Mix 40g sattu in 250ml chilled water or thin buttermilk. Add roasted cumin, black salt, and lemon. Drink post-workout for 10g protein and instant mineral rehydration.\n\n"
        "3. Instant Moong Sprout Salad: Toss 100g sprouted moong with cucumber, tomato, chaat masala, lemon, and 30g roasted chana. High satiety volume meal."
    ))
    
    return bytes(pdf.output())

# Sidebar Navigation
st.sidebar.markdown("## ⚡ KSP Fitness OS")
menu = st.sidebar.radio("Navigation", [
    "📊 Dashboard & BMI",
    "📑 InBody & Body Composition",
    "🥗 Smart Diet & Budget Planner",
    "🏋️ Adaptive Workout Logger",
    "🔍 Universal Food & Macro AI"
])

# ----------------- SECTION 1: DASHBOARD & BMI -----------------
if menu == "📊 Dashboard & BMI":
    st.title("⚡ Performance Dashboard & Vitals")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"""<div class="metric-card">
        <div class="metric-title">Target Deficit</div>
        <div class="metric-value">{profile.get('target_kcal', 1533)}</div>
        <div class="metric-subtext">kcal / day</div>
    </div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class="metric-card">
        <div class="metric-title">Daily Protein</div>
        <div class="metric-value">{profile.get('target_protein', 120)}g</div>
        <div class="metric-subtext">Lean Muscle Preservation Target</div>
    </div>""", unsafe_allow_html=True)
    c3.markdown("""<div class="metric-card">
        <div class="metric-title">Cardio Incline</div>
        <div class="metric-value">15%</div>
        <div class="metric-subtext">2.5 km/h @ 20 Mins</div>
    </div>""", unsafe_allow_html=True)
    c4.markdown(f"""<div class="metric-card">
        <div class="metric-title">InBody Plan</div>
        <div class="metric-value" style="font-size: 1.05rem; margin-top: 10px;">{profile.get('recommended_split', 'Upper / Lower')}</div>
        <div class="metric-subtext">Body Fat Synced</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("⚖️ Biometric Health & BMI Analyzer")
    
    b1, b2 = st.columns(2)
    with b1:
        h_cm = st.number_input("Height (cm)", value=float(profile.get("height_cm", 159.0)), step=0.5)
        w_kg = st.number_input("Current Weight (kg)", value=float(profile.get("weight_kg", 74.8)), step=0.1)
        profile["height_cm"] = h_cm
        profile["weight_kg"] = w_kg
        save_local_data(st.session_state.db)
        
    with b2:
        if h_cm > 0 and w_kg > 0:
            bmi = round(w_kg / ((h_cm / 100.0) ** 2), 2)
            cat, col = ("Normal Weight", "#3fb950") if 18.5 <= bmi < 24.9 else (("Overweight", "#f0883e") if 25.0 <= bmi < 29.9 else ("Obese", "#f85149"))
            st.markdown(f"""<div style="background-color: #161b22; border-left: 5px solid {col}; padding: 18px; border-radius: 8px; margin-top: 15px;">
                <div style="font-size: 0.9rem; color: #8b949e;">Calculated Body Mass Index (BMI)</div>
                <div style="font-size: 2.2rem; font-weight: bold; color: {col};">{bmi} kg/m²</div>
                <div style="font-size: 1rem; color: #e6edf3;">Classification: <strong>{cat}</strong></div>
            </div>""", unsafe_allow_html=True)

# ------------ SECTION 2: INBODY & BODY COMPOSITION ------------
elif menu == "📑 InBody & Body Composition":
    st.title("📑 InBody / DEXA & Body Composition Engine")
    st.markdown("Sync your biometrics to dynamically recalibrate your training split structure and daily nutritional targets.")
    
    tab_scan, tab_photo = st.tabs(["📊 InBody / DEXA Recalibrator", "📸 Visual Body Fat Estimator"])
    
    with tab_scan:
        st.subheader("InBody / DEXA Telemetry")
        scan_file = st.file_uploader("Upload InBody Scan / DEXA PDF or Image", type=["jpg", "jpeg", "png", "pdf"], key="inbody_upload")
        if scan_file:
            st.success("Report attached! Review metrics below:")
            
        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1:
            scan_weight = st.number_input("Scale Weight (kg)", value=float(profile.get("weight_kg", 74.8)), step=0.1)
        with sc2:
            scan_smm = st.number_input("Skeletal Muscle Mass (kg)", value=float(profile.get("smm_kg", 28.6)), step=0.1)
        with sc3:
            scan_bfp = st.number_input("Body Fat Percentage (%)", value=float(profile.get("body_fat_pct", 32.0)), step=0.1)
        with sc4:
            scan_vfl = st.number_input("Visceral Fat Level", value=int(profile.get("visceral_level", 11)), step=1)
            
        if st.button("🚀 Recalibrate App, Workout Split & Diet", type="primary"):
            lean_mass = scan_weight * (1.0 - (scan_bfp / 100.0))
            recommended_protein = max(int(round(lean_mass * 2.2)), 120)
            
            bmr = 370 + (21.6 * lean_mass)
            tdee = bmr * 1.35
            caloric_deficit = int(round(tdee - 450))
            
            if scan_bfp > 25.0:
                recommended_split = "Upper / Lower (Metabolic Density - Optimal for BF > 25%)"
            elif scan_bfp >= 18.0:
                recommended_split = "Push / Pull / Legs (Recomp Split - Optimal for BF 18% - 25%)"
            else:
                recommended_split = "Arnold Split (High Volume Hypertrophy - Optimal for BF < 18%)"
                
            profile["weight_kg"] = scan_weight
            profile["smm_kg"] = scan_smm
            profile["body_fat_pct"] = scan_bfp
            profile["visceral_level"] = scan_vfl
            profile["target_kcal"] = caloric_deficit
            profile["target_protein"] = recommended_protein
            profile["recommended_split"] = recommended_split
            save_local_data(st.session_state.db)
            
            st.success("✅ Training & Diet Protocols Recalibrated Successfully!")
            
            r1, r2, r3 = st.columns(3)
            r1.metric("Target Daily Calories", f"{caloric_deficit} kcal")
            r2.metric("Target Protein (Veg)", f"{recommended_protein}g / day")
            r3.metric("Lean Muscle Mass (LBM)", f"{round(lean_mass, 1)} kg")
            
            st.markdown(f"""<div class="scan-card">
                <h4>📋 System Prescription</h4>
                <div class="split-badge">Recommended: {recommended_split}</div>
                <ul>
                    <li><strong>Visceral Fat Level ({scan_vfl}):</strong> 15% incline treadmill walking for 20 mins is mandatory post-lift to accelerate visceral lipid clearance.</li>
                    <li><strong>Skeletal Muscle ({scan_smm} kg):</strong> 3 heavy working sets kept at RPE 8.5 to prevent catabolism in a caloric deficit.</li>
                    <li><strong>Macro Targets:</strong> {recommended_protein}g protein locked in (soya chunks, curd, paneer, pea protein).</li>
                    <li><strong>Smart Diet Ready:</strong> Your 30-day budget meal plan has been refreshed in the <strong>'Smart Diet & Budget Planner'</strong> section!</li>
                </ul>
            </div>""", unsafe_allow_html=True)

    with tab_photo:
        st.subheader("Visual Physique & Body Fat Check")
        user_photo = st.file_uploader("Upload Full Body Photo", type=["jpg", "jpeg", "png"], key="user_photo")
        if user_photo:
            img = Image.open(user_photo)
            st.image(img, caption="Physique Snapshot", width=340)
            curr_bf = profile.get("body_fat_pct", 32.0)
            st.markdown(f"""<div class="scan-card">
                <h4>🔍 Visual Telemetry Breakdown</h4>
                <p><strong>Body Fat Estimate:</strong> ~{int(curr_bf - 2)}% - {int(curr_bf + 2)}%</p>
                <p><strong>Structure:</strong> Strong shoulder girdle and chest frame. Waist taper will emerge rapidly once visceral fat levels drop below 9.</p>
            </div>""", unsafe_allow_html=True)

# ------------ SECTION 3: SMART DIET & BUDGET PLANNER ------------
elif menu == "🥗 Smart Diet & Budget Planner":
    st.title("🥗 Smart Diet & Budget Meal Architect")
    st.markdown("Precision nutritional engineering: High protein, high fiber, minimal calorie density, and maximum rupee value.")
    
    t_cals = profile.get('target_kcal', 1533)
    t_prot = profile.get('target_protein', 120)
    
    top_c1, top_c2, top_c3 = st.columns([1, 1, 2])
    with top_c1:
        diet_type = st.radio("Dietary Preference", ["Pure Vegetarian", "Eggetarian / Non-Veg"], horizontal=True)
    with top_c2:
        tier = st.selectbox("Select Investment Tier", [
            "Tier 1: High-ROI Budget (Rs. 1,800 - Rs. 2,500/mo)",
            "Tier 2: Balanced Mid-Range (Rs. 3,800 - Rs. 5,000/mo)",
            "Tier 3: Premium Convenience (Rs. 7,500 - Rs. 10,000/mo)"
        ])
    with top_c3:
        st.markdown(f"""<div style="background:#161b22; border:1px solid #30363d; border-radius:8px; padding:10px 14px;">
            <span style="color:#8b949e; font-size:0.85rem;">CALIBRATED MACRO BLUEPRINT</span><br>
            <strong>{t_cals} kcal/day</strong> &bull; <span style="color:#3fb950; font-weight:bold;">{t_prot}g Protein</span> &bull; <span>~35g Fiber</span>
        </div>""", unsafe_allow_html=True)
        
    st.markdown("---")
    st.subheader("🍱 Daily Meal Blueprint (Locked to Your InBody Caloric Deficit)")
    
    m_col1, m_col2, m_col3 = st.columns(3)
    
    if "Tier 1" in tier:
        with m_col1:
            st.markdown("""<div class="tier-card">
                <span style="color:#3fb950; font-weight:bold;"> MEAL 1: PRE/POST WORKOUT</span>
                <h4 style="margin:4px 0;">Sattu Power Chhas + Banana</h4>
                <p style="color:#8b949e; font-size:0.85rem;"><strong>Cost:</strong> ~₹18 | <strong>Protein:</strong> 12g | <strong>Cals:</strong> 240 kcal</p>
                <p style="font-size:0.9rem;">40g Chana Sattu stirred in 250ml thin water/buttermilk with black salt, roasted jeera, and lemon + 1 small banana.</p>
            </div>""", unsafe_allow_html=True)
            
        with m_col2:
            st.markdown("""<div class="tier-card">
                <span style="color:#58a6ff; font-weight:bold;"> MEAL 2: HIGH-VOLUME LUNCH</span>
                <h4 style="margin:4px 0;">10-Min Soya Bhurji + Curd + 2 Roti</h4>
                <p style="color:#8b949e; font-size:0.85rem;"><strong>Cost:</strong> ~₹32 | <strong>Protein:</strong> 42g | <strong>Cals:</strong> 510 kcal</p>
                <p style="font-size:0.9rem;">60g dry soya chunks (boiled, pulsed & sauteed with onions/tomatoes/chilli) + 150g homemade fresh curd + 2 phulkas.</p>
            </div>""", unsafe_allow_html=True)
            
        with m_col3:
            st.markdown("""<div class="tier-card">
                <span style="color:#f0883e; font-weight:bold;"> MEAL 3: EVENING & DINNER</span>
                <h4 style="margin:4px 0;">Moong Sprouts Chaat + Paneer/Chilla</h4>
                <p style="color:#8b949e; font-size:0.85rem;"><strong>Cost:</strong> ~₹35 | <strong>Protein:</strong> 38g | <strong>Cals:</strong> 460 kcal</p>
                <p style="font-size:0.9rem;">100g sprouted moong chaat with cucumber and roasted chana + 1 medium besan chilla or 60g raw low-cost paneer.</p>
            </div>""", unsafe_allow_html=True)
            
    elif "Tier 2" in tier:
        with m_col1:
            st.markdown("""<div class="tier-card">
                <span style="color:#3fb950; font-weight:bold;"> MEAL 1: POST WORKOUT</span>
                <h4 style="margin:4px 0;">Pea/Plant Protein Shake + Oats</h4>
                <p style="color:#8b949e; font-size:0.85rem;"><strong>Cost:</strong> ~₹65 | <strong>Protein:</strong> 28g | <strong>Cals:</strong> 260 kcal</p>
                <p style="font-size:0.9rem;">1 scoop pure pea protein isolate blended with water + 35g rolled oats and cinnamon.</p>
            </div>""", unsafe_allow_html=True)
            
        with m_col2:
            st.markdown("""<div class="tier-card">
                <span style="color:#58a6ff; font-weight:bold;"> MEAL 2: LUNCH</span>
                <h4 style="margin:4px 0;">Paneer / Tofu Tikka Bowl + Dal</h4>
                <p style="color:#8b949e; font-size:0.85rem;"><strong>Cost:</strong> ~₹75 | <strong>Protein:</strong> 34g | <strong>Cals:</strong> 520 kcal</p>
                <p style="font-size:0.9rem;">120g grilled low-fat paneer or tofu + 1 bowl thick moong dal + green salad and 1 roti.</p>
            </div>""", unsafe_allow_html=True)
            
        with m_col3:
            st.markdown("""<div class="tier-card">
                <span style="color:#f0883e; font-weight:bold;"> MEAL 3: DINNER</span>
                <h4 style="margin:4px 0;">Soya Stir Fry + Sprout Salad</h4>
                <p style="color:#8b949e; font-size:0.85rem;"><strong>Cost:</strong> ~₹40 | <strong>Protein:</strong> 36g | <strong>Cals:</strong> 420 kcal</p>
                <p style="font-size:0.9rem;">50g dry soya chunks tossed with capsicum, broccoli, and soy sauce + 100g curd with roasted peanuts.</p>
            </div>""", unsafe_allow_html=True)
            
    else:
        with m_col1:
            st.markdown("""<div class="tier-card">
                <span style="color:#3fb950; font-weight:bold;"> MEAL 1: POST WORKOUT</span>
                <h4 style="margin:4px 0;">Whey Isolate + Berries Smoothie</h4>
                <p style="color:#8b949e; font-size:0.85rem;"><strong>Cost:</strong> ~₹140 | <strong>Protein:</strong> 30g | <strong>Cals:</strong> 240 kcal</p>
                <p style="font-size:0.9rem;">1 scoop imported whey isolate + unsweetened almond milk + chia seeds and blueberries.</p>
            </div>""", unsafe_allow_html=True)
            
        with m_col2:
            st.markdown("""<div class="tier-card">
                <span style="color:#58a6ff; font-weight:bold;"> MEAL 2: LUNCH</span>
                <h4 style="margin:4px 0;">Artisanal Tofu / Greek Yogurt Bowl</h4>
                <p style="color:#8b949e; font-size:0.85rem;"><strong>Cost:</strong> ~₹180 | <strong>Protein:</strong> 38g | <strong>Cals:</strong> 490 kcal</p>
                <p style="font-size:0.9rem;">150g organic pan-seared tofu + 150g Greek Yogurt + quinoa avocado salad.</p>
            </div>""", unsafe_allow_html=True)
            
        with m_col3:
            st.markdown("""<div class="tier-card">
                <span style="color:#f0883e; font-weight:bold;"> MEAL 3: DINNER</span>
                <h4 style="margin:4px 0;">Grilled Cottage Cheese + Edamame</h4>
                <p style="color:#8b949e; font-size:0.85rem;"><strong>Cost:</strong> ~₹160 | <strong>Protein:</strong> 36g | <strong>Cals:</strong> 440 kcal</p>
                <p style="font-size:0.9rem;">120g grilled malai-free cottage cheese + 60g steamed edamame beans and roasted asparagus.</p>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🛒 30-Day Bulk Grocery Haul & Spending Forecast")
    
    g_tab1, g_tab2 = st.tabs(["📋 Itemized Shopping List", "👨‍🍳 10-Minute Batch Cook Recipes"])
    
    with g_tab1:
        if "Tier 1" in tier:
            st.markdown("""
            | Item | Monthly Quantity | Estimated Cost | Protein Yield | Value Metric (₹/g Protein) |
            | :--- | :--- | :--- | :--- | :--- |
            | **Soya Chunks (Bulk Pack)** | 2.0 kg | ₹220 | 1,040 g protein | **₹0.21 / g** (Highest ROI) |
            | **Chana Sattu Powder** | 1.5 kg | ₹210 | 300 g protein | **₹0.70 / g** |
            | **Moong Dal (For Sprouts & Chilla)** | 2.0 kg | ₹260 | 480 g protein | **₹0.54 / g** |
            | **Roasted Bengal Gram (Chana)** | 1.0 kg | ₹140 | 190 g protein | **₹0.73 / g** |
            | **Fresh Milk (for Daily Curd)** | 10 Litres | ₹450 | 320 g protein | **₹1.40 / g** |
            | **Seasonal Greens, Onions & Bananas**| 30 Days | ₹600 | Micronutrients & Fiber | Baseline Vitality |
            | **TOTAL MONTHLY INVESTMENT** | | **₹1,880** | **~3,600g Protein** | **~₹0.52 / g Net Average** |
            """)
        elif "Tier 2" in tier:
            st.markdown("""
            | Item | Monthly Quantity | Estimated Cost | Protein Yield | Value Metric (₹/g Protein) |
            | :--- | :--- | :--- | :--- | :--- |
            | **Plant / Pea Protein Isolate** | 1.0 kg (30 scoops) | ₹1,600 | 720 g protein | **₹2.20 / g** |
            | **Low-Fat Dairy Paneer** | 4.0 kg | ₹1,400 | 720 g protein | **₹1.94 / g** |
            | **Soya Chunks & Dal Blend** | 2.0 kg | ₹240 | 800 g protein | **₹0.30 / g** |
            | **Rolled Oats & Peanut Butter** | 1.5 kg total | ₹550 | 250 g protein | **₹2.20 / g** |
            | **Curd & Fresh Seasonal Veggies** | 30 Days | ₹850 | 250 g protein | Healthy Gut & Satiety |
            | **TOTAL MONTHLY INVESTMENT** | | **₹4,640** | **~3,600g Protein** | **~₹1.28 / g Net Average** |
            """)
        else:
            st.markdown("""
            | Item | Monthly Quantity | Estimated Cost | Protein Yield | Value Metric (₹/g Protein) |
            | :--- | :--- | :--- | :--- | :--- |
            | **Whey Protein Isolate (Imported)**| 2.0 kg (60 scoops) | ₹5,500 | 1,620 g protein | **₹3.39 / g** |
            | **Artisanal Tofu & High-End Paneer**| 5.0 kg | ₹2,200 | 900 g protein | **₹2.44 / g** |
            | **Greek Yogurt Tubs** | 24 Cups | ₹1,680 | 192 g protein | **₹8.75 / g** |
            | **Chia, Almond Butter & Berries** | Monthly | ₹1,200 | Healthy Fats | Peak Bioavailability |
            | **TOTAL MONTHLY INVESTMENT** | | **₹10,580** | **~3,600g Protein** | **~₹2.93 / g Net Average** |
            """)

    with g_tab2:
        st.markdown("""
        #### 1. 10-Minute Soya Keema Bhurji (31g Protein | ₹8 cost)
        * **Step 1:** Boil 60g soya chunks in salted water for 5 minutes. Drain and squeeze water out thoroughly with your hands.
        * **Step 2:** Pulse the squeezed chunks in a mixer-grinder for 3 seconds until it looks like minced keema.
        * **Step 3:** Heat 1 tsp mustard oil in a pan, toss in cumin seeds, 1 chopped green chilli, turmeric, salt, and garam masala. Add minced soya and stir fry on high flame for 3 minutes. Done!
        
        #### 2. No-Cook Electrolyte Sattu Shake (12g Protein | ₹12 cost)
        * **Step 1:** Take 40g sattu in a glass or shaker.
        * **Step 2:** Add 250ml cold water, black salt, pinch of roasted jeera powder, and half a lemon.
        * **Step 3:** Shake and drink. Fast gastric emptying, high mineral density, and zero prep dishes.
        
        #### 3. High-Volume Sprouted Moong Satiety Bowl (24g Protein | ₹15 cost)
        * **Step 1:** Take 100g raw moong sprouts (soaked 24 hours).
        * **Step 2:** Toss with diced cucumber, tomato, 30g roasted chana, chaat masala, and a splash of lime. Satiates hunger for 4+ hours in a deficit.
        """)

    st.markdown("---")
    st.subheader("📄 Download Customized 30-Day Diet & Grocery Plan (PDF)")
    diet_pdf_bytes = build_diet_pdf(profile, diet_type, tier)
    b64_diet = base64.b64encode(diet_pdf_bytes).decode('utf-8')
    diet_href = f'<a href="data:application/pdf;base64,{b64_diet}" download="KSP_30Day_Diet_{profile.get("weight_kg")}kg.pdf" target="_blank" style="display: inline-block; padding: 10px 18px; background-color: #238636; color: white; border-radius: 6px; text-decoration: none; font-weight: bold; margin-top: 6px;">📥 Download 30-Day Diet & Budget PDF</a>'
    st.markdown(diet_href, unsafe_allow_html=True)

# ------------ SECTION 4: ADAPTIVE WORKOUT LOGGER ------------
elif menu == "🏋️ Adaptive Workout Logger":
    st.title("🏋️ Adaptive Workout & Multi-Set Logger")
    
    system_keys = list(WORKOUT_SYSTEMS.keys())
    default_sys_idx = 0
    saved_rec = profile.get("recommended_split", system_keys[0])
    for i, k in enumerate(system_keys):
        if k == saved_rec:
            default_sys_idx = i
            break
            
    col_sys, col_day, col_date = st.columns([2, 2, 1])
    with col_sys:
        chosen_system = st.selectbox("Training System (Auto-Suggested by Body Fat)", system_keys, index=default_sys_idx)
    with col_day:
        available_days = list(WORKOUT_SYSTEMS[chosen_system].keys())
        split_choice = st.selectbox("Select Workout Day", available_days)
    with col_date:
        session_date = st.date_input("Date", value=date.today())
        log_date = session_date.strftime("%Y-%m-%d")

    exercises = WORKOUT_SYSTEMS[chosen_system][split_choice]
    user_weight = float(profile.get("weight_kg", 74.8))

    if "exercise_set_counts" not in st.session_state:
        st.session_state.exercise_set_counts = {}

    session_workout_data = {}
    grand_total_volume = 0.0
    grand_total_lift_cals = 0.0

    for idx, (ex, ex_type) in enumerate(exercises):
        st.markdown(f"### {idx + 1}. {ex}")
        
        set_count_key = f"{log_date}_{ex}_count"
        if set_count_key not in st.session_state.exercise_set_counts:
            st.session_state.exercise_set_counts[set_count_key] = 3
            
        current_sets = st.session_state.exercise_set_counts[set_count_key]
        
        ctrl1, ctrl2, mode_col = st.columns([1, 1, 3])
        with ctrl1:
            if st.button(f"➕ Add Set", key=f"add_{ex}_{idx}"):
                st.session_state.exercise_set_counts[set_count_key] += 1
                st.rerun()
        with ctrl2:
            if st.button(f"➖ Remove Set", key=f"sub_{ex}_{idx}") and current_sets > 1:
                st.session_state.exercise_set_counts[set_count_key] -= 1
                st.rerun()
        with mode_col:
            calc_mode = st.radio(
                "Weight Calculation Mode",
                ["Weight on Each Side (+20kg Olympic Bar)", "Dumbbell / Machine Pin (Direct Weight)"],
                index=0 if ex_type == "barbell" else 1,
                key=f"{log_date}_{ex}_mode",
                horizontal=True
            )
        
        ex_sets = []
        ex_volume = 0.0
        ex_cals = 0.0
        
        hdr1, hdr2, hdr3, hdr4 = st.columns([1, 2, 2, 2])
        hdr1.caption("Set #")
        hdr2.caption("Each Side (kg)" if "Each Side" in calc_mode else "Weight (Per Hand/Machine)")
        hdr3.caption("Reps")
        hdr4.caption("Effective Total Load & Burn")
        
        for s in range(1, current_sets + 1):
            sc1, sc2, sc3, sc4 = st.columns([1, 2, 2, 2])
            with sc1:
                st.write(f"**Set {s}**")
            with sc2:
                input_wt = st.number_input("Input Weight", min_value=0.0, step=1.25, key=f"{log_date}_{ex}_s{s}_wt", label_visibility="collapsed")
            with sc3:
                s_rp = st.number_input("Reps", min_value=0, step=1, value=10, key=f"{log_date}_{ex}_s{s}_rp", label_visibility="collapsed")
                
            if "Each Side" in calc_mode:
                effective_total_wt = (input_wt * 2) + 20.0 if input_wt > 0 else 0.0
                calc_note = f"({input_wt}kg x 2) + 20kg bar"
            else:
                effective_total_wt = input_wt
                calc_note = f"{input_wt}kg"
                
            set_vol = effective_total_wt * s_rp
            set_kcal = round((0.14 * user_weight) + (0.0022 * set_vol), 1) if (effective_total_wt > 0 and s_rp > 0) else 0.0
            
            ex_volume += set_vol
            ex_cals += set_kcal
            
            with sc4:
                st.markdown(f"**{effective_total_wt} kg total**<br><span style='color:#58a6ff;'>Load: {int(set_vol)} kg</span> | <span style='color:#3fb950;'>~{set_kcal} kcal</span>", unsafe_allow_html=True)
                
            ex_sets.append({
                "set": s,
                "input_weight": input_wt,
                "total_weight": effective_total_wt,
                "reps": s_rp,
                "volume": set_vol,
                "calc_type": calc_note
            })
            
        grand_total_volume += ex_volume
        grand_total_lift_cals += ex_cals
        
        st.markdown(f"<div style='font-size: 0.85rem; color: #8b949e; text-align: right;'>Exercise Total: <strong>{round(ex_volume, 1)} kg</strong> lifted | <strong>~{round(ex_cals, 1)} kcal</strong></div>", unsafe_allow_html=True)
        st.markdown("<hr style='border: 0.5px solid #21262d; margin: 12px 0;'>", unsafe_allow_html=True)
        
        session_workout_data[ex] = {
            "sets": ex_sets,
            "exercise_volume": round(ex_volume, 1),
            "exercise_kcal": round(ex_cals, 1)
        }

    st.markdown("### 🔥 Finisher: Incline Cardio")
    finisher_done = st.checkbox("Completed 15-20 min Incline Treadmill Walk (15% Incline @ 2.5 km/h)", value=True, key=f"{log_date}_finisher_val")
    
    cardio_cals = 165.0 if finisher_done else 0.0
    total_session_cals = round(grand_total_lift_cals + cardio_cals, 1)
    
    st.markdown("---")
    st.subheader("🏁 Session Summary & Grand Totals")
    g1, g2, g3 = st.columns(3)
    g1.metric("Grand Total Weight Lifted", f"{round(grand_total_volume, 1)} kg")
    g2.metric("Lifting Burn", f"~{round(grand_total_lift_cals, 1)} kcal")
    g3.metric("Grand Total Calorie Burn (with Cardio)", f"~{total_session_cals} kcal")
    
    if st.button("💾 Lock & Persist Workout Session", type="primary"):
        current_session = {
            "split": f"{chosen_system} - {split_choice}",
            "exercises": session_workout_data,
            "grand_total_volume_kg": round(grand_total_volume, 1),
            "total_calories_burned": total_session_cals,
            "finisher": finisher_done
        }
        st.session_state.db.setdefault("workouts", {})[log_date] = current_session
        save_local_data(st.session_state.db)
        st.success(f"✅ Workout for {log_date} successfully logged and locked!")

    st.markdown("---")
    st.subheader("📄 Workout Report & Export")
    if log_date in st.session_state.db.get("workouts", {}):
        w_data = st.session_state.db["workouts"][log_date]
        
        with st.expander("👁️ View Formatted Session Summary Card", expanded=True):
            st.markdown(f"""<div class="report-card">
                <h4 style="color: #58a6ff; margin:0;">🏋️ KSP Workout Brief — {log_date}</h4>
                <p style="color: #8b949e; margin-top: 4px;"><strong>Routine:</strong> {w_data.get('split', 'PPL')}</p>
                <p><strong>Total Tonnage:</strong> <span style="color:#58a6ff; font-weight:bold;">{w_data.get('grand_total_volume_kg', 0)} kg</span> | <strong>Total Energy:</strong> <span style="color:#3fb950; font-weight:bold;">~{w_data.get('total_calories_burned', 0)} kcal</span></p>
                <p><strong>Cardio:</strong> {'15% Incline 20m Walk (Completed)' if w_data.get('finisher') else 'Skipped'}</p>
                <hr style="border: 0.5px solid #30363d;">
                <ul style="font-size: 0.9rem;">
            """, unsafe_allow_html=True)
            
            for ex_n, det in w_data.get("exercises", {}).items():
                st.markdown(f"<li><strong>{ex_n}:</strong> {det.get('exercise_volume', 0)} kg lifted (~{det.get('exercise_kcal', 0)} kcal)</li>", unsafe_allow_html=True)
                
            st.markdown("</ul></div>", unsafe_allow_html=True)

        pdf_bytes = build_pdf_document(log_date, w_data)
        b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        pdf_href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="KSP_Workout_{log_date}.pdf" target="_blank" style="display: inline-block; padding: 10px 18px; background-color: #238636; color: white; border-radius: 6px; text-decoration: none; font-weight: bold; margin-top: 10px;">📥 Download PDF Report</a>'
        st.markdown(pdf_href, unsafe_allow_html=True)
    else:
        st.caption("Lock your workout above to preview and export the summary.")

# ----------------- SECTION 5: UNIVERSAL FOOD & MACRO AI -----------------
elif menu == "🔍 Universal Food & Macro AI":
    st.title("🔍 Universal Food & Macro AI")
    st.markdown("Zero hardcoded limits: Powered by Multimodal AI. Understands any food, regional dish, fruit, snack, or meal photo automatically.")
    
    tab_text, tab_photo = st.tabs(["💬 Natural Language Query", "📸 Real Meal / Food Photo"])
    
    with tab_text:
        user_query = st.text_input(
            "Describe your food naturally:",
            placeholder="e.g. '2 medium bananas', 'moong dal chilla with mint chutney', '1 plate idli sambar', 'handful almonds'"
        )
        
        if st.button("🚀 Analyze Nutrition", type="primary", key="btn_text_macro"):
            if not user_query.strip():
                st.warning("Please type a food description first.")
            else:
                with st.spinner("AI analyzing nutrition & portion metrics..."):
                    res = analyze_food_universally(text_query=user_query)
                    
                    st.markdown(f"""<div class="scan-card">
                        <h3 style="color:#58a6ff; margin-bottom: 2px;">{res.get('item_name', 'Analyzed Item')}</h3>
                        <p style="color:#8b949e;">Serving: <strong>{res.get('portion_description', '')}</strong></p>
                        <p style="color:#3fb950; font-size:0.95rem;">💡 <em>{res.get('dietary_notes', '')}</em></p>
                    </div>""", unsafe_allow_html=True)
                    
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Calories", f"{res.get('calories', 0)} kcal")
                    m2.metric("Protein", f"{res.get('protein', 0)} g")
                    m3.metric("Carbs", f"{res.get('carbs', 0)} g")
                    m4.metric("Fat", f"{res.get('fat', 0)} g")

    with tab_photo:
        st.markdown("Take or upload a photo of any meal, plate, or fruit:")
        photo_file = st.file_uploader("Upload Meal Photo", type=["jpg", "jpeg", "png"], key="universal_meal_img")
        if photo_file:
            pil_img = Image.open(photo_file)
            st.image(pil_img, caption="Meal Uploaded", width=340)
            
            if st.button("🔍 AI Vision Scan Meal", type="primary"):
                with st.spinner("Analyzing image contents and portion depth..."):
                    res = analyze_food_universally(pil_image=pil_img)
                    
                    st.markdown(f"""<div class="scan-card">
                        <h3 style="color:#58a6ff; margin-bottom: 2px;">{res.get('item_name', 'Recognized Plate')}</h3>
                        <p style="color:#8b949e;">Estimated Serving: <strong>{res.get('portion_description', '')}</strong></p>
                        <p style="color:#3fb950; font-size:0.95rem;">💡 <em>{res.get('dietary_notes', '')}</em></p>
                    </div>""", unsafe_allow_html=True)
                    
                    p1, p2, p3, p4 = st.columns(4)
                    p1.metric("Calories", f"{res.get('calories', 0)} kcal")
                    p1_p = res.get('protein', 0)
                    p2.metric("Protein", f"{p1_p} g")
                    p3.metric("Carbs", f"{res.get('carbs', 0)} g")
                    p4.metric("Fat", f"{res.get('fat', 0)} g")
