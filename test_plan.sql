CREATE DATABASE testdb; USE testdb;
CREATE TABLE t1 (id INT(4));
CREATE TABLE t2 (id INT(4));
SELECT * FROM t1, t2 WHERE t1.id = t2.id;
