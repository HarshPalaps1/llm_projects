import os
from flask import Flask, render_template, request, send_file
import pdfplumber
import docx
from werkzeug.utils import secure_filename
from fpdf import FPDF

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from dotenv import load_dotenv
from asgiref.wsgi import WsgiToAsgi  # ✅ NEW

load_dotenv()

# ----------------------------
# Flask App Setup
# ----------------------------
flask_app = Flask(__name__)   # 🔹 renamed
flask_app.config['UPLOAD_FOLDER'] = 'uploads/'
flask_app.config['RESULTS_FOLDER'] = 'results/'
flask_app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'txt', 'docx'}

os.makedirs(flask_app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(flask_app.config['RESULTS_FOLDER'], exist_ok=True)

# ----------------------------
# Initialize LLM
# ----------------------------
llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.3-70b-versatile",
    temperature=0.0
)

# ----------------------------
# Prompt Template
# ----------------------------
mcq_prompt = ChatPromptTemplate.from_template("""
You are an AI assistant helping the user generate multiple-choice questions (MCQs) from the text below.

Text:
{context}

Generate {num_questions} MCQs...
""")

mcq_chain = mcq_prompt | llm | StrOutputParser()

# ----------------------------
# Routes (IMPORTANT CHANGE)
# ----------------------------
@flask_app.route('/')
def index():
    return render_template('index.html')

@flask_app.route('/generate', methods=['POST'])
def generate_mcqs():

    if 'file' not in request.files:
        return "No file uploaded."

    file = request.files['file']

    if file and '.' in file.filename:
        filename = secure_filename(file.filename)
        file_path = os.path.join(flask_app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # (same logic as before...)
        return "Processing done"

    return "Error"

@flask_app.route('/download/<filename>')
def download_file(filename):
    path = os.path.join(flask_app.config['RESULTS_FOLDER'], filename)
    return send_file(path, as_attachment=True)

# ----------------------------
# 🔥 CONVERT TO ASGI
# ----------------------------
app = WsgiToAsgi(flask_app)

# ----------------------------
# LOCAL RUN (OPTIONAL)
# ----------------------------
if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=8000, debug=True)