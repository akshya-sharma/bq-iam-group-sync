-- =============================================================================
-- 01_group_memberships_ddl.sql
-- Creates the group memberships lookup table in the private dataset.
-- Populated atomically by the Cloud Run Job (WRITE_TRUNCATE).
-- =============================================================================

CREATE TABLE IF NOT EXISTS `my-project.private_dataset.group_memberships` (
  user_email STRING NOT NULL OPTIONS(description="Lowercase email address of the user"),
  group_email STRING NOT NULL OPTIONS(description="Lowercase email address of the Cloud Identity / Entra ID group")
)
CLUSTER BY user_email, group_email
OPTIONS(
  description="Transitive group memberships synced from Google Cloud Identity / Entra ID for CLS/RLS enforcement"
);
