SELECT *
FROM store_sales ss
JOIN customer c
    ON ss.ss_customer_sk = c.c_customer_sk
JOIN date_dim d
    ON ss.ss_sold_date_sk = d.d_date_sk
JOIN item i
    ON ss.ss_item_sk = i.i_item_sk;

SELECT *
FROM store_sales ss
JOIN customer c
    ON ss.ss_customer_sk = c.c_customer_sk
JOIN date_dim d
    ON ss.ss_sold_date_sk = d.d_date_sk
JOIN item i
    ON ss.ss_item_sk = i.i_item_sk
JOIN store s
    ON ss.ss_store_sk = s.s_store_sk;

SELECT *
FROM store_sales ss
JOIN customer c
    ON ss.ss_customer_sk = c.c_customer_sk
JOIN date_dim d
    ON ss.ss_sold_date_sk = d.d_date_sk
JOIN item i
    ON ss.ss_item_sk = i.i_item_sk
JOIN store s
    ON ss.ss_store_sk = s.s_store_sk
JOIN promotion p
    ON ss.ss_promo_sk = p.p_promo_sk;
