import os
import subprocess
import sys


def test_migration_round_trip_and_metadata(database_url):
    env = {**os.environ, "DATABASE_URL": database_url}
    for args in [("downgrade", "base"), ("upgrade", "head"), ("check",)]:
        subprocess.run([sys.executable, "-m", "alembic", *args], env=env, check=True)
