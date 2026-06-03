import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, DataReturnMode

def render_comparison_matrix(extracted_data_list: list):
    if not extracted_data_list:
        st.warning("No data available to compare.")
        return

    df = pd.DataFrame(extracted_data_list)
    df_transposed = df.T
    
    # FIX: Guarantee unique column names by prefixing "Quote 1:", "Quote 2:", etc.
    column_headers = []
    for i, doc in enumerate(extracted_data_list):
        company = doc.get('insurance_company', 'Unknown')
        plan = doc.get('plan_name', 'Plan')
        column_headers.append(f"Quote {i+1}: {company} - {plan}")
        
    df_transposed.columns = column_headers
    
    df_transposed = df_transposed.reset_index()
    df_transposed.rename(columns={'index': 'Policy Feature'}, inplace=True)
    df_transposed['Policy Feature'] = df_transposed['Policy Feature'].apply(lambda x: str(x).replace('_', ' ').title())

    gb = GridOptionsBuilder.from_dataframe(df_transposed)
    gb.configure_column("Policy Feature", pinned="left", cellStyle={'fontWeight': 'bold', 'backgroundColor': '#f0f2f6'})
    gb.configure_default_column(wrapText=True, autoHeight=True, resizable=True)
    grid_options = gb.build()

    st.write("### 🧮 Side-by-Side Comparison Matrix")
    
    AgGrid(
        df_transposed,
        gridOptions=grid_options,
        data_return_mode=DataReturnMode.AS_INPUT,
        update_mode=GridUpdateMode.NO_UPDATE,
        fit_columns_on_grid_load=True,
        theme='streamlit',
        height=500
    )
