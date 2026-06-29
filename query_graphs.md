# TPC-DS Flat Queries Join Structures

This document outlines the join graphs for the perfectly flattened TPC-DS queries.

### query10 (7 tables)
- **Join Graph:**
  - `catalog_sales -- customer`
  - `catalog_sales -- date_dim`
  - `customer -- customer_address`
  - `customer -- customer_demographics`
  - `customer -- store_sales`
  - `customer -- web_sales`
  - `date_dim -- store_sales`
  - `date_dim -- web_sales`

### query12 (3 tables)
- **Join Graph:**
  - `date_dim -- web_sales`
  - `item -- web_sales`

### query15 (4 tables)
- **Join Graph:**
  - `catalog_sales -- customer`
  - `catalog_sales -- date_dim`
  - `customer -- customer_address`

### query17 (8 tables)
- **Join Graph:**
  - `catalog_sales -- date_dim`
  - `catalog_sales -- store_returns`
  - `date_dim -- store_returns`
  - `date_dim -- store_sales`
  - `item -- store_sales`
  - `store -- store_sales`
  - `store_returns -- store_sales`

### query18 (7 tables)
- **Join Graph:**
  - `catalog_sales -- customer`
  - `catalog_sales -- customer_demographics`
  - `catalog_sales -- date_dim`
  - `catalog_sales -- item`
  - `customer -- customer_address`
  - `customer -- customer_demographics`

### query20 (3 tables)
- **Join Graph:**
  - `catalog_sales -- date_dim`
  - `catalog_sales -- item`

### query21 (4 tables)
- **Join Graph:**
  - `date_dim -- inventory`
  - `inventory -- item`
  - `inventory -- warehouse`

### query22 (3 tables)
- **Join Graph:**
  - `date_dim -- inventory`
  - `inventory -- item`

### query23 (6 tables)
- **Join Graph:**
  - `catalog_sales -- customer`
  - `catalog_sales -- date_dim`
  - `customer -- store_sales`
  - `customer -- web_sales`
  - `date_dim -- store_sales`
  - `date_dim -- web_sales`
  - `item -- store_sales`

### query25 (8 tables)
- **Join Graph:**
  - `catalog_sales -- date_dim`
  - `catalog_sales -- store_returns`
  - `date_dim -- store_returns`
  - `date_dim -- store_sales`
  - `item -- store_sales`
  - `store -- store_sales`
  - `store_returns -- store_sales`

### query26 (5 tables)
- **Join Graph:**
  - `catalog_sales -- customer_demographics`
  - `catalog_sales -- date_dim`
  - `catalog_sales -- item`
  - `catalog_sales -- promotion`

### query27 (5 tables)
- **Join Graph:**
  - `customer_demographics -- store_sales`
  - `date_dim -- store_sales`
  - `item -- store_sales`
  - `store -- store_sales`

### query28 (1 tables)
- *No equi-joins detected in AST*

### query29 (8 tables)
- **Join Graph:**
  - `catalog_sales -- date_dim`
  - `catalog_sales -- store_returns`
  - `date_dim -- store_returns`
  - `date_dim -- store_sales`
  - `item -- store_sales`
  - `store -- store_sales`
  - `store_returns -- store_sales`

### query3 (3 tables)
- **Join Graph:**
  - `date_dim -- store_sales`
  - `item -- store_sales`

### query30 (4 tables)
- **Join Graph:**
  - `customer -- customer_address`
  - `customer_address -- web_returns`
  - `date_dim -- web_returns`

### query31 (4 tables)
- **Join Graph:**
  - `customer_address -- store_sales`
  - `customer_address -- web_sales`
  - `date_dim -- store_sales`
  - `date_dim -- web_sales`

### query32 (3 tables)
- **Join Graph:**
  - `catalog_sales -- date_dim`
  - `catalog_sales -- item`

### query33 (6 tables)
- **Join Graph:**
  - `catalog_sales -- customer_address`
  - `catalog_sales -- date_dim`
  - `catalog_sales -- item`
  - `customer_address -- store_sales`
  - `customer_address -- web_sales`
  - `date_dim -- store_sales`
  - `date_dim -- web_sales`
  - `item -- store_sales`
  - `item -- web_sales`

### query34 (5 tables)
- **Join Graph:**
  - `customer -- store_sales`
  - `date_dim -- store_sales`
  - `household_demographics -- store_sales`
  - `store -- store_sales`

### query35 (7 tables)
- **Join Graph:**
  - `catalog_sales -- customer`
  - `catalog_sales -- date_dim`
  - `customer -- customer_address`
  - `customer -- customer_demographics`
  - `customer -- store_sales`
  - `customer -- web_sales`
  - `date_dim -- store_sales`
  - `date_dim -- web_sales`

### query36 (4 tables)
- **Join Graph:**
  - `date_dim -- store_sales`
  - `item -- store_sales`
  - `store -- store_sales`

### query37 (4 tables)
- **Join Graph:**
  - `catalog_sales -- item`
  - `date_dim -- inventory`
  - `inventory -- item`

### query38 (5 tables)
- **Join Graph:**
  - `catalog_sales -- customer`
  - `catalog_sales -- date_dim`
  - `customer -- store_sales`
  - `customer -- web_sales`
  - `date_dim -- store_sales`
  - `date_dim -- web_sales`

### query39 (4 tables)
- **Join Graph:**
  - `date_dim -- inventory`
  - `inventory -- item`
  - `inventory -- warehouse`

### query40 (5 tables)
- **Join Graph:**
  - `catalog_returns -- catalog_sales`
  - `catalog_sales -- date_dim`
  - `catalog_sales -- item`
  - `catalog_sales -- warehouse`

### query42 (3 tables)
- **Join Graph:**
  - `date_dim -- store_sales`
  - `item -- store_sales`

### query43 (3 tables)
- **Join Graph:**
  - `date_dim -- store_sales`
  - `store -- store_sales`

### query45 (5 tables)
- **Join Graph:**
  - `customer -- customer_address`
  - `customer -- web_sales`
  - `date_dim -- web_sales`
  - `item -- web_sales`

### query49 (7 tables)
- **Join Graph:**
  - `catalog_returns -- catalog_sales`
  - `catalog_sales -- date_dim`
  - `date_dim -- store_sales`
  - `date_dim -- web_sales`
  - `store_returns -- store_sales`
  - `web_returns -- web_sales`

### query50 (5 tables)
- **Join Graph:**
  - `date_dim -- store_returns`
  - `date_dim -- store_sales`
  - `store -- store_sales`
  - `store_returns -- store_sales`

### query52 (3 tables)
- **Join Graph:**
  - `date_dim -- store_sales`
  - `item -- store_sales`

### query53 (4 tables)
- **Join Graph:**
  - `date_dim -- store_sales`
  - `item -- store_sales`
  - `store -- store_sales`

### query55 (3 tables)
- **Join Graph:**
  - `date_dim -- store_sales`
  - `item -- store_sales`

### query56 (6 tables)
- **Join Graph:**
  - `catalog_sales -- customer_address`
  - `catalog_sales -- date_dim`
  - `catalog_sales -- item`
  - `customer_address -- store_sales`
  - `customer_address -- web_sales`
  - `date_dim -- store_sales`
  - `date_dim -- web_sales`
  - `item -- store_sales`
  - `item -- web_sales`

### query58 (5 tables)
- **Join Graph:**
  - `catalog_sales -- date_dim`
  - `catalog_sales -- item`
  - `date_dim -- store_sales`
  - `date_dim -- web_sales`
  - `item -- store_sales`
  - `item -- web_sales`

### query60 (6 tables)
- **Join Graph:**
  - `catalog_sales -- customer_address`
  - `catalog_sales -- date_dim`
  - `catalog_sales -- item`
  - `customer_address -- store_sales`
  - `customer_address -- web_sales`
  - `date_dim -- store_sales`
  - `date_dim -- web_sales`
  - `item -- store_sales`
  - `item -- web_sales`

### query61 (7 tables)
- **Join Graph:**
  - `customer -- customer_address`
  - `customer -- store_sales`
  - `date_dim -- store_sales`
  - `item -- store_sales`
  - `promotion -- store_sales`
  - `store -- store_sales`

### query62 (5 tables)
- **Join Graph:**
  - `date_dim -- web_sales`
  - `ship_mode -- web_sales`
  - `warehouse -- web_sales`
  - `web_sales -- web_site`

### query63 (4 tables)
- **Join Graph:**
  - `date_dim -- store_sales`
  - `item -- store_sales`
  - `store -- store_sales`

### query66 (6 tables)
- **Join Graph:**
  - `catalog_sales -- date_dim`
  - `catalog_sales -- ship_mode`
  - `catalog_sales -- time_dim`
  - `catalog_sales -- warehouse`
  - `date_dim -- web_sales`
  - `ship_mode -- web_sales`
  - `time_dim -- web_sales`
  - `warehouse -- web_sales`

### query69 (7 tables)
- **Join Graph:**
  - `catalog_sales -- customer`
  - `catalog_sales -- date_dim`
  - `customer -- customer_address`
  - `customer -- customer_demographics`
  - `customer -- store_sales`
  - `customer -- web_sales`
  - `date_dim -- store_sales`
  - `date_dim -- web_sales`

### query7 (5 tables)
- **Join Graph:**
  - `customer_demographics -- store_sales`
  - `date_dim -- store_sales`
  - `item -- store_sales`
  - `promotion -- store_sales`

### query72 (11 tables)
- **Join Graph:**
  - `catalog_returns -- catalog_sales`
  - `catalog_sales -- customer_demographics`
  - `catalog_sales -- date_dim`
  - `catalog_sales -- household_demographics`
  - `catalog_sales -- inventory`
  - `catalog_sales -- item`
  - `catalog_sales -- promotion`
  - `date_dim -- inventory`
  - `inventory -- warehouse`

### query73 (5 tables)
- **Join Graph:**
  - `customer -- store_sales`
  - `date_dim -- store_sales`
  - `household_demographics -- store_sales`
  - `store -- store_sales`

### query74 (4 tables)
- **Join Graph:**
  - `customer -- store_sales`
  - `customer -- web_sales`
  - `date_dim -- store_sales`
  - `date_dim -- web_sales`

### query75 (8 tables)
- **Join Graph:**
  - `catalog_returns -- catalog_sales`
  - `catalog_sales -- date_dim`
  - `catalog_sales -- item`
  - `date_dim -- store_sales`
  - `date_dim -- web_sales`
  - `item -- store_sales`
  - `item -- web_sales`
  - `store_returns -- store_sales`
  - `web_returns -- web_sales`

### query77 (9 tables)
- **Join Graph:**
  - `catalog_returns -- date_dim`
  - `catalog_sales -- date_dim`
  - `date_dim -- store_returns`
  - `date_dim -- store_sales`
  - `date_dim -- web_returns`
  - `date_dim -- web_sales`
  - `store -- store_returns`
  - `store -- store_sales`
  - `web_page -- web_returns`
  - `web_page -- web_sales`

### query79 (5 tables)
- **Join Graph:**
  - `customer -- store_sales`
  - `date_dim -- store_sales`
  - `household_demographics -- store_sales`
  - `store -- store_sales`

### query80 (12 tables)
- **Join Graph:**
  - `catalog_page -- catalog_sales`
  - `catalog_returns -- catalog_sales`
  - `catalog_sales -- date_dim`
  - `catalog_sales -- item`
  - `catalog_sales -- promotion`
  - `date_dim -- store_sales`
  - `date_dim -- web_sales`
  - `item -- store_sales`
  - `item -- web_sales`
  - `promotion -- store_sales`
  - `promotion -- web_sales`
  - `store -- store_sales`
  - `store_returns -- store_sales`
  - `web_returns -- web_sales`
  - `web_sales -- web_site`

### query81 (4 tables)
- **Join Graph:**
  - `catalog_returns -- customer_address`
  - `catalog_returns -- date_dim`
  - `customer -- customer_address`

### query82 (4 tables)
- **Join Graph:**
  - `date_dim -- inventory`
  - `inventory -- item`
  - `item -- store_sales`

### query83 (5 tables)
- **Join Graph:**
  - `catalog_returns -- date_dim`
  - `catalog_returns -- item`
  - `date_dim -- store_returns`
  - `date_dim -- web_returns`
  - `item -- store_returns`
  - `item -- web_returns`

### query84 (6 tables)
- **Join Graph:**
  - `customer -- customer_address`
  - `customer -- customer_demographics`
  - `customer -- household_demographics`
  - `customer_demographics -- store_returns`
  - `household_demographics -- income_band`

### query85 (8 tables)
- **Join Graph:**
  - `customer_address -- web_returns`
  - `customer_demographics -- web_returns`
  - `date_dim -- web_sales`
  - `reason -- web_returns`
  - `web_page -- web_sales`
  - `web_returns -- web_sales`

### query86 (3 tables)
- **Join Graph:**
  - `date_dim -- web_sales`
  - `item -- web_sales`

### query87 (5 tables)
- **Join Graph:**
  - `catalog_sales -- customer`
  - `catalog_sales -- date_dim`
  - `customer -- store_sales`
  - `customer -- web_sales`
  - `date_dim -- store_sales`
  - `date_dim -- web_sales`

### query88 (4 tables)
- **Join Graph:**
  - `household_demographics -- store_sales`
  - `store -- store_sales`
  - `store_sales -- time_dim`

### query89 (4 tables)
- **Join Graph:**
  - `date_dim -- store_sales`
  - `item -- store_sales`
  - `store -- store_sales`

### query90 (4 tables)
- **Join Graph:**
  - `household_demographics -- web_sales`
  - `time_dim -- web_sales`
  - `web_page -- web_sales`

### query91 (7 tables)
- **Join Graph:**
  - `call_center -- catalog_returns`
  - `catalog_returns -- customer`
  - `catalog_returns -- date_dim`
  - `customer -- customer_address`
  - `customer -- customer_demographics`
  - `customer -- household_demographics`

### query92 (3 tables)
- **Join Graph:**
  - `date_dim -- web_sales`
  - `item -- web_sales`

### query93 (3 tables)
- **Join Graph:**
  - `reason -- store_returns`
  - `store_returns -- store_sales`

### query96 (4 tables)
- **Join Graph:**
  - `household_demographics -- store_sales`
  - `store -- store_sales`
  - `store_sales -- time_dim`

### query97 (3 tables)
- **Join Graph:**
  - `catalog_sales -- date_dim`
  - `date_dim -- store_sales`

### query98 (3 tables)
- **Join Graph:**
  - `date_dim -- store_sales`
  - `item -- store_sales`

### query99 (5 tables)
- **Join Graph:**
  - `call_center -- catalog_sales`
  - `catalog_sales -- date_dim`
  - `catalog_sales -- ship_mode`
  - `catalog_sales -- warehouse`
