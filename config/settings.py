"""
Configuration Loader & Settings Manager.
Loads settings from YAML files and environment variables.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_yaml(file_path: Path) -> Dict[str, Any]:
    if not file_path.exists():
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Warning: Failed to load {file_path}: {e}")
        return {}


class AppSettings:
    def __init__(self):
        self.config_yaml = load_yaml(CONFIG_DIR / "config.yaml")
        self.secrets_yaml = load_yaml(CONFIG_DIR / "secrets.yaml")
        if not self.secrets_yaml:
            self.secrets_yaml = load_yaml(CONFIG_DIR / "secrets.yaml.example")
        self.profile_yaml = load_yaml(CONFIG_DIR / "profile_resume.yaml")

    # App Info
    @property
    def app_name(self) -> str:
        return self.config_yaml.get("app", {}).get("name", "AI Job Hunter")

    @property
    def port(self) -> int:
        return int(os.getenv("PORT", self.config_yaml.get("app", {}).get("port", 8000)))

    @property
    def host(self) -> str:
        return os.getenv("HOST", self.config_yaml.get("app", {}).get("host", "0.0.0.0"))

    # Database
    @property
    def database_url(self) -> str:
        default_db = f"sqlite:///{DATA_DIR / 'job_hunter.db'}"
        return os.getenv("DATABASE_URL", self.secrets_yaml.get("database_url") or default_db)

    # AI & LLM Providers
    @property
    def active_llm_provider(self) -> str:
        return os.getenv("LLM_PROVIDER", self.config_yaml.get("ai_router", {}).get("active_provider", "ollama"))

    @property
    def active_llm_model(self) -> str:
        return os.getenv("LLM_MODEL", self.config_yaml.get("ai_router", {}).get("model_name", "llama3.3"))

    @property
    def ollama_host(self) -> str:
        return os.getenv("OLLAMA_HOST", self.secrets_yaml.get("ollama_host", "http://localhost:11434"))

    @property
    def openai_api_key(self) -> str:
        return os.getenv("OPENAI_API_KEY", self.secrets_yaml.get("openai_api_key", ""))

    @property
    def gemini_api_key(self) -> str:
        return os.getenv("GEMINI_API_KEY", self.secrets_yaml.get("gemini_api_key", ""))

    @property
    def anthropic_api_key(self) -> str:
        return os.getenv("ANTHROPIC_API_KEY", self.secrets_yaml.get("anthropic_api_key", ""))

    @property
    def deepseek_api_key(self) -> str:
        return os.getenv("DEEPSEEK_API_KEY", self.secrets_yaml.get("deepseek_api_key", ""))

    @property
    def groq_api_key(self) -> str:
        return os.getenv("GROQ_API_KEY", self.secrets_yaml.get("groq_api_key", ""))

    @property
    def openrouter_api_key(self) -> str:
        return os.getenv("OPENROUTER_API_KEY", self.secrets_yaml.get("openrouter_api_key", ""))

    # Search & Targets
    @property
    def target_positions(self) -> List[str]:
        return self.config_yaml.get("search_preferences", {}).get("positions", ["Software Engineer"])

    @property
    def target_locations(self) -> List[str]:
        return self.config_yaml.get("search_preferences", {}).get("locations", ["Remote"])

    @property
    def remote_only(self) -> bool:
        return self.config_yaml.get("search_preferences", {}).get("remote_only", True)

    @property
    def ats_targets(self) -> Dict[str, List[str]]:
        return self.config_yaml.get("ats_targets", {
            "greenhouse": ["stripe", "figma", "anthropic"],
            "lever": ["palantir", "spotify"],
            "ashby": ["retool", "openai", "cursor"]
        })

    # Evaluation
    @property
    def min_match_score(self) -> int:
        return self.config_yaml.get("evaluation", {}).get("min_match_score", 70)

    @property
    def auto_apply_threshold(self) -> int:
        return self.config_yaml.get("evaluation", {}).get("auto_apply_score_threshold", 85)

    @property
    def dealbreakers(self) -> List[str]:
        return self.config_yaml.get("evaluation", {}).get("dealbreakers", [])

    # Browser & Automation
    @property
    def headless(self) -> bool:
        return self.config_yaml.get("automation", {}).get("headless", False)

    @property
    def user_data_dir(self) -> Path:
        p = BASE_DIR / self.config_yaml.get("automation", {}).get("user_data_dir", "data/chrome_profile")
        p.mkdir(parents=True, exist_ok=True)
        return p

    # Candidate Mobility Policy (Dynamic - No Hardcoding)
    @property
    def home_country(self) -> str:
        return self.config_yaml.get("candidate_mobility", {}).get(
            "home_country",
            self.profile_yaml.get("personal_information", {}).get("country", "Bangladesh")
        )

    @property
    def home_city(self) -> str:
        return self.config_yaml.get("candidate_mobility", {}).get(
            "home_city",
            self.profile_yaml.get("personal_information", {}).get("city", "Dhaka")
        )

    @property
    def candidate_mobility(self) -> Dict[str, Any]:
        return self.config_yaml.get("candidate_mobility", {
            "home_country": self.home_country,
            "home_city": self.home_city,
            "accept_remote_worldwide": True,
            "accept_home_country_onsite": True,
            "accept_foreign_onsite_with_visa": True,
            "reject_foreign_onsite_without_visa": True
        })

    def get_candidate_profile(self) -> Dict[str, Any]:
        return self.profile_yaml

    def reload(self):
        """Reload configuration from disk."""
        self.config_yaml = load_yaml(CONFIG_DIR / "config.yaml")
        self.secrets_yaml = load_yaml(CONFIG_DIR / "secrets.yaml")
        if not self.secrets_yaml:
            self.secrets_yaml = load_yaml(CONFIG_DIR / "secrets.yaml.example")
        self.profile_yaml = load_yaml(CONFIG_DIR / "profile_resume.yaml")

    def save_llm_settings(
        self,
        provider: str,
        model: str,
        groq_key: Optional[str] = None,
        api_keys: Optional[Dict[str, str]] = None,
        ollama_host: Optional[str] = None
    ) -> bool:
        """Persists LLM router selection and API keys to disk and reloads in-memory config."""
        try:
            config_path = CONFIG_DIR / "config.yaml"
            cfg = load_yaml(config_path)
            if "ai_router" not in cfg:
                cfg["ai_router"] = {}
            cfg["ai_router"]["active_provider"] = provider
            cfg["ai_router"]["model_name"] = model
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)

            secrets_path = CONFIG_DIR / "secrets.yaml"
            sec = load_yaml(secrets_path) or {}

            # Save legacy groq_key parameter if present
            if groq_key and groq_key.strip() and not groq_key.startswith("gsk_your_"):
                sec["groq_api_key"] = groq_key.strip()

            # Save dictionary of provider api_keys
            if api_keys and isinstance(api_keys, dict):
                for k, v in api_keys.items():
                    if v and str(v).strip() and not str(v).startswith("your_") and not str(v).startswith("sk-your"):
                        sec[k] = str(v).strip()

            # Save ollama_host
            if ollama_host and ollama_host.strip():
                sec["ollama_host"] = ollama_host.strip()

            with open(secrets_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(sec, f, sort_keys=False, allow_unicode=True)

            self.reload()
            return True
        except Exception as e:
            print(f"Error persisting LLM settings: {e}")
            return False

    def save_search_preferences(
        self,
        positions: List[str],
        locations: List[str],
        max_age_days: int = 7,
        mobility: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Persists target job roles, locations, and mobility rules to config.yaml."""
        try:
            config_path = CONFIG_DIR / "config.yaml"
            cfg = load_yaml(config_path)
            if "search_preferences" not in cfg:
                cfg["search_preferences"] = {}

            clean_positions = [p.strip() for p in positions if p and p.strip()]
            clean_locations = [l.strip() for l in locations if l and l.strip()]

            if clean_positions:
                cfg["search_preferences"]["positions"] = clean_positions
            if clean_locations:
                cfg["search_preferences"]["locations"] = clean_locations
            cfg["search_preferences"]["max_age_days"] = max_age_days

            if mobility:
                if "candidate_mobility" not in cfg:
                    cfg["candidate_mobility"] = {}
                cfg["candidate_mobility"].update(mobility)

            with open(config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)

            self.reload()
            return True
        except Exception as e:
            print(f"Error persisting search preferences: {e}")
            return False


settings = AppSettings()
