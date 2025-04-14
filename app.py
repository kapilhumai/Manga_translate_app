import os
import zipfile
import shutil

from flask import Flask, request, render_template, send_file
from PIL import Image, ImageDraw, ImageFont
import pytesseract
import cv2
import numpy as np
from transformers import pipeline

app = Flask(__name__)

# Use Hugging Face translation pipeline
translator = pipeline("translation", model="Helsinki-NLP/opus-mt-ja-en")  # Japanese to English

UPLOAD_FOLDER = "uploads"
RESULT_FOLDER = "translated"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)


def translate_image_text(image_path):
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    data = pytesseract.image_to_data(gray, lang='jpn', output_type=pytesseract.Output.DICT)

    for i in range(len(data['text'])):
        if int(data['conf'][i]) > 50 and data['text'][i].strip() != "":
            x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
            original_text = data['text'][i]
            try:
                translated = translator(original_text)[0]['translation_text']
            except:
                translated = "[error]"
            
            # White out the original text
            cv2.rectangle(img, (x, y), (x + w, y + h), (255, 255, 255), -1)
            # Write translated text
            cv2.putText(img, translated, (x, y + h - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

    output_path = os.path.join(RESULT_FOLDER, os.path.basename(image_path))
    cv2.imwrite(output_path, img)
    return output_path


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'zipfile' not in request.files:
            return "No file uploaded"

        zip_file = request.files['zipfile']
        upload_path = os.path.join(UPLOAD_FOLDER, "uploaded.zip")
        zip_file.save(upload_path)

        extract_folder = os.path.join(UPLOAD_FOLDER, "extracted")
        shutil.unpack_archive(upload_path, extract_folder)

        output_images = []
        for filename in os.listdir(extract_folder):
            if filename.lower().endswith((".png", ".jpg", ".jpeg")):
                img_path = os.path.join(extract_folder, filename)
                out_path = translate_image_text(img_path)
                output_images.append(out_path)

        # Zip result
        result_zip = os.path.join(RESULT_FOLDER, "translated.zip")
        with zipfile.ZipFile(result_zip, 'w') as zipf:
            for img_path in output_images:
                zipf.write(img_path, os.path.basename(img_path))

        return send_file(result_zip, as_attachment=True)

    return render_template("index.html")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
