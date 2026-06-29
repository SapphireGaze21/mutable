SELECT * FROM customer, store_sales, date_dim, web_sales WHERE c_customer_sk = ss_customer_sk AND ss_sold_date_sk = d_date_sk AND c_customer_sk = ws_bill_customer_sk AND ws_sold_date_sk = d_date_sk;
