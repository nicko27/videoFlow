#!/usr/bin/env python3
"""
Migration Script: Drop video_hashes table (Bug #1)

This script removes the duplicate video_hashes table and consolidates
all hash storage to use only method_signatures.

CORRECTION BUG #1: Tables `video_hashes` vs `method_signatures` dupliquées

Context:
- Two tables (`video_hashes` and `method_signatures`) stored the same data
- This caused cache fragmentation and wasted storage
- method_signatures is the newer, better designed table
- User confirmed data can be emptied (no migration needed)

Solution:
- Drop video_hashes table and all its indexes
- Keep method_signatures as the single source of truth
- Update schema_manager.py to not recreate video_hashes

Date: 2025-12-14
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.logger import Logger
from src.plugins.duplicate_finder.data.connection_pool import ConnectionPool

logger = Logger.get_logger('Migration.DropVideoHashes')


def migrate_drop_video_hashes(db_path: str):
    """
    Drop video_hashes table and its indexes.

    Args:
        db_path: Path to the SQLite database
    """
    logger.info("=" * 80)
    logger.info("MIGRATION: Drop video_hashes table (Bug #1)")
    logger.info("=" * 80)

    pool = ConnectionPool(db_path, pool_size=1)

    try:
        with pool.get_connection() as conn:
            cursor = conn.cursor()

            # Step 1: Check if video_hashes exists
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='video_hashes'
            """)
            table_exists = cursor.fetchone() is not None

            if not table_exists:
                logger.info("✅ video_hashes table does not exist - already migrated")
                return True

            # Step 2: Get table info
            cursor.execute("SELECT COUNT(*) FROM video_hashes")
            row_count = cursor.fetchone()[0]
            logger.info(f"📊 video_hashes table contains {row_count} rows")

            # Step 3: Drop indexes first
            logger.info("🗑️  Dropping video_hashes indexes...")

            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='index' AND tbl_name='video_hashes'
            """)
            indexes = [row[0] for row in cursor.fetchall()]

            for index_name in indexes:
                if not index_name.startswith('sqlite_'):  # Skip auto-created indexes
                    logger.info(f"   Dropping index: {index_name}")
                    cursor.execute(f"DROP INDEX IF EXISTS {index_name}")

            # Step 4: Drop the table
            logger.info("🗑️  Dropping video_hashes table...")
            cursor.execute("DROP TABLE IF EXISTS video_hashes")

            conn.commit()

            # Step 5: Verify method_signatures exists
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='method_signatures'
            """)
            method_sigs_exists = cursor.fetchone() is not None

            if not method_sigs_exists:
                logger.error("❌ ERROR: method_signatures table does not exist!")
                logger.error("   Database is in inconsistent state!")
                return False

            cursor.execute("SELECT COUNT(*) FROM method_signatures")
            method_sigs_count = cursor.fetchone()[0]
            logger.info(f"✅ method_signatures table exists with {method_sigs_count} rows")

            # Step 6: Verify cleanup
            cursor.execute("""
                SELECT COUNT(*) FROM sqlite_master
                WHERE type='table' AND name='video_hashes'
            """)
            still_exists = cursor.fetchone()[0] > 0

            if still_exists:
                logger.error("❌ ERROR: video_hashes table still exists after DROP!")
                return False

            logger.info("")
            logger.info("=" * 80)
            logger.info("✅ MIGRATION COMPLETED SUCCESSFULLY")
            logger.info("=" * 80)
            logger.info(f"   - Dropped video_hashes table ({row_count} rows)")
            logger.info(f"   - Dropped {len(indexes)} indexes")
            logger.info(f"   - method_signatures remains as single source of truth")
            logger.info("")

            return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        pool.shutdown()


if __name__ == "__main__":
    # Default database path
    DB_PATH = "/Users/nico/Documents/videoFlow/src/plugins/duplicate_finder/video_duplicates.db"

    if len(sys.argv) > 1:
        DB_PATH = sys.argv[1]

    logger.info(f"Database path: {DB_PATH}")

    if not os.path.exists(DB_PATH):
        logger.error(f"❌ Database file not found: {DB_PATH}")
        sys.exit(1)

    success = migrate_drop_video_hashes(DB_PATH)

    if success:
        logger.info("")
        logger.info("🎉 Migration completed successfully!")
        logger.info("")
        logger.info("NEXT STEPS:")
        logger.info("1. Update schema_manager.py to remove video_hashes table creation")
        logger.info("2. Update hasher.py log message (line 507)")
        logger.info("3. Test that caching still works with method_signatures")
        sys.exit(0)
    else:
        logger.error("")
        logger.error("❌ Migration failed! Please review errors above.")
        sys.exit(1)
