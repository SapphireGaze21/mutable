SELECT * FROM store_sales, date_dim, customer_address, web_sales WHERE ss_sold_date_sk = d_date_sk AND ss_addr_sk = ca_address_sk AND ws_sold_date_sk = d_date_sk AND ws_bill_addr_sk = ca_address_sk;
