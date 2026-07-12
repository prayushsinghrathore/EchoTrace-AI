"""
Neo4j Connection Diagnostic Script.

Loads the exact same Settings and Neo4jConnectionManager used by the app,
then performs a single connection attempt and prints the complete diagnostics.

Usage:
    cd backend && PYTHONPATH=. .venv/bin/python scripts/test_neo4j_connection.py

WARNING: This connects to the actual Neo4j instance configured in your environment.
"""

import asyncio
import importlib
import os
import sys

# Force reload of settings to pick up any env vars
# Don't set anything — let it read from the actual environment

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Delete cached imports if any
for mod in list(sys.modules.keys()):
    if "app.core.config" in mod:
        del sys.modules[mod]


async def diagnose() -> None:
    print("=" * 72)
    print("  NEO4J CONNECTION DIAGNOSTIC")
    print("=" * 72)

    # Import fresh
    from app.core.config import settings

    # ── Step 1: Print config sources ─────────────────────────────────────
    print()
    print("─── 1. Configuration ───")
    enabled = settings.NEO4J_ENABLED
    uri = settings.NEO4J_URI
    user = settings.NEO4J_USER
    pw = settings.NEO4J_PASSWORD
    database = settings.NEO4J_DATABASE

    print(f"  NEO4J_ENABLED  = {enabled!r}")
    print(f"  NEO4J_URI      = {uri!r}")
    print(f"  NEO4J_USER     = {user!r}")
    print(f"  PASSWORD_LEN   = {len(pw) if isinstance(pw, str) else 0}")
    print(f"  PASSWORD_EMPTY = {not bool(pw)}")
    print(f"  NEO4J_DATABASE = {database!r}")

    # Check for whitespace issues
    if isinstance(uri, str) and uri != uri.strip():
        print(f"  ⚠️  URI has leading/trailing whitespace!")
    if isinstance(user, str) and user != user.strip():
        print(f"  ⚠️  USER has leading/trailing whitespace!")
    if isinstance(pw, str) and pw != pw.strip():
        print(f"  ⚠️  PASSWORD has leading/trailing whitespace!")

    # Check env vs default
    env_uri = os.environ.get("NEO4J_URI")
    env_user = os.environ.get("NEO4J_USER")
    env_pw = os.environ.get("NEO4J_PASSWORD")
    env_enabled = os.environ.get("NEO4J_ENABLED")

    print()
    print("─── 2. Environment Variable Sources ───")
    print(f"  NEO4J_ENABLED   env={'SET' if env_enabled is not None else 'NOT SET'}  app={enabled!r}")
    print(f"  NEO4J_URI       env={'SET' if env_uri is not None else 'NOT SET'}  app={uri!r}")
    print(f"  NEO4J_USER      env={'SET' if env_user is not None else 'NOT SET'}  app={user!r}")
    print(f"  NEO4J_PASSWORD  env={'SET' if env_pw is not None else 'NOT SET'}  len={len(env_pw) if env_pw else 0}  app_len={len(pw) if isinstance(pw, str) else 0}")

    if env_enabled is not None and env_enabled != str(enabled):
        print(f"  ⚠️  NEO4J_ENABLED env='{env_enabled}' != app={enabled}")

    # ── Step 3: Attempt connection ───────────────────────────────────────
    print()
    print("─── 3. Connection Attempt ───")

    if not enabled:
        print("  SKIPPED: NEO4J_ENABLED is False")
        print()
        print("=" * 72)
        print("  DIAGNOSIS: Neo4j is disabled. No connection attempted.")
        print("  To enable: set NEO4J_ENABLED=true in environment")
        print("=" * 72)
        return

    print(f"  Connecting to: {uri}")
    print(f"  As user:       {user}")
    print(f"  Database:      {database}")
    print()

    try:
        from neo4j import AsyncGraphDatabase

        driver = AsyncGraphDatabase.driver(
            uri,
            auth=(user, pw),
            max_connection_lifetime=3600,
            max_connection_pool_size=1,
            connection_acquisition_timeout=10,
            connection_timeout=10,
        )

        async with driver:
            print("  Driver created successfully.")

            # Verify connectivity
            try:
                await driver.verify_connectivity()
                print("  ✅ verify_connectivity() PASSED")

                # Test with a simple query
                async with driver.session(database=database) as session:
                    result = await session.run("RETURN 1 AS health")
                    record = await result.single()
                    print(f"  ✅ Test query returned: {record}")
                    print()
                    print("=" * 72)
                    print("  ✅ NEO4J CONNECTION SUCCESSFUL")
                    print("=" * 72)

            except Exception as verify_err:
                print(f"  ❌ verify_connectivity() FAILED: {type(verify_err).__name__}")
                print(f"     {verify_err}")
                print()
                import traceback as tb_module
                trace = tb_module.format_exception(type(verify_err), verify_err, verify_err.__traceback__)
                print(f"  Full traceback (last 10 lines):")
                for line in trace[-10:]:
                    for l in line.split("\n"):
                        if l.strip():
                            print(f"    {l.strip()}")

    except Exception as driver_err:
        print(f"  ❌ Driver creation FAILED: {type(driver_err).__name__}")
        print(f"     {driver_err}")
        print()
        import traceback as tb_module
        trace = tb_module.format_exception(type(driver_err), driver_err, driver_err.__traceback__)
        print(f"  Full traceback (last 10 lines):")
        for line in trace[-10:]:
            for l in line.split("\n"):
                if l.strip():
                    print(f"    {l.strip()}")

    print()
    print("=" * 72)
    print("  DIAGNOSTIC COMPLETE")
    print("=" * 72)


if __name__ == "__main__":
    asyncio.run(diagnose())
