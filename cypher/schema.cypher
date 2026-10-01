CREATE CONSTRAINT course_rec_student_id IF NOT EXISTS
FOR (s:CourseRecStudent) REQUIRE s.student_id IS UNIQUE;

CREATE CONSTRAINT course_rec_course_id IF NOT EXISTS
FOR (c:CourseRecCourse) REQUIRE c.course_id IS UNIQUE;

CREATE CONSTRAINT course_rec_category_name IF NOT EXISTS
FOR (c:CourseRecCategory) REQUIRE c.name IS UNIQUE;
