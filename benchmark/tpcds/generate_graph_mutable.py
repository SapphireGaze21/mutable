import yaml

with open('benchmark/dataset_for_graph/graph.yml', 'r') as f:
    graph = yaml.safe_load(f)

with open('benchmark/dataset_for_graph/data_tpcds.yml', 'r') as f:
    tpcds_data = yaml.safe_load(f)

graph['data'] = tpcds_data['data']
graph['systems'] = {
    'mutable': {
        'configurations': {
            'Interpreter-DPsub': {
                'args': '--backend Interpreter --plan-enumerator DPsub --plan',
                'pattern': '^Execute query:.*'
            }
        },
        'cases': {
            'Join4': 'SELECT * FROM store_sales ss, customer c, date_dim d, item i WHERE ss.ss_customer_sk = c.c_customer_sk AND ss.ss_sold_date_sk = d.d_date_sk AND ss.ss_item_sk = i.i_item_sk;',
            'Join5': 'SELECT * FROM store_sales ss, customer c, date_dim d, item i, store s WHERE ss.ss_customer_sk = c.c_customer_sk AND ss.ss_sold_date_sk = d.d_date_sk AND ss.ss_item_sk = i.i_item_sk AND ss.ss_store_sk = s.s_store_sk;',
            'Join6': 'SELECT * FROM store_sales ss, customer c, date_dim d, item i, store s, promotion p WHERE ss.ss_customer_sk = c.c_customer_sk AND ss.ss_sold_date_sk = d.d_date_sk AND ss.ss_item_sk = i.i_item_sk AND ss.ss_store_sk = s.s_store_sk AND ss.ss_promo_sk = p.p_promo_sk;'
        }
    }
}

with open('benchmark/dataset_for_graph/graph_mutable.yml', 'w') as f:
    yaml.dump(graph, f, sort_keys=False)
