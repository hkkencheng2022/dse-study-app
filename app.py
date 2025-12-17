import streamlit as st
from openai import OpenAI

# --- 1. 頁面設定 ---
st.set_page_config(
    page_title="DSE 智能温習系統 (Web版)", 
    layout="wide", 
    page_icon="🇭🇰",
    initial_sidebar_state="expanded"
)

# --- 2. API Key 設定 (優先從 Secrets 讀取) ---
api_key = None
if "DEEPSEEK_API_KEY" in st.secrets:
    api_key = st.secrets["DEEPSEEK_API_KEY"]
else:
    api_key = st.sidebar.text_input("DeepSeek API Key (用於 Tab 2)", type="password")

# 初始化 Client
client = None
if api_key:
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

# --- 3. 側邊欄 ---
with st.sidebar:
    st.title("🇭🇰 DSE 備戰中心")
    st.caption("官網清洗 -> 貼上筆記 -> 智能温習")
    st.divider()
    
    subject = st.selectbox(
        "當前科目", 
        ["Biology", "Chemistry", "Economics", "Chinese", "English", "History", "Maths", "Liberal Studies"]
    )
    
    st.info("""
    **💡 極速流程：**
    1. **Tab 1:** 獲取指令 -> 去 DeepSeek 官網整理 -> 複製結果。
    2. **Tab 2:** 選擇「直接貼上」 -> 貼上文字。
    3. (選填) 上傳 NotebookLM 的音檔。
    4. 開始温習！
    """)

# --- 4. 主功能區 ---
tab_factory, tab_study = st.tabs(["🏭 步驟一：官網資料清洗", "🎓 步驟二：智能温習室"])

# ==========================================
# TAB 1: 官網資料清洗 (The Bridge)
# ==========================================
with tab_factory:
    st.header(f"🚀 {subject} - 資料清洗橋樑")
    st.markdown("利用 DeepSeek 官網處理掃描檔或亂碼 PDF。")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("1. 複製指令 (Prompt)")
        prompt_text = f"""
        (請上傳附件 PDF/圖片)
        你是一位香港 DSE {subject} 的專業教材編輯。
        請閱讀我上傳的文件，並將其整理為一份「結構清晰」的 Markdown 筆記。
        
        要求：
        1. 【去蕪存菁】：去除頁碼、廣告、重複的考試規則。
        2. 【結構化】：按課題 (Topic) 使用 # 和 ## 標題分類。
        3. 【關鍵詞】：保留所有 DSE 專用術語 (Keywords)。
        4. 【題目】：如果內容包含題目與答案，請整理為 Q: ... A: ... 格式。
        5. 【輸出】：直接輸出整理後的內容，不需要開場白。
        """
        st.code(prompt_text, language="text")
        st.link_button("🔗 前往 DeepSeek 官網", "https://chat.deepseek.com", type="primary")

    with col2:
        st.subheader("2. (選填) 備份存檔")
        st.write("如果你想把整理好的筆記存成檔案，可以在這裡貼上並下載：")
        with st.form("save_file_form"):
            text_to_save = st.text_area("貼上 DeepSeek 內容...", height=200)
            submitted = st.form_submit_button("💾 下載 .txt 檔")
        
        if submitted and text_to_save:
            st.download_button(
                label="📥 點擊下載",
                data=text_to_save,
                file_name=f"{subject}_Cleaned_Notes.txt",
                mime="text/plain"
            )

# ==========================================
# TAB 2: 智能温習室 (Study Room) - 已新增貼上功能
# ==========================================
with tab_study:
    st.header(f"🎓 {subject} - 衝刺模式")
    
    col_input, col_main = st.columns([1, 2])
    
    # --- 左側：資源輸入區 (修改重點) ---
    with col_input:
        st.markdown("### 📥 載入溫習資源")
        
        # 1. 筆記輸入方式選擇
        input_method = st.radio(
            "選擇筆記來源：", 
            ["📋 直接貼上文字", "📂 上傳 .txt 檔案"], 
            horizontal=True
        )
        
        notes_text = ""
        
        if input_method == "📋 直接貼上文字":
            notes_text = st.text_area(
                "請在此貼上 DeepSeek 整理好的筆記內容：", 
                height=300,
                placeholder="在此貼上 (# 課題...)"
            )
        else:
            notes_file = st.file_uploader("上傳筆記檔案", type=["txt", "md"])
            if notes_file:
                notes_text = notes_file.read().decode("utf-8")

        # 2. 音頻上傳 (始終保留)
        st.markdown("---")
        audio_file = st.file_uploader("上傳 NotebookLM 音檔 (選填)", type=["mp3", "wav"])
    
    # --- 右側：主要功能區 ---
    with col_main:
        if not notes_text:
            st.info("👈 請在左側「貼上文字」或「上傳檔案」以解鎖功能。")
        else:
            if not client:
                 st.error("⚠️ 未偵測到 API Key。")
                 st.stop()
                 
            # 顯示目前讀取到的字數
            st.caption(f"✅ 已載入筆記內容 (共 {len(notes_text)} 字)")

            sub_tab1, sub_tab2, sub_tab3 = st.tabs(["🎧 多媒體學習", "💬 導師問答", "✍️ 模擬試卷"])
            
            # --- 1. 聽覺學習 ---
            with sub_tab1:
                st.subheader("🔊 NotebookLM Audio")
                if audio_file:
                    st.audio(audio_file)
                else:
                    st.warning("尚未上傳音頻 (可略過)")
                
                with st.expander("📖 查看完整筆記內容", expanded=False):
                    st.markdown(notes_text)

            # --- 2. AI 導師問答 ---
            with sub_tab2:
                st.subheader("💬 AI 導師")
                
                if "messages" not in st.session_state:
                    st.session_state.messages = []

                for msg in st.session_state.messages:
                    st.chat_message(msg["role"]).write(msg["content"])
                
                if user_input := st.chat_input("輸入問題..."):
                    st.session_state.messages.append({"role": "user", "content": user_input})
                    st.chat_message("user").write(user_input)
                    
                    with st.chat_message("assistant"):
                        rag_prompt = f"""
                        你是一位香港 DSE {subject} 導師。
                        請【嚴格根據以下筆記】回答學生問題，並使用【廣東話】。
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

            # --- 3. 模擬試卷 ---
            with sub_tab3:
                st.subheader("🔥 題目生成器")
                col_q1, col_q2 = st.columns(2)
                with col_q1:
                    diff = st.select_slider("難度", options=["Level 3", "Level 4", "Level 5**"], value="Level 4")
                with col_q2:
                    q_type = st.radio("題型", ["MC", "LQ"], horizontal=True)

                if st.button("🚀 生成題目"):
                     with st.spinner("出卷中..."):
                        gen_prompt = f"""
                        角色：DSE {subject} 出卷員。
                        任務：根據筆記設計一條 {diff} 的 {q_type}。
                        要求：清晰題目、Marking Scheme、解釋。
                        筆記：{notes_text[:5000]}
                        """
                        res = client.chat.completions.create(
                            model="deepseek-chat",
                            messages=[{"role": "user", "content": gen_prompt}]
                        )
                        st.markdown(res.choices[0].message.content)        1. 【去蕪存菁】：去除頁碼、廣告、重複的考試規則。
        2. 【結構化】：按課題 (Topic) 使用 # 和 ## 標題分類。
        3. 【關鍵詞】：保留所有 DSE 專用術語 (Keywords)，不要過度簡化。
        4. 【題目】：如果內容包含題目與答案，請整理為 Q: ... A: ... 格式。
        5. 【輸出】：直接輸出整理後的內容，不需要開場白。
        """
        st.code(prompt_text, language="text")
        
        st.markdown("---")
        st.subheader("2. 前往 DeepSeek 官網")
        st.markdown("帶著複製好的指令和你的檔案，前往官網處理。")
        st.link_button("🔗 打開 chat.deepseek.com", "https://chat.deepseek.com", type="primary")

    # 右欄：接收結果 (使用 st.form 實現按鈕觸發)
    with col2:
        st.subheader("3. 接收成果")
        st.write("DeepSeek 整理好後，請將**所有文字複製**，貼在下方並按確認：")
        
        # --- 這裡使用了 Form 表單 ---
        with st.form("clean_data_form"):
            cleaned_text_input = st.text_area("在此貼上 DeepSeek 的回應內容...", height=350)
            
            # 這是你要的「執行按鈕」
            submitted = st.form_submit_button("✅ 確認並建立檔案")
            
        # 當按鈕被按下後執行
        if submitted:
            if cleaned_text_input.strip():
                word_count = len(cleaned_text_input)
                st.success(f"🎉 成功接收！共 {word_count} 字。")
                st.balloons() # 給點鼓勵效果
                
                # 下載按鈕
                file_name = f"{subject}_Cleaned_Notes.txt"
                st.download_button(
                    label="📥 點擊下載 .txt 檔案 (用於 NotebookLM)",
                    data=cleaned_text_input,
                    file_name=file_name,
                    mime="text/plain"
                )
                st.info("👉 現在，請將此檔案上傳至 NotebookLM 生成 Audio，然後到「步驟二」使用。")
            else:
                st.error("⚠️ 內容是空的！請先貼上文字再按確認。")

# ==========================================
# TAB 2: 智能温習室 (Study Room)
# ==========================================
with tab_study:
    st.header(f"🎓 {subject} - 衝刺模式")
    
    col_input, col_main = st.columns([1, 2])
    
    # 左側：資源上傳區
    with col_input:
        st.markdown("### 📥 載入溫習資源")
        st.caption("請上傳剛剛下載的 TXT 以及 NotebookLM 的 MP3")
        
        notes_file = st.file_uploader("1. 筆記檔案 (.txt/.md)", type=["txt", "md"], key="notes")
        audio_file = st.file_uploader("2. 導讀音檔 (.mp3/.wav)", type=["mp3", "wav"], key="audio")
        
        # 讀取文字內容
        notes_text = ""
        if notes_file:
             notes_text = notes_file.read().decode("utf-8")
    
    # 右側：主要功能區
    with col_main:
        if not notes_text:
            st.info("👈 請先在左側上傳筆記檔案以解鎖功能。")
        else:
            # 檢查 API Key
            if not client:
                 st.error("⚠️ 未偵測到 API Key。請在 Secrets 或 Sidebar 設定，才能使用 AI 問答。")
                 st.stop()
                 
            # 功能分頁
            sub_tab1, sub_tab2, sub_tab3 = st.tabs(["🎧 多媒體學習", "💬 導師問答", "✍️ 模擬試卷"])
            
            # --- 1. 聽覺學習 ---
            with sub_tab1:
                st.subheader("🔊 NotebookLM Audio Overview")
                if audio_file:
                    st.audio(audio_file)
                else:
                    st.warning("尚未上傳音頻 (建議配合 NotebookLM 使用)")
                
                st.divider()
                with st.expander("📖 查看完整筆記內容", expanded=False):
                    st.markdown(notes_text)

            # --- 2. AI 導師問答 ---
            with sub_tab2:
                st.subheader("💬 AI 導師 (DeepSeek)")
                st.caption("根據你的筆記內容，用廣東話為你解題。")
                
                # 初始化對話歷史
                if "messages" not in st.session_state:
                    st.session_state.messages = []

                # 顯示歷史訊息
                for msg in st.session_state.messages:
                    st.chat_message(msg["role"]).write(msg["content"])
                
                # 輸入框
                if user_input := st.chat_input("輸入問題 (例如: 解釋呢個 Concept)..."):
                    # 顯示用戶問題
                    st.session_state.messages.append({"role": "user", "content": user_input})
                    st.chat_message("user").write(user_input)
                    
                    # 呼叫 AI
                    with st.chat_message("assistant"):
                        rag_prompt = f"""
                        你是一位香港 DSE {subject} 科目的補習導師。
                        請【嚴格根據以下筆記內容】回答學生的問題。
                        
                        規則：
                        1. 必須使用【廣東話】口語。
                        2. 引用筆記中的關鍵字。
                        3. 若筆記未提及，請誠實告知。
                        
                        筆記內容：
                        {notes_text[:12000]}
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
                    
                    # 儲存 AI 回答
                    st.session_state.messages.append({"role": "assistant", "content": response})

            # --- 3. 模擬試卷 ---
            with sub_tab3:
                st.subheader("🔥 DSE 題目生成器")
                
                col_q1, col_q2 = st.columns(2)
                with col_q1:
                    diff_level = st.select_slider("難度", options=["Level 3", "Level 4", "Level 5", "Level 5**"], value="Level 4")
                with col_q2:
                    q_type = st.radio("題型", ["MC (多項選擇)", "LQ (長題目)"], horizontal=True)

                if st.button("🚀 生成題目"):
                     with st.spinner("DeepSeek 正在參考筆記出卷..."):
                        gen_prompt = f"""
                        角色：香港考評局 DSE {subject} 出卷員。
                        任務：根據提供的筆記內容，設計一條 {diff_level} 程度的 {q_type}。
                        
                        要求：
                        1. 題目內容清晰。
                        2. 提供標準答案 (Marking Scheme)。
                        3. 若是 MC，解釋每個選項。
                        
                        筆記內容：{notes_text[:5000]}
                        """
                        res = client.chat.completions.create(
                            model="deepseek-chat",
                            messages=[{"role": "user", "content": gen_prompt}]
                        )
                        st.markdown(res.choices[0].message.content)
