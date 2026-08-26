from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from models import Appointment, db


admin_appointments_bp = Blueprint("admin_appointments", __name__)
_admin_required = None
_notify_user = None
_appointment_statuses = []


def register_admin_appointment_routes(app, admin_required, notify_user_func, appointment_statuses):
    global _admin_required, _notify_user, _appointment_statuses
    _admin_required = admin_required
    _notify_user = notify_user_func
    _appointment_statuses = appointment_statuses
    app.register_blueprint(admin_appointments_bp)


@admin_appointments_bp.record_once
def register_routes(state):
    state.app.add_url_rule(
        "/admin/appointments",
        endpoint="admin_appointments",
        view_func=_admin_required(admin_appointments),
    )
    state.app.add_url_rule(
        "/admin/appointments/<int:appointment_id>/status",
        endpoint="admin_appointment_status",
        view_func=_admin_required(admin_appointment_status),
        methods=["POST"],
    )


def admin_appointments():
    appointment_list = Appointment.query.order_by(Appointment.created_at.desc()).all()
    pending_appointments = [item for item in appointment_list if item.status == "待确认"]
    active_appointments = [item for item in appointment_list if item.status in ("已确认", "服务中")]
    archived_appointments = [item for item in appointment_list if item.status in ("已完成", "已取消")]
    appointment_stats = {
        "pending": len(pending_appointments),
        "active": len(active_appointments),
        "completed": len([item for item in appointment_list if item.status == "已完成"]),
        "cancelled": len([item for item in appointment_list if item.status == "已取消"]),
    }
    return render_template(
        "admin/appointments.html",
        appointments=appointment_list,
        pending_appointments=pending_appointments,
        active_appointments=active_appointments,
        archived_appointments=archived_appointments,
        appointment_stats=appointment_stats,
        statuses=_appointment_statuses,
    )


def admin_appointment_status(appointment_id):
    appointment = db.session.get(Appointment, appointment_id) or abort(404)
    old_status = appointment.status
    new_status = request.form.get("status", appointment.status)
    if new_status in _appointment_statuses:
        appointment.status = new_status
    appointment.process_note = request.form.get("process_note", "").strip()
    if appointment.status != old_status:
        _notify_user(
            appointment.user_id,
            "预约状态更新",
            "您的服务预约状态已更新。",
            "appointment",
            url_for("appointments"),
        )
    db.session.commit()
    flash("预约处理信息已更新。", "success")
    return redirect(url_for("admin_appointments"))
