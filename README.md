# 🛒 RetailRocket Big Data Recommendation System

This project is a Big Data Recommendation System, similar to the engines used by Amazon and Netflix. It processes millions of real shopping events to learn user preferences and predict which products a user is most likely to buy next.

## 🧠 Core Concepts

1. **Apache Spark (Big Data Engine)**:
   Regular Python/Pandas struggles to efficiently process millions of rows on a single machine. This project utilizes PySpark to split the data across CPU cores and process chunks in parallel, allowing the code to run seamlessly whether on a local machine or a cloud cluster.

2. **ALS Algorithm (The Recommendation Brain)**:
   We use **Alternating Least Squares (ALS)**, a matrix factorization technique. ALS breaks down the massive User-Item matrix into two smaller matrices. It represents every user and item as a vector of 20 hidden numbers ("taste vectors"). The dot product of a user's vector and an item's vector determines how much the user would like that item.

3. **Implicit Feedback**:
   The dataset doesn't contain explicit star ratings, only behavioral signals (clicks, carts, buys). We assign implicit scores:
   - `view` = 1.0
   - `addtocart` = 3.0
   - `transaction` = 5.0

## 📊 Dataset & Results

- **Dataset**: RetailRocket (2,756,101 events, 94 MB)
- **Users Indexed**: 100,000
- **Items in Catalogue**: 109,845
- **Training Time**: ~79 seconds
- **Test RMSE**: 1.3086
- **Recommendations Generated**: 499,825 (Top 5 for each user)

## 🏗️ System Architecture

1. **📥 Data Ingestion**: `events.csv` is read via PySpark, distributed across local cores.
2. **⚙️ Preprocessing & Scoring**: Events mapped to implicit feedback scores.
3. **🔢 ID Indexing**: StringIndexer converts String IDs to Integer indices for ALS.
4. **🤖 ALS Model Training**: ALS with `implicitPrefs=True`, `rank=20`, `maxIter=10`, `regParam=0.1`.
5. **📊 Evaluation**: RegressionEvaluator computes RMSE on a 20% test split.
6. **💾 Parquet Output**: Top-5 recommendations for every user are saved as a lightweight Parquet file.
7. **🖥️ Streamlit Dashboard**: An interactive UI to visualize user history and personalized recommendations.

## 🚀 Running the Project

### 1. Train the Model

Run the PySpark pipeline to process the data, train the ALS model, and generate recommendations:

```bash
python src/pipeline.py
```
*(This will generate `recommendations.parquet` and `meta.json` inside the `output/` directory)*

### 2. Launch the Dashboard

Start the Streamlit interactive dashboard:

```bash
streamlit run app.py
```

## 🎯 Dashboard Features

- **User Simulator**: Pick a user or type a Visitor ID to see their past activity (views, carts, transactions) alongside their personalized Top 5 recommendations.
- **Analytics & Architecture**: View dataset statistics, class imbalance (96% view / 3% cart / 0.5% transaction split), model hyperparameters, and the system architecture.
- **Cold Start Handling**: Try searching an unknown Visitor ID (e.g., `123` or `999999999`) to see how the system handles the Cold Start problem gracefully.

### Interesting Visitor IDs to Demo:
- `684514`: Most active user in the dataset.
- `599528`: Made purchases AND added items to the cart.
- `121688`: Made a transaction.
- `158090`: Added items to cart.
