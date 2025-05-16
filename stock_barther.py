import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import sqlite3
import io

# Database connection
conn = sqlite3.connect("inventory.db", check_same_thread=False)
cursor = conn.cursor()

# Ensure tables exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS product_registry (
    product_id TEXT PRIMARY KEY,
    product_name TEXT,
    description TEXT,
    unit_type TEXT,
    batch_id TEXT,
    date_registered TEXT,
    total_units INTEGER,
    expiration_date TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS inventory_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT,
    name TEXT,
    description TEXT,
    stock_in INTEGER,
    stock_out INTEGER,
    price REAL,
    units TEXT,
    batch_id TEXT,
    date_in TEXT,
    time_in TEXT,
    date_out TEXT,
    time_out TEXT,
    current_inventory INTEGER
)
""")

conn.commit()

# Navigation
st.set_page_config(page_title="Inventory Management", layout="wide")
menu = st.sidebar.radio("Navigation", ["Dashboard", "SQL Console"])

# Query history state
if "query_history" not in st.session_state:
    st.session_state.query_history = []

# Product registration form
def register_product(product_df):

    # Inventory entry form
    st.subheader("📥 Add Inventory Movement")

    if not product_df.empty:
        with st.form("inventory_form"):
            selected_product = st.selectbox("Select Product", product_df["product_name"].tolist(), key="inv_select")
            product_row = product_df[product_df["product_name"] == selected_product].iloc[0]
            st.markdown(f"**Unit Type:** {product_row['unit_type']}")
            st.markdown(f"**Batch ID:** {product_row['batch_id']}")
            stock_in = st.number_input("Stock In", min_value=0, step=1, key="inv_stock_in")
            stock_out = st.number_input("Stock Out", min_value=0, step=1, key="inv_stock_out")
            price = st.number_input("Price per Unit", min_value=0.0, step=0.1, key="inv_price")
            submitted_inv = st.form_submit_button("Add Inventory Entry")

    
        # Ensure submitted_inv is only checked if it exists
        if 'submitted_inv' in locals() and submitted_inv:
            st.markdown("### ✅ Confirm Inventory Entry")
            st.write("**Product:**", selected_product)
            st.write("**Stock In:**", stock_in)
            st.write("**Stock Out:**", stock_out)
            st.write("**Price per Unit:**", price)

            # Show current stock balance for this product
            try:
                stock_summary = pd.read_sql("""
SELECT name, SUM(stock_in) AS total_in, SUM(stock_out) AS total_out
FROM inventory_log
WHERE name = ?
GROUP BY name
""", conn, params=(selected_product,))

                if not stock_summary.empty:
                    current_balance = stock_summary["total_in"].iloc[0] - stock_summary["total_out"].iloc[0]
                    st.info(f"📦 Current stock for '{selected_product}': {current_balance} units")
                else:
                    st.info(f"📦 No stock data found yet for '{selected_product}'.")
            except Exception as e:
                st.warning("⚠️ Could not calculate current stock due to a query error.")

            if 'current_balance' not in locals():
                current_balance = 0
            if stock_out > current_balance:
                st.error(f"❌ Stock out ({stock_out}) exceeds available balance ({current_balance}). Entry not allowed.")
            elif st.button("✅ Confirm and Submit Entry"):
                product_row = product_df[product_df["product_name"] == selected_product].iloc[0]
                peru_tz = pytz.timezone("America/Lima")
                now = datetime.now(peru_tz)
                date_str = now.strftime("%Y-%m-%d")
                time_str = now.strftime("%H:%M:%S")
                cursor.execute("""
                    INSERT INTO inventory_log (product_id, name, description, stock_in, stock_out, price, units, batch_id, date_in, time_in, date_out, time_out, current_inventory)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
                    product_row["product_id"],
                    selected_product,
                    product_row["description"],
                    stock_in,
                    stock_out,
                    price,
                    product_row["unit_type"],
                    product_row["batch_id"],
                    date_str,
                    time_str,
                    "",
                    "",
current_balance
))
                conn.commit()
                st.success("Inventory entry added successfully!")
        else:
            st.warning("Please register a product before adding inventory entries.")
    st.subheader("➕ Register New Product")
    with st.form("product_form"):
        col1, col2 = st.columns(2)
        with col1:
            product_id = st.text_input("Product ID")
            product_name = st.text_input("Product Name", key="product_name")
            unit_type = st.text_input("Unit Type", key="unit_type")
            batch_id = st.text_input("Batch ID", key="batch_id")
            total_units_input = st.number_input("Total Units", min_value=0, key="total_units")
        with col2:
            description = st.text_area("Description", key="description")
            expiration_input = st.date_input("Expiration Date", key="expiration_date")
        
        submitted = st.form_submit_button("Register Product")
        if submitted:
            try:
                cursor.execute("""
                    INSERT INTO product_registry (product_id, product_name, description, unit_type, batch_id, date_registered, total_units, expiration_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (product_id, product_name, description, unit_type, batch_id, datetime.now(pytz.timezone("America/Lima")).strftime("%Y-%m-%d"),
                      int(total_units_input), expiration_input.strftime("%Y-%m-%d")))
                conn.commit()
                st.success(f"Product '{product_name}' registered successfully.")
            except sqlite3.IntegrityError:
                st.error("❌ Product ID already exists. Please use a unique ID.")
                conn.commit()
                st.success(f"Product '{product_name}' registered successfully.")
            except sqlite3.IntegrityError:
                st.error("❌ Product ID already exists. Please use a unique ID.")

if menu == "Dashboard":
    st.title("📦 Inventory In/Out Dashboard - 40 Items")

    try:
        product_df = pd.read_sql("SELECT *, total_units, expiration_date FROM product_registry", conn)
    except Exception:
        product_df = pd.DataFrame()

    register_product(product_df)

    try:
        st.subheader("📒 Product Registry")
        product_df = pd.read_sql("SELECT * FROM product_registry", conn)
        st.dataframe(product_df, use_container_width=True)

        selected_delete = st.selectbox("Select Product ID to Delete", product_df["product_id"].tolist() if not product_df.empty else [])
        if st.button("🗑️ Delete Selected Product"):
            cursor.execute("DELETE FROM product_registry WHERE product_id = ?", (selected_delete,))
            conn.commit()
            st.success(f"Product ID '{selected_delete}' deleted.")
    except Exception:
        product_df = pd.DataFrame()
        st.warning("📭 Product registry is empty or missing.")

    try:
        st.subheader("📋 Current Inventory")
        inventory_df = pd.read_sql("SELECT *, (stock_in - stock_out) AS stock_total, (stock_in - stock_out) AS stock_change FROM inventory_log", conn)
        inventory_df["trend"] = inventory_df["stock_in"] - inventory_df["stock_out"]
        inventory_df["trend_icon"] = inventory_df["trend"].apply(lambda x: "📈" if x > 0 else ("📉" if x < 0 else "➖"))
        inventory_df["display_name"] = inventory_df["trend_icon"] + " " + inventory_df["name"]

        trend_summary = inventory_df.groupby("display_name")["trend"].sum().reset_index().rename(columns={"trend": "total_trend"})
        st.subheader("📊 Product Trend Summary")
        st.dataframe(trend_summary, use_container_width=True)

        import plotly.express as px
        fig = px.bar(trend_summary, x="display_name", y="total_trend", color="total_trend", title="📈 Trend Change per Product")
        st.plotly_chart(fig, use_container_width=True)
        import numpy as np

        def highlight_stock(row):
            if row["stock_total"] <= 5:
                return ["background-color: #ffcccc"] * len(row)
            elif row["stock_total"] <= 10:
                return ["background-color: #fff3cd"] * len(row)
            else:
                return [""] * len(row)

        styled_inventory = inventory_df.style.apply(highlight_stock, axis=1)
        st.dataframe(styled_inventory, use_container_width=True)

        selected_log = st.selectbox("Select Inventory Row ID to Delete", inventory_df["id"].tolist() if not inventory_df.empty else [])
        if st.button("🗑️ Delete Selected Inventory Record"):
            cursor.execute("DELETE FROM inventory_log WHERE id = ?", (selected_log,))
            conn.commit()
            st.success(f"Inventory log ID '{selected_log}' deleted.")

        # Check for low inventory warnings
        inventory_df = pd.read_sql("SELECT *, (stock_in - stock_out) AS stock_total FROM inventory_log", conn)
        try:
            stock_summary = inventory_df.groupby("name")[["stock_in", "stock_out"]].sum()
            stock_summary["balance"] = stock_summary["stock_in"] - stock_summary["stock_out"]
            for product in stock_summary.index:
                total_in = stock_summary.loc[product, "stock_in"]
                balance = stock_summary.loc[product, "balance"]
                if total_in > 0 and balance / total_in <= 0.2:
                    st.warning(f"⚠️ Warning: '{product}' has dropped to {balance} units, which is below 20% of its total stock ({total_in}).")
        except Exception as e:
            st.info("ℹ️ Unable to calculate inventory warnings due to missing or malformed data.")
        st.dataframe(inventory_df, use_container_width=True)
    except Exception:
        inventory_df = pd.DataFrame()
        st.warning("📭 Inventory log is empty or missing.")

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

    with st.expander("📂 Show Raw Tables"):
        try:
            st.subheader("🗂 Product Registry (Raw View)")
            st.dataframe(pd.read_sql("SELECT * FROM product_registry", conn))
            st.subheader("🧾 Inventory Log (Raw View)")
            st.dataframe(pd.read_sql("SELECT * FROM inventory_log", conn))
        except Exception:
            st.info("🔍 Tables will appear here once data is entered.")

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





