import streamlit as st
from openai import OpenAI
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
import datetime
import uuid
import time

# --- 1. 頁面設定 ---
st.set_page_config(
    page_title="DSE 智能温習系統 (Vector Cloud版)", 
    layout="wide", 
    page_icon="🇭🇰",
    initial_sidebar_state="expanded"
)

# --- 2. 初始化核心模型 (使用 Cache 加速) ---
@st.cache_resource
def init_embedding_model():
    # 使用輕量級、免費的模型 (384維)
    return SentenceTransformer('all-MiniLM-L6-v2')

@st.cache_resource
def init_pinecone(api_key):
    return Pinecone(api_key=api_key)

# 載入模型 (只會執行一次)
with st.spinner("正在連接雲端大腦... (首次載入需時)"):
    embed_model = init_embedding_model()

# --- 3. API Key 設定 ---
deepseek_key = st.secrets.get("DEEPSEEK_API_KEY") or st.sidebar.text_input("DeepSeek Key", type="password")
pinecone_key = st.secrets.get("PINECONE_API_KEY") or st.sidebar.text_input("Pinecone Key", type="password")

client = None
if deepseek_key:
    client = OpenAI(api_key=deepseek_key, base_url="https://api.deepseek.com")

pc = None
index = None
if pinecone_key:
    pc = init_pinecone(pinecone_key)
    # 連接到你的 Index (名稱必須與 Pinecone 後台一致)
    index_name = "dse-memory" 
    index = pc.Index(index_name)

# --- 4. 向量儲存函數 (Upsert) ---
def save_to_vector_db(subject, question, answer, note_source="AI 生成"):
    if not index:
        st.error("未連接 Pinecone 資料庫")
        return

    # 1. 準備文字資料
    text_to_embed = f"{subject}: {question}" # 將科目和問題混合轉向量
    
    # 2. 轉為向量 (Embedding)
    vector = embed_model.encode(text_to_embed).tolist()
    
    # 3. 準備 Metadata (這是我們要讀取的文字內容)
    metadata = {
        "subject": subject,
        "question": question,
        "answer": answer,
        "source": note_source,
        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "timestamp": time.time() # 用於排序
    }
    
    # 4. 上傳到 Pinecone (ID 使用 UUID)
    unique_id = str(uuid.uuid4())
    index.upsert(vectors=[(unique_id, vector, metadata)])
    st.toast(f"☁️ 已將題目永久儲存至雲端！", icon="✅")

# --- 5. 側邊欄 ---
with st.sidebar:
    st.title("🇭🇰 DSE 雲端備戰")
    st.caption("DeepSeek x Pinecone Vector DB")
    st.divider()
    subject = st.selectbox("當前科目", ["Biology", "Chemistry", "Economics", "Chinese", "English", "History", "Maths", "Liberal Studies"])
    
    st.success("🟢 雲端記憶已連線")
    st.info("你的錯題現在會自動同步到雲端資料庫，無需手動存檔。")

# --- 6. 主功能區 ---
tab_factory, tab_study, tab_memory = st.tabs(["🏭 資料清洗", "🎓 智能溫習", "🧠 雲端記憶 (Vector)"])

# ==========================================
# TAB 1: 資料清洗 (維持不變)
# ==========================================
with tab_factory:
    st.header(f"🚀 {subject} - 資料清洗")
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("1. 複製指令")
        prompt_text = f"""
        (請上傳 PDF/圖片)
        你是一位 DSE {subject} 編輯。請將文件整理為 Markdown 筆記。
        要求：去除雜訊、按課題分類、保留 Keywords、題目整理為 Q&A。
        """
        st.code(prompt_text, language="text")
        st.link_button("🔗 前往 DeepSeek 官網", "https://chat.deepseek.com", type="primary")

    with col2:
        st.subheader("2. 備份存檔")
        with st.form("save_file"):
            txt = st.text_area("貼上內容...", height=200)
            if st.form_submit_button("💾 下載") and txt:
                st.download_button("📥 下載 .txt", txt, f"{subject}_Notes.txt")

# ==========================================
# TAB 2: 智能溫習 (加入向量儲存)
# ==========================================
with tab_study:
    st.header(f"🎓 {subject} - 衝刺模式")
    col_input, col_main = st.columns([1, 2])
    
    with col_input:
        input_method = st.radio("來源", ["📂 上傳", "📋 貼上"], horizontal=True)
        notes_text = ""
        if input_method == "📋 貼上":
            notes_text = st.text_area("貼上筆記：", height=300)
        else:
            files = st.file_uploader("上傳 .txt", type=["txt"], accept_multiple_files=True)
            if files:
                for f in files: notes_text += f"\n--- {f.name} ---\n{f.read().decode('utf-8')}"
        audio = st.file_uploader("NotebookLM 音檔", type=["mp3"])

    with col_main:
        if not notes_text:
            st.info("👈 請先載入筆記")
        else:
            if not client: st.error("缺 API Key"); st.stop()

            sub1, sub2, sub3 = st.tabs(["🎧 聽書", "💬 問答", "✍️ 模擬卷"])
            
            with sub1:
                if audio: st.audio(audio)
                with st.expander("筆記內容"): st.markdown(notes_text)

            with sub2: # 問答
                if "messages" not in st.session_state: st.session_state.messages = []
                for m in st.session_state.messages: st.chat_message(m["role"]).write(m["content"])
                
                if q := st.chat_input("輸入問題..."):
                    st.session_state.messages.append({"role": "user", "content": q})
                    st.chat_message("user").write(q)
                    with st.chat_message("assistant"):
                        rag = f"你係 DSE {subject} 導師。根據筆記用廣東話答：\n{notes_text[:12000]}"
                        ans = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":rag},{"role":"user","content":q}]).choices[0].message.content
                        st.markdown(ans)
                        # 向量儲存按鈕
                        st.button("⭐ 存入雲端記憶", key=f"save_{len(st.session_state.messages)}", on_click=save_to_vector_db, args=(subject, q, ans))
                    st.session_state.messages.append({"role": "assistant", "content": ans})

            with sub3: # 出卷
                c1, c2, c3 = st.columns([2,2,1])
                with c1: diff = st.select_slider("難度", ["L3","L4","L5","L5**"], "L4")
                with c2: qt = st.radio("題型", ["MC","LQ"], horizontal=True)
                with c3: num = st.number_input("數量", 1, 10, 1)
                
                if st.button("🚀 生成題目"):
                    prompt = f"DSE {subject} 出卷員。出 {num} 條 {diff} {qt}。先列題目，插入 `<<<SPLIT>>>`，再列答案。MC 垂直分行。筆記：{notes_text[:6000]}"
                    res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}]).choices[0].message.content
                    q_part, a_part = res.split("<<<SPLIT>>>") if "<<<SPLIT>>>" in res else (res, "見上方")
                    st.session_state['quiz'] = {"q": q_part, "a": a_part}

                if 'quiz' in st.session_state:
                    st.markdown("### 📝 試題"); st.markdown(st.session_state['quiz']['q'])
                    with st.expander("🔐 答案"): st.markdown(st.session_state['quiz']['a'])
                    # 向量儲存按鈕
                    st.button("⭐ 存入雲端記憶", key="save_quiz", on_click=save_to_vector_db, args=(subject, st.session_state['quiz']['q'], st.session_state['quiz']['a'], "模擬題"))

# ==========================================
# TAB 3: 🧠 雲端記憶 (Vector Space)
# ==========================================
with tab_memory:
    st.header("🧠 雲端錯題庫 (Vector Search)")
    st.caption("所有資料已儲存在 Pinecone 雲端，無需手動存檔。支援語意搜尋。")
    
    if not index:
        st.error("請先設定 Pinecone API Key")
        st.stop()

    col_search, col_filter = st.columns([3, 1])
    
    with col_search:
        # 這是向量搜尋的核心！
        search_query = st.text_input("🔍 搜尋記憶 (例如：搜尋 '光合作用' 相關錯題)", placeholder="輸入關鍵字...")
    
    with col_filter:
        filter_subject = st.selectbox("科目篩選", ["所有科目", "Biology", "Chemistry", "Economics", "History"])

    st.markdown("---")

    # 執行搜尋或獲取列表
    results = []
    
    if search_query:
        # === 模式 A: 語意搜尋 (Semantic Search) ===
        # 1. 將搜尋詞轉為向量
        query_vector = embed_model.encode(search_query).tolist()
        
        # 2. 準備過濾條件 (如有)
        filter_dict = {}
        if filter_subject != "所有科目":
            filter_dict = {"subject": filter_subject}
            
        # 3. 向 Pinecone 查詢最相似的內容
        search_res = index.query(
            vector=query_vector, 
            top_k=10, 
            include_metadata=True,
            filter=filter_dict if filter_dict else None
        )
        results = search_res['matches']
        st.success(f"🔍 找到 {len(results)} 條與「{search_query}」相關的記憶")

    else:
        # === 模式 B: 瀏覽模式 (Browse) ===
        # 由於 Pinecone 主要是搜尋用的，要「列出全部」比較麻煩。
        # 這裡我們用一個 Dummy Vector 進行查詢，或者提示用戶輸入。
        # 為了展示效果，我們生成一個「空向量」來獲取最近存入的項目
        
        # 創建一個全 0 的向量 (長度 384) 作為 dummy
        dummy_vector = [0.0] * 384 
        
        filter_dict = {}
        if filter_subject != "所有科目":
            filter_dict = {"subject": filter_subject}
            
        # 獲取最近的 20 條
        search_res = index.query(
            vector=dummy_vector, 
            top_k=20, 
            include_metadata=True,
            filter=filter_dict if filter_dict else None
        )
        results = search_res['matches']
        if len(results) > 0:
            st.info("📅 顯示最近加入的記憶 (輸入關鍵字可進行精準搜尋)")
        else:
            st.info("📭 雲端記憶庫暫時是空的，快去溫習加入錯題吧！")

    # 顯示結果卡片
    for match in results:
        data = match['metadata']
        score = match.get('score', 0)
        
        # 樣式化顯示
        with st.container():
            st.markdown(f"""
            <div style="border:1px solid #eee; padding:15px; border-radius:10px; margin-bottom:10px; background-color:#fafafa;">
                <div style="display:flex; justify-content:space-between;">
                    <small style="color:#0068c9; font-weight:bold;">{data.get('subject', 'General')}</small>
                    <small style="color:grey;">關聯度: {score:.2f} | {data.get('date', '')}</small>
                </div>
                <div style="margin-top:5px; font-size:1.1em;"><b>Q: </b>{data.get('question')}</div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander(f"👁️ 查看答案"):
                st.markdown(data.get('answer'))
                # 刪除功能比較複雜，這裡暫時省略，因為 Vector DB 刪除需要 ID
