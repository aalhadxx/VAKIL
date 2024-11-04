from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import logging

# Import your necessary modules
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.prompts import PromptTemplate
from langchain_together import Together
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferWindowMemory

app = FastAPI()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Load environment variables
TOGETHER_AI_API_KEY = os.environ.get('4569143f0e2c15d6680c634d84e17c9f61dfa9417deb8698a7247a1037b17c2a')
if not TOGETHER_AI_API_KEY:
    raise EnvironmentError("TOGETHER_AI_API_KEY not found in environment variables.")

# Initialize components
embeddings = HuggingFaceEmbeddings(
    model_name="nomic-ai/nomic-embed-text-v1",
    model_kwargs={"trust_remote_code": True}
)

# Load your FAISS index
db = FAISS.load_local(
    "../ipc_vector_db",  # Adjust path if necessary
    embeddings,
    allow_dangerous_serialization=True
)
db_retriever = db.as_retriever(search_type="similarity", search_kwargs={"k": 4})

# Define your prompt template
prompt_template = """<s>[INST]...Your prompt here...</s>[INST]"""

prompt = PromptTemplate(
    template=prompt_template,
    input_variables=['context', 'question', 'chat_history']
)

# Initialize the LLM
llm = Together(
    model="mistralai/Mistral-7B-Instruct-v0.2",
    temperature=0.5,
    max_tokens=1024,
    together_api_key=TOGETHER_AI_API_KEY
)

# Initialize the conversation chain
qa = ConversationalRetrievalChain.from_llm(
    llm=llm,
    memory=ConversationBufferWindowMemory(k=2, memory_key="chat_history", return_messages=True),
    retriever=db_retriever,
    combine_docs_chain_kwargs={'prompt': prompt}
)

# Define the request and response models
class ChatRequest(BaseModel):
    question: str
    chat_history: list = []

class ChatResponse(BaseModel):
    answer: str
    chat_history: list

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        logger.info(f"Received question: {request.question}")
        # Update the memory with chat history
        qa.memory.chat_memory.messages = request.chat_history

        # Generate response
        result = qa({"question": request.question})
        logger.info(f"Generated answer: {result['answer']}")

        # Update chat history
        new_chat_history = request.chat_history + [
            {"role": "user", "content": request.question},
            {"role": "assistant", "content": result["answer"]}
        ]

        return ChatResponse(answer=result["answer"], chat_history=new_chat_history)
    except Exception as e:
        logger.exception("Error in chat_endpoint")
        raise HTTPException(status_code=500, detail=str(e))
