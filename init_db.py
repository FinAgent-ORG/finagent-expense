import os
import sys
import time

import pymysql


def env(name: str, default: str | None = None, *, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value or ""


def connect_with_retry():
    host = env("MYSQL_ADMIN_HOST", env("MYSQL_HOST", "mysql-server"))
    port = int(env("MYSQL_ADMIN_PORT", env("MYSQL_PORT", "3306")))
    user = env("MYSQL_ADMIN_USER", "root", required=True)
    password = env("MYSQL_ADMIN_PASSWORD", required=True)
    database = env("MYSQL_ADMIN_DATABASE", "mysql")
    connect_timeout = int(env("MYSQL_CONNECT_TIMEOUT_SECONDS", "10"))
    max_attempts = int(env("MYSQL_INIT_MAX_ATTEMPTS", "30"))
    retry_delay = int(env("MYSQL_INIT_RETRY_DELAY_SECONDS", "5"))

    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                charset="utf8mb4",
                autocommit=True,
                connect_timeout=connect_timeout,
            )
        except Exception as exc:
            last_error = exc
            print(f"[expense-init-db] MySQL connection attempt {attempt}/{max_attempts} failed: {exc}", flush=True)
            if attempt < max_attempts:
                time.sleep(retry_delay)

    raise RuntimeError(f"Unable to connect to MySQL after {max_attempts} attempts") from last_error


def quote_identifier(value: str) -> str:
    return f"`{value.replace('`', '``')}`"


def quote_string(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def main() -> int:
    database = env("MYSQL_DATABASE", "finagent_expense", required=True)
    user = env("MYSQL_USER", "finagent_expense_user", required=True)
    password = env("MYSQL_PASSWORD", required=True)

    connection = connect_with_retry()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS {quote_identifier(database)} "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            cursor.execute(
                f"CREATE USER IF NOT EXISTS {quote_string(user)}@'%' "
                f"IDENTIFIED BY {quote_string(password)}"
            )
            cursor.execute(
                f"ALTER USER {quote_string(user)}@'%' IDENTIFIED BY {quote_string(password)}"
            )
            cursor.execute(
                f"GRANT ALL PRIVILEGES ON {quote_identifier(database)}.* "
                f"TO {quote_string(user)}@'%'"
            )
            cursor.execute("FLUSH PRIVILEGES")
    finally:
        connection.close()

    print(f"[expense-init-db] Database bootstrap completed for {database}.", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[expense-init-db] Fatal error: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1)
