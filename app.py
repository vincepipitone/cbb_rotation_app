import streamlit as st
from rotation_chart import generate_rotation_chart

st.set_page_config(layout="wide")
st.title("CBB Rotation Chart Generator")

url_input = st.text_input("Paste StatBroadcast XML URL here:")

if st.button("Generate Chart"):
    if url_input.strip() == "":
        st.error("Please enter a valid XML URL.")
    else:
        try:
            fig = generate_rotation_chart(url_input.strip())
            st.pyplot(fig)
        except Exception as e:
            st.error(f"Error generating chart: {e}")
