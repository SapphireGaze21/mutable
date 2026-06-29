SELECT * FROM store_sales, store_returns, reason WHERE sr_reason_sk = r_reason_sk AND (sr_item_sk = ss_item_sk AND sr_ticket_number = ss_ticket_number);
