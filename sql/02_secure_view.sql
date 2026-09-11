-- =============================================================================
-- 02_secure_view.sql
-- Creates a Standard View in shared_dataset over a base table in private_dataset.
--
-- Useful in scenarios where BigQuery native Row-Level Security (RLS) and
-- Column-Level Security (CLS / Policy Tags) are not feasible or supported,
-- providing a custom, small-scale SQL masking and row-filtering pattern using
-- a 1-row CTE + CROSS JOIN and SESSION_USER() lookup against group_memberships.
-- =============================================================================

CREATE OR REPLACE VIEW `shared_dataset.employees_secure_view` AS
WITH user_permissions AS (
  -- Evaluates once per query and always returns exactly 1 row of boolean flags
  SELECT
    COUNTIF(group_email = 'hr-admins@company.com') > 0 AS can_view_salary,
    COUNTIF(group_email IN ('hr-admins@company.com', 'finance-users@company.com')) > 0 AS can_view_ssn
  FROM
    `private_dataset.group_memberships`
  WHERE
    user_email = LOWER(SESSION_USER())
)
SELECT
  t.employee_id,
  t.name,
  t.department,
  -- Dynamic CLS: Unmask salary only for HR Admins
  IF(p.can_view_salary, t.salary, NULL) AS salary,
  -- Dynamic CLS: Unmask full SSN for HR/Finance, partially mask for everyone else
  IF(p.can_view_ssn, t.ssn, CONCAT('XXX-XX-', SUBSTR(t.ssn, -4))) AS ssn
FROM
  `private_dataset.employees` AS t
CROSS JOIN
  user_permissions AS p;
