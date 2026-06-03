import pandas as pd
import io
from xlsxwriter.utility import xl_rowcol_to_cell

def generate_excel_bytes(extracted_data_list: list, recommendation: dict = None) -> bytes:
    cleaned_data = []
    for doc in extracted_data_list:
        clean_doc = {}
        for k, v in doc.items():
            if isinstance(v, list):
                clean_doc[k] = "• " + "\n• ".join(v) if v else "None"
            else:
                clean_doc[k] = v
        cleaned_data.append(clean_doc)

    df = pd.DataFrame(cleaned_data)
    df_transposed = df.T
    
    # FIX: Guarantee unique column names
    column_headers = []
    for i, doc in enumerate(cleaned_data):
        company = doc.get('insurance_company', 'Unknown')
        plan = doc.get('plan_name', 'Plan')
        column_headers.append(f"Quote {i+1}: {company} - {plan}")
        
    df_transposed.columns = column_headers
    
    df_transposed = df_transposed.reset_index()
    df_transposed.rename(columns={'index': 'Policy Feature'}, inplace=True)
    df_transposed['Policy Feature'] = df_transposed['Policy Feature'].apply(lambda x: str(x).replace('_', ' ').title())

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_transposed.to_excel(writer, index=False, sheet_name='Comparison Matrix')
        
        workbook = writer.book
        worksheet = writer.sheets['Comparison Matrix']

        header_format = workbook.add_format({'bold': True, 'bg_color': '#0F172A', 'font_color': 'white', 'text_wrap': True, 'valign': 'vcenter', 'border': 1})
        winner_header_format = workbook.add_format({'bold': True, 'bg_color': '#10B981', 'font_color': 'white', 'text_wrap': True, 'valign': 'vcenter', 'border': 1})
        
        feature_col_format = workbook.add_format({'bold': True, 'bg_color': '#F1F5F9', 'valign': 'top', 'text_wrap': True, 'border': 1})
        cell_format = workbook.add_format({'text_wrap': True, 'valign': 'top', 'border': 1})
        
        red_format = workbook.add_format({'bg_color': '#FEE2E2', 'font_color': '#991B1B'})
        green_format = workbook.add_format({'bg_color': '#DCFCE7', 'font_color': '#166534'})

        winner_company = recommendation.get("winning_company", "") if recommendation else ""
        
        for col_num, value in enumerate(df_transposed.columns.values):
            if col_num == 0:
                worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 25, feature_col_format)
            else:
                if winner_company and winner_company.lower() in value.lower():
                    worksheet.write(0, col_num, "🏆 " + value, winner_header_format)
                else:
                    worksheet.write(0, col_num, value, header_format)
                worksheet.set_column(col_num, col_num, 45, cell_format)

        max_row = len(df_transposed)
        max_col = len(df_transposed.columns) - 1
        
        if max_row > 0 and max_col > 0:
            start_cell = 'B2'
            end_cell = xl_rowcol_to_cell(max_row, max_col)
            data_range = f'{start_cell}:{end_cell}'

            red_keywords = ['Not Mentioned', 'Not Covered', 'Not Applicable']
            for kw in red_keywords:
                worksheet.conditional_format(data_range, {'type': 'text', 'criteria': 'containing', 'value': kw, 'format': red_format})
            
            green_keywords = ['Unlimited', 'Covered up to', 'Single Pvt', 'Single Private', 'Day 1', 'No Claim Bonus']
            for kw in green_keywords:
                worksheet.conditional_format(data_range, {'type': 'text', 'criteria': 'containing', 'value': kw, 'format': green_format})

    return output.getvalue()
