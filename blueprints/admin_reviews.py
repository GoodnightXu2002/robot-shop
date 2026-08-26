from flask import Blueprint, abort, flash, redirect, render_template, url_for

from models import Review, db


admin_reviews_bp = Blueprint("admin_reviews", __name__)
_admin_required = None


def register_admin_review_routes(app, admin_required):
    global _admin_required
    _admin_required = admin_required
    app.register_blueprint(admin_reviews_bp)


@admin_reviews_bp.record_once
def register_routes(state):
    state.app.add_url_rule(
        "/admin/reviews",
        endpoint="admin_reviews",
        view_func=_admin_required(admin_reviews),
    )
    state.app.add_url_rule(
        "/admin/reviews/<int:review_id>/delete",
        endpoint="admin_delete_review",
        view_func=_admin_required(admin_delete_review),
        methods=["POST"],
    )


def admin_reviews():
    review_list = Review.query.order_by(Review.created_at.desc()).all()
    return render_template("admin/reviews.html", reviews=review_list)


def admin_delete_review(review_id):
    review = db.session.get(Review, review_id) or abort(404)
    db.session.delete(review)
    db.session.commit()
    flash("评价删除成功。", "success")
    return redirect(url_for("admin_reviews"))
