import os
import zipfile
from flask import Flask, request, send_file, jsonify
from PIL import Image, ImageDraw, ImageFont
import pytesseract
pytesseract.pytesseract.tesseract_cmd = '/data/data/com.termux/files/usr/bin/tesseract'
from deep_translator import GoogleTranslator

app = Flask(name)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return '''
        <h1>Manga Translator (Termux)</h1>
        <form method="POST" action="/upload" enctype="multipart/form-data">
            <input type="file" name="zip_file" accept=".zip" />
            <input type="submit" value="Upload & Translate" />
        </form>
    '''

@app.route('/upload', methods=['POST'])
def upload_and_translate():
    zip_file = request.files['zip_file']
    zip_path = os.path.join(UPLOAD_FOLDER, zip_file.filename)
    zip_file.save(zip_path)

    extract_folder = os.path.join(UPLOAD_FOLDER, 'extracted')
    os.makedirs(extract_folder, exist_ok=True)

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_folder)

    translated_folder = os.path.join(OUTPUT_FOLDER, 'translated')
    os.makedirs(translated_folder, exist_ok=True)

    for filename in os.listdir(extract_folder):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            path = os.path.join(extract_folder, filename)
            img = Image.open(path)
            text = pytesseract.image_to_string(img, lang='eng+jpn')

            translated_text = GoogleTranslator(source='auto', target='en').translate(text)

            draw = ImageDraw.Draw(img)
            draw.rectangle([0, 0, img.width, 100], fill="white")  # Clear top area
            draw.text((10, 10), translated_text, fill="black")

            img.save(os.path.join(translated_folder, filename))

    output_zip = os.path.join(OUTPUT_FOLDER, 'translated.zip')
    with zipfile.ZipFile(output_zip, 'w') as zipf:
        for filename in os.listdir(translated_folder):
            zipf.write(os.path.join(translated_folder, filename), filename)

    return send_file(output_zip, as_attachment=True)

if name == 'main':
    app.run(debug=True, host='0.0.0.0', port=5000)
