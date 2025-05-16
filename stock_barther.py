import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
import io

# Database connection
conn = sqlite3.connect("inventory.db", check_same_thread=False)
cursor = conn.cursor()

# Navigation
st.set_page_config(page_title="Inventory Management", layout="wide")
menu = st.sidebar.radio("Navigation", ["Dashboard", "SQL Console"])

# Query history state
if "query_history" not in st.session_state:
    st.session_state.query_history = []

if menu == "Dashboard":
    st.title("📦 Inventory In/Out Dashboard - 40 Items")

    # -- Product Registry Sheet --
    st.subheader("📒 Product Registry")
    product_df = pd.read_sql("SELECT * FROM product_registry", conn)
    st.dataframe(product_df, use_container_width=True)

    # -- Inventory Log Sheet (Stock Movements) --
    st.subheader("📋 Current Inventory")
    inventory_df = pd.read_sql("SELECT * FROM inventory_log", conn)
    st.dataframe(inventory_df, use_container_width=True)

    def convert_multi_sheet_excel(products_df, inventory_df):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            products_df.to_excel(writer, sheet_name="Product Registry", index=False)
            inventory_df.to_excel(writer, sheet_name="Stock Movements", index=False)
        return output.getvalue()

    def convert_df(df, to_excel=False):
        if to_excel:
            return convert_multi_sheet_excel(product_df, inventory_df)
        else:
            return inventory_df.to_csv(index=False).encode("utf-8")

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="⬇️ Download as CSV",
            data=convert_df(inventory_df),
            file_name="inventory_data.csv",
            mime="text/csv"
        )
    with col2:
        st.download_button(
            label="⬇️ Download Inventory File (2 Sheets)",
            data=convert_df(inventory_df, to_excel=True),
            file_name="inventory_management.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # Raw Database Tables
    with st.expander("📂 Show Raw Tables"):
        st.subheader("🗂 Product Registry (Raw View)")
        st.dataframe(pd.read_sql("SELECT * FROM product_registry", conn))

        st.subheader("🧾 Inventory Log (Raw View)")
        st.dataframe(pd.read_sql("SELECT * FROM inventory_log", conn))

        with open("inventory.db", "rb") as db_file:
            st.download_button(
                label="⬇️ Download SQLite Database",
                data=db_file,
                file_name="inventory.db",
                mime="application/octet-stream"
            )

elif menu == "SQL Console":
    st.title("🧠 SQL Query Interface")
    st.write("Run custom SQL queries on the inventory database. Only SELECT statements are allowed.")

    query_input = st.text_area("Enter SQL query:", value="SELECT * FROM inventory_log LIMIT 10;")

    if st.button("Run Query"):
        if query_input.strip().lower().startswith("select"):
            try:
                query_result = pd.read_sql(query_input, conn)
                st.success("✅ Query executed successfully!")
                st.dataframe(query_result, use_container_width=True)

                # Save query to history
                if query_input not in st.session_state.query_history:
                    st.session_state.query_history.insert(0, query_input)

                with io.StringIO() as buffer:
                    query_result.to_csv(buffer, index=False)
                    st.download_button(
                        label="⬇️ Download Query Results as CSV",
                        data=buffer.getvalue(),
                        file_name="query_results.csv",
                        mime="text/csv"
                    )
            except Exception as e:
                st.error(f"❌ Error: {e}")
        else:
            st.warning("🚫 Only SELECT statements are allowed for security reasons.")

    st.markdown("""
    #### 💡 Example Queries:
    - `SELECT * FROM product_registry;`
    - `SELECT name, SUM(stock_in) AS total_in, SUM(stock_out) AS total_out FROM inventory_log GROUP BY name;`
    - `SELECT * FROM inventory_log WHERE price > 5.0;`
    - `SELECT DISTINCT batch_id FROM inventory_log;`
    - `SELECT * FROM product_registry WHERE product_name LIKE '%mask%';`
    """)

    if st.session_state.query_history:
        st.markdown("#### 🕓 Query History")
        for q in st.session_state.query_history:
            if st.button(f"📋 {q}"):
                query_input = q
