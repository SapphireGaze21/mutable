SELECT * FROM inventory, item, warehouse, date_dim WHERE inv_item_sk = i_item_sk AND inv_warehouse_sk = w_warehouse_sk AND inv_date_sk = d_date_sk AND d_year = 1998;
