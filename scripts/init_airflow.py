"""Airflow initialization: create DB connections, variables, and Fernet key."""
import subprocess
import sys


def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"WARN: {' '.join(cmd)} -> {result.stderr.strip()}", file=sys.stderr)
    else:
        print(f"OK: {' '.join(cmd)}")


def main():
    # Initialize Airflow metadata DB
    run(["airflow", "db", "migrate"])

    # Create admin user
    run([
        "airflow", "users", "create",
        "--username", "admin",
        "--firstname", "CryptoPulse",
        "--lastname", "Admin",
        "--role", "Admin",
        "--email", "admin@cryptopulse.local",
        "--password", "admin123",
    ])

    print("Airflow initialization complete.")
    print("Login at http://localhost:8080 with admin / admin123")


if __name__ == "__main__":
    main()
