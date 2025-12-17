import streamlit as st
from openai import OpenAI
import io

# --- 1. 頁面設定 ---
st.set_page_config(page_title="DSE 智能温習系統 (Web版)", layout="wide", page_icon="🇭🇰")

# --- 2. API Key 設定 (用於 Tab 2 的問答) ---
api_key = None
if "DEEPSEEK_API_KEY" in st.secrets:
    api_key = st.secrets["DEEPSEEK_API_KEY"]
else:
    api_key = st.sidebar.text_input("DeepSeek API Key (用於温習室)", type="password")

# 初始化 Client (只在 Tab 2 使用)
client = None
if api_key:
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

# --- 3. 側邊欄 ---
with st.sidebar:
    st.title("🇭🇰 DSE 備戰中心")
    st.caption("官網清洗 -> NotebookLM -> 智能温習")
    st.divider()
    subject = st.selectbox("當前科目", ["Biology", "Chemistry", "Economics", "Chinese", "English", "History", "Maths"])
    st.info("💡 提示：此版本利用 DeepSeek 官網強大的讀檔能力，解決掃描檔問題。")

# --- 4. 主功能區 ---
tab_factory, tab_study = st.tabs(["🏭 步驟一：官網資料清洗", "🎓 步驟二：智能温習室"])

# ==========================================
# TAB 1: 官網資料清洗 (The Bridge)
# ==========================================
with tab_factory:
    st.header(f"🚀 {subject} - 資料清洗橋樑")
    st.markdown("""
    由於 PDF 掃描檔或複雜格式難以用程式讀取，我們直接利用 **DeepSeek 官網** 的強大能力來處理。
    請跟隨以下三步曲：
    """)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("1. 複製指令 (Prompt)")
        st.write("點擊右上角複製按鈕，這段指令會教 DeepSeek 如何整理筆記：")
        
        # 預設的強力 Prompt
        prompt_text = f"""
        (請上傳附件 PDF/圖片)
        你是一位香港 DSE {subject} 的專業教材編輯。
        請閱讀我上傳的文件，並將其整理為一份「結構清晰」的 Markdown 筆記。
        
        要求：
        1. 【去蕪存菁】：去除頁碼、廣告、重複的考試規則。
        2. 【結構化】：按課題 (Topic) 使用 # 和 ## 標題分類。
        3. 【關鍵詞】：保留所有 DSE 專用術語 (Keywords)，不要過度簡化。
        4. 【題目】：如果內容包含題目與答案，請整理為 Q: ... A: ... 格式。
        5. 【輸出】：直接輸出整理後的內容，不需要開場白。
        """
        st.code(prompt_text, language="text")
        
        st.subheader("2. 前往 DeepSeek 官網")
        st.markdown("帶著複製好的指令和你的 PDF 檔案，前往官網處理。")
        st.link_button("🔗 打開 DeepSeek (chat.deepseek.com)", "https://chat.deepseek.com", type="primary")

    with col2:
        st.subheader("3. 接收成果")
        st.write("DeepSeek 整理好後，請將**所有文字複製**，並貼在下方：")
        
        cleaned_text = st.text_area("在此貼上 DeepSeek 的回應內容...", height=300)
        
        if cleaned_text:
            word_count = len(cleaned_text)
            st.success(f"✅ 已接收 {word_count} 字的筆記！")
            
            # 下載按鈕
            file_name = f"{subject}_Cleaned_Notes.txt"
            st.download_button(
                label="📥 下載 .txt 檔案 (用於 NotebookLM)",
                data=cleaned_content if 'cleaned_content' in locals() else cleaned_text,
                file_name=file_name,
                mime="text/plain"
            )
            st.info("👉 下一步：將此 .txt 上傳至 NotebookLM 生成 Audio，然後到「智能温習室」使用。")

# ==========================================
# TAB 2: 智能温習室 (Study Room) - 保持不變
# ==========================================
with tab_study:
    st.header(f"🎓 {subject} - 衝刺模式")
    
    col_input, col_main = st.columns([1, 2])
    with col_input:
        st.markdown("### 載入資源")
        # 這裡只需要簡單的 txt 和 mp3 上傳
        notes_file = st.file_uploader("上傳剛才下載的筆記 (.txt)", type=["txt", "md"], key="notes")
        audio_file = st.file_uploader("上傳 NotebookLM 音檔 (.mp3)", type=["mp3", "wav"], key="audio")
        
        notes_text = ""
        if notes_file:
             notes_text = notes_file.read().decode("utf-8")
    
    with col_main:
        if not notes_text:
            st.info("👈 請先上傳筆記")
        else:
            if not client:
                 st.error("⚠️ 請輸入 API Key 才能使用 AI 問答功能")
                 st.stop()
                 
            sub_tab1, sub_tab2, sub_tab3 = st.tabs(["🎧 聽覺學習", "💬 導師問答", "✍️ 模擬試卷"])
            
            with sub_tab1:
                st.subheader("NotebookLM Podcast")
                if audio_file:
                    st.audio(audio_file)
                else:
                    st.warning("未上傳音頻")
                with st.expander("查看筆記內容"):
                    st.markdown(notes_text)

            with sub_tab2:
                st.subheader("AI 導師")
                if "messages" not in st.session_state:
                    st.session_state.messages = []
                for msg in st.session_state.messages:
                    st.chat_message(msg["role"]).write(msg["content"])
                
                if user_input := st.chat_input("輸入問題..."):
                    st.session_state.messages.append({"role": "user", "content": user_input})
                    st.chat_message("user").write(user_input)
                    with st.chat_message("assistant"):
                        rag_prompt = f"你是 DSE 導師。根據筆記回答 (廣東話)：\n{notes_text[:10000]}"
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

            with sub_tab3:
                if st.button("生成題目"):
                     with st.spinner("出卷中..."):
                        res = client.chat.completions.create(
                            model="deepseek-chat",
                            messages=[{"role": "user", "content": f"根據筆記出 DSE 題目：{notes_text[:5000]}"}]
                        )
                        st.markdown(res.choices[0].message.content)        return f"讀取檔案錯誤 ({file_type}): {str(e)}"
        
    return text
