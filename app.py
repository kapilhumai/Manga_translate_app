manga_translate_app/main.py

import os import zipfile import shutil from flask import Flask, request, render_template, send_file from PIL import Image, ImageDraw, ImageFont import pytesseract import cv2 import numpy as np from transformers import pipeline

app = Flask(name) UPLOAD_FOLDER = 'uploads' OUTPUT_FOLDER = 'output' os.makedirs(UPLOAD_FOLDER, exist_ok=True) os.makedirs(OUTPUT_FOLDER, exist_ok=True)

Translation pipeline (default: Japanese to English)

translator = pipeline("translation", model="Helsinki-NLP/opus-mt-ja-en")

Load a default font for drawing (replace with manga-style font if available)

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" FONT = ImageFont.truetype(FONT_PATH, 20)

@app.route('/', methods=['GET', 'POST']) def index(): if request.method == 'POST': zip_file = request.files['zip_file'] lang_code = request.form.get('lang_code', 'ja')

model_map = {
        'ja': 'Helsinki-NLP/opus-mt-ja-en',
        'zh': 'Helsinki-NLP/opus-mt-zh-en',
        'ko': 'Helsinki-NLP/opus-mt-ko-en'
    }

    model_name = model_map.get(lang_code, 'Helsinki-NLP/opus-mt-ja-en')
    global translator
    translator = pipeline("translation", model=model_name)

    if zip_file:
        zip_path = os.path.join(UPLOAD_FOLDER, 'manga.zip')
        zip_file.save(zip_path)

        extract_path = os.path.join(UPLOAD_FOLDER, 'pages')
        if os.path.exists(extract_path):
            shutil.rmtree(extract_path)
        os.makedirs(extract_path, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)

        output_images = process_manga_pages(extract_path, lang_code)

        output_zip = os.path.join(OUTPUT_FOLDER, 'translated_manga.zip')
        with zipfile.ZipFile(output_zip, 'w') as zipf:
            for image_path in output_images:
                zipf.write(image_path, arcname=os.path.basename(image_path))

        return send_file(output_zip, as_attachment=True)

return render_template('index.html')

def process_manga_pages(folder, lang_code): output_files = [] lang_map = { 'ja': 'jpn', 'zh': 'chi_sim', 'ko': 'kor' } ocr_lang = lang_map.get(lang_code, 'jpn')

for filename in sorted(os.listdir(folder)):
    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        img_path = os.path.join(folder, filename)
        img = cv2.imread(img_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # OCR with Tesseract
        data = pytesseract.image_to_data(gray, lang=ocr_lang, output_type=pytesseract.Output.DICT)

        pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil_img)

        n_boxes = len(data['level'])
        for i in range(n_boxes):
            (x, y, w, h) = (data['left'][i], data['top'][i], data['width'][i], data['height'][i])
            text = data['text'][i].strip()
            if text:
                translated = translator(text)[0]['translation_text']
                draw.rectangle([x, y, x+w, y+h], fill='white')
                draw.text((x, y), translated, fill='black', font=FONT)

        out_path = os.path.join(OUTPUT_FOLDER, filename)
        pil_img.save(out_path)
        output_files.append(out_path)

return output_files

if name == 'main': app.run(debug=True)

