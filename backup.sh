#!/bin/bash
# =====================================================
# 📦 Daily SQLite Backup + S3 Sync for DrHealth
# =====================================================

DATE=$(date +%Y-%m-%d_%H-%M)
BACKUP_DIR=/app/backups
DB_FILE=/app/drhealth.db
S3_BUCKET=s3://$S3_BUCKET_NAME/drhealth_backups

mkdir -p $BACKUP_DIR
cp $DB_FILE $BACKUP_DIR/drhealth_$DATE.sqlite

if [ -n "$AWS_ACCESS_KEY_ID" ]; then
  aws s3 cp $BACKUP_DIR/drhealth_$DATE.sqlite $S3_BUCKET/
  echo "✅ Backup uploaded to $S3_BUCKET"
else
  echo "⚠️ AWS not configured, backup saved locally at $BACKUP_DIR"
fi
