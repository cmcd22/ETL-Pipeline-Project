import sys
from awsglue.context import GlueContext
from pyspark.context import SparkContext
import pyspark.sql.functions as F
from pyspark.sql.functions import regexp_extract, input_file_name

BRONZE_PATH = "s3://cmcd-etl-weather-lake/bronze/raw/*/*/*/*/*/data.json"
SILVER_PATH = "s3://cmcd-etl-weather-lake/silver/hourly/"

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session

# Read Bronze JSON
df = spark.read.json(BRONZE_PATH)

# Extract city name from the S3 path
df = df.withColumn(
    "city",
    regexp_extract(
        input_file_name(),
        r"city=([^/]+)",  # Extract the value after "city="
        1
    )
)

# Zip arrays into structs
df = df.withColumn(
    "hourly_struct",
    F.arrays_zip(
        "hourly.time",
        "hourly.temperature_2m",
        "hourly.precipitation",
        "hourly.wind_speed_10m",
        "hourly.windgusts_10m",
        "hourly.pressure_msl",
        "hourly.uv_index",
        "hourly.shortwave_radiation"
    )
)

# Explode into rows
df = df.withColumn("hour", F.explode("hourly_struct"))

# Flatten fields
df = df.select(
    "city",
    F.to_timestamp("hour.time").alias("timestamp"),
    F.col("hour.temperature_2m").alias("temperature"),
    F.col("hour.precipitation").alias("precipitation"),
    F.col("hour.wind_speed_10m").alias("windspeed"),
    F.col("hour.windgusts_10m").alias("windgusts"),
    F.col("hour.pressure_msl").alias("pressure"),
    F.col("hour.uv_index").alias("uv_index"),
    F.col("hour.shortwave_radiation").alias("radiation")
)

# Add partition columns
df = (
    df.withColumn("year", F.year("timestamp"))
      .withColumn("month", F.month("timestamp"))
      .withColumn("day", F.dayofmonth("timestamp"))
)

# Write partitioned parquet to Silver layer
df.write.mode("overwrite").partitionBy("city", "year", "month", "day").parquet(SILVER_PATH)
