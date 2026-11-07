-- Current-batch SENR rows with Fatal-flagged lines removed.
select r.*
from {{ source('raw', 'senr') }} r
join {{ ref('stg_current_batch') }} b using (batch_id)
where not exists (
    select 1 from {{ ref('stg_fatal_lines') }} f
    where f.record_type = 'SENR' and f.line_no = r.line_no)
