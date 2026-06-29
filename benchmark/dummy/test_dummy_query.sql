USE custom_suite;

SELECT * 
FROM students s1, mentor m1, mentor m2, students s2
WHERE s1.id = m1.sid 
  AND m1.mid = m2.mid 
  AND m2.sid = s2.id;
