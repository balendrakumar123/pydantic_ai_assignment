from fasthtml.common import *
import asyncio
from backend_agent import run_agent_with_logging
import json
from starlette.requests import Request

app, rt = fast_app(
    hdrs=(
        Script(src="https://unpkg.com/htmx.org@1.9.10"),
    )
)

# Session storage - per user session
sessions = {}

def get_session_id(request: Request):
    """Get or create session ID from cookie"""
    session_id = request.cookies.get('session_id')
    if not session_id:
        import uuid
        session_id = str(uuid.uuid4())
    return session_id

def get_session_data(session_id: str):
    """Get session data, create if doesn't exist"""
    if session_id not in sessions:
        sessions[session_id] = {
            'messages': [],
            'agent_message_history': [],
            'cart': {}
        }
    return sessions[session_id]

# ---------------------------
# Updated product catalog (4 categories + many items)
# ---------------------------
products = [
    # Groceries
    {"name": "Salt", "price": 2.50, "emoji": "🧂", "category": "Groceries"},
    {"name": "Pepper", "price": 3.00, "emoji": "🌶️", "category": "Groceries"},
    {"name": "Sugar", "price": 2.99, "emoji": "🍬", "category": "Groceries"},
    {"name": "Rice", "price": 12.49, "emoji": "🍚", "category": "Groceries"},
    {"name": "Bread", "price": 3.79, "emoji": "🍞", "category": "Groceries"},
    {"name": "Milk", "price": 1.49, "emoji": "🥛", "category": "Groceries"},
    {"name": "Eggs", "price": 2.99, "emoji": "🥚", "category": "Groceries"},
    {"name": "Cheese", "price": 4.49, "emoji": "🧀", "category": "Groceries"},

    # Electronics
    {"name": "Laptop", "price": 899.99, "emoji": "💻", "category": "Electronics"},
    {"name": "Headphones", "price": 59.99, "emoji": "🎧", "category": "Electronics"},
    {"name": "Keyboard", "price": 29.99, "emoji": "⌨️", "category": "Electronics"},
    {"name": "Mouse", "price": 19.99, "emoji": "🖱️", "category": "Electronics"},
    {"name": "Smartphone", "price": 699.99, "emoji": "📱", "category": "Electronics"},
    {"name": "Charger", "price": 15.99, "emoji": "🔌", "category": "Electronics"},
    {"name": "USB Cable", "price": 5.99, "emoji": "🔗", "category": "Electronics"},

    # Home Essentials
    {"name": "Detergent", "price": 8.99, "emoji": "🧴", "category": "Home Essentials"},
    {"name": "Soap", "price": 2.99, "emoji": "🧼", "category": "Home Essentials"},
    {"name": "Shampoo", "price": 6.99, "emoji": "🧴", "category": "Home Essentials"},
    {"name": "Paper Towels", "price": 5.49, "emoji": "🧻", "category": "Home Essentials"},
    {"name": "Floor Cleaner", "price": 4.59, "emoji": "🧹", "category": "Home Essentials"},
    {"name": "Dish Soap", "price": 3.25, "emoji": "🍽️", "category": "Home Essentials"},
    {"name": "Trash Bags", "price": 6.99, "emoji": "🗑️", "category": "Home Essentials"},

    # Clothing
    {"name": "T-Shirt", "price": 14.99, "emoji": "👕", "category": "Clothing"},
    {"name": "Jeans", "price": 39.99, "emoji": "👖", "category": "Clothing"},
    {"name": "Jacket", "price": 59.99, "emoji": "🧥", "category": "Clothing"},
    {"name": "Sneakers", "price": 49.99, "emoji": "👟", "category": "Clothing"},
    {"name": "Socks", "price": 5.99, "emoji": "🧦", "category": "Clothing"},
    {"name": "Cap", "price": 9.99, "emoji": "🧢", "category": "Clothing"},
    {"name": "Hoodie", "price": 29.99, "emoji": "🧥", "category": "Clothing"},
]

# Product card no longer needed - products shown in sidebar / via agent responses

def CartItem(name, price, emoji, quantity):
    """Create a cart item card with quantity controls"""
    return Div(
        Div(
            Span(emoji, cls="cart-item-emoji"),
            Div(
                Div(name, cls="cart-item-name"),
                Div(f"${price:.2f}", cls="cart-item-price"),
                cls="cart-item-info"
            ),
            cls="cart-item-header"
        ),
        Div(
            Button("-",
                hx_post=f"/cart/decrease/{name}",
                hx_target="#cart-items",
                hx_swap="innerHTML",
                cls="qty-button"
            ),
            Span(str(quantity), cls="qty-value"),
            Button("+",
                hx_post=f"/cart/increase/{name}",
                hx_target="#cart-items",
                hx_swap="innerHTML",
                cls="qty-button"
            ),
            cls="cart-item-controls"
        ),
        cls="cart-item"
    )

def ChatMessage(text, is_user=False):
    """Create a chat message in ChatGPT style"""
    wrapper_class = "message-wrapper user" if is_user else "message-wrapper bot"
    avatar_class = "avatar user" if is_user else "avatar bot"
    avatar_text = "U" if is_user else "AI"

    return Div(
        Div(avatar_text, cls=avatar_class),
        Div(
            Div(text, cls="message-text"),
            cls="message-content"
        ),
        cls=wrapper_class,
        style="animation: fadeIn 0.3s;"
    )
@rt("/")
def get(request: Request):
    """Main chat page"""
    session_id = get_session_id(request)
    # Initialize session data
    get_session_data(session_id)
    
    response = Html(
        Head(
            Title("Shopping Assistant"),
            Meta(name="viewport", content="width=device-width, initial-scale=1.0"),
            Link(rel="stylesheet", href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"),
            Style("""
                /* ---------- Global reset (kept minimal) ---------- */
                * { margin: 0; padding: 0; box-sizing: border-box; }
                html, body, #app { height: 100%; }

                /* ---------- Page background & typography ---------- */
                body {
                    font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial;
                    background: linear-gradient(180deg, #f6f8fb 0%, #eef3f9 100%);
                    color: #1f2937;
                    height: 100vh;
                    display: flex;
                    overflow: hidden;
                }

                /* ---------- Layout containers ---------- */
                .main-wrapper {
                    display: flex;
                    width: 100%;
                    height: 100vh;
                    gap: 20px;
                    padding: 20px;
                }

                .main-content {
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                    max-width: 1100px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 6px 20px rgba(20, 30, 60, 0.08);
                    overflow: hidden;
                }

                /* ---------- Header ---------- */
                .chat-header {
                    padding: 18px 24px;
                    border-bottom: 1px solid rgba(31,41,55,0.06);
                    background: linear-gradient(90deg, rgba(255,255,255,0.6), rgba(250,250,250,0.6));
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 12px;
                }

                .header-left { display: flex; align-items: center; gap: 14px; }

                .logo {
                    width: 48px; height: 48px;
                    background: linear-gradient(135deg, #4f46e5 0%, #06b6d4 100%);
                    border-radius: 10px;
                    display: flex; align-items: center; justify-content: center;
                    font-size: 20px; font-weight: 800; color: white;
                    box-shadow: 0 6px 18px rgba(79,70,229,0.12);
                }

                .header-info { display: flex; flex-direction: column; }
                .chat-title { font-size: 18px; font-weight: 700; color: #0f172a; }
                .chat-subtitle { font-size: 13px; color: #475569; margin-top: 2px; }

                .header-badge {
                    padding: 6px 14px;
                    background: #f1f5f9;
                    border-radius: 999px;
                    font-size: 12px;
                    color: #0f172a;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.6px;
                    border: 1px solid rgba(15,23,42,0.04);
                }

                /* ---------- Chat area ---------- */
                .chat-messages {
                    flex: 1;
                    overflow-y: auto;
                    padding: 28px;
                    display: flex;
                    flex-direction: column;
                    gap: 18px;
                    background: linear-gradient(180deg, rgba(255,255,255,0.9), rgba(250,250,250,0.9));
                }

                .welcome-message {
                    text-align: center;
                    padding: 50px 20px;
                    max-width: 720px;
                    margin: 0 auto;
                    background: linear-gradient(180deg, #ffffff, #fbfdff);
                    border-radius: 10px;
                    box-shadow: 0 8px 20px rgba(31,41,55,0.04);
                }

                .welcome-icon { font-size: 56px; margin-bottom: 18px; }
                .welcome-title {
                    font-size: 26px;
                    font-weight: 800;
                    color: #0f172a;
                    margin-bottom: 8px;
                    background: linear-gradient(90deg,#4f46e5,#06b6d4);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }
                .welcome-text { font-size: 14px; color: #475569; line-height: 1.6; margin-bottom: 18px; }

                .quick-prompts { display: grid; grid-template-columns: repeat(1, minmax(0,1fr)); gap: 12px; margin-top: 12px; }
                .prompt-card {
                    padding: 14px;
                    background: #ffffff;
                    border-radius: 10px;
                    text-align: left;
                    cursor: pointer;
                    transition: transform .14s ease, box-shadow .14s ease;
                    border: 1px solid rgba(15,23,42,0.04);
                }
                .prompt-card:hover {
                    transform: translateY(-4px);
                    box-shadow: 0 12px 30px rgba(16,24,40,0.06);
                }
                .prompt-icon { font-size: 20px; margin-bottom: 6px; }
                .prompt-text { font-size: 13px; color: #0f172a; font-weight: 600; }

                /* ---------- Messages ---------- */
                .message-wrapper { display: flex; gap: 14px; max-width: 100%; align-items: flex-start; }
                .message-wrapper.user { flex-direction: row-reverse; justify-content: flex-start; }
                .message-wrapper.bot { justify-content: flex-start; }

                .avatar {
                    width: 40px; height: 40px; border-radius: 50%;
                    display: flex; align-items: center; justify-content: center;
                    font-size: 15px; font-weight: 700; flex-shrink: 0;
                    color: white;
                    box-shadow: 0 6px 16px rgba(15,23,42,0.06);
                }
                .avatar.bot { background: linear-gradient(135deg,#06b6d4 0%, #0ea5a4 100%); }
                .avatar.user { background: linear-gradient(135deg,#4f46e5 0%, #8b5cf6 100%); }

                .message-content { flex: 0 1 auto; min-width: 0; max-width: 75%; }
                .message-text {
                    padding: 14px 16px;
                    border-radius: 12px;
                    line-height: 1.5;
                    font-size: 14px;
                    word-wrap: break-word;
                    display: inline-block;
                    width: 100%;
                }

                .message-wrapper.bot .message-text {
                    background: #f8fafc;
                    color: #0f172a;
                    box-shadow: 0 6px 18px rgba(15,23,42,0.04);
                }

                .message-wrapper.user .message-text {
                    background: linear-gradient(135deg,#4f46e5,#06b6d4);
                    color: white;
                    box-shadow: 0 8px 24px rgba(79,70,229,0.06);
                }

                /* ---------- Typing indicator ---------- */
                .typing-indicator { display: flex; gap: 14px; animation: fadeIn .25s; align-items: center; }
                .typing-indicator .message-text { display: inline-flex; gap: 6px; align-items: center; background: #f8fafc; }
                .typing-dot { width: 8px; height: 8px; background: #94a3b8; border-radius: 50%; animation: typing 1.2s infinite ease-in-out; }
                .typing-dot:nth-child(2) { animation-delay: .12s; }
                .typing-dot:nth-child(3) { animation-delay: .24s; }

                @keyframes typing {
                    0%, 60%, 100% { transform: translateY(0); opacity: .35; }
                    30% { transform: translateY(-6px); opacity: 1; }
                }

                /* ---------- Input area ---------- */
                .chat-input-container {
                    padding: 18px;
                    background: linear-gradient(180deg, #ffffff, #fbfdff);
                    border-top: 1px solid rgba(15,23,42,0.04);
                }

                .input-wrapper {
                    max-width: 920px;
                    margin: 0 auto;
                    position: relative;
                    display: flex;
                    align-items: center;
                    background: #f1f5f9;
                    border-radius: 999px;
                    padding: 8px 10px;
                    transition: box-shadow .12s ease, transform .12s ease;
                    box-shadow: 0 6px 18px rgba(15,23,42,0.03);
                }
                .input-wrapper:focus-within { box-shadow: 0 10px 28px rgba(79,70,229,0.06); transform: translateY(-1px); }

                .input-wrapper.loading { opacity: 0.7; pointer-events: none; }

                .chat-input {
                    flex: 1;
                    padding: 12px 14px;
                    background: transparent;
                    border: none;
                    outline: none;
                    color: #0f172a;
                    font-size: 15px;
                    font-family: inherit;
                    resize: none;
                    max-height: 160px;
                }
                .chat-input::placeholder { color: #94a3b8; }

                .send-button {
                    width: 44px; height: 44px;
                    background: linear-gradient(135deg,#4f46e5 0%,#06b6d4 100%);
                    color: white; border: none; border-radius: 999px;
                    cursor: pointer; display: flex; align-items: center; justify-content: center;
                    transition: transform .12s ease, box-shadow .12s ease; margin-left: 8px;
                    font-size: 16px; font-weight: 800;
                    box-shadow: 0 8px 22px rgba(79,70,229,0.08);
                }
                .send-button:hover:not(:disabled) { transform: translateY(-3px); box-shadow: 0 12px 34px rgba(79,70,229,0.12); }
                .send-button:disabled { opacity: .6; cursor: not-allowed; }

                .loading-dots { display: none; }
                .loading-dots.active { display: flex; gap: 6px; align-items: center; justify-content: center; }
                .loading-dot { width: 6px; height: 6px; background: white; border-radius: 50%; animation: bounce 1.1s infinite ease-in-out both; }
                .loading-dot:nth-child(1) { animation-delay: -0.24s; }
                .loading-dot:nth-child(2) { animation-delay: -0.12s; }

                @keyframes bounce {
                    0%, 80%, 100% { transform: scale(0); opacity: 0.4; }
                    40% { transform: scale(1); opacity: 1; }
                }

                /* ---------- Cart sidebar (right) ---------- */
                .cart-sidebar {
                    width: 360px;
                    background: linear-gradient(180deg,#ffffff,#fbfdff);
                    border-radius: 12px;
                    border: 1px solid rgba(15,23,42,0.04);
                    display: flex;
                    flex-direction: column;
                    box-shadow: 0 8px 30px rgba(15,23,42,0.04);
                    padding: 12px;
                }
                .cart-sidebar2 {
                    width: 360px;
                    background: linear-gradient(180deg,#ffffff,#fbfdff);
                    border-radius: 12px;
                    border: 1px solid rgba(15,23,42,0.04);
                    display: flex;
                    flex-direction: column;
                    box-shadow: 0 8px 30px rgba(15,23,42,0.04);
                    padding: 12px;
                }

                .cart-header { padding: 18px; border-bottom: 1px solid rgba(15,23,42,0.04); }
                .cart-title { font-size: 16px; font-weight: 700; color: #0f172a; display: flex; align-items: center; gap: 10px; }
                .cart-count { font-size: 12px; color: #475569; }

                .cart-items { flex: 1; overflow-y: auto; padding: 12px; }
                .cart-empty { text-align: center; color: #64748b; padding: 36px 12px; font-size: 13px; line-height: 1.6; }

                .cart-empty-icon { font-size: 44px; margin-bottom: 8px; opacity: 0.6; }

                .cart-item {
                    background: #ffffff;
                    border-radius: 10px;
                    padding: 12px;
                    margin-bottom: 12px;
                    transition: transform .12s ease, box-shadow .12s ease;
                    border: 1px solid rgba(15,23,42,0.04);
                    box-shadow: 0 8px 20px rgba(15,23,42,0.03);
                }
                .cart-item:hover { transform: translateY(-4px); box-shadow: 0 18px 40px rgba(15,23,42,0.06); }

                .cart-item-header { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
                .cart-item-emoji { font-size: 26px; }
                .cart-item-info { flex: 1; }
                .cart-item-name { font-size: 14px; font-weight: 700; color: #0f172a; margin-bottom: 4px; }
                .cart-item-price { font-size: 13px; color: #0ea5a4; font-weight: 700; }

                .cart-item-controls { display: flex; align-items: center; justify-content: center; gap: 10px; }
                .qty-button {
                    width: 34px; height: 34px;
                    background: #e6eef6;
                    color: #0f172a;
                    border: none; border-radius: 8px;
                    cursor: pointer; font-size: 16px; font-weight: 700;
                    transition: transform .12s ease, background .12s ease;
                    display: flex; align-items: center; justify-content: center;
                }
                .qty-button:hover { background: #06b6d4; color: white; transform: translateY(-2px); }
                .qty-button:active { transform: translateY(0); }

                .qty-value { font-size: 14px; font-weight: 700; color: #0f172a; min-width: 28px; text-align: center; }

                .cart-footer { padding: 14px; border-top: 1px solid rgba(15,23,42,0.04); background: transparent; }
                .cart-total { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
                .total-label { font-size: 14px; color: #475569; font-weight: 600; }
                .total-amount { font-size: 20px; color: #06b6d4; font-weight: 800; }

                .checkout-button {
                    width: 100%; padding: 12px;
                    background: linear-gradient(90deg,#06b6d4,#4f46e5);
                    color: white; border: none; border-radius: 10px;
                    font-size: 14px; font-weight: 800; cursor: pointer;
                    transition: transform .12s ease, box-shadow .12s ease;
                    box-shadow: 0 10px 30px rgba(79,70,229,0.08);
                }
                .checkout-button:hover { transform: translateY(-4px); box-shadow: 0 18px 44px rgba(79,70,229,0.12); }

                /* ---------- Scrollbars ---------- */
                .chat-messages::-webkit-scrollbar, .cart-items::-webkit-scrollbar { width: 10px; }
                .chat-messages::-webkit-scrollbar-thumb, .cart-items::-webkit-scrollbar-thumb { background: rgba(71,85,105,0.12); border-radius: 8px; }
                .chat-messages::-webkit-scrollbar-thumb:hover, .cart-items::-webkit-scrollbar-thumb:hover { background: rgba(71,85,105,0.18); }

                /* Responsive tweak */
                @media (max-width: 980px) {
                    .main-wrapper { padding: 12px; gap: 12px; flex-direction: column; align-items: stretch; }
                    .cart-sidebar { width: 100%; order: 2; }
                    . .cart-sidebar2 { width: 100%; order: 2; }
                    .main-content { width: 100%; order: 1; }
                    .chat-messages { padding: 18px; }
                }
            """)
        ),
        Body(
            Div(
                # Main chat area
                Div(  Img(src="cart.gif", cls="cart-icon"), cls="cart-sidebar"),
                Div(
                    Div(
                        Div(
        
                            Div(
                                Div("Balendra AI Shopping Assistant", cls="chat-title"),
                                Div("Ask for anything you need", cls="chat-subtitle"),
                                cls="header-info"
                            ),
                            cls="header-left"
                        ),
                        Div("Beta", cls="header-badge"),
                        cls="chat-header"
                    ),
                    Div(
                        id="chat-messages",
                        cls="chat-messages",
                        hx_get="/messages",
                        hx_trigger="load",
                        hx_swap="innerHTML"
                    ),
                    Div(
                        Form(
                            Div(
                                Input(
                                    type="text",
                                    name="message",
                                    placeholder="Ask for any product you need...",
                                    autocomplete="off",
                                    id="message-input",
                                    cls="chat-input"
                                ),
                                Button(
                                    Span("↑", id="send-icon"),
                                    Div(
                                        Div(cls="loading-dot"),
                                        Div(cls="loading-dot"),
                                        Div(cls="loading-dot"),
                                        cls="loading-dots",
                                        id="loading-dots"
                                    ),
                                    type="submit",
                                    cls="send-button",
                                    id="send-button"
                                ),
                                cls="input-wrapper",
                                id="input-wrapper"
                            ),
                            hx_post="/send",
                            hx_target="#chat-messages",
                            hx_swap="innerHTML",
                            hx_indicator="#loading-indicator",
                            **{
                                "hx-on::before-request": """
                                    const input = document.getElementById('message-input');
                                    const wrapper = document.getElementById('input-wrapper');
                                    const sendBtn = document.getElementById('send-button');
                                    const sendIcon = document.getElementById('send-icon');
                                    const loadingDots = document.getElementById('loading-dots');
                                    const chatMessages = document.getElementById('chat-messages');
                                    
                                    if (!input.value.trim()) {
                                        event.preventDefault();
                                        return false;
                                    }
                                    
                                    // Disable input
                                    input.disabled = true;
                                    sendBtn.disabled = true;
                                    wrapper.classList.add('loading');
                                    
                                    // Show loading animation
                                    sendIcon.style.display = 'none';
                                    loadingDots.classList.add('active');
                                    
                                    // Clear welcome screen if it exists
                                    const welcomeMsg = chatMessages.querySelector('.welcome-message');
                                    if (welcomeMsg) {
                                        chatMessages.innerHTML = '';
                                    }
                                    
                                    // Add user message immediately
                                    const userMsg = document.createElement('div');
                                    userMsg.className = 'message-wrapper user';
                                    userMsg.style.animation = 'fadeIn 0.3s';
                                    userMsg.innerHTML = `
                                        <div class="avatar user">U</div>
                                        <div class="message-content">
                                            <div class="message-text">${input.value}</div>
                                        </div>
                                    `;
                                    chatMessages.appendChild(userMsg);
                                    
                                    // Show typing indicator
                                    const typingIndicator = document.createElement('div');
                                    typingIndicator.id = 'typing-indicator';
                                    typingIndicator.className = 'typing-indicator';
                                    typingIndicator.innerHTML = `
                                        <div class="avatar bot">AI</div>
                                        <div class="message-content">
                                            <div class="message-text">
                                                <div class="typing-dot"></div>
                                                <div class="typing-dot"></div>
                                                <div class="typing-dot"></div>
                                            </div>
                                        </div>
                                    `;
                                    chatMessages.appendChild(typingIndicator);
                                    chatMessages.scrollTop = chatMessages.scrollHeight;
                                """,
                                "hx-on::after-request": """
                                    const input = document.getElementById('message-input');
                                    const wrapper = document.getElementById('input-wrapper');
                                    const sendBtn = document.getElementById('send-button');
                                    const sendIcon = document.getElementById('send-icon');
                                    const loadingDots = document.getElementById('loading-dots');
                                    const chatMessages = document.getElementById('chat-messages');
                                    
                                    // Re-enable input
                                    input.disabled = false;
                                    sendBtn.disabled = false;
                                    wrapper.classList.remove('loading');
                                    input.value = '';
                                    
                                    // Hide loading animation
                                    sendIcon.style.display = 'block';
                                    loadingDots.classList.remove('active');
                                    
                                    // Scroll to bottom
                                    chatMessages.scrollTop = chatMessages.scrollHeight;
                                    
                                    // Focus input
                                    input.focus();
                                """
                            }
                        ),
                        cls="chat-input-container"
                    ),
                    cls="main-content"
                ),
                # Right cart sidebar
                Div(
                    Div(
                        Div("🛒 Your Cart", cls="cart-title"),
                        Div(id="cart-count", cls="cart-count"),
                        cls="cart-header"
                    ),
                    Div(
                        Div(
                            Div("🛍️", cls="cart-empty-icon"),
                            "Your cart is empty\n\nStart shopping by asking for products!",
                            cls="cart-empty"
                        ),
                        id="cart-items",
                        cls="cart-items"
                    ),
                    Div(
                        Div(
                            Div("Total", cls="total-label"),
                            Div("$0.00", id="total-amount", cls="total-amount"),
                            cls="cart-total"
                        ),
                        Button("Checkout", cls="checkout-button"),
                        id="cart-footer",
                        cls="cart-footer",
                        style="display: none;"
                    ),
                    cls="cart-sidebar"
                ),
                cls="main-wrapper"
            ),
            Script(src="https://unpkg.com/htmx.org@1.9.10")
        )
    )
    
    # Set cookie using FastHTML's built-in response handling
    from fasthtml.common import cookie
    return response, cookie("session_id", session_id, max_age=86400*30)

@rt("/messages")
def get(request: Request):
    """Get all messages"""
    session_id = get_session_id(request)
    session_data = get_session_data(session_id)
    messages = session_data['messages']

    if not messages:
        # Welcome cards — each button now posts a category-specific message to /send
        return Div(
            Div("Welcome to Balendra AI Shopping Assistant", cls="welcome-title"),
            Div("I can help you find and add any products to your cart. Just tell me what you need!", cls="welcome-text"),
            Div(
                Div(
                    Div("Add groceries to my cart", cls="prompt-text"),
                    cls="prompt-card",
                    **{
                        "hx-post": "/send",
                        "hx-vals": '{"message":"Show me groceries"}',
                        "hx-target": "#chat-messages",
                        "hx-swap": "innerHTML"
                    }
                ),
                Div(
                    Div("I need some electronics", cls="prompt-text"),
                    cls="prompt-card",
                    **{
                        "hx-post": "/send",
                        "hx-vals": '{"message":"Show me electronics"}',
                        "hx-target": "#chat-messages",
                        "hx-swap": "innerHTML"
                    }
                ),
                Div(
                    Div("Show me home essentials", cls="prompt-text"),
                    cls="prompt-card",
                    **{
                        "hx-post": "/send",
                        "hx-vals": '{"message":"Show me home essentials"}',
                        "hx-target": "#chat-messages",
                        "hx-swap": "innerHTML"
                    }
                ),
                Div(
                    Div("Add clothing items", cls="prompt-text"),
                    cls="prompt-card",
                    **{
                        "hx-post": "/send",
                        "hx-vals": '{"message":"Show me clothing"}',
                        "hx-target": "#chat-messages",
                        "hx-swap": "innerHTML"
                    }
                ),
                cls="quick-prompts"
            ),
            cls="welcome-message"
        )

    result = []
    for msg in messages:
        result.append(ChatMessage(msg['text'], is_user=msg['is_user']))
    return result

@rt("/send")
async def post(request: Request, message: str):
    """Handle message submission"""
    session_id = get_session_id(request)
    session_data = get_session_data(session_id)
    messages = session_data['messages']
    agent_message_history = session_data['agent_message_history']
    cart = session_data['cart']

    bot_response = ""

    if message.strip():
        messages.append({"text": message, "is_user": True})

        # Check for clear command
        if message.lower().strip() in ["clear", "clear chat", "reset"]:
            messages.clear()
            session_data['agent_message_history'] = []
            bot_response = "Chat cleared! How can I help you?"
            messages.append({"text": bot_response, "is_user": False})
        else:
            # Use Pydantic agent for response
            try:
                result = await run_agent_with_logging(message, agent_message_history)
                bot_response = result.output

                # Get the new messages from this interaction only
                new_messages = result.new_messages()

                # Process tool calls for cart actions (only from new messages)
                import json
                for msg in new_messages:
                    if hasattr(msg, 'parts'):
                        for part in msg.parts:
                            if part.__class__.__name__ == 'ToolReturnPart':
                                try:
                                    cart_action = json.loads(part.content)
                                    action = cart_action.get('action')
                                    product_name = cart_action.get('product')
                                    quantity = cart_action.get('quantity', 1)
                                    price = cart_action.get('price', 0)
                                    emoji = cart_action.get('emoji', '📦')

                                    if action == 'add':
                                        if product_name in cart:
                                            cart[product_name]['quantity'] += quantity
                                        else:
                                            cart[product_name] = {
                                                'quantity': quantity,
                                                'price': price,
                                                'emoji': emoji
                                            }
                                    elif action == 'remove':
                                        cart.pop(product_name, None)
                                    elif action == 'update':
                                        if quantity > 0:
                                            if product_name in cart:
                                                cart[product_name]['quantity'] = quantity
                                            else:
                                                cart[product_name] = {
                                                    'quantity': quantity,
                                                    'price': price,
                                                    'emoji': emoji
                                                }
                                        else:
                                            cart.pop(product_name, None)
                                except (json.JSONDecodeError, AttributeError, KeyError):
                                    pass

                # Update message history with all messages
                session_data['agent_message_history'] = result.all_messages()

                messages.append({"text": bot_response, "is_user": False})
            except Exception as e:
                bot_response = f"Sorry, I encountered an error: {str(e)}"
                messages.append({"text": bot_response, "is_user": False})

    # Return user message and bot response
    result = [
        ChatMessage(message, is_user=True),
        ChatMessage(bot_response, is_user=False)
    ]

    # Add OOB cart update
    cart_div = Div(*get_cart_items(cart), id="cart-items", **{"hx-swap-oob": "innerHTML"})
    result.append(cart_div)

    return result

@rt("/cart/increase/{name}")
def post(request: Request, name: str):
    """Increase cart item quantity"""
    session_id = get_session_id(request)
    session_data = get_session_data(session_id)
    cart = session_data['cart']

    if name in cart:
        cart[name]['quantity'] += 1
    return get_cart_items(cart)

@rt("/cart/decrease/{name}")
def post(request: Request, name: str):
    """Decrease cart item quantity"""
    session_id = get_session_id(request)
    session_data = get_session_data(session_id)
    cart = session_data['cart']

    if name in cart:
        cart[name]['quantity'] -= 1
        if cart[name]['quantity'] <= 0:
            del cart[name]
    return get_cart_items(cart)

def get_cart_items(cart):
    """Generate cart items HTML"""
    if not cart:
        return [
            Div(
                Div("🛍️", cls="cart-empty-icon"),
                "Your cart is empty\n\nStart shopping by asking for products!",
                cls="cart-empty"
            )
        ]

    items = []
    total = 0.0
    item_count = 0

    for name, item_data in cart.items():
        qty = item_data['quantity']
        price = item_data['price']
        emoji = item_data['emoji']
        items.append(CartItem(name, price, emoji, qty))
        total += price * qty
        item_count += qty

    # Add cart count update (OOB)
    count_text = f"{item_count} item{'s' if item_count != 1 else ''}"
    items.append(Div(count_text, id="cart-count", cls="cart-count", **{"hx-swap-oob": "innerHTML"}))

    # Add total amount update (OOB)
    items.append(Div(f"${total:.2f}", id="total-amount", cls="total-amount", **{"hx-swap-oob": "innerHTML"}))

    # Show footer (OOB)
    items.append(Div(id="cart-footer", style="display: block;", **{"hx-swap-oob": "outerHTML"}))

    return items

serve(port=8000)
