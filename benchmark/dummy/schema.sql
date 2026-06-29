CREATE DATABASE custom_suite;
USE custom_suite;

CREATE TABLE students (
    id INT(4) NOT NULL PRIMARY KEY,
    name CHAR(20) NOT NULL,
    grade CHAR(2) NOT NULL
);

IMPORT INTO students DSV "benchmark/dummy/students.csv" HAS HEADER SKIP HEADER;

CREATE TABLE mentor (
    mid INT(4) NOT NULL PRIMARY KEY,
    sid INT(4) NOT NULL,
    names CHAR(20) NOT NULL
);

IMPORT INTO mentor DSV "benchmark/dummy/mentor.csv" HAS HEADER SKIP HEADER;
