import os
import zipfile
import shutil
from flask import Flask, request, send_file, render_template_string
from PIL import Image, ImageDraw, ImageFont
import pytesseract
from deep_translator import GoogleTranslator

# Set Tesseract path for Termux; verify the path if needed
pytesseract.pytesseract.tesseract_cmd = '/data/data/com.termux/files/usr/bin/tesseract'

app = Flask(__name__)

# Determine base directory (adjust as necessary)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Define folders (absolute paths)
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(BASE_DIR, 'output')
EXTRACT_FOLDER = os.path.join(UPLOAD_FOLDER, 'extracted')
TRANSLATED_FOLDER = os.path.join(OUTPUT_FOLDER, 'translated')

# Font path in Termux (make sure fonts-dejavu is installed)
TERMUX_FONT_PATH = "/data/data/com.termux/files/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Create necessary directories
for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, EXTRACT_FOLDER, TRANSLATED_FOLDER]:
    try:
        os.makedirs(folder, exist_ok=True)
        print(f"[SETUP] Directory ensured: {folder}")
    except OSError as e:
        print(f"[ERROR] Could not create directory {folder}: {e}")
        exit()

@app.route('/')
def index():
    # Simple HTML form for upload using render_template_string for simplicity
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Manga Translator (Termux)</title>
        </head>
        <body>
            <h1>Manga Translator (Termux)</h1>
            <form method="POST" action="/upload" enctype="multipart/form-data">
                <label for="zip_file">Select Manga ZIP File:</label>
                <input type="file" id="zip_file" name="zip_file" accept=".zip" required /><br><br>
                <input type="submit" value="Upload & Translate" />
            </form>
            <p>Note: Your ZIP must contain image files (.png, .jpg, .jpeg) at the root (no subdirectories).</p>
        </body>
        </html>
    ''')

@app.route('/upload', methods=['POST'])
def upload_and_translate():
    # Check file upload key & type
    if 'zip_file' not in request.files or not request.files['zip_file'].filename:
        return "No file selected.", 400
    zip_file = request.files['zip_file']
    if not zip_file.filename.lower().endswith('.zip'):
        return "Invalid file type. Please upload a .zip file.", 400

    # Save uploaded ZIP using a fixed name ("input.zip")
    zip_filename = zip_file.filename  # To later use in naming output ZIP
    zip_path = os.path.join(UPLOAD_FOLDER, "input.zip")
    try:
        zip_file.save(zip_path)
        print(f"[INFO] Uploaded ZIP saved to: {zip_path}")
    except Exception as e:
        print(f"[ERROR] Could not save uploaded ZIP: {e}")
        return "Error saving uploaded file.", 500

    # Clean previous extracted and translated folders
    print("[INFO] Cleaning previous output...")
    for folder in [EXTRACT_FOLDER, TRANSLATED_FOLDER]:
        try:
            if os.path.exists(folder):
                shutil.rmtree(folder)
            os.makedirs(folder, exist_ok=True)
            print(f"[CLEAN] Folder cleaned and recreated: {folder}")
        except Exception as e:
            print(f"[ERROR] Cleaning folder {folder} failed: {e}")
            return f"Error cleaning folder {folder}.", 500

    # Extract the ZIP file and verify contents
    print(f"[INFO] Extracting ZIP: {zip_path}")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(EXTRACT_FOLDER)
        print(f"[INFO] ZIP successfully extracted to: {EXTRACT_FOLDER}")
        extracted_files = os.listdir(EXTRACT_FOLDER)
        print(f"[DEBUG] Extracted files: {extracted_files}")
        if not extracted_files:
            print("[WARNING] No files found in ZIP.")
            return "Uploaded ZIP file is empty.", 400
    except zipfile.BadZipFile:
        print(f"[ERROR] The uploaded file is not a valid ZIP: {zip_path}")
        return "Invalid or corrupted ZIP file.", 400
    except Exception as e:
        print(f"[ERROR] ZIP extraction failed: {e}")
        return "ZIP extraction failed.", 500

    image_count = 0
    processed_files = []  # To track successfully processed image paths

    # Attempt to load a custom font
    try:
        if os.path.exists(TERMUX_FONT_PATH):
            font = ImageFont.truetype(TERMUX_FONT_PATH, 24)
            print(f"[INFO] Loaded custom font from {TERMUX_FONT_PATH}")
        else:
            print(f"[WARNING] Custom font not found. Using default font.")
            font = ImageFont.load_default()
    except Exception as font_err:
        print(f"[ERROR] Font loading failed: {font_err}. Using default font.")
        font = ImageFont.load_default()

    # Process each file in the extraction folder
    valid_extensions = ('.png', '.jpg', '.jpeg')
    for filename in os.listdir(EXTRACT_FOLDER):
        file_path = os.path.join(EXTRACT_FOLDER, filename)
        if not os.path.isfile(file_path) or not filename.lower().endswith(valid_extensions):
            print(f"[SKIP] Ignored non-image file: {filename}")
            continue

        print(f"--- Processing file: {filename} ---")
        try:
            img = Image.open(file_path).convert("RGB")
            print(f"[DEBUG] Opened image: {filename} (Size: {img.size})")
        except Exception as img_error:
            print(f"[ERROR] Could not open image {filename}: {img_error}")
            continue

        # Perform OCR with robust error handling
        try:
            text = pytesseract.image_to_string(img, lang='eng+jpn')
            if text.strip():
                print(f"[OCR] Detected text in {filename}: '{text.strip()[:150]}'")
            else:
                print(f"[OCR] EMPTY OCR output for {filename}. Skipping this image.")
                continue
        except Exception as ocr_error:
            print(f"[ERROR] OCR failed on {filename}: {ocr_error}")
            continue

        # Translate the detected text
        try:
            translated_text = GoogleTranslator(source='auto', target='en').translate(text)
            if translated_text:
                print(f"[TRANSLATED] {filename}: '{translated_text.strip()[:150]}'")
            else:
                print(f"[WARNING] Translation resulted in empty text for {filename}.")
                translated_text = "[Translation Failed]"
        except Exception as translate_error:
            print(f"[ERROR] Translation failed for {filename}: {translate_error}")
            translated_text = "[Translation Error]"

        # Draw the translated text onto the image
        try:
            draw = ImageDraw.Draw(img)
            box_height = 100  # Fixed height for the text box at the top
            draw.rectangle([0, 0, img.width, box_height], fill="white", outline="black")
            draw.text((10, 10), translated_text, fill="black", font=font)
            print(f"[DRAW] Text drawn on {filename}")
        except Exception as draw_error:
            print(f"[ERROR] Failed to draw text on {filename}: {draw_error}")
            continue

        # Save the processed image
        output_img_path = os.path.join(TRANSLATED_FOLDER, filename)
        try:
            img.save(output_img_path)
            print(f"[SAVE] Saved processed image: {output_img_path}")
            image_count += 1
            processed_files.append(filename)
        except Exception as save_err:
            print(f"[ERROR] Saving image {filename} failed: {save_err}")
            continue
        finally:
            img.close()

    print(f"[INFO] Image processing completed. Processed images: {image_count}")
    print(f"[DEBUG] Files in TRANSLATED_FOLDER: {os.listdir(TRANSLATED_FOLDER)}")
    if image_count == 0:
        return "No images were successfully processed.", 200

    # Create a ZIP file containing all translated images
    output_zip_filename = f"translated_{os.path.splitext(zip_filename)[0]}.zip"
    output_zip_path = os.path.join(OUTPUT_FOLDER, output_zip_filename)
    print(f"[INFO] Creating output ZIP: {output_zip_path}")
    try:
        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for fname in processed_files:
                file_to_zip = os.path.join(TRANSLATED_FOLDER, fname)
                if os.path.exists(file_to_zip):
                    zipf.write(file_to_zip, fname)
                else:
                    print(f"[WARNING] Expected file not found for zipping: {file_to_zip}")
        if os.path.getsize(output_zip_path) > 0:
            print(f"[DONE] Output ZIP created successfully: {output_zip_path}")
            return send_file(output_zip_path, as_attachment=True)
        else:
            print(f"[ERROR] Generated ZIP file is empty: {output_zip_path}")
            return "Output ZIP is empty.", 500
    except Exception as zip_err:
        print(f"[ERROR] Failed to create output ZIP: {zip_err}")
        return "Failed to create ZIP file.", 500

if __name__ == '__main__':
    print("[START] Starting Flask server...")
    print(f"[CONFIG] Tesseract command: {pytesseract.pytesseract.tesseract_cmd}")
    print(f"[CONFIG] Font path: {TERMUX_FONT_PATH}")
    print(f"[CONFIG] Upload folder: {UPLOAD_FOLDER}")
    print(f"[CONFIG] Output folder: {OUTPUT_FOLDER}")
    print(f"[CONFIG] Extract folder: {EXTRACT_FOLDER}")
    print(f"[CONFIG] Translated folder: {TRANSLATED_FOLDER}")
    print("Access the app via http://<your-phone-ip>:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
