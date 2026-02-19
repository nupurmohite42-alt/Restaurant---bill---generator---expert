import streamlit as st
import os
from datetime import datetime
import base64
from io import BytesIO
import json

# For PDF generation - install with: pip install reportlab
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    st.warning("Install reportlab for PDF generation: pip install reportlab")


# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="Bravo Restaurant", page_icon="🍽️", layout="wide")


# ---------------- CONSTANTS ----------------
RESTAURANT = "Bravo"
ASSETS_DIR = "assets"
FOOD_DIR = os.path.join(ASSETS_DIR, "food")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")
BILLS_DIR = "bills"  # Directory to save bills
GST_RATE = 0.18

# Create bills directory if it doesn't exist
os.makedirs(BILLS_DIR, exist_ok=True)

# Coupon codes
COUPONS = {
    "BRAVO10": {"type": "percent", "value": 10},   # 10% off
    "WELCOME50": {"type": "flat", "value": 50},    # ₹50 off
    "BRAVO100": {"type": "flat", "value": 100},    # ₹100 off
}

# Payment methods
PAYMENT_METHODS = ["Cash", "Card (Credit/Debit)", "UPI", "Net Banking"]


# ---------------- MENU ----------------
MENU = {
    "Breakfast": {
        "Idli": 30,
        "Ghee Dosa": 65,
        "Puri": 40,
        "Mysore Bonda": 50,
        "Egg Omelette": 50,
        "Chapati": 35,
    },
    "Main Course": {
        "Veg Biryani": 259,
        "Chicken Biryani": 349,
        "Mutton Biryani": 499,
        "Veg Fried Rice": 150,
        "Egg Fried Rice": 170,
    },
    "Beverages": {
        "Tea": 25,
        "Coffee": 40,
        "Soft Drink": 45,
    },
    "Desserts": {
        "Gulab Jamun": 60,
        "Ice Cream Chocolate": 80,
        "Vanilla": 70,
        "Kunafa": 110,
        "Pastries": 50,
    },
}


# ---------------- SESSION STATE INITIALIZATION ----------------
def init_session_state():
    """Initialize all session state variables"""
    if "cart" not in st.session_state:
        st.session_state.cart = {}
    if "bill_generated" not in st.session_state:
        st.session_state.bill_generated = False
    if "applied_coupon" not in st.session_state:
        st.session_state.applied_coupon = None
    if "discount_amount" not in st.session_state:
        st.session_state.discount_amount = 0.0
    if "payment_method" not in st.session_state:
        st.session_state.payment_method = None
    if "customer_name" not in st.session_state:
        st.session_state.customer_name = ""
    if "bill_number" not in st.session_state:
        # Generate unique bill number
        st.session_state.bill_number = f"BRV{datetime.now().strftime('%Y%m%d%H%M%S')}"

init_session_state()


# ---------------- HELPER FUNCTIONS ----------------
def slug(name: str) -> str:
    """Convert name to filename-friendly format"""
    return name.strip().lower().replace(" ", "_")


def safe_find_image(item_name: str):
    """Find image file for menu item"""
    base = slug(item_name)
    for ext in ("jpg", "png", "jpeg"):
        p = os.path.join(FOOD_DIR, f"{base}.{ext}")
        if os.path.exists(p):
            return p
    return None


def add_to_cart(item, price, qty):
    """Add item to cart"""
    if item in st.session_state.cart:
        st.session_state.cart[item]["qty"] += qty
    else:
        st.session_state.cart[item] = {"price": price, "qty": qty}
    st.session_state.bill_generated = False


def remove_item(item):
    """Remove item from cart"""
    st.session_state.cart.pop(item, None)
    st.session_state.bill_generated = False


def clear_cart():
    """Clear entire cart and reset state"""
    st.session_state.cart = {}
    st.session_state.bill_generated = False
    st.session_state.applied_coupon = None
    st.session_state.discount_amount = 0.0
    st.session_state.payment_method = None
    st.session_state.bill_number = f"BRV{datetime.now().strftime('%Y%m%d%H%M%S')}"


def compute_subtotal():
    """Calculate cart subtotal"""
    return sum(v["price"] * v["qty"] for v in st.session_state.cart.values())


def calc_discount(subtotal: float, coupon_code: str):
    """Calculate discount amount and return (discount, error_message)"""
    code = coupon_code.strip().upper()
    if code == "":
        return 0.0, "Enter a coupon code."

    if code not in COUPONS:
        return 0.0, "Invalid coupon code."

    rule = COUPONS[code]
    if rule["type"] == "percent":
        pct = float(rule["value"])
        discount = subtotal * (pct / 100.0)
    elif rule["type"] == "flat":
        discount = float(rule["value"])
    else:
        return 0.0, "Coupon config error."

    discount = max(0.0, min(discount, subtotal))
    return discount, None


def logo_to_base64(path):
    """Convert logo to base64 for HTML display"""
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def generate_pdf_bill():
    """Generate PDF bill and return BytesIO object"""
    if not PDF_AVAILABLE:
        return None

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Header
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width/2, height - 50, f"{RESTAURANT} Restaurant")

    c.setFont("Helvetica", 10)
    c.drawCentredString(width/2, height - 70, "Your Favorite Dining Destination")
    c.drawCentredString(width/2, height - 85, f"Bill No: {st.session_state.bill_number}")

    # Date and time
    now = datetime.now()
    c.drawString(50, height - 110, f"Date: {now.strftime('%d %B %Y')}")
    c.drawString(50, height - 125, f"Time: {now.strftime('%I:%M %p')}")

    # Customer name
    if st.session_state.customer_name:
        c.drawString(50, height - 140, f"Customer: {st.session_state.customer_name}")

    # Line separator
    c.line(50, height - 155, width - 50, height - 155)

    # Table header
    y_position = height - 185
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y_position, "Item")
    c.drawString(300, y_position, "Qty")
    c.drawString(370, y_position, "Price")
    c.drawString(470, y_position, "Amount")

    c.line(50, y_position - 5, width - 50, y_position - 5)

    # Items
    c.setFont("Helvetica", 10)
    y_position -= 25

    for item, data in st.session_state.cart.items():
        if y_position < 100:  # Check if we need a new page
            c.showPage()
            y_position = height - 50
            c.setFont("Helvetica", 10)

        amount = data["price"] * data["qty"]
        c.drawString(50, y_position, item[:30])  # Truncate long names
        c.drawString(300, y_position, str(data["qty"]))
        c.drawString(370, y_position, f"₹{data['price']}")
        c.drawString(470, y_position, f"₹{amount}")
        y_position -= 20

    # Calculations
    y_position -= 20
    c.line(50, y_position, width - 50, y_position)
    y_position -= 25

    subtotal = compute_subtotal()
    discount = min(st.session_state.discount_amount, float(subtotal))
    after_discount = max(0.0, float(subtotal) - float(discount))
    gst = after_discount * GST_RATE
    total = after_discount + gst

    c.setFont("Helvetica", 11)
    c.drawString(370, y_position, "Subtotal:")
    c.drawString(470, y_position, f"₹{subtotal:.2f}")
    y_position -= 20

    if st.session_state.applied_coupon:
        c.drawString(370, y_position, f"Discount ({st.session_state.applied_coupon}):")
        c.drawString(470, y_position, f"-₹{discount:.2f}")
        y_position -= 20

    c.drawString(370, y_position, "GST (18%):")
    c.drawString(470, y_position, f"₹{gst:.2f}")
    y_position -= 20

    c.line(370, y_position + 5, width - 50, y_position + 5)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(370, y_position - 10, "Total:")
    c.drawString(470, y_position - 10, f"₹{total:.2f}")

    # Payment method
    if st.session_state.payment_method:
        y_position -= 40
        c.setFont("Helvetica", 10)
        c.drawString(50, y_position, f"Payment Method: {st.session_state.payment_method}")

    # Footer
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(width/2, 50, "Thank you for dining with us!")
    c.drawCentredString(width/2, 35, "Please visit again!")

    c.save()
    buffer.seek(0)
    return buffer


def save_bill_json():
    """Save bill data as JSON for record keeping"""
    bill_data = {
        "bill_number": st.session_state.bill_number,
        "timestamp": datetime.now().isoformat(),
        "customer_name": st.session_state.customer_name,
        "items": [
            {
                "name": item,
                "quantity": data["qty"],
                "price": data["price"],
                "amount": data["qty"] * data["price"]
            }
            for item, data in st.session_state.cart.items()
        ],
        "subtotal": compute_subtotal(),
        "coupon": st.session_state.applied_coupon,
        "discount": st.session_state.discount_amount,
        "gst": (compute_subtotal() - st.session_state.discount_amount) * GST_RATE,
        "total": (compute_subtotal() - st.session_state.discount_amount) * (1 + GST_RATE),
        "payment_method": st.session_state.payment_method
    }

    filename = os.path.join(BILLS_DIR, f"{st.session_state.bill_number}.json")
    with open(filename, "w") as f:
        json.dump(bill_data, f, indent=2)

    return filename


# ---------------- CUSTOM CSS ----------------
st.markdown("""
<style>
/* Warm background */
html, body, [data-testid="stAppViewContainer"], .main {
  background: linear-gradient(180deg, #fff1e6 0%, #fffaf3 45%, #fff1e6 100%) !important;
}

/* Banner */
.bravo-banner{
  width: 100%;
  border-radius: 18px;
  padding: 18px 20px;
  background: linear-gradient(90deg, #fde68a 0%, #fdba74 60%, #fb923c 100%);
  box-shadow: 0 10px 30px rgba(0,0,0,0.10);
  display: flex;
  gap: 18px;
  align-items: center;
  margin-bottom: 18px;
}
.bravo-logo{
  height: 90px;
  width: auto;
  border-radius: 14px;
  background: rgba(255,255,255,0.28);
  padding: 8px;
}
.bravo-title{ 
  font-size: 34px; 
  font-weight: 900; 
  color: #111827; 
  margin: 0; 
  line-height: 1.1; 
}
.bravo-sub{ 
  margin-top: 6px; 
  color: rgba(17,24,39,0.75); 
  font-weight: 700; 
}

/* Section titles */
.section-title{ 
  font-size: 28px; 
  font-weight: 900; 
  color: #111827; 
  margin: 0 0 10px 0; 
}

/* Cards */
.card{
  background: rgba(255,255,255,0.92);
  border: 1px solid rgba(17,24,39,0.10);
  border-radius: 16px;
  padding: 14px;
  box-shadow: 0 6px 18px rgba(0,0,0,0.05);
  margin-bottom: 10px;
}

/* Labels */
label[data-testid="stWidgetLabel"] p {
  font-size: 16px !important;
  font-weight: 800 !important;
  color: #111827 !important;
}

/* Dropdowns */
div[data-baseweb="select"] > div {
  min-height: 52px !important;
  font-size: 16px !important;
  border-radius: 12px !important;
  background: rgba(255,255,255,0.95) !important;
  border: 1px solid rgba(17,24,39,0.12) !important;
}

/* Inputs */
input, textarea {
  background: rgba(255,255,255,0.95) !important;
  border: 1px solid rgba(17,24,39,0.12) !important;
  color: #111827 !important;
  border-radius: 12px !important;
}

/* Buttons */
.stButton > button{
  background: #111827 !important;
  color: #ffffff !important;
  border-radius: 12px !important;
  font-weight: 900 !important;
  padding: 10px 14px !important;
  border: 1px solid rgba(17,24,39,0.0) !important;
  transition: all 0.3s ease !important;
}
.stButton > button *{
  color: #ffffff !important;
  fill: #ffffff !important;
}
.stButton > button:hover{
  background: #1f2937 !important;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
}

/* Download button special styling */
.stDownloadButton > button {
  background: #059669 !important;
  color: #ffffff !important;
}
.stDownloadButton > button:hover {
  background: #047857 !important;
}

/* Number input */
[data-baseweb="stepper"] button{
  background:#111827 !important;
  color:#ffffff !important;
  border-radius: 10px !important;
}
[data-baseweb="stepper"] button *{ 
  color:#ffffff !important; 
  fill:#ffffff !important; 
}

/* Radio buttons */
div[role="radiogroup"] label {
  background: rgba(255,255,255,0.95) !important;
  padding: 12px !important;
  border-radius: 10px !important;
  border: 1px solid rgba(17,24,39,0.12) !important;
  margin-bottom: 8px !important;
}

/* Reduce top padding */
.block-container { padding-top: 1rem; }

/* Success box styling */
.success-box {
  background: #d1fae5;
  border: 2px solid #059669;
  border-radius: 12px;
  padding: 16px;
  margin: 10px 0;
  text-align: center;
}
</style>
""", unsafe_allow_html=True)


# ---------------- BANNER ----------------
now_txt = datetime.now().strftime("%d %b %Y • %I:%M %p")
b64 = logo_to_base64(LOGO_PATH)

if b64:
    st.markdown(
        f"""
        <div class="bravo-banner">
          <img class="bravo-logo" src="data:image/png;base64,{b64}" />
          <div>
            <div class="bravo-title">{RESTAURANT} Restaurant</div>
            <div class="bravo-sub">{now_txt}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.markdown(
        f"""
        <div class="bravo-banner">
          <div>
            <div class="bravo-title">{RESTAURANT} Restaurant</div>
            <div class="bravo-sub">{now_txt}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# ---------------- MAIN LAYOUT ----------------
left, right = st.columns([2, 1], gap="large")


# ---------- LEFT: MENU ----------
with left:
    st.markdown('<div class="section-title">🍽️ MENU</div>', unsafe_allow_html=True)
    category = st.selectbox("Select Category", list(MENU.keys()), key="category_select")
    st.write("")

    for item, price in MENU[category].items():
        img = safe_find_image(item)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 2.2, 1.2], vertical_alignment="center")

        with c1:
            if img:
                st.image(img, width=120)
            else:
                st.image("https://via.placeholder.com/120x120?text=No+Image", width=120)

        with c2:
            st.markdown(f"### {item}")
            st.caption(f"₹ {price}")

        with c3:
            qty = st.number_input("Qty", min_value=1, max_value=20, value=1, step=1, 
                                key=f"qty_{item}_{category}", label_visibility="collapsed")
            if st.button("➕ Add", key=f"add_{item}_{category}", use_container_width=True):
                add_to_cart(item, price, int(qty))
                st.toast(f"✅ Added {item} x{qty}", icon="✅")
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


# ---------- RIGHT: CART & CHECKOUT ----------
with right:
    st.markdown('<div class="section-title">🛒 Cart</div>', unsafe_allow_html=True)

    if not st.session_state.cart:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.info("🛒 Cart is empty. Add items from menu!", icon="ℹ️")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        # Display cart items
        for item, data in list(st.session_state.cart.items()):
            amount = data["price"] * data["qty"]
            st.markdown('<div class="card">', unsafe_allow_html=True)

            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"*{item}*")
                st.caption(f"Qty: {data['qty']} × ₹{data['price']} = ₹{amount}")
            with col2:
                if st.button("🗑️", key=f"rm_{item}", use_container_width=True, 
                           help="Remove item"):
                    remove_item(item)
                    st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

        st.write("")

        # Customer Name Input
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 👤 Customer Details")
        st.session_state.customer_name = st.text_input(
            "Customer Name (Optional)", 
            value=st.session_state.customer_name,
            placeholder="Enter customer name",
            key="customer_name_input"
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # Coupon section
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 🎫 Coupon Code")

        c1, c2 = st.columns([2, 1])
        with c1:
            coupon_input = st.text_input(
                "Enter code", 
                value=(st.session_state.applied_coupon or ""),
                placeholder="Enter coupon code",
                label_visibility="collapsed"
            )
        with c2:
            apply_clicked = st.button("Apply", use_container_width=True, key="apply_coupon_btn")

        if apply_clicked:
            subtotal_now = compute_subtotal()
            disc, err = calc_discount(subtotal_now, coupon_input)
            if err:
                st.session_state.applied_coupon = None
                st.session_state.discount_amount = 0.0
                st.error(err)
            else:
                st.session_state.applied_coupon = coupon_input.strip().upper()
                st.session_state.discount_amount = disc
                st.success(f"✅ Coupon {st.session_state.applied_coupon} applied!")
                st.rerun()

        if st.session_state.applied_coupon:
            if st.button("Remove Coupon", use_container_width=True, key="remove_coupon_btn"):
                st.session_state.applied_coupon = None
                st.session_state.discount_amount = 0.0
                st.rerun()

        with st.expander("💡 Available Coupons"):
            for code, rule in COUPONS.items():
                if rule["type"] == "percent":
                    st.caption(f"*{code}*: {rule['value']}% off")
                else:
                    st.caption(f"*{code}*: ₹{rule['value']} off")

        st.markdown("</div>", unsafe_allow_html=True)

        # Bill Summary
        subtotal = compute_subtotal()
        discount = min(st.session_state.discount_amount, float(subtotal))
        after_discount = max(0.0, float(subtotal) - float(discount))
        gst = after_discount * GST_RATE
        total = after_discount + gst

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 💰 Bill Summary")

        st.write(f"*Subtotal:* ₹{subtotal:.2f}")
        if st.session_state.applied_coupon:
            st.write(f"*Discount ({st.session_state.applied_coupon}):* -₹{discount:.2f}")
            st.write(f"*After Discount:* ₹{after_discount:.2f}")
        st.write(f"*GST (18%):* ₹{gst:.2f}")
        st.markdown(f"### 💳 *Total: ₹{total:.2f}*")
        st.caption(f"Bill No: {st.session_state.bill_number}")

        st.markdown("</div>", unsafe_allow_html=True)

        # Payment Method Selection
        if not st.session_state.bill_generated:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### 💳 Payment Method")
            payment_method = st.radio(
                "Select payment method",
                PAYMENT_METHODS,
                key="payment_radio",
                label_visibility="collapsed"
            )
            st.session_state.payment_method = payment_method
            st.markdown("</div>", unsafe_allow_html=True)

        # Action Buttons
        st.write("")
        cA, cB = st.columns(2)
        with cA:
            if st.button("🗑️ Clear Cart", use_container_width=True, key="clear_cart_btn"):
                clear_cart()
                st.rerun()
        with cB:
            if not st.session_state.bill_generated:
                if st.button("✅ Generate Bill", use_container_width=True, 
                           key="generate_bill_btn", type="primary"):
                    if st.session_state.payment_method:
                        st.session_state.bill_generated = True
                        st.rerun()
                    else:
                        st.error("Please select a payment method!")

        # Bill Generated Section
        if st.session_state.bill_generated:
            st.markdown("""
            <div class="success-box">
                <h3 style="color: #047857; margin: 0;">✅ Bill Generated Successfully!</h3>
                <p style="margin: 5px 0 0 0; color: #065f46;">Payment: {}</p>
            </div>
            """.format(st.session_state.payment_method), unsafe_allow_html=True)

            # Save bill as JSON
            json_file = save_bill_json()

            # Download Buttons
            col1, col2, col3 = st.columns(3)

            with col1:
                # Download as JSON
                with open(json_file, "r") as f:
                    st.download_button(
                        label="📄 JSON",
                        data=f.read(),
                        file_name=f"{st.session_state.bill_number}.json",
                        mime="application/json",
                        use_container_width=True
                    )

            with col2:
                # Download as PDF
                if PDF_AVAILABLE:
                    pdf_buffer = generate_pdf_bill()
                    if pdf_buffer:
                        st.download_button(
                            label="📑 PDF",
                            data=pdf_buffer,
                            file_name=f"{st.session_state.bill_number}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                else:
                    st.button("📑 PDF", disabled=True, use_container_width=True,
                            help="Install reportlab")

            with col3:
                if st.button("🆕 New Order", use_container_width=True, key="new_order_btn"):
                    clear_cart()
                    st.rerun()

            # Display bill details in expander
            with st.expander("📋 View Bill Details"):
                for item, data in st.session_state.cart.items():
                    st.write(f"*{item}* - Qty: {data['qty']} × ₹{data['price']} = ₹{data['qty'] * data['price']}")
                st.divider()
                st.write(f"*Subtotal:* ₹{subtotal:.2f}")
                if discount > 0:
                    st.write(f"*Discount:* -₹{discount:.2f}")
                st.write(f"*GST (18%):* ₹{gst:.2f}")
                st.write(f"*Total:* ₹{total:.2f}")


# ---------------- FOOTER ----------------
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #6b7280; font-size: 14px;'>"
    f"© 2026 {RESTAURANT} Restaurant | Bill Management System v2.0"
    "</p>", 
    unsafe_allow_html=True
)