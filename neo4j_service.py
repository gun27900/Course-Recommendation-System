from __future__ import annotations

import os
from typing import Any

import streamlit as st
from neo4j import GraphDatabase, RoutingControl


def _config() -> tuple[str, str, str, str | None]:
    """Read Neo4j connection values from Streamlit Secrets or environment variables."""
    if "neo4j" in st.secrets:
        cfg = st.secrets["neo4j"]
        return (
            cfg["uri"],
            cfg["username"],
            cfg["password"],
            cfg.get("database") or None,
        )

    uri = os.getenv("NEO4J_URI", "")
    username = os.getenv("NEO4J_USERNAME", "")
    password = os.getenv("NEO4J_PASSWORD", "")
    database = os.getenv("NEO4J_DATABASE") or None
    if not (uri and username and password):
        raise RuntimeError("Neo4j credentials are not configured")
    return uri, username, password, database


@st.cache_resource(show_spinner=False)
def get_driver():
    uri, username, password, _ = _config()
    driver = GraphDatabase.driver(uri, auth=(username, password))
    driver.verify_connectivity()
    return driver


def query(cypher: str, parameters: dict[str, Any] | None = None, *, write: bool = False) -> list[dict[str, Any]]:
    _, _, _, database = _config()
    records, _, _ = get_driver().execute_query(
        cypher,
        parameters_=parameters or {},
        database_=database,
        routing_=RoutingControl.WRITE if write else RoutingControl.READ,
    )
    return [record.data() for record in records]


def ping() -> bool:
    rows = query("RETURN 1 AS ok")
    return bool(rows and rows[0]["ok"] == 1)


def create_schema() -> None:
    statements = [
        "CREATE CONSTRAINT course_rec_student_id IF NOT EXISTS FOR (s:CourseRecStudent) REQUIRE s.student_id IS UNIQUE",
        "CREATE CONSTRAINT course_rec_course_id IF NOT EXISTS FOR (c:CourseRecCourse) REQUIRE c.course_id IS UNIQUE",
        "CREATE CONSTRAINT course_rec_category_name IF NOT EXISTS FOR (c:CourseRecCategory) REQUIRE c.name IS UNIQUE",
    ]
    for stmt in statements:
        query(stmt, write=True)


def seed_demo_data() -> None:
    """Seed the same 5 students, 6 courses and 13 interests from the original notebook.

    Extra course code/category/image properties are presentation metadata added for the Streamlit version.
    MERGE makes this safe to run repeatedly.
    """
    create_schema()

    students = [
        {"student_id": "Nat", "name": "Nat"},
        {"student_id": "Beam", "name": "Beam"},
        {"student_id": "Game", "name": "Game"},
        {"student_id": "Mint", "name": "Mint"},
        {"student_id": "Pond", "name": "Pond"},
    ]

    courses = [
        {"course_id": "Python Programming", "title": "Python Programming", "code": "CS101", "category": "Programming", "image": "assets/python_programming.png"},
        {"course_id": "Database Systems", "title": "Database Systems", "code": "CS202", "category": "Database", "image": "assets/database_systems.png"},
        {"course_id": "Web Development", "title": "Web Development", "code": "CS203", "category": "Web Development", "image": "assets/web_development.png"},
        {"course_id": "Cyber Security", "title": "Cyber Security", "code": "CS304", "category": "Security", "image": "assets/cyber_security.png"},
        {"course_id": "Data Science", "title": "Data Science", "code": "CS305", "category": "Data & AI", "image": "assets/data_science.png"},
        {"course_id": "Computer Networks", "title": "Computer Networks", "code": "CS206", "category": "Networking", "image": "assets/computer_networks.png"},
    ]

    interests = [
        ["Nat", "Python Programming"],
        ["Nat", "Database Systems"],
        ["Beam", "Python Programming"],
        ["Beam", "Database Systems"],
        ["Beam", "Data Science"],
        ["Game", "Python Programming"],
        ["Game", "Cyber Security"],
        ["Game", "Computer Networks"],
        ["Mint", "Web Development"],
        ["Mint", "Cyber Security"],
        ["Pond", "Database Systems"],
        ["Pond", "Web Development"],
        ["Pond", "Data Science"],
    ]

    query(
        """
        UNWIND $rows AS row
        MERGE (s:CourseRecStudent {student_id: row.student_id})
        SET s.name = row.name
        """,
        {"rows": students},
        write=True,
    )

    query(
        """
        UNWIND $rows AS row
        MERGE (c:CourseRecCourse {course_id: row.course_id})
        SET c.title = row.title,
            c.code = row.code,
            c.image = row.image
        MERGE (cat:CourseRecCategory {name: row.category})
        MERGE (c)-[:IN_CATEGORY]->(cat)
        """,
        {"rows": courses},
        write=True,
    )

    query(
        """
        UNWIND $rows AS row
        MATCH (s:CourseRecStudent {student_id: row[0]})
        MATCH (c:CourseRecCourse {course_id: row[1]})
        MERGE (s)-[:INTERESTED_IN]->(c)
        """,
        {"rows": interests},
        write=True,
    )


def get_students() -> list[dict[str, Any]]:
    return query(
        """
        MATCH (s:CourseRecStudent)
        RETURN s.student_id AS student_id, s.name AS name
        ORDER BY s.name
        """
    )


def get_dashboard_metrics() -> dict[str, int]:
    rows = query(
        """
        CALL { MATCH (s:CourseRecStudent) RETURN count(s) AS students }
        CALL { MATCH (c:CourseRecCourse) RETURN count(c) AS courses }
        CALL { MATCH (:CourseRecStudent)-[r:INTERESTED_IN]->(:CourseRecCourse) RETURN count(r) AS interests }
        CALL { MATCH (cat:CourseRecCategory) RETURN count(cat) AS categories }
        RETURN students, courses, interests, categories
        """
    )
    return rows[0] if rows else {"students": 0, "courses": 0, "interests": 0, "categories": 0}


def get_profile(student_id: str) -> dict[str, Any] | None:
    rows = query(
        """
        MATCH (s:CourseRecStudent {student_id: $student_id})
        OPTIONAL MATCH (s)-[:INTERESTED_IN]->(c:CourseRecCourse)
        OPTIONAL MATCH (c)-[:IN_CATEGORY]->(cat:CourseRecCategory)
        RETURN s.student_id AS student_id,
               s.name AS name,
               collect(DISTINCT {
                   course_id: c.course_id,
                   title: c.title,
                   code: c.code,
                   category: cat.name,
                   image: c.image
               }) AS courses
        """,
        {"student_id": student_id},
    )
    if not rows:
        return None
    row = rows[0]
    row["courses"] = [x for x in row["courses"] if x.get("course_id")]
    return row


def recommend_courses(student_id: str, limit: int = 6) -> list[dict[str, Any]]:
    """Collaborative graph traversal from the original notebook.

    score = number of Student->shared Course<-similar Student->candidate Course paths.
    """
    return query(
        """
        MATCH (me:CourseRecStudent {student_id: $student_id})
              -[:INTERESTED_IN]->(shared:CourseRecCourse)
              <-[:INTERESTED_IN]-(similar:CourseRecStudent)
              -[:INTERESTED_IN]->(candidate:CourseRecCourse)
        WHERE similar <> me
          AND NOT EXISTS {
            MATCH (me)-[:INTERESTED_IN]->(candidate)
          }
        WITH candidate,
             count(*) AS score,
             collect(DISTINCT similar.name) AS supported_by,
             collect(DISTINCT shared.title) AS shared_courses
        OPTIONAL MATCH (other:CourseRecStudent)-[:INTERESTED_IN]->(candidate)
        WITH candidate, score, supported_by, shared_courses,
             count(DISTINCT other) AS popularity
        OPTIONAL MATCH (candidate)-[:IN_CATEGORY]->(cat:CourseRecCategory)
        RETURN candidate.course_id AS course_id,
               candidate.title AS recommendation,
               candidate.code AS code,
               candidate.image AS image,
               cat.name AS category,
               score,
               supported_by,
               shared_courses,
               popularity
        ORDER BY score DESC, recommendation
        LIMIT $limit
        """,
        {"student_id": student_id, "limit": int(limit)},
    )


def search_courses(keyword: str = "", category: str | None = None) -> list[dict[str, Any]]:
    return query(
        """
        MATCH (c:CourseRecCourse)
        OPTIONAL MATCH (c)-[:IN_CATEGORY]->(cat:CourseRecCategory)
        WHERE ($keyword = '' OR toLower(c.title) CONTAINS toLower($keyword)
               OR toLower(coalesce(c.code, '')) CONTAINS toLower($keyword))
          AND ($category = '' OR cat.name = $category)
        OPTIONAL MATCH (s:CourseRecStudent)-[:INTERESTED_IN]->(c)
        RETURN c.course_id AS course_id,
               c.code AS code,
               c.title AS title,
               cat.name AS category,
               c.image AS image,
               count(DISTINCT s) AS interested_students
        ORDER BY c.title
        """,
        {"keyword": keyword.strip(), "category": category or ""},
    )


def list_categories() -> list[str]:
    return [
        row["name"]
        for row in query("MATCH (c:CourseRecCategory) RETURN c.name AS name ORDER BY c.name")
    ]



def update_course(course_id: str, *, title: str, code: str, category: str) -> None:
    """Update display information for a course without changing its stable course_id."""
    query(
        """
        MATCH (c:CourseRecCourse {course_id: $course_id})
        SET c.title = $title,
            c.code = $code
        WITH c
        OPTIONAL MATCH (c)-[old_rel:IN_CATEGORY]->(:CourseRecCategory)
        DELETE old_rel
        WITH c
        MERGE (cat:CourseRecCategory {name: $category})
        MERGE (c)-[:IN_CATEGORY]->(cat)
        """,
        {
            "course_id": course_id,
            "title": title,
            "code": code,
            "category": category,
        },
        write=True,
    )

    # Remove category nodes that are no longer used by any course.
    query(
        """
        MATCH (cat:CourseRecCategory)
        WHERE NOT (cat)<-[:IN_CATEGORY]-(:CourseRecCourse)
        DELETE cat
        """,
        write=True,
    )


def add_interest(student_id: str, course_id: str) -> None:
    query(
        """
        MATCH (s:CourseRecStudent {student_id: $student_id})
        MATCH (c:CourseRecCourse {course_id: $course_id})
        MERGE (s)-[:INTERESTED_IN]->(c)
        """,
        {"student_id": student_id, "course_id": course_id},
        write=True,
    )


def remove_interest(student_id: str, course_id: str) -> None:
    query(
        """
        MATCH (s:CourseRecStudent {student_id: $student_id})
              -[r:INTERESTED_IN]->
              (c:CourseRecCourse {course_id: $course_id})
        DELETE r
        """,
        {"student_id": student_id, "course_id": course_id},
        write=True,
    )


def graph_neighborhood(student_id: str, limit: int = 60) -> list[dict[str, Any]]:
    return query(
        """
        MATCH (u:CourseRecStudent {student_id: $student_id})
        OPTIONAL MATCH p=(u)-[:INTERESTED_IN|IN_CATEGORY*1..2]-(x)
        WITH collect(p)[0..$limit] AS paths
        UNWIND paths AS p
        UNWIND relationships(p) AS r
        WITH DISTINCT startNode(r) AS s, r, endNode(r) AS t
        RETURN elementId(s) AS source_id,
               labels(s)[0] AS source_label,
               coalesce(s.name, s.title, s.student_id, s.course_id) AS source_name,
               type(r) AS relationship,
               elementId(t) AS target_id,
               labels(t)[0] AS target_label,
               coalesce(t.name, t.title, t.student_id, t.course_id) AS target_name
        LIMIT $limit
        """,
        {"student_id": student_id, "limit": int(limit)},
    )
