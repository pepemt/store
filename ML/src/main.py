import os
from pathlib import Path

from dotenv import load_dotenv
from pyspark.sql import SparkSession

load_dotenv()

def main():

    spark_app_name = os.getenv("SPARK_APP_NAME")
    spark_master_url = os.getenv("SPARK_MASTER_URL")
    postgres_url = os.getenv("POSTGRES_UL")
    postgres_user = os.getenv("POSTGRES_USER")
    postgres_password = os.getenv("POSTGRES_PASSWORD")

    spark = (
        SparkSession.builder.appName(spark_app_name)
        .master(spark_master_url)
        .config("spark.jars.packages", "org.postgresql:postgresql:42.7.8")
        .config("spark.ui.showConsoleProgress", "false")
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
        .getOrCreate()
    )

    df = (
        spark.read.format("jdbc")
        .option("url", postgres_url)
        .option("dbtable", "articles")
        .option("user", postgres_user)
        .option("password", postgres_password)
        .option("driver", "org.postgresql.Driver")
        .load()
    )

    df.show()


if __name__ == "__main__":
    main()
