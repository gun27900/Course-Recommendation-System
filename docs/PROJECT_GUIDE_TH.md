# คู่มือโครงงานระบบแนะนำรายวิชา

## 1. ที่มา

โปรเจกต์นี้ต่อยอดจาก Notebook ระบบแนะนำรายวิชาด้วย Neo4j และ Python โดยยังคง Graph Traversal เดิม แต่เพิ่มเว็บ Streamlit เพื่อให้สามารถสาธิตการใช้งานเป็นระบบได้

## 2. Graph Model

```text
(Student)-[:INTERESTED_IN]->(Course)-[:IN_CATEGORY]->(Category)
```

Label จริงที่ใช้เพื่อไม่ชนกับข้อมูลอื่นในฐานข้อมูล:

- `CourseRecStudent`
- `CourseRecCourse`
- `CourseRecCategory`

## 3. Recommendation Algorithm

เส้นทางที่ใช้:

```text
Student เป้าหมาย
  -> Course ที่สนใจ
  <- Student ที่มีความสนใจเหมือนกัน
  -> Course ใหม่
```

ระบบตัดวิชาที่ Student เป้าหมายสนใจอยู่แล้วออก และนับจำนวนเส้นทางเป็น `score`

ตัวอย่างผลเดิมของ Nat จากชุดข้อมูลต้นฉบับ:

```text
Data Science       score 3
Cyber Security     score 1
Computer Networks  score 1
Web Development    score 1
```

## 4. สิ่งที่ควรสาธิตตอน Present

1. เปิด Dashboard ให้เห็นจำนวน Student/Course/Relationship
2. เลือก Nat และดูวิชาที่สนใจเดิม
3. ไปหน้า Recommendations แล้วอธิบายเส้นทาง Graph
4. แสดงรูปประกอบรายวิชาที่ระบบแนะนำ
5. ไป Manage Interest เพิ่มวิชาให้ Nat
6. กลับ Recommendations เพื่อดูว่าผลเปลี่ยนตามข้อมูล
7. เปิด Graph Explorer เพื่อแสดง Node และ Relationship
8. แสดง GitHub repository และโครงสร้างไฟล์

## 5. จุดที่ควรพูด

- Neo4j เหมาะกับโจทย์นี้เพราะ Recommendation อาศัยการเดินความสัมพันธ์ใน Graph
- ใช้ Parameterized Cypher
- ใช้ `MERGE` เพื่อสร้างข้อมูลซ้ำได้อย่างปลอดภัย
- แยก Credential ออกจาก Source Code ด้วย Streamlit Secrets
- ระบบสามารถอธิบายได้ว่ารายวิชาถูกแนะนำจาก Student คนใดและมีวิชาใดที่สนใจร่วมกัน
