from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class Product(BaseModel):
    name: str
    description: str
    price: float
    quantity: int

client = OpenAI()

def generate_product_names() -> list[str]:
    prompt = f"Generate 50 products for a toy store"
    
    response = client.chat.completions.parse(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that generates creative product names."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=100,
        temperature=0.7,
        response_format=Product
    )
    
    products = response.choices[0].message.content.strip().split('\n')
    return products

if __name__ == "__main__":
    products = generate_product_names()
    for product in products:
        print(product)

