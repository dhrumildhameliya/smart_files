from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os
from PyPDF2 import PdfMerger
from PIL import Image
from flask import send_from_directory
import zipfile
from datetime import datetime
import os

IS_RENDER = os.getenv("RENDER") is not None

os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)

app = Flask(__name__)
app.secret_key = "smartfile"

# Folders
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["OUTPUT_FOLDER"] = OUTPUT_FOLDER

# Allowed extensions
ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "docx"}

# Create folders if not exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# Home Page (Upload)
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":

        files = request.files.getlist("files")
        operation = request.form.get("operation")

        uploaded_files = []

        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(path)
                uploaded_files.append(filename)

        # Decide operation
        if operation == "merge_pdf":
            return redirect(url_for("dashboard"))

        elif operation == "image_to_pdf":
            return redirect(url_for("dashboard"))

        elif operation == "compress_pdf":
            return redirect(url_for("dashboard"))

        elif operation == "zip_files":
            return redirect(url_for("dashboard"))

    return render_template("index.html")


# Dashboard Page
@app.route("/dashboard")
def dashboard():
    files = os.listdir(app.config["UPLOAD_FOLDER"])
    return render_template("dashboard.html", files=files)

@app.route("/merge-pdf", methods=["POST"])
def merge_pdf():
    selected_files = request.form.getlist("pdf_files")

    if len(selected_files) < 2:
        flash("Select at least 2 PDFs")
        return redirect(url_for("dashboard"))

    merger = PdfMerger()

    for pdf in selected_files:
        merger.append(os.path.join(app.config["UPLOAD_FOLDER"], pdf))

    output_file = "merged.pdf"
    output_path = os.path.join(app.config["OUTPUT_FOLDER"], output_file)

    merger.write(output_path)
    merger.close()

    # 🔥 DELETE OLD FILES
    clear_folder(app.config["UPLOAD_FOLDER"])

    return redirect(url_for("download_file", filename=output_file))

@app.route("/image-to-pdf", methods=["POST"])
def image_to_pdf():
    selected_images = request.form.getlist("image_files")

    if not selected_images:
        flash("No image selected")
        return redirect(url_for("dashboard"))

    images = []
    for img in selected_images:
        path = os.path.join(app.config["UPLOAD_FOLDER"], img)
        images.append(Image.open(path).convert("RGB"))

    output_file = "images.pdf"
    output_path = os.path.join(app.config["OUTPUT_FOLDER"], output_file)

    images[0].save(output_path, save_all=True, append_images=images[1:])

    # 🔥 DELETE OLD FILES
    clear_folder(app.config["UPLOAD_FOLDER"])

    return redirect(url_for("download_file", filename=output_file))

from flask import after_this_request

@app.route("/download/<filename>")
def download_file(filename):
    file_path = os.path.join(app.config["OUTPUT_FOLDER"], filename)

    @after_this_request
    def remove_file(response):
        try:
            os.remove(file_path)
        except:
            pass
        return response

    return send_from_directory(app.config["OUTPUT_FOLDER"], filename, as_attachment=True)

def clear_folder(folder_path):
    for file in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file)
        if os.path.isfile(file_path):
            os.remove(file_path)


@app.route("/zip-files", methods=["POST"])
def zip_files():
    selected_files = request.form.getlist("zip_files")

    if not selected_files:
        flash("Select files to ZIP")
        return redirect(url_for("dashboard"))

    zip_name = f"files_{datetime.now().strftime('%Y%m%d%H%M%S')}.zip"
    zip_path = os.path.join(app.config["OUTPUT_FOLDER"], zip_name)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in selected_files:
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], file)
            zipf.write(file_path, arcname=file)

    clear_folder(app.config["UPLOAD_FOLDER"])

    return redirect(url_for("download_file", filename=zip_name))

from pdf2image import convert_from_path
import pikepdf
import pikepdf

@app.route("/compress-pdf", methods=["POST"])
def compress_pdf():
    pdf_file = request.form.get("compress_pdf")

    if not pdf_file:
        flash("Select a PDF to compress")
        return redirect(url_for("dashboard"))

    input_path = os.path.join(app.config["UPLOAD_FOLDER"], pdf_file)
    output_filename = "compressed.pdf"
    output_path = os.path.join(app.config["OUTPUT_FOLDER"], output_filename)

    # 📏 Before size (KB)
    before_size = round(os.path.getsize(input_path) / 1024, 2)

    # ✅ Compress PDF (compatible with all versions)
    with pikepdf.open(input_path) as pdf:
        pdf.save(
            output_path,
            compress_streams=True
        )

    # 📏 After size (KB)
    after_size = round(os.path.getsize(output_path) / 1024, 2)

    reduction = round(before_size - after_size, 2)

    # 🔥 Clear uploaded files
    clear_folder(app.config["UPLOAD_FOLDER"])

    flash(
        f"Compression done | Before: {before_size} KB | "
        f"After: {after_size} KB | Reduced: {reduction} KB"
    )

    return redirect(url_for("download_file", filename=output_filename))

# from docx2pdf import convert

# @app.route("/word-to-pdf", methods=["POST"])
# def word_to_pdf():
#     word_file = request.form.get("word_file")

#     if not word_file:
#         flash("Select Word file")
#         return redirect(url_for("dashboard"))

#     input_path = os.path.join(app.config["UPLOAD_FOLDER"], word_file)
#     output_path = os.path.join(app.config["OUTPUT_FOLDER"], "word_converted.pdf")

#     convert(input_path, output_path)

#     clear_folder(app.config["UPLOAD_FOLDER"])

#     return redirect(url_for("download_file", filename="word_converted.pdf"))

@app.route("/word-to-pdf", methods=["POST"])
def word_to_pdf():
    if IS_RENDER:
        flash("Word to PDF is not supported on cloud deployment.")
        return redirect(url_for("dashboard"))

    # Local machine only
    from docx2pdf import convert

    word_file = request.form.get("word_file")

    if not word_file:
        flash("Select Word file")
        return redirect(url_for("dashboard"))

    input_path = os.path.join(app.config["UPLOAD_FOLDER"], word_file)
    output_path = os.path.join(app.config["OUTPUT_FOLDER"], "word_converted.pdf")

    convert(input_path, output_path)

    clear_folder(app.config["UPLOAD_FOLDER"])

    return redirect(url_for("download_file", filename="word_converted.pdf"))

# Run server
# if __name__ == "__main__":
#     app.run(debug=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

