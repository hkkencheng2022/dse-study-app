# --- Sub Tab 3: 模擬試卷 (已修復數學符號顯示問題) ---
            with sub_tab3:
                st.subheader("🔥 題目生成器")
                
                # 設定區
                row1_col1, row1_col2, row1_col3 = st.columns([2, 2, 1])
                
                with row1_col1:
                    diff = st.select_slider("難度選擇", options=["Level 3", "Level 4", "Level 5", "Level 5**"], value="Level 4")
                
                with row1_col2:
                    q_type = st.radio("題型", ["MC (多項選擇)", "LQ (長題目)"], horizontal=True)
                
                with row1_col3:
                    num_questions = st.number_input("題目數量", min_value=1, max_value=20, value=1, step=1)

                st.markdown("---")

                if st.button(f"🚀 生成 {num_questions} 條題目"):
                     with st.spinner(f"DeepSeek 正在參考筆記，設計 {num_questions} 條題目..."):
                        
                        # 定義分隔符號
                        separator = "<<<SPLIT_HERE>>>"

                        # Prompt Engineering (加入數學格式要求)
                        gen_prompt = f"""
                        角色：香港考評局 DSE {subject} 出卷員。
                        任務：根據提供的筆記內容，設計 **{num_questions} 條** {diff} 程度的 {q_type}。
                        
                        【極重要格式要求】：
                        1. **題目與答案分離**：
                           請先列出「試題卷 (Question Paper)」，完全不要包含答案。
                           然後插入分隔符號：`{separator}`
                           最後列出「參考答案 (Marking Scheme)」。

                        2. **MC 格式 (強制垂直分行)**：
                           每個選項必須獨立一行，使用 Markdown 列表格式。
                           範例：
                           1. 題目內容...
                              - A. 選項一
                              - B. 選項二
                              - C. 選項三
                              - D. 選項四
                        
                        3. **LQ 格式**：請標註分數 (e.g., [4 marks])。

                        4. **數學符號 (Math LaTeX)**：
                           - 所有數學公式、變數 (如 x, y, k)、希臘字母 (如 alpha, beta) **必須** 使用 LaTeX 格式。
                           - **必須** 使用單個錢號 `$` 包裹內文公式 (Inline Math)。
                           - **必須** 使用雙錢號 `$$` 包裹獨立一行的公式 (Block Math)。
                           - 錯誤範例：( x^2 ) 或 [ x^2 ]
                           - 正確範例： $x^2 - 4x + k = 0$ 或 $\\alpha + \\beta = 4$
                        
                        筆記內容範圍：{notes_text[:6000]}
                        """
                        
                        try:
                            # 呼叫 API
                            response = client.chat.completions.create(
                                model="deepseek-chat",
                                messages=[{"role": "user", "content": gen_prompt}]
                            )
                            full_text = response.choices[0].message.content
                            
                            # 處理分割邏輯
                            if separator in full_text:
                                parts = full_text.split(separator)
                                questions_part = parts[0].strip()
                                answers_part = parts[1].strip()
                            else:
                                questions_part = full_text
                                answers_part = "AI 未能自動分離答案，請參閱上方內容。"
                            
                            st.success("✅ 出卷完成！")
                            
                            # 1. 顯示題目
                            st.markdown("### 📝 試題卷")
                            st.markdown(questions_part) # Streamlit 會自動渲染裡面的 $LaTeX$
                            
                            st.markdown("---")
                            
                            # 2. 顯示答案
                            st.info("👇 完成作答後，點擊下方查看答案")
                            with st.expander("🔐 點擊查看 Marking Scheme (參考答案)"):
                                st.markdown("### ✅ 參考答案與詳解")
                                st.markdown(answers_part)

                        except Exception as e:
                            st.error(f"生成失敗: {e}")
