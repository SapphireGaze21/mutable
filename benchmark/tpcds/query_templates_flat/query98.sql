SELECT * FROM store_sales, item, date_dim WHERE ss_item_sk = i_item_sk AND ss_sold_date_sk = d_date_sk;
