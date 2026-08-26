from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import Notification, db


notifications_bp = Blueprint("notifications", __name__)
_admin_required = None


def register_notification_routes(app, admin_required):
    global _admin_required
    _admin_required = admin_required
    app.register_blueprint(notifications_bp)


@notifications_bp.record_once
def register_routes(state):
    state.app.add_url_rule("/messages", endpoint="messages", view_func=login_required(messages))
    state.app.add_url_rule(
        "/messages/<int:notification_id>",
        endpoint="message_detail",
        view_func=login_required(message_detail),
    )
    state.app.add_url_rule(
        "/messages/<int:notification_id>/read",
        endpoint="mark_message_read",
        view_func=login_required(mark_message_read),
        methods=["POST"],
    )
    state.app.add_url_rule(
        "/admin/messages",
        endpoint="admin_messages",
        view_func=_admin_required(admin_messages),
    )
    state.app.add_url_rule(
        "/admin/messages/<int:notification_id>/read",
        endpoint="admin_mark_message_read",
        view_func=_admin_required(admin_mark_message_read),
        methods=["POST"],
    )


def messages():
    if current_user.is_admin:
        return redirect(url_for("admin_messages"))
    notification_list = (
        Notification.query.filter_by(user_id=current_user.id, role_target="user")
        .order_by(Notification.created_at.desc())
        .all()
    )
    return render_template("messages.html", notifications=notification_list)


def message_detail(notification_id):
    notification = db.session.get(Notification, notification_id) or abort(404)
    if notification.user_id != current_user.id or notification.role_target != "user":
        abort(403)
    notification.is_read = True
    db.session.commit()
    return render_template("message_detail.html", notification=notification)


def mark_message_read(notification_id):
    notification = db.session.get(Notification, notification_id) or abort(404)
    if notification.user_id != current_user.id or notification.role_target != "user":
        abort(403)
    notification.is_read = True
    db.session.commit()
    flash("消息已标记为已读。", "success")
    return redirect(request.referrer or url_for("messages"))


def admin_messages():
    notification_list = (
        Notification.query.filter_by(role_target="admin")
        .order_by(Notification.created_at.desc())
        .all()
    )
    return render_template("admin/messages.html", notifications=notification_list)


def admin_mark_message_read(notification_id):
    notification = db.session.get(Notification, notification_id) or abort(404)
    if notification.role_target != "admin":
        abort(403)
    notification.is_read = True
    db.session.commit()
    flash("消息已标记为已读。", "success")
    return redirect(request.referrer or url_for("admin_messages"))
