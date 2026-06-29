SELECT * FROM store_sales, date_dim d1, item, store WHERE d1.d_year = 1998 AND d1.d_date_sk = ss_sold_date_sk AND i_item_sk = ss_item_sk AND s_store_sk = ss_store_sk;
