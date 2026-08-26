from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import CartItem, Product, Wishlist, db


cart_bp = Blueprint("cart", __name__)


def register_cart_routes(app):
    app.register_blueprint(cart_bp)


@cart_bp.record_once
def register_routes(state):
    state.app.add_url_rule("/cart", endpoint="cart", view_func=cart)
    state.app.add_url_rule("/cart/add/<int:product_id>", endpoint="add_cart", view_func=add_cart, methods=["POST"])
    state.app.add_url_rule("/cart/<int:item_id>/update", endpoint="update_cart", view_func=update_cart, methods=["POST"])
    state.app.add_url_rule("/cart/<int:item_id>/remove", endpoint="remove_cart", view_func=remove_cart, methods=["POST"])
    state.app.add_url_rule("/wishlist/add/<int:product_id>", endpoint="add_wishlist", view_func=add_wishlist, methods=["POST"])
    state.app.add_url_rule("/wishlist/remove/<int:wishlist_id>", endpoint="remove_wishlist", view_func=remove_wishlist, methods=["POST"])


@login_required
def cart():
    items = (
        CartItem.query.filter_by(user_id=current_user.id)
        .order_by(CartItem.created_at.desc())
        .all()
    )
    total_price = sum(item.product.price * item.quantity for item in items)
    return render_template("cart.html", items=items, total_price=total_price)


@login_required
def add_cart(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    try:
        quantity = int(request.form.get("quantity", 1))
    except ValueError:
        quantity = 1
    quantity = max(quantity, 1)
    if not product.is_active or product.stock <= 0:
        flash("该产品暂不可加入购物车。", "warning")
        return redirect(url_for("product_detail", product_id=product.id))
    item = CartItem.query.filter_by(user_id=current_user.id, product_id=product.id).first()
    if item:
        item.quantity = min(item.quantity + quantity, product.stock)
    else:
        db.session.add(CartItem(user_id=current_user.id, product_id=product.id, quantity=min(quantity, product.stock)))
    db.session.commit()
    flash("已加入购物车。", "success")
    return redirect(url_for("cart"))


@login_required
def update_cart(item_id):
    item = db.session.get(CartItem, item_id) or abort(404)
    if item.user_id != current_user.id:
        abort(403)
    try:
        quantity = int(request.form.get("quantity", 1))
    except ValueError:
        quantity = 1
    if quantity <= 0 or item.product.stock <= 0:
        db.session.delete(item)
    else:
        item.quantity = min(quantity, item.product.stock)
    db.session.commit()
    flash("购物车已更新。", "success")
    return redirect(url_for("cart"))


@login_required
def remove_cart(item_id):
    item = db.session.get(CartItem, item_id) or abort(404)
    if item.user_id != current_user.id:
        abort(403)
    db.session.delete(item)
    db.session.commit()
    flash("商品已从购物车删除。", "success")
    return redirect(url_for("cart"))


@login_required
def add_wishlist(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    exists = Wishlist.query.filter_by(user_id=current_user.id, product_id=product.id).first()
    if exists:
        flash("该产品已在意向清单中。", "info")
    else:
        db.session.add(Wishlist(user_id=current_user.id, product_id=product.id))
        db.session.commit()
        flash("已加入意向清单。", "success")
    return redirect(request.referrer or url_for("product_detail", product_id=product.id))


@login_required
def remove_wishlist(wishlist_id):
    item = db.session.get(Wishlist, wishlist_id) or abort(404)
    if item.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    db.session.delete(item)
    db.session.commit()
    flash("已从意向清单删除。", "success")
    return redirect(url_for("user_center"))
