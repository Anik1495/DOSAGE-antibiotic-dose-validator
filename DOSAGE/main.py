import math
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from io import StringIO
from contextlib import asynccontextmanager
from typing import Optional
from pydantic import BaseModel, validator
import logging
from pathlib import Path

# --- 1. SETUP FOR ROBUST, ABSOLUTE FILE PATHS ---
# The published DOSAGE dataset is bundled locally instead of being pulled
# from a private database. Drop your CSV exports into the data/ folder
# (see data/README.md for the exact filenames and columns expected).
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
DATA_DIR = BASE_DIR / "data"


def load_csv_table(table_name: str) -> pd.DataFrame:
    """Load a dataset table from data/<table_name>.csv."""
    csv_path = DATA_DIR / f"{table_name}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(
            f"CRITICAL: Missing dataset file '{csv_path}'. "
            f"Place '{table_name}.csv' in the data/ directory before starting the app. "
            f"See data/README.md for details."
        )
    return pd.read_csv(csv_path)


# --- 2. PRELOAD DATA ON APP STARTUP (LIFESPAN MANAGER) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global normal_dose_data, standard_dose_data, pregnancy_risk_data, renal_data
    print("Starting data preloading...")
    normal_dose_data = load_csv_table("normal_dose")
    standard_dose_data = load_csv_table("standard_dose")
    pregnancy_risk_data = load_csv_table("pregnancy")
    renal_data = load_csv_table("renal_dose")
    print("Data preloading complete.")
    yield

app = FastAPI(lifespan=lifespan)

# --- 4. MOUNT STATIC DIRECTORY USING THE ROBUST PATH ---
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- 5. Pydantic Models for Data Validation ---
class MedicationData(BaseModel):
    generic: str
    disease: str
    administration: str
    dose_daily: float
    dose_unit: str
    age_unit: str
    age_number: float
    weight: float
    crcl_rate: Optional[float] = None

    @validator("dose_daily")
    def validate_dose(cls, v):
        if v <= 0:
            raise ValueError("Dose daily must be greater than 0.")
        return v

    @validator("weight")
    def validate_weight(cls, v):
        if v <= 0:
            raise ValueError("Weight must be greater than 0.")
        return v

    @validator("crcl_rate", pre=True)
    def clean_crcl(cls, v):
        if v in ["", None]:
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            raise ValueError("crcl_rate must be a number or left blank.")

# --- 6. ALL HELPER AND LOGIC FUNCTIONS (your full code) ---
def validate_range(value, min_value, max_value):
    """Check if a value falls within a specified range (handles NaN)."""
    if not pd.isna(min_value) and value < min_value:
        return False
    if not pd.isna(max_value) and value > max_value:
        return False
    return True

def validate_age(patient_row, dose_row):
    """
    Validate if the patient's age falls within the specified range.
    Assumes that dose data columns are named like: min_age_Y, max_age_Y, etc.
    """
    # We assume the patient sends age_unit as one of "Y", "M", or "D"
    unit = patient_row["age_unit"].upper()
    min_age = dose_row.get(f"min_age_{unit}")
    max_age = dose_row.get(f"max_age_{unit}")
    return validate_range(patient_row["age_number"], min_age, max_age)

def validate_weight(patient_row, dose_row):
    """Validate if the patient's weight falls within any of the weight ranges."""
    weight = patient_row["weight"]

    # If no weight is provided in the dataset, it's valid
    if pd.isna(weight):
        return False, "weight_missing", "Weight is missing, unable to validate weight.", None

    # Get the minimum and maximum weight ranges from the dose row
    min_weight = dose_row.get("min_weight")
    max_weight = dose_row.get("max_weight")

    # If both min_weight and max_weight are not provided, treat it as valid (no restrictions)
    if pd.isna(min_weight) and pd.isna(max_weight):
        return True, "valid", "No weight restrictions.", None

    # Check if the weight falls within the given weight range
    if not pd.isna(min_weight) and weight < min_weight:
        return False, "weight_too_low", f"Weight ({weight} kg) is below the minimum allowed ({min_weight} kg).", None
    if not pd.isna(max_weight) and weight > max_weight:
        return False, "weight_too_high", f"Weight ({weight} kg) exceeds the maximum allowed ({max_weight} kg).", None

    return True, "valid", "Weight is within valid range.", None

def handle_missing_weights(dose_row): ########
    """Handle missing weight columns. If min_weight is missing, assume it to be 0. If max_weight is missing, assume it to be a very large value."""
    if pd.isna(dose_row["min_weight"]) and pd.notna(dose_row["max_weight"]):
        dose_row["min_weight"] = 0  # If min_weight is missing, assume 0.
    elif pd.notna(dose_row["min_weight"]) and pd.isna(dose_row["max_weight"]):
        dose_row["max_weight"] = float('inf')  # If max_weight is missing, assume it is infinity (max possible weight).
    return dose_row

def validate_age_and_weight(patient_row, dose_row, is_standard=False):  ########
    """
    Validate both age and weight for a given patient and dose row.
    Handles missing weight fields and age group validation for both standard and normal dose data.
    """
    # Handle missing weight fields
    dose_row = handle_missing_weights(dose_row)

    # Validate age based on the normal or standard dosing regimen
    if not validate_age(patient_row, dose_row):
        return "age_missed", "Patient's age doesn't match the valid range.", None, None

    # Validate weight based on the given patient data and the dose row
    if not validate_weight(patient_row, dose_row):
        return "weight_missed", "Patient's weight doesn't match the valid range.", None, None

    return "valid", "Age and weight match the valid range.", None, None

def determine_dose_type_and_unit(dose_row):
    """Determine the dose type and unit based on available columns."""
    for dose_type in ["dw", "dd"]:
        for unit in ["mg", "UNIT"]:
            if (not pd.isna(dose_row.get(f"min_dose_{dose_type}_{unit}")) and
                not pd.isna(dose_row.get(f"max_dose_{dose_type}_{unit}"))):
                return dose_type, unit
    return None, None

def validate_dose_with_tolerance(patient_row, dose_row, dose_type, dose_unit):
    """Validate the patient's dose with a 15% tolerance and robust type checking."""
    dose = patient_row["dose_daily"]
    weight = patient_row["weight"]
    min_dose = None
    max_dose = None

    if dose_type == "dw":
        if pd.isna(weight) or weight <= 0:
            return False, "Weight Missing", "Weight-based dose cannot be calculated as patient weight is missing or zero.", None, None

        min_dose = dose_row.get(f"min_dose_{dose_type}_{dose_unit}") * weight
        max_dose = dose_row.get(f"max_dose_{dose_type}_{dose_unit}") * weight

    else:  # direct dose (dd)
        min_dose = dose_row.get(f"min_dose_{dose_type}_{dose_unit}")
        max_dose = dose_row.get(f"max_dose_{dose_type}_{dose_unit}")

    # Sanity check to ensure doses from the database are valid numbers before proceeding.
    if not isinstance(min_dose, (int, float)) or not isinstance(max_dose, (int, float)):
        return False, "Data Error", "Invalid dose data in database for this rule. Min/Max dose is not a number.", None, None

    # Apply 15% tolerance
    allowed_max_dose = max_dose * 1.15
    allowed_min_dose = min_dose * 0.85

    # Check for overdose or underdose with tolerance
    if dose > allowed_max_dose:
        # Using .2f to format the number nicely
        # --- Capitalization Change Here ---
        return False, "Overdose", f"Dose {dose} exceeds max limit ({max_dose:.2f}) by more than 15%.", dose - allowed_max_dose, None

    if dose < allowed_min_dose:
        # --- Capitalization Change Here ---
        return False, "Underdose", f"Dose {dose} is below minimum ({min_dose:.2f}) by more than 15%.", None, allowed_min_dose - dose

    # If it passes the checks above, it's valid.
    return True, "yes", "Dose is within the valid range, considering 15% tolerance.", None, None


# Normal Dose Validation
def process_normal_dose_with_tolerance(patient_row, dose_data, is_standard=False):
    """Process a single patient row against the given dose dataset considering 15% tolerance."""
    generic = patient_row["generic"]
    diseases_str = str(patient_row.get("disease", ""))
    diseases = [d.strip() for d in diseases_str.split(",")] if diseases_str else []
    administration = str(patient_row["administration"]).strip().lower()
    dose_unit = str(patient_row["dose_unit"]).strip()

    # Step 1: Filter by Generic Name
    generic_matched_data = dose_data[dose_data["generic"] == generic]
    if generic_matched_data.empty:
        return "no_match", f"No data found for generic: {generic}", None, None

    # Step 2: Filter by Disease
    # If is_standard, we ignore disease. Otherwise, we match it.
    if is_standard:
        disease_matched_data = generic_matched_data
    else:
        # This handles multiple diseases in the input correctly
        disease_matched_data = generic_matched_data[generic_matched_data["disease"].isin(diseases)]

    if disease_matched_data.empty:
        available_diseases = generic_matched_data["disease"].dropna().unique().tolist()
        return "no_match", f"No matching disease found for {generic}. Available diseases: {', '.join(available_diseases)}", None, None

    # Step 3: Filter by Administration Route
    admin_matched_data = disease_matched_data[
        disease_matched_data["administration"].str.strip().str.lower() == administration
    ]

    if admin_matched_data.empty:
        available_routes = disease_matched_data["administration"].dropna().unique()
        return (
            "Wrong Administration",
            f"Administration route '{administration.upper()}' is not valid for this generic/disease. Available routes are: {', '.join(available_routes)}.",
            None,
            None
        )

    # Step 4: Iterate through the final matched rows to find a valid rule
    for _, dose_row in admin_matched_data.iterrows():
        # Validate Age and Weight
        age_weight_result, age_weight_message, _, _ = validate_age_and_weight(patient_row, dose_row, is_standard)
        if age_weight_result != "valid":
            # If age/weight doesn't match this rule, continue to the next rule
            continue

        # Determine Dose Type and Unit for this rule
        dose_type, dose_unit_data = determine_dose_type_and_unit(dose_row)
        if dose_type is None or dose_unit_data.lower() != dose_unit.lower():
            # If dose unit/type doesn't match this rule, continue to the next rule
            continue

        # --- THIS IS THE FIX ---
        # Validate the dose itself using the tuple structure
        is_valid, result, message, excess, deficit = validate_dose_with_tolerance(patient_row, dose_row, dose_type, dose_unit_data)

        # If the dose is valid for this rule, we're done. Return this result.
        if is_valid:
            return result, message, excess, deficit

        # If it was an overdose/underdose/error for this rule, return that immediately.
        # This assumes the first matching rule is the one we should check against.
        return result, message, excess, deficit
        # --- END OF FIX ---

    # If the loop finishes, it means we matched generic/disease/admin, but no rule passed the age/weight/dose unit checks.
    return "no_valid_dose", "A matching rule was found, but the patient's age, weight, or dose unit was not applicable for any specific dose range.", None, None

# --- Renal Dose Processing Helpers ---
def is_in_range(value, min_val, max_val):
    if pd.isna(min_val) and pd.isna(max_val):
        return True
    if pd.isna(min_val):
        return value <= max_val
    if pd.isna(max_val):
        return value >= max_val
    return min_val <= value <= max_val

def check_not_required_flag(patient_row, renal_data):
    """Check if the recommendation_flag is 'Not Required' and skip further validation."""
    crcl = float(patient_row["crcl_rate"])
    not_required_rows = renal_data[
        (renal_data["generic"] == patient_row["generic"]) &
        (renal_data["recommendation_flag"] == "Not Required")
    ]
    if not not_required_rows.empty:
        return (
            f"No renal adjustment required for {patient_row['generic']}.",
            None,  # No renal dose adjustment required
            None
        )
    return None

def check_not_recommended_flag(patient_row, renal_data):
    """Check if the recommendation_flag is 'Not Recommended' and return a message accordingly."""
    crcl = float(patient_row["crcl_rate"])
    not_recommended_rows = renal_data[
        (renal_data["generic"] == patient_row["generic"]) &
        (renal_data["recommendation_flag"] == "Not Recommended")
    ]
    if not not_recommended_rows.empty:
        return (
            f"No dose recommended for {patient_row['generic']} based on CrCl range for {crcl} mL/min.",
            "no",  # Renal dose result should be "no"
            None
        )
    return None

# Renal Dose Validation
def process_renal_dose_with_tolerance(patient_row, renal_data):
    """
    Processes renal dose adjustment, with disease matching and messaging.
    """

    generic = patient_row["generic"]
    crcl = patient_row["crcl_rate"]
    weight = patient_row["weight"]
    dose = patient_row["dose_daily"]
    dose_unit = patient_row["dose_unit"]
    administration = str(patient_row["administration"]).strip().lower()
    diseases = [d.strip().lower() for d in str(patient_row.get("diseases", "")).split(",")] if "diseases" in patient_row else []

    # Handle missing CrCl
    if pd.isna(crcl):
        return "", "", None

    # 1. Check for "Not Required" flag (highest priority)
    generic_data = renal_data[renal_data["generic"] == generic]
    if generic_data.empty:
        return f"No renal dose data available for {generic}.", "Data Not Available", None

    if (generic_data["recommendation_flag"] == "Not Required").any():
        return f"No renal adjustment required for {generic} generic.", "Not Required", None

    # 2. Check CrCl coverage
    min_crcl_kb = generic_data["min_crcl"].min()
    max_crcl_kb = generic_data["max_crcl"].max()
    if crcl < min_crcl_kb or crcl > max_crcl_kb:
        return f"Data available for {generic} from CrCl {min_crcl_kb} to {max_crcl_kb} mL/min.", "Data Not Available", None

    # 3. Check if CrCl > 90
    if crcl > 90:
        return "No renal dose adjustment is typically needed for CrCl > 90 mL/min.", "Not Required", None

    # 4. Check if administration route is valid
    valid_administrations = generic_data["administration"].str.strip().str.lower().unique()
    if administration not in valid_administrations:
        return f"Administration Error: 'Valid routes administration route for {generic} are: {', '.join(valid_administrations)}.", "Administration Error", None

    # 5. Find matching row
    matching_row = None
    matched_disease = None

    for _, row in generic_data.iterrows():
        # Disease Match
        disease_match = False
        if not pd.isna(row["disease"]) and row["disease"] != "":
            for disease in diseases:
                if disease == str(row["disease"]).strip().lower():
                    disease_match = True
                    matched_disease = disease
                    break
            if not disease_match:
                continue

        # Administration Match
        if str(row["administration"]).strip().lower() != administration:
            continue

        # Weight Match
        if not pd.isna(row["min_weight"]) and not pd.isna(row["max_weight"]):
            min_weight = row["min_weight"]
            max_weight = row["max_weight"]
            if weight < min_weight or (not pd.isna(max_weight) and weight > max_weight):
                continue

        matching_row = row
        break

    # 6. Handle no matching criteria
    if matching_row is None:
        admin_display = str(patient_row["administration"]).strip() or "not specified"
        diseases_display = ', '.join(diseases) if diseases else "none"
        message = (
            f"No matching data found for {generic} at CrCl {crcl} mL/min. "
            f"Criteria used: administration '{admin_display}', "
            f"weight {weight} kg, disease(s): {diseases_display}."
        )
        return message, "Not Found", None

    # 7. Check "Not Recommended"
    if matching_row["recommendation_flag"] == "Not Recommended":
        message = f"Not recommended for {generic} for CrCl {min_crcl_kb} to {max_crcl_kb} mL/min."
        if matched_disease:
            message += f" (Matched disease: {matched_disease})"
        return message, "Not Recommended", None

    # 8. Dose calculation and validation
    max_dose = None
    dose_unit_lower = dose_unit.lower()

    if not pd.isna(matching_row["max_dose_dd_mg"]) and dose_unit_lower == "mg":
        max_dose = matching_row["max_dose_dd_mg"]
    elif not pd.isna(matching_row["max_dose_dw_mg"]) and dose_unit_lower == "mg":
        max_dose = matching_row["max_dose_dw_mg"] * weight
    elif not pd.isna(matching_row["max_dose_dd_UNIT"]) and dose_unit_lower == "unit":
        max_dose = matching_row["max_dose_dd_UNIT"]
    elif not pd.isna(matching_row["max_dose_dw_UNIT"]) and dose_unit_lower == "unit":
        max_dose = matching_row["max_dose_dw_UNIT"] * weight

    if max_dose is None:
        return "No valid dose information found in the database.", "Dose Info Missing", None

    allowed_max_dose = max_dose * 1.15  # 15% tolerance

    if dose > allowed_max_dose:
        excess_dose = dose - allowed_max_dose  # Calculate the exceeded amount
        message = f"Dose exceeds {allowed_max_dose:.2f} {dose_unit}, the maximum allowed limit."
        if matched_disease:
            message += f" (Matched disease: {matched_disease})"
        return message, "Overdose_Renal", excess_dose  # Return the exceeded amount

    message = "Renal dose is correct."
    if matched_disease:
        message += f" (Matched disease: {matched_disease})"
    return message, "Appropriate", None

# --- Combined Dose Processing ---
# In the process_all_doses function:
# Replace your entire existing process_all_doses function with this one.

def process_all_doses(patient_row, normal_dose_data, standard_dose_data, renal_data, pregnancy_risk_data):
    """
    Process patient data for normal/standard and renal dose adjustments.
    """
    # Add pregnancy risk category.
    pregnancy_risk = "Unknown"
    risk_row = pregnancy_risk_data[pregnancy_risk_data["generic"] == patient_row["generic"]]
    if not risk_row.empty:
        pregnancy_risk = risk_row.iloc[0]["pregnancy_risk"]

    # --- THIS IS THE FIX ---
    # Process normal dose and correctly unpack the returned tuple.
    result, message, excess, deficit = process_normal_dose_with_tolerance(
        patient_row, normal_dose_data, is_standard=False
    )

    # If the first check resulted in "no_match", try again with standard dose data.
    if result == "no_match":
        result, message, excess, deficit = process_normal_dose_with_tolerance(
            patient_row, standard_dose_data, is_standard=True
        )
    # --- END OF FIX ---

    # Build the combined output dictionary.
    combined = {}
    combined["pregnancy_risk_category"] = pregnancy_risk

    # Set default keys
    combined["normal_dose_result"] = "yes"
    combined["normal_dose_message"] = "Dose is appropriate."
    combined["dose_excess"] = None
    combined["dose_deficit"] = None

    # Overwrite defaults if there was an issue with the normal dose.
    if result != "yes":
        combined["normal_dose_result"] = result
        combined["normal_dose_message"] = message
        if result == "overdose":
            combined["dose_excess"] = excess
        elif result == "underdose":
            combined["dose_deficit"] = deficit

    # --- Renal Dose Processing Section ---
    # Handle CrCl being missing or null for the output
    if "crcl_rate" not in patient_row or pd.isna(patient_row.get("crcl_rate")):
        combined["renal_dose_result"] = "Not Provided"
        combined["renal_dose_message"] = "CrCl rate was not provided; renal dose cannot be calculated."
        combined["renal_dose_exceeded_amount"] = None
    else:
        # Process renal dose only if crcl_rate is present and valid
        renal_message, renal_result, renal_exceeded = process_renal_dose_with_tolerance(patient_row, renal_data)
        combined["renal_dose_result"] = renal_result
        combined["renal_dose_message"] = renal_message
        combined["renal_dose_exceeded_amount"] = renal_exceeded

    # The original "if not combined:" check is no longer needed as `combined` is always populated.
    return combined


# --- Helper Function for JSON Serialization: Replace NaN with None ---
def replace_nan(obj):
    if isinstance(obj, dict):
        return {k: replace_nan(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [replace_nan(item) for item in obj]
    elif isinstance(obj, float) and math.isnan(obj):
        return None
    else:
        return obj

# --- Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def index():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/generic_names")
async def get_generic_names():
    try:
        unique_generics = normal_dose_data["generic"].dropna().unique().tolist()
        unique_generics.sort()
        return JSONResponse(content={"generic_names": unique_generics})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/disease_names")
async def get_disease_names(generic: str):
    try:
        generic_lower = generic.lower()
        df = normal_dose_data[normal_dose_data["generic"].str.lower() == generic_lower]
        diseases = df["disease"].dropna().unique().tolist()
        diseases.sort()
        return JSONResponse(content={"disease_names": diseases})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/validate_medication/")
async def validate_medication(data: MedicationData):
    # --- START NEW DEBUGGING CODE ---
    logging.basicConfig(level=logging.INFO)
    logging.info(f"Received single validation request with data: {data.dict()}")
    # --- END NEW DEBUGGING CODE ---
    try:
        patient_row = data.dict()
        result = process_all_doses(patient_row, normal_dose_data, standard_dose_data, renal_data, pregnancy_risk_data)
        logging.info(f"Successfully processed. Result: {result}") # Log success too
        return JSONResponse(content={"validation_result": replace_nan(result)})
    except Exception as e:
        # --- IMPROVED ERROR LOGGING ---
        logging.error(f"Error during single medication validation: {e}", exc_info=True)
        # The line above (exc_info=True) will print the full traceback to your console.
        return JSONResponse(content={"error": str(e)}, status_code=500) # Changed to 500 for internal errors


# In the /validate_batch/ endpoint:
@app.post("/validate_batch/")
async def validate_batch(file: UploadFile = File(...)):
    try:
        if "csv" not in file.content_type.lower():
            raise HTTPException(status_code=400, detail="File must be a CSV")
        file_content = await file.read()
        try:
            df = pd.read_csv(StringIO(file_content.decode("utf-8")), low_memory=False)
            df = df.loc[:, ~df.columns.duplicated()]
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error parsing CSV file: {str(e)}")
        required_columns = [
            "generic", "administration", "dose_daily", "dose_unit",
            "age_unit", "age_number", "disease", "weight"
        ]
        # For batch, crcl_rate is optional.
        if "crcl_rate" in df.columns:
            required_columns.append("crcl_rate")
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(status_code=400, detail=f"Missing required columns: {', '.join(missing_columns)}")
        df = df[required_columns]
        for col in ["age_number", "weight", "dose_daily"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        # For crcl_rate, convert it without fillna(0) so that missing values remain NaN.
        if "crcl_rate" in df.columns:
            df["crcl_rate"] = pd.to_numeric(df["crcl_rate"], errors="coerce")
        input_data = df.to_dict(orient="records")
        results = []
        for patient_row in input_data:
            try:
                processed_row = process_all_doses(patient_row, normal_dose_data, standard_dose_data, renal_data, pregnancy_risk_data)
                results.append({"row": patient_row, "result": processed_row})
            except Exception as e:
                results.append({"row": patient_row, "error": str(e)})
        response_data = {"input_data": input_data, "results": results}
        response_data = replace_nan(response_data)
        return JSONResponse(content=response_data)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
