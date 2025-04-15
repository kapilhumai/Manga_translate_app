import os
import zipfile
from flask import Flask, request, send_file
from PIL import Image, ImageDraw, ImageFont
import pytesseract
from deep_translator import GoogleTranslator

# Path to tesseract binary in Termux
pytesseract.pytesseract.tesseract_cmd = '/data/data/com.termux/files/usr/bin/tesseract'

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
EXTRACT_FOLDER = os.path.join(UPLOAD_FOLDER, 'extracted')
TRANSLATED_FOLDER = os.path.join(OUTPUT_FOLDER, 'translated')

# Make necessary directories
for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, EXTRACT_FOLDER, TRANSLATED_FOLDER]:
    os.makedirs(folder, exist_ok=True)

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

    # Clean extracted and translated folders
    for folder in [EXTRACT_FOLDER, TRANSLATED_FOLDER]:
        for f in os.listdir(folder):
            file_path = os.path.join(folder, f)
            os.remove(file_path)

    # Extract ZIP
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(EXTRACT_FOLDER)
        print(f"[INFO] ZIP extracted to {EXTRACT_FOLDER}")
    except Exception as e:
        print(f"[ERROR] ZIP extraction failed: {e}")
        return "ZIP extraction failed."

    image_count = 0
    for filename in os.listdir(EXTRACT_FOLDER):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            image_path = os.path.join(EXTRACT_FOLDER, filename)
            print(f"[INFO] Processing {filename}")
            try:
                img = Image.open(image_path).convert("RGB")
            except Exception as img_error:
                print(f"[ERROR] Could not open image {filename}: {img_error}")
                continue

            try:
                text = pytesseract.image_to_string(img, lang='eng+jpn')
                if text.strip():
                    print(f"[OCR] Text from {filename}:\n{text.strip()[:150]}")
                else:
                    print(f"[OCR] EMPTY OCR result from {filename}")
                    continue
            except Exception as ocr_error:
                print(f"[ERROR] OCR failed on {filename}: {ocr_error}")
                continue

            try:
                translated_text = GoogleTranslator(source='auto', target='en').translate(text)
                print(f"[TRANSLATED] {filename}:\n{translated_text.strip()[:150]}")
            except Exception as translate_error:
                print(f"[ERROR] Translation failed for {filename}: {translate_error}")
                continue

            # Add translated text to image
            try:
                draw = ImageDraw.Draw(img)
                try:
                    font = ImageFont.truetype("/data/data/com.termux/files/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
                except:
                    font = ImageFont.load_default()

                draw.rectangle([0, 0, img.width, 100], fill="white")
                draw.text((10, 10), translated_text, fill="black", font=font)
            except Exception as draw_error:
                print(f"[ERROR] Drawing text failed for {filename}: {draw_error}")
                continue

            try:
                img.save(os.path.join(TRANSLATED_FOLDER, filename))
                print(f"[SAVE] Saved translated image: {filename}")
                image_count += 1
            except Exception as save_err:
                print(f"[ERROR] Saving image failed: {save_err}")
                continue

    if image_count == 0:
        return "No images found or successfully processed."

    # Create output ZIP
    output_zip = os.path.join(OUTPUT_FOLDER, 'translated.zip')
    try:
        with zipfile.ZipFile(output_zip, 'w') as zipf:
            for filename in os.listdir(TRANSLATED_FOLDER):
                zipf.write(os.path.join(TRANSLATED_FOLDER, filename), filename)
        print(f"[DONE] Translated ZIP created: {output_zip}")
        return send_file(output_zip, as_attachment=True)
    except Exception as zip_err:
        print(f"[ERROR] Failed to create output ZIP: {zip_err}")
        return "Failed to create output ZIP."

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
