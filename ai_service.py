import os
import base64
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv
import pandas as pd
from scipy import stats

load_dotenv()

XAI_API_KEY = os.getenv("XAI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EXCHANGERATE_API_KEY = os.getenv("EXCHANGERATE_API_KEY")

# xAI client
xai_client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")
# OpenAI client for Whisper
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def encode_image_bytes(image_bytes):
    return base64.b64encode(image_bytes).decode('utf-8')

# --- Advanced Receipt Analysis ---
def analyze_receipt_advanced(image_bytes):
    base64_image = encode_image_bytes(image_bytes)
    prompt = """
    Menganalisis struk belanja ini secara detail.
    Ekstrak:
    1. Nama Toko
    2. Daftar Item (Nama, Qty, Harga Satuan, Total Harga per Item)
    3. PPN/Tax
    4. Diskon
    5. Total Akhir
    6. Kategori per Item (Makanan, Transportasi, Keperluan Pribadi, dll)
    
    Berikan output dalam format JSON yang valid:
    {
        "toko": "...",
        "items": [{"name": "...", "qty": 1, "price": 1000, "total": 1000, "category": "..."}],
        "tax": 0,
        "discount": 0,
        "total": 0
    }
    """
    try:
        response = xai_client.chat.completions.create(
            model="grok-2-vision-1212",
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error Advanced OCR: {e}")
        return None

# --- Voice Transcription (Whisper) ---
def transcribe_voice(voice_file_path):
    if not OPENAI_API_KEY:
        return "API Key OpenAI tidak ditemukan."
    try:
        with open(voice_file_path, "rb") as audio_file:
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
        return transcript.text
    except Exception as e:
        print(f"Error Whisper: {e}")
        return None

# --- Bank Statement Parsing ---
def parse_bank_statement(text_content):
    prompt = f"""
    Ekstrak transaksi dari teks mutasi bank berikut menjadi daftar JSON.
    Teks: {text_content}
    Format: [{"date": "...", "description": "...", "amount": 0, "type": "masuk/keluar"}]
    """
    try:
        response = xai_client.chat.completions.create(
            model="grok-2-1212",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content).get("transactions", [])
    except Exception as e:
        print(f"Error Parsing Statement: {e}")
        return []

# --- Anomaly Detection ---
def detect_anomaly(amount, category, history_df):
    if history_df.empty:
        return False, 0
    
    cat_history = history_df[history_df['description'].str.contains(category, case=False, na=False)]
    if len(cat_history) < 3:
        return False, 0
    
    z_score = (amount - cat_history['amount'].mean()) / cat_history['amount'].std()
    is_anomaly = abs(z_score) > 3
    return is_anomaly, z_score

# --- Currency Conversion ---
def get_exchange_rate(from_curr, to_curr='IDR'):
    url = f"https://api.exchangerate.host/convert?from={from_curr}&to={to_curr}"
    try:
        response = requests.get(url)
        data = response.json()
        return data.get('result', 1.0)
    except:
        return 1.0

# --- Sentiment & Pattern Analysis ---
def get_spending_feedback(description, amount, sentiment_score):
    prompt = f"Analisis pengeluaran: '{description}' sebesar Rp{amount}. User merasa {sentiment_score}/5 (1: terpaksa, 5: impulsif). Berikan saran singkat dan bijak."
    try:
        response = xai_client.chat.completions.create(
            model="grok-2-1212",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except:
        return "Tetap pantau pengeluaran Anda!"
