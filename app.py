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
    st.markdown("利用 DeepSeek 官網處理掃描檔、手寫筆記或亂碼 PDF。")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("1. 複製指令 (Prompt)")
        st.write("點擊右上角複製按鈕，將指令貼給 DeepSeek：")
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
        st.link_button("🔗 前往 DeepSeek 官網 (chat.deepseek.com)", "https://chat.deepseek.com", type="primary")

    with col2:
        st.subheader("2. (選填) 備份存檔")
        st.write("如果你想把整理好的筆記存成檔案，可以在這裡貼上並下載：")
        
        # 使用 Form 防止誤觸
        with st.form("save_file_form"):
            text_to_save = st.text_area("貼上 DeepSeek 內容...", height=200)
            submitted = st.form_submit_button("💾 下載 .txt 檔")
        
        if submitted and text_to_save:
            st.success(f"已接收 {len(text_to_save)} 字！")
            st.download_button(
                label="📥 點擊下載",
                data=text_to_save,
                file_name=f"{subject}_Cleaned_Notes.txt",
                mime="text/plain"
            )

# ==========================================
# TAB 2: 智能温習室 (Study Room)
# ==========================================
with tab_study:
    st.header(f"🎓 {subject} - 衝刺模式")
    
    col_input, col_main = st.columns([1, 2])
    
    # --- 左側：資源輸入區 ---
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
                 st.error("⚠️ 未偵測到 API Key。請在 Secrets 設定。")
                 st.stop()
                 
            st.caption(f"✅ 已載入筆記內容 (共 {len(notes_text)} 字)")

            sub_tab1, sub_tab2, sub_tab3 = st.tabs(["🎧 多媒體學習", "💬 導師問答", "✍️ 模擬試卷"])
            
            # --- Sub Tab 1: 聽覺學習 ---
            with sub_tab1:
                st.subheader("🔊 NotebookLM Audio")
                if audio_file:
                    st.audio(audio_file)
                else:
                    st.warning("尚未上傳音頻 (可略過)")
                
                with st.expander("📖 查看完整筆記內容", expanded=False):
                    st.markdown(notes_text)

            # --- Sub Tab 2: AI 導師問答 ---
            with sub_tab2:
                st.subheader("💬 AI 導師")
                
                if "messages" not in st.session_state:
                    st.session_state.messages = []

                for msg in st.session_state.messages:
                    st.chat_message(msg["role"]).write(msg["content"])
                
                if user_input := st.chat_input("輸入問題 (e.g., 解釋下呢段)..."):
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

            # --- Sub Tab 3: 模擬試卷 (升級版) ---
            with sub_tab3:
                st.subheader("🔥 題目生成器")
                
                # 第一行：設定區
                row1_col1, row1_col2, row1_col3 = st.columns([2, 2, 1])
                
                with row1_col1:
                    diff = st.select_slider("難度選擇", options=["Level 3", "Level 4", "Level 5", "Level 5**"], value="Level 4")
                
                with row1_col2:
                    q_type = st.radio("題型", ["MC (多項選擇)", "LQ (長題目)"], horizontal=True)
                
                with row1_col3:
                    # 數量輸入：如果沒輸入(預設)，就是 1 即逐條
                    num_questions = st.number_input("題目數量", min_value=1, max_value=20, value=1, step=1)

                st.markdown("---")

                if st.button(f"🚀 生成 {num_questions} 條題目"):
                     with st.spinner(f"DeepSeek 正在參考筆記，設計 {num_questions} 條題目..."):
                        
                        # Prompt Engineering: 強制垂直排列與有序生成
                        gen_prompt = f"""
                        角色：香港考評局 DSE {subject} 出卷員。
                        任務：根據提供的筆記內容，設計 **{num_questions} 條** {diff} 程度的 {q_type}。
                        
                        【極重要格式要求】：
                        1. **題目與答案分離**：請先列出所有題目 (Question Paper)，最後才列出答案 (Marking Scheme)。
                        2. **MC 格式**：
                           - 選項 (A, B, C, D) 必須 **垂直分行排列**。
                           - 不要將選項擠在同一行。
                           - 格式範例：
                             1. 題目...
                                A. 選項一
                                B. 選項二
                                C. 選項三
                                D. 選項四
                        
                        3. **LQ 格式**：請標註分數 (e.g., [4 marks])。
                        
                        筆記內容範圍：{notes_text[:6000]}
                        """
                        
                        try:
                            # 呼叫 API
                            response = client.chat.completions.create(
                                model="deepseek-chat",
                                messages=[{"role": "user", "content": gen_prompt}]
                            )
                            result_text = response.choices[0].message.content
                            
                            st.success("✅ 出卷完成！")
                            
                            # 顯示結果
                            st.markdown("### 📝 模擬試題")
                            st.markdown(result_text)
                            
                            st.info("💡 提示：答案通常位於試題的下方 (Marking Scheme 部分)")

                        except Exception as e:
                            st.error(f"生成失敗: {e}")
