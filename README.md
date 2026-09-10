 🩺 Probabilistic Medical Diagnostic Assistant
**Deep Network with Probabilistic Modelling**

## 📖 What is this project?
Imagine you ask a doctor for a diagnosis. If the symptoms are clear, they confidently tell you what's wrong. But if the symptoms are confusing, a good doctor won't just guess—they will say, "I am not sure, let's get a senior specialist." 

Standard AI doesn't do this. Standard AI always guesses, even when it is completely confused. In healthcare, a wrong guess can be dangerous.

This project fixes that. It is a machine learning application that predicts diabetes risk using clinical data (like Glucose, BMI, and Age). But more importantly, **it knows when it is confused**. If the patient data is borderline or ambiguous, the AI stops, raises a yellow flag, and asks for a human doctor's review.

## ✨ How does it work? (The Magic Trick)
We used a deep learning technique called **Monte Carlo (MC) Dropout**.
Instead of making the AI guess just once, we force it to look at the same patient data **50 different times**, but each time, we randomly turn off different parts of its "brain" (neurons).

* **Low Uncertainty (Confident):** If the AI gives the exact same answer all 50 times, it means the clinical patterns are obvious. The AI is confident in its prediction (Green for Healthy, Red for High Risk).
* **High Uncertainty (Confused):** If the AI gives wildly different answers during the 50 passes, it means it is guessing. The mathematical "variance" between the guesses spikes up. If the variance goes above **0.008**, the system automatically halts the automated diagnosis and flags a doctor (Yellow Warning).

## 🛠️ Tech Stack Used
* **PyTorch:** The heavy-duty engine used to build the deep neural network.
* **Scikit-Learn (StandardScaler):** Used to scale the patient data so the AI doesn't get confused by big numbers (like Insulin levels) vs small numbers (like Age).
* **SQLite:** A relational database to securely store and retrieve structured patient records.
* **Streamlit:** Used to turn the Python code into a beautiful, interactive web dashboard.
* **Pandas & NumPy:** For data handling and mathematical calculations.

## 🚀 How to Run the Project on Your Computer

**1. Clone the repository:**
```bash
git clone https://github.com/Adarsh-Senpai/probabilistic-medical-diagnostic.git
cd "probabilistic-medical-diagnostic"
```

**2. Install the required tools:**
```bash
pip install -r requirements.txt
```

**3. Run the Dashboard:**
```bash
streamlit run app.py
```
*(This will open the application in your default web browser).*

## 📊 Dashboard Features
1. **Key Metrics:** Instantly see the Mean Risk Probability and the Uncertainty Variance.
2. **Clinical Decision Support:** A color-coded triage box that dynamically explains the math behind the AI's decision.
3. **MC Distribution Graph:** A visual histogram proving whether the 50 AI guesses agreed or disagreed with each other.

## 👨‍💻 Developer
Developed by **Adarsh Nagaraj Madivala**
* **GitHub:** [Adarsh-Senpai](https://github.com/Adarsh-Senpai)
* **LinkedIn:** [Adarsh Madivala](https://www.linkedin.com/in/adarsh-madivala-b1bab8284/)
