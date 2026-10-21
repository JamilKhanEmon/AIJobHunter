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

    def parse_resume(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        End-to-end resume pipeline:
        1. Extract text from uploaded document.
        2. Prompt Groq Cloud LLM to extract structured JSON profile.
        3. Save copy to data/resume.pdf for ATS applier bots.
        4. Persist to config/profile_resume.yaml and update active settings.
        """
        raw_text = self.extract_text(file_bytes, filename)
        logger.info(f"Resume text extracted ({len(raw_text)} chars). Querying AI for structured schema...")

        prompt = RESUME_EXTRACTION_USER_TEMPLATE.format(resume_text=raw_text[:12000])

        parsed_profile: Optional[Dict[str, Any]] = None
        try:
            parsed_profile = self.router.generate_json(
                system_prompt=RESUME_EXTRACTION_SYSTEM_PROMPT,
                user_prompt=prompt
            )
        except Exception as e:
            logger.warning(f"LLM resume parsing encountered error: {e}. Falling back to heuristic extractor...")

        if not parsed_profile or not isinstance(parsed_profile, dict) or "personal_information" not in parsed_profile:
            parsed_profile = self._heuristic_parse(raw_text)

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
        """Intelligent regex fallback if LLM inference is completely unavailable."""
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        phone_match = re.search(r"(\+?\d{1,4}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,5}", text)
        linkedin_match = re.search(r"linkedin\.com/in/[\w\.-]+", text, re.IGNORECASE)
        github_match = re.search(r"github\.com/[\w\.-]+", text, re.IGNORECASE)

        # Attempt to find name in top 3 lines
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        first_name = "Candidate"
        last_name = "User"
        if lines:
            top_line = lines[0]
            parts = top_line.split()
            if 1 <= len(parts) <= 3 and all(p.isalpha() for p in parts):
                first_name = parts[0]
                last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

        # Extract common tech keywords
        known_keywords = [
            "Python", "JavaScript", "TypeScript", "Go", "Java", "C++", "SQL",
            "FastAPI", "Django", "React", "Next.js", "Node.js", "Express",
            "Docker", "Kubernetes", "AWS", "GCP", "PostgreSQL", "MongoDB", "Redis",
            "LangChain", "LlamaIndex", "LLMs", "Machine Learning", "PyTorch"
        ]
        found_skills = [kw for kw in known_keywords if re.search(r"\b" + re.escape(kw) + r"\b", text, re.IGNORECASE)]

        return {
            "personal_information": {
                "first_name": first_name,
                "last_name": last_name,
                "headline": "Software Engineer & AI Developer",
                "email": email_match.group(0) if email_match else "candidate@example.com",
                "phone_country_code": "+880",
                "phone_number": phone_match.group(0) if phone_match else "",
                "city": "Dhaka",
                "country": "Bangladesh",
                "github_url": f"https://{github_match.group(0)}" if github_match else "",
                "linkedin_url": f"https://{linkedin_match.group(0)}" if linkedin_match else "",
                "portfolio_url": ""
            },
            "summary": "Experienced software professional with demonstrated technical proficiency in modern systems architecture, distributed backends, and AI pipelines.",
            "skills": {
                "languages": [s for s in found_skills if s in ["Python", "JavaScript", "TypeScript", "Go", "Java", "C++", "SQL"]],
                "frameworks_and_backend": [s for s in found_skills if s in ["FastAPI", "Django", "React", "Next.js", "Node.js", "Express"]],
                "ai_and_data": [s for s in found_skills if s in ["PostgreSQL", "MongoDB", "Redis", "LangChain", "LlamaIndex", "LLMs", "PyTorch"]],
                "devops_and_tools": [s for s in found_skills if s in ["Docker", "Kubernetes", "AWS", "GCP"]]
            },
            "experience": [],
            "education": []
        }


resume_parser = ResumeParser()
