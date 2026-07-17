CREATE DATABASE TPC_DS;
USE TPC_DS;
CREATE TABLE Customer (c_customer_sk INT(4) NOT NULL,
c_customer_id CHAR(16) NOT NULL,
c_current_cdemo_sk INT(4),
c_current_hdemo_sk INT(4),
c_current_addr_sk INT(4),
c_first_shipto_date_sk INT(4),
c_first_sales_date_sk INT(4),
c_salutation CHAR(10),
c_first_name CHAR(20),
c_last_name CHAR(30),
c_preferred_cust_flag CHAR(1),
c_birth_day INT(4),
c_birth_month INT(4),
c_birth_year INT(4),
c_birth_country CHAR(20),
c_login CHAR(13),
c_email_address CHAR(50),
c_last_review_date_sk INT(4));
IMPORT INTO Customer DSV "benchmark/tpcds/data/customer.csv" ROWS 100000 DELIMITER "," HAS HEADER SKIP HEADER;
CREATE TABLE DateDim (d_date_sk INT(4) NOT NULL,
d_date_id CHAR(16) NOT NULL,
d_date DATE,
d_month_seq INT(4),
d_week_seq INT(4),
d_quarter_seq INT(4),
d_year INT(4),
d_dow INT(4),
d_moy INT(4),
d_dom INT(4),
d_qoy INT(4),
d_fy_year INT(4),
d_fy_quarter_seq INT(4),
d_fy_week_seq INT(4),
d_day_name CHAR(9),
d_quarter_name CHAR(6),
d_holiday CHAR(1),
d_weekend CHAR(1),
d_following_holiday CHAR(1),
d_first_dom INT(4),
d_last_dom INT(4),
d_same_day_ly INT(4),
d_same_day_lq INT(4),
d_current_day CHAR(1),
d_current_week CHAR(1),
d_current_month CHAR(1),
d_current_quarter CHAR(1),
d_current_year CHAR(1));
IMPORT INTO DateDim DSV "benchmark/tpcds/data/date_dim.csv" ROWS 73049 DELIMITER "," HAS HEADER SKIP HEADER;
CREATE TABLE Store (s_store_sk INT(4) NOT NULL,
s_store_id CHAR(16) NOT NULL,
s_rec_start_date DATE,
s_rec_end_date DATE,
s_closed_date_sk INT(4),
s_store_name CHAR(50),
s_number_employees INT(4),
s_floor_space INT(4),
s_hours CHAR(20),
s_manager CHAR(40),
s_market_id INT(4),
s_geography_class CHAR(100),
s_market_desc CHAR(100),
s_market_manager CHAR(40),
s_division_id INT(4),
s_division_name CHAR(50),
s_company_id INT(4),
s_company_name CHAR(50),
s_street_number CHAR(10),
s_street_name CHAR(60),
s_street_type CHAR(15),
s_suite_number CHAR(10),
s_city CHAR(60),
s_county CHAR(30),
s_state CHAR(2),
s_zip CHAR(10),
s_country CHAR(20),
s_gmt_offset DECIMAL(5, 2),
s_tax_precentage DECIMAL(5, 2));
IMPORT INTO Store DSV "benchmark/tpcds/data/store.csv" ROWS 12 DELIMITER "," HAS HEADER SKIP HEADER;
CREATE TABLE StoreReturns (sr_returned_date_sk INT(4),
sr_return_time_sk INT(4),
sr_item_sk INT(4) NOT NULL,
sr_customer_sk INT(4),
sr_cdemo_sk INT(4),
sr_hdemo_sk INT(4),
sr_addr_sk INT(4),
sr_store_sk INT(4),
sr_reason_sk INT(4),
sr_ticket_number INT(4) NOT NULL,
sr_return_quantity INT(4),
sr_return_amt DECIMAL(7, 2),
sr_return_tax DECIMAL(7, 2),
sr_return_amt_inc_tax DECIMAL(7, 2),
sr_fee DECIMAL(7, 2),
sr_return_ship_cost DECIMAL(7, 2),
sr_refunded_cash DECIMAL(7, 2),
sr_reversed_charge DECIMAL(7, 2),
sr_store_credit DECIMAL(7, 2),
sr_net_loss DECIMAL(7, 2));
IMPORT INTO StoreReturns DSV "benchmark/tpcds/data/store_returns.csv" ROWS 287867 DELIMITER "," HAS HEADER SKIP HEADER;
SELECT c_customer_id
FROM (SELECT sr_customer_sk AS ctr_customer_sk,
             sr_store_sk AS ctr_store_sk,
             SUM(sr_return_amt) AS ctr_total_return
      FROM StoreReturns,
           DateDim
      WHERE sr_returned_date_sk = d_date_sk
        AND d_year = 2000
      GROUP BY sr_customer_sk,
               sr_store_sk) ctr1,
     Store,
     Customer
WHERE ctr1.ctr_total_return >
    (SELECT AVG(ctr_total_return)
     FROM (SELECT sr_customer_sk AS ctr_customer_sk,
                  sr_store_sk AS ctr_store_sk,
                  SUM(sr_return_amt) AS ctr_total_return
           FROM StoreReturns,
                DateDim
           WHERE sr_returned_date_sk = d_date_sk
             AND d_year = 2000
           GROUP BY sr_customer_sk,
                    sr_store_sk) ctr2
     WHERE ctr1.ctr_store_sk = ctr2.ctr_store_sk) * 1.2
  AND s_store_sk = ctr1.ctr_store_sk
  AND s_state = "TN"
  AND ctr1.ctr_customer_sk = c_customer_sk
ORDER BY c_customer_id
LIMIT 100;

