from datetime import datetime
from functools import wraps

from flask import Flask, abort, render_template
from flask_login import current_user, login_required
from sqlalchemy import func

from blueprints.admin_appointments import register_admin_appointment_routes
from blueprints.appointments import register_appointment_routes
from blueprints.auth import register_auth_routes
from blueprints.admin_consultations import register_admin_consultation_routes
from blueprints.admin_dashboard import register_admin_dashboard_routes
from blueprints.admin_orders import register_admin_order_routes
from blueprints.admin_products import register_admin_product_routes
from blueprints.admin_reviews import register_admin_review_routes
from blueprints.admin_users import register_admin_user_routes
from blueprints.ai import register_ai_routes
from blueprints.cart import register_cart_routes
from blueprints.consultations import register_consultation_routes
from blueprints.notifications import register_notification_routes
from blueprints.orders import register_order_routes
from blueprints.public import register_public_routes
from blueprints.reviews import register_review_routes
from config import get_config
from models import CartItem, Notification, User, db, login_manager
from services.database import init_database
from services.notifications import notify_admin, notify_user


ORDER_STATUSES = ["待支付", "已支付", "待发货", "已确认", "已发货", "已完成", "已取消"]
LOGISTICS_STATUSES = ["订单已提交", "支付成功", "仓库配货", "已发货", "运输中", "已签收"]
CONSULTATION_STATUSES = ["待处理", "处理中", "已回复", "已关闭"]
APPOINTMENT_STATUSES = ["待确认", "已确认", "服务中", "已完成", "已取消"]
SERVICE_TYPES = ["安装调试", "故障维修", "定期维护", "软件升级", "使用培训"]
TIME_SLOTS = ["09:00-11:00", "11:00-13:00", "14:00-16:00", "16:00-18:00"]


def create_app():
    app = Flask(__name__)
    app.config.from_object(get_config())

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "login"
    login_manager.login_message = "请先登录后再使用该功能"
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.context_processor
    def inject_globals():
        cart_count = 0
        unread_user_notifications = 0
        unread_admin_notifications = 0
        if current_user.is_authenticated:
            cart_count = db.session.query(func.coalesce(func.sum(CartItem.quantity), 0)).filter_by(user_id=current_user.id).scalar() or 0
            unread_user_notifications = Notification.query.filter_by(user_id=current_user.id, role_target="user", is_read=False).count()
            if current_user.is_admin:
                unread_admin_notifications = Notification.query.filter_by(role_target="admin", is_read=False).count()
        return {
            "now": datetime.now(),
            "cart_count": cart_count,
            "unread_user_notifications": unread_user_notifications,
            "unread_admin_notifications": unread_admin_notifications,
        }

    def admin_required(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(*args, **kwargs):
            if not current_user.is_admin:
                abort(403)
            return view_func(*args, **kwargs)

        return wrapper

    register_ai_routes(app, admin_required)
    register_public_routes(app)
    register_auth_routes(app, notify_admin)
    register_cart_routes(app)
    register_order_routes(app, notify_user, notify_admin, LOGISTICS_STATUSES)
    register_admin_dashboard_routes(app, admin_required)
    register_admin_product_routes(app, admin_required)
    register_admin_order_routes(app, admin_required, notify_user, ORDER_STATUSES, LOGISTICS_STATUSES)
    register_admin_user_routes(app, admin_required)
    register_admin_consultation_routes(app, admin_required, notify_user, CONSULTATION_STATUSES)
    register_admin_appointment_routes(app, admin_required, notify_user, APPOINTMENT_STATUSES)
    register_admin_review_routes(app, admin_required)
    register_notification_routes(app, admin_required)
    register_review_routes(app)
    register_consultation_routes(app, notify_admin)
    register_appointment_routes(app, notify_admin, APPOINTMENT_STATUSES, SERVICE_TYPES, TIME_SLOTS)

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("403.html"), 403

    return app


app = create_app()


def run_debug_enabled(flask_app):
    return bool(flask_app.config.get("DEBUG", False))


if __name__ == "__main__":
    init_database(app)
    app.run(host="127.0.0.1", port=5000, debug=run_debug_enabled(app))
