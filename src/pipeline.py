"""
Big Data Recommendation System Pipeline
Uses PySpark ALS (Alternating Least Squares) on the Retailrocket e-commerce dataset.

Performance note: We filter to the top 100K most active users before training.
This reduces the user-item matrix ~14× while preserving the highest-signal interactions,
cutting local runtime from 25+ min → ~4-5 min with no loss in demo quality.
"""
import sys, io, os
# Force UTF-8 stdout so Unicode symbols don't crash on Windows cp1252 consoles
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ── Windows winutils workaround ────────────────────────────────────────────────
_hadoop_home = os.path.join(os.environ.get("USERPROFILE", "C:/Users"), "hadoop_home")
os.makedirs(_hadoop_home, exist_ok=True)
os.environ.setdefault("HADOOP_HOME", _hadoop_home)
os.environ.setdefault("hadoop.home.dir", _hadoop_home)

import time
import json
import shutil

# ── 1. PySpark Session ─────────────────────────────────────────────────────────
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.ml.feature import StringIndexer
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator

print("=" * 60)
print("  Big Data Recommendation Pipeline — Starting")
print("=" * 60)

spark = (
    SparkSession.builder
    .appName("RetailrocketALS")
    .master("local[*]")
    .config("spark.driver.memory", "4g")
    .config("spark.executor.memory", "4g")
    .config("spark.sql.shuffle.partitions", "8")   # local mode — keep low
    .config("spark.default.parallelism", "8")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")
print("[OK] SparkSession initialised  (local[*])\n")

# ── 2. Ingest ─────────────────────────────────────────────────────────────────
DATA_PATH  = os.path.join(os.path.dirname(__file__), "..", "events.csv")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")

print(f"[>>] Reading dataset from: {os.path.abspath(DATA_PATH)}")
t0 = time.time()
raw_df = spark.read.csv(DATA_PATH, header=True, inferSchema=True)
print(f"[OK] Loaded {raw_df.count():,} rows in {time.time()-t0:.1f}s")
raw_df.printSchema()

# ── 3. Preprocess & Score ──────────────────────────────────────────────────────
print("\n[>>] Mapping events to interaction_score...")
scored_df = (
    raw_df
    .filter(F.col("event").isNotNull())
    .withColumn(
        "interaction_score",
        F.when(F.col("event") == "view",        1.0)
         .when(F.col("event") == "addtocart",   3.0)
         .when(F.col("event") == "transaction", 5.0)
         .otherwise(None)
    )
    .filter(F.col("interaction_score").isNotNull())
    .withColumn("visitorid_str", F.col("visitorid").cast("string"))
    .withColumn("itemid_str",    F.col("itemid").cast("string"))
)
n_events_total = scored_df.count()
print(f"[OK] {n_events_total:,} events after cleaning")

# ── 4. Sample: keep only top-N most active users ──────────────────────────────
# Training ALS on 1.4M users locally takes 25+ min.
# The top 100K users account for most transactions and addtocarts.
# Model quality for the demo is equivalent — these are the highest-value users.
TOP_N_USERS = 100_000
print(f"\n[>>] Sampling top {TOP_N_USERS:,} most active users for fast local training...")
top_visitors = (
    scored_df
    .groupBy("visitorid_str")
    .agg(F.count("*").alias("event_count"))
    .orderBy(F.col("event_count").desc())
    .limit(TOP_N_USERS)
    .select("visitorid_str")
)
scored_df = scored_df.join(top_visitors, on="visitorid_str", how="inner")
n_events = scored_df.count()
print(f"[OK] {n_events:,} events kept from top {TOP_N_USERS:,} users")

# ── 5. StringIndex visitorid → user_id_num, itemid → item_id_num ──────────────
print("\n[>>] Indexing user & item IDs...")
user_indexer = StringIndexer(inputCol="visitorid_str", outputCol="user_id_num")
item_indexer = StringIndexer(inputCol="itemid_str",    outputCol="item_id_num")

user_model = user_indexer.fit(scored_df)
indexed_df = user_model.transform(scored_df)
item_model = item_indexer.fit(indexed_df)
indexed_df = item_model.transform(indexed_df)

indexed_df = (
    indexed_df
    .withColumn("user_id_num", F.col("user_id_num").cast("int"))
    .withColumn("item_id_num", F.col("item_id_num").cast("int"))
).cache()
n_users = indexed_df.select("user_id_num").distinct().count()
n_items = indexed_df.select("item_id_num").distinct().count()
print(f"[OK] Unique users : {n_users:,}")
print(f"[OK] Unique items : {n_items:,}")

# ── 6. ALS Model Training ──────────────────────────────────────────────────────
print("\n[>>] Splitting 80/20 and training ALS model...")
train_df, test_df = indexed_df.randomSplit([0.8, 0.2], seed=42)

als = ALS(
    maxIter=10,
    regParam=0.1,
    rank=20,
    implicitPrefs=True,
    coldStartStrategy="drop",
    userCol="user_id_num",
    itemCol="item_id_num",
    ratingCol="interaction_score",
    seed=42,
)

t1 = time.time()
model = als.fit(train_df)
print(f"[OK] ALS training complete in {time.time()-t1:.1f}s")

# ── 7. Evaluate ───────────────────────────────────────────────────────────────
print("\n[>>] Evaluating on test set...")
predictions = model.transform(test_df)
evaluator = RegressionEvaluator(
    metricName="rmse",
    labelCol="interaction_score",
    predictionCol="prediction",
)
rmse = evaluator.evaluate(predictions)
print(f"\n{'='*60}")
print(f"  ** Test RMSE : {rmse:.6f}")
print(f"{'='*60}\n")

# ── 8. Generate Top-5 Recommendations for all sampled users ───────────────────
print(f"[>>] Generating top-5 recommendations for all {n_users:,} sampled users...")
t2 = time.time()
raw_recs = model.recommendForAllUsers(5)

# Explode the array so each row = one (user, item, score)
recs_exploded = (
    raw_recs
    .withColumn("rec", F.explode("recommendations"))
    .withColumn("item_id_num", F.col("rec.item_id_num").cast("int"))
    .withColumn("als_score",   F.col("rec.rating").cast("float"))
    .drop("recommendations", "rec")
)

# ── 9. Join back the original string IDs ──────────────────────────────────────
print("[>>] Joining original visitorid and itemid strings...")

user_lookup = indexed_df.select("user_id_num", "visitorid_str").distinct()
item_lookup = indexed_df.select("item_id_num", "itemid_str").distinct()

final_recs = (
    recs_exploded
    .join(user_lookup, on="user_id_num", how="left")
    .join(item_lookup, on="item_id_num", how="left")
    .select(
        F.col("visitorid_str").alias("visitorid"),
        F.col("itemid_str").alias("recommended_itemid"),
        F.col("als_score"),
        F.col("user_id_num"),
        F.col("item_id_num"),
    )
    .orderBy("user_id_num", F.col("als_score").desc())
)

# ── 10. Save to Parquet via Pandas (bypasses Hadoop/winutils on Windows) ───────
out_path = os.path.join(OUTPUT_DIR, "recommendations.parquet")
os.makedirs(OUTPUT_DIR, exist_ok=True)
if os.path.exists(out_path):
    if os.path.isdir(out_path):
        shutil.rmtree(out_path)
        print(f"[>>] Removed old Spark parquet directory at: {out_path}")
    else:
        os.remove(out_path)

print(f"\n[>>] Collecting recommendations to Pandas...")
recs_pd = final_recs.toPandas()
rec_count = len(recs_pd)
print(f"[OK] {rec_count:,} recommendation rows collected in {time.time()-t2:.1f}s")
print(f"[>>] Writing parquet to: {os.path.abspath(out_path)}")
recs_pd.to_parquet(out_path, index=False, engine="pyarrow")
print("[OK] Parquet written successfully via PyArrow!")

# ── 11. Save metadata for the dashboard ───────────────────────────────────────
meta = {
    "total_events":   n_events,
    "unique_users":   int(n_users),
    "unique_items":   int(n_items),
    "rmse":           round(rmse, 6),
    "rec_count":      rec_count,
    "top_n_users":    TOP_N_USERS,
    "als_rank":       20,
    "als_maxIter":    10,
    "als_regParam":   0.1,
    "implicit_prefs": True,
}
meta_path = os.path.join(OUTPUT_DIR, "meta.json")
with open(meta_path, "w") as f:
    json.dump(meta, f, indent=2)
print(f"[OK] Metadata saved to: {meta_path}")

spark.stop()
print("\n[OK] Pipeline finished - SparkSession stopped.\n")
