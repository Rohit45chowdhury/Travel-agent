import os
import google.generativeai as genai
from dotenv import load_dotenv


load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

model = genai.GenerativeModel("gemini-3-flash-preview")

def gemini(prompt):
    try:
        response = model.generate_content(prompt)

        
        if hasattr(response, "text"):
            return response.text.strip()
        else:
            return str(response).strip()

    except Exception as e:
        return f"Error: {str(e)}"


# stream
def gemini_stream(prompt):
    response = gemini(prompt) 

    words = response.split()

    for word in words:
        yield word + " "