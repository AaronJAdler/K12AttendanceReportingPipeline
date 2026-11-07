-- The newest accepted batch is the one reported. Rejected batches never reach the marts.
select max(batch_id) as batch_id
from {{ source('raw', 'batches') }}
where status = 'accepted'
