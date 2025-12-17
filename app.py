import streamlit as st
from openai import OpenAI
import PyPDF2
import io

# --- 1. 頁面設定 ---
st.set_page_config(page_title="DSE All-in-One 溫習平台", layout="wide", page_icon="🇭🇰")

# --- 2. 安全讀取 API Key ---
api_key = None
if "DEEPSEEK_API_KEY" in st.secrets:
    api_key = st.secrets["DEEPSEEK_API_KEY"]
else:
    # 這是為了防呆，如果後台沒設定，側邊欄會出現輸入框
    api_key = st.sidebar.text_input("DeepSeek API Key", type="password")

if not api_key:
    st.warning("⚠️ 系統偵測不到 API Key。請在 Streamlit Cloud 設定 Secrets，或在側邊欄輸入。")
    st.stop()

client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

# --- 3. 側邊欄 ---
with st.sidebar:
    st.title("🇭🇰 DSE 備戰中心")
    st.caption("PDF 清洗 -> NotebookLM -> 智能溫習")
    st.divider()
    subject = st.selectbox("當前科目", ["Biology", "Chemistry", "Economics", "Chinese", "English", "History"])
    st.info("💡 提示：先在 Tab 1 清洗 PDF，再去 NotebookLM 生成音檔，最後在 Tab 2 溫習。")

# --- 4. 主功能區 (Tabs) ---
tab_factory, tab_study = st.tabs(["🛠️ 步驟一：資料清洗工廠", "🎓 步驟二：智能溫習室"])

# ==========================================
# TAB 1: 資料清洗工廠 (Data Preparation)
# ==========================================
with tab_factory:
    st.header(f"🧹 {subject} - PDF 資料清洗器")
    st.write("將雜亂的 PDF (Past Paper/書) 轉換為 AI 易讀的筆記，供 NotebookLM 使用。")
    
    uploaded_pdf = st.file_uploader("上傳原始 PDF", type=["pdf"])
    
    if uploaded_pdf:
        # 讀取 PDF
        try:
            reader = PyPDF2.PdfReader(uploaded_pdf)
            raw_text = ""
            for page in reader.pages:
                raw_text += page.extract_text() + "\n"
            
            st.success(f"📄 成功讀取 {len(reader.pages)} 頁，共 {len(raw_text)} 字。")
            
            if st.button("🚀 開始 DeepSeek 清洗 (轉換為筆記)"):
                with st.spinner("DeepSeek 正在閱讀並整理重點... (需時約 30-60 秒)"):
                    # 清洗 Prompt
                    clean_prompt = f"""
                    你是一位專業的香港 DSE {subject} 教材編輯。
                    請處理以下 PDF 原始文本，轉換為結構清晰的 Markdown 筆記。
                    
                    要求：
                    1. 【去除雜訊】：刪除頁碼、重複的頁眉頁腳、考試規則。
                    2. 【結構化】：按課題 (Topic) 使用 # 和 ## 標題。
                    3. 【精煉】：保留所有 DSE 關鍵字 (Keywords)，去除冗餘廢話。
                    4. 【格式】：若有題目，請整理為 Q&A 格式。
                    
                    原始文本(截取部分)：
                    {raw_text[:15000]} 
                    """
                    
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[{"role": "user", "content": clean_prompt}]
                    )
                    cleaned_content = response.choices[0].message.content
                    
                    # 顯示結果與下載
                    st.subheader("📝 筆記預覽")
                    st.text_area("Result", cleaned_content, height=300)
                    
                    file_name = f"{subject}_Cleaned_Notes.txt"
                    st.download_button(
                        label="📥 下載 .txt 檔案 (用於 NotebookLM)",
                        data=cleaned_content,
                        file_name=file_name,
                        mime="text/plain"
                    )
                    st.success("✅ 完成！請將此檔案上傳至 NotebookLM 生成 Audio。")
                    
        except Exception as e:
            st.error(f"讀取 PDF 時發生錯誤: {e}")

# ==========================================
# TAB 2: 智能溫習室 (Study Room)
# ==========================================
with tab_study:
    st.header(f"🎓 {subject} - 衝刺模式")
    
    col_input, col_main = st.columns([1, 2])
    
    with col_input:
        st.markdown("### 1. 載入資源")
        notes_file = st.file_uploader("上傳清洗後的筆記 (.txt)", type=["txt", "md"], key="notes")
        audio_file = st.file_uploader("上傳 NotebookLM 音檔 (.mp3)", type=["mp3", "wav"], key="audio")
        
        notes_text = ""
        if notes_file:
            notes_text = notes_file.read().decode("utf-8")
    
    with col_main:
        if not notes_text:
            st.info("👈 請先在左側上傳資源 (步驟一產出的 TXT + NotebookLM 的 MP3)")
        else:
            # === 功能分頁 ===
            sub_tab1, sub_tab2, sub_tab3 = st.tabs(["🎧 聽覺學習", "💬 導師問答", "✍️ 模擬試卷"])
            
            # --- 聽覺學習 ---
            with sub_tab1:
                st.subheader("NotebookLM Podcast")
                if audio_file:
                    st.audio(audio_file)
                else:
                    st.warning("未上傳音頻，建議配合 NotebookLM 使用以達最佳效果。")
                
                with st.expander("查看完整筆記內容"):
                    st.markdown(notes_text)

            # --- 導師問答 ---
            with sub_tab2:
                st.subheader("AI 導師 (DeepSeek)")
                if "messages" not in st.session_state:
                    st.session_state.messages = []

                for msg in st.session_state.messages:
                    st.chat_message(msg["role"]).write(msg["content"])

                if user_input := st.chat_input("e.g. 用廣東話解釋呢個 Concept"):
                    st.session_state.messages.append({"role": "user", "content": user_input})
                    st.chat_message("user").write(user_input)

                    with st.chat_message("assistant"):
                        rag_prompt = f"""
                        你是一位 DSE {subject} 導師。請根據以下筆記回答學生問題。
                        必須使用【廣東話】。
                        筆記內容：{notes_text[:12000]}
                        """
                        stream = client.chat.completions.create(
                            model="deepseek-chat",
                            messages=[
                                {"role": "system", "content": rag_prompt},
                                {"role": "user", "content": user_input}
                            ],
                            stream=True
                        )
                        response = st.write_stream(stream)
                    st.session_state.messages.append({"role": "assistant", "content": response})

            # --- 模擬試卷 ---
            with sub_tab3:
                st.subheader("DSE 題目生成器")
                diff = st.select_slider("難度", options=["Level 2", "Level 4", "Level 5**"])
                if st.button("生成題目"):
                    with st.spinner("出卷中..."):
                        q_prompt = f"""
                        根據筆記，設計一條 {subject} {diff} 的題目 (MC 或 LQ)。
                        附帶詳細 Marking Scheme。
                        筆記：{notes_text[:5000]}
                        """
                        res = client.chat.completions.create(
                            model="deepseek-chat",
                            messages=[{"role": "user", "content": q_prompt}]
                        )
                        st.markdown(res.choices[0].message.content)
