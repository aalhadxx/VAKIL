from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import logging
import traceback
import re
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.prompts import PromptTemplate
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferWindowMemory
from langchain_together import Together

# Initialize the app and logging
app = FastAPI()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("ChatbotApp")

# Load the embeddings model
embeddings = HuggingFaceEmbeddings(model_name="nomic-ai/nomic-embed-text-v1", model_kwargs={"trust_remote_code": True})

# Load FAISS index with LangChain
try:
    db = FAISS.load_local("../ipc_vector_db", embeddings, allow_dangerous_deserialization=True)
    db_retriever = db.as_retriever(search_type="similarity", search_kwargs={"k": 4})
    logger.info("FAISS index loaded successfully.")
except Exception as e:
    logger.error(f"Error loading FAISS index: {e}")
    raise

# Together AI API configuration
TOGETHER_AI_API_KEY = '4569143f0e2c15d6680c634d84e17c9f61dfa9417deb8698a7247a1037b17c2a'
llm = Together(
    model="mistralai/Mistral-7B-Instruct-v0.2",
    temperature=0.7,
    max_tokens=350,
    together_api_key=TOGETHER_AI_API_KEY
)

# Add these new patterns after your existing GREETING_PATTERNS
GRATITUDE_PATTERNS = [
    r'thank(?:s| you)',
    r'appreciate it',
    r'grateful',
    r'helpful',
    r'thanks'
]

GOODBYE_PATTERNS = [
    r'bye',
    r'goodbye',
    r'see you',
    r'talk to you later',
    r'exit'
]

CAPABILITY_PATTERNS = [
    r'what can you do',
    r'help me with',
    r'capabilities',
    r'features',
    r'how do you work'
]

# Greetings and casual conversation patterns
GREETING_PATTERNS = [
    r'^hi$', r'^hello$', r'^hey$', r'^hi there$', r'^hello there$',
    r'^greetings$', r'^good morning$', r'^good afternoon$', r'^good evening$',
    r'^how are you$', r'^how are you\?$'
]

# Greeting responses
GREETING_RESPONSES = [
    "Hello! I'm here to help with your Indian Penal Code related questions. What would you like to know?",
    "Hi! How can I assist you with your IPC-related questions today?",
    "Hello! I'm ready to help you understand the Indian Penal Code better. What's your question?"
]

GRATITUDE_RESPONSES = [
    "You're welcome! Feel free to ask any other questions about the IPC.",
    "Happy to help! Let me know if you need other legal information.",
    "Glad I could assist! Don't hesitate to ask more questions about Indian law."
]

GOODBYE_RESPONSES = [
    "Goodbye! Feel free to return if you have more questions about the IPC.",
    "Take care! I'm here 24/7 if you need more legal assistance.",
]

CAPABILITY_RESPONSES = [
    "I can help you understand various sections of the Indian Penal Code, explain legal terms, and provide information about specific offenses and their punishments.",
    "I'm specialized in the Indian Penal Code. I can explain different sections, help you understand legal concepts, and provide information about criminal laws in India.",
]


# Main conversation prompt template
main_prompt_template = """<s>[INST] You are a legal chatbot specializing in Indian Penal Code queries.
Provide a clear and direct response focused only on the current question.
Keep responses concise and relevant to IPC matters.

Context: {context}
Question: {question}

Response: [/INST]"""

# Initialize prompt template
prompt = PromptTemplate(template=main_prompt_template, input_variables=["context", "question"])

# Initialize conversational retrieval chain with LangChain
qa_chain = ConversationalRetrievalChain.from_llm(
    llm=llm,
    memory=ConversationBufferWindowMemory(k=2, memory_key="chat_history", return_messages=True),
    retriever=db_retriever,
    combine_docs_chain_kwargs={"prompt": prompt}
)

def is_greeting(text):
    """Check if the input is a greeting."""
    text = text.lower().strip()
    return any(re.match(pattern, text) for pattern in GREETING_PATTERNS)

def get_greeting_response():
    """Get a random greeting response."""
    import random
    return random.choice(GREETING_RESPONSES)

def detect_input_type(text: str) -> str:
    """Detect the type of user input."""
    text = text.lower()
    
    if any(re.search(pattern, text) for pattern in GRATITUDE_PATTERNS):
        return "gratitude"
    if any(re.search(pattern, text) for pattern in GOODBYE_PATTERNS):
        return "goodbye"
    if any(re.search(pattern, text) for pattern in CAPABILITY_PATTERNS):
        return "capability"
    if len(text.split()) < 3:
        return "clarification_needed"
    return "legal_query"

def get_response_by_type(input_type: str) -> str:
    """Get appropriate response based on input type."""
    responses = {
        "gratitude": GRATITUDE_RESPONSES,
        "goodbye": GOODBYE_RESPONSES,
        "capability": CAPABILITY_RESPONSES
    }
    return random.choice(responses.get(input_type, [""]))

@app.get("/", response_class=HTMLResponse)
async def get_html():
    try:
        with open("index.html", "r") as file:
            html_content = file.read()
        logger.info("Served HTML interface.")
        return HTMLResponse(content=html_content)
    except Exception as e:
        logger.error(f"Error serving HTML file: {e}")
        return HTMLResponse(content="Error loading chat interface.", status_code=500)

@app.get("/chat.js")
async def get_js():
    try:
        with open("chat.js", "r") as file:
            js_content = file.read()
        return HTMLResponse(content=js_content, media_type="application/javascript") 
    except Exception as e:
        logger.error(f"Error serving JavaScript file: {e}")
        return {"response": "Cpuldnt fetch chat.js  Please try again later."}


@app.post("/chat")
async def chat(request: Request):
    try:
        data = await request.json()
        user_input = data.get("user_input", "").strip()
        logger.info(f"Received user input: {user_input}")

        # First check if it's a greeting (using your existing is_greeting function)
        if is_greeting(user_input):
            response = get_greeting_response()
        else:
            # Check for other types of inputs
            input_type = detect_input_type(user_input)
            
            if input_type in ["gratitude", "goodbye", "capability"]:
                response = get_response_by_type(input_type)
            else:
                # Use the QA chain for legal queries
                result = qa_chain({"question": user_input})
                response = result.get("answer", "I'm sorry, I couldn't generate a response.")
        
        logger.info(f"Responded to user with: {response}")
        return {"response": response}

    except Exception as e:
        logger.error(f"Error in /chat endpoint: {e}")
        logger.debug(traceback.format_exc())
        return {"response": "An error occurred. Please try again later."}