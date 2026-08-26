from datetime import datetime

from flask_login import LoginManager, UserMixin
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
login_manager = LoginManager()


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(120), default="")
    phone = db.Column(db.String(30), default="")
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    orders = db.relationship("Order", back_populates="user", cascade="all, delete-orphan")
    consultations = db.relationship("Consultation", back_populates="user", cascade="all, delete-orphan")
    appointments = db.relationship("Appointment", back_populates="user", cascade="all, delete-orphan")
    wishlists = db.relationship("Wishlist", back_populates="user", cascade="all, delete-orphan")
    cart_items = db.relationship("CartItem", back_populates="user", cascade="all, delete-orphan")
    notifications = db.relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    reviews = db.relationship("Review", back_populates="user", cascade="all, delete-orphan")


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    price = db.Column(db.Float, nullable=False, default=0)
    stock = db.Column(db.Integer, nullable=False, default=0)
    sales = db.Column(db.Integer, nullable=False, default=0)
    image = db.Column(db.String(255), default="images/robot-food.svg")
    brand = db.Column(db.String(120), default="")
    country_region = db.Column(db.String(80), default="")
    description = db.Column(db.Text, nullable=False)
    detail = db.Column(db.Text, default="")
    video_url = db.Column(db.String(255), default="")
    video_desc = db.Column(db.Text, default="")
    source_url = db.Column(db.String(255), default="")
    demo_url = db.Column(db.String(255), default="")
    parameters = db.Column(db.Text, default="")
    features = db.Column(db.Text, default="")
    model = db.Column(db.String(120), default="")
    size = db.Column(db.String(120), default="")
    battery_life = db.Column(db.String(120), default="")
    charge_time = db.Column(db.String(120), default="")
    speed = db.Column(db.String(120), default="")
    scene = db.Column(db.Text, nullable=False)
    is_hot = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    orders = db.relationship("Order", back_populates="product")
    wishlists = db.relationship("Wishlist", back_populates="product", cascade="all, delete-orphan")
    cart_items = db.relationship("CartItem", back_populates="product", cascade="all, delete-orphan")
    reviews = db.relationship("Review", back_populates="product", cascade="all, delete-orphan")


class Consultation(db.Model):
    __tablename__ = "consultations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"))
    name = db.Column(db.String(80), nullable=False)
    contact = db.Column(db.String(80), nullable=False)
    title = db.Column(db.String(150), nullable=False, default="产品咨询")
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="待处理")
    admin_reply = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship("User", back_populates="consultations")
    product = db.relationship("Product")


class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    service_type = db.Column(db.String(80), nullable=False)
    appointment_time = db.Column(db.String(80), nullable=False)
    appointment_date = db.Column(db.String(40), default="")
    time_slot = db.Column(db.String(80), default="")
    address = db.Column(db.String(255))
    contact_name = db.Column(db.String(80), default="")
    contact = db.Column(db.String(80), nullable=False)
    remark = db.Column(db.Text)
    process_note = db.Column(db.Text, default="")
    status = db.Column(db.String(30), nullable=False, default="待确认")
    created_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship("User", back_populates="appointments")


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(40), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    total_price = db.Column(db.Float, nullable=False, default=0)
    status = db.Column(db.String(30), nullable=False, default="待确认")
    logistics_status = db.Column(db.String(30), nullable=False, default="订单已提交")
    paid_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship("User", back_populates="orders")
    product = db.relationship("Product", back_populates="orders")


class Wishlist(db.Model):
    __tablename__ = "wishlists"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship("User", back_populates="wishlists")
    product = db.relationship("Product", back_populates="wishlists")

    __table_args__ = (db.UniqueConstraint("user_id", "product_id", name="uq_user_product_wishlist"),)


class CartItem(db.Model):
    __tablename__ = "cart_items"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship("User", back_populates="cart_items")
    product = db.relationship("Product", back_populates="cart_items")

    __table_args__ = (db.UniqueConstraint("user_id", "product_id", name="uq_user_product_cart"),)


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False, default=5)
    content = db.Column(db.Text, nullable=False)
    is_verified_purchase = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship("User", back_populates="reviews")
    product = db.relationship("Product", back_populates="reviews")

    __table_args__ = (db.UniqueConstraint("user_id", "product_id", name="uq_user_product_review"),)


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(40), nullable=False, default="system")
    is_read = db.Column(db.Boolean, default=False)
    link = db.Column(db.String(255), default="")
    role_target = db.Column(db.String(30), nullable=False, default="user")
    created_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship("User", back_populates="notifications")


class AIChatLog(db.Model):
    __tablename__ = "ai_chat_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    page_url = db.Column(db.String(500), default="")
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"))
    created_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship("User")
    product = db.relationship("Product")
