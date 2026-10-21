"""
Profile and Candidate Configuration Endpoints.
"""

from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
import yaml
from config.settings import settings, CONFIG_DIR
from ai_engine.resume_parser import resume_parser

router = APIRouter(prefix="/api/profile", tags=["Profile"])

PROFILE_FILE = CONFIG_DIR / "profile_resume.yaml"


@router.post("/upload-resume")
async def upload_resume_file(file: UploadFile = File(...)):
    """
    Upload a resume file (PDF, DOCX, TXT),
    extracts the text, uses Groq LLM to parse into candidate schema,
    saves the profile and updates candidate mobility & visual profile.
    """
    from backend.websocket import manager
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        manager.broadcast_sync({
            "type": "RESUME_UPLOAD_START",
            "message": f"Parsing uploaded resume '{file.filename}' ({len(content)} bytes) with Groq AI..."
        })

        parsed = resume_parser.parse_resume(file_bytes=content, filename=file.filename or "resume.pdf")

        manager.broadcast_sync({
            "type": "RESUME_PARSED",
            "message": f"Successfully parsed resume for {parsed.get('personal_information', {}).get('first_name', 'Candidate')}! Profile updated."
        })

        return {
            "success": True,
            "message": f"Resume '{file.filename}' parsed and profile generated successfully!",
            "profile": parsed,
            "filename": file.filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse resume: {str(e)}")


@router.get("")
def get_profile():
    return {
        "profile": settings.get_candidate_profile(),
        "active_llm": {
            "provider": settings.active_llm_provider,
            "model": settings.active_llm_model,
            "ollama_host": settings.ollama_host
        }
    }


@router.put("")
def update_profile(new_profile: dict):
    try:
        with open(PROFILE_FILE, "w", encoding="utf-8") as f:
            yaml.safe_dump(new_profile, f, sort_keys=False, allow_unicode=True)
        # Reload settings cache
        settings.profile_yaml = new_profile
        return {"success": True, "message": "Profile updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save profile: {e}")


@router.get("/preferences")
def get_search_preferences():
    from backend.services.autopilot import autopilot_service
    return {
        "positions": settings.target_positions,
        "locations": settings.target_locations,
        "max_age_days": settings.config_yaml.get("search_preferences", {}).get("max_age_days", 7),
        "mobility": settings.candidate_mobility,
        "autopilot_running": autopilot_service.is_running,
        "autopilot_interval_hours": 12.0,
        "last_run_time": autopilot_service.last_run_time.isoformat() if autopilot_service.last_run_time else None,
        "last_run_stats": autopilot_service.last_run_stats
    }


@router.post("/preferences")
def update_search_preferences(payload: dict):
    from backend.websocket import manager
    positions = payload.get("positions", [])
    locations = payload.get("locations", [])
    max_age_days = int(payload.get("max_age_days", 7))
    mobility = payload.get("mobility")

    success = settings.save_search_preferences(
        positions=positions,
        locations=locations,
        max_age_days=max_age_days,
        mobility=mobility
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save search preferences")

    manager.broadcast_sync({
        "type": "PREFERENCES_UPDATED",
        "positions": settings.target_positions,
        "locations": settings.target_locations,
        "message": f"Updated search preferences: {len(settings.target_positions)} roles, {len(settings.target_locations)} locations."
    })

    return {
        "success": True,
        "message": "Search preferences updated successfully",
        "positions": settings.target_positions,
        "locations": settings.target_locations,
        "max_age_days": max_age_days
    }


# Settings Router
settings_router = APIRouter(prefix="/api/settings", tags=["Settings"])


def _mask_key(key: str) -> str:
    if not key or "your" in key.lower() or len(key) < 8:
        return ""
    if len(key) <= 12:
        return f"{key[:3]}...{key[-3:]}"
    return f"{key[:6]}...{key[-4:]}"


@settings_router.get("")
def get_settings():
    groq_k = settings.groq_api_key
    openai_k = settings.openai_api_key
    anthropic_k = settings.anthropic_api_key
    gemini_k = settings.gemini_api_key
    deepseek_k = settings.deepseek_api_key
    openrouter_k = settings.openrouter_api_key

    providers_catalog = {
        "groq": {
            "name": "Groq Cloud (Free LPU)",
            "configured": bool(groq_k and "your" not in groq_k.lower() and len(groq_k) > 10),
            "masked_key": _mask_key(groq_k),
            "default_model": "llama-3.3-70b-versatile",
            "recommended_models": [
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant",
                "mixtral-8x7b-32768",
                "gemma2-9b-it"
            ],
            "portal_url": "https://console.groq.com/keys",
            "portal_name": "Groq Console"
        },
        "openai": {
            "name": "OpenAI Commercial API",
            "configured": bool(openai_k and "your" not in openai_k.lower() and len(openai_k) > 10),
            "masked_key": _mask_key(openai_k),
            "default_model": "gpt-4o-mini",
            "recommended_models": ["gpt-4o-mini", "gpt-4o", "o3-mini"],
            "portal_url": "https://platform.openai.com/api-keys",
            "portal_name": "OpenAI Platform"
        },
        "anthropic": {
            "name": "Anthropic Claude API",
            "configured": bool(anthropic_k and "your" not in anthropic_k.lower() and len(anthropic_k) > 10),
            "masked_key": _mask_key(anthropic_k),
            "default_model": "claude-3-5-sonnet-20241022",
            "recommended_models": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
            "portal_url": "https://console.anthropic.com/settings/keys",
            "portal_name": "Anthropic Console"
        },
        "gemini": {
            "name": "Google Gemini API",
            "configured": bool(gemini_k and "your" not in gemini_k.lower() and len(gemini_k) > 10),
            "masked_key": _mask_key(gemini_k),
            "default_model": "gemini-2.0-flash",
            "recommended_models": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
            "portal_url": "https://aistudio.google.com/app/apikey",
            "portal_name": "Google AI Studio"
        },
        "deepseek": {
            "name": "DeepSeek API",
            "configured": bool(deepseek_k and "your" not in deepseek_k.lower() and len(deepseek_k) > 10),
            "masked_key": _mask_key(deepseek_k),
            "default_model": "deepseek-chat",
            "recommended_models": ["deepseek-chat", "deepseek-reasoner"],
            "portal_url": "https://platform.deepseek.com/api_keys",
            "portal_name": "DeepSeek Platform"
        },
        "openrouter": {
            "name": "OpenRouter (200+ Models)",
            "configured": bool(openrouter_k and "your" not in openrouter_k.lower() and len(openrouter_k) > 10),
            "masked_key": _mask_key(openrouter_k),
            "default_model": "openrouter/auto",
            "recommended_models": ["openrouter/auto", "anthropic/claude-3.5-sonnet", "deepseek/deepseek-r1"],
            "portal_url": "https://openrouter.ai/keys",
            "portal_name": "OpenRouter Keys"
        },
        "ollama": {
            "name": "Ollama Local Private",
            "configured": True,
            "masked_key": "",
            "default_model": "llama3.3",
            "recommended_models": ["llama3.3", "mistral", "deepseek-r1:8b", "qwen2.5"],
            "portal_url": "https://ollama.ai",
            "portal_name": "Ollama Download"
        }
    }

    return {
        "provider": settings.active_llm_provider,
        "model": settings.active_llm_model,
        "groq_configured": providers_catalog["groq"]["configured"],
        "ollama_host": settings.ollama_host,
        "candidate_mobility": settings.candidate_mobility,
        "home_country": settings.home_country,
        "home_city": settings.home_city,
        "providers": providers_catalog
    }


@settings_router.post("")
def update_settings(payload: dict):
    provider = payload.get("provider", "groq").lower()
    model = payload.get("model", "llama-3.3-70b-versatile")
    api_key = payload.get("api_key")
    ollama_host = payload.get("ollama_host")

    # Map single api_key to the provider's specific key name in secrets.yaml
    api_keys = payload.get("api_keys", {})
    if api_key and api_key.strip():
        key_mapping = {
            "groq": "groq_api_key",
            "openai": "openai_api_key",
            "anthropic": "anthropic_api_key",
            "gemini": "gemini_api_key",
            "deepseek": "deepseek_api_key",
            "openrouter": "openrouter_api_key"
        }
        field_name = key_mapping.get(provider)
        if field_name:
            api_keys[field_name] = api_key.strip()

    legacy_groq_key = payload.get("groq_key")
    if legacy_groq_key and legacy_groq_key.strip():
        api_keys["groq_api_key"] = legacy_groq_key.strip()

    success = settings.save_llm_settings(
        provider=provider,
        model=model,
        api_keys=api_keys,
        ollama_host=ollama_host
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save settings to disk")

    return {
        "success": True,
        "message": f"Inference Router configured to '{provider}' ({model})",
        "provider": provider,
        "model": model
    }


@settings_router.post("/test-connection")
def test_settings_connection(payload: dict):
    """Live probe against the specified provider using the provided or configured credentials."""
    from ai_engine.llm_router import LLMRouter
    provider = payload.get("provider", "groq")
    model = payload.get("model")
    api_key = payload.get("api_key")
    ollama_host = payload.get("ollama_host")

    router = LLMRouter(provider=provider, model=model)
    result = router.test_connection(
        provider=provider,
        model=model,
        api_key=api_key,
        ollama_host=ollama_host
    )
    return result


