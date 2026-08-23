ALTER TABLE sponsors
ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMP_NTZ;

UPDATE sponsors
SET submitted_at = CURRENT_TIMESTAMP()
WHERE submitted_at IS NULL;