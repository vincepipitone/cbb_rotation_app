import streamlit as st
from power_rankings import get_power_rankings

st.set_page_config(layout="wide", page_title="CBB Power Rankings")

st.title("📊 CBB Power Rankings")
st.markdown("Current revised power ratings based on market spreads and recency weighting.")

@st.cache_data(ttl=1800)
def load_rankings():
    return get_power_rankings("ncaa_hca.csv")

try:
    rankings_revised = load_rankings()

    search = st.text_input("Search team")
    display_df = rankings_revised.copy()

    if search:
        display_df = display_df[
            display_df["team"].str.contains(search, case=False, na=False)
        ]

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        label="⬇️ Download rankings as CSV",
        data=display_df.to_csv(index=False).encode("utf-8"),
        file_name="cbb_power_rankings.csv",
        mime="text/csv"
    )

except Exception as e:
    st.error(f"Failed to load power rankings: {e}")

