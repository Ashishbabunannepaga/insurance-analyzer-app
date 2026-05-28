import json
import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List

# --- SCHEMA ---

class Recommendation(BaseModel):
    winning_policy_name: str = Field(description="Name of the best policy overall")
    winning_company: str = Field(description="Company offering the winning policy")
    why_it_won: List[str] = Field(description="3 to 4 bullet points explaining exactly why this policy is mathematically and functionally the best choice (coverage vs cost).")
    flaws_of_others: List[str] = Field(description="2 to 3 bullet points explaining why the runners-up were not chosen (e.g., higher premium, missing coverage).")

# --- FUNCTION ---

def generate_best_pick(extracted_data_list: list) -> dict:
    """Evaluates multiple quotes and returns the Best Pick logic."""
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    
    data_string = json.dumps(extracted_data_list, indent=2)

    prompt = f"""
    You are an expert Insurance Financial Advisor. 
    Analyze the following extracted insurance quotes carefully:
    {data_string}
    
    Evaluate them based on:
    1. Premium cost vs. Total coverage/Sum Insured
    2. Waiting periods (lower is better)
    3. Room rent limits (no limit is better)
    4. Special features (like No Claim Bonus, Restore benefits)
    
    Determine the single best policy and return your recommendation in the exact JSON format requested.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=Recommendation,
                temperature=0.2,
            ),
        )
        return json.loads(response.text)
    except Exception as e:
        return {"error": str(e)}