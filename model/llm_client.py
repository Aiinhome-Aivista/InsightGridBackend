import requests
import json 
import google.generativeai as genai
import os
from dotenv import load_dotenv
# ---------- Load environment variables ----------
load_dotenv()  # loads variables from .env file

# ---------- LLM Configuration ----------
ACTIVE_LLM = os.getenv("ACTIVE_LLM", "mistral_cloud")              # "gemini", "mistral_cloud", "mistral_local"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-1")            # for Gemini
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
MISTRAL_API_URL = os.getenv("MISTRAL_API_URL", "http://localhost:11434/api/generate")  # local Ollama
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-small-latest")  # cloud or local model


def call_llm(prompt: str) -> str:
    try:
        #  Gemini Cloud
        if ACTIVE_LLM == "gemini":
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel(MODEL_NAME)
            response = model.generate_content(prompt)
            return response.text.strip()

        #  Mistral Cloud API
        elif ACTIVE_LLM == "mistral_cloud":
            url = "https://api.mistral.ai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "mistral-small",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            }
            res = requests.post(url, json=payload, headers=headers, timeout=60)
            res.raise_for_status()
            data = res.json()
            return data["choices"][0]["message"]["content"].strip()

        #  Local Ollama (via localhost)
        elif ACTIVE_LLM == "mistral_local":
            payload = {"model": "mistral:latest", "prompt": prompt}
            res = requests.post(MISTRAL_API_URL, json=payload, stream=True)

            # Ollama streams multiple JSON lines (one per token)
            full_response = ""
            for line in res.iter_lines():
                if line:
                    try:
                        chunk = line.decode("utf-8")
                        data = json.loads(chunk)
                        if "response" in data:
                            full_response += data["response"]
                    except Exception:
                        continue  # Skip malformed lines

            return full_response.strip() if full_response else "[Ollama Error] No response received."

        # Invalid LLM setting
        else:
            return "[LLM Error] Invalid ACTIVE_LLM configuration."

    except Exception as e:
        return f"[LLM Error] {str(e)}"