import os
import sys

# Ensure env is configured BEFORE any app import (settings are cached).
os.environ.setdefault("SUPABASE_URL", "http://localhost:54321")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test")
os.environ.setdefault("SUPABASE_PUBLISHABLE_KEY", "test")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("LLM_ENABLED", "false")
os.environ.setdefault("SQL_SECRETS_KEY", "1234567890123456789012345678901234567890123456789012345678901234")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
