# =============================================================================
# FILE: inference.py
# PURPOSE: The Probabilistic Engine - Runs Monte Carlo Dropout inference
#          to generate predictions WITH uncertainty estimates.
#
# KEY FIX IN THIS VERSION:
#   Previously, this file used hardcoded approximations for Z-score
#   normalization. This caused a TRAINING / INFERENCE MISMATCH:
#   the model was trained with sklearn's StandardScaler values, but inference
#   used slightly different constants --> predictions were wrong.
#
#   Now we LOAD the scaler.pkl file that was saved during training and apply
#   scaler.transform() to ALL user inputs. This guarantees the exact same
#   transformation is used at both training and inference time.
#
# THE PIPELINE FOR EACH PREDICTION:
#   Raw user input (8 floats)
#       --> numpy array in EXACT column order matching training data
#       --> scaler.transform()  [same scaler fitted during training]
#       --> torch.tensor (float32, shape (1, 8))
#       --> model(tensor) called 50 times with Dropout ACTIVE (model.train())
#       --> collect 50 outputs --> mean (risk %) + variance (uncertainty)
#       --> classify_risk_tier() --> clinical decision
# =============================================================================

import os
import numpy as np
import torch
import joblib                   # For loading the saved StandardScaler

from model import ProbabilisticDiagnosticNN


# =============================================================================
# UNCERTAINTY THRESHOLD (single source of truth)
# =============================================================================
# This constant controls when the model flags a result as "too uncertain"
# to trust and refers it to a senior physician instead.
#
# VALUE: 0.008
#   After switching to sklearn StandardScaler, the variance of the 50 MC
#   Dropout samples is much smaller (features are tightly scaled to mean=0,
#   std=1). Empirically, borderline/ambiguous patient profiles produce
#   variances in the 0.008 – 0.025 range. Setting the threshold at 0.008
#   catches these cases and correctly triggers FLAG_FOR_DOCTOR.
#
# HOW TO ADJUST:
#   Change the value here ONLY. Both classify_risk_tier() (logic) and
#   app.py (UI text) import this constant, so the entire app stays in sync.
UNCERTAINTY_THRESHOLD = 0.008


# =============================================================================
# COLUMN ORDER (MUST MATCH TRAINING DATA EXACTLY)
# =============================================================================
# This is the EXACT order of feature columns used when training the model.
# When preparing user input, we must build a numpy array in this same order.
# Getting this wrong would be like giving a recipe's ingredients in the wrong
# order -- the model would interpret Glucose as Age and produce nonsense.

FEATURE_ORDER = [
    "Pregnancies",               # Column 0
    "Glucose",                   # Column 1
    "BloodPressure",             # Column 2
    "SkinThickness",             # Column 3
    "Insulin",                   # Column 4
    "BMI",                       # Column 5
    "DiabetesPedigreeFunction",  # Column 6
    "Age",                       # Column 7
]


# =============================================================================
# LOAD THE FITTED SCALER FROM DISK
# =============================================================================

def load_scaler(scaler_path: str = "scaler.pkl"):
    """
    Loads the StandardScaler that was fitted and saved during model training.

    WHY THIS MATTERS:
        The StandardScaler object stores the mean and standard deviation of each
        feature column, computed from the 768 training rows. By saving and
        reloading this EXACT scaler, we guarantee that:
            - Training used: scaled = (raw - training_mean) / training_std
            - Inference uses: scaled = (raw - SAME training_mean) / SAME training_std
        If the means/stds differed between training and inference, the model
        would receive inputs it has never seen before, producing garbage outputs.

    Args:
        scaler_path (str): Path to the saved scaler pickle file.

    Returns:
        sklearn.preprocessing.StandardScaler: The fitted scaler object.

    Raises:
        FileNotFoundError: If scaler.pkl doesn't exist yet (model not trained).
    """
    if not os.path.exists(scaler_path):
        raise FileNotFoundError(
            f"[ERROR] '{scaler_path}' not found. The model has not been trained yet.\n"
            f"Please restart the app so the training step can run and save the scaler."
        )

    scaler = joblib.load(scaler_path)
    print(f"[INFO] Scaler loaded from '{scaler_path}'.")
    return scaler


# =============================================================================
# MAIN FUNCTION: PREPARE INPUT TENSOR
# =============================================================================

def prepare_input_tensor(
    pregnancies: float,
    glucose: float,
    blood_pressure: float,
    skin_thickness: float,
    insulin: float,
    bmi: float,
    diabetes_pedigree: float,
    age: float,
    scaler,
) -> torch.Tensor:
    """
    Converts the 8 raw clinical values from the Streamlit UI into a
    properly scaled PyTorch tensor, ready for the neural network.

    THE PIPELINE (step by step):
        1. Build a NumPy array from the 8 raw values in the EXACT same
           column order used during training (FEATURE_ORDER above).
        2. Apply scaler.transform() using the SAME StandardScaler that was
           fitted on the training data. This scales each feature identically
           to how the training rows were scaled.
        3. Convert the scaled array to a float32 PyTorch tensor.
        4. Add a batch dimension: shape (8,) --> (1, 8).

    WHY THE COLUMN ORDER MATTERS:
        Neural network weights are tied to specific input positions.
        Weight[0] learned to process "Pregnancies". If we accidentally pass
        "Insulin" in position 0, weight[0] will apply a "Pregnancies" lens
        to Insulin values -- completely wrong predictions result.

    Args:
        pregnancies (float):       Number of pregnancies.
        glucose (float):           Plasma glucose concentration (mg/dL).
        blood_pressure (float):    Diastolic blood pressure (mm Hg).
        skin_thickness (float):    Triceps skin fold thickness (mm).
        insulin (float):           2-hour serum insulin (mu U/ml).
        bmi (float):               Body mass index (kg/m2).
        diabetes_pedigree (float): Diabetes pedigree function score.
        age (float):               Patient age (years).
        scaler:                    Fitted StandardScaler loaded from scaler.pkl.

    Returns:
        torch.Tensor: Shape (1, 8), dtype float32. Ready for model inference.
    """

    # Step 1: Build a 2D NumPy array with shape (1, 8).
    # The (1, ...) shape is required by scaler.transform() which expects
    # a 2D array: (number_of_samples, number_of_features).
    # The order here MUST exactly match FEATURE_ORDER / training column order.
    raw_input = np.array([[
        pregnancies,        # Column 0: Pregnancies
        glucose,            # Column 1: Glucose
        blood_pressure,     # Column 2: BloodPressure
        skin_thickness,     # Column 3: SkinThickness
        insulin,            # Column 4: Insulin
        bmi,                # Column 5: BMI
        diabetes_pedigree,  # Column 6: DiabetesPedigreeFunction
        age,                # Column 7: Age
    ]], dtype=np.float64)   # float64 is sklearn's expected dtype

    # Step 2: Apply the SAME StandardScaler used during training.
    # scaler.transform() uses the mean and std values LEARNED from training data.
    # It does NOT re-fit; it only applies: scaled = (raw - training_mean) / training_std
    scaled_input = scaler.transform(raw_input)  # Shape: (1, 8)

    # Step 3: Convert to float32 PyTorch tensor (PyTorch's default float type).
    # The tensor has shape (1, 8): batch_size=1, features=8.
    input_tensor = torch.tensor(scaled_input, dtype=torch.float32)

    return input_tensor


# =============================================================================
# MAIN FUNCTION: MONTE CARLO DROPOUT INFERENCE
# =============================================================================

def predict_with_uncertainty(
    model: ProbabilisticDiagnosticNN,
    input_tensor: torch.Tensor,
    num_samples: int = 50,
) -> dict:
    """
    Performs Monte Carlo Dropout inference to get a prediction AND uncertainty.

    THE KEY TRICK -- WHY model.train() INSTEAD OF model.eval()?
        model.eval() turns OFF Dropout --> every forward pass gives the EXACT
        SAME output --> variance = 0 --> no uncertainty estimate.

        model.train() keeps Dropout ON --> each of the N forward passes uses
        a DIFFERENT randomly masked version of the network (30% of neurons
        dropped each time) --> each pass gives a SLIGHTLY DIFFERENT output.

        The VARIANCE of those N outputs is our uncertainty estimate:
        - Small variance  --> all masked versions AGREED --> CONFIDENT
        - Large variance  --> masked versions DISAGREED --> UNCERTAIN

        This is Monte Carlo Dropout (Gal & Ghahramani, 2016).

    Args:
        model (ProbabilisticDiagnosticNN): Trained neural network.
        input_tensor (torch.Tensor):       Scaled input, shape (1, 8).
        num_samples (int):                 Number of MC forward passes. Default 50.

    Returns:
        dict:
            'mean'        --> float: mean of N predictions (best risk estimate)
            'variance'    --> float: variance of N predictions (uncertainty)
            'all_samples' --> list:  raw output of each forward pass (for histogram)
    """
    # Keep Dropout active -- this is what makes inference probabilistic.
    model.train()

    # Disable gradient computation to save memory and time.
    # We are not training here, so we don't need to build a computation graph.
    with torch.no_grad():

        mc_predictions = []

        # --- MONTE CARLO SAMPLING LOOP ---
        # Each iteration: a different random set of neurons is dropped,
        # producing a slightly different output.
        for _ in range(num_samples):
            output = model(input_tensor)   # Shape: (1, 1)
            mc_predictions.append(output.item())  # Extract float from tensor

    # Convert to NumPy array for easy statistical calculation
    samples_array = np.array(mc_predictions)

    # Mean (mu): best estimate of the true probability
    mean_prediction = float(np.mean(samples_array))

    # Variance (sigma^2): how spread out the 50 predictions are
    # High variance = model "hesitated" a lot = UNCERTAIN
    # Low variance  = model was consistent   = CONFIDENT
    uncertainty_variance = float(np.var(samples_array))

    return {
        "mean": mean_prediction,
        "variance": uncertainty_variance,
        "all_samples": mc_predictions,
    }


# =============================================================================
# TRIAGE FUNCTION: CLASSIFY RISK TIER
# =============================================================================

def classify_risk_tier(mean_prediction: float, uncertainty_variance: float) -> str:
    """
    Converts the raw probabilistic output into a clinical risk tier.

    DECISION LOGIC:
        1. Check uncertainty FIRST:
           variance >= 0.008 --> FLAG_FOR_DOCTOR (don't trust any uncertain result)
        2. If confident, classify by mean:
           mean > 0.5  --> HIGH_CONFIDENCE_POSITIVE (likely diabetic)
           mean <= 0.5 --> HIGH_CONFIDENCE_NEGATIVE (likely not diabetic)

    THRESHOLD (variance >= 0.008):
        After StandardScaler normalization, MC Dropout variance values are
        much smaller than with raw features. Borderline/ambiguous cases
        produce variances in the 0.008 – 0.025 range. A threshold of 0.008
        correctly catches these and refers them to a physician.
        The threshold is defined as UNCERTAINTY_THRESHOLD at the top of
        this file so it stays consistent across all logic and UI text.

    Args:
        mean_prediction (float):      Average MC sample (0 to 1).
        uncertainty_variance (float): Variance of MC samples.

    Returns:
        str: "FLAG_FOR_DOCTOR" | "HIGH_CONFIDENCE_POSITIVE" | "HIGH_CONFIDENCE_NEGATIVE"
    """
    # Use the module-level constant so UI text and logic always match.
    # >= means a variance EQUAL TO the threshold also triggers FLAG_FOR_DOCTOR.
    if uncertainty_variance >= UNCERTAINTY_THRESHOLD:
        return "FLAG_FOR_DOCTOR"
    elif mean_prediction > 0.5:
        return "HIGH_CONFIDENCE_POSITIVE"
    else:
        return "HIGH_CONFIDENCE_NEGATIVE"


# =============================================================================
# QUICK SELF-TEST
# =============================================================================

if __name__ == "__main__":
    print("--- Running inference.py self-test ---\n")

    # This test requires scaler.pkl to exist (run app.py first to train and save it)
    try:
        scaler = load_scaler("scaler.pkl")
    except FileNotFoundError as e:
        print(e)
        print("Skipping self-test. Run the Streamlit app first to generate scaler.pkl.")
        exit()

    model = ProbabilisticDiagnosticNN(input_dim=8)

    # Test with Row 1 of the Pima dataset:
    # Pregnancies=6, Glucose=148, BP=72, Skin=35, Insulin=0,
    # BMI=33.6, Pedigree=0.627, Age=50 --> Outcome=1 (diabetic)
    tensor = prepare_input_tensor(
        pregnancies=6, glucose=148, blood_pressure=72,
        skin_thickness=35, insulin=0, bmi=33.6,
        diabetes_pedigree=0.627, age=50,
        scaler=scaler,
    )
    print(f"Input tensor shape:  {tensor.shape}")
    print(f"Scaled values:       {tensor.numpy()}")

    results = predict_with_uncertainty(model, tensor, num_samples=50)
    print(f"\nMean prediction:  {results['mean']:.4f} ({results['mean']*100:.1f}%)")
    print(f"Uncertainty (s2): {results['variance']:.6f}")
    print(f"Risk tier:        {classify_risk_tier(results['mean'], results['variance'])}")
    print("\n--- inference.py self-test complete ---")
