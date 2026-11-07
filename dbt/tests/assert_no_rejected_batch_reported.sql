select b.batch_id from {{ ref('stg_current_batch') }} c
join {{ source('raw', 'batches') }} b using (batch_id)
where b.status <> 'accepted'
