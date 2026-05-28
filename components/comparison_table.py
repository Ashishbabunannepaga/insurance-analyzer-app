import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

def render_comparison_matrix(extracted_data_list: list):
    """
    Takes a list of policy dictionaries (parsed from Gemini JSON)
    and builds an interactive side-by-side comparison matrix.
    """
    if not extracted_data_list:
        st.warning("No data available to compare.")
        return

    # 1. Convert the list of dictionaries into a Pandas DataFrame
    df = pd.DataFrame(extracted_data_list)

    # 2. Transpose the DataFrame (Flip it!)
    # We want Attributes as Rows, and Policies as Columns.
    df_transposed = df.T
    
    # 3. Clean up the headers and index
    # Use the 'insurance_company' or 'plan_name' as column headers
    column_headers = [f"{doc.get('insurance_company', 'Quote')} - {doc.get('plan_name', str(i+1))}" for i, doc in enumerate(extracted_data_list)]
    df_transposed.columns = column_headers
    
    # Reset index so the attributes become a normal column named "Policy Feature"
    df_transposed = df_transposed.reset_index()
    df_transposed.rename(columns={'index': 'Policy Feature'}, inplace=True)
    
    # Make feature names readable (e.g., 'total_premium_1_year' -> 'Total Premium 1 Year')
    df_transposed['Policy Feature'] = df_transposed['Policy Feature'].apply(lambda x: str(x).replace('_', ' ').title())

    # 4. Build the Interactive Ag-Grid
    gb = GridOptionsBuilder.from_dataframe(df_transposed)
    
    # Pin the "Policy Feature" column to the left so it stays visible when scrolling sideways
    gb.configure_column("Policy Feature", pinned="left", cellStyle={'fontWeight': 'bold', 'backgroundColor': '#f0f2f6'})
    
    # Auto-size columns and enable text wrapping for long lists (like add-ons)
    gb.configure_default_column(wrapText=True, autoHeight=True, resizable=True)
    
    grid_options = gb.build()

    st.write("### 🧮 Side-by-Side Comparison Matrix")
    
    # Render the grid in Streamlit
    AgGrid(
        df_transposed,
        gridOptions=grid_options,
        data_return_mode=DataReturnMode.AS_INPUT,
        update_mode=GridUpdateMode.NO_UPDATE,
        fit_columns_on_grid_load=True,
        theme='streamlit', # options: 'streamlit', 'alpine', 'balham', 'material'
        height=500
    )