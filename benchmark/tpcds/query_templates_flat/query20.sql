SELECT * FROM catalog_sales, item, date_dim WHERE cs_item_sk = i_item_sk AND cs_sold_date_sk = d_date_sk;
