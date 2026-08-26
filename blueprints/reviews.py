from flask import Blueprint, abort, flash, redirect, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from models import Order, Product, Review, db


reviews_bp = Blueprint("reviews", __name__)


def register_review_routes(app):
    app.register_blueprint(reviews_bp)


@reviews_bp.record_once
def register_routes(state):
    state.app.add_url_rule(
        "/products/<int:product_id>/review",
        endpoint="add_review",
        view_func=login_required(add_review),
        methods=["POST"],
    )


def add_review(product_id):
    product = db.session.get(Product, product_id) or abort(404)
    if not product.is_active:
        flash("该产品已下架，暂不可评价。", "warning")
        return redirect(url_for("product_detail", product_id=product.id))

    try:
        rating = int(request.form.get("rating", 5))
    except ValueError:
        rating = 5
    content = request.form.get("content", "").strip()

    if rating < 1 or rating > 5:
        flash("评分必须在 1 到 5 分之间。", "danger")
        return redirect(url_for("product_detail", product_id=product.id))
    if not content:
        flash("评价内容不能为空。", "danger")
        return redirect(url_for("product_detail", product_id=product.id))
    if Review.query.filter_by(user_id=current_user.id, product_id=product.id).first():
        flash("您已经评价过该产品。", "warning")
        return redirect(url_for("product_detail", product_id=product.id))

    is_verified_purchase = (
        Order.query.filter_by(user_id=current_user.id, product_id=product.id).first()
        is not None
    )
    review = Review(
        user_id=current_user.id,
        product_id=product.id,
        rating=rating,
        content=content,
        is_verified_purchase=is_verified_purchase,
    )
    db.session.add(review)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("您已经评价过该产品。", "warning")
    else:
        flash("评价提交成功，感谢您的反馈。", "success")
    return redirect(url_for("product_detail", product_id=product.id))
