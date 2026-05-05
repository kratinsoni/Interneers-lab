import streamlit as st

st.title("Hello, Streamlit!")
st.write("This is a simple Streamlit app.")
st.write("Choose your fav. variety of chai")

chai = st.selectbox(
    "Your fav chai: ", ["Masala chai", "Lemon Tea", "Adrak Tea", "Kesar chai"]
)

st.write(f"Your Choose {chai}. Excellent choice")

st.title("Chai Maker App")

if st.button("Make Chai"):
    st.success("Your chai is brewed")

add_masala = st.checkbox("Add Masala")

if add_masala:
    st.write("Masala added to you chai")

tea_type = st.radio("Pick Your chai base: ", ["Milk", "Water", "Almond Milk"])
st.write(f"Selected Base {tea_type}")

flavour = st.selectbox("Chooser flavours: ", ["Adrak", "Kesar", "Tulsi"])

st.write(f"Added Flavour: {flavour}")

sugar = st.slider("Sugar Level: ", 0, 5, 3)

st.write(f"Selected Sugar Amount: {sugar}")

chai_cups = st.number_input("How many cups: ", 0, 10, step=1)

if chai_cups:
    st.write(f"{chai_cups} cups of chai ordered")

name = st.text_input("Enter Your Name")

if name:
    st.write(f"Welcome, {name} ! Your chai is on the way")

dob = st.date_input("Select Your date of Birth")

if dob:
    st.write(f"You birth date is {dob}")


st.title("Chai taste Poll")

col1, col2 = st.columns(2)

with col1:
    st.header("Masala chai")
    st.image(
        "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTFYqoKTu_o3Zns2yExbst2Co84Gpc2Q1RJbA&s"
    )
    vote1 = st.button("Vote Masala Chai")

with col2:
    st.header("Adrak chai")
    st.image(
        "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTFYqoKTu_o3Zns2yExbst2Co84Gpc2Q1RJbA&s"
    )
    vote2 = st.button("Vote Adrak Chai")

if vote1:
    st.success("Thanks for voting Masala Chai")
elif  vote2:
    st.success("Thanks for voting Adrak chai")

name = st.sidebar.text_input("Enter Your Name")
tea = st.sidebar.selectbox("Choose your tea: ", ["Masala chai", "Adrak chai", "Lemon Tea"])

st.write(f"Welcome {name}, you have selected {tea} from the sidebar")

with st.expander("See the recipe"):
    st.write("1. Boil water")
    st.write("2. Add tea leaves")
    st.write("3. Add milk and sugar")
    st.write("4. Let it simmer for 5 minutes")
    st.write("5. Strain and serve hot")