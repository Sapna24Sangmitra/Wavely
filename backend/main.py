from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import os
import google.generativeai as genai
from gtts import gTTS
import uuid
import re

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Create FastAPI app
app = FastAPI()

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Gemini model
model = genai.GenerativeModel(model_name="gemini-2.0-flash")

# Root route
@app.get("/")
def root():
    return {"message": "Wavelly API is running"}

# Text cleaning function to remove stage directions
def clean_text_for_tts(text):
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)   # remove bold (**)
    text = re.sub(r"\[(.*?)\]", "", text)          # remove [brackets]
    text = re.sub(r"\((.*?)\)", "", text)          # remove (stage directions)
    text = re.sub(r"\s{2,}", " ", text)            # extra spaces
    return text.strip()

# Fake call endpoint
@app.post("/fake-call/audio")
async def fake_call_audio(request: Request):
    data = await request.json()
    context = data.get("context", "Act like a protective dad calling his daughter.")

    try:
        # Generate content using Gemini
        response = model.generate_content(context)
        print("🧠 Gemini raw response:", response)

        # Extract message
        message = None
        try:
            if response.text:
                message = response.text
        except:
            pass

        if not message:
            try:
                message = response.candidates[0].content.parts[0].text
            except:
                message = "Hi honey, just checking in. Are you okay?"

        # Clean the message
        cleaned_message = clean_text_for_tts(message)
        print("🧹 Cleaned message:", cleaned_message)

        # Convert to speech
        tts = gTTS(text=cleaned_message)
        filename = f"fake_call_{uuid.uuid4().hex}.mp3"
        filepath = os.path.join("audio", filename)

        os.makedirs("audio", exist_ok=True)
        tts.save(filepath)

        print("✅ Audio generated at:", filepath)
        return FileResponse(filepath, media_type="audio/mpeg", filename=filename)

    except Exception as e:
        print("❌ Gemini or TTS error:", str(e))
        return {"error": str(e)}
    
@app.post("/fake-call")
async def fake_call(request: Request):
    data = await request.json()
    context = data.get("context", "Act like a protective dad calling his daughter.")
    try:
        response = model.generate_content(context)
        message = getattr(response, "text", None)
        if not message and hasattr(response, "candidates"):
            message = response.candidates[0].content.parts[0].text
        return {"message": message or "Hi sweetheart, just checking in."}
    except Exception as e:
        return {"error": str(e)}

