from flask import Blueprint, render_template
from sqlalchemy import func

from models import Appointment, Consultation, Notification, Order, Product, User, db


admin_dashboard_bp = Blueprint("admin_dashboard", __name__)
_admin_required = None


def register_admin_dashboard_routes(app, admin_required):
    global _admin_required
    _admin_required = admin_required
    app.register_blueprint(admin_dashboard_bp)


@admin_dashboard_bp.record_once
def register_routes(state):
    state.app.add_url_rule("/admin", endpoint="admin_dashboard", view_func=_admin_required(admin_dashboard))
    state.app.add_url_rule("/admin/statistics", endpoint="admin_statistics", view_func=_admin_required(admin_statistics))


def admin_dashboard():
    stats = dashboard_stats()
    latest_orders = Order.query.order_by(Order.created_at.desc()).limit(6).all()
    latest_consultations = Consultation.query.order_by(Consultation.created_at.desc()).limit(6).all()
    latest_appointments = Appointment.query.order_by(Appointment.created_at.desc()).limit(6).all()
    unread_notifications = (
        Notification.query.filter_by(role_target="admin", is_read=False)
        .order_by(Notification.created_at.desc())
        .limit(5)
        .all()
    )
    category_stats = category_product_counts()
    return render_template(
        "admin/dashboard.html",
        stats=stats,
        latest_orders=latest_orders,
        latest_consultations=latest_consultations,
        latest_appointments=latest_appointments,
        unread_notifications=unread_notifications,
        category_stats=category_stats,
    )


def admin_statistics():
    hot_products = Product.query.order_by(Product.sales.desc()).limit(8).all()
    category_stats = category_product_counts()
    order_status_stats = order_status_counts()
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(7).all()
    return render_template(
        "admin/statistics.html",
        stats=dashboard_stats(),
        hot_products=hot_products,
        category_stats=category_stats,
        order_status_stats=order_status_stats,
        recent_orders=recent_orders,
    )


def dashboard_stats():
    completed_sales = (
        db.session.query(func.coalesce(func.sum(Order.total_price), 0))
        .filter(Order.status == "已完成")
        .scalar()
    )
    all_sales = db.session.query(func.coalesce(func.sum(Order.total_price), 0)).scalar()
    return {
        "user_count": User.query.count(),
        "product_count": Product.query.count(),
        "order_count": Order.query.count(),
        "consultation_count": Consultation.query.count(),
        "appointment_count": Appointment.query.count(),
        "total_sales": all_sales or 0,
        "completed_sales": completed_sales or 0,
        "completed_order_count": Order.query.filter_by(status="已完成").count(),
        "pending_consultation_count": Consultation.query.filter_by(status="待处理").count(),
        "pending_appointment_count": Appointment.query.filter_by(status="待确认").count(),
    }


def category_product_counts():
    rows = (
        db.session.query(Product.category, func.count(Product.id))
        .group_by(Product.category)
        .order_by(func.count(Product.id).desc())
        .all()
    )
    total = sum(count for _, count in rows) or 1
    return [{"category": category, "count": count, "percent": round(count / total * 100)} for category, count in rows]


def order_status_counts():
    rows = (
        db.session.query(Order.status, func.count(Order.id))
        .group_by(Order.status)
        .order_by(func.count(Order.id).desc())
        .all()
    )
    total = sum(count for _, count in rows) or 1
    return [{"status": status, "count": count, "percent": round(count / total * 100)} for status, count in rows]
