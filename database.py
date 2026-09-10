# =============================================================================
# FILE: database.py
# PURPOSE: Data Layer - Loads the REAL Pima Indians Diabetes Dataset from
#          the local CSV file into a SQLite database using SQLAlchemy ORM.
#
# DATASET: Pima Indians Diabetes Database (768 patient records)
# SOURCE:  Originally from the National Institute of Diabetes and Digestive
#          and Kidney Diseases. Available on Kaggle / UCI ML Repository.
#
# COLUMNS (8 features + 1 label):
#   1. Pregnancies              - Number of times pregnant
#   2. Glucose                  - Plasma glucose concentration (mg/dL)
#   3. BloodPressure            - Diastolic blood pressure (mm Hg)
#   4. SkinThickness            - Triceps skin fold thickness (mm)
#   5. Insulin                  - 2-Hour serum insulin (mu U/ml)
#   6. BMI                      - Body mass index (kg/m^2)
#   7. DiabetesPedigreeFunction - Diabetes pedigree function (genetic risk score)
#   8. Age                      - Age (years)
#   9. Outcome                  - 1 = diabetic, 0 = not diabetic (TARGET LABEL)
# =============================================================================

# --- Standard Library Imports ---
import os      # For checking if the CSV file exists

# --- Third-Party Library Imports ---
import pandas as pd  # For reading the CSV file
import numpy as np   # For numerical operations

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    Float,
    String,
    ForeignKey,
)
from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
    relationship,
)


# =============================================================================
# STEP 1: DATABASE ENGINE AND BASE MODEL
# =============================================================================

# Connect to (or create) the local SQLite database file.
engine = create_engine("sqlite:///clinical_data.db", echo=False)

# All ORM table classes must inherit from this Base.
Base = declarative_base()


# =============================================================================
# STEP 2: DEFINE DATABASE TABLES AS PYTHON CLASSES
# =============================================================================

# --- Table 1: patients ---
# Stores patient-level demographic info (age from the Pima dataset).
# The Pima dataset does not have a separate gender column, so we set a default.
class Patient(Base):
    """Represents the 'patients' table. One row = one patient."""
    __tablename__ = "patients"

    patient_id = Column(Integer, primary_key=True, autoincrement=True)
    age = Column(Integer, nullable=False)
    # Pima dataset is exclusively female patients (Pima Indian women)
    gender = Column(String(10), nullable=False, default="Female")

    # Python-level relationship: patient.records --> list of DiagnosticRecords
    records = relationship("DiagnosticRecord", back_populates="patient")


# --- Table 2: diagnostic_records ---
# Stores all 8 clinical features + the actual diagnosis label for each patient.
class DiagnosticRecord(Base):
    """
    Represents the 'diagnostic_records' table.
    Each row holds the full set of clinical measurements for one patient visit.
    All 8 Pima dataset features are stored here.
    """
    __tablename__ = "diagnostic_records"

    record_id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key linking this record to a specific patient
    patient_id = Column(Integer, ForeignKey("patients.patient_id"), nullable=False)

    # --- All 8 Pima Dataset Features ---
    pregnancies = Column(Float, nullable=False)              # Number of pregnancies
    glucose = Column(Float, nullable=False)                  # Plasma glucose (mg/dL)
    blood_pressure = Column(Float, nullable=False)           # Diastolic BP (mm Hg)
    skin_thickness = Column(Float, nullable=False)           # Triceps skin fold (mm)
    insulin = Column(Float, nullable=False)                  # Serum insulin (mu U/ml)
    bmi = Column(Float, nullable=False)                      # Body mass index (kg/m^2)
    diabetes_pedigree = Column(Float, nullable=False)        # Genetic risk score
    actual_diagnosis = Column(Integer, nullable=False)       # 1 = diabetic, 0 = not

    # Python-level relationships
    patient = relationship("Patient", back_populates="records")
    prediction = relationship("ModelPrediction", back_populates="record", uselist=False)


# --- Table 3: model_predictions ---
# Stores the probabilistic OUTPUT of our neural network for each record.
class ModelPrediction(Base):
    """
    Represents the 'model_predictions' table.
    Stores the Monte Carlo Dropout output (mean prediction + uncertainty variance)
    for each diagnostic record that has been assessed by the model.
    """
    __tablename__ = "model_predictions"

    prediction_id = Column(Integer, primary_key=True, autoincrement=True)
    record_id = Column(Integer, ForeignKey("diagnostic_records.record_id"), nullable=False)

    # The average of the 50 Monte Carlo prediction samples
    mean_prediction = Column(Float, nullable=False)

    # The variance of those 50 samples -- our measure of uncertainty
    uncertainty_variance = Column(Float, nullable=False)

    # Human-readable classification: "FLAG_FOR_DOCTOR", "HIGH_CONFIDENCE_POSITIVE",
    # or "HIGH_CONFIDENCE_NEGATIVE"
    risk_tier = Column(String(30), nullable=False)

    record = relationship("DiagnosticRecord", back_populates="prediction")


# =============================================================================
# STEP 3: CREATE ALL TABLES IN THE DATABASE
# =============================================================================

# Safely creates all tables defined above. If they already exist, does nothing.
Base.metadata.create_all(engine)

# Session factory -- used to open database transactions
SessionLocal = sessionmaker(bind=engine)


# =============================================================================
# STEP 4: LOAD THE PIMA INDIANS CSV INTO THE DATABASE
# =============================================================================

# The standard column names for the Pima Indians Diabetes Dataset.
# The CSV file has NO header row, so we supply these names manually.
PIMA_COLUMN_NAMES = [
    "Pregnancies",
    "Glucose",
    "BloodPressure",
    "SkinThickness",
    "Insulin",
    "BMI",
    "DiabetesPedigreeFunction",
    "Age",
    "Outcome",
]

# Path to the CSV file (must be in the same directory as this script)
CSV_FILE_PATH = "pima-indians-diabetes.csv"


def load_pima_data_into_db():
    """
    Reads the Pima Indians Diabetes CSV file and inserts all 768 rows
    into the SQLite database (patients + diagnostic_records tables).

    This function is IDEMPOTENT: if the database already has data,
    it skips insertion to avoid duplicates on every app restart.
    """
    # --- Guard: Check the CSV file exists ---
    if not os.path.exists(CSV_FILE_PATH):
        raise FileNotFoundError(
            f"Could not find '{CSV_FILE_PATH}' in the current directory.\n"
            f"Please download the Pima Indians Diabetes dataset CSV and place it here."
        )

    session = SessionLocal()

    # If the DB already has patient records, skip re-loading
    existing_count = session.query(Patient).count()
    if existing_count > 0:
        print(f"[INFO] Database already contains {existing_count} records. Skipping CSV load.")
        session.close()
        return

    print(f"[INFO] Loading Pima Indians Diabetes dataset from '{CSV_FILE_PATH}'...")

    # --- Read the CSV into a Pandas DataFrame ---
    # `header=None` tells pandas there is no header row in the file.
    # `names=PIMA_COLUMN_NAMES` assigns our column names to each column.
    df = pd.read_csv(CSV_FILE_PATH, header=None, names=PIMA_COLUMN_NAMES)

    print(f"[INFO] Dataset loaded: {len(df)} rows, {len(df.columns)} columns.")
    print(f"[INFO] Positive diagnoses: {df['Outcome'].sum()} / {len(df)} "
          f"({df['Outcome'].mean()*100:.1f}%)")

    # --- Insert each row into the database ---
    # We iterate row by row, creating a Patient and a DiagnosticRecord for each.
    for index, row in df.iterrows():

        # Create the Patient object using the Age from the dataset.
        # All Pima patients are female (the study was conducted on Pima Indian women).
        new_patient = Patient(
            age=int(row["Age"]),
            gender="Female",
        )
        session.add(new_patient)

        # `flush()` sends the INSERT to the DB within the current transaction
        # so we can get back the auto-generated patient_id for the next table.
        session.flush()

        # Create the DiagnosticRecord with all 8 clinical features
        new_record = DiagnosticRecord(
            patient_id=new_patient.patient_id,
            pregnancies=float(row["Pregnancies"]),
            glucose=float(row["Glucose"]),
            blood_pressure=float(row["BloodPressure"]),
            skin_thickness=float(row["SkinThickness"]),
            insulin=float(row["Insulin"]),
            bmi=float(row["BMI"]),
            diabetes_pedigree=float(row["DiabetesPedigreeFunction"]),
            actual_diagnosis=int(row["Outcome"]),
        )
        session.add(new_record)

    # Commit (save) all 768 inserts to the database file in one transaction.
    # If anything goes wrong, SQLAlchemy will automatically roll back.
    session.commit()
    print(f"[INFO] Successfully inserted {len(df)} patient records into the database.")
    session.close()


# =============================================================================
# STEP 5: EXPORT DATA AS A PANDAS DATAFRAME (for model training / display)
# =============================================================================

def get_clinical_data_as_dataframe() -> pd.DataFrame:
    """
    Fetches all records from the database (joining patients + diagnostic_records)
    and returns them as a Pandas DataFrame ready for analysis or model training.

    Returns:
        pd.DataFrame: 768 rows, one per patient. Columns include all 8 clinical
                      features plus patient demographics and the diagnosis label.
    """
    session = SessionLocal()

    # SQL JOIN: combine columns from both tables where patient_id matches
    results = (
        session.query(
            DiagnosticRecord.record_id,
            Patient.patient_id,
            Patient.age,
            Patient.gender,
            DiagnosticRecord.pregnancies,
            DiagnosticRecord.glucose,
            DiagnosticRecord.blood_pressure,
            DiagnosticRecord.skin_thickness,
            DiagnosticRecord.insulin,
            DiagnosticRecord.bmi,
            DiagnosticRecord.diabetes_pedigree,
            DiagnosticRecord.actual_diagnosis,
        )
        .join(Patient, DiagnosticRecord.patient_id == Patient.patient_id)
        .all()
    )

    session.close()

    df = pd.DataFrame(
        results,
        columns=[
            "record_id",
            "patient_id",
            "age",
            "gender",
            "pregnancies",
            "glucose",
            "blood_pressure",
            "skin_thickness",
            "insulin",
            "bmi",
            "diabetes_pedigree",
            "actual_diagnosis",
        ],
    )

    print(f"[INFO] Loaded {len(df)} records from the database.")
    return df


def get_feature_array() -> tuple:
    """
    Returns the features (X) and labels (y) as NumPy arrays, ready to be
    used for training a PyTorch model.

    The 8 feature columns are returned as X; 'actual_diagnosis' is returned as y.

    Returns:
        tuple: (X: np.ndarray of shape (768, 8), y: np.ndarray of shape (768,))
    """
    df = get_clinical_data_as_dataframe()

    # The 8 feature columns (inputs to the neural network)
    feature_columns = [
        "pregnancies",
        "glucose",
        "blood_pressure",
        "skin_thickness",
        "insulin",
        "bmi",
        "diabetes_pedigree",
    ]
    # NOTE: 'age' is stored in the Patient table and also in DiagnosticRecord
    # via the join. We include it separately here from the patient table.
    # For simplicity, we re-read age from the df directly.
    feature_columns_full = [
        "pregnancies", "glucose", "blood_pressure", "skin_thickness",
        "insulin", "bmi", "diabetes_pedigree", "age",
    ]

    X = df[feature_columns_full].values.astype(float)  # Shape: (768, 8)
    y = df["actual_diagnosis"].values.astype(float)    # Shape: (768,)

    return X, y


# =============================================================================
# STEP 6: SAVE A MODEL PREDICTION BACK TO THE DATABASE
# =============================================================================

def save_prediction(record_id: int, mean_pred: float, variance: float, risk_tier: str):
    """
    Saves the model's probabilistic output to the 'model_predictions' table.

    Args:
        record_id (int):    The ID of the diagnostic record this prediction belongs to.
        mean_pred (float):  The mean probability from Monte Carlo sampling.
        variance (float):   The uncertainty variance from Monte Carlo sampling.
        risk_tier (str):    The human-readable risk classification.
    """
    session = SessionLocal()
    new_pred = ModelPrediction(
        record_id=record_id,
        mean_prediction=round(float(mean_pred), 6),
        uncertainty_variance=round(float(variance), 6),
        risk_tier=risk_tier,
    )
    session.add(new_pred)
    session.commit()
    session.close()
    print(f"[INFO] Saved prediction: record_id={record_id}, mean={mean_pred:.4f}, "
          f"variance={variance:.6f}, tier={risk_tier}")


# =============================================================================
# QUICK SELF-TEST
# =============================================================================

if __name__ == "__main__":
    print("--- Running database.py self-test (Pima Indians Dataset) ---\n")

    # Drop all tables and recreate them so we always start fresh.
    # We use SQLAlchemy's drop_all / create_all instead of deleting the
    # .db file directly, because the file may be locked by another process
    # (e.g., a running Streamlit server).
    print("[INFO] Dropping and recreating all tables to start fresh...")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("[INFO] Tables reset successfully.")

    # Load the real dataset
    load_pima_data_into_db()

    # Export to DataFrame and inspect
    df = get_clinical_data_as_dataframe()
    print("\nFirst 5 rows of clinical data:")
    print(df.head().to_string())
    print(f"\nDataFrame shape: {df.shape}")
    print(f"Positive diagnoses: {df['actual_diagnosis'].sum()} / {len(df)}")

    # Check feature/label arrays
    X, y = get_feature_array()
    print(f"\nFeature array X shape: {X.shape}")
    print(f"Label array   y shape: {y.shape}")

    print("\n--- Self-test complete. ---")
