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
from asgiref.wsgi import WsgiToAsgi  # ✅ ASGI adapter

load_dotenv()

# ----------------------------
# Flask App Setup
# ----------------------------
flask_app = Flask(__name__)
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

Generate {num_questions} MCQs. Each should include:
- A clear question
- Four options A, B, C, D
- Correct answer

Format:
## MCQ
Question: ...
A) ...
B) ...
C) ...
D) ...
Correct Answer: ...
""")

mcq_chain = mcq_prompt | llm | StrOutputParser()

# ----------------------------
# Helpers
# ----------------------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in flask_app.config['ALLOWED_EXTENSIONS']


def extract_text_from_file(file_path):
    ext = file_path.rsplit('.', 1)[1].lower()

    if ext == 'pdf':
        with pdfplumber.open(file_path) as pdf:
            return ''.join([page.extract_text() or "" for page in pdf.pages])

    elif ext == 'docx':
        doc = docx.Document(file_path)
        return ' '.join([para.text for para in doc.paragraphs])

    elif ext == 'txt':
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    return None


def generate_mcqs(text, num_questions):
    return mcq_chain.invoke({
        "context": text,
        "num_questions": num_questions
    }).strip()


def save_txt(mcqs, filename):
    path = os.path.join(flask_app.config['RESULTS_FOLDER'], filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(mcqs)
    return path


def create_pdf(mcqs, filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    for mcq in mcqs.split("## MCQ"):
        if mcq.strip():
            pdf.multi_cell(0, 10, mcq.strip())
            pdf.ln(5)

    path = os.path.join(flask_app.config['RESULTS_FOLDER'], filename)
    pdf.output(path)
    return path

# ----------------------------
# Routes
# ----------------------------
@flask_app.route('/')
def index():
    return render_template('index.html')


@flask_app.route('/generate', methods=['POST'])
def generate():
    if 'file' not in request.files:
        return "No file uploaded."

    file = request.files['file']

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(flask_app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        text = extract_text_from_file(file_path)

        if text:
            num_questions = int(request.form['num_questions'])
            mcqs = generate_mcqs(text, num_questions)

            base = filename.rsplit('.', 1)[0]
            txt_file = f"{base}.txt"
            pdf_file = f"{base}.pdf"

            save_txt(mcqs, txt_file)
            create_pdf(mcqs, pdf_file)

            return render_template(
                'results.html',
                mcqs=mcqs,
                txt_filename=txt_file,
                pdf_filename=pdf_file
            )

    return "Error processing file."


# @flask_app.route('/download/<filename>')
# def download(filename):
#     path = os.path.join(flask_app.config['RESULTS_FOLDER'], filename)
#     return send_file(path, as_attachment=True)

# ----------------------------
# ✅ ASGI APP FOR UVICORN
# ----------------------------
app = WsgiToAsgi(flask_app)