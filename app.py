# 記得在最上面 import pdfplumber
import pdfplumber 

# ... (前面的 import 保持不變)

def extract_text_from_file(uploaded_file):
    text = ""
    file_type = uploaded_file.name.split('.')[-1].lower()
    
    try:
        # A. 加強版 PDF 處理 (改用 pdfplumber)
        if file_type == 'pdf':
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    # extract_text() 比 PyPDF2 強大
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            # 如果讀完還是空的，提示用戶這是掃描檔
            if not text.strip():
                return "[系統提示] 偵測到此 PDF 可能是掃描圖片檔 (Scanned PDF)。請將其截圖存為 JPG/PNG 圖片後重新上傳，系統將改用 OCR 辨識。"

        # B. 處理 Word
        elif file_type == 'docx':
            doc = Document(uploaded_file)
            for para in doc.paragraphs:
                text += para.text + "\n"
        
        # ... (其他 C, D, E, F, G 保持不變) ...
        elif file_type == 'pptx':
             prs = Presentation(uploaded_file)
             for slide in prs.slides:
                 for shape in slide.shapes:
                     if hasattr(shape, "text"):
                         text += shape.text + "\n"
        
        elif file_type in ['xlsx', 'xls', 'csv']:
            if file_type == 'csv':
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            text = df.to_markdown(index=False)

        elif file_type in ['jpg', 'jpeg', 'png']:
            image = Image.open(uploaded_file)
            text = pytesseract.image_to_string(image, lang='chi_tra+eng')
            if not text.strip():
                text = "[OCR 提示] 圖片中未能識別出文字，請確保圖片清晰。"

        elif file_type in ['mp3', 'wav', 'm4a']:
            audio = AudioSegment.from_file(uploaded_file)
            wav_buffer = io.BytesIO()
            audio.export(wav_buffer, format="wav")
            wav_buffer.seek(0)
            recognizer = sr.Recognizer()
            with sr.AudioFile(wav_buffer) as source:
                audio_data = recognizer.record(source)
                try:
                    text = recognizer.recognize_google(audio_data, language="yue-Hant-HK")
                except:
                    text = "[Audio] 無法識別。"

        elif file_type in ['txt', 'md']:
            text = uploaded_file.read().decode("utf-8")
            
    except Exception as e:
        return f"讀取檔案錯誤 ({file_type}): {str(e)}"
        
    return text
