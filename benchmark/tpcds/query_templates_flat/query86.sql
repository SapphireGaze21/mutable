SELECT * FROM web_sales, date_dim d1, item WHERE d1.d_date_sk = ws_sold_date_sk AND i_item_sk = ws_item_sk;
