from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from models import Consultation, db


admin_consultations_bp = Blueprint("admin_consultations", __name__)
_admin_required = None
_notify_user = None
_consultation_statuses = []


def register_admin_consultation_routes(app, admin_required, notify_user_func, consultation_statuses):
    global _admin_required, _notify_user, _consultation_statuses
    _admin_required = admin_required
    _notify_user = notify_user_func
    _consultation_statuses = consultation_statuses
    app.register_blueprint(admin_consultations_bp)


@admin_consultations_bp.record_once
def register_routes(state):
    state.app.add_url_rule(
        "/admin/consultations",
        endpoint="admin_consultations",
        view_func=_admin_required(admin_consultations),
    )
    state.app.add_url_rule(
        "/admin/consultations/<int:consultation_id>/status",
        endpoint="admin_consultation_status",
        view_func=_admin_required(admin_consultation_status),
        methods=["POST"],
    )


def admin_consultations():
    consultation_list = Consultation.query.order_by(Consultation.created_at.desc()).all()
    pending_consultations = [item for item in consultation_list if item.status == "待处理"]
    processing_consultations = [item for item in consultation_list if item.status in ("处理中", "已回复")]
    archived_consultations = [item for item in consultation_list if item.status in ("已关闭", "已完成")]
    consultation_stats = {
        "pending": len(pending_consultations),
        "processing": len([item for item in consultation_list if item.status == "处理中"]),
        "replied": len([item for item in consultation_list if item.status == "已回复"]),
        "archived": len(archived_consultations),
    }
    return render_template(
        "admin/consultations.html",
        consultations=consultation_list,
        pending_consultations=pending_consultations,
        processing_consultations=processing_consultations,
        archived_consultations=archived_consultations,
        consultation_stats=consultation_stats,
        statuses=_consultation_statuses,
    )


def admin_consultation_status(consultation_id):
    consultation_item = db.session.get(Consultation, consultation_id) or abort(404)
    old_reply = consultation_item.admin_reply or ""
    old_status = consultation_item.status
    new_status = request.form.get("status", consultation_item.status)
    if new_status in _consultation_statuses:
        consultation_item.status = new_status
    consultation_item.admin_reply = request.form.get("admin_reply", "").strip()
    if consultation_item.admin_reply and (
        consultation_item.admin_reply != old_reply or consultation_item.status != old_status
    ):
        _notify_user(
            consultation_item.user_id,
            "咨询已回复",
            "管理员已回复您的咨询。",
            "consultation",
            url_for("consultations"),
        )
    db.session.commit()
    flash("咨询处理信息已更新。", "success")
    return redirect(url_for("admin_consultations"))
