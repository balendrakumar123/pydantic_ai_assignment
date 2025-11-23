from pydantic_ai import Agent, RunContext
from dotenv import load_dotenv
import logfire
import os
import asyncio
import json
from typing import Any

load_dotenv()

# Configure Logfire
logfire.configure()
logfire.instrument_pydantic_ai()

# ---------------- PRODUCT CATALOG ----------------
# 4 Categories + Many Items Under Each Category
AVAILABLE_PRODUCTS = [
    # ---------------- Groceries ----------------
    {"name": "Salt", "price": 2.50, "emoji": "🧂", "category": "Groceries"},
    {"name": "Pepper", "price": 3.00, "emoji": "🌶️", "category": "Groceries"},
    {"name": "Sugar", "price": 2.99, "emoji": "🍬", "category": "Groceries"},
    {"name": "Rice", "price": 12.49, "emoji": "🍚", "category": "Groceries"},
    {"name": "Bread", "price": 3.79, "emoji": "🍞", "category": "Groceries"},
    {"name": "Milk", "price": 1.49, "emoji": "🥛", "category": "Groceries"},
    {"name": "Eggs", "price": 2.99, "emoji": "🥚", "category": "Groceries"},
    {"name": "Cheese", "price": 4.49, "emoji": "🧀", "category": "Groceries"},

    # ---------------- Electronics ----------------
    {"name": "Laptop", "price": 899.99, "emoji": "💻", "category": "Electronics"},
    {"name": "Headphones", "price": 59.99, "emoji": "🎧", "category": "Electronics"},
    {"name": "Keyboard", "price": 29.99, "emoji": "⌨️", "category": "Electronics"},
    {"name": "Mouse", "price": 19.99, "emoji": "🖱️", "category": "Electronics"},
    {"name": "Smartphone", "price": 699.99, "emoji": "📱", "category": "Electronics"},
    {"name": "Charger", "price": 15.99, "emoji": "🔌", "category": "Electronics"},
    {"name": "USB Cable", "price": 5.99, "emoji": "🧵", "category": "Electronics"},

    # ---------------- Home Essentials ----------------
    {"name": "Detergent", "price": 8.99, "emoji": "🧴", "category": "Home Essentials"},
    {"name": "Soap", "price": 2.99, "emoji": "🧼", "category": "Home Essentials"},
    {"name": "Shampoo", "price": 6.99, "emoji": "🧴", "category": "Home Essentials"},
    {"name": "Paper Towels", "price": 5.49, "emoji": "🧻", "category": "Home Essentials"},
    {"name": "Floor Cleaner", "price": 4.59, "emoji": "🧹", "category": "Home Essentials"},
    {"name": "Dish Soap", "price": 3.25, "emoji": "🍽️", "category": "Home Essentials"},
    {"name": "Trash Bags", "price": 6.99, "emoji": "🗑️", "category": "Home Essentials"},

    # ---------------- Clothing ----------------
    {"name": "T-Shirt", "price": 14.99, "emoji": "👕", "category": "Clothing"},
    {"name": "Jeans", "price": 39.99, "emoji": "👖", "category": "Clothing"},
    {"name": "Jacket", "price": 59.99, "emoji": "🧥", "category": "Clothing"},
    {"name": "Sneakers", "price": 49.99, "emoji": "👟", "category": "Clothing"},
    {"name": "Socks", "price": 5.99, "emoji": "🧦", "category": "Clothing"},
    {"name": "Cap", "price": 9.99, "emoji": "🧢", "category": "Clothing"},
    {"name": "Hoodie", "price": 29.99, "emoji": "🧥", "category": "Clothing"},
]


# ---------------- CART MANAGEMENT TOOL ----------------
async def manage_cart(
    ctx: RunContext[Any], 
    product_name: str, 
    action: str, 
    quantity: int = 1, 
    price: float = 0.0
) -> str:
    """
    Tool for the agent — modifies cart.
    """

    with logfire.span('manage_cart', product_name=product_name, action=action, quantity=quantity):

        # Lookup product
        product = next(
            (p for p in AVAILABLE_PRODUCTS if p["name"].lower() == product_name.lower()),
            None
        )

        # If custom item (not available)
        if not product and action in ['add', 'update']:
            return json.dumps({
                "action": action,
                "product": product_name,
                "quantity": quantity,
                "price": price if price > 0 else 5.99,
                "emoji": "📦",
                "category": "Custom",
                "is_custom": True
            })

        # If product not found and user didn't request remove
        if not product and action != "remove":
            available_names = ", ".join([p["name"] for p in AVAILABLE_PRODUCTS])
            return f"Sorry, '{product_name}' is not available. Try one of: {available_names}"

        # Normal action
        return json.dumps({
            "action": action,
            "product": product["name"] if product else product_name,
            "quantity": quantity,
            "price": product["price"] if product else price,
            "emoji": product["emoji"] if product else "📦",
            "category": product["category"] if product else "Custom",
            "is_custom": False
        })


# ---------------- AGENT SETUP ----------------
model = "gemini-2.5-flash"

agent = Agent(
    model,
    tools=[manage_cart],
    system_prompt=
    """
    You are an AI Shopping Assistant.

    We have 4 product categories:
    1. Groceries
    2. Electronics
    3. Home Essentials
    4. Clothing

    When the user says:
    - "show groceries", "add groceries", "I need groceries"
      → list grocery products first.

    - "show electronics"
      → list electronic items first.

    - "home essentials"
      → list cleaning & home items.

    - "clothing"
      → list clothing products.

    ALWAYS use the manage_cart tool when modifying the cart.
    - action="add" → add product (quantity default 1)
    - action="remove" → remove product
    - action="update" → set EXACT quantity the user mentions

    If user requests an item not in the inventory,
    you may still add it as a custom item.

    Be friendly and always explain what you added.
    """
)


# ---------------- AGENT RUNNER ----------------
async def run_agent_with_logging(user_input: str, message_history: list):
    with logfire.span("agent_interaction"):
        logfire.info("User input", user_input=user_input)

        result = await agent.run(user_input, message_history=message_history)

        logfire.info("Agent response", response=str(result.output))

        return result


# Standalone test runner (optional)
async def main():
    history = []

    print("AI Shopping Assistant Ready.\n")

    while True:
        msg = await asyncio.to_thread(input, "You: ")

        if msg.lower() in ["exit", "quit"]:
            break

        result = await run_agent_with_logging(msg, history)

        print("AI:", result.output)
        history = result.all_messages()


if __name__ == "__main__":
    asyncio.run(main())
