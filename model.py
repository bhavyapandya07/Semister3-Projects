# =============================================================================
# FILE: model.py
# PURPOSE: Neural Network Architecture for the Pima Indians Diabetes Dataset.
#
# CHANGE FROM PREVIOUS VERSION:
#   The Pima Indians dataset has 8 features (not 4).
#   We updated `input_dim` from 4 to 8 to match all columns:
#       Pregnancies, Glucose, BloodPressure, SkinThickness,
#       Insulin, BMI, DiabetesPedigreeFunction, Age
#
# ARCHITECTURE:
#   Input (8) --> Linear(64) --> ReLU --> Dropout(0.3)
#             --> Linear(32) --> ReLU --> Dropout(0.3)
#             --> Linear(1)  --> Sigmoid
#             --> Output: probability of diabetes (0 to 1)
#
# KEY CONCEPT - MONTE CARLO DROPOUT (MC Dropout):
#   Keeping Dropout active during inference lets us run the model N times
#   and observe how much its outputs vary. That variation is our uncertainty.
#   High variance = model is unsure --> flag for a human doctor.
# =============================================================================

import torch
import torch.nn as nn


class ProbabilisticDiagnosticNN(nn.Module):
    """
    A Feedforward Neural Network for probabilistic binary classification
    on the Pima Indians Diabetes Dataset.

    ARCHITECTURE:
        Input (8 features)
            └─► Linear(8 → 64) ─► ReLU ─► Dropout(p=0.3)
                └─► Linear(64 → 32) ─► ReLU ─► Dropout(p=0.3)
                    └─► Linear(32 → 1) ─► Sigmoid
                        └─► Output: P(diabetes) in [0, 1]

    WHY THESE LAYER SIZES?
        8 inputs  --> 64 neurons: The network can create 64 "combinations"
                                  of our 8 input signals to find patterns.
        64       --> 32 neurons: Compresses the learned patterns, forcing
                                 the network to keep only the most useful ones.
        32       --> 1 neuron:   Binary classification needs just one output,
                                 which Sigmoid turns into a probability.
    """

    def __init__(self, input_dim: int = 8):
        """
        Constructor: defines all layers of the network.

        Args:
            input_dim (int): Number of input features.
                             8 for the full Pima Indians dataset.
        """
        super(ProbabilisticDiagnosticNN, self).__init__()

        # ------------------------------------------------------------------
        # LAYER 1: First Fully-Connected (Linear) Layer
        # ------------------------------------------------------------------
        # Maps 8 input features to 64 hidden neurons.
        # Every input is connected to every one of the 64 neurons.
        # Learnable parameters here: (8 × 64) weights + 64 biases = 576 params
        self.fc1 = nn.Linear(in_features=input_dim, out_features=64)

        # ------------------------------------------------------------------
        # ACTIVATION: ReLU (Rectified Linear Unit)
        # ------------------------------------------------------------------
        # f(x) = max(0, x) -- kills negative values, passes positives through.
        # Without activation functions, multiple linear layers collapse into one.
        # ReLU is the most popular choice: fast, simple, avoids vanishing gradients.
        self.relu = nn.ReLU()

        # ------------------------------------------------------------------
        # REGULARIZATION + UNCERTAINTY ENGINE: Dropout
        # ------------------------------------------------------------------
        # p=0.3 means 30% of neurons are randomly zeroed on each forward pass.
        #
        # ROLE 1 - DURING TRAINING (prevent overfitting):
        #   Randomly dropping neurons prevents the network from memorizing the
        #   training data. Forces redundant, generalizable representations.
        #   Like training a sports team where any player may be benched --
        #   everyone must learn to cover for each other.
        #
        # ROLE 2 - DURING INFERENCE (MC Dropout for uncertainty):
        #   If we keep model.train() active (NOT model.eval()), Dropout stays ON.
        #   Running the same input 50 times → 50 different masked networks → 50
        #   slightly different predictions.
        #   - Low spread (variance) → network versions AGREE → HIGH CONFIDENCE
        #   - High spread (variance) → network versions DISAGREE → HIGH UNCERTAINTY
        #   This variance is a free uncertainty estimate with no extra computation!
        self.dropout = nn.Dropout(p=0.3)

        # ------------------------------------------------------------------
        # LAYER 2: Second Fully-Connected Layer
        # ------------------------------------------------------------------
        # Compresses from 64 to 32 neurons.
        # Learnable parameters: (64 × 32) weights + 32 biases = 2,080 params
        self.fc2 = nn.Linear(in_features=64, out_features=32)

        # ------------------------------------------------------------------
        # LAYER 3: Output Layer
        # ------------------------------------------------------------------
        # Final compression: 32 → 1 neuron.
        # Learnable parameters: (32 × 1) weights + 1 bias = 33 params
        self.fc3 = nn.Linear(in_features=32, out_features=1)

        # ------------------------------------------------------------------
        # OUTPUT ACTIVATION: Sigmoid
        # ------------------------------------------------------------------
        # Sigmoid squashes any real number to (0, 1).
        # Formula: σ(x) = 1 / (1 + e^(−x))
        # Output close to 1 → high probability of diabetes
        # Output close to 0 → low probability of diabetes
        self.sigmoid = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Defines the forward pass: how data flows through the network layer by layer.
        PyTorch calls this automatically when you do: output = model(input_tensor)

        Args:
            x (torch.Tensor): Input of shape (batch_size, 8)
                               Each row is one patient's 8 clinical measurements.

        Returns:
            torch.Tensor: Shape (batch_size, 1), values in (0, 1).
                          Each value is P(patient is diabetic).
        """
        # BLOCK 1
        x = self.fc1(x)       # (batch, 8) --> (batch, 64): learn feature combinations
        x = self.relu(x)      # Apply ReLU: zero out negatives
        x = self.dropout(x)   # Randomly zero 30% of the 64 values

        # BLOCK 2
        x = self.fc2(x)       # (batch, 64) --> (batch, 32): compress representation
        x = self.relu(x)      # Apply ReLU again
        x = self.dropout(x)   # Randomly zero 30% of the 32 values

        # OUTPUT BLOCK
        x = self.fc3(x)       # (batch, 32) --> (batch, 1): single score
        x = self.sigmoid(x)   # Squash to (0, 1): now it is a probability

        return x


# =============================================================================
# TRAINING FUNCTION
# =============================================================================

def train_model(
    model: "ProbabilisticDiagnosticNN",
    X_raw: "np.ndarray",
    y: "np.ndarray",
    epochs: int = 200,
    lr: float = 0.005,
    scaler_path: str = "scaler.pkl",
) -> tuple:
    """
    Scales the input features with StandardScaler, trains the neural network,
    saves the fitted scaler to disk, and returns both the trained model and scaler.

    WHY FEATURE SCALING IS NECESSARY FOR NEURAL NETWORKS:
        The 8 Pima dataset features have very different numerical scales:
            - Pregnancies:  0  –  17      (small range)
            - Glucose:      44 – 199      (medium range)
            - Insulin:      0  – 846      (50x larger than Pregnancies!)
        Without scaling, gradient updates are dominated by high-magnitude
        features. Low-magnitude features barely learn at all.
        StandardScaler maps every feature to mean=0, std=1 so the network
        trains equally on ALL features simultaneously.

    WHY FIT SCALER ON TRAINING DATA ONLY (no data leakage):
        Fitting the scaler on all data (including future inference inputs)
        would let the model "peek" at future data -- called data leakage.
        We fit only on the 768 training rows, save the scaler to scaler.pkl,
        then LOAD that same scaler at inference time. This guarantees that
        new user inputs are scaled identically to what the model saw in training.

    HOW TRAINING WORKS (one epoch):
        1. Forward Pass:  Run all scaled patients through the network.
        2. Loss:          Measure error with Binary Cross-Entropy Loss.
        3. Backward Pass: Compute gradients (how to nudge each weight).
        4. Step:          Adam optimizer applies those nudges.
        Repeat for `epochs` iterations until the loss converges (~0.45-0.55).

    Args:
        model       : The ProbabilisticDiagnosticNN to train.
        X_raw       : RAW (unscaled) feature matrix, shape (N, 8).
        y           : Label vector of shape (N,) with values 0 or 1.
        epochs      : Training iterations over the full dataset. Default: 200.
        lr          : Adam learning rate. Default: 0.005.
        scaler_path : File path to save the fitted scaler. Default: 'scaler.pkl'.

    Returns:
        tuple: (trained_model, fitted_scaler)
    """
    import numpy as np
    import joblib
    import torch.optim as optim
    from sklearn.preprocessing import StandardScaler

    # -------------------------------------------------------------------------
    # STEP 1: FIT StandardScaler ON TRAINING DATA AND SCALE FEATURES
    # -------------------------------------------------------------------------
    # StandardScaler computes: scaled_x = (x - column_mean) / column_std
    # for each of the 8 feature columns independently.
    # After scaling, every column has mean ≈ 0 and std ≈ 1.
    scaler = StandardScaler()

    # fit_transform() first learns the mean/std from X_raw (fit),
    # then applies the scaling transformation (transform).
    X_scaled = scaler.fit_transform(X_raw)         # Shape: (N, 8)

    print(f"[INFO] StandardScaler fitted on training data.")
    print(f"[INFO]   Feature means (per column): {scaler.mean_.round(2)}")
    print(f"[INFO]   Feature stds  (per column): {scaler.scale_.round(2)}")

    # -------------------------------------------------------------------------
    # STEP 2: SAVE THE FITTED SCALER TO DISK
    # -------------------------------------------------------------------------
    # We MUST use the SAME scaler at inference time. By saving it to a file,
    # app.py can load it and apply .transform() to user inputs before feeding
    # them to the model -- ensuring training and inference are perfectly aligned.
    joblib.dump(scaler, scaler_path)
    print(f"[INFO] Scaler saved to '{scaler_path}'.")

    # -------------------------------------------------------------------------
    # STEP 3: CONVERT SCALED DATA TO PYTORCH TENSORS
    # -------------------------------------------------------------------------
    # X_scaled is float64 (NumPy default); PyTorch Linear layers need float32.
    X_tensor = torch.tensor(X_scaled, dtype=torch.float32)  # Shape: (N, 8)
    y_tensor = torch.tensor(y, dtype=torch.float32).unsqueeze(1)  # Shape: (N, 1)

    # -------------------------------------------------------------------------
    # STEP 4: LOSS FUNCTION AND OPTIMIZER
    # -------------------------------------------------------------------------
    # BCELoss: standard for binary classification, penalizes wrong predictions.
    criterion = nn.BCELoss()

    # Adam: adaptive learning rate optimizer. Converges faster than plain SGD.
    # weight_decay=1e-4 adds L2 regularization to discourage very large weights.
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)

    # -------------------------------------------------------------------------
    # STEP 5: TRAINING LOOP
    # -------------------------------------------------------------------------
    model.train()  # Activate Dropout during training (regularization role)

    print(f"[INFO] Training for {epochs} epochs...")
    for epoch in range(epochs):

        optimizer.zero_grad()       # Clear gradients from previous iteration
        outputs = model(X_tensor)   # Forward pass: predict on all training rows
        loss = criterion(outputs, y_tensor)  # Measure prediction error
        loss.backward()             # Backprop: compute gradient of loss
        optimizer.step()            # Update weights using Adam

        if (epoch + 1) % 50 == 0:
            print(f"  Epoch [{epoch+1:3d}/{epochs}]  Loss: {loss.item():.4f}")

    print(f"[INFO] Training complete! Final Loss: {loss.item():.4f}")

    # Return BOTH the trained model and the fitted scaler.
    # The scaler is needed in app.py to transform user inputs.
    return model, scaler


# =============================================================================
# QUICK SELF-TEST
# =============================================================================

if __name__ == "__main__":
    print("--- Running model.py self-test (8-feature Pima model) ---\n")

    # Create the model with 8 input features (matching the Pima dataset)
    model = ProbabilisticDiagnosticNN(input_dim=8)

    print("Model Architecture:")
    print(model)

    # Count total trainable parameters
    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"\nTotal trainable parameters: {total_params:,}")

    # Test with a fake batch of 5 patients, each with 8 features
    fake_input = torch.randn(5, 8)
    print(f"\nFake input shape: {fake_input.shape}")

    model.train()  # Keep dropout active
    output = model(fake_input)
    print(f"Output shape: {output.shape}")
    print(f"Output (probabilities): {output.detach().numpy().flatten()}")
    # All values should be between 0 and 1 thanks to Sigmoid

    print("\n--- model.py self-test complete ---")
