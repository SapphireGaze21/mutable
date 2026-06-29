SELECT * FROM inventory, warehouse, item, date_dim WHERE i_item_sk = inv_item_sk AND inv_warehouse_sk = w_warehouse_sk AND inv_date_sk = d_date_sk;
