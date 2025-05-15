import streamlit as st
import pandas as pd
from datetime import datetime
import io

st.set_page_config(page_title="Inventory Management", layout="wide")
st.title("📦 Inventory In/Out Dashboard - 40 Items")

# Initialize session state
if "inventory" not in st.session_state:
    st.session_state.inventory = pd.DataFrame(columns=[
        "Product ID", "Name", "Description", "Stock In", "Stock Out", "Price", "Units",
        "Batch ID", "Date In", "Time In", "Date Out", "Time Out"
    ])

if "product_registry" not in st.session_state:
    st.session_state.product_registry = pd.DataFrame(columns=[
        "Product ID", "Product Name", "Description", "Unit Type", "Batch ID", "Date Registered"
    ])

# Sidebar: Register new product
with st.sidebar.expander("📦 Register New Product"):
    pid = st.text_input("Product ID", key="reg_id")
    pname = st.text_input("Product Name", key="reg_name")
    pdesc = st.text_area("Product Description", key="reg_desc")
    unit_type = st.text_input("Unit Type (pcs, kg, etc.)", key="reg_unit")
    batch = st.text_input("Batch ID (optional)", key="reg_batch")

    if st.button("➕ Register Product"):
        new_product = {
            "Product ID": pid,
            "Product Name": pname,
            "Description": pdesc,
            "Unit Type": unit_type,
            "Batch ID": batch,
            "Date Registered": datetime.now().date().isoformat()
        }
        st.session_state.product_registry = pd.concat([
            st.session_state.product_registry,
            pd.DataFrame([new_product])
        ], ignore_index=True)
        st.success(f"Product {pname} registered.")

# Sidebar: Add stock movement
with st.sidebar:
    st.header("➕ Add Stock Movement")
    product_list = st.session_state.product_registry["Product Name"].tolist()
    selected_product = st.selectbox("Select Product", product_list)

    if selected_product:
        product_info = st.session_state.product_registry[
            st.session_state.product_registry["Product Name"] == selected_product
        ].iloc[0]

        description = product_info["Description"]
        units = product_info["Unit Type"]
        batch_id = product_info["Batch ID"]
        pid = product_info["Product ID"]

        stock_in = st.number_input("Stock In", min_value=0, step=1)
        stock_out = st.number_input("Stock Out", min_value=0, step=1)
        price = st.number_input("Price per Unit", min_value=0.0, step=0.1)

        if st.button("Add Entry"):
            now = datetime.now()
            new_row = {
                "Product ID": pid,
                "Name": selected_product,
                "Description": description,
                "Stock In": stock_in,
                "Stock Out": stock_out,
                "Price": price,
                "Units": units,
                "Batch ID": batch_id,
                "Date In": now.date().isoformat(),
                "Time In": now.strftime("%H:%M:%S"),
                "Date Out": now.date().isoformat() if stock_out > 0 else "",
                "Time Out": now.strftime("%H:%M:%S") if stock_out > 0 else ""
            }
            st.session_state.inventory = pd.concat([
                st.session_state.inventory,
                pd.DataFrame([new_row])
            ], ignore_index=True)
            st.success("✅ Stock entry added.")

# Display product registry
st.subheader("📒 Product Registry")
st.dataframe(st.session_state.product_registry, use_container_width=True)

# Display inventory table
st.subheader("📋 Current Inventory")
st.dataframe(st.session_state.inventory, use_container_width=True)

# Download as Excel or CSV

def convert_multi_sheet_excel(products_df, inventory_df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        products_df.to_excel(writer, sheet_name="Product Registry", index=False)
        inventory_df.to_excel(writer, sheet_name="Stock Movements", index=False)
    return output.getvalue()

def convert_df(df, to_excel=False):
    if to_excel:
        return convert_multi_sheet_excel(
            st.session_state.product_registry,
            st.session_state.inventory
        )
    else:
        return st.session_state.inventory.to_csv(index=False).encode("utf-8")

col1, col2 = st.columns(2)
with col1:
    st.download_button(
        label="⬇️ Download as CSV",
        data=convert_df(st.session_state.inventory),
        file_name="inventory_data.csv",
        mime="text/csv"
    )
with col2:
    st.download_button(
        label="⬇️ Download Inventory File (2 Sheets)",
        data=convert_df(st.session_state.inventory, to_excel=True),
        file_name="inventory_management.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
