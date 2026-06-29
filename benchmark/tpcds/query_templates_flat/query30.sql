SELECT * FROM customer_address, customer, web_returns, date_dim WHERE ca_address_sk = c_current_addr_sk AND wr_returned_date_sk = d_date_sk AND d_year = 1999 AND wr_returning_addr_sk = ca_address_sk;
