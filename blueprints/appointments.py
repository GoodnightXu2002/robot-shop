from datetime import date, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import Appointment, Consultation, Product, db


appointments_bp = Blueprint("appointments", __name__)
_notify_admin = None
_appointment_statuses = []
_service_types = []
_time_slots = []


def register_appointment_routes(app, notify_admin_func, appointment_statuses, service_types, time_slots):
    global _notify_admin, _appointment_statuses, _service_types, _time_slots
    _notify_admin = notify_admin_func
    _appointment_statuses = appointment_statuses
    _service_types = service_types
    _time_slots = time_slots
    app.register_blueprint(appointments_bp)


@appointments_bp.record_once
def register_routes(state):
    state.app.add_url_rule(
        "/appointments",
        endpoint="appointments",
        view_func=login_required(appointments),
        methods=["GET", "POST"],
    )


def appointments():
    selected_product_id = request.args.get("product_id", type=int)
    prefill_title = request.args.get("title", "").strip()[:150]
    prefill_content = request.args.get("content", "").strip()[:800]
    source_from_ai = request.args.get("source") == "ai"
    show_consultation = (
        request.args.get("consultation") == "1"
        or source_from_ai
        or bool(prefill_title)
        or bool(prefill_content)
    )
    appointment_min_date = (date.today() + timedelta(days=1)).isoformat()
    default_time_slot = next((slot for slot in _time_slots if slot), "")

    if request.method == "POST":
        appointment_form = {
            field: request.form.get(field, "")
            for field in (
                "service_type",
                "appointment_date",
                "time_slot",
                "address",
                "contact_name",
                "contact",
                "remark",
            )
        }
    else:
        appointment_form = {
            "service_type": _service_types[0] if _service_types else "",
            "appointment_date": appointment_min_date,
            "time_slot": default_time_slot,
            "address": "",
            "contact_name": "",
            "contact": "",
            "remark": "",
        }

    if request.method == "POST":
        appointment_date = request.form.get("appointment_date", "").strip()
        time_slot = request.form.get("time_slot", "").strip()
        appointment = Appointment(
            user_id=current_user.id,
            service_type=request.form.get("service_type", "").strip(),
            appointment_date=appointment_date,
            time_slot=time_slot,
            appointment_time=f"{appointment_date} {time_slot}".strip(),
            address=request.form.get("address", "").strip(),
            contact_name=request.form.get("contact_name", "").strip(),
            contact=request.form.get("contact", "").strip(),
            remark=request.form.get("remark", "").strip(),
            status="待确认",
        )
        if not appointment.service_type or not appointment.appointment_date or not appointment.time_slot or not appointment.contact_name or not appointment.contact:
            flash("请填写服务类型、预约日期、时间段、联系人和联系电话。", "danger")
        else:
            db.session.add(appointment)
            _notify_admin(
                "新服务预约",
                f"用户 {current_user.username} 提交了新的服务预约。",
                "appointment",
                "/admin/appointments",
            )
            db.session.commit()
            flash("服务预约提交成功。", "success")
            return redirect(url_for("appointments"))

    appointment_list = (
        Appointment.query.filter_by(user_id=current_user.id)
        .order_by(Appointment.created_at.desc())
        .all()
    )
    active_appointments = [item for item in appointment_list if item.status in ("待确认", "已确认", "服务中")]
    archived_appointments = [item for item in appointment_list if item.status in ("已完成", "已取消")]
    latest_appointment = active_appointments[0] if active_appointments else (appointment_list[0] if appointment_list else None)
    consultation_list = (
        Consultation.query.filter_by(user_id=current_user.id)
        .order_by(Consultation.created_at.desc())
        .all()
    )
    active_consultations = [item for item in consultation_list if item.status in ("待处理", "处理中", "已回复")]
    archived_consultations = [item for item in consultation_list if item.status in ("已关闭", "已完成")]
    product_list = Product.query.filter_by(is_active=True).order_by(Product.id.asc()).all()
    return render_template(
        "appointments.html",
        appointments=appointment_list,
        active_appointments=active_appointments,
        archived_appointments=archived_appointments,
        latest_appointment=latest_appointment,
        service_types=_service_types,
        time_slots=_time_slots,
        appointment_form=appointment_form,
        appointment_min_date=appointment_min_date,
        progress_steps=_appointment_statuses,
        consultations=consultation_list,
        active_consultations=active_consultations,
        archived_consultations=archived_consultations,
        products=product_list,
        selected_product_id=selected_product_id,
        prefill_title=prefill_title,
        prefill_content=prefill_content,
        source_from_ai=source_from_ai,
        show_consultation=show_consultation,
    )
