select distinct v.record_type, v.line_no
from {{ source('raw', 'validation_results') }} v
join {{ ref('stg_current_batch') }} b using (batch_id)
where v.severity = 'Fatal' and v.line_no is not null
