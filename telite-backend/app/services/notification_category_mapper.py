from typing import Any

def event_to_category(event_name: str) -> str:
    """Map a domain event name to a NotificationCategory string."""
    if event_name.startswith("task.") or event_name.startswith("assignment."):
        return "tasks"
    if event_name.startswith("course.") or event_name.startswith("enrollment.") or event_name.startswith("module.") or event_name.startswith("learning_path.") or event_name.startswith("certificate."):
        return "courses"
    if event_name.startswith("announcement."):
        return "announcements"
    if event_name.startswith("message."):
        return "messages"
    if event_name.startswith("user.joined") or event_name.startswith("user.role_changed"):
        return "system"
    # Default to system if unknown
    return "system"
