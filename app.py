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
                text = pytesseract.image_to_string(img, lang='eng+jpn')
                print(f"[OCR] Text from {filename}:\n{text.strip()[:100]}")

                if not text.strip():
                    print(f"[WARN] No text found in {filename}")
                    continue

                translated_text = GoogleTranslator(source='auto', target='en').translate(text)
                print(f"[TRANSLATED] {filename}:\n{translated_text.strip()[:100]}")

                # Add translated text to image
                draw = ImageDraw.Draw(img)
                try:
                    font = ImageFont.truetype("/data/data/com.termux/files/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
                except:
                    font = ImageFont.load_default()

                draw.rectangle([0, 0, img.width, 100], fill="white")
                draw.text((10, 10), translated_text, fill="black", font=font)

                img.save(os.path.join(TRANSLATED_FOLDER, filename))
                print(f"[SAVE] Translated image saved as {filename}")
                image_count += 1

            except Exception as e:
                print(f"[ERROR] Failed processing {filename}: {e}")

    if image_count == 0:
        return "No images found in uploaded ZIP."

    # Create output ZIP
    output_zip = os.path.join(OUTPUT_FOLDER, 'translated.zip')
    with zipfile.ZipFile(output_zip, 'w') as zipf:
        for filename in os.listdir(TRANSLATED_FOLDER):
            zipf.write(os.path.join(TRANSLATED_FOLDER, filename), filename)
    print(f"[DONE] Translated ZIP created: {output_zip}")

    return send_file(output_zip, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
