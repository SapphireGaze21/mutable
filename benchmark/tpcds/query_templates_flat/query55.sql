SELECT * FROM date_dim, store_sales, item WHERE d_date_sk = ss_sold_date_sk AND ss_item_sk = i_item_sk AND i_manager_id = 1 AND d_moy = 11 AND d_year = 1998;
