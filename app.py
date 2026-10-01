from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from neo4j_service import (
    add_interest,
    get_dashboard_metrics,
    get_profile,
    get_students,
    graph_neighborhood,
    list_categories,
    ping,
    recommend_courses,
    remove_interest,
    search_courses,
    seed_demo_data,
)

BASE_DIR = Path(__file__).resolve().parent

st.set_page_config(
    page_title="Course Recommendation System",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
      .hero {
        padding: 1.45rem 1.6rem; border-radius: 22px;
        background: linear-gradient(120deg, #0f172a 0%, #1d4ed8 58%, #0891b2 100%);
        color: white; margin-bottom: 1rem;
      }
      .hero h1 {margin:0; font-size:2.1rem;}
      .hero p {opacity:.9; margin:.35rem 0 0 0;}
      .course-card {
        padding: 1rem; border: 1px solid rgba(128,128,128,.24);
        border-radius: 18px; margin-bottom: .8rem;
      }
      .score-pill {
        display:inline-block; padding:.22rem .58rem; border-radius:999px;
        background:#1d4ed8; color:white; font-size:.8rem; font-weight:700;
      }
      .muted {opacity:.72; font-size:.9rem;}
      .reason {margin-top:.45rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


def image_path(relative_path: str | None) -> str | None:
    if not relative_path:
        return None
    path = BASE_DIR / relative_path
    return str(path) if path.exists() else None


def require_connection() -> None:
    try:
        if not ping():
            raise RuntimeError("Neo4j did not return a healthy response")
    except Exception as exc:
        st.error("ยังเชื่อมต่อ Neo4j Aura ไม่สำเร็จ")
        st.code(
            '[neo4j]\nuri = "neo4j+s://YOUR_INSTANCE.databases.neo4j.io"\n'
            'username = "YOUR_USERNAME"\npassword = "YOUR_PASSWORD"\ndatabase = "neo4j"',
            language="toml",
        )
        st.caption("คัดลอก .streamlit/secrets.toml.example เป็น .streamlit/secrets.toml แล้วใส่ข้อมูล Aura ของตัวเอง")
        st.caption("ห้ามนำไฟล์ secrets.toml หรือรหัสผ่านขึ้น GitHub")
        st.exception(exc)
        st.stop()


def student_selector(key: str) -> str:
    students = get_students()
    if not students:
        st.info("ยังไม่มีข้อมูลนักศึกษา กรุณาไปหน้า Admin / Setup แล้วสร้าง Demo Data")
        st.stop()
    labels = {f"{x['student_id']} — {x['name']}": x["student_id"] for x in students}
    selected = st.selectbox("เลือกนักศึกษา", list(labels), key=key)
    return labels[selected]


def recommendation_reason(row: dict) -> str:
    supporters = ", ".join(row.get("supported_by") or [])
    shared = ", ".join(row.get("shared_courses") or [])
    parts = []
    if supporters:
        parts.append(f"นักศึกษาที่มีความสนใจคล้ายกัน: {supporters}")
    if shared:
        parts.append(f"มีรายวิชาที่สนใจร่วมกัน: {shared}")
    if row.get("popularity"):
        parts.append(f"มีผู้สนใจรายวิชานี้ {row['popularity']} คน")
    return " • ".join(parts) or "แนะนำจากเส้นทางความสัมพันธ์ในกราฟ"


require_connection()

with st.sidebar:
    st.markdown("## 🎓 CourseRec")
    st.caption("Neo4j Aura + Streamlit")
    page = st.radio(
        "เมนู",
        [
            "Dashboard",
            "Recommendations",
            "Course Search",
            "Manage Interest",
            "Graph Explorer",
            "Admin / Setup",
        ],
    )
    st.divider()
    st.caption("ต่อยอดจาก Course_Recommender_Neo4j_Python.ipynb")

st.markdown(
    """
    <div class="hero">
      <h1>🎓 Course Recommendation System</h1>
      <p>ระบบแนะนำรายวิชาด้วย Graph Database โดยวิเคราะห์ความสนใจที่คล้ายกันของนักศึกษา</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if page == "Dashboard":
    st.subheader("ภาพรวมระบบ")
    m = get_dashboard_metrics()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Students", m.get("students", 0))
    c2.metric("Courses", m.get("courses", 0))
    c3.metric("INTERESTED_IN", m.get("interests", 0))
    c4.metric("Categories", m.get("categories", 0))

    st.divider()
    student_id = student_selector("dashboard_student")
    profile = get_profile(student_id)
    if profile:
        st.markdown(f"### 👤 {profile['name']}")
        st.caption(f"Student ID: {profile['student_id']}")
        st.markdown("#### รายวิชาที่สนใจ")
        courses = profile.get("courses", [])
        if not courses:
            st.info("นักศึกษาคนนี้ยังไม่มีรายวิชาที่สนใจ")
        else:
            cols = st.columns(min(3, len(courses)))
            for i, course in enumerate(courses):
                with cols[i % len(cols)]:
                    img = image_path(course.get("image"))
                    if img:
                        st.image(img, use_container_width=True)
                    st.markdown(f"**{course.get('title', '')}**")
                    st.caption(f"{course.get('code') or '-'} · {course.get('category') or 'ไม่ระบุหมวด'}")

elif page == "Recommendations":
    st.subheader("✨ รายวิชาที่แนะนำ")
    student_id = student_selector("recommend_student")
    top_n = st.slider("จำนวนคำแนะนำ", 1, 6, 4)
    rows = recommend_courses(student_id, top_n)
    st.caption("Score = จำนวนเส้นทาง Student → วิชาที่สนใจร่วมกัน → Student ที่คล้ายกัน → วิชาใหม่ ตามหลักการจาก Notebook เดิม")

    if not rows:
        st.info("ยังไม่มีรายวิชาใหม่ที่ระบบสามารถแนะนำได้สำหรับผู้ใช้นี้")
    else:
        for i, row in enumerate(rows, start=1):
            left, right = st.columns([1, 3])
            with left:
                img = image_path(row.get("image"))
                if img:
                    st.image(img, use_container_width=True)
            with right:
                st.markdown('<div class="course-card">', unsafe_allow_html=True)
                st.markdown(f'<span class="score-pill">#{i} · score {row["score"]}</span>', unsafe_allow_html=True)
                st.markdown(f"### {row['recommendation']}")
                st.markdown(
                    f'<div class="muted">{row.get("code") or "-"} · {row.get("category") or "ไม่ระบุหมวด"}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(f"**เหตุผล:** {recommendation_reason(row)}")
                st.markdown("</div>", unsafe_allow_html=True)

elif page == "Course Search":
    st.subheader("🔎 ค้นหารายวิชา")
    c1, c2 = st.columns([2, 1])
    keyword = c1.text_input("ชื่อหรือรหัสรายวิชา", placeholder="เช่น Python, CS202")
    categories = [""] + list_categories()
    category = c2.selectbox("หมวด", categories, format_func=lambda x: "ทุกหมวด" if x == "" else x)
    rows = search_courses(keyword, category)
    st.write(f"พบ {len(rows)} รายการ")
    if rows:
        table = pd.DataFrame(rows).drop(columns=["image"], errors="ignore")
        st.dataframe(table, use_container_width=True, hide_index=True)

elif page == "Manage Interest":
    st.subheader("📝 เพิ่ม / ลบความสนใจรายวิชา")
    student_id = student_selector("manage_student")
    courses = search_courses()
    if not courses:
        st.info("ยังไม่มีข้อมูลรายวิชา")
        st.stop()

    labels = {f"{c.get('code') or '-'} — {c['title']}": c["course_id"] for c in courses}
    selected = st.selectbox("เลือกรายวิชา", list(labels))
    c1, c2 = st.columns(2)
    if c1.button("➕ เพิ่ม INTERESTED_IN", type="primary", use_container_width=True):
        add_interest(student_id, labels[selected])
        st.success("เพิ่มความสนใจเรียบร้อยแล้ว")
        st.rerun()
    if c2.button("➖ ลบ INTERESTED_IN", use_container_width=True):
        remove_interest(student_id, labels[selected])
        st.success("ลบความสนใจเรียบร้อยแล้ว")
        st.rerun()

elif page == "Graph Explorer":
    st.subheader("🕸️ Graph Explorer")
    student_id = student_selector("graph_student")
    rows = graph_neighborhood(student_id)
    if not rows:
        st.info("ยังไม่มี neighborhood graph สำหรับนักศึกษาคนนี้")
    else:
        dot = [
            "digraph G {",
            'rankdir="LR";',
            'node [shape=box, style="rounded,filled", fillcolor="#f8fafc"];',
        ]
        seen_nodes = set()
        for r in rows:
            for node_id, label, name in [
                (r["source_id"], r["source_label"], r["source_name"]),
                (r["target_id"], r["target_label"], r["target_name"]),
            ]:
                if node_id not in seen_nodes:
                    safe_name = str(name).replace('"', "'")
                    dot.append(f'"{node_id}" [label="{safe_name}\\n:{label}"];')
                    seen_nodes.add(node_id)
            dot.append(f'"{r["source_id"]}" -> "{r["target_id"]}" [label="{r["relationship"]}"];')
        dot.append("}")
        st.graphviz_chart("\n".join(dot), use_container_width=True)
        with st.expander("ดูข้อมูล Edge"):
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

elif page == "Admin / Setup":
    st.subheader("⚙️ Setup ข้อมูลตัวอย่าง")
    st.warning("ข้อมูลหลักยังคงเป็นชุดเดิมจาก Notebook: 5 นักศึกษา, 6 รายวิชา และ 13 INTERESTED_IN")
    st.markdown(
        """
        **Graph schema**
        - `(:CourseRecStudent)-[:INTERESTED_IN]->(:CourseRecCourse)`
        - `(:CourseRecCourse)-[:IN_CATEGORY]->(:CourseRecCategory)`

        ระบบใช้ `MERGE` จึงสามารถกดสร้างข้อมูลซ้ำได้โดยไม่เพิ่ม Node หลักซ้ำจาก key เดิม
        """
    )
    if st.button("สร้าง Constraint + Demo Data", type="primary", use_container_width=True):
        with st.spinner("กำลังสร้างข้อมูล..."):
            seed_demo_data()
        st.success("สร้างข้อมูลตัวอย่างเรียบร้อยแล้ว")
        st.rerun()
