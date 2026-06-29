SELECT * FROM web_sales, item, date_dim WHERE ws_item_sk = i_item_sk AND ws_sold_date_sk = d_date_sk;
