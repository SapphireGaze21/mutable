SELECT * FROM item, inventory, date_dim, catalog_sales WHERE inv_item_sk = i_item_sk AND d_date_sk = inv_date_sk AND cs_item_sk = i_item_sk;
