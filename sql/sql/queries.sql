%%writefile sql/queries.sql
-- Q1
SELECT customer_id FROM orders WHERE status = 'completed' AND order_amount > 500 GROUP BY customer_id HAVING SUM(order_amount) > 8000;

-- Q2
SELECT c.city, p.category, SUM(o.order_amount) AS revenue FROM orders o JOIN customers c ON o.customer_id = c.customer_id JOIN products p ON o.product_id = p.product_id WHERE o.status = 'completed' GROUP BY c.city, p.category;

-- Q3
SELECT product_name FROM products WHERE price_inr > (SELECT AVG(price_inr) FROM products);

-- Q4
SELECT c.customer_id FROM customers c LEFT JOIN orders o ON c.customer_id = o.customer_id AND o.status = 'completed' WHERE o.order_id IS NULL;

-- Q5
WITH cust_spend AS (SELECT customer_id, SUM(order_amount) AS total_spend FROM orders WHERE status = 'completed' GROUP BY customer_id), avg_spend AS (SELECT AVG(total_spend) AS avg_val FROM cust_spend) SELECT cs.customer_id FROM cust_spend cs, avg_spend av WHERE cs.total_spend > av.avg_val;

-- Q6
SELECT customer_id, city, total_spend, RANK() OVER(PARTITION BY city ORDER BY total_spend DESC) as rnk, DENSE_RANK() OVER(PARTITION BY city ORDER BY total_spend DESC) as drnk, ROW_NUMBER() OVER(PARTITION BY city ORDER BY total_spend DESC) as rnum FROM (SELECT c.customer_id, c.city, SUM(o.order_amount) AS total_spend FROM orders o JOIN customers c ON o.customer_id = c.customer_id WHERE o.status = 'completed' GROUP BY c.city) sub;

-- Q7
SELECT SUBSTR(order_ts, 1, 10) AS day, SUM(order_amount) AS daily_rev, SUM(SUM(order_amount)) OVER(ORDER BY SUBSTR(order_ts, 1, 10)) AS cumulative_rev FROM orders WHERE status = 'completed' GROUP BY day;
