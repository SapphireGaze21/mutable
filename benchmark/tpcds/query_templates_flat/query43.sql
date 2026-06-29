SELECT * FROM date_dim, store_sales, store WHERE d_date_sk = ss_sold_date_sk AND s_store_sk = ss_store_sk AND d_year = 1998;
