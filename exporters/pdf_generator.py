import os
import io
import re
import base64
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt

def extract_numeric_premium(premium_str: str) -> float:
    if not premium_str or premium_str == "Not Mentioned":
        return 0.0
    clean_str = str(premium_str).replace(',', '')
    numbers = re.findall(r"[-+]?\d*\.\d+|\d+", clean_str)
    if numbers:
        return float(numbers[0])
    return 0.0

def generate_charts(chart_data: list, winner_company: str) -> dict:
    names = [d["company"] for d in chart_data]
    premiums = [d["premium"] for d in chart_data]
    
    colors = ['#10B981' if name == winner_company else '#6366F1' for name in names]
    
    # 1. Compact Bar Chart
    fig1, ax1 = plt.subplots(figsize=(5.5, 2.5)) # Made smaller for minimalist layout
    bars = ax1.barh(names, premiums, color=colors, height=0.5)
    ax1.set_xlabel('Annual Premium (₹)', fontsize=9, color='#64748B')
    ax1.tick_params(axis='both', colors='#475569', labelsize=8)
    
    for spine in ax1.spines.values():
        spine.set_visible(False)
    ax1.xaxis.grid(True, linestyle='--', alpha=0.3, color='#94A3B8')
    plt.tight_layout()
    
    buf1 = io.BytesIO()
    plt.savefig(buf1, format='png', dpi=200, transparent=True)
    buf1.seek(0)
    bar_chart_b64 = base64.b64encode(buf1.read()).decode('utf-8')
    plt.close(fig1)

    # 2. Compact Donut Chart
    fig2, ax2 = plt.subplots(figsize=(3.5, 3.5)) # Made smaller
    wedges, texts, autotexts = ax2.pie(
        premiums, labels=names, autopct='%1.0f%%', startangle=90, 
        colors=colors, wedgeprops=dict(width=0.35, edgecolor='white', linewidth=1.5)
    )
    plt.setp(autotexts, size=8, weight="bold", color="white")
    plt.setp(texts, size=8, color="#475569")
    plt.tight_layout()
    
    buf2 = io.BytesIO()
    plt.savefig(buf2, format='png', dpi=200, transparent=True)
    buf2.seek(0)
    pie_chart_b64 = base64.b64encode(buf2.read()).decode('utf-8')
    plt.close(fig2)

    return {"bar": bar_chart_b64, "pie": pie_chart_b64}

def generate_pdf_bytes(extracted_data_list: list, recommendation: dict) -> bytes:
    template_dir = os.path.join(os.getcwd(), 'assets', 'templates')
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template('report_template.html')
    
    chart_data = []
    winner_company = recommendation.get('winning_company', '')
    
    for doc in extracted_data_list:
        chart_data.append({
            "company": doc.get('insurance_company', 'Unknown'),
            "premium": extract_numeric_premium(doc.get('total_premium_1_year', '0'))
        })
    
    chart_images = generate_charts(chart_data, winner_company)

    html_out = template.render(
        data=extracted_data_list, 
        rec=recommendation,
        bar_chart=chart_images["bar"],
        pie_chart=chart_images["pie"],
        date=datetime.now().strftime("%B %d, %Y")
    )
    
    result_file = io.BytesIO()
    pisa_status = pisa.CreatePDF(src=html_out, dest=result_file)
    
    if pisa_status.err:
        raise Exception("Error generating PDF")
        
    return result_file.getvalue()