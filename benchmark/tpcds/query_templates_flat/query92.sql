SELECT * FROM web_sales, item, date_dim WHERE i_manufact_id = 1 AND i_item_sk = ws_item_sk AND d_date_sk = ws_sold_date_sk AND ws_item_sk = i_item_sk;
