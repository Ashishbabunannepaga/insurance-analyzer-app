import json
import os
import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List

# --- SCHEMAS ---

class QuoteIdentity(BaseModel):
    insurance_company: str = Field(description="Name of the insurance company")
    plan_name: str = Field(description="Name of the specific insurance plan")

class PolicyQuote(BaseModel):
    insurance_company: str = Field(description="Name of the insurance company")
    plan_name: str = Field(description="Name of the specific insurance plan")
    sum_insured: str = Field(description="Base sum insured amount")
    total_premium_1_year: str = Field(description="Total premium for a 1-year tenure")
    covered_members: str = Field(description="List of covered members and ages")
    room_rent_limit: str = Field(description="Room rent capping (e.g., Single Pvt Room, No Limit)")
    co_payment: str = Field(description="Co-payment percentage if applicable")
    aggregate_deductible: str = Field(description="Deductible amount, if any")
    pre_post_hospitalization: str = Field(description="Days covered before and after hospitalization")
    day_care_treatments: str = Field(description="Coverage for day care")
    domiciliary_hospitalization: str = Field(description="Coverage for treatment at home")
    ayush_treatment: str = Field(description="Coverage for Ayurveda, Unani, Siddha, Homeopathy")
    maternity_cover: str = Field(description="Maternity coverage details and limits")
    waiting_period_ped: str = Field(description="Waiting period for Pre-Existing Diseases (PED)")
    waiting_period_specific_illness: str = Field(description="Waiting period for specific illnesses")
    initial_waiting_period: str = Field(description="Initial waiting period for general claims")
    key_addons_riders: List[str] = Field(description="Selected optional riders/add-ons")
    special_features: List[str] = Field(description="Built-in unique features")
    key_exclusions: List[str] = Field(description="Any specific exclusions mentioned")

# --- FUNCTIONS ---

def identify_document(pdf_file_path: str) -> dict:
    """Fast AI pass to automatically figure out the Company and Plan Name."""
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    
    with open(pdf_file_path, "rb") as f:
        doc = types.Part.from_bytes(data=f.read(), mime_type='application/pdf')
    
    response = client.models.generate_content(
        model='gemini-2.5-pro', 
        contents=[doc, "Analyze this document. Identify the Insurance Company Name and the Plan Name. If it's a general company brochure, set plan_name to 'Master Brochure'."],
        config=types.GenerateContentConfig(
            response_mime_type="application/json", 
            response_schema=QuoteIdentity, 
            temperature=0.0
        )
    )
    return json.loads(response.text)

def extract_policy_data(quote_path: str, brochure_path: str = None) -> str:
    """Extracts data. If brochure_path is provided, merges data from BOTH PDFs."""
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    
    with open(quote_path, "rb") as f:
        quote_doc = types.Part.from_bytes(data=f.read(), mime_type='application/pdf')
    
    contents = ["DOCUMENT 1 (THE SPECIFIC QUOTE):", quote_doc]
    
    # If a brochure was found in the database, attach it for deep context
    if brochure_path and os.path.exists(brochure_path):
        with open(brochure_path, "rb") as f:
            brochure_doc = types.Part.from_bytes(data=f.read(), mime_type='application/pdf')
        contents.extend(["\nDOCUMENT 2 (THE MASTER BROCHURE):", brochure_doc])
        
    contents.append("""
    You are an elite Insurance Actuary. 
    If provided both a Quote and a Brochure:
    1. Extract Specifics (Premium, Members, Sum Insured, Chosen Riders) strictly from Document 1 (Quote).
    2. Extract Coverages (Room rent, Waiting periods, Limits) from Document 2 (Brochure).
    Pay extremely close attention to Checkboxes (☑, [x], [✓]) or 'Yes/No' columns in the Quote document to determine if optional covers (like Maternity or Consumables) were selected.
    If a variable is genuinely not in the documents, output 'Not Mentioned'.
    """)

    response = client.models.generate_content(
        model='gemini-2.5-pro',
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json", 
            response_schema=PolicyQuote, 
            temperature=0.0
        )
    )
    return response.text