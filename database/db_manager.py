import tempfile
import psycopg2
import streamlit as st

# Pulling credentials natively from Streamlit Secrets
DB_HOST = st.secrets["DB_HOST"]
DB_PORT = st.secrets["DB_PORT"]
DB_USER = st.secrets["DB_USER"]
DB_PASS = st.secrets["DB_PASS"]
DB_NAME = st.secrets["DB_NAME"]

def get_db_connection():
    """Establishes a direct connection to your Supabase database."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        dbname=DB_NAME
    )

def init_db():
    """Automatically creates the table in Supabase if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS brochures (
            id SERIAL PRIMARY KEY,
            company_name TEXT NOT NULL,
            plan_name TEXT NOT NULL,
            file_data BYTEA NOT NULL,
            version INTEGER DEFAULT 1,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
        );
    ''')
    conn.commit()
    cursor.close()
    conn.close()

def add_brochure(company_name: str, plan_name: str, local_file_path: str):
    """Saves the PDF as binary data directly into the Postgres database."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Deactivate older versions of this brochure
    cursor.execute('''
        UPDATE brochures SET is_active = false 
        WHERE company_name = %s AND plan_name = %s
    ''', (company_name, plan_name))
    
    # 2. Get the next version number
    cursor.execute('''
        SELECT MAX(version) FROM brochures 
        WHERE company_name = %s AND plan_name = %s
    ''', (company_name, plan_name))
    result = cursor.fetchone()
    version = (result[0] or 0) + 1
    
    # 3. Read the PDF file into binary format
    with open(local_file_path, "rb") as f:
        pdf_binary = f.read()
        
    # 4. Insert the new active record
    cursor.execute('''
        INSERT INTO brochures (company_name, plan_name, file_data, version, is_active)
        VALUES (%s, %s, %s, %s, true)
    ''', (company_name, plan_name, psycopg2.Binary(pdf_binary), version))
    
    conn.commit()
    cursor.close()
    conn.close()

def get_active_brochure(company_name: str, plan_name: str) -> str:
    """Fetches the active PDF from Postgres and saves it to a temp file for Gemini to read."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT file_data FROM brochures 
        WHERE is_active = true 
        AND company_name ILIKE %s 
        AND plan_name ILIKE %s
    ''', (f"%{company_name}%", f"%{plan_name}%"))
    
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not result:
        return None
        
    # Reconstruct the PDF from binary data
    pdf_binary = result[0]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.write(pdf_binary)
    tmp.close()
    
    return tmp.name

def get_all_active_brochures() -> list:
    """Fetches all active brochures from the database to display in the UI."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT company_name, plan_name, version, created_at 
        FROM brochures 
        WHERE is_active = true
        ORDER BY company_name ASC
    ''')
    
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Format the data for Streamlit's dataframe
    result = []
    for row in rows:
        # Format the date safely
        date_val = row[3]
        formatted_date = date_val.strftime("%Y-%m-%d %H:%M") if hasattr(date_val, 'strftime') else str(date_val)
        
        result.append({
            "Insurance Company": row[0],
            "Plan Name": row[1],
            "Version": f"v{row[2]}",
            "Date Vaulted": formatted_date
        })
    return result