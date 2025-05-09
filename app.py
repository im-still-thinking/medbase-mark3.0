import ast
import re
import time

import firebase_admin
import google.generativeai as genai
import requests
import streamlit as st
from dotenv import load_dotenv
from firebase_admin import credentials, firestore

load_dotenv()

# Initialize Firebase Admin SDK (only once)
if not firebase_admin._apps:
    cred = credentials.Certificate(ast.literal_eval(st.secrets["FIREBASE_CREDENTIALS"]))
    firebase_admin.initialize_app(cred, name='medbase')
else:
    # Get the existing app
    firebase_admin.get_app(name='medbase')

# Firestore client
app = firebase_admin.get_app(name='medbase')
db = firestore.client(app=app)

# Configure Gemini API
GOOGLE_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GOOGLE_API_KEY)

# def load_text_data():
#     """Load content from text file"""
#     try:
#         with open("patient_data.txt", "r") as file:
#             return file.read()
#     except FileNotFoundError:
#         st.error("Patient data file not found!")
#         return None

def fetch_ipfs_text(cid):
    """
    Fetch text data from IPFS using the given CID
    
    Args:
        cid (str): Content Identifier for the IPFS resource
    
    Returns:
        str or None: Text content from IPFS, or None if retrieval fails
    """
    try:
        # Construct the full IPFS gateway URL
        ipfs_url = f"https://gateway.lighthouse.storage/ipfs/{cid}"
        
        # Fetch the content
        response = requests.get(ipfs_url, timeout=10)
        
        # Check if request was successful
        if response.status_code == 200:
            return response.text
        else:
            st.error(f"Failed to retrieve IPFS content. Status code: {response.status_code}")
            return None
    
    except requests.RequestException as e:
        st.error(f"Error fetching IPFS content: {e}")
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


def check_phone_number(phone_number):
    """
    Check if a document with the phone number exists and retrieve the last hash
    
    Args:
        phone_number (str): Phone number to search for as document ID
    
    Returns:
        str or None: Hash from the last object in cid array, or None if not found
    """
    try:
        # Reference the document with phone number as ID
        doc_ref = db.collection('users').document(phone_number)
        doc = doc_ref.get()
        
        # Check if document exists
        if doc.exists:
            user_data = doc.to_dict()
            
            # Check if 'cid' array exists and is not empty
            if 'cid' in user_data and user_data['cid']:
                # Return the hash from the last object in the cid array
                return user_data['cid'][-1].get('hash')
        
        return None
    
    except Exception as e:
        st.error(f"Error checking phone number: {e}")
        return None
    
def main():
    st.title("MedBase AI")

    # Phone Number Verification Step
    if 'phone_verified' not in st.session_state:
        st.session_state.phone_verified = False
    
    if not st.session_state.phone_verified:
        st.subheader("Phone Number Verification")
        phone_number = st.text_input("Please enter your phone number")
        
        if st.button("Verify"):
            # Check phone number document in Firestore
            user_hash = check_phone_number(phone_number)
            
            if user_hash:
                st.session_state.phone_verified = True
                st.session_state.user_hash = user_hash
                st.success(f"Phone number verified! Retrieved hash: {user_hash}")
            else:
                st.warning("No user found with this phone number.")
        
        return
    
    # Load the text data
    text_data = fetch_ipfs_text(st.session_state.user_hash)
    
    if text_data is None:
        st.error("Failed to retrieve patient data.")
        return
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and "report_url" in message:
                # st.markdown(f"📄 [Report URL]({report_url})")
                st.markdown(f"📄 Report URL: {message['report_url']}")
    
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
                # st.markdown(f"📄 [Report URL]({report_url})")
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