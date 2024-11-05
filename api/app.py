from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import logging
import traceback
import re
import random
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
    r'\b(hi|hey|hello|howdy)\b',
    r'good\s*(morning|afternoon|evening)',
    r'greetings'
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
    return random.choice(GREETING_RESPONSES)

def detect_input_type(text: str) -> str:
    """Detect the type of user input."""
    text = text.lower().strip()
    
    # Check for simple greetings first - using more lenient matching
    if any(re.search(pattern, text) for pattern in GREETING_PATTERNS):
        return "greeting"
    
    # Then check other patterns
    if any(re.search(pattern, text) for pattern in GRATITUDE_PATTERNS):
        return "gratitude"
    if any(re.search(pattern, text) for pattern in GOODBYE_PATTERNS):
        return "goodbye"
    if any(re.search(pattern, text) for pattern in CAPABILITY_PATTERNS):
        return "capability"
    
    # Only consider it a clarification needed if very short and not a greeting
    if len(text.split()) < 2 and not any(re.search(pattern, text) for pattern in GREETING_PATTERNS):
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
        # Get and validate input
        data = await request.json()
        user_input = data.get("user_input", "").strip()
        if not user_input:
            return {
                "response": "I couldn't understand that. Could you please try again?",
                "suggestions": ["Tell me about IPC", "Show common sections", "Explain legal terms"],
                "typing_duration": 500
            }

        logger.info(f"Received user input: {user_input}")

        # Detect input type and log it
        input_type = detect_input_type(user_input)
        logger.info(f"Detected input type: {input_type}")
        
        # Initialize response parameters
        response = ""
        suggestions = []
        typing_duration = 1000
        
        try:
            if input_type == "greeting":
                # Handle greetings with personalized responses
                response = random.choice([
                    "Hello! I'm here to assist you with IPC-related questions. What would you like to know?",
                    "Hi there! I can help you understand Indian Penal Code matters. What's your question?",
                    "Greetings! Feel free to ask me about any IPC sections or legal terms."
                ])
                suggestions = [
                    "What is Section 302 IPC?",
                    "Explain criminal conspiracy",
                    "Show punishment for theft"
                ]
                typing_duration = 500

            elif input_type == "clarification_needed":
                # Handle short or unclear inputs
                response = "Could you please provide more details? I can help you with:"
                response += "\n• Specific IPC sections and their interpretations"
                response += "\n• Legal terms and definitions"
                response += "\n• Criminal offenses and their punishments"
                
                suggestions = [
                    "Show all IPC sections",
                    "Common criminal offenses",
                    "Basic legal terms"
                ]
                typing_duration = 800

            elif input_type == "gratitude":
                response = random.choice(GRATITUDE_RESPONSES)
                suggestions = [
                    "Tell me about another section",
                    "Explain more legal terms",
                    "Show related provisions"
                ]
                typing_duration = 500

            elif input_type == "goodbye":
                response = random.choice(GOODBYE_RESPONSES)
                suggestions = [
                    "Ask another question",
                    "Learn about IPC",
                    "View legal guidelines"
                ]
                typing_duration = 500

            elif input_type == "capability":
                response = random.choice(CAPABILITY_RESPONSES)
                suggestions = [
                    "Show an example section",
                    "List common offenses",
                    "Explain IPC structure"
                ]
                typing_duration = 800

            else:
                # Process legal queries using QA chain
                logger.info("Processing legal query...")
                result = qa_chain({"question": user_input})
                response = result.get("answer", "")
                
                # Validate and clean response
                if not response or len(response.strip()) < 10:
                    response = "I apologize, but I couldn't generate a proper response. Could you please rephrase your question?"
                
                # Generate contextual suggestions based on query
                if "section" in user_input.lower():
                    suggestions = [
                        "What's the punishment?",
                        "Show related sections",
                        "Explain in simple terms"
                    ]
                elif "punishment" in user_input.lower():
                    suggestions = [
                        "Show maximum penalty",
                        "Related offenses",
                        "Recent amendments"
                    ]
                else:
                    suggestions = [
                        "Tell me more",
                        "Show legal provisions",
                        "Practical examples"
                    ]
                
                # Adjust typing duration based on response length
                typing_duration = min(len(response.split()) * 100, 3000)

        except Exception as query_error:
            logger.error(f"Error processing query: {query_error}")
            return {
                "response": "I encountered an issue while processing your query. Could you please rephrase it?",
                "suggestions": ["Try different wording", "Ask simpler question", "Break down query"],
                "typing_duration": 500
            }

        # Log the response and return
        logger.info(f"Response type: {input_type}, Response length: {len(response)}")
        return {
            "response": response,
            "suggestions": suggestions,
            "typing_duration": typing_duration
        }

    except Exception as e:
        # Handle general errors
        logger.error(f"Unexpected error in chat endpoint: {e}")
        logger.error(traceback.format_exc())
        return {
            "response": "I apologize, but I'm having trouble processing requests right now. Please try again in a moment.",
            "suggestions": ["Refresh and try again", "Ask about IPC", "Show legal terms"],
            "typing_duration": 500
        }