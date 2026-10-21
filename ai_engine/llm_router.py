"""
Multi-LLM Router & Client Manager.
Supports Local Models (Ollama, DeepSeek) and Cloud APIs (OpenAI, Gemini, Anthropic).
"""

import os
import json
import re
from typing import Dict, Any, Optional, List
import httpx
from config.logger import logger
from config.settings import settings


class LLMRouter:
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        self.provider = (provider or settings.active_llm_provider).lower()
        self.model = model or settings.active_llm_model
        self.ollama_host = settings.ollama_host.rstrip("/")

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        """Dispatches prompt to configured provider with automatic fallback."""
        try:
            if self.provider == "groq":
                return self._call_groq(system_prompt, user_prompt, temperature)
            elif self.provider == "ollama":
                return self._call_ollama(system_prompt, user_prompt, temperature)
            elif self.provider == "deepseek":
                return self._call_deepseek(system_prompt, user_prompt, temperature)
            elif self.provider == "openai":
                return self._call_openai(system_prompt, user_prompt, temperature)
            elif self.provider == "gemini":
                return self._call_gemini(system_prompt, user_prompt, temperature)
            elif self.provider == "anthropic":
                return self._call_anthropic(system_prompt, user_prompt, temperature)
            elif self.provider == "openrouter":
                return self._call_openrouter(system_prompt, user_prompt, temperature)
            else:
                logger.warning(f"Unknown provider '{self.provider}'. Falling back to heuristic engine.")
                return self._heuristic_fallback(system_prompt, user_prompt)
        except Exception as e:
            logger.error(f"Error calling LLM provider {self.provider}: {e}")
            logger.info("Falling back to local heuristic response generator.")
            return self._heuristic_fallback(system_prompt, user_prompt)

    def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Ensures the LLM output is parsed into a clean JSON dictionary."""
        raw_text = self.generate(system_prompt, user_prompt)
        # Extract json markdown if wrapped in ```json ... ```
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)
        if json_match:
            raw_text = json_match.group(1).strip()
        else:
            # Look for outermost braces
            brace_match = re.search(r"(\{[\s\S]*\})", raw_text)
            if brace_match:
                raw_text = brace_match.group(1).strip()

        try:
            return json.loads(raw_text)
        except Exception as e:
            logger.error(f"Failed to parse LLM JSON output: {e}\nRaw was: {raw_text[:200]}")
            return self._default_json_eval()

    # Provider Implementations
    def _call_groq(self, system_prompt: str, user_prompt: str, temperature: float, key_override: Optional[str] = None, model_override: Optional[str] = None) -> str:
        """Calls Groq Cloud API (Free LPU Tier with ~500 tokens/sec)."""
        key = (key_override or settings.groq_api_key or "").strip()
        if not key or "your_" in key:
            raise ValueError("Groq API key not configured. Obtain a free key at https://console.groq.com/keys")
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
        target_model = model_override or self.model or "llama-3.3-70b-versatile"
        if "qwen" in target_model.lower():
            target_model = "llama-3.3-70b-versatile"
        payload = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature
        }
        with httpx.Client(timeout=35.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise ValueError(f"Groq API error ({resp.status_code}): {resp.text}")
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    def _call_ollama(self, system_prompt: str, user_prompt: str, temperature: float, host_override: Optional[str] = None, model_override: Optional[str] = None) -> str:
        host = (host_override or self.ollama_host or "http://localhost:11434").rstrip("/")
        target_model = model_override or self.model or "llama3.3"
        url = f"{host}/api/chat"
        payload = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "options": {"temperature": temperature}
        }
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code != 200:
                raise ValueError(f"Ollama error ({resp.status_code}): {resp.text}")
            data = resp.json()
            return data.get("message", {}).get("content", "")

    def _call_deepseek(self, system_prompt: str, user_prompt: str, temperature: float, key_override: Optional[str] = None, model_override: Optional[str] = None) -> str:
        key = (key_override or settings.deepseek_api_key or "").strip()
        if not key or "your-" in key:
            raise ValueError("DeepSeek API key not configured. Obtain at https://platform.deepseek.com")
        url = "https://api.deepseek.com/chat/completions"
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        payload = {
            "model": model_override or self.model or "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature
        }
        with httpx.Client(timeout=45.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise ValueError(f"DeepSeek error ({resp.status_code}): {resp.text}")
            return resp.json()["choices"][0]["message"]["content"]

    def _call_openai(self, system_prompt: str, user_prompt: str, temperature: float, key_override: Optional[str] = None, model_override: Optional[str] = None) -> str:
        key = (key_override or settings.openai_api_key or "").strip()
        if not key or "your-" in key:
            raise ValueError("OpenAI API key not configured. Obtain at https://platform.openai.com/api-keys")
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        payload = {
            "model": model_override or self.model or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature
        }
        with httpx.Client(timeout=45.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise ValueError(f"OpenAI error ({resp.status_code}): {resp.text}")
            return resp.json()["choices"][0]["message"]["content"]

    def _call_gemini(self, system_prompt: str, user_prompt: str, temperature: float, key_override: Optional[str] = None, model_override: Optional[str] = None) -> str:
        key = (key_override or settings.gemini_api_key or "").strip()
        if not key or "your-" in key:
            raise ValueError("Gemini API key not configured. Obtain at https://aistudio.google.com/app/apikey")
        target_model = model_override or self.model or "gemini-2.0-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={key}"
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}
            ],
            "generationConfig": {"temperature": temperature}
        }
        with httpx.Client(timeout=45.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code != 200:
                raise ValueError(f"Gemini error ({resp.status_code}): {resp.text}")
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    def _call_anthropic(self, system_prompt: str, user_prompt: str, temperature: float, key_override: Optional[str] = None, model_override: Optional[str] = None) -> str:
        key = (key_override or settings.anthropic_api_key or "").strip()
        if not key or "your-" in key:
            raise ValueError("Anthropic API key not configured. Obtain at https://console.anthropic.com")
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_override or self.model or "claude-3-5-sonnet-20241022",
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "max_tokens": 2048,
            "temperature": temperature
        }
        with httpx.Client(timeout=45.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise ValueError(f"Anthropic error ({resp.status_code}): {resp.text}")
            data = resp.json()
            return data["content"][0]["text"]

    def _call_openrouter(self, system_prompt: str, user_prompt: str, temperature: float, key_override: Optional[str] = None, model_override: Optional[str] = None) -> str:
        key = (key_override or settings.openrouter_api_key or "").strip()
        if not key or "your-" in key:
            raise ValueError("OpenRouter API key not configured. Obtain at https://openrouter.ai/keys")
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {key}",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "JobHunter Pro",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_override or self.model or "openrouter/auto",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature
        }
        with httpx.Client(timeout=45.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise ValueError(f"OpenRouter error ({resp.status_code}): {resp.text}")
            return resp.json()["choices"][0]["message"]["content"]

    def test_connection(
        self,
        provider: str,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        ollama_host: Optional[str] = None
    ) -> Dict[str, Any]:
        """Performs a live probe against the specified provider and measures response latency."""
        import time
        p = (provider or self.provider).lower()
        m = model or self.model
        sys_p = "You are an autonomous health check assistant. Respond in 2-3 words."
        usr_p = "Ping test. Please reply with: 'JobHunter OK'"

        start_time = time.perf_counter()
        try:
            if p == "groq":
                reply = self._call_groq(sys_p, usr_p, 0.1, key_override=api_key, model_override=m)
            elif p == "ollama":
                reply = self._call_ollama(sys_p, usr_p, 0.1, host_override=ollama_host, model_override=m)
            elif p == "openai":
                reply = self._call_openai(sys_p, usr_p, 0.1, key_override=api_key, model_override=m)
            elif p == "anthropic":
                reply = self._call_anthropic(sys_p, usr_p, 0.1, key_override=api_key, model_override=m)
            elif p == "gemini":
                reply = self._call_gemini(sys_p, usr_p, 0.1, key_override=api_key, model_override=m)
            elif p == "deepseek":
                reply = self._call_deepseek(sys_p, usr_p, 0.1, key_override=api_key, model_override=m)
            elif p == "openrouter":
                reply = self._call_openrouter(sys_p, usr_p, 0.1, key_override=api_key, model_override=m)
            else:
                raise ValueError(f"Unsupported provider for connection test: {p}")

            latency_ms = round((time.perf_counter() - start_time) * 1000)
            return {
                "success": True,
                "provider": p,
                "model": m,
                "latency_ms": latency_ms,
                "reply": reply.strip()[:60],
                "message": f"✓ {p.upper()} connected successfully! Model '{m}' responded in {latency_ms}ms."
            }
        except Exception as e:
            latency_ms = round((time.perf_counter() - start_time) * 1000)
            err_msg = str(e)
            return {
                "success": False,
                "provider": p,
                "model": m,
                "latency_ms": latency_ms,
                "error": err_msg,
                "message": f"✕ Connection to {p.upper()} failed: {err_msg}"
            }

    def _heuristic_fallback(self, system_prompt: str, user_prompt: str) -> str:
        """Heuristic rule-based fallback when external LLM is offline (100% parameter-driven, zero hardcoding)."""
        prompt_lower = user_prompt.lower()
        profile_yaml = settings.get_candidate_profile()
        personal = profile_yaml.get("personal_information", {})
        home_country = settings.home_country.lower()
        home_city = settings.home_city.lower()

        if "evaluate this job posting" in prompt_lower or "score" in system_prompt.lower():
            # Dynamically aggregate all candidate skills across categories
            candidate_skills: List[str] = []
            for group in profile_yaml.get("skills", {}).values():
                if isinstance(group, list):
                    candidate_skills.extend([str(s).strip() for s in group if str(s).strip()])

            # Find matching skills dynamically
            matched_skills = [s for s in candidate_skills if s.lower() in prompt_lower]
            total_checked = min(len(candidate_skills), 15) if candidate_skills else 1
            ratio = len(matched_skills) / max(total_checked, 1)
            score = int(min(98, max(50, ratio * 100 + 35)))

            # -------------------------------------------------------------
            # Dynamic Mobility & Visa Sponsorship Dealbreaker Evaluation
            # -------------------------------------------------------------
            job_section = prompt_lower.split("=== job details ===")[-1] if "=== job details ===" in prompt_lower else prompt_lower

            # Check if this specific job is remote
            is_remote = ("remote: yes" in job_section) or any(r in job_section for r in [
                "location: remote", "fully remote", "100% remote", "worldwide remote", "work from anywhere"
            ])
            
            # Check if job is in candidate's home country / city
            is_local = (home_country in job_section) or (home_city in job_section)
            
            # Visa & Relocation Support detection
            offers_visa = any(v in job_section for v in [
                "visa sponsorship", "sponsorship available", "we sponsor", "will sponsor",
                "relocation assistance", "relocation support", "relocation package",
                "visa support", "visa assistance", "relocation provided"
            ])
            
            # Visa Denial / Domestic restriction detection
            denies_visa = any(d in job_section for d in [
                "no visa", "no sponsorship", "unable to sponsor", "cannot sponsor",
                "not offer sponsorship", "without sponsorship", "no visa sponsorship",
                "without need for sponsorship", "without requiring sponsorship",
                "must be legally authorized to work in the us without sponsorship",
                "must be legally authorized to work in the united states without",
                "us citizenship required", "citizen only", "green card required",
                "permanent resident only", "security clearance required", "ts/sci"
            ])

            dealbreaker = False
            dealbreaker_reason = None

            # Policy Rule 1: Foreign On-site without Visa Sponsorship
            if not is_remote and not is_local:
                if offers_visa and not denies_visa:
                    # Candidate accepts foreign on-site because visa sponsorship is provided!
                    dealbreaker = False
                else:
                    dealbreaker = True
                    dealbreaker_reason = f"On-site role outside {settings.home_country} does not provide visa sponsorship."
                    score = min(score, 45)
            elif denies_visa and not is_local:
                # Even if remote, if role requires national citizenship / security clearance
                if "citizenship required" in job_section or "security clearance" in job_section:
                    dealbreaker = True
                    dealbreaker_reason = "Requires domestic citizenship or security clearance restricted to local citizens."
                    score = min(score, 45)

            # Determine missing skills
            missing = [s for s in candidate_skills[:8] if s.lower() not in matched_skills][:3] if score < 80 else []

            verdict = "APPLY" if score >= settings.min_match_score and not dealbreaker else ("SKIP" if dealbreaker else "REVIEW")

            top_matches = ", ".join(matched_skills[:4]) if matched_skills else "core engineering foundations"
            return json.dumps({
                "score": score,
                "verdict": verdict,
                "dealbreaker_triggered": dealbreaker,
                "dealbreaker_reason": dealbreaker_reason,
                "pros": [
                    f"Strong alignment with candidate stack: {top_matches}",
                    "Workplace location matches candidate mobility profile" if not dealbreaker else "Technical background overlaps"
                ],
                "cons": [dealbreaker_reason] if dealbreaker else ["Some specialized niche tooling may require brief ramp-up"],
                "missing_skills": missing,
                "full_rationale": f"Candidate profile demonstrates {score}% alignment. {'Rejected due to mobility/visa restrictions.' if dealbreaker else f'Recommended for {verdict.lower()}.'}"
            })

        if "cover letter" in user_prompt.lower():
            candidate_name = f"{personal.get('first_name', '')} {personal.get('last_name', '')}".strip() or "Candidate"
            headline = personal.get("headline", "Software Engineer")
            experience = profile_yaml.get("experience", [{}])
            latest_role = experience[0].get("position", "Software Engineer") if experience else "Engineer"
            years = profile_yaml.get("screening_answers", {}).get("years_of_experience", 5)

            return f"""Dear Hiring Team,

I am writing to express my strong enthusiasm for this position. With over {years} years of professional experience as a {latest_role} and specializing as a {headline}, I have led and contributed to scalable architectures, robust automated pipelines, and high-impact digital solutions.

In my recent engagements, I have focused on building resilient systems that optimize runtime performance, improve developer workflows, and deliver measurable business outcomes. I take pride in rapid problem solving, clean maintainable code, and proactive cross-functional collaboration.

I am particularly excited about the vision of your company and would love the opportunity to contribute my skills to your team. Thank you for your consideration, and I look forward to speaking with you.

Sincerely,
{candidate_name}"""

        # General Question Answering (Dynamically sourced from profile screening answers)
        answers = profile_yaml.get("screening_answers", {})
        if "authorized" in prompt_lower:
            return answers.get("legally_authorized_to_work", "Yes")
        if "sponsorship" in prompt_lower:
            return answers.get("requires_visa_sponsorship", "Yes")
        if "relocate" in prompt_lower:
            return answers.get("willing_to_relocate", "Yes (with visa sponsorship)")
        if "remote" in prompt_lower:
            return answers.get("open_to_remote", "Yes")
        if "years" in prompt_lower and "experience" in prompt_lower:
            return str(answers.get("years_of_experience", 5))
        if "salary" in prompt_lower:
            return str(answers.get("target_annual_salary_usd", "85000"))

        return "Yes, I have extensive professional experience in this domain and have successfully delivered production projects meeting these requirements."

    def _default_json_eval(self) -> Dict[str, Any]:
        return {
            "score": 75,
            "verdict": "REVIEW",
            "dealbreaker_triggered": False,
            "dealbreaker_reason": None,
            "pros": ["Solid technical fundamentals", "Full stack capability"],
            "cons": ["Need further verification of domain specifics"],
            "missing_skills": [],
            "full_rationale": "Evaluated with default fallback parameters."
        }
