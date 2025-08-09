from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import requests
import base64
from fpdf import FPDF
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# --- Configuration ---
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

if not STABILITY_API_KEY:
    print("WARNING: STABILITY_API_KEY not found. 'Create NFT with AI' will not work.")
if not PEXELS_API_KEY:
    print("WARNING: PEXELS_API_KEY not found. Dashboard image generation will not work.")

CONTRACTS_DIR = "contracts"
TRANSACTIONS_DIR = "transactions"
TRANSACTION_LOG_FILE = "transactions.log"
os.makedirs(CONTRACTS_DIR, exist_ok=True)
os.makedirs(TRANSACTIONS_DIR, exist_ok=True)


# --- API Endpoints ---
@app.route('/api/generate-ai-image', methods=['POST'])
def generate_ai_image():
    if not STABILITY_API_KEY:
        return jsonify({"error": "AI service is not configured on the server."}), 500
    data = request.get_json(); prompt = data.get('prompt')
    if not prompt: return jsonify({"error": "Prompt is required"}), 400
    try:
        api_host = 'https://api.stability.ai'; engine_id = "stable-diffusion-v1-6"
        response = requests.post(
            f"{api_host}/v1/generation/{engine_id}/text-to-image",
            headers={"Content-Type": "application/json", "Accept": "application/json", "Authorization": f"Bearer {STABILITY_API_KEY}"},
            json={"text_prompts": [{"text": prompt}], "cfg_scale": 7, "height": 512, "width": 512, "samples": 1, "steps": 30}
        )
        response.raise_for_status(); response_data = response.json()
        image_data_url = f"data:image/png;base64,{response_data['artifacts'][0]['base64']}"
        return jsonify({"imageDataUrl": image_data_url})
    except Exception as e:
        print(f"AI Generation Error: {e}")
        return jsonify({"error": f"Failed to generate AI image: {e}"}), 500

@app.route('/api/generate-dashboard-image', methods=['POST'])
def generate_dashboard_image():
    if not PEXELS_API_KEY:
        return jsonify({"error": "Image generation service is not configured."}), 500
    data = request.get_json(); prompt = data.get('prompt')
    if not prompt: return jsonify({"error": "A prompt is required."}), 400
    try:
        headers = {"Authorization": PEXELS_API_KEY}
        url = f"https://api.pexels.com/v1/search?query={prompt}&per_page=1"
        response = requests.get(url, headers=headers); response.raise_for_status()
        pexels_data = response.json()
        if not pexels_data.get("photos"): return jsonify({"error": "No images found for that prompt."}), 404
        image_url = pexels_data["photos"][0]["src"]["medium"]
        return jsonify({"imageUrl": image_url})
    except Exception as e:
        print(f"Pexels API Error: {e}")
        return jsonify({"error": f"Failed to fetch image from Pexels."}), 500


class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'NovaMint Document', 0, 1, 'C')
        self.ln(10)
    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 8); self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

@app.route('/api/save-contract', methods=['POST'])
def save_contract():
    data = request.get_json(); filename = data.get('filename', 'contract.sol'); code = data.get('code', '')
    if not code: return jsonify({"error": "Contract code is required"}), 400
    pdf_filename = filename.replace('.sol', '.pdf'); safe_filename = "".join([c for c in pdf_filename if c.isalpha() or c.isdigit() or c in ('.','_')]).rstrip()
    filepath = os.path.join(CONTRACTS_DIR, safe_filename)
    try:
        pdf = PDF(); pdf.add_page(); pdf.set_font("Courier", size=10); pdf.multi_cell(0, 5, txt=code)
        pdf.output(filepath)
        return jsonify({"message": f"Contract saved as {safe_filename} in the backend."})
    except Exception as e:
        print(f"PDF Generation Error: {e}")
        return jsonify({"error": "Failed to save contract as PDF."}), 500

@app.route('/api/record-transaction', methods=['POST'])
def record_transaction():
    data = request.get_json()
    nft_name = data.get('nftName', 'Unknown NFT')
    price = data.get('price', 0)
    buyer_info = data.get('buyerInfo', 'Unknown Buyer')
    seller_info = data.get('sellerInfo', 'Unknown Seller')
    purchase_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_entry = f"Date: {purchase_date}, NFT: {nft_name}, Price: {price} ETH, Buyer: {buyer_info}, Seller: {seller_info}\\n"
    with open(TRANSACTION_LOG_FILE, "a") as f:
        f.write(log_entry)

    receipt_content = (
        f"--- NovaMint Transaction Receipt ---\\n\\n"
        f"Item: {nft_name}\\n"
        f"Price: {price} ETH\\n"
        f"Seller: {seller_info}\\n"
        f"Buyer: {buyer_info}\\n"
        f"Date: {purchase_date}\\n\\n"
        f"This document certifies the simulated purchase of the above NFT."
    )
    safe_filename = f"receipt_{nft_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    filepath = os.path.join(TRANSACTIONS_DIR, safe_filename)
    try:
        pdf = PDF(orientation='P', unit='mm', format='A4'); pdf.add_page()
        pdf.set_font("Arial", size=12); pdf.multi_cell(0, 10, txt=receipt_content)
        pdf.output(filepath)
        return jsonify({"message": f"Transaction recorded and receipt saved as {safe_filename}."})
    except Exception as e:
        print(f"Receipt Generation Error: {e}")
        return jsonify({"error": "Failed to generate transaction receipt."}), 500

@app.route('/api/get-transactions', methods=['GET'])
def get_transactions():
    if not os.path.exists(TRANSACTION_LOG_FILE):
        return jsonify([])
    try:
        with open(TRANSACTION_LOG_FILE, "r") as f:
            lines = f.readlines()
        transactions = []
        for line in lines:
            parts = {p.split(':')[0].strip(): ':'.join(p.split(':')[1:]).strip() for p in line.strip().split(', ')}
            transactions.append(parts)
        return jsonify(transactions)
    except Exception as e:
        print(f"Error reading transaction log: {e}")
        return jsonify({"error": "Could not retrieve transaction history."}), 500

if __name__ == '__main__':
    print("Starting NovaMint backend server on http://127.0.0.1:5001")
    app.run(host='0.0.0.0', port=5001, debug=True)
