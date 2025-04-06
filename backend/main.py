from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import google.generativeai as genai

# Load .env file
load_dotenv()
genai_api_key = os.getenv("GEMINI_API_KEY")

# Configure Gemini
genai.configure(api_key=genai_api_key)
model = genai.GenerativeModel("gemini-pro")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/fake-call")
async def fake_call(request: Request):
    data = await request.json()
    context = data.get("context", "Act like a protective dad calling his daughter who may be in danger.")
    
    try:
        response = model.generate_content(context)
        return { "message": response.text }
    except Exception as e:
        return { "error": str(e) }