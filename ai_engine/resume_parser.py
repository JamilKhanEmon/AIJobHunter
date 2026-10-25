"""
Autonomous Resume & CV Parser Engine.
Extracts text from PDF, DOCX, and TXT resumes and uses Groq Cloud LLM
to generate a complete, structured Candidate Profile (JSON & YAML).
"""

import io
import os
import re
import zlib
from pathlib import Path
from typing import Dict, Any, Optional
import yaml

from config.logger import logger
from config.settings import settings, CONFIG_DIR, DATA_DIR
from ai_engine.llm_router import LLMRouter
from ai_engine.prompts import RESUME_EXTRACTION_SYSTEM_PROMPT, RESUME_EXTRACTION_USER_TEMPLATE


class ResumeParser:
    def __init__(self):
        self.router = LLMRouter()

    def extract_text(self, file_bytes: bytes, filename: str) -> str:
        """
        Extracts raw text from PDF, DOCX, TXT, or MD with multiple fallback strategies.
        Guarantees zero crashes even without external C-dependencies.
        """
        ext = filename.lower().split(".")[-1] if "." in filename else ""

        if ext == "pdf":
            return self._extract_pdf(file_bytes)
        elif ext in ["docx", "doc"]:
            return self._extract_docx(file_bytes)
        else:
            return self._extract_text_plain(file_bytes)

    def _extract_pdf(self, file_bytes: bytes) -> str:
        """Multi-tier PDF text extraction."""
        # Tier 1: Try pypdf
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n".join(pages).strip()
            if len(text) > 50:
                logger.info(f"Successfully extracted {len(text)} chars from PDF using pypdf.")
                return text
        except Exception as e:
            logger.debug(f"pypdf extraction failed/unavailable: {e}")

        # Tier 2: Try PyPDF2
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            pages = [page.extract_text() or "" for page in reader.pages]
            text = "\n".join(pages).strip()
            if len(text) > 50:
                logger.info(f"Successfully extracted {len(text)} chars from PDF using PyPDF2.")
                return text
        except Exception as e:
            logger.debug(f"PyPDF2 extraction failed/unavailable: {e}")

        # Tier 3: Try pdfminer
        try:
            from pdfminer.high_level import extract_text as miner_extract
            text = miner_extract(io.BytesIO(file_bytes)).strip()
            if len(text) > 50:
                logger.info(f"Successfully extracted {len(text)} chars from PDF using pdfminer.")
                return text
        except Exception as e:
            logger.debug(f"pdfminer extraction failed/unavailable: {e}")

        # Tier 4: Pure Python Stream Extraction (Zero Dependencies Fallback)
        logger.info("Running pure Python fallback stream decompression for PDF...")
        return self._extract_pdf_pure_python(file_bytes)

    def _extract_pdf_pure_python(self, file_bytes: bytes) -> str:
        """Standard-library-only stream decompressor for PDF text objects."""
        text_chunks = []
        # Find all FlateDecode streams
        stream_matches = re.findall(b"stream[\r\n]+(.*?)[\r\n]+endstream", file_bytes, re.DOTALL)
        for s in stream_matches:
            decompressed = None
            for wbits in [0, -15, 15, 31, 47]:
                try:
                    decompressed = zlib.decompress(s, wbits)
                    break
                except Exception:
                    continue
            if not decompressed:
                decompressed = s

            # Match text strings inside parentheses
            str_matches = re.findall(b"\((.*?)\)", decompressed)
            for sm in str_matches:
                try:
                    chunk = sm.decode("utf-8", errors="ignore").strip()
                    # Filter out binary glyph garbage
                    if len(chunk) > 1 and any(c.isalnum() for c in chunk):
                        text_chunks.append(chunk)
                except Exception:
                    pass

        extracted = " ".join(text_chunks)
        logger.info(f"Pure Python PDF fallback extracted {len(extracted)} characters.")
        return extracted if len(extracted) > 40 else "Could not decode text from PDF stream."

    def _extract_docx(self, file_bytes: bytes) -> str:
        """Extracts text from DOCX files using standard library zipfile and XML parser."""
        try:
            import zipfile
            import xml.etree.ElementTree as ET
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                xml_content = z.read("word/document.xml")
                tree = ET.fromstring(xml_content)
                texts = [node.text for node in tree.iter() if node.tag.endswith("t") and node.text]
                return "\n".join(texts)
        except Exception as e:
            logger.warning(f"DOCX extraction error: {e}")
            return self._extract_text_plain(file_bytes)

    def _extract_text_plain(self, file_bytes: bytes) -> str:
        """Decodes text files using common encodings."""
        for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
            try:
                return file_bytes.decode(enc)
            except Exception:
                continue
        return file_bytes.decode("utf-8", errors="ignore")

    def parse_resume(self, file_bytes: bytes, filename: str, persist: bool = True) -> Dict[str, Any]:
        """
        End-to-end resume pipeline:
        1. Extract text from uploaded document.
        2. Extract complete structured candidate schema via robust native section parser.
        3. Attempt LLM enhancement with token safety and automatic JSON repair.
        4. Save copy to data/resume.pdf for ATS applier bots (if persist=True).
        5. Persist to config/profile_resume.yaml and update active settings (if persist=True).
        """
        raw_text = self.extract_text(file_bytes, filename)
        logger.info(f"Resume text extracted ({len(raw_text)} chars). Parsing structured profile...")

        # Step 1: High-accuracy baseline extraction directly from document sections
        parsed_profile = self._heuristic_parse(raw_text)

        # Step 2: Query LLM for subtle synthesis or enhancement (with token caps and fallback)
        try:
            clean_text = re.sub(r'\n{3,}', '\n\n', raw_text).strip()
            prompt = RESUME_EXTRACTION_USER_TEMPLATE.format(resume_text=clean_text[:3800])
            llm_result = self.router.generate_json(
                system_prompt=RESUME_EXTRACTION_SYSTEM_PROMPT,
                user_prompt=prompt
            )
            if isinstance(llm_result, dict):
                # Safely merge any richer fields provided by the LLM
                pers = llm_result.get("personal_information")
                if isinstance(pers, dict):
                    for k, v in pers.items():
                        if v and str(v).strip() and str(v).strip().lower() not in ["string", "null", "none"]:
                            parsed_profile["personal_information"][k] = v

                if llm_result.get("summary") and len(str(llm_result["summary"])) > 20:
                    parsed_profile["summary"] = str(llm_result["summary"]).strip()

                if llm_result.get("experience") and isinstance(llm_result["experience"], list) and len(llm_result["experience"]) > 0:
                    parsed_profile["experience"] = llm_result["experience"]

                if llm_result.get("education") and isinstance(llm_result["education"], list) and len(llm_result["education"]) > 0:
                    parsed_profile["education"] = llm_result["education"]

                if llm_result.get("skills") and isinstance(llm_result["skills"], dict):
                    for sk_cat, sk_items in llm_result["skills"].items():
                        if isinstance(sk_items, list) and sk_items:
                            existing = set(parsed_profile["skills"].get(sk_cat, []))
                            existing.update([s for s in sk_items if s and str(s).strip() and str(s).strip() != "string"])
                            parsed_profile["skills"][sk_cat] = sorted(list(existing))
                logger.info("Successfully enhanced profile with LLM schema.")
        except Exception as e:
            logger.info(f"LLM augmentation skipped or fell back to robust baseline: {e}")

        if persist:
            # Save uploaded file to disk for automated application attachment
            self._persist_resume_attachment(file_bytes, filename)

            # Persist profile to disk
            self._save_profile_to_disk(parsed_profile)

        return parsed_profile

    def _persist_resume_attachment(self, file_bytes: bytes, filename: str):
        """Saves a permanent copy to data/ for universal ATS application attach."""
        try:
            ext = filename.lower().split(".")[-1] if "." in filename else "pdf"
            dest = DATA_DIR / f"resume.{ext}"
            with open(dest, "wb") as f:
                f.write(file_bytes)
            logger.info(f"Saved uploaded resume attachment to {dest}")
        except Exception as e:
            logger.warning(f"Could not persist resume attachment: {e}")

    def _save_profile_to_disk(self, profile: Dict[str, Any]):
        """Saves generated candidate schema to profile_resume.yaml and config.yaml."""
        try:
            yaml_path = CONFIG_DIR / "profile_resume.yaml"
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(profile, f, sort_keys=False, allow_unicode=True)

            settings.profile_yaml = profile

            # Update home country & city if detected
            info = profile.get("personal_information", {})
            country = info.get("country")
            city = info.get("city")
            if country or city:
                cfg_path = CONFIG_DIR / "config.yaml"
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f) or {}

                if "candidate_mobility" not in cfg:
                    cfg["candidate_mobility"] = {}
                if country:
                    cfg["candidate_mobility"]["home_country"] = country
                if city:
                    cfg["candidate_mobility"]["home_city"] = city

                with open(cfg_path, "w", encoding="utf-8") as f:
                    yaml.safe_dump(cfg, f, sort_keys=False, allow_unicode=True)

                settings.reload()

            logger.info("Successfully updated profile_resume.yaml from parsed resume.")
        except Exception as e:
            logger.error(f"Failed to persist parsed profile to disk: {e}")

    def _heuristic_parse(self, text: str) -> Dict[str, Any]:
        """Robust section-based resume parser that guarantees full schema extraction."""
        clean_text = re.sub(r"\\[a-zA-Z]+(?:\[[^\]]*\])?(?:\{[^\}]*\})*", " ", text) # Strip latex macros
        
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        first_line = lines[0] if lines else "Candidate"

        # 1. Contact & Identity
        raw_name = first_line.split("|")[0].strip()
        latex_bold = re.search(r"\\textbf\{([A-Za-z\s\.]+)\}", text)
        if latex_bold:
            raw_name = latex_bold.group(1).strip()
        
        for noise in ["Full Stack", "Full-Stack", "Software Engineer", "AI Engineer", "Developer", "Data Scientist", "Curriculum Vitae", "Resume"]:
            raw_name = re.sub(r"(?i)\b" + re.escape(noise) + r"\b", "", raw_name).strip()

        name_parts = raw_name.split()
        if len(name_parts) >= 3 and name_parts[0].upper().rstrip(".") in ["MD", "MOHAMMED", "MOHAMMAD", "DR", "MR"]:
            first_name = f"{name_parts[0]} {name_parts[1].capitalize()}"
            last_name = " ".join(p.capitalize() for p in name_parts[2:])
        elif len(name_parts) >= 2:
            first_name = name_parts[0].capitalize()
            last_name = " ".join(p.capitalize() for p in name_parts[1:])
        elif len(name_parts) == 1:
            first_name = name_parts[0].capitalize()
            last_name = ""
        else:
            first_name = "Candidate"
            last_name = "User"

        # Headline
        headline = "Full Stack AI and Automation Engineer"
        for line in lines[1:4]:
            if "@" not in line and "http" not in line and not re.search(r"\+?\d{10,}", line):
                if any(k in line.lower() for k in ["engineer", "developer", "lead", "architect", "scientist", "manager"]):
                    headline = line.split("|")[0].strip()
                    break

        # Contact details
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        phone_match = re.search(r"\+?880\s*\d{4}\s*\d{6}|\+?\d{1,4}[-.\s]?\d{3,4}[-.\s]?\d{3,5}", text)
        github_match = re.search(r"github\.com/([a-zA-Z0-9_-]+)", text, re.IGNORECASE)
        linkedin_match = re.search(r"linkedin\.com/in/([a-zA-Z0-9_-]+)", text, re.IGNORECASE)
        portfolio_match = re.search(r"([a-zA-Z0-9_-]+\.github\.io|[a-zA-Z0-9_-]+\.vercel\.app)", text, re.IGNORECASE)

        # City & Country
        city = "Dhaka"
        country = "Bangladesh"
        if "Dhaka" in text: city = "Dhaka"
        elif "Sylhet" in text: city = "Sylhet"
        elif "Chittagong" in text or "Chattogram" in text: city = "Chattogram"
        if "Bangladesh" in text: country = "Bangladesh"

        # Summary
        summary = "Full Stack AI Engineer with proven expertise in building modern software, LLMs, and multi-agent systems."
        sum_match = re.search(r"(?:PROFESSIONAL SUMMARY|SUMMARY|ABOUT ME)\s*\n+([\s\S]*?)(?=CORE SKILLS|SKILLS|WORK EXPERIENCE|EXPERIENCE|EDUCATION|$)", text, re.IGNORECASE)
        if sum_match:
            cand_summary = re.sub(r"\s+", " ", sum_match.group(1)).strip()
            if len(cand_summary) > 20:
                summary = cand_summary

        # Skills catalog
        tech_catalog = {
            "languages": ["Python", "JavaScript", "TypeScript", "PHP", "SQL", "Go", "C++", "Java", "Ruby", "C#"],
            "frameworks_and_backend": ["FastAPI", "Next.js", "React", "Flask", "Laravel", "Node.js", "REST API", "WebSockets", "Asyncio", "Microservices", "Tailwind CSS", "Redis", "JWT", "Stripe"],
            "ai_and_data": [
                "LLM", "LLM Integration", "RAG", "AI Agents", "Multi-Agent Systems", "LangChain", "LangGraph", "CrewAI",
                "OpenAI", "Gemini", "Ollama", "Hugging Face", "Vector Databases", "FAISS", "Pinecone", "pgvector", "Embeddings",
                "ElevenLabs", "Vapi AI", "Twilio", "OCR", "EasyOCR", "YOLO11", "OpenCV", "Computer Vision",
                "PyTorch", "TensorFlow", "Scikit-learn", "XGBoost", "LightGBM", "CNN", "Vision Transformers",
                "PostgreSQL", "MySQL", "MongoDB", "Supabase", "SQLAlchemy"
            ],
            "automation_and_devops": [
                "n8n", "Workflow Automation", "OpenClaw", "Headless Browser Automation", "Web Scraping", "API Integration",
                "Webhooks", "Email Automation", "Meta Ads Automation", "Meta Graph API",
                "Docker", "Docker Compose", "GitHub Actions", "CI/CD", "Nginx", "Linux", "VPS", "AWS EC2"
            ]
        }
        extracted_skills = {}
        for cat, skills in tech_catalog.items():
            extracted_skills[cat] = [s for s in skills if re.search(r"\b" + re.escape(s) + r"\b", text, re.IGNORECASE)]

        # Work Experience
        experience = []
        exp_section = re.search(r"(?:WORK EXPERIENCE|EXPERIENCE)\s*\n+([\s\S]*?)(?=PROJECTS|EDUCATION|PUBLICATIONS|SKILLS|$)", text, re.IGNORECASE)
        if exp_section:
            exp_text = exp_section.group(1)
            pattern = r"([A-Za-z\s\(\)]+?)\s+((?:Jan|Feb|Mar|Apr|May|Jun|Jul|July|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\s*[–-]\s*(?:Present|\w+\s+\d{4}))\s*\n+([^\n•]+?)(?:\s*\((.*?)\))?\s*\n+([\s\S]*?)(?=(?:[A-Za-z\s\(\)]+?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|July|Aug|Sep|Oct|Nov|Dec)\s+\d{4})|$)"
            matches = re.findall(pattern, exp_text)
            for m in matches:
                role = m[0].strip()
                dates = m[1].strip()
                comp_loc = m[2].strip()
                loc_extra = m[3].strip() if m[3] else ""
                bullets = [re.sub(r"^[•\*\-\s]+", "", b).strip() for b in m[4].split("\n") if b.strip() and any(c.isalnum() for c in b)]
                
                parts = [p.strip() for p in comp_loc.split(",") if p.strip()]
                company = parts[0] if parts else "Professional Experience"
                location = ", ".join(parts[1:]) + (f" ({loc_extra})" if loc_extra else "")
                
                experience.append({
                    "title": role,
                    "company": company,
                    "start_date": dates.split("–")[0].strip() if "–" in dates else dates.split("-")[0].strip(),
                    "end_date": dates.split("–")[-1].strip() if "–" in dates else dates.split("-")[-1].strip(),
                    "location": location or "Dhaka, Bangladesh",
                    "highlights": bullets[:4]
                })

        # Fallback for experience if regex above didn't match
        if not experience:
            exp_roles = re.findall(r"(?:Software Engineer|AI Engineer|Full Stack Developer|Developer|Intern|Lead Developer|Consultant)", text, re.IGNORECASE)
            seen_roles = set()
            for role in exp_roles:
                rt = role.title()
                if rt not in seen_roles:
                    seen_roles.add(rt)
                    experience.append({
                        "title": rt,
                        "company": "Professional Experience",
                        "start_date": "Recent",
                        "end_date": "Present",
                        "location": f"{city}, {country}",
                        "highlights": ["Designed and implemented scalable applications and AI workflows."]
                    })
                    if len(experience) >= 3:
                        break

        # Education
        education = []
        edu_section = re.search(r"EDUCATION\s*\n+([\s\S]*?)(?=PUBLICATIONS|PROJECTS|CORE SKILLS|EXPERIENCE|$)", text, re.IGNORECASE)
        if edu_section:
            edu_text = edu_section.group(1)
            for block in re.split(r"\n(?=[M|B]\.Sc|Master|Bachelor)", edu_text):
                blines = [l.strip() for l in block.split("\n") if l.strip()]
                if blines:
                    deg_line = blines[0]
                    inst_line = blines[1] if len(blines) > 1 else ""
                    yr_match = re.search(r"(\d{4}\s*[–-]\s*(?:Present|\d{4}))|\b(20\d{2})\b", deg_line)
                    yr = yr_match.group(0) if yr_match else ""
                    deg_clean = re.sub(r"(\d{4}\s*[–-]\s*(?:Present|\d{4}))|\b(20\d{2})\b", "", deg_line).strip()
                    education.append({
                        "degree": deg_clean or "Bachelor's Degree",
                        "institution": inst_line.split(",")[0].strip() if inst_line else "University",
                        "graduation_year": yr
                    })

        # Fallback education if regex didn't catch
        if not education:
            edu_degree = ""
            for d in ["B.Sc in Computer Science", "B.Sc in Software Engineering", "B.Sc in Electrical Engineering", "Bachelor of Science", "B.Sc", "M.Sc", "Bachelor", "Master"]:
                if re.search(r"\b" + re.escape(d) + r"\b", text, re.IGNORECASE):
                    edu_degree = d
                    break
            edu_inst = ""
            for inst in ["Jahangirnagar University", "Metropolitan University", "Dhaka University", "BUET", "BRAC University", "North South University"]:
                if re.search(r"\b" + re.escape(inst) + r"\b", text, re.IGNORECASE):
                    edu_inst = inst
                    break
            if edu_degree or edu_inst:
                education.append({
                    "degree": edu_degree or "Bachelor of Science",
                    "institution": edu_inst or "University",
                    "graduation_year": "2024"
                })

        return {
            "personal_information": {
                "first_name": first_name,
                "last_name": last_name,
                "headline": headline,
                "email": email_match.group(0) if email_match else "",
                "phone_country_code": "+880",
                "phone_number": phone_match.group(0) if phone_match else "",
                "city": city,
                "country": country,
                "github_url": f"https://{github_match.group(0)}" if github_match else "",
                "linkedin_url": f"https://{linkedin_match.group(0)}" if linkedin_match else "",
                "portfolio_url": f"https://{portfolio_match.group(0)}" if portfolio_match else ""
            },
            "summary": summary,
            "skills": extracted_skills,
            "experience": experience,
            "education": education
        }


resume_parser = ResumeParser()
