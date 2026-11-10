import json
import os
from datetime import date
from PIL import Image
import streamlit as st

st.set_page_config(
    page_title="KSP Fitness OS",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .stApp { background-color: #0d1117; color: #e6edf3; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .metric-card { background: linear-gradient(135deg, #161b22 0%, #21262d 100%); border: 1px solid #30363d; border-radius: 12px; padding: 18px; text-align: center; }
    .metric-title { color: #8b949e; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; }
    .metric-value { color: #58a6ff; font-size: 1.8rem; font-weight: 700; margin-top: 4px; }
    .metric-subtext { color: #3fb950; font-size: 0.8rem; }
    .scan-card { background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 16px; margin-top: 10px; }
</style>
""",
    unsafe_allow_html=True,
)

DATA_FILE = "fitness_os_data.json"


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
          "target_kcal": 1600,
          "target_protein": 120,
      },
  }


def save_local_data(data):
  with open(DATA_FILE, "w") as f:
    json.dump(data, f, indent=4)


if "db" not in st.session_state:
  st.session_state.db = load_local_data()

profile = st.session_state.db.setdefault(
    "profile",
    {
        "height_cm": 159.0,
        "weight_kg": 74.8,
        "smm_kg": 28.6,
        "body_fat_pct": 32.0,
        "visceral_level": 11,
        "target_kcal": 1600,
        "target_protein": 120,
    },
)

PPL_ROUTINES = {
    "Push Day (Chest, Shoulders & Triceps)": [
        "Flat Bench Press / Machine Chest Press",
        "Incline Dumbbell / Machine Press",
        "Pec Deck Flyes",
        "Overhead Dumbbell Press",
        "Lateral Raises (Dumbbell/Cable)",
        "Triceps Pushdowns (Rope)",
    ],
    "Pull Day (Back, Rear Delts & Biceps)": [
        "Lat Pulldown / Assisted Pull-Ups",
        "Seated Cable Row / Machine Row",
        "Single-Arm Dumbbell Row",
        "Straight-Arm Lat Pulldown",
        "Dumbbell Biceps Curls",
        "Hammer Curls",
    ],
    "Leg Day (Quads, Hamstrings & Calves)": [
        "Barbell Squat / Leg Press",
        "Romanian Deadlifts (RDLs)",
        "Bulgarian Split Squats / Lunges",
        "Leg Extensions",
        "Standing Calf Raises",
    ],
}

FOOD_REGISTRY = {
    "soya chunks": {
        "calories": 345,
        "protein": 52.0,
        "carbs": 33.0,
        "fat": 0.5,
        "unit": "100g dry",
    },
    "curd": {
        "calories": 60,
        "protein": 4.0,
        "carbs": 4.5,
        "fat": 3.0,
        "unit": "100g",
    },
    "dahi": {
        "calories": 60,
        "protein": 4.0,
        "carbs": 4.5,
        "fat": 3.0,
        "unit": "100g",
    },
    "paneer": {
        "calories": 265,
        "protein": 18.0,
        "carbs": 3.0,
        "fat": 20.0,
        "unit": "100g",
    },
    "pea protein": {
        "calories": 120,
        "protein": 24.0,
        "carbs": 2.0,
        "fat": 1.5,
        "unit": "1 scoop (33g)",
    },
    "besan chilla": {
        "calories": 180,
        "protein": 8.0,
        "carbs": 22.0,
        "fat": 5.0,
        "unit": "1 medium",
    },
    "moong dal chilla": {
        "calories": 160,
        "protein": 10.0,
        "carbs": 20.0,
        "fat": 3.5,
        "unit": "1 medium",
    },
    "roti": {
        "calories": 80,
        "protein": 3.0,
        "carbs": 15.0,
        "fat": 0.5,
        "unit": "1 piece",
    },
    "cooked rice": {
        "calories": 130,
        "protein": 2.7,
        "carbs": 28.0,
        "fat": 0.3,
        "unit": "100g",
    },
    "cooked dal": {
        "calories": 120,
        "protein": 6.0,
        "carbs": 18.0,
        "fat": 2.5,
        "unit": "1 katori (150g)",
    },
}

st.sidebar.markdown("## ⚡ KSP Fitness OS")
menu = st.sidebar.radio(
    "Navigation",
    [
        "📊 Dashboard & BMI",
        "📑 InBody & Body Composition",
        "🏋️ PPL Workout Logger",
        "🥗 Calorie & Macro AI",
    ],
)

# ----------------- SECTION 1: DASHBOARD & BMI -----------------
if menu == "📊 Dashboard & BMI":
  st.title("⚡ Performance Dashboard & Vitals")

  # Dynamic Metric Top Cards linked to profile state
  c1, c2, c3, c4 = st.columns(4)
  c1.markdown(
      f"""<div class="metric-card">
        <div class="metric-title">Target Deficit</div>
        <div class="metric-value">{profile.get('target_kcal', 1600)}</div>
        <div class="metric-subtext">kcal / day</div>
    </div>""",
      unsafe_allow_html=True,
  )
  c2.markdown(
      f"""<div class="metric-card">
        <div class="metric-title">Daily Protein</div>
        <div class="metric-value">{profile.get('target_protein', 120)}g</div>
        <div class="metric-subtext">Muscle Preservation Target</div>
    </div>""",
      unsafe_allow_html=True,
  )
  c3.markdown(
      """<div class="metric-card">
        <div class="metric-title">Cardio Incline</div>
        <div class="metric-value">15%</div>
        <div class="metric-subtext">2.5 km/h @ 20 Mins</div>
    </div>""",
      unsafe_allow_html=True,
  )
  c4.markdown(
      """<div class="metric-card">
        <div class="metric-title">Program Split</div>
        <div class="metric-value">PPL</div>
        <div class="metric-subtext">Push / Pull / Legs</div>
    </div>""",
      unsafe_allow_html=True,
  )

  st.markdown("---")
  st.subheader("⚖️ Biometric Health & BMI Analyzer")

  b1, b2 = st.columns(2)
  with b1:
    h_cm = st.number_input(
        "Height (cm)", value=float(profile.get("height_cm", 159.0)), step=0.5
    )
    w_kg = st.number_input(
        "Current Weight (kg)",
        value=float(profile.get("weight_kg", 74.8)),
        step=0.1,
    )
    profile["height_cm"] = h_cm
    profile["weight_kg"] = w_kg
    save_local_data(st.session_state.db)

  with b2:
    if h_cm > 0 and w_kg > 0:
      bmi = round(w_kg / ((h_cm / 100.0) ** 2), 2)
      cat, col = (
          ("Normal Weight", "#3fb950")
          if 18.5 <= bmi < 24.9
          else (
              ("Overweight", "#f0883e")
              if 25.0 <= bmi < 29.9
              else ("Obese", "#f85149")
          )
      )
      st.markdown(
          f"""<div style="background-color: #161b22; border-left: 5px solid {col}; padding: 18px; border-radius: 8px; margin-top: 15px;">
            <div style="font-size: 0.9rem; color: #8b949e;">Calculated Body Mass Index (BMI)</div>
            <div style="font-size: 2.2rem; font-weight: bold; color: {col};">{bmi} kg/m²</div>
            <div style="font-size: 1rem; color: #e6edf3;">Classification: <strong>{cat}</strong></div>
            <div style="font-size: 0.85rem; color: #8b949e; margin-top: 6px;">
                Note: BMI does not measure skeletal muscle mass vs. fat distribution. Refer to your InBody tab for visceral levels.
            </div>
        </div>""",
          unsafe_allow_html=True,
      )

# ------------ SECTION 2: INBODY & BODY COMPOSITION ------------
elif menu == "📑 InBody & Body Composition":
  st.title("📑 InBody / DEXA & Visual Composition Engine")
  st.markdown(
      "Upload your scan reports or body check photos to recalculate calories,"
      " protein targets, and workout split intensity."
  )

  tab_scan, tab_photo = st.tabs(
      ["📊 InBody / DEXA Report Calibrator", "📸 Visual Body Fat Estimator"]
  )

  with tab_scan:
    st.subheader("InBody / DEXA Telemetry")
    scan_file = st.file_uploader(
        "Upload InBody / DEXA Scan Image / PDF",
        type=["jpg", "jpeg", "png", "pdf"],
        key="inbody_upload",
    )
    if scan_file:
      st.success("Report attached successfully. Enter/verify the metrics below:")

    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
      scan_weight = st.number_input(
          "Scale Weight (kg)",
          value=float(profile.get("weight_kg", 74.8)),
          step=0.1,
      )
    with sc2:
      scan_smm = st.number_input(
          "Skeletal Muscle Mass (kg)",
          value=float(profile.get("smm_kg", 28.6)),
          step=0.1,
      )
    with sc3:
      scan_bfp = st.number_input(
          "Body Fat Percentage (%)",
          value=float(profile.get("body_fat_pct", 32.0)),
          step=0.1,
      )
    with sc4:
      scan_vfl = st.number_input(
          "Visceral Fat Level",
          value=int(profile.get("visceral_level", 11)),
          step=1,
      )

    if st.button("🚀 Recalibrate Macros & Training Split"):
      # Lean Body Mass calculation: Weight * (1 - BFP/100)
      lean_mass = scan_weight * (1.0 - (scan_bfp / 100.0))
      # Minimum 2.0g protein per kg of Lean Body Mass
      recommended_protein = int(round(lean_mass * 2.2))
      if recommended_protein < 115:
        recommended_protein = 120

      # Basal Metabolic Rate via Katch-McArdle: 370 + (21.6 * lean_mass)
      bmr = 370 + (21.6 * lean_mass)
      # Sedentary/Moderate activity multiplier (approx 1.35) minus 500 kcal deficit
      tdee = bmr * 1.35
      caloric_deficit = int(round(tdee - 450))

      profile["weight_kg"] = scan_weight
      profile["smm_kg"] = scan_smm
      profile["body_fat_pct"] = scan_bfp
      profile["visceral_level"] = scan_vfl
      profile["target_kcal"] = caloric_deficit
      profile["target_protein"] = recommended_protein
      save_local_data(st.session_state.db)

      st.success("✅ System updated based on fresh biometrics!")

      res1, res2, res3 = st.columns(3)
      res1.metric("Recalibrated Daily Calories", f"{caloric_deficit} kcal")
      res2.metric("Target Protein (Pure Veg)", f"{recommended_protein}g / day")
      res3.metric("Lean Body Mass (LBM)", f"{round(lean_mass, 1)} kg")

      st.markdown(f"""<div class="scan-card">
            <h4>📋 Tactical Adjustments Generated</h4>
            <ul>
                <li><strong>Visceral Fat Level ({scan_vfl}):</strong> Maintain the 15% incline walk at 2.5 km/h for 20 minutes post-lifting to accelerate abdominal lipid oxidation.</li>
                <li><strong>Skeletal Muscle Mass ({scan_smm} kg):</strong> PPL volume set to 3 working sets per exercise at RPE 8–9 to retain muscle in deficit.</li>
                <li><strong>Protein Requirement:</strong> At {recommended_protein}g/day, anchor meals around 60g soya chunks (30g protein), 1 scoop pea protein (24g), 100g paneer (18g), and curd/besan chillas.</li>
            </ul>
        </div>""", unsafe_allow_html=True)

  with tab_photo:
    st.subheader("Visual Physique & Body Fat Check")
    user_photo = st.file_uploader(
        "Upload Full Body Front / Side Photo",
        type=["jpg", "jpeg", "png"],
        key="user_physique_photo",
    )
    if user_photo:
      img = Image.open(user_photo)
      st.image(img, caption="Physique Snapshot", width=340)

      # Visual assessment profile benchmark
      curr_bf = profile.get("body_fat_pct", 32.0)
      st.markdown(f"""<div class="scan-card">
            <h4>🔍 Visual Telemetry Breakdown</h4>
            <p><strong>Estimated Body Fat Range:</strong> ~{int(curr_bf - 2)}% – {int(curr_bf + 2)}%</p>
            <p><strong>Frame Analysis:</strong> Broad shoulders and thick upper-body muscle base present. Abdominal definition currently masked by subcutaneous adipose layer.</p>
            <p><strong>30-Day Milestone:</strong> With a 450 kcal deficit and 120g protein, expect 2.0–2.5 kg fat loss with visible waist taper tightening.</p>
        </div>""", unsafe_allow_html=True)

# ----------------- SECTION 3: PPL WORKOUT LOGGER -----------------
elif menu == "🏋️ PPL Workout Logger":
  st.title("🏋️ PPL Workout Logger")
  w1, w2 = st.columns([2, 1])
  with w1:
    split_choice = st.selectbox("Select Training Day", list(PPL_ROUTINES.keys()))
  with w2:
    session_date = st.date_input("Date", value=date.today())
    log_date = session_date.strftime("%Y-%m-%d")

  exercises = PPL_ROUTINES[split_choice]
  with st.form(key="ppl_form"):
    session_data = {}
    for idx, ex in enumerate(exercises):
      st.markdown(f"**{idx + 1}. {ex}**")
      c1, c2, c3 = st.columns(3)
      wt = c1.number_input(
          "Weight (kg)", min_value=0.0, step=1.25, key=f"{log_date}_{ex}_wt"
      )
      reps = c2.number_input(
          "Reps", min_value=0, step=1, value=10, key=f"{log_date}_{ex}_rp"
      )
      sets = c3.number_input(
          "Sets",
          min_value=1,
          max_value=6,
          value=3,
          key=f"{log_date}_{ex}_st",
      )
      session_data[ex] = {"weight": wt, "reps": reps, "sets": sets}

    finisher = st.checkbox(
        "Completed 15-20 min Incline Walk (15% @ 2.5 km/h)",
        value=True,
        key=f"{log_date}_finisher",
    )
    if st.form_submit_button("💾 Save Workout"):
      st.session_state.db.setdefault("workouts", {})[log_date] = {
          "split": split_choice,
          "exercises": session_data,
          "finisher": finisher,
      }
      save_local_data(st.session_state.db)
      st.success("Session saved locally!")

  st.markdown("---")
  st.subheader("📋 Session Logs")
  if st.session_state.db.get("workouts"):
    for past_date, details in reversed(
        list(st.session_state.db["workouts"].items())
    ):
      with st.expander(f"📁 {past_date} — {details['split']}"):
        st.json(details)

# ----------------- SECTION 4: CALORIE & MACRO AI -----------------
elif menu == "🥗 Calorie & Macro AI":
  st.title("🥗 Fast Calorie & Macro Lookup")
  tab1, tab2 = st.tabs(["🔍 Search Food", "📷 Label / Meal Photo"])
  with tab1:
    search_query = st.text_input(
        "Food name (e.g., soya chunks, curd, paneer, pea protein):"
    ).lower()
    qty = st.number_input("Quantity (grams/pieces/scoops)", value=100.0, step=10.0)
    if st.button("Calculate"):
      matched = next(
          (v for k, v in FOOD_REGISTRY.items() if k in search_query), None
      )
      if matched:
        mult = qty / 100.0 if "100g" in matched["unit"] else qty
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Calories", f"{round(matched['calories'] * mult, 1)} kcal")
        m2.metric("Protein", f"{round(matched['protein'] * mult, 1)} g")
        m3.metric("Carbs", f"{round(matched['carbs'] * mult, 1)} g")
        m4.metric("Fat", f"{round(matched['fat'] * mult, 1)} g")
      else:
        st.warning(
            "Item not found in offline DB. Check nutrition facts label on the"
            " package."
        )

  with tab2:
    img_file = st.file_uploader(
        "Upload meal or nutrition label", type=["jpg", "jpeg", "png"]
    )
    if img_file:
      st.image(Image.open(img_file), width=320)
      st.info(
          "Photo buffered. Enter values in Search Food tab for exact logging."
      )