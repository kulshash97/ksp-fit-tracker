import os
import io
import re
import json
import base64
import urllib.request
import urllib.error
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
    if not isinstance(text, str):
        text = str(text)
    replacements = {
        "₹": "Rs.", "→": "->", "•": "-", "—": "-", "–": "-",
        "“": '"', "”": '"', "’": "'", "‘": "'",
        "⚡": "", "🥗": "", "🏋️": "", "📊": "", "📑": "",
        "🔍": "", "🌅": "", "☀️": "", "🌙": "", "💡": ""
    }
    for orig, rep in replacements.items():
        text = text.replace(orig, rep)
    return text.encode('latin-1', 'replace').decode('latin-1')

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

# --- SECURE PIN LOGIN & URL PERSISTENCE ---
query_user = st.query_params.get("user", None)
if "logged_in_user" not in st.session_state:
    if query_user and query_user in st.session_state.all_users_db:
        st.session_state.logged_in_user = query_user
    else:
        st.session_state.logged_in_user = None

if not st.session_state.logged_in_user:
    st.markdown("<h1 style='text-align:center;'>⚡ KSP Fitness OS</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#8b949e;'>Sign in or create a quick PIN profile to keep your body stats, workouts, and diet private.</p>", unsafe_allow_html=True)
    
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
                            st.error("❌ Incorrect PIN for this profile. Try again or use a different username.")
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
                                "height_cm": 170.0,
                                "weight_kg": 70.0,
                                "age": 28,
                                "sex": "Male",
                                "smm_kg": 28.0,
                                "body_fat_pct": 22.0,
                                "visceral_level": 8,
                                "target_kcal": 1700,
                                "target_protein": 115,
                                "recommended_split": "Push / Pull / Legs (Recomp Split - Optimal for BF 18% - 25%)",
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

# --- ANTHROPOMETRIC + VISION FUSION ENGINE ---
def calculate_anthropometric_baseline(height_cm, weight_kg, age, sex):
    """Calculates BMI and South Asian-adjusted Deurenberg baseline BF%."""
    if height_cm <= 0 or weight_kg <= 0:
        return 22.0, 22.0
    bmi = weight_kg / ((height_cm / 100.0) ** 2)
    sex_factor = 1 if sex == "Male" else 0
    # Standard Deurenberg + 3.0% South Asian visceral/adiposity offset
    deurenberg_bf = (1.20 * bmi) + (0.23 * age) - (10.8 * sex_factor) - 5.4
    indian_adjusted_bf = max(8.0, min(50.0, deurenberg_bf + 3.0))
    return round(bmi, 1), round(indian_adjusted_bf, 1)

def analyze_physique_fusion_ai(pil_image, height_cm, weight_kg, age, sex):
    fixed_img = ImageOps.exif_transpose(pil_image)
    if fixed_img.mode in ("RGBA", "P"):
        fixed_img = fixed_img.convert("RGB")
        
    bmi, baseline_bf = calculate_anthropometric_baseline(height_cm, weight_kg, age, sex)
    api_key = get_gemini_api_key()
    
    if not api_key:
        low_b = round(baseline_bf - 1.5, 1)
        high_b = round(baseline_bf + 1.5, 1)
        return {
            "estimated_bf_num": baseline_bf,
            "estimated_body_fat_range": f"{low_b}% - {high_b}%",
            "frame_analysis": f"Anthropometric baseline calibrated at {height_cm} cm and {weight_kg} kg (BMI {bmi}). Add GEMINI_API_KEY in secrets for live visual muscle-vs-fat refinement.",
            "recommendation": "Maintain high daily protein (2.0g/kg lean mass) alongside progressive compound lifts."
        }
    
    sys_prompt = (
        "You are an expert clinical anthropometrist and sports body-composition specialist performing Multimodal Vision + Biometric Fusion.\n"
        f"Subject Biometrics:\n"
        f"- Height: {height_cm} cm | Weight: {weight_kg} kg | Age: {age} | Biological Sex: {sex}\n"
        f"- Calculated BMI: {bmi} kg/m2\n"
        f"- South Asian Anthropometric Baseline BF%: {baseline_bf}%\n\n"
        "Instructions for Fusion Calibration:\n"
        "1. Anchor your assessment around the anthropometric baseline ({baseline_bf}%) so you do NOT underestimate total body mass on shorter statures or hidden visceral fat.\n"
        "2. Inspect the photo closely to refine that baseline UP or DOWN based on visible muscle mass vs fat:\n"
        "   - If the subject has visible muscular hypertrophy (thick delts, arms, chest separation, visible abs), adjust LOWER than the BMI-based baseline.\n"
        "   - If the subject carries noticeable abdominal/lower-chest subcutaneous fat or lacks muscle density, keep close to or slightly ABOVE the baseline.\n"
        "   - Account for loose clothing vs shirtless/fitted wear.\n"
        "Return ONLY a valid JSON object with these exact keys:\n"
        '{\n'
        '  "estimated_bf_num": single_float_number_midpoint,\n'
        '  "estimated_body_fat_range": "e.g. 28% - 31%",\n'
        '  "frame_analysis": "2-3 specific sentences explaining how height/weight mass interacts with visible muscle density and abdominal fat in the photo",\n'
        '  "recommendation": "1-2 sentences with exact caloric and lifting advice tailored to this fused profile"\n'
        '}'
    )
    
    try:
        buffered = io.BytesIO()
        fixed_img.save(buffered, format="JPEG", quality=85)
        img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        parts = [
            {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
            {"text": f"Fuse the subject's biometrics ({height_cm}cm, {weight_kg}kg, {age}y, {sex}, BMI {bmi}) with visual physique cues to calculate true body fat percentage."}
        ]
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": parts}],
            "systemInstruction": {"parts": [{"text": sys_prompt}]},
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.15
            }
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=15) as response:
            resp_data = json.loads(response.read().decode("utf-8"))
            raw_text = resp_data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(raw_text)
    except Exception:
        low_b = round(baseline_bf - 1.5, 1)
        high_b = round(baseline_bf + 1.5, 1)
        return {
            "estimated_bf_num": baseline_bf,
            "estimated_body_fat_range": f"{low_b}% - {high_b}%",
            "frame_analysis": f"Calibrated using stature-to-mass ratio ({height_cm}cm, {weight_kg}kg, BMI {bmi}) combined with upper-body frame proportions.",
            "recommendation": "Prioritize progressive resistance training with a structured caloric deficit and high protein intake."
        }

def analyze_food_universally(text_query=None, pil_image=None):
    api_key = get_gemini_api_key()
    sys_instruction = (
        "You are an expert clinical and sports nutritionist. Analyze the food query or photo. "
        "Return ONLY a valid JSON object with:\n"
        '{\n  "item_name": "name",\n  "portion_description": "serving size",\n  "calories": kcal_num,\n'
        '  "protein": p_num,\n  "carbs": c_num,\n  "fat": f_num,\n  "fiber": fib_num,\n  "dietary_notes": "tip"\n}'
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
                buffered = io.BytesIO()
                fixed_img.save(buffered, format="JPEG", quality=85)
                img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
                parts.append({"inline_data": {"mime_type": "image/jpeg", "data": img_b64}})
                parts.append({"text": "Identify food dish in photo, portion size, and macros."})
                
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": parts}],
                "systemInstruction": {"parts": [{"text": sys_instruction}]},
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}
            }
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=12) as response:
                resp_data = json.loads(response.read().decode("utf-8"))
                return json.loads(resp_data["candidates"][0]["content"]["parts"][0]["text"])
        except Exception:
            pass

    q = (text_query or "").lower()
    count_m = re.search(r"^(\d+(\.\d+)?)", q)
    qty = float(count_m.group(1)) if count_m else 1.0
    if "bann" in q or "banana" in q or "kela" in q:
        return {"item_name": "Banana", "portion_description": f"{qty} unit(s)", "calories": round(95*qty,1), "protein": round(1.2*qty,1), "carbs": round(24*qty,1), "fat": 0.3, "fiber": 2.6, "dietary_notes": "Pre-workout carb."}
    return {"item_name": text_query.title() if text_query else "Custom Item", "portion_description": f"{qty} serving", "calories": round(180*qty,1), "protein": round(8*qty,1), "carbs": round(26*qty,1), "fat": 5.0, "fiber": 2.0, "dietary_notes": "Clean source."}

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
        recommended_split = "Upper / Lower (Metabolic Density - Optimal for BF > 25%)"
    elif bfp >= 18.0:
        recommended_split = "Push / Pull / Legs (Recomp Split - Optimal for BF 18% - 25%)"
    else:
        recommended_split = "Arnold Split (High Volume Hypertrophy - Optimal for BF < 18%)"
        
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
    pdf.set_fill_color(22, 27, 34)
    pdf.rect(0, 0, 210, 32, 'F')
    pdf.set_text_color(88, 166, 255)
    pdf.set_font('Helvetica', 'B', 15)
    pdf.set_xy(10, 8)
    pdf.cell(190, 8, clean_pdf_str("KSP FITNESS OS - PERFORMANCE WORKOUT LOG"), ln=True, align='C')
    pdf.set_text_color(200, 200, 200)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(190, 6, clean_pdf_str(f"Athlete: {display_name} | Session Date: {log_date}"), ln=True, align='C')
    pdf.ln(12)
    pdf.set_text_color(20, 20, 20)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 7, clean_pdf_str(f"Program Split: {workout_data.get('split', 'PPL')}"), ln=True)
    grand_vol = workout_data.get('grand_total_volume_kg', 0)
    cals_burned = workout_data.get('total_calories_burned', 0)
    pdf.cell(0, 7, clean_pdf_str(f"Total Weight Lifted (Tonnage): {grand_vol} kg"), ln=True)
    pdf.cell(0, 7, clean_pdf_str(f"Total Calorie Burn (with Cardio): ~{cals_burned} kcal"), ln=True)
    finisher_txt = "15-20 min Incline Walk (15% @ 2.5 km/h) - COMPLETED" if workout_data.get('finisher') else "Skipped"
    pdf.cell(0, 7, clean_pdf_str(f"Cardio Finisher: {finisher_txt}"), ln=True)
    pdf.ln(4)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    pdf.set_font('Helvetica', 'B', 12)
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
        for s in details.get('sets', []):
            set_num = s.get('set', 1)
            tot_wt = s.get('total_weight', 0.0)
            reps = s.get('reps', 0)
            vol = s.get('volume', tot_wt * reps)
            calc = s.get('calc_type', f"{tot_wt}kg")
            pdf.cell(190, 6, clean_pdf_str(f"      Set {set_num}: {tot_wt} kg total ({reps} reps) -> Load: {vol} kg [{calc}]"), border='LR', ln=True)
        pdf.cell(190, 1, '', border='T', ln=True)
        pdf.ln(3)
    return bytes(pdf.output())

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
    pdf.cell(190, 6, clean_pdf_str(f"User: {display_name} | Pref: {diet_pref} | {tier_choice}"), ln=True, align='C')
    pdf.ln(12)
    pdf.set_text_color(20, 20, 20)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 7, clean_pdf_str(f"Target Daily Calories: {profile_data.get('target_kcal', 1600)} kcal"), ln=True)
    pdf.cell(0, 7, clean_pdf_str(f"Target Daily Protein Floor: {profile_data.get('target_protein', 115)} g/day"), ln=True)
    pdf.cell(0, 7, clean_pdf_str(f"Weight: {profile_data.get('weight_kg', 70.0)} kg | Body Fat: {profile_data.get('body_fat_pct', 22.0)}%"), ln=True)
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
            ("Fresh Curd Setup", "6.0 kg", "Rs. 380", "15g protein / day"),
            ("Roasted Chana", "1.0 kg", "Rs. 140", "Intra-day fiber & protein"),
            ("Moong Dal for Sprouts", "2.0 kg", "Rs. 260", "24g protein / 100g raw"),
            ("Seasonal Veggies", "Monthly", "Rs. 600", "Potassium & fiber"),
        ]
        est_cost = "Rs. 1,810 - Rs. 2,200 / month"
    elif "Tier 2" in tier_choice:
        groceries = [
            ("Low-Fat Paneer", "4.0 kg", "Rs. 1,400", "18g protein / 100g"),
            ("Plant / Pea Protein", "1 Tub (1kg)", "Rs. 1,600", "25g protein / scoop"),
            ("Soya Chunks & Dal", "1.5 kg", "Rs. 200", "Secondary clean bulk"),
            ("Rolled Oats & PB", "1.5 kg", "Rs. 550", "Complex carbs & healthy fats"),
            ("Curd & Seasonal Greens", "Monthly", "Rs. 800", "Gut health & satiety"),
        ]
        est_cost = "Rs. 4,200 - Rs. 4,800 / month"
    else:
        groceries = [
            ("Whey Protein Isolate", "2.0 kg", "Rs. 5,400", "27g protein / scoop"),
            ("Artisanal Tofu & Paneer", "5.0 kg", "Rs. 2,200", "Clean bioavailability"),
            ("Greek Yogurt & Berries", "Monthly", "Rs. 1,800", "Probiotics & polyphenols"),
            ("Almond Butter & Chia", "Monthly", "Rs. 1,100", "Omega-3 & healthy fats"),
        ]
        est_cost = "Rs. 8,500 - Rs. 10,500 / month"

    for itm, qty, prc, note in groceries:
        pdf.cell(190, 6, clean_pdf_str(f"  - {itm} [{qty}] -> {prc} ({note})"), ln=True)
    pdf.ln(3)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.cell(0, 7, clean_pdf_str(f"Total Monthly Investment: {est_cost}"), ln=True)
    return bytes(pdf.output())

menu = st.sidebar.radio("Navigation", [
    "📊 Dashboard & BMI",
    "📑 InBody & Body Composition",
    "🥗 Smart Diet & Budget Planner",
    "🏋️ Adaptive Workout Logger",
    "🔍 Universal Food & Macro AI"
])

# ----------------- SECTION 1: DASHBOARD & BMI -----------------
if menu == "📊 Dashboard & BMI":
    st.title(f"⚡ Performance Dashboard — {display_name}")
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"""<div class="metric-card"><div class="metric-title">Daily Calories</div><div class="metric-value">{profile.get('target_kcal', 1600)}</div><div class="metric-subtext">kcal / day</div></div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class="metric-card"><div class="metric-title">Daily Protein</div><div class="metric-value">{profile.get('target_protein', 115)}g</div><div class="metric-subtext">Body Fat: {profile.get('body_fat_pct', 22.0)}%</div></div>""", unsafe_allow_html=True)
    c3.markdown("""<div class="metric-card"><div class="metric-title">Cardio Incline</div><div class="metric-value">15%</div><div class="metric-subtext">2.5 km/h @ 20 Mins</div></div>""", unsafe_allow_html=True)
    c4.markdown(f"""<div class="metric-card"><div class="metric-title">Active Split</div><div class="metric-value" style="font-size: 1.05rem; margin-top: 10px;">{profile.get('recommended_split', 'Push / Pull / Legs')}</div><div class="metric-subtext">Synced</div></div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("⚖️ Biometric Health & BMI Analyzer")
    b1, b2 = st.columns(2)
    with b1:
        h_cm = st.number_input("Height (cm)", value=float(profile.get("height_cm", 170.0)), step=0.5)
        w_kg = st.number_input("Current Weight (kg)", value=float(profile.get("weight_kg", 70.0)), step=0.1)
        if st.button("💾 Save Height & Weight"):
            profile["height_cm"] = h_cm
            profile["weight_kg"] = w_kg
            recalibrate_user_targets(w_kg, profile.get("body_fat_pct", 22.0))
            st.success("Vitals saved!")
            st.rerun()
    with b2:
        if h_cm > 0 and w_kg > 0:
            bmi = round(w_kg / ((h_cm / 100.0) ** 2), 2)
            cat, col = ("Normal Weight", "#3fb950") if 18.5 <= bmi < 23.0 else (("Overweight (Indian Cut-Off)", "#f0883e") if 23.0 <= bmi < 25.0 else ("Obese Range", "#f85149"))
            st.markdown(f"""<div style="background-color: #161b22; border-left: 5px solid {col}; padding: 18px; border-radius: 8px; margin-top: 15px;">
                <div style="font-size: 0.9rem; color: #8b949e;">Calculated Body Mass Index (BMI)</div>
                <div style="font-size: 2.2rem; font-weight: bold; color: {col};">{bmi} kg/m²</div>
                <div style="font-size: 1rem; color: #e6edf3;">Classification: <strong>{cat}</strong></div>
            </div>""", unsafe_allow_html=True)

# ------------ SECTION 2: INBODY & BODY COMPOSITION (MULTIMODAL FUSION) ------------
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
                f_h = st.number_input("Height (cm)", min_value=120.0, max_value=230.0, value=float(profile.get("height_cm", 170.0)), step=0.5, key="fusion_h")
                f_w = st.number_input("Weight (kg)", min_value=30.0, max_value=200.0, value=float(profile.get("weight_kg", 70.0)), step=0.1, key="fusion_w")
                c_age, c_sex = st.columns(2)
                with c_age:
                    f_age = st.number_input("Age", min_value=14, max_value=90, value=int(profile.get("age", 28)), step=1, key="fusion_age")
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
                est_num = float(vres.get("estimated_bf_num", 25.0))
                st.markdown(f"""<div class="scan-card">
                    <h4 style="color:#58a6ff; margin-bottom:6px;">🔍 Fused Anthropometric + Vision Breakdown</h4>
                    <p style="font-size: 1.2rem;"><strong>Calibrated Body Fat Range:</strong> <span style="color:#3fb950; font-weight:bold;">{vres.get('estimated_body_fat_range', '')}</span></p>
                    <p><strong>Physique & Mass Analysis:</strong> {vres.get('frame_analysis', '')}</p>
                    <p style="color:#8b949e; font-size:0.9rem;"><strong>Protocol:</strong> {vres.get('recommendation', '')}</p>
                </div>""", unsafe_allow_html=True)
                
                if st.button(f"⚡ Sync {est_num}% Body Fat & {f_w} kg to My Dashboard & Split"):
                    recalibrate_user_targets(f_w, est_num)
                    st.success(f"✅ Dashboard, calories, and workout split updated to {est_num}% body fat!")
                    st.rerun()

    with tab_scan:
        st.subheader("InBody / DEXA Telemetry")
        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1:
            scan_weight = st.number_input("Scale Weight (kg)", value=float(profile.get("weight_kg", 70.0)), step=0.1)
        with sc2:
            scan_smm = st.number_input("Skeletal Muscle Mass (kg)", value=float(profile.get("smm_kg", 28.0)), step=0.1)
        with sc3:
            scan_bfp = st.number_input("Body Fat Percentage (%)", value=float(profile.get("body_fat_pct", 22.0)), step=0.1)
        with sc4:
            scan_vfl = st.number_input("Visceral Fat Level", value=int(profile.get("visceral_level", 8)), step=1)
            
        if st.button("🚀 Recalibrate App & Workout Plan", type="primary"):
            profile["smm_kg"] = scan_smm
            profile["visceral_level"] = scan_vfl
            recalibrate_user_targets(scan_weight, scan_bfp)
            st.success("✅ Profile calibrated!")
            st.rerun()

# ------------ SECTION 3: SMART DIET & BUDGET PLANNER ------------
elif menu == "🥗 Smart Diet & Budget Planner":
    st.title(f"🥗 Smart Diet & Budget Architect — {display_name}")
    t_cals = profile.get('target_kcal', 1600)
    t_prot = profile.get('target_protein', 115)
    
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
            <strong>{t_cals} kcal/day</strong> &bull; <span style="color:#3fb950; font-weight:bold;">{t_prot}g Protein</span> &bull; <span>~30g Fiber</span>
        </div>""", unsafe_allow_html=True)
        
    st.markdown("---")
    st.subheader("🍱 Daily Meal Blueprint")
    m_col1, m_col2, m_col3 = st.columns(3)
    with m_col1:
        st.markdown("""<div class="tier-card"><span style="color:#3fb950; font-weight:bold;">MEAL 1: PRE/POST</span><h4>Sattu Power Chhas + Banana</h4><p style="font-size:0.9rem;">40g Chana Sattu in buttermilk + 1 banana. ~12g Protein.</p></div>""", unsafe_allow_html=True)
    with m_col2:
        st.markdown("""<div class="tier-card"><span style="color:#58a6ff; font-weight:bold;">MEAL 2: LUNCH</span><h4>Soya Bhurji + Curd + Roti</h4><p style="font-size:0.9rem;">60g dry soya chunks + 150g curd + 2 rotis. ~42g Protein.</p></div>""", unsafe_allow_html=True)
    with m_col3:
        st.markdown("""<div class="tier-card"><span style="color:#f0883e; font-weight:bold;">MEAL 3: DINNER</span><h4>Moong Sprouts Chaat + Paneer</h4><p style="font-size:0.9rem;">100g sprouted moong + 60g paneer. ~36g Protein.</p></div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📄 Download Customized 30-Day Diet & Grocery Plan (PDF)")
    diet_pdf_bytes = build_diet_pdf(profile, diet_type, tier)
    b64_diet = base64.b64encode(diet_pdf_bytes).decode('utf-8')
    diet_href = f'<a href="data:application/pdf;base64,{b64_diet}" download="KSP_30Day_Diet_{display_name}.pdf" target="_blank" style="display: inline-block; padding: 10px 18px; background-color: #238636; color: white; border-radius: 6px; text-decoration: none; font-weight: bold; margin-top: 6px;">📥 Download 30-Day Diet & Budget PDF</a>'
    st.markdown(diet_href, unsafe_allow_html=True)

# ------------ SECTION 4: ADAPTIVE WORKOUT LOGGER ------------
elif menu == "🏋️ Adaptive Workout Logger":
    st.title("🏋️ Adaptive Workout & Multi-Set Logger")
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
    user_weight = float(profile.get("weight_kg", 70.0))

    if "exercise_set_counts" not in st.session_state:
        st.session_state.exercise_set_counts = {}

    session_workout_data = {}
    grand_total_volume = 0.0
    grand_total_lift_cals = 0.0

    for idx, (ex, ex_type) in enumerate(exercises):
        st.markdown(f"### {idx + 1}. {ex}")
        set_count_key = f"{active_key}_{log_date}_{ex}_count"
        if set_count_key not in st.session_state.exercise_set_counts:
            st.session_state.exercise_set_counts[set_count_key] = 3
        current_sets = st.session_state.exercise_set_counts[set_count_key]
        
        ctrl1, ctrl2, mode_col = st.columns([1, 1, 3])
        with ctrl1:
            if st.button("➕ Add Set", key=f"add_{active_key}_{ex}_{idx}"):
                st.session_state.exercise_set_counts[set_count_key] += 1
                st.rerun()
        with ctrl2:
            if st.button("➖ Remove Set", key=f"sub_{active_key}_{ex}_{idx}") and current_sets > 1:
                st.session_state.exercise_set_counts[set_count_key] -= 1
                st.rerun()
        with mode_col:
            calc_mode = st.radio(
                "Weight Mode",
                ["Weight on Each Side (+20kg Olympic Bar)", "Dumbbell / Machine Pin (Direct Weight)"],
                index=0 if ex_type == "barbell" else 1,
                key=f"{active_key}_{log_date}_{ex}_mode",
                horizontal=True
            )
            
        ex_sets = []
        ex_volume = 0.0
        ex_cals = 0.0
        for s in range(1, current_sets + 1):
            sc1, sc2, sc3, sc4 = st.columns([1, 2, 2, 2])
            sc1.write(f"**Set {s}**")
            input_wt = sc2.number_input("Wt", min_value=0.0, step=1.25, key=f"{active_key}_{log_date}_{ex}_s{s}_wt", label_visibility="collapsed")
            s_rp = sc3.number_input("Reps", min_value=0, step=1, value=10, key=f"{active_key}_{log_date}_{ex}_s{s}_rp", label_visibility="collapsed")
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
            sc4.markdown(f"**{effective_total_wt} kg** | <span style='color:#3fb950;'>~{set_kcal} kcal</span>", unsafe_allow_html=True)
            ex_sets.append({"set": s, "total_weight": effective_total_wt, "reps": s_rp, "volume": set_vol, "calc_type": calc_note})
        grand_total_volume += ex_volume
        grand_total_lift_cals += ex_cals
        session_workout_data[ex] = {"sets": ex_sets, "exercise_volume": round(ex_volume, 1), "exercise_kcal": round(ex_cals, 1)}

    finisher_done = st.checkbox("Completed 15-20 min Incline Treadmill Walk (15% @ 2.5 km/h)", value=True, key=f"{active_key}_{log_date}_finisher")
    total_session_cals = round(grand_total_lift_cals + (165.0 if finisher_done else 0.0), 1)
    if st.button("💾 Lock & Persist Workout Session", type="primary"):
        user_data.setdefault("workouts", {})[log_date] = {
            "split": f"{chosen_system} - {split_choice}",
            "exercises": session_workout_data,
            "grand_total_volume_kg": round(grand_total_volume, 1),
            "total_calories_burned": total_session_cals,
            "finisher": finisher_done
        }
        persist_current_user()
        st.success(f"✅ Workout saved for {display_name}!")

    if log_date in user_data.get("workouts", {}):
        pdf_bytes = build_pdf_document(log_date, user_data["workouts"][log_date])
        b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        st.markdown(f'<a href="data:application/pdf;base64,{b64_pdf}" download="KSP_Workout_{display_name}_{log_date}.pdf" target="_blank" style="display: inline-block; padding: 10px 18px; background-color: #238636; color: white; border-radius: 6px; text-decoration: none; font-weight: bold; margin-top: 10px;">📥 Download Workout PDF</a>', unsafe_allow_html=True)

# ------------ SECTION 5: UNIVERSAL FOOD & MACRO AI ------------
elif menu == "🔍 Universal Food & Macro AI":
    st.title("🔍 Universal Food & Macro AI")
    user_query = st.text_input("Describe your food naturally (e.g. '2 medium bananas', 'moong dal chilla'):")
    if st.button("🚀 Analyze Nutrition", type="primary"):
        res = analyze_food_universally(text_query=user_query)
        st.markdown(f"""<div class="scan-card">
            <h3 style="color:#58a6ff;">{res.get('item_name', 'Item')} ({res.get('portion_description', '')})</h3>
            <p style="color:#3fb950;">💡 {res.get('dietary_notes', '')}</p>
        </div>""", unsafe_allow_html=True)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Calories", f"{res.get('calories', 0)} kcal")
        m2.metric("Protein", f"{res.get('protein', 0)} g")
        m3.metric("Carbs", f"{res.get('carbs', 0)} g")
        m4.metric("Fat", f"{res.get('fat', 0)} g")
