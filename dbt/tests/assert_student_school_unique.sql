select ssid, school_code from {{ ref('fct_student_school_year') }}
group by 1, 2 having count(*) > 1
