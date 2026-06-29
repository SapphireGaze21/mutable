SELECT * FROM inventory, date_dim, item WHERE inv_date_sk = d_date_sk AND inv_item_sk = i_item_sk;
