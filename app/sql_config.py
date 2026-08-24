import yaml
import os
import streamlit as st

@st.cache_data(show_spinner=False)
def get_sql_query(section, key):
    config_path = os.path.join(os.path.dirname(__file__), "sql_config.yaml")
    with open(config_path, "r") as f:
        queries = yaml.safe_load(f)
    return queries.get(section, {}).get(key)
