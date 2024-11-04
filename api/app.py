from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os

# Import your necessary modules
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.prompts import PromptTemplate
from langchain_together import Together
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferWindowMemory

app = FastAPI()

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
    "ipc_vector_db",
    embeddings,
    allow_dangerous_serialization=True  # Be cautious with this in production
)
db_retriever = db.as_retriever(search_type="similarity", search_kwargs={"k": 4})

# Define your prompt template

prompt_template = """<s>[INST]This is a chat template and As a legal chat bot specializing in Indian Penal Code queries, your primary objective is to provide accurate and concise information based on the user's questions. Do not generate your own questions and answers. You will adhere strictly to the instructions provided, offering relevant context from the knowledge base while avoiding unnecessary details. Your responses will be brief, to the point, and in compliance with the established format. If a question falls outside the given context, you will refrain from utilizing the chat history and instead rely on your own knowledge base to generate an appropriate response. You will prioritize the user's query and refrain from posing additional questions. The aim is to deliver professional, precise, and contextually relevant information pertaining to the Indian Penal Code.
CONTEXT: {context}
CHAT HISTORY: {chat_history}
QUESTION: {question}
ANSWER:
</s>[INST]
"""

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
        # Update the memory with chat history
        qa.memory.chat_memory.messages = request.chat_history

        # Generate response
        result = qa({"question": request.question})

        # Update chat history
        new_chat_history = request.chat_history + [
            {"role": "user", "content": request.question},
            {"role": "assistant", "content": result["answer"]}
        ]

        return ChatResponse(answer=result["answer"], chat_history=new_chat_history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
