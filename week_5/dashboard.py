import streamlit as st
import pandas as pd
from mongoengine import connect, Document, StringField, FloatField, IntField

connect("inventory_db", host="localhost", port=27017)

class Product(Document):
    name = StringField(required=True)
    price = FloatField(required=True)
    quantity = IntField(required=True)

    meta = {"collection": "products"}

st.title("Inventory Dashboard")

st.subheader("Inventory Data")

def load_data():
    products = Product.objects.all()

    if not products:
        st.warning("No products found in the inventory.")
        return pd.DataFrame(columns=["Name", "Price", "Quantity"])
    
    data = [{
        "Name": product.name,
        "Price": product.price,
        "Quantity": product.quantity
    } for product in products] 
    return pd.DataFrame(data)

df = load_data()

st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()

st.subheader("Add New Product")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**➕ Add New Product**")
    name = st.text_input("Product Name")
    price = st.number_input("Price", min_value=0.0, step=0.01)
    quantity = st.number_input("Quantity", min_value=0, step=1)
    if st.button("Add Product"):
        if name and price > 0 and quantity > 0:
            new_product = Product(name=name, price=price, quantity=quantity)
            new_product.save()
            st.success(f"Product '{name}' added successfully!")
            df = load_data()  # Refresh the data
        else:
            st.error("Please enter valid product details.")

with col2:
    st.markdown("** 🗑️ Remove Product**")
    product_names = df["Name"].tolist()
    if product_names:
        product_to_remove = st.selectbox("Select Product to Remove", product_names)
        if st.button("Remove Product"):
            Product.objects(name=product_to_remove).delete()
            st.success(f"Product '{product_to_remove}' removed successfully!")
            df = load_data()  # Refresh the data
    else:
        st.warning("No products available to remove.")

