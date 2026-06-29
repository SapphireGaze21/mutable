SELECT * FROM catalog_sales, item, date_dim WHERE i_manufact_id = 1 AND i_item_sk = cs_item_sk AND d_date_sk = cs_sold_date_sk AND cs_item_sk = i_item_sk;
