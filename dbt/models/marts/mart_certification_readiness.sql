-- For the latest batch submitted (accepted or not): open findings by school.
with latest as (
    select batch_id, status, reason from {{ source('raw', 'batches') }}
    order by batch_id desc limit 1
)
select
    l.batch_id,
    l.status as batch_status,
    v.school_code,
    count(*) filter (where v.severity = 'Fatal') as fatal_count,
    count(*) filter (where v.severity = 'Warning') as warning_count,
    count(*) filter (where v.severity = 'Fatal') = 0 and l.status = 'accepted' as ready
from latest l
join {{ source('raw', 'validation_results') }} v using (batch_id)
group by 1, 2, 3
