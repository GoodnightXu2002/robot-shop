from datetime import datetime
from uuid import uuid4

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from models import CartItem, Order, Product, db


orders_bp = Blueprint("orders", __name__)
_notify_user = None
_notify_admin = None
_logistics_statuses = None


def register_order_routes(app, notify_user_func, notify_admin_func, logistics_statuses):
    global _notify_user, _notify_admin, _logistics_statuses
    _notify_user = notify_user_func
    _notify_admin = notify_admin_func
    _logistics_statuses = logistics_statuses
    app.register_blueprint(orders_bp)


@orders_bp.record_once
def register_routes(state):
    state.app.add_url_rule("/products/<int:product_id>/order", endpoint="create_order", view_func=create_order, methods=["POST"])
    state.app.add_url_rule("/orders", endpoint="orders", view_func=orders)
    state.app.add_url_rule("/orders/<int:order_id>", endpoint="order_detail", view_func=order_detail)
    state.app.add_url_rule("/orders/<int:order_id>/payment", endpoint="payment", view_func=payment)
    state.app.add_url_rule("/orders/<int:order_id>/payment/confirm", endpoint="confirm_payment", view_func=confirm_payment, methods=["POST"])
    state.app.add_url_rule("/cart/checkout", endpoint="checkout_cart", view_func=checkout_cart, methods=["POST"])


@login_required
def create_order(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    if not product.is_active:
        flash("该产品已下架，暂不可下单。", "warning")
        return redirect(url_for("product_detail", product_id=product.id))

    try:
        quantity = int(request.form.get("quantity", 1))
    except ValueError:
        quantity = 1

    if quantity <= 0 or quantity > product.stock:
        flash("购买数量必须大于 0。" if quantity <= 0 else "库存不足，无法创建订单。", "danger")
        return redirect(url_for("product_detail", product_id=product.id))

    order = Order(
        order_no="RS" + datetime.now().strftime("%Y%m%d") + uuid4().hex[:8].upper(),
        user_id=current_user.id,
        product_id=product.id,
        quantity=quantity,
        total_price=product.price * quantity,
        status="待支付",
        logistics_status="订单已提交",
    )
    product.stock -= quantity
    product.sales += quantity
    db.session.add(order)
    _notify_admin(
        "新订单创建",
        f"用户 {current_user.username} 创建了新的订单。",
        "order",
        "/admin/orders",
    )
    db.session.commit()
    flash("订单创建成功，请完成模拟支付。", "success")
    return redirect(url_for("payment", order_id=order.id))


@login_required
def orders():
    status_filter = request.args.get("status", "all").strip().lower()
    if status_filter not in {"all", "pending", "processing", "completed"}:
        status_filter = "all"

    processing_statuses = ("待确认", "已支付", "待发货", "已确认", "已发货")
    user_orders = Order.query.filter_by(user_id=current_user.id)
    order_counts = {
        "all": user_orders.count(),
        "pending": user_orders.filter(Order.status == "待支付").count(),
        "processing": user_orders.filter(Order.status.in_(processing_statuses)).count(),
        "completed": user_orders.filter(Order.status == "已完成").count(),
    }

    filtered_orders = user_orders
    if status_filter == "pending":
        filtered_orders = filtered_orders.filter(Order.status == "待支付")
    elif status_filter == "processing":
        filtered_orders = filtered_orders.filter(Order.status.in_(processing_statuses))
    elif status_filter == "completed":
        filtered_orders = filtered_orders.filter(Order.status == "已完成")

    page = request.args.get("page", 1, type=int)
    pagination = filtered_orders.order_by(Order.created_at.desc()).paginate(
        page=max(page, 1),
        per_page=10,
        error_out=False,
    )
    return render_template(
        "orders.html",
        orders=pagination.items,
        pagination=pagination,
        order_counts=order_counts,
        current_status=status_filter,
    )


@login_required
def order_detail(order_id):
    order = db.session.get(Order, order_id) or abort(404)
    if order.user_id != current_user.id:
        abort(403)
    return render_template(
        "order_detail.html",
        order=order,
        logistics_steps=_logistics_statuses,
    )


@login_required
def payment(order_id):
    order = db.session.get(Order, order_id) or abort(404)
    if order.user_id != current_user.id:
        abort(403)
    return render_template("payment.html", order=order)


@login_required
def confirm_payment(order_id):
    order = db.session.get(Order, order_id) or abort(404)
    if order.user_id != current_user.id:
        abort(403)
    if order.status == "待支付":
        order.status = "待发货"
        order.logistics_status = "支付成功"
        order.paid_at = datetime.now()
        _notify_user(
            order.user_id,
            "支付成功",
            f"订单 {order.order_no} 已完成模拟支付，等待发货。",
            "order",
            url_for("order_detail", order_id=order.id),
        )
        _notify_admin(
            "订单已支付",
            f"用户 {current_user.username} 的订单已支付，请及时处理。",
            "order",
            "/admin/orders",
        )
        db.session.commit()
        flash("模拟支付成功，订单已进入待发货状态。", "success")
    else:
        flash("该订单当前无需重复支付。", "info")
    return redirect(url_for("order_detail", order_id=order.id))


@login_required
def checkout_cart():
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not items:
        flash("购物车为空，无法生成订单。", "warning")
        return redirect(url_for("cart"))
    created_orders = []
    for item in items:
        product = item.product
        if item.quantity <= 0 or not product.is_active or product.stock <= 0:
            db.session.delete(item)
            continue
        quantity = min(item.quantity, product.stock)
        order = Order(
            order_no="RS" + datetime.now().strftime("%Y%m%d") + uuid4().hex[:8].upper(),
            user_id=current_user.id,
            product_id=product.id,
            quantity=quantity,
            total_price=product.price * quantity,
            status="待支付",
            logistics_status="订单已提交",
        )
        product.stock -= quantity
        product.sales += quantity
        db.session.add(order)
        _notify_admin(
            "新订单创建",
            f"用户 {current_user.username} 创建了新的订单。",
            "order",
            "/admin/orders",
        )
        db.session.delete(item)
        created_orders.append(order)
    db.session.commit()
    if not created_orders:
        flash("购物车商品库存不足，无法生成订单。", "danger")
        return redirect(url_for("cart"))
    session["checkout_order_ids"] = [order.id for order in created_orders]
    flash("购物车已生成订单，请完成模拟支付。", "success")
    return redirect(url_for("payment", order_id=created_orders[0].id))
