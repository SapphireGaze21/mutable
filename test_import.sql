CREATE DATABASE testdb; USE testdb; CREATE TABLE a (b INT(4)); IMPORT INTO a DSV "benchmark/tpcds/data/csvs/income_band.csv" DELIMITER "," HAS HEADER SKIP HEADER; SELECT * FROM a;
