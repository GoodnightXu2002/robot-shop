from flask import Blueprint, render_template

from models import User


admin_users_bp = Blueprint("admin_users", __name__)
_admin_required = None


def register_admin_user_routes(app, admin_required):
    global _admin_required
    _admin_required = admin_required
    app.register_blueprint(admin_users_bp)


@admin_users_bp.record_once
def register_routes(state):
    state.app.add_url_rule("/admin/users", endpoint="admin_users", view_func=_admin_required(admin_users))


def admin_users():
    users = User.query.order_by(User.is_admin.desc(), User.created_at.desc()).all()
    return render_template("admin/users.html", users=users)
