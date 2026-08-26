from flask import Blueprint, flash, redirect, render_template, request, url_for

from models import Order, db


admin_orders_bp = Blueprint("admin_orders", __name__)
_admin_required = None
_notify_user = None
_order_statuses = None
_logistics_statuses = None


def register_admin_order_routes(app, admin_required, notify_user_func, order_statuses, logistics_statuses):
    global _admin_required, _notify_user, _order_statuses, _logistics_statuses
    _admin_required = admin_required
    _notify_user = notify_user_func
    _order_statuses = order_statuses
    _logistics_statuses = logistics_statuses
    app.register_blueprint(admin_orders_bp)


@admin_orders_bp.record_once
def register_routes(state):
    state.app.add_url_rule("/admin/orders", endpoint="admin_orders", view_func=_admin_required(admin_orders))
    state.app.add_url_rule(
        "/admin/orders/<int:order_id>/status",
        endpoint="admin_order_status",
        view_func=_admin_required(admin_order_status),
        methods=["POST"],
    )


def admin_orders():
    order_list = Order.query.order_by(Order.created_at.desc()).all()
    return render_template(
        "admin/orders.html",
        orders=order_list,
        statuses=_order_statuses,
        logistics_statuses=_logistics_statuses,
    )


def admin_order_status(order_id):
    order = db.session.get(Order, order_id) or abort(404)
    old_status = order.status
    old_logistics_status = order.logistics_status
    new_status = request.form.get("status", order.status)
    if new_status in _order_statuses:
        order.status = new_status
    new_logistics_status = request.form.get("logistics_status", order.logistics_status)
    if new_logistics_status in _logistics_statuses:
        order.logistics_status = new_logistics_status
    if order.status != old_status or order.logistics_status != old_logistics_status:
        _notify_user(
            order.user_id,
            "订单状态更新",
            f"您的订单 {order.order_no} 状态或物流状态已更新。",
            "logistics" if order.logistics_status != old_logistics_status else "order",
            url_for("order_detail", order_id=order.id),
        )
    db.session.commit()
    flash("订单状态已更新。", "success")
    return redirect(url_for("admin_orders"))
