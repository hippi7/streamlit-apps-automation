import streamlit as st

# st.title('🎈 シンプルカウンターアプリ')  <- 変更前
st.title('🚀 自動デプロイ成功！ 🚀') # <- 変更後

if 'count' not in st.session_state:
    st.session_state.count = 0

increment = st.button('カウントアップ')
if increment:
    st.session_state.count += 1

st.write('カウント:', st.session_state.count)