SELECT * FROM store_sales, date_dim, catalog_sales WHERE ss_sold_date_sk = d_date_sk AND cs_sold_date_sk = d_date_sk;
