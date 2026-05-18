
import sys
import os

# Add the Server directory to sys.path explicitly
server_dir = os.path.dirname(os.path.abspath(__file__))
if server_dir not in sys.path:
    sys.path.append(server_dir)

from sqlalchemy import text
from app.database import engine_tools

TOOL_SEED = [
    (1, "Adjustable Wrench", "onesize", "Borrowable"),
    (2, "Allen Key", "onesize", "Borrowable"),
    (3, "Box Cutter", "onesize", "Borrowable"),
    (4, "Breadboard", "onesize", "Borrowable"),
    (5, "Caliper", "onesize", "Borrowable"),
    (6, "Channel Lock", "onesize", "Borrowable"),
    (7, "File", "onesize", "Borrowable"),
    (8, "Hot Glue Gun", "onesize", "Borrowable"),
    (9, "Multimeter", "onesize", "Borrowable"),
    (10, "Plier", "onesize", "Borrowable"),
    (11, "Safety Glasses", "onesize", "Borrowable"),
    (12, "Scissors", "onesize", "Borrowable"),
    (13, "Screwdriver", "onesize", "Borrowable"),
    (14, "Super Glue", "onesize", "Consumable"),
    (15, "Tape Measure", "onesize", "Borrowable"),
]

def reset_database():
    print("WARNING: This will delete ALL transactions and reseed the tools table.")
    user_input = input("Are you sure you want to proceed? (y/n): ")
    if user_input.lower() != 'y':
        print("Aborted.")
        return

    try:
        with engine_tools.connect() as conn:
            print("Resetting transactions and tools tables...")
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
            conn.execute(text("TRUNCATE TABLE transactions;"))
            conn.execute(text("TRUNCATE TABLE tools;"))

            print("Seeding tools with fixed IDs, sizes, and types...")
            insert_sql = text("""
                INSERT INTO tools (
                    tool_id,
                    tool_name,
                    tool_size,
                    tool_type,
                    current_status,
                    total_quantity,
                    available_quantity,
                    consumed_quantity,
                    trained,
                    image
                )
                VALUES (
                    :tool_id,
                    :tool_name,
                    :tool_size,
                    :tool_type,
                    'Available',
                    5,
                    5,
                    0,
                    0,
                    NULL
                )
            """)

            for tool_id, tool_name, tool_size, tool_type in TOOL_SEED:
                conn.execute(
                    insert_sql,
                    {
                        "tool_id": tool_id,
                        "tool_name": tool_name,
                        "tool_size": tool_size,
                        "tool_type": tool_type,
                    },
                )

            # Ensure next inserted tool_id continues after seeded IDs.
            conn.execute(text("ALTER TABLE tools AUTO_INCREMENT = 16;"))

            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
            conn.commit()

        print("Database reset successfully.")
        print("- Transactions cleared")
        print("- Tools reseeded (IDs 1-15)")
        print("- Quantity per tool: total=5, available=5, consumed=0")

    except Exception as e:
        print(f"Error resetting database: {e}")

if __name__ == "__main__":
    reset_database()
