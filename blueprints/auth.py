from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from models import Appointment, Consultation, Order, Review, User, Wishlist, db


auth_bp = Blueprint("auth", __name__)
_notify_admin = None


def register_auth_routes(app, notify_admin_func):
    global _notify_admin
    _notify_admin = notify_admin_func
    app.register_blueprint(auth_bp)


@auth_bp.record_once
def register_routes(state):
    state.app.add_url_rule("/register", endpoint="register", view_func=register, methods=["GET", "POST"])
    state.app.add_url_rule("/login", endpoint="login", view_func=login, methods=["GET", "POST"])
    state.app.add_url_rule("/logout", endpoint="logout", view_func=logout)
    state.app.add_url_rule("/user/center", endpoint="user_center", view_func=user_center)


def register():
    if current_user.is_authenticated:
        return redirect(url_for("user_center"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not password:
            flash("用户名和密码不能为空。", "danger")
        elif len(password) < 6:
            flash("密码长度不能少于 6 位。", "danger")
        elif password != confirm_password:
            flash("两次输入的密码不一致。", "danger")
        elif User.query.filter_by(username=username).first():
            flash("该用户名已存在，请更换后重试。", "danger")
        else:
            db.session.add(
                User(
                    username=username,
                    email=email,
                    phone=phone,
                    password_hash=generate_password_hash(password),
                    is_admin=False,
                )
            )
            _notify_admin(
                "新用户注册",
                f"用户 {username} 已完成注册。",
                "system",
                "/admin/users",
            )
            db.session.commit()
            flash("注册成功，请登录。", "success")
            return redirect(url_for("login"))

    return render_template("register.html")


def login():
    if current_user.is_authenticated:
        return redirect(url_for("user_center"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash("登录成功。", "success")
            next_url = safe_next_url(request.args.get("next"))
            default_url = url_for("admin_dashboard") if user.is_admin else url_for("user_center")
            return redirect(next_url or default_url)

        flash("用户名或密码错误。", "danger")

    return render_template("login.html")


def safe_next_url(next_url):
    if not next_url or not next_url.startswith("/") or next_url.startswith("//"):
        return None
    return next_url


@login_required
def logout():
    logout_user()
    flash("已退出登录。", "info")
    return redirect(url_for("index"))


@login_required
def user_center():
    all_orders = (
        Order.query.filter_by(user_id=current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    consultation_list = (
        Consultation.query.filter_by(user_id=current_user.id)
        .order_by(Consultation.created_at.desc())
        .limit(8)
        .all()
    )
    appointment_list = (
        Appointment.query.filter_by(user_id=current_user.id)
        .order_by(Appointment.created_at.desc())
        .limit(8)
        .all()
    )
    wishlist_items = (
        Wishlist.query.filter_by(user_id=current_user.id)
        .order_by(Wishlist.created_at.desc())
        .all()
    )
    review_items = (
        Review.query.filter_by(user_id=current_user.id)
        .order_by(Review.created_at.desc())
        .limit(6)
        .all()
    )
    service_records = [
        {
            "kind": "consultation",
            "title": item.title,
            "status": item.status,
            "created_at": item.created_at,
        }
        for item in consultation_list
    ] + [
        {
            "kind": "appointment",
            "title": item.service_type,
            "status": item.status,
            "created_at": item.created_at,
        }
        for item in appointment_list
    ]
    service_records.sort(key=lambda item: item["created_at"], reverse=True)
    order_status_counts = {
        "pending_payment": len([item for item in all_orders if item.status == "待支付"]),
        "pending_shipment": len(
            [item for item in all_orders if item.status in ("已支付", "待发货", "已确认")]
        ),
        "pending_receipt": len([item for item in all_orders if item.status == "已发货"]),
        "completed": len([item for item in all_orders if item.status == "已完成"]),
    }
    stats = {
        "order_count": len(all_orders),
        "consultation_count": Consultation.query.filter_by(user_id=current_user.id).count(),
        "appointment_count": Appointment.query.filter_by(user_id=current_user.id).count(),
        "wishlist_count": len(wishlist_items),
        "review_count": Review.query.filter_by(user_id=current_user.id).count(),
    }
    return render_template(
        "user_center.html",
        stats=stats,
        order_status_counts=order_status_counts,
        orders=all_orders[:4],
        consultations=consultation_list,
        appointments=appointment_list,
        service_records=service_records[:6],
        wishlist_items=wishlist_items,
        reviews=review_items,
    )
