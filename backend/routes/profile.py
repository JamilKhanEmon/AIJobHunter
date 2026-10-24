"""
Profile and Candidate Configuration Endpoints.
"""

from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from sqlalchemy.orm import Session
import yaml
from config.settings import settings, CONFIG_DIR, DATA_DIR
from ai_engine.resume_parser import resume_parser
from database.connection import get_db
from database.models import User, UserProfile
from backend.auth import get_current_user

router = APIRouter(prefix="/api/profile", tags=["Profile"])

PROFILE_FILE = CONFIG_DIR / "profile_resume.yaml"


@router.post("/upload-resume")
async def upload_resume_file(
    file: UploadFile = File(...),
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a resume file (PDF, DOCX, TXT),
    extracts the text, uses LLM to parse into candidate schema,
    saves the profile to the authenticated user's profile record (or local yaml if guest).
    """
    from backend.websocket import manager
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        manager.broadcast_sync({
            "type": "RESUME_UPLOAD_START",
            "message": f"Parsing uploaded resume '{file.filename}' ({len(content)} bytes) with AI..."
        })

        # If user is authenticated, do not overwrite default global file
        should_persist_global = (user is None)
        parsed = resume_parser.parse_resume(file_bytes=content, filename=file.filename or "resume.pdf", persist=should_persist_global)

        if user:
            # Save directly to user's profile in database
            user_prof = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
            if not user_prof:
                user_prof = UserProfile(user_id=user.id)
                db.add(user_prof)

            pers = parsed.get("personal_information", {})
            user_prof.headline = pers.get("headline", "")
            user_prof.phone = f"{pers.get('phone_country_code', '')}{pers.get('phone_number', '')}"
            user_prof.city = pers.get("city", "")
            user_prof.country = pers.get("country", "Bangladesh")
            user_prof.github_url = pers.get("github_url", "")
            user_prof.linkedin_url = pers.get("linkedin_url", "")
            user_prof.portfolio_url = pers.get("portfolio_url", "")
            user_prof.summary = parsed.get("summary", "")
            user_prof.skills = parsed.get("skills", {})
            user_prof.experience = parsed.get("experience", [])
            user_prof.education = parsed.get("education", [])
            user_prof.screening_answers = parsed.get("screening_answers", {})
            user_prof.resume_filename = file.filename

            # If full name was extracted, update user model
            first = pers.get("first_name", "")
            last = pers.get("last_name", "")
            if first or last:
                user.full_name = f"{first} {last}".strip()

            db.commit()
            db.refresh(user_prof)

        first_name = parsed.get('personal_information', {}).get('first_name', user.full_name if user else 'Candidate')
        manager.broadcast_sync({
            "type": "RESUME_PARSED",
            "message": f"Successfully parsed resume for {first_name}! Profile updated."
        })

        return {
            "success": True,
            "message": f"Resume '{file.filename}' parsed and profile generated successfully!",
            "profile": parsed,
            "filename": file.filename,
            "is_authenticated": user is not None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse resume: {str(e)}")


@router.get("")
def get_profile(user: Optional[User] = Depends(get_current_user)):
    """Returns candidate profile for the active authenticated user, or None if guest in multi-user environment."""
    if user and user.profile:
        profile_data = user.profile.to_candidate_schema()
    elif user:
        profile_data = None
    else:
        profile_data = None

    return {
        "profile": profile_data,
        "is_authenticated": user is not None,
        "user": user.to_dict() if user else None,
        "active_llm": {
            "provider": settings.active_llm_provider,
            "model": settings.active_llm_model,
            "ollama_host": settings.ollama_host
        }
    }


@router.put("")
def update_profile(
    new_profile: dict,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        if user:
            user_prof = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
            if not user_prof:
                user_prof = UserProfile(user_id=user.id)
                db.add(user_prof)

            pers = new_profile.get("personal_information", {})
            user_prof.headline = pers.get("headline", user_prof.headline)
            user_prof.phone = pers.get("phone_number", user_prof.phone)
            user_prof.city = pers.get("city", user_prof.city)
            user_prof.country = pers.get("country", user_prof.country)
            user_prof.summary = new_profile.get("summary", user_prof.summary)
            user_prof.skills = new_profile.get("skills", user_prof.skills)
            user_prof.experience = new_profile.get("experience", user_prof.experience)
            user_prof.education = new_profile.get("education", user_prof.education)
            db.commit()
            return {"success": True, "message": "User profile updated successfully in database"}

        # Fallback to local file for single-user/guest
        with open(PROFILE_FILE, "w", encoding="utf-8") as f:
            yaml.safe_dump(new_profile, f, sort_keys=False, allow_unicode=True)
        settings.profile_yaml = new_profile
        return {"success": True, "message": "Profile updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save profile: {e}")


@router.get("/preferences")
def get_search_preferences(
    user: Optional[User] = Depends(get_current_user)
):
    from backend.services.autopilot import autopilot_service
    # If user is authenticated and has custom preferences saved, return them
    if user and user.profile and user.profile.search_preferences:
        up = user.profile.search_preferences
        return {
            "positions": up.get("positions", settings.target_positions),
            "locations": up.get("locations", settings.target_locations),
            "max_age_days": up.get("max_age_days", 5),
            "mobility": up.get("mobility", settings.candidate_mobility),
            "autopilot_running": autopilot_service.is_running,
            "autopilot_interval_hours": 12.0,
            "last_run_time": autopilot_service.last_run_time.isoformat() if autopilot_service.last_run_time else None,
            "last_run_stats": autopilot_service.last_run_stats
        }

    return {
        "positions": settings.target_positions,
        "locations": settings.target_locations,
        "max_age_days": settings.config_yaml.get("search_preferences", {}).get("max_age_days", 5),
        "mobility": settings.candidate_mobility,
        "autopilot_running": autopilot_service.is_running,
        "autopilot_interval_hours": 12.0,
        "last_run_time": autopilot_service.last_run_time.isoformat() if autopilot_service.last_run_time else None,
        "last_run_stats": autopilot_service.last_run_stats
    }


@router.post("/preferences")
def update_search_preferences(
    payload: dict,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from backend.websocket import manager
    positions = payload.get("positions", [])
    locations = payload.get("locations", [])
    max_age_days = int(payload.get("max_age_days", 5))
    mobility = payload.get("mobility")

    if user:
        user_prof = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
        if not user_prof:
            user_prof = UserProfile(user_id=user.id)
            db.add(user_prof)
        user_prof.search_preferences = {
            "positions": positions,
            "locations": locations,
            "max_age_days": max_age_days,
            "mobility": mobility
        }
        db.commit()

    # Also persist to settings for guest fallback
    settings.save_search_preferences(
        positions=positions,
        locations=locations,
        max_age_days=max_age_days,
        mobility=mobility
    )

    manager.broadcast_sync({
        "type": "PREFERENCES_UPDATED",
        "positions": positions or settings.target_positions,
        "locations": locations or settings.target_locations,
        "message": f"Updated search preferences: {len(positions or settings.target_positions)} roles, {len(locations or settings.target_locations)} locations."
    })

    return {
        "success": True,
        "message": "Search preferences updated successfully",
        "positions": positions or settings.target_positions,
        "locations": locations or settings.target_locations,
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
def get_settings(user: Optional[User] = Depends(get_current_user)):
    user_keys = (user.profile.api_keys or {}) if user and user.profile else {}

    groq_k = user_keys.get("groq_api_key") or settings.groq_api_key
    openai_k = user_keys.get("openai_api_key") or settings.openai_api_key
    anthropic_k = user_keys.get("anthropic_api_key") or settings.anthropic_api_key
    gemini_k = user_keys.get("gemini_api_key") or settings.gemini_api_key
    deepseek_k = user_keys.get("deepseek_api_key") or settings.deepseek_api_key
    openrouter_k = user_keys.get("openrouter_api_key") or settings.openrouter_api_key

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
        "is_authenticated": user is not None,
        "user_email": user.email if user else None,
        "providers": providers_catalog
    }


@settings_router.post("")
def update_settings(
    payload: dict,
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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

    # Save to user profile in DB if user is authenticated
    if user:
        user_prof = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
        if not user_prof:
            user_prof = UserProfile(user_id=user.id)
            db.add(user_prof)
        current_keys = dict(user_prof.api_keys or {})
        current_keys.update(api_keys)
        user_prof.api_keys = current_keys
        db.commit()

    # Also persist to settings for system fallback
    settings.save_llm_settings(
        provider=provider,
        model=model,
        api_keys=api_keys,
        ollama_host=ollama_host
    )

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


@settings_router.post("/list-models")
def list_provider_models(payload: dict):
    """
    Fetches the live list of available models from the selected provider using the given API key.
    Falls back to a curated static list if the provider API does not support model listing.
    """
    import httpx
    provider = (payload.get("provider") or "groq").lower()
    api_key = (payload.get("api_key") or "").strip()

    # Static fallback curated lists (used when provider has no models API or key is missing)
    STATIC_FALLBACKS = {
        "groq": [
            {"id": "openai/gpt-oss-120b", "name": "OpenAI GPT-OSS 120B (Best Quality)", "active": True},
            {"id": "openai/gpt-oss-20b", "name": "OpenAI GPT-OSS 20B (Ultra Fast)"},
            {"id": "qwen/qwen3.8-27b", "name": "Qwen 3.8 27B"},
            {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3 70B Versatile"},
            {"id": "llama-3.1-8b-instant", "name": "Llama 3.1 8B Instant"},
            {"id": "llama-3.1-70b-versatile", "name": "Llama 3.1 70B Versatile"},
        ],
        "openai": [
            {"id": "gpt-4o", "name": "GPT-4o (Best Quality)"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini (Fast & Cheap)", "active": True},
            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo"},
            {"id": "o1-mini", "name": "o1 Mini (Reasoning)"},
            {"id": "o3-mini", "name": "o3 Mini (Reasoning)"},
        ],
        "anthropic": [
            {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet (Best)", "active": True},
            {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku (Fast)"},
            {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus (Most Capable)"},
        ],
        "gemini": [
            {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash (Fastest)", "active": True},
            {"id": "gemini-2.0-flash-thinking-exp", "name": "Gemini 2.0 Flash Thinking"},
            {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro"},
            {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash"},
            {"id": "gemini-1.5-flash-8b", "name": "Gemini 1.5 Flash 8B (Nano)"},
        ],
        "deepseek": [
            {"id": "deepseek-chat", "name": "DeepSeek Chat (V3)", "active": True},
            {"id": "deepseek-reasoner", "name": "DeepSeek Reasoner (R1)"},
        ],
        "openrouter": [
            {"id": "openrouter/auto", "name": "Auto Router (Best Available)", "active": True},
            {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet"},
            {"id": "google/gemini-2.0-flash-001", "name": "Gemini 2.0 Flash"},
            {"id": "deepseek/deepseek-r1", "name": "DeepSeek R1 (Reasoning)"},
            {"id": "deepseek/deepseek-chat-v3-0324", "name": "DeepSeek V3"},
            {"id": "meta-llama/llama-3.3-70b-instruct", "name": "Llama 3.3 70B"},
            {"id": "mistralai/mistral-large-2411", "name": "Mistral Large"},
            {"id": "qwen/qwen-2.5-72b-instruct", "name": "Qwen 2.5 72B"},
        ],
        "ollama": [
            {"id": "llama3.3", "name": "Llama 3.3", "active": True},
            {"id": "llama3.1", "name": "Llama 3.1"},
            {"id": "mistral", "name": "Mistral"},
            {"id": "qwen2.5", "name": "Qwen 2.5"},
            {"id": "deepseek-r1:8b", "name": "DeepSeek R1 8B"},
        ],
    }

    # Resolve current key from secrets if not provided in payload
    if not api_key:
        key_map = {
            "groq": settings.groq_api_key,
            "openai": settings.openai_api_key,
            "anthropic": settings.anthropic_api_key,
            "gemini": settings.gemini_api_key,
            "deepseek": settings.deepseek_api_key,
            "openrouter": settings.openrouter_api_key,
        }
        api_key = (key_map.get(provider) or "").strip()

    # For Ollama: try to list local models
    if provider == "ollama":
        try:
            ollama_host = (payload.get("ollama_host") or settings.ollama_host or "http://localhost:11434").rstrip("/")
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{ollama_host}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    local_models = [
                        {"id": m["name"], "name": m["name"]}
                        for m in data.get("models", [])
                    ]
                    if local_models:
                        return {"provider": provider, "models": local_models, "source": "live"}
        except Exception:
            pass
        return {"provider": provider, "models": STATIC_FALLBACKS["ollama"], "source": "fallback"}

    # For Groq: use their live /openai/v1/models endpoint
    if provider == "groq" and api_key and "your" not in api_key:
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    active_ids = {m["id"] for m in data.get("data", [])}
                    # Filter to chat-capable models only (exclude whisper, tts, vision-only)
                    chat_models = [
                        m for m in data.get("data", [])
                        if not any(skip in m["id"] for skip in ["whisper", "distil-whisper", "tts", "guard"])
                    ]
                    models = [{"id": m["id"], "name": m["id"]} for m in sorted(chat_models, key=lambda x: x["id"])]
                    return {"provider": provider, "models": models, "source": "live"}
        except Exception:
            pass

    # For OpenAI: live /v1/models endpoint (filter to gpt only)
    if provider == "openai" and api_key and "your" not in api_key:
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    gpt_models = [
                        m for m in data.get("data", [])
                        if any(pfx in m["id"] for pfx in ["gpt-", "o1", "o3"])
                        and "instruct" not in m["id"]
                    ]
                    models = [{"id": m["id"], "name": m["id"]} for m in sorted(gpt_models, key=lambda x: x["id"], reverse=True)[:20]]
                    return {"provider": provider, "models": models, "source": "live"}
        except Exception:
            pass

    # For OpenRouter: live /api/v1/models endpoint
    if provider == "openrouter" and api_key and "your" not in api_key:
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "HTTP-Referer": "http://localhost:8000"
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    all_models = data.get("data", [])
                    # Sort by context_length desc, limit to top 40 popular ones
                    sorted_models = sorted(all_models, key=lambda x: x.get("context_length", 0), reverse=True)
                    models = [
                        {"id": m["id"], "name": f"{m['id']} ({m.get('context_length', 0)//1000}K ctx)"}
                        for m in sorted_models[:40]
                    ]
                    return {"provider": provider, "models": models, "source": "live"}
        except Exception:
            pass

    # For Gemini: use the REST endpoint to list models
    if provider == "gemini" and api_key and "your" not in api_key:
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                )
                if resp.status_code == 200:
                    data = resp.json()
                    gen_models = [
                        m for m in data.get("models", [])
                        if "generateContent" in m.get("supportedGenerationMethods", [])
                    ]
                    models = [
                        {"id": m["name"].replace("models/", ""), "name": m.get("displayName", m["name"])}
                        for m in gen_models
                    ]
                    return {"provider": provider, "models": models, "source": "live"}
        except Exception:
            pass

    # For Anthropic: no public models list API - use static
    # For DeepSeek: no public models list API - use static

    # Return static fallback
    fallback = STATIC_FALLBACKS.get(provider, [])
    return {"provider": provider, "models": fallback, "source": "fallback"}
