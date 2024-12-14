# main.py

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import logging
from .ai_features import process_legal_query

app = FastAPI()
logger = logging.getLogger("ChatbotApp")

@app.get("/", response_class=HTMLResponse)
async def get_html():
    try:
        with open("index.html", "r") as file:
            return HTMLResponse(content=file.read())
    except Exception as e:
        logger.error(f"Error serving HTML file: {e}")
        return HTMLResponse(content="Error loading chat interface.", status_code=500)

@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        user_input = data.get("user_input", "").strip()
        
        if not user_input:
            return {
                "response": "I couldn't understand that. Please try again.",
                "typing_duration": 500
            }

        response = process_legal_query(user_input)
        typing_duration = min(len(response.split()) * 100, 3000)

        return {
            "response": response,
            "typing_duration": typing_duration
        }
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return {
            "response": "I'm having trouble processing requests right now. Please try again.",
            "typing_duration": 500
        }
