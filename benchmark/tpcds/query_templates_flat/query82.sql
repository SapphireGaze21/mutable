SELECT * FROM item, inventory, date_dim, store_sales WHERE inv_item_sk = i_item_sk AND d_date_sk = inv_date_sk AND ss_item_sk = i_item_sk;
