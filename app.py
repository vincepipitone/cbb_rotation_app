import streamlit as st
from rotation_chart import generate_rotation_chart

st.title("CBB Rotation Chart Generator")

game_id = st.text_input("Enter StatBroadcast Game ID (e.g., 625309):")

if st.button("Generate Chart"):
    if not game_id.strip():
        st.error("Please enter a valid game ID.")
    else:
        try:
            fig = generate_rotation_chart(game_id.strip())
            st.pyplot(fig)
        except Exception as e:
            st.error(f"Error generating chart: {e}")
