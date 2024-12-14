# ai_features.py

import logging
from langchain_community.vectorstores import FAISS
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferWindowMemory
from langchain_together import Together
from langchain.prompts import PromptTemplate

# Configure logging
logger = logging.getLogger("ChatbotAI")
logger.setLevel(logging.INFO)

# Together AI API key
TOGETHER_AI_API_KEY = '4569143f0e2c15d6680c634d84e17c9f61dfa9417deb8698a7247a1037b17c2a'

# Load the existing FAISS index
try:
    db = FAISS.load_local("path/to/your/vector_db")
    db_retriever = db.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 4}
    )
    logger.info("FAISS index loaded successfully.")
except Exception as e:
    logger.error(f"Error loading FAISS index: {e}")
    raise

# Initialize Together AI LLM
llm = Together(
    model="mistralai/Mistral-7B-Instruct-v0.2",
    temperature=0.5,
    max_tokens=200,
    together_api_key=TOGETHER_AI_API_KEY
)

# Prompt template
prompt = PromptTemplate(
    template="""<s>[INST] You are a legal expert chatbot specializing in queries related to the Indian Penal Code.
    Respond directly to the question based on the specific section or context provided.
    Keep responses short, relevant, and factually accurate.

    Context: {context}
    Question: {question}

    Response: [/INST]""",
    input_variables=["context", "question"]
)

# Initialize the QA chain
qa_chain = ConversationalRetrievalChain.from_llm(
    llm=llm,
    retriever=db_retriever,
    memory=ConversationBufferWindowMemory(k=2, memory_key="chat_history", return_messages=True),
    combine_docs_chain_kwargs={"prompt": prompt}
)

def process_legal_query(user_input):
    """Process the user's legal query using the QA chain."""
    try:
        result = qa_chain({"question": user_input})
        response = result.get("answer", "")
        if not response or len(response.strip()) < 10:
            response = "I apologize, but I couldn't generate a proper response. Could you please rephrase your question?"
        return response
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        return "I encountered an issue while processing your query. Please try again."
