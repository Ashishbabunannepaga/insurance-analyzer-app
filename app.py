import streamlit as st
import tempfile
import os
import json
from datetime import datetime  # <-- Added this for timestamping

# Import custom modules
from core.gemini_client import identify_document, extract_policy_data
from core.scorer import generate_best_pick
from components.comparison_table import render_comparison_matrix
from exporters.excel_generator import generate_excel_bytes
from exporters.pdf_generator import generate_pdf_bytes
from database.db_manager import add_brochure, get_active_brochure, init_db, get_all_active_brochures

# Configure page settings
st.set_page_config(page_title="AI Policy Analyzer", page_icon="🛡️", layout="wide")

# Ensure the database table exists on startup
init_db()

def main():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["📊 Quote Analyzer", "📁 Agentic Brochure Vault"])
    
    if page == "📁 Agentic Brochure Vault":
        render_brochure_vault()
    else:
        render_analyzer()

def render_brochure_vault():
    st.title("📁 Agentic Brochure Vault")
    st.markdown("Upload generic insurance brochures here. **The AI will automatically detect the Company and Plan Name**, and file it directly into the Supabase Postgres Database.")
    
    # --- UPLOAD SECTION ---
    uploaded_file = st.file_uploader("Upload Master Brochure (PDF)", type="pdf")
    
    if uploaded_file:
        if st.button("🤖 Auto-Detect & Save to Vault", type="primary"):
            with st.spinner("🧠 AI Agent is scanning the brochure to identify it..."):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded_file.read())
                    tmp_path = tmp.name
                try:
                    identity = identify_document(tmp_path)
                    company = identity.get("insurance_company", "Unknown Company").strip()
                    plan = identity.get("plan_name", "Unknown Plan").strip()
                    
                    add_brochure(company, plan, tmp_path)
                    
                    st.success(f"✅ **Success!** AI automatically identified and vaulted into Supabase:")
                    st.info(f"🏢 **Company:** {company} \n\n📄 **Plan:** {plan}")
                except Exception as e:
                    st.error(f"Failed to process brochure: {e}")
                finally:
                    os.remove(tmp_path)

    # --- VAULT INVENTORY TABLE ---
    st.write("---")
    st.write("### 🗄️ Currently Vaulted Master Brochures")
    
    active_brochures = get_all_active_brochures()
    
    if active_brochures:
        st.dataframe(active_brochures, use_container_width=True)
    else:
        st.info("No brochures are currently saved in the vault. Upload one above!")

def render_analyzer():
    st.title("🛡️ AI Insurance Policy Analyzer")
    st.markdown("Upload Quote PDFs. The AI will seamlessly fetch the Master Brochure from Supabase to generate a deep-dive analysis.")

    uploaded_files = st.file_uploader("Upload Client Quotes (PDF)", type="pdf", accept_multiple_files=True)

    # Initialize Session State
    if "extracted_data" not in st.session_state:
        st.session_state.extracted_data = []
    if "recommendation" not in st.session_state:
        st.session_state.recommendation = None

    if uploaded_files:
        if st.button("🚀 Analyze Policies & Generate Best Pick", type="primary"):
            st.session_state.extracted_data = [] 
            st.session_state.recommendation = None
            
            progress_bar = st.progress(0)
            status_text = st.empty()

            for i, file in enumerate(uploaded_files):
                status_text.text(f"🔍 Analyzing {file.name}...")
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(file.read())
                    tmp_path = tmp_file.name
                
                brochure_path = None
                try:
                    # 1. Fast Pass: Identify the Quote
                    identity = identify_document(tmp_path)
                    company = identity.get("insurance_company", "")
                    plan = identity.get("plan_name", "")
                    
                    # 2. DB Lookup: Fetch Brochure from Supabase (if exists)
                    brochure_path = get_active_brochure(company, plan)
                    
                    if brochure_path:
                        st.toast(f"✅ Found matching brochure in Supabase for: {company} {plan}")
                    else:
                        st.toast(f"⚠️ No brochure found for {company} {plan}. Extracting from Quote only.", icon="⚠️")

                    # 3. Deep Extract & Merge Logic
                    json_result = extract_policy_data(tmp_path, brochure_path)
                    json_result = json_result.strip().removeprefix("```json").removesuffix("```").strip()
                    
                    # Append extracted dict to session state
                    st.session_state.extracted_data.append(json.loads(json_result))
                    
                except Exception as e:
                    st.error(f"Failed to process {file.name}: {e}")
                finally:
                    # Cleanup local temporary files
                    os.remove(tmp_path)
                    if brochure_path and os.path.exists(brochure_path):
                        os.remove(brochure_path)
                
                # Update progress bar
                progress_bar.progress((i + 1) / len(uploaded_files))
            
            # Generate Final Recommendation
            status_text.text("🏆 AI is evaluating policies to find the Best Pick...")
            st.session_state.recommendation = generate_best_pick(st.session_state.extracted_data)
            status_text.success("✅ Analysis Complete!")

    # --- RENDER RESULTS ---
    if st.session_state.extracted_data:
        st.write("---")
        
        # 1. Recommendation Banner
        if st.session_state.recommendation and "error" not in st.session_state.recommendation:
            rec = st.session_state.recommendation
            st.success(f"### 🏆 AI Recommended Pick: {rec.get('winning_company')} - {rec.get('winning_policy_name')}")
            col1, col2 = st.columns(2)
            with col1:
                st.write("#### ✅ Why it won:")
                for point in rec.get("why_it_won", []):
                    st.markdown(f"- {point}")
            with col2:
                st.write("#### ❌ Flaws of others:")
                for point in rec.get("flaws_of_others", []):
                    st.markdown(f"- {point}")
            st.write("---")

        # 2. Interactive Matrix
        render_comparison_matrix(st.session_state.extracted_data)
        
        # 3. Export Buttons
        st.write("---")
        st.write("### 📥 Download Reports")
        col_ex1, col_ex2 = st.columns(2)
        
        # <-- TIMESTAMP LOGIC ADDED HERE -->
        # Get current date and time formatted like: 2026-05-28_13-08-45
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        excel_filename = f"CapitUp_Comparison_{timestamp}.xlsx"
        pdf_filename = f"CapitUp_Analysis_Report_{timestamp}.pdf"
        
        with col_ex1:
            # We now pass both extracted_data AND recommendation into the Excel generator!
            excel_bytes = generate_excel_bytes(st.session_state.extracted_data, st.session_state.recommendation)
            
            st.download_button(
                label="📊 Download Excel Matrix (.xlsx)", 
                data=excel_bytes, 
                file_name=excel_filename, 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                use_container_width=True
            )
            
        with col_ex2:
            if st.session_state.recommendation:
                try:
                    pdf_bytes = generate_pdf_bytes(st.session_state.extracted_data, st.session_state.recommendation)
                    st.download_button(
                        label="📄 Download Full PDF Report", 
                        data=pdf_bytes, 
                        file_name=pdf_filename,  # Dynamic filename applied
                        mime="application/pdf", 
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"Could not generate PDF: {e}")

if __name__ == "__main__":
    main()