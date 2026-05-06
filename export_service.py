import pandas as pd
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import os

def generate_excel_report(transactions):
    df = pd.DataFrame(transactions)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Transaksi')
    output.seek(0)
    return output

def generate_pdf_report(transactions, chat_id):
    df = pd.DataFrame(transactions)
    if df.empty:
        return None
    
    # Create Pie Chart
    summary = df.groupby('type')['amount'].sum()
    plt.figure(figsize=(6, 4))
    summary.plot(kind='pie', autopct='%1.1f%%', startangle=140, colors=['#ff9999','#66b3ff'])
    plt.title('Proporsi Pemasukan vs Pengeluaran')
    
    chart_path = f"chart_{chat_id}.png"
    plt.savefig(chart_path)
    plt.close()
    
    # Create PDF
    output = BytesIO()
    p = canvas.Canvas(output, pagesize=letter)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 750, f"Laporan Keuangan Toyamas Finance")
    p.setFont("Helvetica", 12)
    p.drawString(100, 730, f"User ID: {chat_id}")
    
    # Add Chart
    p.drawImage(chart_path, 100, 450, width=400, height=250)
    
    # List Transactions (Simple list)
    p.drawString(100, 420, "Ringkasan Transaksi Terakhir:")
    y = 400
    for idx, row in df.head(10).iterrows():
        p.drawString(100, y, f"{row['timestamp']} - {row['type']} - {row['amount']} - {row['description']}")
        y -= 20
    
    p.showPage()
    p.save()
    output.seek(0)
    
    # Cleanup chart image
    if os.path.exists(chart_path):
        os.remove(chart_path)
        
    return output
