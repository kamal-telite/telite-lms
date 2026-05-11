# telite-backend/pal_engine.py
# Phase 4 — PAL Rule Engine
# Analyses scores → classifies level → generates recommendations

from __future__ import annotations
import json
from dataclasses import dataclass, field


# ── Level thresholds (easy to tune) ───────────────────────────────────────
REMEDIAL_THRESHOLD  = 50.0   # below this → remedial
ADVANCED_THRESHOLD  = 80.0   # above this → advanced
WEAK_TOPIC_THRESHOLD   = 60.0
STRONG_TOPIC_THRESHOLD = 75.0


# ── Course catalogue for recommendations ──────────────────────────────────
# Maps branch → level → list of course suggestions
# Extend this as you add real courses to Moodle
COURSE_CATALOGUE: dict[str, dict[str, list[dict]]] = {
    "CSE": {
        "remedial": [
            {"name": "Programming Fundamentals",     "moodle_course_id": None, "level": "remedial"},
            {"name": "Basic Data Structures",        "moodle_course_id": None, "level": "remedial"},
            {"name": "Mathematics for Computing",    "moodle_course_id": None, "level": "remedial"},
        ],
        "normal": [
            {"name": "Data Structures and Algorithms", "moodle_course_id": 1,    "level": "normal"},
            {"name": "Operating Systems",              "moodle_course_id": 2,    "level": "normal"},
            {"name": "Database Management Systems",    "moodle_course_id": None, "level": "normal"},
        ],
        "advanced": [
            {"name": "Advanced Algorithms",          "moodle_course_id": None, "level": "advanced"},
            {"name": "System Design",                "moodle_course_id": None, "level": "advanced"},
            {"name": "Machine Learning Fundamentals","moodle_course_id": None, "level": "advanced"},
        ],
    },
    "ECE": {
        "remedial": [
            {"name": "Basic Electronics",            "moodle_course_id": None, "level": "remedial"},
            {"name": "Mathematics for Engineers",    "moodle_course_id": None, "level": "remedial"},
        ],
        "normal": [
            {"name": "Signals and Systems",          "moodle_course_id": 3,    "level": "normal"},
            {"name": "Digital Electronics",          "moodle_course_id": None, "level": "normal"},
        ],
        "advanced": [
            {"name": "VLSI Design",                  "moodle_course_id": None, "level": "advanced"},
            {"name": "Embedded Systems",             "moodle_course_id": None, "level": "advanced"},
        ],
    },
    "Maths": {
        "remedial": [
            {"name": "Foundation Mathematics",       "moodle_course_id": None, "level": "remedial"},
        ],
        "normal": [
            {"name": "Linear Algebra",               "moodle_course_id": None, "level": "normal"},
            {"name": "Calculus",                     "moodle_course_id": None, "level": "normal"},
        ],
        "advanced": [
            {"name": "Real Analysis",                "moodle_course_id": None, "level": "advanced"},
            {"name": "Number Theory",                "moodle_course_id": None, "level": "advanced"},
        ],
    },
}

# Default for unknown branches
DEFAULT_CATALOGUE = {
    "remedial":  [{"name": "Foundation Course",  "moodle_course_id": None, "level": "remedial"}],
    "normal":    [{"name": "Core Course",        "moodle_course_id": None, "level": "normal"}],
    "advanced":  [{"name": "Advanced Elective",  "moodle_course_id": None, "level": "advanced"}],
}

# ── Topic resource links ───────────────────────────────────────────────────
TOPIC_RESOURCES: dict[str, list[dict]] = {
    "arrays":        [{"title": "Arrays — GeeksForGeeks",     "url": "https://www.geeksforgeeks.org/array-data-structure/"}],
    "linked lists":  [{"title": "Linked Lists — Visualgo",    "url": "https://visualgo.net/en/list"}],
    "sorting":       [{"title": "Sorting Algorithms",         "url": "https://www.toptal.com/developers/sorting-algorithms"}],
    "trees":         [{"title": "Binary Trees — GFG",         "url": "https://www.geeksforgeeks.org/binary-tree-data-structure/"}],
    "graphs":        [{"title": "Graph Algorithms",           "url": "https://www.geeksforgeeks.org/graph-data-structure-and-algorithms/"}],
    "os":            [{"title": "OS Concepts — Tutorialspoint","url": "https://www.tutorialspoint.com/operating_system/"}],
    "signals":       [{"title": "Signals and Systems — MIT",  "url": "https://ocw.mit.edu/courses/6-003-signals-and-systems-fall-2011/"}],
    "default":       [{"title": "Khan Academy",               "url": "https://www.khanacademy.org"}],
}


# ── Result dataclass ──────────────────────────────────────────────────────
@dataclass
class PALResult:
    enrollment_number: str
    avg_score:         float
    level:             str                    # remedial / normal / advanced
    level_color:       str                    # red / amber / green
    weak_topics:       list[str]   = field(default_factory=list)
    strong_topics:     list[str]   = field(default_factory=list)
    recommended_courses:   list[dict] = field(default_factory=list)
    recommended_resources: list[dict] = field(default_factory=list)
    message:           str = ""
    total_quizzes:     int = 0

    def to_dict(self) -> dict:
        return {
            "enrollment_number":      self.enrollment_number,
            "avg_score":              self.avg_score,
            "level":                  self.level,
            "level_color":            self.level_color,
            "weak_topics":            self.weak_topics,
            "strong_topics":          self.strong_topics,
            "recommended_courses":    self.recommended_courses,
            "recommended_resources":  self.recommended_resources,
            "message":                self.message,
            "total_quizzes":          self.total_quizzes,
        }


# ── Core engine function ───────────────────────────────────────────────────
def analyse(
    enrollment_number: str,
    avg_score: float,
    weak_topics: list[str],
    strong_topics: list[str],
    branch: str = "CSE",
    total_quizzes: int = 0,
) -> PALResult:
    """
    Main PAL rule engine.
    Takes performance data → returns level + recommendations.
    """
    branch = branch or "CSE"

    # ── Classify level ────────────────────────────────────────────────────
    if avg_score < REMEDIAL_THRESHOLD:
        level       = "remedial"
        level_color = "red"
        message     = (
            f"Your average score is {avg_score:.1f}%. "
            "Focus on the remedial courses below before moving forward. "
            "Practice the weak topics listed daily."
        )
    elif avg_score >= ADVANCED_THRESHOLD:
        level       = "advanced"
        level_color = "green"
        message     = (
            f"Excellent work! Your average score is {avg_score:.1f}%. "
            "You're ready for advanced material. "
            "Check out the next-level courses below."
        )
    else:
        level       = "normal"
        level_color = "amber"
        message     = (
            f"Your average score is {avg_score:.1f}%. "
            "You're on track. Work on your weak topics to move to the advanced level."
        )

    # ── Get course recommendations ─────────────────────────────────────────
    catalogue     = COURSE_CATALOGUE.get(branch, DEFAULT_CATALOGUE)
    level_courses = catalogue.get(level, [])

    # For remedial students: also show normal courses as targets
    if level == "remedial" and len(level_courses) < 3:
        level_courses = level_courses + catalogue.get("normal", [])[:1]

    # ── Get topic resources for weak topics ───────────────────────────────
    resources = []
    for topic in weak_topics[:3]:   # max 3 topic resources
        topic_lower = topic.lower()
        found = False
        for key, res_list in TOPIC_RESOURCES.items():
            if key in topic_lower or topic_lower in key:
                resources.extend(res_list)
                found = True
                break
        if not found:
            resources.extend(TOPIC_RESOURCES["default"])

    # Deduplicate resources by URL
    seen_urls = set()
    unique_resources = []
    for r in resources:
        if r["url"] not in seen_urls:
            seen_urls.add(r["url"])
            unique_resources.append(r)

    return PALResult(
        enrollment_number=enrollment_number,
        avg_score=avg_score,
        level=level,
        level_color=level_color,
        weak_topics=weak_topics,
        strong_topics=strong_topics,
        recommended_courses=level_courses,
        recommended_resources=unique_resources,
        message=message,
        total_quizzes=total_quizzes,
    )


def build_recommendation_email(student_name: str, result: PALResult) -> tuple[str, str]:
    """Returns (subject, html_body) for the recommendation email."""

    color_map = {"red": "#dc2626", "amber": "#d97706", "green": "#16a34a"}
    bg_map    = {"red": "#fef2f2", "amber": "#fffbeb", "green": "#f0fdf4"}
    color     = color_map.get(result.level_color, "#374151")
    bg        = bg_map.get(result.level_color, "#f9fafb")
    level_cap = result.level.capitalize()

    subject = f"Telite LMS — Your Learning Report ({level_cap} Level)"

    courses_html = "".join(
        f'<li style="margin-bottom:6px;font-size:13px;color:#374151;">{c["name"]}</li>'
        for c in result.recommended_courses[:3]
    )

    resources_html = "".join(
        f'<li style="margin-bottom:6px;font-size:13px;">'
        f'<a href="{r["url"]}" style="color:#6366f1;">{r["title"]}</a></li>'
        for r in result.recommended_resources[:3]
    )

    weak_html = ", ".join(result.weak_topics[:5]) or "None identified yet"

    html = f"""
<!DOCTYPE html><html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f8fafc;font-family:sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 0;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0"
       style="background:#fff;border-radius:12px;border:1px solid #e5e7eb;overflow:hidden;">

  <tr><td style="background:{color};padding:24px 32px;">
    <div style="font-size:20px;font-weight:700;color:#fff;">Telite LMS — Learning Report</div>
    <div style="font-size:13px;color:rgba(255,255,255,0.85);margin-top:4px;">
      Personalised Adaptive Learning
    </div>
  </td></tr>

  <tr><td style="padding:28px 32px;">
    <p style="font-size:15px;color:#374151;margin:0 0 16px;">
      Hello <strong>{student_name}</strong>,
    </p>

    <div style="background:{bg};border-radius:8px;padding:16px;margin-bottom:20px;
                border-left:4px solid {color};">
      <div style="font-size:13px;color:#6b7280;margin-bottom:4px;">Your current level</div>
      <div style="font-size:22px;font-weight:700;color:{color};">{level_cap}</div>
      <div style="font-size:13px;color:#374151;margin-top:4px;">
        Average score: <strong>{result.avg_score:.1f}%</strong>
        across {result.total_quizzes} quiz(zes)
      </div>
    </div>

    <p style="font-size:13px;color:#6b7280;margin:0 0 20px;">{result.message}</p>

    {"<div style='margin-bottom:20px;'><div style='font-size:13px;font-weight:600;color:#374151;margin-bottom:8px;'>Topics needing attention</div><div style='font-size:13px;color:#dc2626;background:#fef2f2;padding:10px 14px;border-radius:6px;'>" + weak_html + "</div></div>" if result.weak_topics else ""}

    <div style="margin-bottom:20px;">
      <div style="font-size:13px;font-weight:600;color:#374151;margin-bottom:8px;">
        Recommended courses
      </div>
      <ul style="margin:0;padding-left:20px;">{courses_html}</ul>
    </div>

    {"<div><div style='font-size:13px;font-weight:600;color:#374151;margin-bottom:8px;'>Study resources</div><ul style='margin:0;padding-left:20px;'>" + resources_html + "</ul></div>" if result.recommended_resources else ""}

  </td></tr>

  <tr><td style="padding:16px 32px;border-top:1px solid #f3f4f6;">
    <p style="font-size:11px;color:#9ca3af;margin:0;">
      Telite LMS — Personalised Adaptive Learning System
    </p>
  </td></tr>

</table>
</td></tr>
</table>
</body></html>
""".strip()

    return subject, html
