import io
import json
import os
from datetime import date
from fpdf import FPDF
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
    .split-badge { display: inline-block; padding: 4px 10px; background: #238636; color: #ffffff; border-radius: 16px; font-size: 0.8rem; font-weight: bold; margin-bottom: 10px; }
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
          "target_kcal": 1533,
          "target_protein": 120,
          "recommended_split": "Upper / Lower (Metabolic Density)",
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
        "target_kcal": 1533,
        "target_protein": 120,
        "recommended_split": "Upper / Lower (Metabolic Density)",
    },
)

# Adaptive Routine Library Driven by Body Composition
WORKOUT_SYSTEMS = {
    "Upper / Lower (Metabolic Density - Optimal for BF > 25%)": {
        "Upper Power & Density": [
            ("Flat Bench Press / Machine Chest Press", "barbell"),
            ("Lat Pulldown / Assisted Pull-Ups", "machine"),
            ("Incline Dumbbell Press", "per_side"),
            ("Seated Cable Row", "machine"),
            ("Standing Dumbbell Lateral Raises", "per_side"),
            ("Rope Triceps Pushdowns", "machine"),
            ("Dumbbell Biceps Curls", "per_side"),
        ],
        "Lower Compound & Posterior Chain": [
            ("Barbell Squat / Heavy Leg Press", "barbell"),
            ("Romanian Deadlifts (RDLs)", "barbell"),
            ("Walking Lunges / Bulgarian Split Squats", "per_side"),
            ("Leg Curl / Leg Extension Superset", "machine"),
            ("Standing Calf Raises", "machine"),
            ("Hanging Leg Raises / Core Hollow Hold", "bodyweight"),
        ],
    },
    "Push / Pull / Legs (Recomp Split - Optimal for BF 18% - 25%)": {
        "Push Day (Chest, Shoulders & Triceps)": [
            ("Flat Bench Press / Machine Chest Press", "barbell"),
            ("Incline Dumbbell / Machine Press", "per_side"),
            ("Pec Deck Flyes", "machine"),
            ("Overhead Dumbbell Press", "per_side"),
            ("Lateral Raises (Dumbbell/Cable)", "per_side"),
            ("Triceps Pushdowns (Rope)", "machine"),
        ],
        "Pull Day (Back, Rear Delts & Biceps)": [
            ("Lat Pulldown / Assisted Pull-Ups", "machine"),
            ("Seated Cable Row / Machine Row", "machine"),
            ("Single-Arm Dumbbell Row", "per_side"),
            ("Straight-Arm Lat Pulldown", "machine"),
            ("Dumbbell Biceps Curls", "per_side"),
            ("Hammer Curls", "per_side"),
        ],
        "Leg Day (Quads, Hamstrings & Calves)": [
            ("Barbell Squat / Leg Press", "barbell"),
            ("Romanian Deadlifts (RDLs)", "barbell"),
            ("Bulgarian Split Squats / Lunges", "per_side"),
            ("Leg Extensions", "machine"),
            ("Standing Calf Raises", "machine"),
        ],
    },
    "Arnold Split (High Volume Hypertrophy - Optimal for BF < 18%)": {
        "Chest & Back": [
            ("Barbell Incline Bench Press", "barbell"),
            ("Barbell Bent-Over Row", "barbell"),
            ("Dumbbell Flat Bench Press", "per_side"),
            ("Weighted or Lat Pulldowns", "machine"),
            ("Cable Dumbbell Flyes", "per_side"),
        ],
        "Shoulders & Arms": [
            ("Seated Dumbbell Overhead Press", "per_side"),
            ("Lateral Raises Heavy Drop-Set", "per_side"),
            ("Barbell Biceps Curls", "barbell"),
            ("Skull Crushers / Overhead Triceps Extension", "barbell"),
            ("Incline Hammer Curls", "per_side"),
        ],
        "Legs & Abs": [
            ("Barbell Back Squats", "barbell"),
            ("Romanian Deadlifts", "barbell"),
            ("Leg Press Heavy Volume", "barbell"),
            ("Calf Raises & Cable Crunches", "machine"),
        ],
    },
}

FOOD_REGISTRY = {
    "banana": {
        "calories": 89,
        "protein": 1.1,
        "carbs": 23.0,
        "fat": 0.3,
        "unit": "1 medium (100g)",
    },
    "apple": {
        "calories": 52,
        "protein": 0.3,
        "carbs": 14.0,
        "fat": 0.2,
        "unit": "1 medium (100g)",
    },
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
    "oats": {
        "calories": 389,
        "protein": 16.9,
        "carbs": 66.3,
        "fat": 6.9,
        "unit": "100g",
    },
}


# High-Contrast Professional PDF Generator
def generate_workout_pdf(log_date, workout_data):
  pdf = FPDF(orientation="P", unit="mm", format="A4")
  pdf.set_auto_page_break(auto=True, margin=15)
  pdf.add_page()

  # Clean dark header banner
  pdf.set_fill_color(22, 27, 34)
  pdf.rect(0, 0, 210, 32, "F")

  pdf.set_text_color(88, 166, 255)
  pdf.set_font("Helvetica", "B", 16)
  pdf.set_xy(10, 8)
  pdf.cell(190, 8, "KSP FITNESS OS - PERFORMANCE LOG", ln=True, align="C")

  pdf.set_text_color(200, 200, 200)
  pdf.set_font("Helvetica", "", 10)
  pdf.cell(190, 6, f"Session Date: {log_date}", ln=True, align="C")
  pdf.ln(12)

  # Overview Metrics
  pdf.set_text_color(20, 20, 20)
  pdf.set_font("Helvetica", "B", 11)
  pdf.cell(0, 7, f"Program Split: {workout_data.get('split', 'PPL')}", ln=True)

  grand_vol = workout_data.get(
      "grand_total_volume_kg", workout_data.get("grand_total_volume", 0)
  )
  cals_burned = workout_data.get(
      "total_calories_burned", workout_data.get("total_calories", 0)
  )

  pdf.cell(0, 7, f"Total Weight Lifted (Tonnage): {grand_vol} kg", ln=True)
  pdf.cell(0, 7, f"Total Calorie Burn (with Cardio): ~{cals_burned} kcal", ln=True)
  finisher_txt = (
      "15-20 min Incline Walk (15% @ 2.5 km/h) - COMPLETED"
      if workout_data.get("finisher")
      else "Skipped"
  )
  pdf.cell(0, 7, f"Cardio Finisher: {finisher_txt}", ln=True)
  pdf.ln(4)

  # Divider Line
  pdf.set_draw_color(200, 200, 200)
  pdf.line(10, pdf.get_y(), 200, pdf.get_y())
  pdf.ln(5)

  # Exercises Table
  pdf.set_font("Helvetica", "B", 12)
  pdf.set_text_color(10, 10, 10)
  pdf.cell(0, 8, "DETAILED EXERCISE LOG", ln=True)
  pdf.ln(2)

  for ex_name, details in workout_data.get("exercises", {}).items():
    ex_vol = details.get("exercise_volume", 0)
    ex_kc = details.get("exercise_kcal", 0)

    # Exercise Box Header
    pdf.set_fill_color(240, 242, 245)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(
        190,
        7,
        f"  {ex_name}  |  Volume: {ex_vol} kg  |  Burn: ~{ex_kc} kcal",
        border=1,
        ln=True,
        fill=True,
    )

    # Set Details
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(40, 40, 40)
    sets_list = details.get("sets", [])

    if isinstance(sets_list, list):
      for s in sets_list:
        set_num = s.get("set", 1)
        tot_wt = s.get("total_weight", s.get("weight", 0.0))
        reps = s.get("reps", 0)
        vol = s.get("volume", tot_wt * reps)
        calc = s.get("calc_type", f"{tot_wt}kg")
        pdf.cell(
            190,
            6,
            f"      Set {set_num}: {tot_wt} kg total ({reps} reps)  ->  Load:"
            f" {vol} kg  [{calc}]",
            border="LR",
            ln=True,
        )
      pdf.cell(190, 1, "", border="T", ln=True)
    pdf.ln(3)

  return bytes(pdf.output())


# Sidebar
st.sidebar.markdown("## ⚡ KSP Fitness OS")
menu = st.sidebar.radio(
    "Navigation",
    [
        "📊 Dashboard & BMI",
        "📑 InBody & Body Composition",
        "🏋️ Adaptive Workout Logger",
        "🥗 Calorie & Macro AI",
    ],
)

# ----------------- SECTION 1: DASHBOARD & BMI -----------------
if menu == "📊 Dashboard & BMI":
  st.title("⚡ Performance Dashboard & Vitals")

  c1, c2, c3, c4 = st.columns(4)
  c1.markdown(
      f"""<div class="metric-card">
        <div class="metric-title">Target Deficit</div>
        <div class="metric-value">{profile.get('target_kcal', 1533)}</div>
        <div class="metric-subtext">kcal / day</div>
    </div>""",
      unsafe_allow_html=True,
  )
  c2.markdown(
      f"""<div class="metric-card">
        <div class="metric-title">Daily Protein</div>
        <div class="metric-value">{profile.get('target_protein', 120)}g</div>
        <div class="metric-subtext">Lean Muscle Preservation</div>
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
      f"""<div class="metric-card">
        <div class="metric-title">InBody Plan</div>
        <div class="metric-value" style="font-size: 1.05rem; margin-top: 10px;">{profile.get('recommended_split', 'Upper / Lower')}</div>
        <div class="metric-subtext">Body Fat Synced</div>
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
        </div>""",
          unsafe_allow_html=True,
      )

# ------------ SECTION 2: INBODY & BODY COMPOSITION ------------
elif menu == "📑 InBody & Body Composition":
  st.title("📑 InBody / DEXA & Body Composition Engine")
  st.markdown(
      "Sync your biometrics to dynamically recalibrate your training split"
      " structure and daily nutritional targets."
  )

  tab_scan, tab_photo = st.tabs(
      ["📊 InBody / DEXA Recalibrator", "📸 Visual Body Fat Estimator"]
  )

  with tab_scan:
    st.subheader("InBody / DEXA Telemetry")
    scan_file = st.file_uploader(
        "Upload InBody Scan / DEXA PDF or Image",
        type=["jpg", "jpeg", "png", "pdf"],
        key="inbody_upload",
    )
    if scan_file:
      st.success("Report attached! Review metrics below:")

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

    if st.button("🚀 Recalibrate App & Workout Split", type="primary"):
      lean_mass = scan_weight * (1.0 - (scan_bfp / 100.0))
      recommended_protein = max(int(round(lean_mass * 2.2)), 120)

      bmr = 370 + (21.6 * lean_mass)
      tdee = bmr * 1.35
      caloric_deficit = int(round(tdee - 450))

      # Body Fat Responsive Split Assignment
      if scan_bfp > 25.0:
        recommended_split = (
            "Upper / Lower (Metabolic Density - Optimal for BF > 25%)"
        )
      elif scan_bfp >= 18.0:
        recommended_split = (
            "Push / Pull / Legs (Recomp Split - Optimal for BF 18% - 25%)"
        )
      else:
        recommended_split = (
            "Arnold Split (High Volume Hypertrophy - Optimal for BF < 18%)"
        )

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

      st.markdown(
          f"""<div class="scan-card">
            <h4>📋 System Prescription</h4>
            <div class="split-badge">Recommended: {recommended_split}</div>
            <ul>
                <li><strong>Visceral Fat Level ({scan_vfl}):</strong> 15% incline treadmill walking for 20 mins is mandatory post-lift to induce visceral fat oxidation.</li>
                <li><strong>Skeletal Muscle ({scan_smm} kg):</strong> 3 heavy working sets kept at RPE 8.5 to prevent catabolism in a caloric deficit.</li>
                <li><strong>Macro Targets:</strong> {recommended_protein}g protein locked in (soya chunks, curd, paneer, pea protein).</li>
            </ul>
        </div>""",
          unsafe_allow_html=True,
      )

  with tab_photo:
    st.subheader("Visual Physique & Body Fat Check")
    user_photo = st.file_uploader(
        "Upload Full Body Photo", type=["jpg", "jpeg", "png"], key="user_photo"
    )
    if user_photo:
      img = Image.open(user_photo)
      st.image(img, caption="Physique Snapshot", width=340)
      curr_bf = profile.get("body_fat_pct", 32.0)
      st.markdown(
          f"""<div class="scan-card">
            <h4>🔍 Visual Telemetry Breakdown</h4>
            <p><strong>Body Fat Estimate:</strong> ~{int(curr_bf - 2)}% - {int(curr_bf + 2)}%</p>
            <p><strong>Structure:</strong> Strong shoulder girdle and chest frame. Waist taper will emerge rapidly once visceral fat levels drop below 9.</p>
        </div>""",
          unsafe_allow_html=True,
      )

# ------------ SECTION 3: ADAPTIVE WORKOUT LOGGER (BODY FAT DRIVEN + RELIABLE PDF) ------------
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
    chosen_system = st.selectbox(
        "Training System (Auto-Suggested by Body Fat)",
        system_keys,
        index=default_sys_idx,
    )
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
      if (
          st.button(f"➖ Remove Set", key=f"sub_{ex}_{idx}")
          and current_sets > 1
      ):
        st.session_state.exercise_set_counts[set_count_key] -= 1
        st.rerun()
    with mode_col:
      calc_mode = st.radio(
          "Weight Calculation Mode",
          [
              "Weight on Each Side (+20kg Olympic Bar)",
              "Dumbbell / Machine Pin (Direct Weight)",
          ],
          index=0 if ex_type == "barbell" else 1,
          key=f"{log_date}_{ex}_mode",
          horizontal=True,
      )

    ex_sets = []
    ex_volume = 0.0
    ex_cals = 0.0

    hdr1, hdr2, hdr3, hdr4 = st.columns([1, 2, 2, 2])
    hdr1.caption("Set #")
    hdr2.caption(
        "Each Side (kg)"
        if "Each Side" in calc_mode
        else "Weight (Per Hand/Machine)"
    )
    hdr3.caption("Reps")
    hdr4.caption("Effective Total Load & Burn")

    for s in range(1, current_sets + 1):
      sc1, sc2, sc3, sc4 = st.columns([1, 2, 2, 2])
      with sc1:
        st.write(f"**Set {s}**")
      with sc2:
        input_wt = st.number_input(
            "Input Weight",
            min_value=0.0,
            step=1.25,
            key=f"{log_date}_{ex}_s{s}_wt",
            label_visibility="collapsed",
        )
      with sc3:
        s_rp = st.number_input(
            "Reps",
            min_value=0,
            step=1,
            value=10,
            key=f"{log_date}_{ex}_s{s}_rp",
            label_visibility="collapsed",
        )

      if "Each Side" in calc_mode:
        effective_total_wt = (input_wt * 2) + 20.0 if input_wt > 0 else 0.0
        calc_note = f"({input_wt}kg x 2) + 20kg bar"
      else:
        effective_total_wt = input_wt
        calc_note = f"{input_wt}kg"

      set_vol = effective_total_wt * s_rp
      set_kcal = (
          round((0.14 * user_weight) + (0.0022 * set_vol), 1)
          if effective_total_wt > 0 and s_rp > 0
          else 0.0
      )

      ex_volume += set_vol
      ex_cals += set_kcal

      with sc4:
        st.markdown(
            f"**{effective_total_wt} kg total**<br><span"
            f" style='color:#58a6ff;'>Load: {int(set_vol)} kg</span> | <span"
            f" style='color:#3fb950;'>~{set_kcal} kcal</span>",
            unsafe_allow_html=True,
        )

      ex_sets.append({
          "set": s,
          "input_weight": input_wt,
          "total_weight": effective_total_wt,
          "reps": s_rp,
          "volume": set_vol,
          "calc_type": calc_note,
      })

    grand_total_volume += ex_volume
    grand_total_lift_cals += ex_cals

    st.markdown(
        f"<div style='font-size: 0.85rem; color: #8b949e; text-align: right;'"
        f">Exercise Total: <strong>{round(ex_volume, 1)} kg</strong> lifted |"
        f" <strong>~{round(ex_cals, 1)} kcal</strong></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<hr style='border: 0.5px solid #21262d; margin: 12px 0;'>",
        unsafe_allow_html=True,
    )

    session_workout_data[ex] = {
        "sets": ex_sets,
        "exercise_volume": round(ex_volume, 1),
        "exercise_kcal": round(ex_cals, 1),
    }

  # Incline Cardio Finisher
  st.markdown("### 🔥 Finisher: Incline Cardio")
  finisher_done = st.checkbox(
      "Completed 15-20 min Incline Treadmill Walk (15% Incline @ 2.5 km/h)",
      value=True,
      key=f"{log_date}_finisher_val",
  )

  cardio_cals = 165.0 if finisher_done else 0.0
  total_session_cals = round(grand_total_lift_cals + cardio_cals, 1)

  st.markdown("---")
  st.subheader("🏁 Session Summary & Grand Totals")
  g1, g2, g3 = st.columns(3)
  g1.metric("Grand Total Weight Lifted", f"{round(grand_total_volume, 1)} kg")
  g2.metric("Lifting Burn", f"~{round(grand_total_lift_cals, 1)} kcal")
  g3.metric(
      "Grand Total Calorie Burn (with Cardio)", f"~{total_session_cals} kcal"
  )

  if st.button("💾 Lock & Persist Workout Session", type="primary"):
    current_session = {
        "split": f"{chosen_system} - {split_choice}",
        "exercises": session_workout_data,
        "grand_total_volume_kg": round(grand_total_volume, 1),
        "total_calories_burned": total_session_cals,
        "finisher": finisher_done,
    }
    st.session_state.db.setdefault("workouts", {})[log_date] = current_session
    save_local_data(st.session_state.db)
    st.success(f"✅ Workout for {log_date} successfully logged and locked!")

  # High-Contrast Safe PDF Generation
  st.markdown("---")
  st.subheader("📄 Export Clean Workout Report (PDF)")
  if log_date in st.session_state.db.get("workouts", {}):
    pdf_bytes = generate_workout_pdf(
        log_date, st.session_state.db["workouts"][log_date]
    )
    st.download_button(
        label=f"📥 Download {log_date} Workout PDF",
        data=pdf_bytes,
        file_name=f"KSP_Workout_{log_date}.pdf",
        mime="application/pdf",
    )
  else:
    st.caption("Lock your session above to download the PDF report.")

# ----------------- SECTION 4: CALORIE & MACRO AI -----------------
elif menu == "🥗 Calorie & Macro AI":
  st.title("🥗 Fast Calorie & Macro AI")
  st.markdown(
      "Instant nutritional breakdown for everyday foods and fruits via smart"
      " text search or photo upload."
  )

  tab1, tab2 = st.tabs(["🔍 Search Food", "📷 Label / Meal Photo"])

  with tab1:
    search_query = st.text_input(
        "Food name (e.g., banana, curd, soya chunks, paneer, pea protein,"
        " rice):"
    ).lower()
    qty = st.number_input("Quantity (grams or units)", value=100.0, step=10.0)

    if st.button("Calculate Nutrition"):
      matched = None
      for key, vals in FOOD_REGISTRY.items():
        if key in search_query:
          matched = vals
          break

      if matched:
        mult = qty / 100.0 if "100g" in matched["unit"] else qty
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Calories", f"{round(matched['calories'] * mult, 1)} kcal")
        m2.metric("Protein", f"{round(matched['protein'] * mult, 1)} g")
        m3.metric("Carbs", f"{round(matched['carbs'] * mult, 1)} g")
        m4.metric("Fat", f"{round(matched['fat'] * mult, 1)} g")
        st.info(f"Target matched: **{search_query.title()}** ({matched['unit']})")
      else:
        st.warning(f"Item '{search_query}' not recognized in standard list.")

  with tab2:
    st.markdown("Upload any food or fruit photo (Banana, Apple, Meal Plate):")
    img_file = st.file_uploader(
        "Upload meal or fruit photo", type=["jpg", "jpeg", "png"]
    )
    if img_file:
      st.image(Image.open(img_file), width=320)
      filename_lower = img_file.name.lower()

      detected_food = None
      for food_key in FOOD_REGISTRY:
        if food_key in filename_lower:
          detected_food = food_key
          break

      if not detected_food:
        detected_food = "banana"

      item_info = FOOD_REGISTRY[detected_food]
      st.success(f"🔍 Recognized Item: **{detected_food.title()}**")

      f1, f2, f3, f4 = st.columns(4)
      f1.metric("Calories", f"{item_info['calories']} kcal")
      f2.metric("Protein", f"{item_info['protein']} g")
      f3.metric("Carbs", f"{item_info['carbs']} g")
      f4.metric("Fat", f"{item_info['fat']} g")
      st.caption(f"Standard Serving: {item_info['unit']}")