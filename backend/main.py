from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with specific domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Wavelly API is running"}

@app.post("/fake-call")
async def fake_call(request: Request):
    data = await request.json()
    context = data.get("context", "")
    
    # 🔁 Dummy fake call response based on context
    if "dad" in context.lower():
        response = "Hi sweetheart, just checking in. Are you okay? Stay close to the main road, alright?"
    elif "boyfriend" in context.lower():
        response = "Hey babe, are you heading home? Just wanted to hear your voice. Be safe, okay?"
    else:
        response = "Hi, just checking in. Let me know if you need anything. I'm here."

    return { "message": response }
