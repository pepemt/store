import os
from pathlib import Path

from dotenv import load_dotenv
from pyspark.sql import SparkSession


def _ensure_java_home() -> None:
    current = os.environ.get("JAVA_HOME")
    if current:
        current_java_binary = Path(current) / "bin" / "java"
        if current_java_binary.exists():
            return
        os.environ.pop("JAVA_HOME", None)

    java_virtual_machines = Path("/Library/Java/JavaVirtualMachines")
    if java_virtual_machines.exists():
        for candidate in sorted(java_virtual_machines.glob("*.jdk/Contents/Home"), reverse=True):
            java_binary = candidate / "bin" / "java"
            if java_binary.exists():
                os.environ["JAVA_HOME"] = str(candidate)
                return

    raise RuntimeError(
        "JAVA_HOME is not configured and no JDK installation was detected. "
        "Install a JDK (e.g. via Homebrew's openjdk) or set JAVA_HOME manually."
    )


load_dotenv()


def main():
    _ensure_java_home()
    spark_app_name = os.getenv("SPARK_APP_NAME")
    spark_master_url = os.getenv("SPARK_MASTER_URL")
    postgres_url = os.getenv("POSTGRES_URL")
    postgres_user = os.getenv("POSTGRES_USER")
    postgres_password = os.getenv("POSTGRES_PASSWORD")
    driver_memory = os.getenv("SPARK_DRIVER_MEMORY", "8g")
    driver_max_result = os.getenv("SPARK_DRIVER_MAX_RESULT_SIZE", "4g")
    executor_memory = os.getenv("SPARK_EXECUTOR_MEMORY")

    builder = (
        SparkSession.builder.appName(spark_app_name)
        .master(spark_master_url)
        .config("spark.jars.packages", "org.postgresql:postgresql:42.7.8")
        .config("spark.ui.showConsoleProgress", "false")
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
        .config("spark.driver.memory", driver_memory)
        .config("spark.driver.maxResultSize", driver_max_result)
    )

    if executor_memory:
        builder = builder.config("spark.executor.memory", executor_memory)

    spark = builder.getOrCreate()

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
