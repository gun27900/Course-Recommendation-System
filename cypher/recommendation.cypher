// Course recommendation based on the original notebook graph traversal.
// Path: target student -> shared course <- similar student -> candidate course
// Parameters: $student_id, $limit
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
OPTIONAL MATCH (candidate)-[:IN_CATEGORY]->(category:CourseRecCategory)
RETURN candidate.course_id AS course_id,
       candidate.title AS recommendation,
       candidate.code AS code,
       candidate.image AS image,
       category.name AS category,
       score,
       supported_by,
       shared_courses,
       popularity
ORDER BY score DESC, recommendation
LIMIT $limit;
