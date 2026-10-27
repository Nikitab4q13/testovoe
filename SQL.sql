A)
SELECT DISTINCT ticket_client
FROM tickets
WHERE csat < 3;

Б)
SELECT ticket_id
FROM tickets
WHERE LOWER(text) LIKE '%отлично%'
ORDER BY csat DESC;