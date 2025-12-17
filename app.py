import streamlit as st
from openai import OpenAI
import json
import datetime
import uuid

# --- 1. 頁面設定 ---
st.set_page_config(
    page_title="DSE 智能温習系統 (Pro版)", 
    layout="wide", 
    page_icon="🇭🇰",
    initial_sidebar_state="expanded"
)

# --- 2. Session State 初始化 (用於儲存錯題) ---
if "review_list" not in st.session_state:
    st.session_state.review_list = []

# --- 3. 輔助函數 ---
def save_to_review(subject, question, answer, note_source="AI 生成"):
    """將題目加入重溫列表"""
    item = {
        "id": str(uuid.uuid4()),
        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "subject": subject,
        "question": question,
        "answer": answer,
        "source": note_source,
        "status": "New" # 用於標記熟練度 (New, Learning, Mastered)
    }
    st.session_state.review_list.append(item)
    st.toast(f"✅ 已加入 {subject} 重溫列表！", icon="⭐")

# --- 4. API Key 設定 ---
api_key = None
if "DEEPSEEK_API_KEY" in st.secrets:
    api_key = st.secrets["DEEPSEEK_API_KEY"]
else:
    api_key = st.sidebar.text_input("DeepSeek API Key", type="password")

client = None
if api_key:
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

# --- 5. 側邊欄：設定與進度管理 ---
with st.sidebar:
    st.title("🇭🇰 DSE 備戰中心")
    st.caption("溫習 -> 儲存 -> 重溫 (Spaced Repetition)")
    st.divider()
    
    subject = st.selectbox(
        "當前科目", 
        ["Biology", "Chemistry", "Economics", "Chinese", "English", "History", "Maths", "Liberal Studies"]
    )

    st.markdown("---")
    st.markdown("### 💾 進度存取")
    st.caption("關閉網頁後資料會消失，請下載備份！")
    
    # 匯出按鈕
    if st.session_state.review_list:
        json_data = json.dumps(st.session_state.review_list, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 下載重溫進度 (.json)",
            data=json_data,
            file_name=f"dse_review_data_{datetime.datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json"
        )
    
    # 匯入按鈕
    uploaded_history = st.file_uploader("📂 載入上次進度", type=["json"])
    if uploaded_history:
        try:
            data = json.load(uploaded_history)
            # 合併清單，避免重複 (簡單以 ID 判斷，若無 ID 則視為新)
            existing_ids = {item.get("id") for item in st.session_state.review_list}
            count = 0
            for item in data:
                if item.get("id") not in existing_ids:
                    st.session_state.review_list.append(item)
                    count += 1
            if count > 0:
                st.success(f"成功載入 {count} 條舊紀錄！")
        except Exception as e:
            st.error("檔案格式錯誤")

# --- 6. 主功能區 ---
tab_factory, tab_study, tab_review = st.tabs(["🏭 資料清洗", "🎓 智能溫習", "🧠 錯題重溫"])

# ==========================================
# TAB 1: 官網資料清洗
# ==========================================
with tab_factory:
    st.header(f"🚀 {subject} - 資料清洗橋樑")
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("1. 複製指令")
        prompt_text = f"""
        (請上傳 PDF/圖片)
        你是一位 DSE {subject} 教材編輯。請將文件整理為 Markdown 筆記。
        要求：
        1. 去除雜訊 (頁碼/廣告)。
        2. 按課題 (Topic) 分類。
        3. 保留 Keywords。
        4. 題目整理為 Q: ... A: ... 格式。
        """
        st.code(prompt_text, language="text")
        st.link_button("🔗 前往 DeepSeek 官網", "https://chat.deepseek.com", type="primary")

    with col2:
        st.subheader("2. 備份存檔")
        with st.form("save_file_form"):
            text_to_save = st.text_area("貼上 DeepSeek 內容...", height=200)
            submitted = st.form_submit_button("💾 下載 .txt 檔")
        if submitted and text_to_save:
            st.download_button(
                label="📥 下載筆記",
                data=text_to_save,
                file_name=f"{subject}_Cleaned_Notes.txt",
                mime="text/plain"
            )

# ==========================================
# TAB 2: 智能溫習室 (加入儲存按鈕)
# ==========================================
with tab_study:
    st.header(f"🎓 {subject} - 衝刺模式")
    col_input, col_main = st.columns([1, 2])
    
    with col_input:
        input_method = st.radio("筆記來源：", ["📂 上傳檔案", "📋 貼上文字"], horizontal=True)
        notes_text = ""
        if input_method == "📋 貼上文字":
            notes_text = st.text_area("貼上筆記內容：", height=300)
        else:
            uploaded_files = st.file_uploader("上傳筆記 (.txt)", type=["txt", "md"], accept_multiple_files=True)
            if uploaded_files:
                for f in uploaded_files:
                    notes_text += f"\n\n--- {f.name} ---\n{f.read().decode('utf-8')}"
        st.markdown("---")
        audio_file = st.file_uploader("上傳 NotebookLM 音檔", type=["mp3", "wav"])

    with col_main:
        if not notes_text:
            st.info("👈 請先載入筆記")
        else:
            if not client:
                 st.error("⚠️ 未偵測到 API Key")
                 st.stop()

            sub1, sub2, sub3 = st.tabs(["🎧 聽覺學習", "💬 問答 (可儲存)", "✍️ 模擬卷 (可儲存)"])
            
            # --- 聽覺學習 ---
            with sub1:
                if audio_file: st.audio(audio_file)
                with st.expander("查看筆記"): st.markdown(notes_text)

            # --- 問答 (儲存功能) ---
            with sub2:
                if "messages" not in st.session_state: st.session_state.messages = []
                for msg in st.session_state.messages: st.chat_message(msg["role"]).write(msg["content"])
                
                if user_input := st.chat_input("輸入問題..."):
                    st.session_state.messages.append({"role": "user", "content": user_input})
                    st.chat_message("user").write(user_input)
                    with st.chat_message("assistant"):
                        rag_prompt = f"你係 DSE {subject} 導師。根據筆記用廣東話回答：\n{notes_text[:12000]}"
                        response = client.chat.completions.create(
                            model="deepseek-chat",
                            messages=[{"role": "system", "content": rag_prompt}, {"role": "user", "content": user_input}]
                        ).choices[0].message.content
                        st.markdown(response)
                        
                        # ⭐ 儲存按鈕
                        st.button(
                            "⭐ 加入重溫列表", 
                            key=f"save_qa_{len(st.session_state.messages)}",
                            on_click=save_to_review,
                            args=(subject, user_input, response)
                        )
                    st.session_state.messages.append({"role": "assistant", "content": response})

            # --- 模擬卷 (儲存功能) ---
            with sub3:
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1: diff = st.select_slider("難度", options=["L3", "L4", "L5", "L5**"], value="L4")
                with c2: q_type = st.radio("題型", ["MC", "LQ"], horizontal=True)
                with c3: num = st.number_input("數量", 1, 10, 1)
                
                if st.button("🚀 生成題目"):
                    with st.spinner("出卷中..."):
                        sep = "<<<SPLIT>>>"
                        prompt = f"""
                        DSE {subject} 出卷員。根據筆記出 {num} 條 {diff} 的 {q_type}。
                        極重要：先列題目，插入 `{sep}`，再列答案。
                        MC 選項垂直分行。
                        筆記：{notes_text[:6000]}
                        """
                        res = client.chat.completions.create(
                            model="deepseek-chat",
                            messages=[{"role": "user", "content": prompt}]
                        ).choices[0].message.content
                        
                        if sep in res:
                            q_part, a_part = res.split(sep)
                        else:
                            q_part, a_part = res, "未能自動分離，請見上方"
                        
                        st.session_state['last_quiz'] = {"q": q_part, "a": a_part}

                # 顯示生成的題目 (如果有)
                if 'last_quiz' in st.session_state:
                    q_data = st.session_state['last_quiz']
                    st.markdown("### 📝 試題")
                    st.markdown(q_data['q'])
                    with st.expander("🔐 查看答案"):
                        st.markdown(q_data['a'])
                    
                    # ⭐ 儲存按鈕
                    st.button(
                        "⭐ 將此題儲存至錯題庫", 
                        key="save_quiz",
                        on_click=save_to_review,
                        args=(subject, q_data['q'], q_data['a'], f"{diff} {q_type} 模擬題")
                    )

# ==========================================
# TAB 3: 🧠 錯題重溫 (Spaced Repetition)
# ==========================================
with tab_review:
    st.header("🧠 錯題重溫 (Spaced Repetition)")
    st.caption("利用間隔重複法，鞏固你的長期記憶。")
    
    # 1. 篩選器
    all_subjects = sorted(list(set([item['subject'] for item in st.session_state.review_list])))
    filter_col1, filter_col2 = st.columns([1, 3])
    with filter_col1:
        selected_subject = st.selectbox("篩選科目", ["所有科目"] + all_subjects)
    
    # 2. 獲取篩選後的列表
    filtered_list = [
        item for item in st.session_state.review_list 
        if selected_subject == "所有科目" or item['subject'] == selected_subject
    ]
    
    if not filtered_list:
        st.info("📭 暫無重溫記錄。請在「智能溫習」分頁按 ⭐ 按鈕加入題目。")
    else:
        st.success(f"找到 {len(filtered_list)} 條重溫項目")
        
        # 3. 顯示卡片 (反序顯示，最新的在最上面)
        for index, item in enumerate(reversed(filtered_list)):
            with st.container():
                # 卡片樣式
                st.markdown(f"""
                <div style="border:1px solid #ddd; padding:15px; border-radius:10px; margin-bottom:10px;">
                    <small style="color:grey;">📅 {item['date']} | 📚 {item['subject']} | 來源: {item.get('source', 'AI')}</small>
                    <h4>❓ 問題：</h4>
                    <div style="margin-bottom:10px;">{item['question']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # 間隔重複核心：隱藏答案
                expander_title = f"👁️ 顯示答案 (Card #{len(filtered_list)-index})"
                with st.expander(expander_title):
                    st.markdown("#### ✅ 答案與解析：")
                    st.markdown(item['answer'])
                    
                    # 管理按鈕
                    c1, c2 = st.columns([1, 5])
                    with c1:
                        if st.button("🗑️ 移除", key=f"del_{item['id']}"):
                            st.session_state.review_list = [x for x in st.session_state.review_list if x['id'] != item['id']]
                            st.rerun() # 立即刷新頁面
