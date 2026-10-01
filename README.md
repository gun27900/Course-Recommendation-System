# Course Recommendation System

ระบบแนะนำรายวิชา พัฒนาต่อยอดจาก `Course_Recommender_Neo4j_Python.ipynb` ให้เป็นเว็บ **Streamlit + Neo4j Aura** ในรูปแบบเดียวกับโปรเจกต์ตัวอย่างอาจารย์

## แนวคิดหลัก

ข้อมูลหลักยังคงชุดเดิมจาก Notebook:

- Student 5 คน: Nat, Beam, Game, Mint, Pond
- Course 6 วิชา
- `INTERESTED_IN` 13 ความสัมพันธ์

Graph หลัก:

```text
(:CourseRecStudent)-[:INTERESTED_IN]->(:CourseRecCourse)
(:CourseRecCourse)-[:IN_CATEGORY]->(:CourseRecCategory)
```

Recommendation ใช้เส้นทางเดิม:

```text
Target Student
  -> Shared Course
  <- Similar Student
  -> New Candidate Course
```

`score` = จำนวนเส้นทางที่นำไปถึง Candidate Course นั้น จึงสอดคล้องกับ Notebook ต้นฉบับ

## หน้าจอระบบ

1. Dashboard — จำนวนข้อมูลและรายวิชาที่นักศึกษาสนใจ
2. Recommendations — แนะนำรายวิชาพร้อมรูป, score และเหตุผล
3. Course Search — ค้นหารายวิชาจากชื่อ/รหัส/หมวด
4. Manage Interest — เพิ่มหรือลบ `INTERESTED_IN`
5. Graph Explorer — แสดง Graph ของนักศึกษาและรายวิชา
6. Admin / Setup — สร้าง Constraint และ Demo Data

## รันในเครื่อง

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
```

สร้างไฟล์ `.streamlit/secrets.toml` จากตัวอย่าง:

```toml
[neo4j]
uri = "neo4j+s://YOUR_INSTANCE.databases.neo4j.io"
username = "YOUR_USERNAME"
password = "YOUR_PASSWORD"
database = ""  # optional: leave blank to use the home database
```

แล้วรัน

```bash
streamlit run app.py
```

ครั้งแรกให้เข้า **Admin / Setup** แล้วกด **สร้าง Constraint + Demo Data**

## GitHub / Streamlit Community Cloud

อัปโหลดไฟล์ทั้งหมดขึ้น GitHub แต่ **ห้ามอัปโหลด `.streamlit/secrets.toml`**

บน Streamlit Community Cloud ให้ตั้ง Main file เป็น `app.py` และใส่ Neo4j credential ใน Secrets

## สิ่งที่ต่อยอดจาก Notebook เดิม

- เปลี่ยนจากการดู DataFrame ใน Notebook เป็น Web UI
- แยก Database Layer (`neo4j_service.py`) จาก UI (`app.py`)
- แสดงรูปประกอบของรายวิชา
- แสดงเหตุผลของ Recommendation
- เพิ่ม Search
- เพิ่ม/ลบความสนใจจากหน้าเว็บ
- เพิ่ม Graph Explorer
- เพิ่ม Admin/Setup
- เตรียมโครงสร้างสำหรับ GitHub และ Streamlit Cloud
