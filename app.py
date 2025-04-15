import os
import zipfile
from flask import Flask, request, send_file, jsonify
from PIL import Image, ImageDraw, ImageFont
import pytesseract
from deep_translator import GoogleTranslator

# Correct Tesseract path for Termux
pytesseract.pytesseract.tesseract_cmd = '/data/data/com.termux/files/usr/bin/tesseract'

app = Flask(__name__)

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
    print(f"[INFO] Uploaded ZIP saved to {zip_path}")

    extract_folder = os.path.join(UPLOAD_FOLDER, 'extracted')
    translated_folder = os.path.join(OUTPUT_FOLDER, 'translated')

    # Clean folders
    for folder in [extract_folder, translated_folder]:
        if os.path.exists(folder):
            for f in os.listdir(folder):
                os.remove(os.path.join(folder, f))
        else:
            os.makedirs(folder)

    # Extract ZIP
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_folder)
        print(f"[INFO] ZIP extracted to {extract_folder}")
    except Exception as e:
        print(f"[ERROR] ZIP extraction failed: {e}")
        return "ZIP extraction failed."

    image_count = 0
    for filename in os.listdir(extract_folder):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            image_count += 1
            image_path = os.path.join(extract_folder, filename)
            print(f"[INFO] Processing {filename}")
            try:
                img = Image.open(image_path).convert("RGB")
                text = pytesseract.image_to_string(img, lang='eng+jpn')
                print(f"[OCR] Text from {filename}:\n{text.strip()[:100]}")

                if not text.strip():
                    print(f"[WARN] No text found in {filename}")
                    continue

                translated_text = GoogleTranslator(source='auto', target='en').translate(text)
                print(f"[TRANSLATED] {filename}:\n{translated_text.strip()[:100]}")

                draw = ImageDraw.Draw(img)
                draw.rectangle([0, 0, img.width, 100], fill="white")
                draw.text((10, 10), translated_text, fill="black")
                img.save(os.path.join(translated_folder, filename))
                print(f"[SAVE] Translated image saved as {filename}")
            except Exception as e:
                print(f"[ERROR] Failed processing {filename}: {e}")

    if image_count == 0:
        return "No images found in uploaded ZIP."

    # Create ZIP
    output_zip = os.path.join(OUTPUT_FOLDER, 'translated.zip')
    with zipfile.ZipFile(output_zip, 'w') as zipf:
        for filename in os.listdir(translated_folder):
            zipf.write(os.path.join(translated_folder, filename), filename)
    print(f"[DONE] Translated ZIP created: {output_zip}")

    return send_file(output_zip, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
