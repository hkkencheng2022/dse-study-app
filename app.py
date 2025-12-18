import streamlit as st
from openai import OpenAI
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
import streamlit.components.v1 as components
import datetime
import uuid
import time
import json
import random
import re

# --- 1. 頁面設定 ---
st.set_page_config(
    page_title="DSE 智能温習系統 (Answer Pro)", 
    layout="wide", 
    page_icon="🇭🇰",
    initial_sidebar_state="expanded"
)

# 注入 CSS (卡片風格 + 黃色高亮支援)
st.markdown("""
<style>
    .flashcard {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 30px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        text-align: center;
        transition: transform 0.2s;
    }
    .flashcard:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0,0,0,0.1);
    }
    .card-subject {
        font-size: 0.85em;
        font-weight: 600;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 15px;
    }
    .card-question {
        font-size: 1.4em;
        font-weight: 500;
        color: #333;
        line-height: 1.6;
        margin-bottom: 20px;
    }
    /* 自定義黃色高亮樣式 (讓 AI 呼叫) */
    .highlight-answer {
        color: #D4AC0D; /* 深金色，確保白底可讀 */
        font-weight: bold;
        background-color: #FFF9C4; /* 淡黃底色增加對比 */
        padding: 2px 6px;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 初始化核心模型 ---
@st.cache_resource
def init_embedding_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

@st.cache_resource
def init_pinecone(api_key):
    return Pinecone(api_key=api_key)

with st.spinner("正在啟動雲端連線..."):
    embed_model = init_embedding_model()

# --- 3. API Key 設定 ---
deepseek_key = st.secrets.get("DEEPSEEK_API_KEY")
pinecone_key = st.secrets.get("PINECONE_API_KEY")

# --- 4. 核心函數 ---

def clean_latex(text):
    if not text: return ""
    # 修復 LaTeX 格式
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text, flags=re.DOTALL)
    return text

def manual_save_to_cloud(subject, question, answer, note_type):
    if not index:
        st.error("❌ 未連接 Pinecone")
        return
    question = clean_latex(question)
    answer = clean_latex(answer)
    text_to_embed = f"{subject}: {question}"
    vector = embed_model.encode(text_to_embed).tolist()
    metadata = {
        "subject": subject, "question": question, "answer": answer,
        "type": note_type, "date_added": datetime.datetime.now().strftime("%Y-%m-%d"),
        "weight": 20.0, "timestamp": time.time()
    }
    unique_id = str(uuid.uuid4())
    try:
        index.upsert(vectors=[(unique_id, vector, metadata)])
        st.toast(f"☁️ 已存入【{subject}】！", icon="✅")
        if 'card_pool' in st.session_state: del st.session_state['card_pool']
    except Exception as e:
        st.error(f"上傳失敗: {e}")

def update_weight(item_id, rating):
    if not index: return
    new_weight = 20.0
    msg = ""
    if rating == 1:
        new_weight = 20.0
        msg = "⭕ 標記：需重溫"
    elif rating == 2:
        new_weight = 5.0
        msg = "⚠️ 標記：有點印象"
    elif rating == 3:
        new_weight = 1.0
        msg = "✅ 標記：已掌握"
    
    try:
        index.update(id=item_id, set_metadata={"weight": new_weight})
        st.toast(msg, icon="⚡")
        if 'current_card_data' in st.session_state:
            del st.session_state['current_card_data']
    except Exception as e:
        st.error(f"更新失敗: {e}")

def delete_from_cloud(item_id):
    if not index: return
    try:
        index.delete(ids=[item_id])
        st.toast("🗑️ 已刪除", icon="✅")
        if 'current_card_data' in st.session_state:
            del st.session_state['current_card_data']
        if 'card_pool' in st.session_state:
            del st.session_state['card_pool'] 
    except Exception as e:
        st.error(f"刪除失敗: {e}")

def skip_card():
    if 'current_card_data' in st.session_state:
        st.session_state['previous_card_id'] = st.session_state['current_card_data']['id']
        del st.session_state['current_card_data']

def copy_button_component(text_to_copy):
    js_text = json.dumps(text_to_copy)
    components.html(
        f"""
        <script>
        function copyToClipboard() {{
            const str = {js_text};
            const el = document.createElement('textarea');
            el.value = str;
            document.body.appendChild(el);
            el.select();
            document.execCommand('copy');
            document.body.removeChild(el);
            const btn = document.getElementById('copyBtn');
            btn.innerText = "✅ 複製成功！";
            btn.style.backgroundColor = "#4CAF50";
            setTimeout(() => {{ btn.innerText = "📋 點擊複製所有指令"; btn.style.backgroundColor = "#FF4B4B"; }}, 2000);
        }}
        </script>
        <button id="copyBtn" onclick="copyToClipboard()" style="width: 100%; background-color: #FF4B4B; color: white; border: none; padding: 12px 20px; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 16px;">📋 點擊複製所有指令</button>
        """, height=60
    )

# --- 5. 側邊欄 ---
with st.sidebar:
    st.title("🇭🇰 DSE 備戰中心")
    st.caption("Detailed Answer Mode")
    st.divider()
    if not deepseek_key: deepseek_key = st.text_input("DeepSeek Key", type="password")
    if not pinecone_key: pinecone_key = st.text_input("Pinecone Key", type="password")
    st.divider()
    current_subject = st.selectbox("當前温習科目", ["Biology", "Chemistry", "Economics", "Chinese", "English", "History", "Maths", "Liberal Studies"])

client = None
index = None
if deepseek_key: client = OpenAI(api_key=deepseek_key, base_url="https://api.deepseek.com")
if pinecone_key:
    try:
        pc = init_pinecone(pinecone_key)
        index = pc.Index("dse-memory")
        st.sidebar.success("🟢 雲端已連線")
    except Exception as e:
        st.sidebar.error(f"連線失敗: {e}")

# --- 6. 主功能區 ---
tab_factory, tab_study, tab_review = st.tabs(["🏭 資料清洗", "🎓 智能溫習", "🧠 抽卡溫習"])

# ==========================================
# TAB 1: 資料清洗
# ==========================================
with tab_factory:
    st.header(f"🚀 {current_subject} - 資料清洗")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("1. 獲取指令")
        prompt_text = f"""(請上傳 PDF/圖片) 你是一位 DSE {current_subject} 編輯..."""
        st.text_area("預覽", prompt_text, height=150)
        copy_button_component(prompt_text)
        st.link_button("🔗 前往 DeepSeek", "https://chat.deepseek.com", type="primary")
    with c2:
        st.subheader("2. 備份")
        with st.form("save"):
            txt = st.text_area("貼上內容...", height=250)
            if st.form_submit_button("💾 下載") and txt:
                st.download_button("📥 下載", txt, f"{current_subject}_Notes.txt")

# ==========================================
# TAB 2: 智能溫習 (Prompt 重點升級)
# ==========================================
with tab_study:
    st.header(f"🎓 {current_subject} - 衝刺模式")
    c_in, c_main = st.columns([1, 2])
    with c_in:
        method = st.radio("來源", ["📂 上傳", "📋 貼上"], horizontal=True)
        notes = ""
        if method == "📋 貼上": notes = st.text_area("貼上筆記：", height=300)
        else:
            files = st.file_uploader("上傳 .txt", type=["txt"], accept_multiple_files=True)
            if files:
                for f in files: notes += f"\n---\n{f.read().decode('utf-8')}"
        audio = st.file_uploader("音檔", type=["mp3"])
    with c_main:
        if not notes: st.info("👈 請先載入筆記")
        else:
            if not client: st.error("缺 API Key"); st.stop()
            s1, s2, s3 = st.tabs(["🎧 聽書", "💬 問答", "✍️ 模擬卷 (Answer Pro)"])
            
            with s1:
                if audio: st.audio(audio)
                with st.expander("筆記"): st.markdown(notes)
            
            with s2:
                default_lang_idx = 1 if current_subject == "English" else 0
                lang_choice = st.radio("回答語言", ["中文 (廣東話)", "English"], index=default_lang_idx, horizontal=True)

                if "messages" not in st.session_state: st.session_state.messages = []
                for m in st.session_state.messages: 
                    st.chat_message(m["role"]).write(clean_latex(m["content"]))
                
                if q := st.chat_input("輸入問題..."):
                    st.session_state.messages.append({"role": "user", "content": q})
                    st.chat_message("user").write(q)
                    with st.chat_message("assistant"):
                        lang_instruction = "用廣東話回答" if lang_choice == "中文 (廣東話)" else "Answer in English"
                        rag = f"DSE 導師。{lang_instruction}。數學公式單個 $ 包住。\n筆記：{notes[:12000]}"
                        ans = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":rag},{"role":"user","content":q}]).choices[0].message.content
                        
                        display_ans = clean_latex(ans)
                        st.markdown(display_ans)
                        st.button("☁️ 加入題庫", key=f"s_{len(st.session_state.messages)}", on_click=manual_save_to_cloud, args=(current_subject, q, ans, "問答"))
                    st.session_state.messages.append({"role": "assistant", "content": ans})
            
            # --- [重點修改] Tab 2 Sub 3: 模擬卷 Prompt ---
            with s3:
                st.subheader("設定出題參數")
                default_idx = 1 if current_subject == "English" else 0
                c1,c2,c3,c4 = st.columns([2,2,1,2])
                with c1: diff = st.select_slider("難度", ["L3","L4","L5","L5**"], "L4")
                with c2: qt = st.radio("題型", ["MC","LQ"], horizontal=True)
                with c3: num = st.number_input("數量", 1, 10, 1)
                with c4: lang = st.selectbox("語言", ["中文 (繁體)", "English"], index=default_idx)

                if st.button("🚀 生成題目"):
                    # 升級版 Prompt
                    prompt = f"""
                    角色：香港考評局 DSE {current_subject} 出卷員。
                    語言：請使用 **{lang}**。
                    任務：根據筆記，設計 **{num} 條** {diff} 程度的 {qt}。
                    
                    【極重要格式指令】：
                    1. **題目/答案分離**：先列出「試題卷 (Questions)」，插入 `<<<SPLIT>>>`，再列出「答案與詳解 (Marking Scheme)」。
                    
                    2. **MC 選項格式**：必須 **垂直分行**。
                       正確範例：
                       A. 選項一
                       B. 選項二
                    
                    3. **答案格式 (Highlight & Explanation)**：
                       - 必須提供 **【詳細解釋 (Explanation)】**，分析為何該答案正確，以及其他選項為何錯誤。
                       - **正確答案的關鍵字或選項** 必須使用 HTML 黃色高亮語法包住：
                         請使用: `<span class="highlight-answer">正確答案</span>`
                       - 例子：答案是 <span class="highlight-answer">A</span>。因為...
                    
                    4. **數學公式**：必須用單個 $ 包住 (例如 $x^2$)。
                    
                    筆記內容：{notes[:7000]}
                    """
                    
                    res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}]).choices[0].message.content
                    
                    q_p, a_p = res.split("<<<SPLIT>>>") if "<<<SPLIT>>>" in res else (res, "AI 未能自動分離答案，請見上方。")
                    st.session_state['q'] = {"q": q_p, "a": a_p}
                
                if 'q' in st.session_state:
                    quiz = st.session_state['q']
                    st.markdown("### 📝 試題")
                    st.markdown(clean_latex(quiz['q']))
                    
                    st.info("👇 完成作答後，點擊下方查看詳解")
                    with st.expander("🔐 查看答案與詳細解釋 (Marking Scheme)"): 
                        # 使用 unsafe_allow_html=True 讓黃色高亮生效
                        st.markdown(clean_latex(quiz['a']), unsafe_allow_html=True)
                        
                    st.button("☁️ 加入題庫", key="sq", on_click=manual_save_to_cloud, args=(current_subject, quiz['q'], quiz['a'], "模擬卷"))

# ==========================================
# TAB 3: 權重機率抽卡
# ==========================================
with tab_review:
    c_title, c_act = st.columns([4, 1])
    with c_title: st.subheader("🧠 抽卡溫習")
    with c_act: st.button("⏭️ 下一張", on_click=skip_card, type="primary", use_container_width=True)

    if not index: st.warning("⚠️ 請先設定 Pinecone Key"); st.stop()

    c_filt, c_space = st.columns([2, 3])
    with c_filt: f_sub = st.selectbox("📂 選擇學科", ["顯示全部", "Biology", "Chemistry", "Economics", "Chinese", "English", "History", "Maths"])
    
    if 'last_filter' not in st.session_state: st.session_state.last_filter = f_sub
    if st.session_state.last_filter != f_sub:
        if 'card_pool' in st.session_state: del st.session_state['card_pool']
        if 'current_card_data' in st.session_state: del st.session_state['current_card_data']
        st.session_state.last_filter = f_sub
        st.rerun()

    try:
        if 'card_pool' not in st.session_state:
            dummy = [0.0] * 384
            meta_filter = {"subject": f_sub} if f_sub != "顯示全部" else None
            top_k_count = 500 if f_sub == "顯示全部" else 200
            with st.spinner(f"載入題庫..."):
                res = index.query(vector=dummy, top_k=top_k_count, include_metadata=True, filter=meta_filter)
                st.session_state['card_pool'] = res['matches']
        
        pool = st.session_state['card_pool']

        if not pool:
            st.info(f"📭 題庫中暫時沒有【{f_sub}】的紀錄。")
        else:
            if 'current_card_data' not in st.session_state:
                weights = [float(m['metadata'].get('weight', 20.0)) for m in pool]
                chosen_card = random.choices(pool, weights=weights, k=1)[0]
                
                if len(pool) > 1 and 'previous_card_id' in st.session_state:
                    prev_id = st.session_state['previous_card_id']
                    retry = 0
                    while chosen_card['id'] == prev_id and retry < 5:
                        chosen_card = random.choices(pool, weights=weights, k=1)[0]
                        retry += 1
                st.session_state['current_card_data'] = chosen_card

            card = st.session_state['current_card_data']
            data = card['metadata']
            mid = card['id']
            
            st.markdown(f"""
            <div class="flashcard">
                <div class="card-subject">{data.get('subject')}</div>
                <div class="card-question">
                    {clean_latex(data.get('question'))}
                </div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("👁️ 翻開詳解 (Show Detail)", expanded=False):
                st.markdown("### ✅ 詳細解析")
                # 這裡同樣開啟 HTML 支援，顯示黃色答案
                st.markdown(clean_latex(data.get('answer')), unsafe_allow_html=True)
                
                st.divider()
                st.markdown("<div style='text-align: center; color: grey; margin-bottom: 10px;'>這題你覺得？</div>", unsafe_allow_html=True)
                
                _, col_btns, _ = st.columns([1, 4, 1])
                with col_btns:
                    b1, b2, b3, b_del = st.columns([1, 1, 1, 0.5])
                    with b1: st.button("❌ 忘記了", key="hard", on_click=update_weight, args=(mid, 1), use_container_width=True, type="secondary")
                    with b2: st.button("🟡 不確定", key="med", on_click=update_weight, args=(mid, 2), use_container_width=True, type="secondary")
                    with b3: st.button("✅ 記得了", key="easy", on_click=update_weight, args=(mid, 3), use_container_width=True, type="primary")
                    with b_del: st.button("🗑️", key="del", on_click=delete_from_cloud, args=(mid,), use_container_width=True)

    except Exception as e:
        st.error(f"系統錯誤: {e}")
