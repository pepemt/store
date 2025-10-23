import os
from pathlib import Path

from dotenv import load_dotenv
from pyspark.sql import SparkSession

load_dotenv()

def main():
    spark_app_name = os.getenv("SPARK_APP_NAME")
    spark_master_url = os.getenv("SPARK_MASTER_URL")
    postgres_url = os.getenv("POSTGRES_URL")
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

    required = {
        "POSTGRES_URL": postgres_url,
        "POSTGRES_USER": postgres_user,
        "POSTGRES_PASSWORD": postgres_password,
    }

    missing = [k for k, v in required.items() if not v]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables for JDBC connection: {', '.join(missing)}"
        )

    jdbc_options = {
        "url": str(postgres_url),
        "dbtable": "articles",
        "user": str(postgres_user),
        "password": str(postgres_password),
        "driver": "org.postgresql.Driver",
    }

    reader = spark.read.format("jdbc")
    for k, v in jdbc_options.items():
        reader = reader.option(k, v)

    df = reader.load()

    df.show()


if __name__ == "__main__":
    main()
