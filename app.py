import streamlit as st
import google.generativeai as genai
import time
import re
import os
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini API
GOOGLE_API_KEY = os.environ["GEMINI_API_KEY"] or st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GOOGLE_API_KEY)

def load_text_data():
    """Load content from text file"""
    try:
        with open("patient_data.txt", "r") as file:
            return file.read()
    except FileNotFoundError:
        st.error("Patient data file not found!")
        return None

def get_gemini_response(question, context):
    """Get response from Gemini model"""
    model = genai.GenerativeModel('gemini-1.5-flash-8b')
    prompt = f"""
    Patient Reports: \n\n{context}
    
    Question: {question}
    
    Please answer the question based on the patient reports provided above. Do not include the source URL in your response.
    """
    response = model.generate_content(prompt)
    return response.text

def extract_report_url(text):
    """Extract report URL from the response"""
    url_match = re.search(r'https://gateway\.lighthouse\.storage/ipfs/[^\s]+', text)
    return url_match.group(0) if url_match else None

def main():
    st.title("MedBase AI")
    
    # Load the text data
    text_data = load_text_data()
    print(text_data)
    
    if text_data is None:
        return
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and "report_url" in message:
                st.pill(f"📄 Report URL: {message['report_url']}")
    
    # Chat input
    if question := st.chat_input("Ask a question about the patient"):
        # Display user message
        with st.chat_message("user"):
            st.markdown(question)
        st.session_state.messages.append({"role": "user", "content": question})
        
        # Display assistant response with progress
        with st.chat_message("assistant"):
            with st.status("Processing...", expanded=True) as status:
                st.write("Retrieving patient information from IPFS...")
                time.sleep(1)  # Simulate processing time
                
                st.write("Analyzing your question...")
                response = get_gemini_response(question, text_data)
                time.sleep(0.5)  # Simulate processing time
                
                st.write("Generating response...")
                time.sleep(0.5)  # Simulate processing time
                
                status.update(label="Complete!", state="complete", expanded=False)
            
            st.markdown(response)
            report_url = extract_report_url(text_data)
            if report_url:
                st.pills(label="Report URL", options=[report_url])
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": response,
                    "report_url": report_url
                })
            else:
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": response
                })

if __name__ == "__main__":
    main() 