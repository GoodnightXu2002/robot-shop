from models import Notification, db


def notify_user(user_id, title, content, notification_type="system", link=""):
    db.session.add(
        Notification(
            user_id=user_id,
            title=title,
            content=content,
            type=notification_type,
            link=link,
            role_target="user",
            is_read=False,
        )
    )


def notify_admin(title, content, notification_type="system", link=""):
    db.session.add(
        Notification(
            user_id=None,
            title=title,
            content=content,
            type=notification_type,
            link=link,
            role_target="admin",
            is_read=False,
        )
    )
